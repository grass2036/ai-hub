"""
API Security Protection and Validation
Week 4 Day 26: Performance Optimization and Security Hardening
"""

import re
import hashlib
import hmac
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, validator
import jwt
from passlib.context import CryptContext

from backend.config.settings import get_settings
from backend.models.developer import Developer, DeveloperAPIKey

logger = logging.getLogger(__name__)


class SecurityValidator:
    """安全验证器"""

    def __init__(self):
        self.settings = get_settings()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # 安全模式配置
        self.security_patterns = {
            "sql_injection": [
                r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|SCRIPT)\b)",
                r"([';]|\-\-|\#)",
                r"(\bOR\b.*=.*\bOR\b|\bAND\b.*=.*\bAND\b)",
                r"(\bSLEEP\b|\bBENCHMARK\b)",
                r"(\bINFORMATION_SCHEMA\b|\bSYS\.)",
            ],
            "xss": [
                r"(<script[^>]*>.*?</script>)",
                r"(javascript:|vbscript:|data:)",
                r"(on\w+\s*=)",
                r"(<iframe[^>]*>)",
                r"(<object[^>]*>)",
                r"(<embed[^>]*>)",
                r"eval\s*\(|alert\s*\(|confirm\s*\(",
            ],
            "path_traversal": [
                r"(\.\./|\.\.\\)",
                r"(%2e%2e%2f|%2e%2e\\)",
                r"(/etc/passwd|/proc/|/sys/)",
                r"(\\windows\\system32|c:\\windows)",
            ],
            "command_injection": [
                r"(;\s*\||\|\s*;)",
                r"(&&|\|\|)",
                r"(`\$\(|\$\(`)",
                r"(>\s*/dev/null|2>&1)",
                r"(nc\s|netcat|telnet)",
            ],
            "ldap_injection": [
                r"(\*\)\(|\)\(\*)",
                r"(\(|\))",
                r"(\&|\|)",
                r"(!=|=)",
            ]
        }

    def validate_input(self, input_data: Union[str, Dict, List], input_type: str = "general") -> Dict[str, Any]:
        """验证输入数据"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "sanitized": input_data
        }

        try:
            if isinstance(input_data, str):
                validation_result = self._validate_string(input_data, input_type, validation_result)
            elif isinstance(input_data, dict):
                validation_result = self._validate_dict(input_data, validation_result)
            elif isinstance(input_data, list):
                validation_result = self._validate_list(input_data, validation_result)

        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
            logger.error(f"Input validation error: {e}")

        return validation_result

    def _validate_string(self, input_str: str, input_type: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证字符串输入"""
        # 检查长度
        if len(input_str) > 10000:
            result["valid"] = False
            result["errors"].append("Input too long")

        # 检查各种注入攻击
        for attack_type, patterns in self.security_patterns.items():
            for pattern in patterns:
                if re.search(pattern, input_str, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                    result["valid"] = False
                    result["errors"].append(f"Potential {attack_type.replace('_', ' ')} attack detected")
                    logger.warning(f"Security threat detected: {attack_type} in input: {input_str[:100]}...")
                    break

        # 特定类型的验证
        if input_type == "email":
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, input_str):
                result["valid"] = False
                result["errors"].append("Invalid email format")

        elif input_type == "api_key":
            if not re.match(r'^[a-zA-Z0-9_-]+$', input_str):
                result["valid"] = False
                result["errors"].append("Invalid API key format")

        elif input_type == "prompt":
            # 对提示词进行特殊检查
            if self._contains_malicious_prompt(input_str):
                result["valid"] = False
                result["errors"].append("Malicious prompt detected")

        # 清理输入
        result["sanitized"] = self._sanitize_string(input_str)

        return result

    def _validate_dict(self, input_dict: Dict, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证字典输入"""
        sanitized_dict = {}

        for key, value in input_dict.items():
            # 验证键名
            if isinstance(key, str):
                key_validation = self._validate_string(key, "general", {"valid": True, "errors": [], "warnings": []})
                if not key_validation["valid"]:
                    result["valid"] = False
                    result["errors"].extend([f"Invalid key: {error}" for error in key_validation["errors"]])
                    continue

            # 验证值
            if isinstance(value, str):
                value_validation = self._validate_string(value, "general", {"valid": True, "errors": [], "warnings": []})
                if not value_validation["valid"]:
                    result["valid"] = False
                    result["errors"].extend([f"Invalid value for key '{key}': {error}" for error in value_validation["errors"]])
                    continue
                sanitized_dict[key] = value_validation["sanitized"]
            elif isinstance(value, (dict, list)):
                # 递归验证嵌套结构
                nested_validation = self.validate_input(value, "general")
                if not nested_validation["valid"]:
                    result["valid"] = False
                    result["errors"].extend([f"Invalid nested data in key '{key}': {error}" for error in nested_validation["errors"]])
                    continue
                sanitized_dict[key] = nested_validation["sanitized"]
            else:
                sanitized_dict[key] = value

        result["sanitized"] = sanitized_dict
        return result

    def _validate_list(self, input_list: List, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证列表输入"""
        sanitized_list = []

        if len(input_list) > 1000:
            result["valid"] = False
            result["errors"].append("List too long")

        for i, item in enumerate(input_list):
            if isinstance(item, str):
                item_validation = self._validate_string(item, "general", {"valid": True, "errors": [], "warnings": []})
                if not item_validation["valid"]:
                    result["valid"] = False
                    result["errors"].append(f"Invalid item at index {i}: {', '.join(item_validation['errors'])}")
                    continue
                sanitized_list.append(item_validation["sanitized"])
            elif isinstance(item, (dict, list)):
                nested_validation = self.validate_input(item, "general")
                if not nested_validation["valid"]:
                    result["valid"] = False
                    result["errors"].append(f"Invalid nested item at index {i}")
                    continue
                sanitized_list.append(nested_validation["sanitized"])
            else:
                sanitized_list.append(item)

        result["sanitized"] = sanitized_list
        return result

    def _contains_malicious_prompt(self, prompt: str) -> bool:
        """检查恶意提示词"""
        malicious_patterns = [
            r"(ignore|forget|disregard).*(previous|above|earlier).*(instruction|prompt|rule)",
            r"(act as|pretend to be|roleplay as).*(jailbreak|malicious|harmful)",
            r"(system|developer|admin).*(prompt|instruction|override)",
            r"(execute|run|perform).*(code|script|command)",
            r"(bypass|circumvent|override).*(safety|security|filter)",
            r"( DAN |do anything now)",
            r"(tell me how to|instruct me to|show me how to).*(harmful|illegal|dangerous)",
        ]

        for pattern in malicious_patterns:
            if re.search(pattern, prompt, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                return True

        return False

    def _sanitize_string(self, input_str: str) -> str:
        """清理字符串"""
        # 移除潜在的恶意字符
        sanitized = input_str

        # 移除控制字符
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)

        # 限制Unicode字符范围
        sanitized = re.sub(r'[\uFFF0-\uFFFF]', '', sanitized)

        # 移除多余的空白字符
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()

        return sanitized

    def hash_password(self, password: str) -> str:
        """哈希密码"""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def generate_api_key(self) -> str:
        """生成API密钥"""
        return f"ah_{secrets.token_urlsafe(32)}"

    def generate_jwt_token(self, payload: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """生成JWT令牌"""
        to_encode = payload.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)

        to_encode.update({"exp": expire})

        return jwt.encode(
            to_encode,
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm
        )

    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def create_signature(self, data: str, secret: str) -> str:
        """创建签名"""
        return hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()

    def verify_signature(self, data: str, signature: str, secret: str) -> bool:
        """验证签名"""
        expected_signature = self.create_signature(data, secret)
        return hmac.compare_digest(expected_signature, signature)


class APIKeyValidator:
    """API密钥��证器"""

    def __init__(self, security_validator: SecurityValidator):
        self.security_validator = security_validator

    async def validate_api_key(self, api_key: str, request: Request) -> Optional[DeveloperAPIKey]:
        """验证API密钥"""
        try:
            # 基本格式验证
            validation_result = self.security_validator.validate_input(api_key, "api_key")
            if not validation_result["valid"]:
                logger.warning(f"Invalid API key format: {api_key[:10]}...")
                return None

            # 从数据库查找API密钥
            from backend.core.database import get_db
            db = next(get_db())

            try:
                key_record = db.query(DeveloperAPIKey).filter(
                    DeveloperAPIKey.key_prefix == api_key[:10],  # 只比较前缀
                    DeveloperAPIKey.is_active == True
                ).first()

                if not key_record:
                    logger.warning(f"API key not found: {api_key[:10]}...")
                    return None

                # 验证完整密钥
                if not hmac.compare_digest(key_record.key_hash, self.security_validator.create_signature(api_key, key_record.salt)):
                    logger.warning(f"API key signature mismatch: {api_key[:10]}...")
                    return None

                # 检查IP白名单 (如果有配置)
                if key_record.allowed_ips and len(key_record.allowed_ips) > 0:
                    client_ip = self.security_validator._get_client_ip(request)
                    if client_ip not in key_record.allowed_ips:
                        logger.warning(f"IP not in whitelist: {client_ip}")
                        return None

                # 检查域名白名单 (如果有配置)
                if key_record.allowed_domains and len(key_record.allowed_domains) > 0:
                    origin = request.headers.get("origin", "")
                    if origin not in key_record.allowed_domains:
                        logger.warning(f"Domain not in whitelist: {origin}")
                        return None

                # 更新最后使用时间
                key_record.last_used = datetime.utcnow()
                db.commit()

                return key_record

            finally:
                db.close()

        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return None


class RequestValidator(BaseModel):
    """请求验证模型"""

    @validator('*', pre=True)
    def sanitize_input(cls, v):
        """自动清理输入"""
        if isinstance(v, str):
            # 移除潜在的恶意字符
            v = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', v)
            v = re.sub(r'\s+', ' ', v).strip()
        return v


class SecurityHeaders:
    """安全响应头"""

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """获取安全响应头"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "accelerometer=()"
            ),
            "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }


class InputSanitizer:
    """输入清理器"""

    @staticmethod
    def sanitize_html(html_content: str) -> str:
        """清理HTML内容"""
        # 移除危险标签和属性
        dangerous_tags = [
            'script', 'iframe', 'object', 'embed', 'form', 'input',
            'textarea', 'button', 'select', 'option', 'link', 'meta'
        ]

        dangerous_attributes = [
            'onload', 'onerror', 'onclick', 'onmouseover', 'onmouseout',
            'onfocus', 'onblur', 'onchange', 'onsubmit', 'onreset'
        ]

        # 移除危险标签
        for tag in dangerous_tags:
            html_content = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
            html_content = re.sub(f'<{tag}[^>]*/>', '', html_content, flags=re.IGNORECASE)

        # 移除危险属性
        for attr in dangerous_attributes:
            html_content = re.sub(f'{attr}\s*=\s*["\'][^"\']*["\']', '', html_content, flags=re.IGNORECASE)

        return html_content

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理文件名"""
        # 移除危险字符
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # 移除控制字符
        filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
        # 限制长度
        filename = filename[:255]
        # 移除前后空格和点
        filename = filename.strip(' .')

        return filename or "unnamed_file"


# 全局安全验证器实例
security_validator = SecurityValidator()
api_key_validator = APIKeyValidator(security_validator)


def get_security_validator() -> SecurityValidator:
    """获取安全验证器实例"""
    return security_validator


def get_api_key_validator() -> APIKeyValidator:
    """获取API密钥验证器实例"""
    return api_key_validator