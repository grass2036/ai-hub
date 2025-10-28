"""
API密钥管理器

提供API密钥的生成、验证、权限管理、使用统计等功能。
"""

import secrets
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from fastapi import HTTPException, status
import logging
import asyncio
from dataclasses import dataclass, asdict

from .security import SecurityUtils

logger = logging.getLogger(__name__)


class APIKeyPermission(Enum):
    """API密钥权限枚举"""
    READ = "read"                    # 只读权限
    WRITE = "write"                  # 读写权限
    ADMIN = "admin"                  # 管理权限
    BILLING = "billing"              # 计费权限
    ANALYTICS = "analytics"          # 分析权限
    FULL_ACCESS = "full_access"      # 完全访问权限


class APIKeyStatus(Enum):
    """API密钥状态枚举"""
    ACTIVE = "active"                # 激活状态
    INACTIVE = "inactive"            # 非激活状态
    SUSPENDED = "suspended"          # 暂停状态
    EXPIRED = "expired"              # 已过期
    REVOKED = "revoked"              # 已撤销


@dataclass
class APIKeyInfo:
    """API密钥信息"""
    key_id: str                     # 密钥ID
    name: str                       # 密钥名称
    key_hash: str                   # 密钥哈希值
    user_id: str                    # 所属用户ID
    permissions: List[str]          # 权限列表
    status: str                     # 状态
    created_at: datetime            # 创建时间
    expires_at: Optional[datetime]  # 过期时间
    last_used_at: Optional[datetime]  # 最后使用时间
    usage_count: int                # 使用次数
    rate_limit: int                 # 速率限制（每小时请求数）
    monthly_quota: Optional[int]    # 月度配额
    metadata: Dict[str, Any]        # 元数据


@dataclass
class APIKeyUsage:
    """API密钥使用记录"""
    key_id: str                     # 密钥ID
    endpoint: str                   # 请求端点
    method: str                     # HTTP方法
    status_code: int                # 响应状态码
    request_time: datetime          # 请求时间
    response_time: float            # 响应时间（毫秒）
    ip_address: str                 # 客户端IP
    user_agent: str                 # 用户代理


