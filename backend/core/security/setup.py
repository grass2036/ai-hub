"""
安全模块配置和初始化
Week 6 Day 4: 安全加固和权限配置

提供完整的安全系统配置管理和统一初始化接口
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import redis

from .enhanced_auth import EnhancedJWTAuth, TokenManager, AuthMiddleware
from .api_key_manager import APIKeyManager, APIKeyAuth
from .rbac import RBACManager, PermissionChecker
from .security_policy import SecurityPolicyManager
from .data_encryption import EncryptionKeyManager, DataEncryption, FieldEncryption, SensitiveDataMasker
from .security_audit import SecurityAuditor

@dataclass
class SecurityConfig:
    """安全配置"""
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    session_timeout: int = 3600
    max_concurrent_sessions: int = 5
    enable_geo_tracking: bool = True
    enable_device_fingerprinting: bool = True
    rate_limit_requests_per_minute: int = 60
    encryption_key_rotation_days: int = 90
    audit_retention_days: int = 90

@dataclass
class AuthenticationConfig:
    """认证配置"""
    jwt: Dict[str, Any]
    password_policy: Dict[str, Any]
    session_policy: Dict[str, Any]
    mfa: Dict[str, Any] = None

@dataclass
class AuthorizationConfig:
    """授权配置"""
    rbac_enabled: bool = True
    default_roles: List[str] = None
    permission_cache_ttl: int = 300
    role_hierarchy: Dict[str, List[str]] = None

@dataclass
class EncryptionConfig:
    """加密配置"""
    master_key: str
    default_algorithm: str = "fernet"
    key_rotation_days: int = 90
    field_encryption_enabled: bool = True
    data_masking_enabled: bool = True
    encrypted_fields: List[str] = None

@dataclass
class AuditConfig:
    """审计配置"""
    enabled: bool = True
    log_all_requests: bool = False
    log_sensitive_operations: bool = True
    geoip_database_path: Optional[str] = None
    risk_countries: List[str] = None
    alert_thresholds: Dict[str, float] = None

class SecuritySetup:
    """安全系统设置"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/security.json"
        self.config = self._load_config()
        self.redis_client: Optional[redis.Redis] = None

        # 安全组件
        self.jwt_auth: Optional[EnhancedJWTAuth] = None
        self.api_key_manager: Optional[APIKeyManager] = None
        self.rbac_manager: Optional[RBACManager] = None
        self.policy_manager: Optional[SecurityPolicyManager] = None
        self.encryption_key_manager: Optional[EncryptionKeyManager] = None
        self.data_encryption: Optional[DataEncryption] = None
        self.field_encryption: Optional[FieldEncryption] = None
        self.data_masker: Optional[SensitiveDataMasker] = None
        self.security_auditor: Optional[SecurityAuditor] = None

        # 中间件
        self.auth_middleware: Optional[AuthMiddleware] = None

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 返回默认配置
                return self._get_default_config()
        except Exception as e:
            logging.error(f"Failed to load security config: {str(e)}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "authentication": {
                "jwt": {
                    "secret_key": "your-super-secret-jwt-key-change-in-production",
                    "algorithm": "HS256",
                    "access_token_expire_minutes": 30,
                    "refresh_token_expire_days": 7
                },
                "password_policy": {
                    "min_length": 8,
                    "max_length": 128,
                    "require_uppercase": True,
                    "require_lowercase": True,
                    "require_digits": True,
                    "require_special_chars": True,
                    "forbidden_patterns": ["password", "123456", "qwerty"],
                    "min_score": 60
                },
                "session_policy": {
                    "max_idle_time": 3600,
                    "max_session_time": 28800,
                    "require_same_ip": False,
                    "max_concurrent_sessions": 5
                },
                "mfa": {
                    "enabled": False,
                    "issuer": "AI Hub",
                    "backup_codes_count": 10
                }
            },
            "authorization": {
                "rbac_enabled": True,
                "default_roles": ["user"],
                "permission_cache_ttl": 300,
                "role_hierarchy": {
                    "admin": ["manager", "user"],
                    "manager": ["user"]
                }
            },
            "api_keys": {
                "key_length": 32,
                "key_prefix_length": 8,
                "max_keys_per_user": 10,
                "default_rate_limit": 1000,
                "rate_limit_window": 3600
            },
            "encryption": {
                "master_key": "your-super-secret-encryption-key-change-in-production",
                "default_algorithm": "fernet",
                "key_rotation_days": 90,
                "field_encryption_enabled": True,
                "data_masking_enabled": True,
                "encrypted_fields": [
                    "email", "phone", "credit_card", "ssn",
                    "api_key", "password", "secret"
                ]
            },
            "security_policy": {
                "password_policy": {
                    "min_length": 8,
                    "require_uppercase": True,
                    "require_lowercase": True,
                    "require_digits": True,
                    "require_special_chars": True
                },
                "session_policy": {
                    "max_idle_time": 3600,
                    "max_session_time": 28800,
                    "require_same_ip": False
                },
                "rate_limit_policy": {
                    "window_size": 3600,
                    "max_requests": 1000,
                    "burst_size": 100
                },
                "ip_whitelist": [],
                "ip_blacklist": [],
                "access_time_policy": {
                    "enabled": False
                }
            },
            "audit": {
                "enabled": True,
                "log_all_requests": False,
                "log_sensitive_operations": True,
                "geoip_database_path": "/path/to/GeoLite2-City.mmdb",
                "risk_countries": ["CN", "RU", "KP", "IR"],
                "alert_thresholds": {
                    "high_risk_score": 8.0,
                    "failed_login_attempts": 5,
                    "unusual_access_frequency": 50
                },
                "retention_days": 90
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "password": "",
                "db": 0
            }
        }

    async def initialize(self) -> None:
        """初始化安全系统"""
        try:
            logging.info("Initializing AI Hub security system...")

            # 初始化Redis连接
            await self._setup_redis()

            # 初始化认证系统
            await self._setup_authentication()

            # 初始化API密钥管理
            await self._setup_api_key_management()

            # 初始化RBAC
            await self._setup_rbac()

            # 初始化安全策略
            await self._setup_security_policy()

            # 初始化加密系统
            await self._setup_encryption()

            # 初始化审计系统
            await self._setup_audit()

            # 初始化中间件
            await self._setup_middleware()

            logging.info("AI Hub security system initialized successfully")

        except Exception as e:
            logging.error(f"Failed to initialize security system: {str(e)}")
            raise

    async def _setup_redis(self) -> None:
        """设置Redis连接"""
        try:
            redis_config = self.config.get("redis", {})
            if redis_config.get("host"):
                self.redis_client = redis.Redis(
                    host=redis_config["host"],
                    port=redis_config.get("port", 6379),
                    password=redis_config.get("password"),
                    db=redis_config.get("db", 0),
                    decode_responses=True
                )
                # 测试连接
                self.redis_client.ping()
                logging.info("Redis connection established for security")
            else:
                logging.info("Redis not configured, security features will be limited")
        except Exception as e:
            logging.warning(f"Failed to setup Redis for security: {str(e)}")

    async def _setup_authentication(self) -> None:
        """设置认证系统"""
        try:
            auth_config = self.config["authentication"]["jwt"]
            self.jwt_auth = EnhancedJWTAuth(auth_config)
            await self.jwt_auth.initialize(self.redis_client)
            logging.info("JWT authentication initialized")
        except Exception as e:
            logging.error(f"Failed to setup authentication: {str(e)}")
            raise

    async def _setup_api_key_management(self) -> None:
        """设置API密钥管理"""
        try:
            api_key_config = self.config["api_keys"]
            self.api_key_manager = APIKeyManager(api_key_config)
            await self.api_key_manager.initialize(self.redis_client)
            logging.info("API key management initialized")
        except Exception as e:
            logging.error(f"Failed to setup API key management: {str(e)}")
            raise

    async def _setup_rbac(self) -> None:
        """设置RBAC"""
        try:
            rbac_config = self.config["authorization"]
            self.rbac_manager = RBACManager(rbac_config)
            await self.rbac_manager.initialize(self.redis_client)
            logging.info("RBAC system initialized")
        except Exception as e:
            logging.error(f"Failed to setup RBAC: {str(e)}")
            raise

    async def _setup_security_policy(self) -> None:
        """设置安全策略"""
        try:
            policy_config = self.config["security_policy"]
            self.policy_manager = SecurityPolicyManager(policy_config)
            await self.policy_manager.initialize(self.redis_client)
            logging.info("Security policy manager initialized")
        except Exception as e:
            logging.error(f"Failed to setup security policy: {str(e)}")
            raise

    async def _setup_encryption(self) -> None:
        """设置加密系统"""
        try:
            encryption_config = self.config["encryption"]

            # 密钥管理器
            self.encryption_key_manager = EncryptionKeyManager(encryption_config)
            await self.encryption_key_manager.initialize(self.redis_client)

            # 数据加密器
            self.data_encryption = DataEncryption(self.encryption_key_manager)

            # 字段级加密
            if encryption_config.get("field_encryption_enabled", True):
                self.field_encryption = FieldEncryption(self.data_encryption)
                self._setup_field_encryption_rules()

            # 数据脱敏
            if encryption_config.get("data_masking_enabled", True):
                self.data_masker = SensitiveDataMasker()

            logging.info("Encryption system initialized")
        except Exception as e:
            logging.error(f"Failed to setup encryption: {str(e)}")
            raise

    def _setup_field_encryption_rules(self) -> None:
        """设置字段加密规则"""
        if not self.field_encryption or not self.encryption_key_manager:
            return

        encrypted_fields = self.config["encryption"].get("encrypted_fields", [])
        key = asyncio.run(self.encryption_key_manager.get_active_key())

        if not key:
            return

        from .data_encryption import FieldEncryptionRule, DataType, EncryptionType

        for field in encrypted_fields:
            # 根据字段名确定数据类型
            data_type = self._get_data_type_for_field(field)

            rule = FieldEncryptionRule(
                field_name=field,
                data_type=data_type,
                encryption_type=EncryptionType.FERNET,
                key_id=key.key_id,
                enabled=True
            )
            self.field_encryption.add_encryption_rule(rule)

    def _get_data_type_for_field(self, field_name: str) -> 'DataType':
        """根据字段名获取数据类型"""
        from .data_encryption import DataType

        field_type_mapping = {
            "email": DataType.CONTACT_INFO,
            "phone": DataType.CONTACT_INFO,
            "credit_card": DataType.FINANCIAL_INFO,
            "ssn": DataType.IDENTITY_INFO,
            "password": DataType.CREDENTIALS,
            "secret": DataType.CREDENTIALS,
            "api_key": DataType.CREDENTIALS,
            "first_name": DataType.PERSONAL_INFO,
            "last_name": DataType.PERSONAL_INFO,
            "address": DataType.PERSONAL_INFO
        }

        return field_type_mapping.get(field_name.lower(), DataType.PERSONAL_INFO)

    async def _setup_audit(self) -> None:
        """设置审计系统"""
        try:
            audit_config = self.config["audit"]
            if audit_config.get("enabled", True):
                self.security_auditor = SecurityAuditor(audit_config)
                await self.security_auditor.initialize(self.redis_client)
                logging.info("Security audit system initialized")
        except Exception as e:
            logging.error(f"Failed to setup audit: {str(e)}")
            raise

    async def _setup_middleware(self) -> None:
        """设置中间件"""
        try:
            if self.jwt_auth:
                self.auth_middleware = AuthMiddleware(self.jwt_auth)
                logging.info("Authentication middleware initialized")
        except Exception as e:
            logging.error(f"Failed to setup middleware: {str(e)}")
            raise

    async def get_security_status(self) -> Dict[str, Any]:
        """获取安全状态"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "components": {
                "authentication": {
                    "enabled": self.jwt_auth is not None,
                    "status": "active" if self.jwt_auth else "disabled"
                },
                "api_key_management": {
                    "enabled": self.api_key_manager is not None,
                    "status": "active" if self.api_key_manager else "disabled"
                },
                "rbac": {
                    "enabled": self.rbac_manager is not None,
                    "status": "active" if self.rbac_manager else "disabled"
                },
                "security_policy": {
                    "enabled": self.policy_manager is not None,
                    "status": "active" if self.policy_manager else "disabled"
                },
                "encryption": {
                    "enabled": self.encryption_key_manager is not None,
                    "status": "active" if self.encryption_key_manager else "disabled"
                },
                "field_encryption": {
                    "enabled": self.field_encryption is not None,
                    "status": "active" if self.field_encryption else "disabled"
                },
                "data_masking": {
                    "enabled": self.data_masker is not None,
                    "status": "active" if self.data_masker else "disabled"
                },
                "audit": {
                    "enabled": self.security_auditor is not None,
                    "status": "active" if self.security_auditor else "disabled"
                }
            },
            "redis": {
                "connected": self.redis_client is not None
            }
        }

        # 获取详细统计
        if self.rbac_manager:
            status["rbac_details"] = {
                "total_permissions": len(await self.rbac_manager.get_all_permissions()),
                "total_roles": len(await self.rbac_manager.get_all_roles())
            }

        if self.encryption_key_manager:
            status["encryption_details"] = {
                "active_keys": len([k for k in self.encryption_key_manager.keys.values() if k.is_active]),
                "total_keys": len(self.encryption_key_manager.keys)
            }

        if self.security_auditor:
            # 获取最近24小时的统计
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            status["audit_details"] = await self.security_auditor.get_security_statistics(start_time, end_time)

        return status

    async def security_health_check(self) -> Dict[str, Any]:
        """安全健康检查"""
        health_status = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.now().isoformat()
        }

        all_healthy = True

        # 检查Redis连接
        if self.redis_client:
            try:
                self.redis_client.ping()
                health_status["checks"]["redis"] = {
                    "status": "healthy"
                }
            except Exception as e:
                health_status["checks"]["redis"] = {
                    "status": "error",
                    "message": str(e)
                }
                all_healthy = False
        else:
            health_status["checks"]["redis"] = {
                "status": "warning",
                "message": "Redis not configured"
            }

        # 检查JWT认证
        if self.jwt_auth:
            try:
                # 尝试创建一个测试令牌
                test_token = await self.jwt_auth.token_manager.create_access_token(
                    "test_user", "testuser", "test@example.com",
                    ["user"], ["read:profile"]
                )
                health_status["checks"]["jwt_auth"] = {
                    "status": "healthy"
                }
            except Exception as e:
                health_status["checks"]["jwt_auth"] = {
                    "status": "error",
                    "message": str(e)
                }
                all_healthy = False
        else:
            health_status["checks"]["jwt_auth"] = {
                "status": "error",
                "message": "JWT authentication not initialized"
            }
            all_healthy = False

        # 检查加密系统
        if self.encryption_key_manager:
            try:
                active_key = await self.encryption_key_manager.get_active_key()
                if active_key:
                    health_status["checks"]["encryption"] = {
                        "status": "healthy"
                    }
                else:
                    health_status["checks"]["encryption"] = {
                        "status": "error",
                        "message": "No active encryption key"
                    }
                    all_healthy = False
            except Exception as e:
                health_status["checks"]["encryption"] = {
                    "status": "error",
                    "message": str(e)
                }
                all_healthy = False
        else:
            health_status["checks"]["encryption"] = {
                "status": "error",
                "message": "Encryption system not initialized"
            }
            all_healthy = False

        # 检查RBAC系统
        if self.rbac_manager:
            try:
                permissions = await self.rbac_manager.get_all_permissions()
                roles = await self.rbac_manager.get_all_roles()
                health_status["checks"]["rbac"] = {
                    "status": "healthy",
                    "permissions_count": len(permissions),
                    "roles_count": len(roles)
                }
            except Exception as e:
                health_status["checks"]["rbac"] = {
                    "status": "error",
                    "message": str(e)
                }
                all_healthy = False
        else:
            health_status["checks"]["rbac"] = {
                "status": "error",
                "message": "RBAC system not initialized"
            }
            all_healthy = False

        if not all_healthy:
            health_status["status"] = "unhealthy"

        return health_status

    async def cleanup(self) -> None:
        """清理资源"""
        try:
            if self.redis_client:
                self.redis_client.close()
            logging.info("Security system cleaned up")
        except Exception as e:
            logging.error(f"Error during security cleanup: {str(e)}")

    def save_config(self) -> None:
        """保存配置"""
        try:
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            logging.info(f"Security config saved to {self.config_path}")
        except Exception as e:
            logging.error(f"Failed to save security config: {str(e)}")

    async def rotate_encryption_keys(self) -> bool:
        """轮换加密密钥"""
        try:
            if not self.encryption_key_manager:
                return False

            # 获取当前活跃密钥
            current_key = await self.encryption_key_manager.get_active_key()
            if not current_key:
                return False

            # 创建新密钥
            new_key = await self.encryption_key_manager.rotate_key(current_key.key_id)
            if not new_key:
                return False

            logging.info(f"Encryption key rotated: {current_key.key_id} -> {new_key.key_id}")
            return True

        except Exception as e:
            logging.error(f"Failed to rotate encryption keys: {str(e)}")
            return False

# 全局安全设置实例
security_setup: Optional[SecuritySetup] = None

async def get_security_config() -> SecuritySetup:
    """获取安全设置实例"""
    global security_setup
    if security_setup is None:
        security_setup = SecuritySetup()
        await security_setup.initialize()
    return security_setup

async def setup_production_security(config_path: Optional[str] = None) -> SecuritySetup:
    """设置生产环境安全"""
    setup = SecuritySetup(config_path)
    await setup.initialize()
    return setup

# 导入timedelta
from datetime import timedelta