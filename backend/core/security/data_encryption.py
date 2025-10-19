"""
数据加密和脱敏
Week 6 Day 4: 安全加固和权限配置

提供数据加密、字段级加密和敏感数据脱敏功能
"""

import base64
import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum
import redis
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import re
import json

class EncryptionType(Enum):
    """加密类型"""
    AES_256_GCM = "aes_256_gcm"
    FERNET = "fernet"
    RSA = "rsa"

class DataType(Enum):
    """数据类型"""
    PERSONAL_INFO = "personal_info"
    CONTACT_INFO = "contact_info"
    FINANCIAL_INFO = "financial_info"
    HEALTH_INFO = "health_info"
    IDENTITY_INFO = "identity_info"
    CREDENTIALS = "credentials"
    SYSTEM_LOG = "system_log"

class MaskingType(Enum):
    """脱敏类型"""
    FULL_MASK = "full_mask"           # 完全掩码
    PARTIAL_MASK = "partial_mask"     # 部分掩码
    HASH = "hash"                     # 哈希
    TOKENIZE = "tokenize"             # 令牌化
    GENERALIZE = "generalize"         # 泛化

@dataclass
class EncryptionKey:
    """加密密钥"""
    key_id: str
    key_data: bytes
    algorithm: EncryptionType
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = None

@dataclass
class FieldEncryptionRule:
    """字段加密规则"""
    field_name: str
    data_type: DataType
    encryption_type: EncryptionType
    key_id: str
    enabled: bool = True
    conditions: Dict[str, Any] = None

@dataclass
class DataMaskingRule:
    """数据脱敏规则"""
    field_name: str
    data_type: DataType
    masking_type: MaskingType
    pattern: Optional[str] = None
    replacement_char: str = "*"
    preserve_length: bool = True
    visible_chars: int = 0
    enabled: bool = True
    conditions: Dict[str, Any] = None

