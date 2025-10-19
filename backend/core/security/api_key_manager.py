"""
API密钥管理器
Week 6 Day 4: 安全加固和权限配置

提供安全的API密钥生成、验证、使用追踪和管理功能
"""

import asyncio
import secrets
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import redis
import logging
from fastapi import HTTPException, Request, Depends
from fastapi.security import APIKeyHeader

class APIKeyStatus(Enum):
    """API密钥状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"

class APIKeyType(Enum):
    """API密钥类型"""
    PERSONAL = "personal"           # 个人密钥
    SERVICE = "service"            # 服务密钥
    ORGANIZATION = "organization" # 组织密钥
    TEMPORARY = "temporary"        # 临时密钥

@dataclass
class APIKey:
    """API密钥数据模型"""
    id: str
    name: str
    key_hash: str
    key_prefix: str
    key_type: APIKeyType
    user_id: str
    organization_id: Optional[str] = None
    permissions: List[str] = None
    rate_limit: Optional[int] = None
    daily_quota: Optional[int] = None
    allowed_ips: List[str] = None
    allowed_referers: List[str] = None
    status: APIKeyStatus = APIKeyStatus.ACTIVE
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    created_at: datetime = None
    updated_at: datetime = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（不包含敏感信息）"""
        return {
            "id": self.id,
            "name": self.name,
            "key_prefix": self.key_prefix,
            "key_type": self.key_type.value,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "permissions": self.permissions or [],
            "rate_limit": self.rate_limit,
            "daily_quota": self.daily_quota,
            "allowed_ips": self.allowed_ips or [],
            "allowed_referers": self.allowed_referers or [],
            "status": self.status.value,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata or {}
        }

@dataclass
class APIKeyUsage:
    """API密钥使用记录"""
    api_key_id: str
    timestamp: datetime
    endpoint: str
    method: str
    ip_address: str
    user_agent: str
    status_code: int
    response_time_ms: float
    request_size: int
    response_size: int

