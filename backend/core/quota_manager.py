"""
配额管理器
"""
from datetime import datetime, timedelta
from typing import Optional
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.models import User, APIKey
from backend.config.settings import get_settings

settings = get_settings()


class QuotaManager:
    """配额管理器"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None

    async def initialize(self):
        """初始化Redis连接"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )

    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()

    def _get_quota_key(self, user_id: int) -> str:
        """获取用户配额的Redis键"""
        return f"quota:user:{user_id}"

    def _get_rate_limit_key(self, api_key_id: int) -> str:
        """获取API密钥速率限制的Redis键"""
        return f"rate_limit:key:{api_key_id}"

    async def check_quota(
        self,
        db: AsyncSession,
        user_id: int
    ) -> tuple[bool, int, int]:
        """
        检查用户配额

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            (是否有配额, 已使用, 总配额)
        """
        # 先从Redis获取
        quota_key = self._get_quota_key(user_id)
        cached_used = await self.redis_client.get(quota_key)

        if cached_used is not None:
            # 从数据库获取总配额
            user = await db.get(User, user_id)
            quota_used = int(cached_used)
            has_quota = quota_used < user.monthly_quota
            return has_quota, quota_used, user.monthly_quota

        # 从数据库获取
        user = await db.get(User, user_id)
        if not user:
            return False, 0, 0

        # 缓存到Redis (1小时过期)
        await self.redis_client.setex(
            quota_key,
            3600,
            user.quota_used
        )

        has_quota = user.quota_used < user.monthly_quota
        return has_quota, user.quota_used, user.monthly_quota

    async def consume_quota(
        self,
        db: AsyncSession,
        user_id: int,
        amount: int = 1
    ) -> bool:
        """
        消费配额

        Args:
            db: 数据库会话
            user_id: 用户ID
            amount: 消费数量

        Returns:
            是否成功
        """
        # 检查配额
        has_quota, used, total = await self.check_quota(db, user_id)
        if not has_quota:
            return False

        # 增加Redis中的计数
        quota_key = self._get_quota_key(user_id)
        new_used = await self.redis_client.incrby(quota_key, amount)

        # 异步更新数据库 (每100次同步一次)
        if new_used % 100 == 0:
            await db.execute(
                update(User)
                .where(User.id == user_id)
                .values(quota_used=new_used)
            )
            await db.commit()

        return True

    async def check_rate_limit(
        self,
        api_key: APIKey
    ) -> bool:
        """
        检查速率限制

        Args:
            api_key: API密钥对象

        Returns:
            是否在限制内
        """
        if not api_key.rate_limit:
            return True  # 无限制

        rate_key = self._get_rate_limit_key(api_key.id)

        # 使用Redis的滑动窗口计数
        current = await self.redis_client.get(rate_key)

        if current is None:
            # 第一次请求
            await self.redis_client.setex(rate_key, 60, 1)
            return True

        current_count = int(current)
        if current_count >= api_key.rate_limit:
            return False

        # 增加计数
        await self.redis_client.incr(rate_key)
        return True

    async def get_usage_stats(
        self,
        db: AsyncSession,
        user_id: int
    ) -> dict:
        """
        获取用户使用统计

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            使用统计字典
        """
        user = await db.get(User, user_id)
        if not user:
            return {}

        # 获取实时配额
        has_quota, used, total = await self.check_quota(db, user_id)

        # 计算重置时间
        time_until_reset = user.quota_reset_at - datetime.utcnow()
        days_until_reset = max(0, time_until_reset.days)

        return {
            "quota_used": used,
            "quota_total": total,
            "quota_remaining": total - used,
            "quota_percentage": (used / total * 100) if total > 0 else 0,
            "quota_reset_at": user.quota_reset_at.isoformat(),
            "days_until_reset": days_until_reset,
            "plan": user.plan.value
        }

    async def reset_monthly_quota(
        self,
        db: AsyncSession,
        user_id: int
    ):
        """
        重置月度配额

        Args:
            db: 数据库会话
            user_id: 用户ID
        """
        # 更新数据库
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                quota_used=0,
                quota_reset_at=datetime.utcnow() + timedelta(days=30)
            )
        )
        await db.commit()

        # 清除Redis缓存
        quota_key = self._get_quota_key(user_id)
        await self.redis_client.delete(quota_key)


# 全局实例
quota_manager = QuotaManager()