class APIKeyManager:
    """API密钥管理器"""

    def __init__(
        self,
        storage_backend: Any = None,  # 存储后端（数据库/缓存）
        default_rate_limit: int = 1000,
        max_keys_per_user: int = 10
    ):
        """
        初始化API密钥管理器

        Args:
            storage_backend: 存储后端
            default_rate_limit: 默认速率限制
            max_keys_per_user: 每用户最大密钥数量
        """
        self.storage = storage_backend
        self.default_rate_limit = default_rate_limit
        self.max_keys_per_user = max_keys_per_user

        # 内存缓存（用于存储活跃密钥信息）
        self._cache: Dict[str, APIKeyInfo] = {}
        self._usage_cache: List[APIKeyUsage] = []

        # 定期清理过期数据的任务
        self._cleanup_task = None

    async def generate_api_key(
        self,
        user_id: str,
        name: str,
        permissions: List[str] = None,
        expires_in_days: Optional[int] = None,
        rate_limit: Optional[int] = None,
        monthly_quota: Optional[int] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        生成新的API密钥

        Args:
            user_id: 用户ID
            name: 密钥名称
            permissions: 权限列表
            expires_in_days: 过期天数
            rate_limit: 速率限制
            monthly_quota: 月度配额
            metadata: 元数据

        Returns:
            包含密钥信息的字典

        Raises:
            HTTPException: 生成失败
        """
        try:
            # 检查用户密钥数量限制
            await self._check_user_key_limit(user_id)

            # 生成密钥
            api_key = SecurityUtils.generate_api_key()
            key_id = SecurityUtils.generate_secure_token(16)

            # 计算密钥哈希
            key_hash = self._hash_api_key(api_key)

            # 设置默认值
            permissions = permissions or [APIKeyPermission.READ.value]
            rate_limit = rate_limit or self.default_rate_limit
            expires_at = None
            if expires_in_days:
                expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

            # 创建密钥信息
            key_info = APIKeyInfo(
                key_id=key_id,
                name=name,
                key_hash=key_hash,
                user_id=user_id,
                permissions=permissions,
                status=APIKeyStatus.ACTIVE.value,
                created_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                last_used_at=None,
                usage_count=0,
                rate_limit=rate_limit,
                monthly_quota=monthly_quota,
                metadata=metadata or {}
            )

            # 保存密钥信息
            await self._save_key_info(key_info)

            # 更新缓存
            self._cache[key_id] = key_info

            logger.info(f"API密钥生成成功，用户ID: {user_id}, 密钥ID: {key_id}")

            return {
                "key_id": key_id,
                "api_key": api_key,  # 只在生成时返回完整密钥
                "name": name,
                "permissions": permissions,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "rate_limit": rate_limit,
                "monthly_quota": monthly_quota,
                "created_at": key_info.created_at.isoformat()
            }

        except Exception as e:
            logger.error(f"API密钥生成失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API密钥生成失败"
            )

    async def validate_api_key(
        self,
        api_key: str,
        required_permissions: List[str] = None
    ) -> Optional[APIKeyInfo]:
        """
        验证API密钥

        Args:
            api_key: API密钥
            required_permissions: 需要的权限列表

        Returns:
            密钥信息或None

        Raises:
            HTTPException: 密钥无效或权限不足
        """
        try:
            # 计算密钥哈希
            key_hash = self._hash_api_key(api_key)

            # 查找密钥信息
            key_info = await self._find_key_by_hash(key_hash)
            if not key_info:
                logger.warning(f"无效API密钥尝试使用")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效API密钥"
                )

            # 检查密钥状态
            if not await self._is_key_valid(key_info):
                logger.warning(f"API密钥状态无效，密钥ID: {key_info.key_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"API密钥{key_info.status}"
                )

            # 检查权限
            if required_permissions:
                await self._check_permissions(key_info, required_permissions)

            # 检查速率限制
            await self._check_rate_limit(key_info)

            # 检查月度配额
            await self._check_monthly_quota(key_info)

            # 更新使用信息
            await self._update_key_usage(key_info)

            logger.debug(f"API密钥验证成功，密钥ID: {key_info.key_id}")
            return key_info

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"API密钥验证失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API密钥验证失败"
            )

    async def revoke_api_key(self, key_id: str, user_id: str = None) -> bool:
        """
        撤销API密钥

        Args:
            key_id: 密钥ID
            user_id: 操作用户ID（用于权限检查）

        Returns:
            是否成功撤销
        """
        try:
            # 获取密钥信息
            key_info = await self._get_key_info(key_id)
            if not key_info:
                logger.warning(f"尝试撤销不存在的API密钥: {key_id}")
                return False

            # 检查权限（只有密钥所有者或管理员可以撤销）
            if user_id and key_info.user_id != user_id:
                # 这里应该检查用户是否有管理员权限
                logger.warning(f"用户{user_id}尝试撤销不属于自己的API密钥: {key_id}")
                return False

            # 更新状态
            key_info.status = APIKeyStatus.REVOKED.value
            await self._save_key_info(key_info)

            # 更新缓存
            self._cache[key_id] = key_info

            logger.info(f"API密钥已撤销，密钥ID: {key_id}")
            return True

        except Exception as e:
            logger.error(f"撤销API密钥失败: {e}")
            return False

    async def list_user_api_keys(
        self,
        user_id: str,
        include_usage: bool = False
    ) -> List[Dict[str, Any]]:
        """
        列出用户的API密钥

        Args:
            user_id: 用户ID
            include_usage: 是否包含使用统计

        Returns:
            API密钥列表
        """
        try:
            # 这里应该从数据库查询用户的密钥
            # 暂时返回示例数据
            keys = []
            for key_info in self._cache.values():
                if key_info.user_id == user_id:
                    key_data = {
                        "key_id": key_info.key_id,
                        "name": key_info.name,
                        "permissions": key_info.permissions,
                        "status": key_info.status,
                        "created_at": key_info.created_at.isoformat(),
                        "expires_at": key_info.expires_at.isoformat() if key_info.expires_at else None,
                        "last_used_at": key_info.last_used_at.isoformat() if key_info.last_used_at else None,
                        "usage_count": key_info.usage_count,
                        "rate_limit": key_info.rate_limit,
                        "monthly_quota": key_info.monthly_quota
                    }

                    if include_usage:
                        # 添加使用统计
                        usage_stats = await self._get_key_usage_stats(key_info.key_id)
                        key_data.update(usage_stats)

                    keys.append(key_data)

            return keys

        except Exception as e:
            logger.error(f"获取用户API密钥列表失败: {e}")
            return []

    async def update_api_key(
        self,
        key_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        更新API密钥信息

        Args:
            key_id: 密钥ID
            user_id: 操作用户ID
            updates: 更新数据

        Returns:
            是否成功更新
        """
        try:
            # 获取密钥信息
            key_info = await self._get_key_info(key_id)
            if not key_info:
                return False

            # 检查权限
            if key_info.user_id != user_id:
                logger.warning(f"用户{user_id}尝试更新不属于自己的API密钥: {key_id}")
                return False

            # 更新允许的字段
            allowed_fields = ['name', 'permissions', 'rate_limit', 'monthly_quota', 'metadata']
            for field, value in updates.items():
                if field in allowed_fields and hasattr(key_info, field):
                    setattr(key_info, field, value)

            # 保存更新
            await self._save_key_info(key_info)
            self._cache[key_id] = key_info

            logger.info(f"API密钥更新成功，密钥ID: {key_id}")
            return True

        except Exception as e:
            logger.error(f"更新API密钥失败: {e}")
            return False

    async def get_key_usage_stats(
        self,
        key_id: str,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        获取API密钥使用统计

        Args:
            key_id: 密钥ID
            period_days: 统计周期（天数）

        Returns:
            使用统计数据
        """
        try:
            # 计算时间范围
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=period_days)

            # 这里应该从数据库查询使用记录
            # 暂时返回示例数据
            return {
                "period_days": period_days,
                "total_requests": 1250,
                "successful_requests": 1198,
                "failed_requests": 52,
                "average_response_time": 245.5,
                "most_used_endpoints": [
                    {"endpoint": "/api/v1/chat/completions", "count": 850},
                    {"endpoint": "/api/v1/models", "count": 300},
                    {"endpoint": "/api/v1/sessions", "count": 100}
                ],
                "daily_usage": [
                    {"date": "2025-10-27", "requests": 45},
                    {"date": "2025-10-26", "requests": 38},
                    {"date": "2025-10-25", "requests": 52}
                ]
            }

        except Exception as e:
            logger.error(f"获取API密钥使用统计失败: {e}")
            return {}

    # 私有方法

    def _hash_api_key(self, api_key: str) -> str:
        """计算API密钥的哈希值"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    async def _check_user_key_limit(self, user_id: str) -> None:
        """检查用户密钥数量限制"""
        user_keys = [k for k in self._cache.values() if k.user_id == user_id]
        if len(user_keys) >= self.max_keys_per_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"用户已达到最大密钥数量限制 ({self.max_keys_per_user})"
            )

    async def _save_key_info(self, key_info: APIKeyInfo) -> None:
        """保存密钥信息到存储后端"""
        # 这里应该实现实际的存储逻辑
        # 暂时只更新缓存
        self._cache[key_info.key_id] = key_info

    async def _find_key_by_hash(self, key_hash: str) -> Optional[APIKeyInfo]:
        """根据哈希值查找密钥信息"""
        # 先从缓存查找
        for key_info in self._cache.values():
            if key_info.key_hash == key_hash:
                return key_info

        # 这里应该从数据库查找
        return None

    async def _get_key_info(self, key_id: str) -> Optional[APIKeyInfo]:
        """获取密钥信息"""
        # 先从缓存查找
        if key_id in self._cache:
            return self._cache[key_id]

        # 这里应该从数据库查找
        return None

    async def _is_key_valid(self, key_info: APIKeyInfo) -> bool:
        """检查密钥是否有效"""
        # 检查状态
        if key_info.status != APIKeyStatus.ACTIVE.value:
            return False

        # 检查过期时间
        if key_info.expires_at and key_info.expires_at < datetime.now(timezone.utc):
            key_info.status = APIKeyStatus.EXPIRED.value
            await self._save_key_info(key_info)
            return False

        return True

    async def _check_permissions(
        self,
        key_info: APIKeyInfo,
        required_permissions: List[str]
    ) -> None:
        """检查密钥权限"""
        key_permissions = set(key_info.permissions)

        # 检查是否有完全访问权限
        if APIKeyPermission.FULL_ACCESS.value in key_permissions:
            return

        # 检查每个需要的权限
        for permission in required_permissions:
            if permission not in key_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"API密钥缺少权限: {permission}"
                )

    async def _check_rate_limit(self, key_info: APIKeyInfo) -> None:
        """检查速率限制"""
        # 这里应该实现实际的速率限制检查
        # 可以使用Redis等存储来跟踪请求计数
        pass

    async def _check_monthly_quota(self, key_info: APIKeyInfo) -> None:
        """检查月度配额"""
        if not key_info.monthly_quota:
            return

        # 这里应该实现实际的月度配额检查
        # 需要查询当月的使用量
        pass

    async def _update_key_usage(self, key_info: APIKeyInfo) -> None:
        """更新密钥使用信息"""
        key_info.last_used_at = datetime.now(timezone.utc)
        key_info.usage_count += 1
        await self._save_key_info(key_info)

    async def _get_key_usage_stats(self, key_id: str) -> Dict[str, Any]:
        """获取密钥使用统计"""
        # 这里应该实现实际的统计查询
        return {}

    async def start_cleanup_task(self) -> None:
        """启动定期清理任务"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_data())

    async def _cleanup_expired_data(self) -> None:
        """清理过期数据"""
        while True:
            try:
                await asyncio.sleep(3600)  # 每小时清理一次

                # 清理过期的使用记录
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)
                self._usage_cache = [
                    usage for usage in self._usage_cache
                    if usage.request_time > cutoff_time
                ]

                # 清理过期的密钥
                for key_info in self._cache.values():
                    if (key_info.expires_at and
                        key_info.expires_at < datetime.now(timezone.utc) and
                        key_info.status == APIKeyStatus.ACTIVE.value):
                        key_info.status = APIKeyStatus.EXPIRED.value
                        await self._save_key_info(key_info)

            except Exception as e:
                logger.error(f"清理过期数据失败: {e}")

    async def shutdown(self) -> None:
        """关闭管理器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass