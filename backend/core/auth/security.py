"""
安全工具函数

提供密码加密、令牌生成、安全验证等基础安全功能。
"""

import secrets
import hashlib
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import re


class SecurityUtils:
    """安全工具类"""

    # 密码强度要求
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True

    # 令牌配置
    TOKEN_LENGTH = 32
    API_KEY_LENGTH = 32

    @staticmethod
    def hash_password(password: str) -> str:
        """
        安全加密密码

        Args:
            password: 明文密码

        Returns:
            加密后的密码哈希
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        验证密码

        Args:
            password: 明文密码
            hashed_password: 加密的密码哈希

        Returns:
            密码是否匹配
        """
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )

    @staticmethod
    def generate_secure_token(length: int = None) -> str:
        """
        生成安全令牌

        Args:
            length: 令牌长度

        Returns:
            安全令牌字符串
        """
        length = length or SecurityUtils.TOKEN_LENGTH
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_api_key() -> str:
        """
        生成API密钥

        Returns:
            API密钥字符串
        """
        # 生成更安全的API密钥格式
        token = secrets.token_urlsafe(SecurityUtils.API_KEY_LENGTH)
        return f"ah_{token}"  # ah_ = AI Hub prefix

    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """
        验证密码强度

        Args:
            password: 要验证的密码

        Returns:
            验证结果字典
        """
        errors = []
        is_strong = True

        # 长度检查
        if len(password) < SecurityUtils.PASSWORD_MIN_LENGTH:
            errors.append(f"密码长度至少{SecurityUtils.PASSWORD_MIN_LENGTH}位")
            is_strong = False

        # 大写字母检查
        if SecurityUtils.PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("密码必须包含至少一个大写字母")
            is_strong = False

        # 小写字母检查
        if SecurityUtils.PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("密码必须包含至少一个小写字母")
            is_strong = False

        # 数字检查
        if SecurityUtils.PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
            errors.append("密码必须包含至少一个数字")
            is_strong = False

        # 特殊字符检查
        if SecurityUtils.PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("密码必须包含至少一个特殊字符")
            is_strong = False

        # 常见弱密码检查
        weak_passwords = [
            "password", "123456", "qwerty", "admin", "letmein",
            "welcome", "monkey", "dragon", "master", "hello"
        ]
        if password.lower() in weak_passwords:
            errors.append("不能使用常见弱密码")
            is_strong = False

        return {
            "is_strong": is_strong,
            "errors": errors,
            "strength_score": SecurityUtils._calculate_password_strength(password)
        }

    @staticmethod
    def _calculate_password_strength(password: str) -> int:
        """
        计算密码强度分数 (0-100)

        Args:
            password: 密码

        Returns:
            强度分数
        """
        score = 0

        # 长度分数 (0-30)
        length_score = min(len(password) * 2, 30)
        score += length_score

        # 字符类型分数 (0-40)
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 10

        # 复杂性分数 (0-30)
        unique_chars = len(set(password))
        complexity_score = min(unique_chars * 3, 30)
        score += complexity_score

        return min(score, 100)

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        验证邮箱格式

        Args:
            email: 邮箱地址

        Returns:
            邮箱格式是否有效
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    @staticmethod
    def sanitize_input(input_string: str) -> str:
        """
        清理输入字符串，防止XSS攻击

        Args:
            input_string: 输入字符串

        Returns:
            清理后的字符串
        """
        if not input_string:
            return ""

        # 移除潜在的HTML标签
        import html
        sanitized = html.escape(input_string)

        # 移除额外的空白字符
        sanitized = ' '.join(sanitized.split())

        return sanitized

    @staticmethod
    def generate_session_id() -> str:
        """
        生成会话ID

        Returns:
            会话ID字符串
        """
        return secrets.token_hex(16)

    @staticmethod
    def is_safe_url(url: str, allowed_hosts: list = None) -> bool:
        """
        检查URL是否安全（防止开放重定向）

        Args:
            url: 要检查的URL
            allowed_hosts: 允许的主机列表

        Returns:
            URL是否安全
        """
        if not url:
            return False

        if url.startswith(('http://', 'https://')):
            if allowed_hosts:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                return parsed.netloc in allowed_hosts
            return True

        # 相对URL通常是安全的
        return url.startswith('/') and not url.startswith('//')

    @staticmethod
    def rate_limit_key(identifier: str, action: str) -> str:
        """
        生成速率限制键

        Args:
            identifier: 标识符（IP地址、用户ID等）
            action: 操作类型

        Returns:
            速率限制键
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"rate_limit:{action}:{identifier}:{timestamp}"

    @staticmethod
    def extract_client_info(request) -> Dict[str, str]:
        """
        从请求中提取客户端信息

        Args:
            request: FastAPI请求对象

        Returns:
            客户端信息字典
        """
        client_info = {
            "ip_address": "",
            "user_agent": "",
            "referer": ""
        }

        # 获取IP地址
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_info["ip_address"] = forwarded_for.split(",")[0].strip()
        else:
            client_info["ip_address"] = request.client.host if request.client else ""

        # 获取User-Agent
        client_info["user_agent"] = request.headers.get("User-Agent", "")

        # 获取Referer
        client_info["referer"] = request.headers.get("Referer", "")

        return client_info