class EncryptionKeyManager:
    """加密密钥管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.keys: Dict[str, EncryptionKey] = {}
        self.default_algorithm = EncryptionType(config.get('default_algorithm', 'fernet'))
        self.key_rotation_days = config.get('key_rotation_days', 90)

    async def initialize(self, redis_client: Optional[redis.Redis] = None) -> None:
        """初始化密钥管理器"""
        self.redis_client = redis_client

        # 加载现有密钥
        await self._load_keys()

        # 创建主密钥（如果不存在）
        if not self.keys:
            await self._create_master_key()

    def _generate_key(self, algorithm: EncryptionType) -> bytes:
        """生成密钥"""
        if algorithm == EncryptionType.FERNET:
            return Fernet.generate_key()
        elif algorithm == EncryptionType.AES_256_GCM:
            return secrets.token_bytes(32)  # 256位密钥
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    async def create_key(
        self,
        algorithm: Optional[EncryptionType] = None,
        expires_in_days: Optional[int] = None,
        metadata: Dict[str, Any] = None
    ) -> EncryptionKey:
        """创建新的加密密钥"""
        algorithm = algorithm or self.default_algorithm
        key_data = self._generate_key(algorithm)

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        key = EncryptionKey(
            key_id=str(uuid.uuid4()),
            key_data=key_data,
            algorithm=algorithm,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            metadata=metadata or {}
        )

        # 存储密钥
        await self._store_key(key)
        self.keys[key.key_id] = key

        return key

    async def get_active_key(self, algorithm: Optional[EncryptionType] = None) -> Optional[EncryptionKey]:
        """获取活跃的密钥"""
        algorithm = algorithm or self.default_algorithm

        for key in self.keys.values():
            if (key.algorithm == algorithm and
                key.is_active and
                (key.expires_at is None or key.expires_at > datetime.utcnow())):
                return key

        return None

    async def get_key_by_id(self, key_id: str) -> Optional[EncryptionKey]:
        """根据ID获取密钥"""
        return self.keys.get(key_id)

    async def rotate_key(self, key_id: str) -> Optional[EncryptionKey]:
        """轮换密钥"""
        old_key = self.keys.get(key_id)
        if not old_key:
            return None

        # 创建新密钥
        new_key = await self.create_key(
            algorithm=old_key.algorithm,
            expires_in_days=self.key_rotation_days,
            metadata=old_key.metadata
        )

        # 标记旧密钥为非活跃
        old_key.is_active = False
        await self._store_key(old_key)

        return new_key

    async def _store_key(self, key: EncryptionKey) -> None:
        """存储密钥到Redis"""
        if not self.redis_client:
            return

        key_data_encrypted = self._encrypt_key_data(key.key_data)

        await self.redis_client.hset(f"encryption_key:{key.key_id}", mapping={
            "key_id": key.key_id,
            "key_data": base64.b64encode(key_data_encrypted).decode(),
            "algorithm": key.algorithm.value,
            "created_at": key.created_at.isoformat(),
            "expires_at": key.expires_at.isoformat() if key.expires_at else "",
            "is_active": str(key.is_active),
            "metadata": json.dumps(key.metadata or {})
        })

        await self.redis_client.sadd("encryption_keys:all", key.key_id)

        # 设置过期时间
        if key.expires_at:
            ttl = int((key.expires_at - datetime.utcnow()).total_seconds())
            if ttl > 0:
                await self.redis_client.expire(f"encryption_key:{key.key_id}", ttl)

    async def _load_keys(self) -> None:
        """从Redis加载密钥"""
        if not self.redis_client:
            return

        key_ids = await self.redis_client.smembers("encryption_keys:all")

        for key_id in key_ids:
            data = await self.redis_client.hgetall(f"encryption_key:{key_id}")
            if data:
                key_data_encrypted = base64.b64decode(data["key_data"])
                key_data = self._decrypt_key_data(key_data_encrypted)

                key = EncryptionKey(
                    key_id=data["key_id"],
                    key_data=key_data,
                    algorithm=EncryptionType(data["algorithm"]),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    expires_at=datetime.fromisoformat(data["expires_at"]) if data["expires_at"] else None,
                    is_active=data["is_active"] == "True",
                    metadata=json.loads(data.get("metadata", "{}"))
                )

                self.keys[key_id] = key

    def _encrypt_key_data(self, key_data: bytes) -> bytes:
        """加密密钥数据（使用主密钥）"""
        master_key = self.config.get("master_key")
        if not master_key:
            return key_data

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"ai_hub_encryption_salt",
            backend=default_backend()
        )
        derived_key = kdf.derive(master_key.encode())

        f = Fernet(base64.urlsafe_b64encode(derived_key))
        return f.encrypt(key_data)

    def _decrypt_key_data(self, encrypted_key_data: bytes) -> bytes:
        """解密密钥数据"""
        master_key = self.config.get("master_key")
        if not master_key:
            return encrypted_key_data

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"ai_hub_encryption_salt",
            backend=default_backend()
        )
        derived_key = kdf.derive(master_key.encode())

        f = Fernet(base64.urlsafe_b64encode(derived_key))
        return f.decrypt(encrypted_key_data)

    async def _create_master_key(self) -> None:
        """创建主密钥"""
        master_key = await self.create_key(
            algorithm=self.default_algorithm,
            expires_in_days=365,  # 主密钥一年轮换一次
            metadata={"purpose": "master_key", "auto_rotated": False}
        )
        logging.info(f"Created master encryption key: {master_key.key_id}")

class DataEncryption:
    """数据加密器"""

    def __init__(self, key_manager: EncryptionKeyManager):
        self.key_manager = key_manager

    async def encrypt(
        self,
        data: Union[str, bytes],
        key_id: Optional[str] = None,
        algorithm: Optional[EncryptionType] = None
    ) -> Dict[str, Any]:
        """加密数据"""
        if isinstance(data, str):
            data = data.encode('utf-8')

        # 获取加密密钥
        if key_id:
            key = await self.key_manager.get_key_by_id(key_id)
        else:
            key = await self.key_manager.get_active_key(algorithm)

        if not key:
            raise ValueError("No encryption key available")

        # 根据算法加密
        if key.algorithm == EncryptionType.FERNET:
            encrypted_data = self._encrypt_fernet(data, key)
        elif key.algorithm == EncryptionType.AES_256_GCM:
            encrypted_data = self._encrypt_aes_gcm(data, key)
        else:
            raise ValueError(f"Unsupported encryption algorithm: {key.algorithm}")

        return {
            "encrypted_data": base64.b64encode(encrypted_data["data"]).decode(),
            "key_id": key.key_id,
            "algorithm": key.algorithm.value,
            "nonce": base64.b64encode(encrypted_data.get("nonce", b"")).decode(),
            "tag": base64.b64encode(encrypted_data.get("tag", b"")).decode()
        }

    async def decrypt(self, encrypted_data: Dict[str, Any]) -> bytes:
        """解密数据"""
        key_id = encrypted_data["key_id"]
        algorithm = EncryptionType(encrypted_data["algorithm"])

        # 获取解密密钥
        key = await self.key_manager.get_key_by_id(key_id)
        if not key:
            raise ValueError(f"Encryption key not found: {key_id}")

        # 解码数据
        data = base64.b64decode(encrypted_data["encrypted_data"])
        nonce = base64.b64decode(encrypted_data.get("nonce", ""))
        tag = base64.b64decode(encrypted_data.get("tag", ""))

        # 根据算法解密
        if algorithm == EncryptionType.FERNET:
            return self._decrypt_fernet(data, key)
        elif algorithm == EncryptionType.AES_256_GCM:
            return self._decrypt_aes_gcm(data, nonce, tag, key)
        else:
            raise ValueError(f"Unsupported decryption algorithm: {algorithm}")

    def _encrypt_fernet(self, data: bytes, key: EncryptionKey) -> Dict[str, bytes]:
        """Fernet加密"""
        f = Fernet(key.key_data)
        encrypted_data = f.encrypt(data)
        return {"data": encrypted_data}

    def _decrypt_fernet(self, encrypted_data: bytes, key: EncryptionKey) -> bytes:
        """Fernet解密"""
        f = Fernet(key.key_data)
        return f.decrypt(encrypted_data)

    def _encrypt_aes_gcm(self, data: bytes, key: EncryptionKey) -> Dict[str, bytes]:
        """AES-GCM加密"""
        nonce = secrets.token_bytes(12)  # 96位nonce
        cipher = Cipher(
            algorithms.AES(key.key_data),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(data) + encryptor.finalize()
        return {
            "data": encrypted_data,
            "nonce": nonce,
            "tag": encryptor.tag
        }

    def _decrypt_aes_gcm(self, encrypted_data: bytes, nonce: bytes, tag: bytes, key: EncryptionKey) -> bytes:
        """AES-GCM解密"""
        cipher = Cipher(
            algorithms.AES(key.key_data),
            modes.GCM(nonce, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        return decryptor.update(encrypted_data) + decryptor.finalize()

class FieldEncryption:
    """字段级加密"""

    def __init__(self, data_encryption: DataEncryption):
        self.data_encryption = data_encryption
        self.encryption_rules: Dict[str, FieldEncryptionRule] = {}

    def add_encryption_rule(self, rule: FieldEncryptionRule) -> None:
        """添加加密规则"""
        self.encryption_rules[rule.field_name] = rule

    async def encrypt_field(
        self,
        field_name: str,
        value: Any,
        context: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """加密字段"""
        rule = self.encryption_rules.get(field_name)
        if not rule or not rule.enabled:
            return None

        # 检查条件
        if rule.conditions and not self._evaluate_conditions(rule.conditions, context):
            return None

        if value is None:
            return None

        try:
            # 转换为字符串
            if not isinstance(value, (str, bytes)):
                value = str(value)

            # 加密数据
            encrypted_result = await self.data_encryption.encrypt(
                value, rule.key_id, rule.encryption_type
            )

            return {
                "field_name": field_name,
                "encrypted": True,
                "data": encrypted_result,
                "original_type": type(value).__name__
            }

        except Exception as e:
            logging.error(f"Failed to encrypt field {field_name}: {str(e)}")
            return None

    async def decrypt_field(self, field_name: str, encrypted_data: Dict[str, Any]) -> Any:
        """解密字段"""
        if not encrypted_data.get("encrypted"):
            return encrypted_data.get("data")

        rule = self.encryption_rules.get(field_name)
        if not rule:
            return None

        try:
            decrypted_bytes = await self.data_encryption.decrypt(encrypted_data["data"])
            original_type = encrypted_data.get("original_type", "str")

            # 尝试恢复原始类型
            if original_type == "str":
                return decrypted_bytes.decode('utf-8')
            elif original_type == "int":
                return int(decrypted_bytes.decode('utf-8'))
            elif original_type == "float":
                return float(decrypted_bytes.decode('utf-8'))
            elif original_type == "bool":
                return decrypted_bytes.decode('utf-8').lower() == "true"
            else:
                return decrypted_bytes

        except Exception as e:
            logging.error(f"Failed to decrypt field {field_name}: {str(e)}")
            return None

    def _evaluate_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """评估条件"""
        if not context:
            return True

        for field, expected_value in conditions.items():
            if context.get(field) != expected_value:
                return False

        return True

class SensitiveDataMasker:
    """敏感数据脱敏器"""

    def __init__(self):
        self.masking_rules: Dict[str, DataMaskingRule] = {}
        self._setup_default_rules()

    def add_masking_rule(self, rule: DataMaskingRule) -> None:
        """添加脱敏规则"""
        self.masking_rules[rule.field_name] = rule

    def mask_data(
        self,
        field_name: str,
        value: Any,
        context: Dict[str, Any] = None
    ) -> Any:
        """脱敏数据"""
        if value is None:
            return None

        rule = self.masking_rules.get(field_name)
        if not rule or not rule.enabled:
            return value

        # 检查条件
        if rule.conditions and not self._evaluate_conditions(rule.conditions, context):
            return value

        # 转换为字符串
        str_value = str(value)

        try:
            if rule.masking_type == MaskingType.FULL_MASK:
                return self._full_mask(str_value, rule)
            elif rule.masking_type == MaskingType.PARTIAL_MASK:
                return self._partial_mask(str_value, rule)
            elif rule.masking_type == MaskingType.HASH:
                return self._hash_mask(str_value, rule)
            elif rule.masking_type == MaskingType.TOKENIZE:
                return self._tokenize_mask(str_value, rule)
            elif rule.masking_type == MaskingType.GENERALIZE:
                return self._generalize_mask(str_value, rule)
            else:
                return value

        except Exception as e:
            logging.error(f"Failed to mask field {field_name}: {str(e)}")
            return value

    def _full_mask(self, value: str, rule: DataMaskingRule) -> str:
        """完全掩码"""
        if rule.preserve_length:
            return rule.replacement_char * len(value)
        else:
            return rule.replacement_char * 8

    def _partial_mask(self, value: str, rule: DataMaskingRule) -> str:
        """部分掩码"""
        length = len(value)
        visible_chars = min(rule.visible_chars, length)
        hidden_chars = length - visible_chars

        if rule.pattern:
            # 使用正则表达式模式
            try:
                pattern_match = re.match(rule.pattern, value)
                if pattern_match:
                    return pattern_match.expand(rule.replacement_char * hidden_chars)
            except re.error:
                pass

        # 默认部分掩码逻辑
        if visible_chars == 0:
            return rule.replacement_char * length
        elif visible_chars <= 3:
            # 显示前几个字符
            return value[:visible_chars] + rule.replacement_char * hidden_chars
        else:
            # 显示前几个和后几个字符
            front_visible = visible_chars // 2
            back_visible = visible_chars - front_visible
            middle_hidden = length - front_visible - back_visible
            return (value[:front_visible] +
                   rule.replacement_char * middle_hidden +
                   value[-back_visible:] if back_visible > 0 else
                   value[:front_visible] + rule.replacement_char * middle_hidden)

    def _hash_mask(self, value: str, rule: DataMaskingRule) -> str:
        """哈希掩码"""
        salt = rule.metadata.get("salt", "ai_hub_masking_salt") if rule.metadata else "ai_hub_masking_salt"
        hash_value = hashlib.sha256((value + salt).encode()).hexdigest()
        return f"hashed:{hash_value[:16]}"

    def _tokenize_mask(self, value: str, rule: DataMaskingRule) -> str:
        """令牌化掩码"""
        # 简化的令牌化实现
        import uuid
        token = str(uuid.uuid4())
        # 在实际实现中，应该维护token到原始值的映射
        return f"token:{token}"

    def _generalize_mask(self, value: str, rule: DataMaskingRule) -> str:
        """泛化掩码"""
        # 根据数据类型进行泛化
        data_type = rule.data_type

        if data_type == DataType.AGE:
            try:
                age = int(value)
                if age < 18:
                    return "<18"
                elif age < 30:
                    return "18-29"
                elif age < 50:
                    return "30-49"
                elif age < 65:
                    return "50-64"
                else:
                    return "65+"
            except ValueError:
                return "unknown"

        elif data_type == DataType.CONTACT_INFO:
            # 电话号码泛化
            if re.match(r'^\+?\d{10,15}$', value):
                return value[:3] + "****" + value[-2:]

        elif data_type == DataType.FINANCIAL_INFO:
            # 信用卡号泛化
            if re.match(r'^\d{13,19}$', value):
                return "****-****-****-" + value[-4:]

        # 默认返回部分掩码
        return self._partial_mask(value, rule)

    def _evaluate_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """评估条件"""
        if not context:
            return True

        for field, expected_value in conditions.items():
            if context.get(field) != expected_value:
                return False

        return True

    def _setup_default_rules(self) -> None:
        """设置默认脱敏规则"""
        default_rules = [
            DataMaskingRule(
                field_name="password",
                data_type=DataType.CREDENTIALS,
                masking_type=MaskingType.FULL_MASK,
                preserve_length=False
            ),
            DataMaskingRule(
                field_name="email",
                data_type=DataType.CONTACT_INFO,
                masking_type=MaskingType.PARTIAL_MASK,
                visible_chars=3,
                preserve_length=True
            ),
            DataMaskingRule(
                field_name="phone",
                data_type=DataType.CONTACT_INFO,
                masking_type=MaskingType.PARTIAL_MASK,
                visible_chars=3,
                preserve_length=True
            ),
            DataMaskingRule(
                field_name="credit_card",
                data_type=DataType.FINANCIAL_INFO,
                masking_type=MaskingType.PARTIAL_MASK,
                visible_chars=4,
                preserve_length=True
            ),
            DataMaskingRule(
                field_name="ssn",
                data_type=DataType.IDENTITY_INFO,
                masking_type=MaskingType.PARTIAL_MASK,
                visible_chars=4,
                preserve_length=True
            ),
            DataMaskingRule(
                field_name="api_key",
                data_type=DataType.CREDENTIALS,
                masking_type=MaskingType.PARTIAL_MASK,
                visible_chars=8,
                preserve_length=True
            )
        ]

        for rule in default_rules:
            self.masking_rules[rule.field_name] = rule

# 导入uuid和timedelta
import uuid
from datetime import timedelta