class APIKeyUsageTracker:
    """API密钥使用追踪器"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client

    async def record_usage(self, usage: APIKeyUsage) -> None:
        """记录API密钥使用"""
        if not self.redis_client:
            return

        # 存储使用记录
        usage_key = f"api_key_usage:{usage.api_key_id}:{int(usage.timestamp.timestamp())}"
        await self.redis_client.hset(usage_key, mapping={
            "endpoint": usage.endpoint,
            "method": usage.method,
            "ip_address": usage.ip_address,
            "user_agent": usage.user_agent,
            "status_code": usage.status_code,
            "response_time_ms": usage.response_time_ms,
            "request_size": usage.request_size,
            "response_size": usage.response_size
        })

        # 设置过期时间（保留30天）
        await self.redis_client.expire(usage_key, 30 * 24 * 3600)

        # 更新统计信息
        await self._update_usage_stats(usage)

    async def _update_usage_stats(self, usage: APIKeyUsage) -> None:
        """更新使用统计"""
        if not self.redis_client:
            return

        today = usage.timestamp.strftime("%Y-%m-%d")
        hour = usage.timestamp.strftime("%Y-%m-%d %H:00:00")

        # 每日统计
        daily_key = f"api_key_stats:daily:{usage.api_key_id}:{today}"
        await self.redis_client.hincrby(daily_key, "total_requests", 1)
        await self.redis_client.hincrbyfloat(daily_key, "total_response_time", usage.response_time_ms)
        await self.redis_client.hincrby(daily_key, "total_request_size", usage.request_size)
        await self.redis_client.hincrby(daily_key, "total_response_size", usage.response_size)

        if usage.status_code >= 400:
            await self.redis_client.hincrby(daily_key, "error_count", 1)

        # 每小时统计
        hourly_key = f"api_key_stats:hourly:{usage.api_key_id}:{hour}"
        await self.redis_client.hincrby(hourly_key, "requests", 1)
        await self.redis_client.expire(hourly_key, 7 * 24 * 3600)  # 保留7天

        # 设置过期时间
        await self.redis_client.expire(daily_key, 90 * 24 * 3600)  # 保留90天

    async def get_usage_stats(
        self,
        api_key_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """获取使用统计"""
        if not self.redis_client:
            return {}

        stats = {
            "total_requests": 0,
            "total_response_time": 0.0,
            "total_request_size": 0,
            "total_response_size": 0,
            "error_count": 0,
            "daily_stats": {}
        }

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            daily_key = f"api_key_stats:daily:{api_key_id}:{date_str}"
            daily_data = await self.redis_client.hgetall(daily_key)

            if daily_data:
                day_stats = {
                    "total_requests": int(daily_data.get("total_requests", 0)),
                    "total_response_time": float(daily_data.get("total_response_time", 0)),
                    "total_request_size": int(daily_data.get("total_request_size", 0)),
                    "total_response_size": int(daily_data.get("total_response_size", 0)),
                    "error_count": int(daily_data.get("error_count", 0))
                }

                # 累计统计
                stats["total_requests"] += day_stats["total_requests"]
                stats["total_response_time"] += day_stats["total_response_time"]
                stats["total_request_size"] += day_stats["total_request_size"]
                stats["total_response_size"] += day_stats["total_response_size"]
                stats["error_count"] += day_stats["error_count"]

                # 计算平均响应时间
                if day_stats["total_requests"] > 0:
                    day_stats["avg_response_time"] = day_stats["total_response_time"] / day_stats["total_requests"]
                    day_stats["error_rate"] = day_stats["error_count"] / day_stats["total_requests"]
                else:
                    day_stats["avg_response_time"] = 0
                    day_stats["error_rate"] = 0

                stats["daily_stats"][date_str] = day_stats

            current_date += timedelta(days=1)

        # 计算总体统计
        if stats["total_requests"] > 0:
            stats["avg_response_time"] = stats["total_response_time"] / stats["total_requests"]
            stats["error_rate"] = stats["error_count"] / stats["total_requests"]
        else:
            stats["avg_response_time"] = 0
            stats["error_rate"] = 0

        return stats

class APIKeyManager:
    """API密钥管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.usage_tracker: Optional[APIKeyUsageTracker] = None
        self.key_length = config.get('key_length', 32)
        self.key_prefix_length = config.get('key_prefix_length', 8)

    async def initialize(self, redis_client: Optional[redis.Redis] = None) -> None:
        """初始化API密钥管理器"""
        self.redis_client = redis_client
        self.usage_tracker = APIKeyUsageTracker(redis_client)

    def _generate_api_key(self) -> Tuple[str, str, str]:
        """生成API密钥"""
        # 生成随机密钥
        random_bytes = secrets.token_bytes(self.key_length)
        api_key = secrets.token_urlsafe(self.key_length)

        # 生成前缀（用于识别）
        key_prefix = api_key[:self.key_prefix_length]

        # 生成哈希值（用于存储和验证）
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        return api_key, key_hash, key_prefix

    async def create_api_key(
        self,
        name: str,
        user_id: str,
        key_type: APIKeyType = APIKeyType.PERSONAL,
        organization_id: Optional[str] = None,
        permissions: List[str] = None,
        rate_limit: Optional[int] = None,
        daily_quota: Optional[int] = None,
        allowed_ips: List[str] = None,
        allowed_referers: List[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Dict[str, Any] = None
    ) -> Tuple[str, APIKey]:
        """创建API密钥"""
        # 生成API密钥
        api_key, key_hash, key_prefix = self._generate_api_key()

        # 创建API密钥对象
        api_key_obj = APIKey(
            id=str(uuid.uuid4()),
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            key_type=key_type,
            user_id=user_id,
            organization_id=organization_id,
            permissions=permissions or [],
            rate_limit=rate_limit,
            daily_quota=daily_quota,
            allowed_ips=allowed_ips or [],
            allowed_referers=allowed_referers or [],
            status=APIKeyStatus.ACTIVE,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata=metadata or {}
        )

        # 存储到Redis
        if self.redis_client:
            await self._store_api_key(api_key_obj)

        return api_key, api_key_obj

    async def validate_api_key(
        self,
        api_key: str,
        ip_address: Optional[str] = None,
        referer: Optional[str] = None
    ) -> Optional[APIKey]:
        """验证API密钥"""
        if not self.redis_client:
            return None

        # 生成哈希值
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_prefix = api_key[:self.key_prefix_length]

        # 查找API密钥
        api_key_data = await self._get_api_key_by_hash(key_hash, key_prefix)
        if not api_key_data:
            return None

        # 转换为APIKey对象
        api_key_obj = APIKey(**api_key_data)

        # 检查状态
        if api_key_obj.status != APIKeyStatus.ACTIVE:
            return None

        # 检查过期时间
        if api_key_obj.expires_at and datetime.utcnow() > api_key_obj.expires_at:
            return None

        # 检查IP限制
        if api_key_obj.allowed_ips and ip_address:
            if ip_address not in api_key_obj.allowed_ips:
                return None

        # 检查Referer限制
        if api_key_obj.allowed_referers and referer:
            if not any(referer.startswith(allowed_ref) for allowed_ref in api_key_obj.allowed_referers):
                return None

        # 更新最后使用时间
        await self._update_last_used(api_key_obj.id)

        return api_key_obj

    async def revoke_api_key(self, api_key_id: str, user_id: str) -> bool:
        """撤销API密钥"""
        if not self.redis_client:
            return False

        # 获取API密钥
        api_key_data = await self._get_api_key_by_id(api_key_id)
        if not api_key_data:
            return False

        # 检查权限
        if api_key_data['user_id'] != user_id:
            return False

        # 更新状态
        api_key_data['status'] = APIKeyStatus.REVOKED.value
        api_key_data['updated_at'] = datetime.utcnow().isoformat()

        # 存储更新
        await self._store_api_key_data(api_key_data)

        return True

    async def update_api_key(
        self,
        api_key_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """更新API密钥"""
        if not self.redis_client:
            return False

        # 获取API密钥
        api_key_data = await self._get_api_key_by_id(api_key_id)
        if not api_key_data:
            return False

        # 检查权限
        if api_key_data['user_id'] != user_id:
            return False

        # 更新字段
        allowed_updates = [
            'name', 'permissions', 'rate_limit', 'daily_quota',
            'allowed_ips', 'allowed_referers', 'expires_at', 'metadata'
        ]

        for field, value in updates.items():
            if field in allowed_updates:
                api_key_data[field] = value

        api_key_data['updated_at'] = datetime.utcnow().isoformat()

        # 存储更新
        await self._store_api_key_data(api_key_data)

        return True

    async def get_user_api_keys(self, user_id: str) -> List[APIKey]:
        """获取用户的API密钥列表"""
        if not self.redis_client:
            return []

        # 获取用户的所有API密钥ID
        key_ids = await self.redis_client.smembers(f"user_api_keys:{user_id}")

        api_keys = []
        for key_id in key_ids:
            api_key_data = await self._get_api_key_by_id(key_id)
            if api_key_data:
                api_keys.append(APIKey(**api_key_data))

        return api_keys

    async def get_api_key_usage(
        self,
        api_key_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """获取API密钥使用统计"""
        if self.usage_tracker:
            return await self.usage_tracker.get_usage_stats(api_key_id, start_date, end_date)
        return {}

    async def _store_api_key(self, api_key: APIKey) -> None:
        """存储API密钥"""
        if not self.redis_client:
            return

        # 存储API密钥数据
        api_key_data = asdict(api_key)
        # 转换日期时间为字符串
        for field in ['created_at', 'updated_at', 'expires_at', 'last_used_at']:
            if api_key_data[field]:
                api_key_data[field] = api_key_data[field].isoformat()

        await self._store_api_key_data(api_key_data)

        # 添加到用户的API密钥集合
        await self.redis_client.sadd(f"user_api_keys:{api_key.user_id}", api_key.id)

        # 添加到前缀索引
        await self.redis_client.hset(
            f"api_key_prefix:{api_key.key_prefix}",
            api_key.id,
            api_key.key_hash
        )

    async def _store_api_key_data(self, api_key_data: Dict[str, Any]) -> None:
        """存储API密钥数据"""
        if not self.redis_client:
            return

        key = f"api_key:{api_key_data['id']}"
        await self.redis_client.hset(key, mapping={
            field: str(value) if value is not None else ""
            for field, value in api_key_data.items()
        })

        # 设置过期时间
        if api_key_data.get('expires_at'):
            expire_time = datetime.fromisoformat(api_key_data['expires_at'])
            ttl = int((expire_time - datetime.utcnow()).total_seconds())
            if ttl > 0:
                await self.redis_client.expire(key, ttl)

    async def _get_api_key_by_id(self, api_key_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取API密钥"""
        if not self.redis_client:
            return None

        data = await self.redis_client.hgetall(f"api_key:{api_key_id}")
        if not data:
            return None

        # 转换数据类型
        for field in ['created_at', 'updated_at', 'expires_at', 'last_used_at']:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])

        for field in ['rate_limit', 'daily_quota', 'usage_count']:
            if data.get(field):
                data[field] = int(data[field])

        for field in ['permissions', 'allowed_ips', 'allowed_referers']:
            if data.get(field):
                data[field] = data[field].split(',') if data[field] else []

        if data.get('metadata'):
            try:
                data['metadata'] = json.loads(data['metadata'])
            except:
                data['metadata'] = {}

        return data

    async def _get_api_key_by_hash(self, key_hash: str, key_prefix: str) -> Optional[Dict[str, Any]]:
        """根据哈希值和前缀获取API密钥"""
        if not self.redis_client:
            return None

        # 通过前缀查找可能的API密钥ID
        key_ids = await self.redis_client.hgetall(f"api_key_prefix:{key_prefix}")

        for key_id, stored_hash in key_ids.items():
            if stored_hash == key_hash:
                return await self._get_api_key_by_id(key_id)

        return None

    async def _update_last_used(self, api_key_id: str) -> None:
        """更新最后使用时间"""
        if not self.redis_client:
            return

        await self.redis_client.hset(
            f"api_key:{api_key_id}",
            "last_used_at",
            datetime.utcnow().isoformat()
        )
        await self.redis_client.hincrby(f"api_key:{api_key_id}", "usage_count", 1)

class APIKeyAuth:
    """API密钥认证"""

    def __init__(self, api_key_manager: APIKeyManager):
        self.api_key_manager = api_key_manager
        self.api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

    async def authenticate(
        self,
        request: Request,
        api_key: Optional[str] = None
    ) -> Optional[APIKey]:
        """认证API密钥"""
        # 从请求头获取API密钥
        if not api_key:
            api_key = request.headers.get("X-API-Key")

        if not api_key:
            return None

        # 获取客户端信息
        ip_address = request.client.host if request.client else None
        referer = request.headers.get("Referer")

        # 验证API密钥
        return await self.api_key_manager.validate_api_key(api_key, ip_address, referer)

# 速率限制装饰器
def rate_limit(requests_per_minute: int = 60, per_api_key: bool = True):
    """速率限制装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取请求对象
            request = None
            for arg in args:
                if hasattr(arg, 'headers'):
                    request = arg
                    break

            if not request:
                return await func(*args, **kwargs)

            # 获取标识符
            if per_api_key and hasattr(request.state, 'api_key'):
                identifier = f"api_key:{request.state.api_key.id}"
            else:
                identifier = f"ip:{request.client.host if request.client else 'unknown'}"

            # 检查速率限制
            if not await _check_rate_limit(identifier, requests_per_minute):
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator

async def _check_rate_limit(identifier: str, requests_per_minute: int) -> bool:
    """检查速率限制"""
    # 这里应该使用Redis或其他缓存系统来实现速率限制
    # 示例实现
    return True  # 简化实现

# 导入uuid
import uuid