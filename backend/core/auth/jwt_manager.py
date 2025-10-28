"""
JWT认证管理器

提供JWT令牌的生成、验证、刷新等功能。
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
from fastapi import HTTPException, status
import logging

from .security import SecurityUtils

logger = logging.getLogger(__name__)


class JWTManager:
    """JWT令牌管理器"""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7
    ):
        """
        初始化JWT管理器

        Args:
            secret_key: JWT密钥
            algorithm: 加密算法
            access_token_expire_minutes: 访问令牌过期时间（分钟）
            refresh_token_expire_days: 刷新令牌过期时间（天）
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

        # 验证密钥强度
        if len(secret_key) < 32:
            logger.warning("JWT密钥长度建议至少32位以确保安全性")

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        创建访问令牌

        Args:
            data: 要编码的数据
            expires_delta: 自定义过期时间

        Returns:
            JWT访问令牌
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.access_token_expire_minutes
            )

        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access",
            "jti": SecurityUtils.generate_secure_token(16)  # JWT ID
        })

        try:
            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.algorithm
            )
            logger.debug(f"创建访问令牌成功，用户ID: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"创建访问令牌失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="令牌创建失败"
            )

    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        创建刷新令牌

        Args:
            data: 要编码的数据
            expires_delta: 自定义过期时间

        Returns:
            JWT刷新令牌
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                days=self.refresh_token_expire_days
            )

        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
            "jti": SecurityUtils.generate_secure_token(16)
        })

        try:
            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.algorithm
            )
            logger.debug(f"创建刷新令牌成功，用户ID: {data.get('sub')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"创建刷新令牌失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="刷新令牌创建失败"
            )

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        验证JWT令牌

        Args:
            token: JWT令牌
            token_type: 令牌类型 (access/refresh)

        Returns:
            解码后的令牌数据

        Raises:
            HTTPException: 令牌无效或过期
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            # 检查令牌类型
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"令牌类型不匹配，期望: {token_type}"
                )

            # 检查令牌是否过期
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="令牌已过期"
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已过期"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"无效令牌: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效令牌"
            )
        except Exception as e:
            logger.error(f"令牌验证失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="令牌验证失败"
            )

    def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        使用刷新令牌生成新的访问令牌

        Args:
            refresh_token: 刷新令牌

        Returns:
            包含新访问令牌的字典

        Raises:
            HTTPException: 刷新令牌无效
        """
        try:
            # 验证刷新令牌
            payload = self.verify_token(refresh_token, "refresh")

            # 提取用户信息
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="令牌中缺少用户信息"
                )

            # 创建新的访问令牌
            access_token_data = {
                "sub": user_id,
                "email": payload.get("email"),
                "role": payload.get("role"),
                "permissions": payload.get("permissions", [])
            }

            new_access_token = self.create_access_token(access_token_data)

            logger.info(f"刷新访问令牌成功，用户ID: {user_id}")

            return {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"刷新令牌失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="令牌刷新失败"
            )

    def get_token_payload(self, token: str) -> Optional[Dict[str, Any]]:
        """
        获取令牌载荷（不验证过期时间）

        Args:
            token: JWT令牌

        Returns:
            令牌载荷或None
        """
        try:
            # 不验证过期时间，只解码
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            return payload
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            logger.error(f"获取令牌载荷失败: {e}")
            return None

    def revoke_token(self, token: str) -> bool:
        """
        撤销令牌（标记为已撤销）

        Args:
            token: 要撤销的令牌

        Returns:
            是否成功撤销
        """
        try:
            payload = self.get_token_payload(token)
            if not payload:
                return False

            jti = payload.get("jti")
            if not jti:
                return False

            # 这里应该将jti添加到黑名单中
            # 实际实现需要结合Redis或数据库存储黑名单
            logger.info(f"令牌已撤销，JTI: {jti}")
            return True

        except Exception as e:
            logger.error(f"撤销令牌失败: {e}")
            return False

    def is_token_revoked(self, token: str) -> bool:
        """
        检查令牌是否已被撤销

        Args:
            token: JWT令牌

        Returns:
            令牌是否已被撤销
        """
        try:
            payload = self.get_token_payload(token)
            if not payload:
                return True

            jti = payload.get("jti")
            if not jti:
                return True

            # 这里应该检查黑名单中是否存在该jti
            # 实际实现需要结合Redis或数据库查询黑名单
            return False

        except Exception as e:
            logger.error(f"检查令牌撤销状态失败: {e}")
            return True

    def create_token_pair(
        self,
        user_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        创建令牌对（访问令牌和刷新令牌）

        Args:
            user_data: 用户数据

        Returns:
            包含访问令牌和刷新令牌的字典
        """
        # 创建访问令牌
        access_token = self.create_access_token(user_data)

        # 创建刷新令牌
        refresh_token = self.create_refresh_token(user_data)

        logger.info(f"创建令牌对成功，用户ID: {user_data.get('sub')}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "refresh_expires_in": self.refresh_token_expire_days * 24 * 60 * 60
        }

    def extract_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        从令牌中提取用户信息

        Args:
            token: JWT令牌

        Returns:
            用户信息或None
        """
        try:
            payload = self.verify_token(token, "access")

            return {
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "role": payload.get("role"),
                "permissions": payload.get("permissions", []),
                "token_id": payload.get("jti"),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp")
            }

        except HTTPException:
            return None
        except Exception as e:
            logger.error(f"提取用户信息失败: {e}")
            return None