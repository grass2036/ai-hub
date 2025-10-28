"""
配额管理器

提供API调用配额控制、使用限制、违规处理等功能。
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class QuotaType(Enum):
    """配额类型"""
    API_CALLS = "api_calls"
    TOKENS = "tokens"
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_HOUR = "requests_per_hour"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"


class QuotaStatus(Enum):
    """配额状态"""
    OK = "ok"                    # 正常
    WARNING = "warning"          # 接近限制
    EXCEEDED = "exceeded"        # 已超出
    BLOCKED = "blocked"          # 已被阻止


class QuotaAction(Enum):
    """配额违规处理动作"""
    ALLOW = "allow"              # 允许
    WARN = "warn"                # 警告
    THROTTLE = "throttle"        # 限流
    BLOCK = "block"              # 阻止
    CHARGE = "charge"            # 按量收费


@dataclass
class QuotaLimit:
    """配额限制"""
    user_id: str
    quota_type: QuotaType
    limit: int
    period: timedelta
    current_usage: int = 0
    period_start: datetime = None
    last_updated: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.period_start is None:
            self.period_start = datetime.now(timezone.utc)
        if self.last_updated is None:
            self.last_updated = datetime.now(timezone.utc)
        if self.metadata is None:
            self.metadata = {}

    @property
    def usage_percentage(self) -> float:
        """使用百分比"""
        if self.limit == 0:
            return 0.0
        return (self.current_usage / self.limit) * 100

    @property
    def remaining(self) -> int:
        """剩余配额"""
        return max(0, self.limit - self.current_usage)

    @property
    def is_expired(self) -> bool:
        """检查配额周期是否已过期"""
        return datetime.now(timezone.utc) > (self.period_start + self.period)

    @property
    def status(self) -> QuotaStatus:
        """配额状态"""
        usage_pct = self.usage_percentage

        if usage_pct >= 100:
            return QuotaStatus.EXCEEDED
        elif usage_pct >= 80:
            return QuotaStatus.WARNING
        else:
            return QuotaStatus.OK

    def reset_period(self) -> None:
        """重置配额周期"""
        self.period_start = datetime.now(timezone.utc)
        self.current_usage = 0
        self.last_updated = datetime.now(timezone.utc)


@dataclass
class QuotaViolation:
    """配额违规记录"""
    id: str
    user_id: str
    quota_type: QuotaType
    violation_time: datetime
    current_usage: int
    limit: int
    action_taken: QuotaAction
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class QuotaManager:
    """配额管理器"""

    def __init__(self, storage_backend=None):
        """
        初始化配额管理器

        Args:
            storage_backend: 存储后端（数据库/缓存）
        """
        self.storage = storage_backend

        # 内存缓存
        self._quota_cache: Dict[str, QuotaLimit] = {}
        self._violation_cache: List[QuotaViolation] = []

        # 配额配置
        self.default_limits = {
            QuotaType.API_CALLS: {
                "free": 100,           # 免费用户每月100次
                "pro": 5000,           # 专业用户每月5000次
                "enterprise": None     # 企业用户无限制
            },
            QuotaType.REQUESTS_PER_MINUTE: {
                "free": 10,            # 免费用户每分钟10次
                "pro": 60,             # 专业用户每分钟60次
                "enterprise": 200      # 企业用户每分钟200次
            },
            QuotaType.REQUESTS_PER_HOUR: {
                "free": 100,           # 免费用户每小时100次
                "pro": 1000,           # 专业用户每小时1000次
                "enterprise": 5000     # 企业用户每小时5000次
            }
        }

        # 违规处理策略
        self.violation_actions = {
            QuotaStatus.OK: QuotaAction.ALLOW,
            QuotaStatus.WARNING: QuotaAction.WARN,
            QuotaStatus.EXCEEDED: QuotaAction.THROTTLE,
            QuotaStatus.BLOCKED: QuotaAction.BLOCK
        }

        # 预警阈值配置
        self.warning_thresholds = {
            QuotaType.API_CALLS: 0.8,      # 80%时预警
            QuotaType.REQUESTS_PER_MINUTE: 0.9,  # 90%时预警
            QuotaType.REQUESTS_PER_HOUR: 0.85    # 85%时预警
        }

        # 后台任务
        self._background_task = None
        self._running = False

    async def start(self) -> None:
        """启动配额管理器"""
        if not self._running:
            self._running = True
            self._background_task = asyncio.create_task(self._background_cleanup())
            logger.info("配额管理器已启动")

    async def stop(self) -> None:
        """停止配额管理器"""
        self._running = False
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        logger.info("配额管理器已停止")

    async def check_quota(
        self,
        user_id: str,
        quota_type: QuotaType,
        user_plan: str = "free",
        amount: int = 1
    ) -> Tuple[QuotaStatus, QuotaAction]:
        """
        检查配额

        Args:
            user_id: 用户ID
            quota_type: 配额类型
            user_plan: 用户计划
            amount: 请求数量

        Returns:
            (配额状态, 处理动作)
        """
        try:
            # 获取配额限制
            quota_limit = await self._get_quota_limit(user_id, quota_type, user_plan)

            # 检查配额周期是否过期，如果过期则重置
            if quota_limit.is_expired:
                quota_limit.reset_period()
                await self._save_quota_limit(quota_limit)

            # 计算使用后是否超出限制
            projected_usage = quota_limit.current_usage + amount
            will_exceed = projected_usage > quota_limit.limit if quota_limit.limit else False

            if will_exceed:
                # 检查是否允许按量付费
                can_charge = await self._check_pay_as_you_go(user_id, user_plan)
                if can_charge:
                    return QuotaStatus.OK, QuotaAction.CHARGE
                else:
                    return QuotaStatus.EXCEEDED, self.violation_actions[QuotaStatus.EXCEEDED]
            else:
                # 更新使用量
                quota_limit.current_usage = projected_usage
                quota_limit.last_updated = datetime.now(timezone.utc)
                await self._save_quota_limit(quota_limit)

                # 检查是否需要预警
                if quota_limit.usage_percentage >= self.warning_thresholds.get(quota_type, 0.8):
                    return QuotaStatus.WARNING, QuotaAction.WARN
                else:
                    return QuotaStatus.OK, QuotaAction.ALLOW

        except Exception as e:
            logger.error(f"检查配额失败: {e}")
            # 出错时保守处理，允许请求但记录错误
            return QuotaStatus.OK, QuotaAction.ALLOW

    async def consume_quota(
        self,
        user_id: str,
        quota_type: QuotaType,
        amount: int = 1
    ) -> bool:
        """
        消费配额

        Args:
            user_id: 用户ID
            quota_type: 配额类型
            amount: 消费数量

        Returns:
            是否成功消费
        """
        try:
            quota_limit = await self._get_quota_limit(user_id, quota_type)

            if quota_limit.is_expired:
                quota_limit.reset_period()
                await self._save_quota_limit(quota_limit)

            if quota_limit.remaining >= amount:
                quota_limit.current_usage += amount
                quota_limit.last_updated = datetime.now(timezone.utc)
                await self._save_quota_limit(quota_limit)
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"消费配额失败: {e}")
            return False

    async def get_quota_status(
        self,
        user_id: str,
        quota_type: Optional[QuotaType] = None
    ) -> Dict[str, Any]:
        """
        获取配额状态

        Args:
            user_id: 用户ID
            quota_type: 配额类型（可选）

        Returns:
            配额状态信息
        """
        try:
            if quota_type:
                quota_limit = await self._get_quota_limit(user_id, quota_type)
                return {
                    quota_type.value: {
                        "limit": quota_limit.limit,
                        "current_usage": quota_limit.current_usage,
                        "remaining": quota_limit.remaining,
                        "usage_percentage": quota_limit.usage_percentage,
                        "status": quota_limit.status.value,
                        "period_start": quota_limit.period_start.isoformat(),
                        "period_end": (quota_limit.period_start + quota_limit.period).isoformat()
                    }
                }
            else:
                # 返回所有配额类型的状态
                all_status = {}
                for q_type in QuotaType:
                    quota_limit = await self._get_quota_limit(user_id, q_type)
                    all_status[q_type.value] = {
                        "limit": quota_limit.limit,
                        "current_usage": quota_limit.current_usage,
                        "remaining": quota_limit.remaining,
                        "usage_percentage": quota_limit.usage_percentage,
                        "status": quota_limit.status.value,
                        "period_start": quota_limit.period_start.isoformat(),
                        "period_end": (quota_limit.period_start + quota_limit.period).isoformat()
                    }
                return all_status

        except Exception as e:
            logger.error(f"获取配额状态失败: {e}")
            return {}

    async def set_quota_limit(
        self,
        user_id: str,
        quota_type: QuotaType,
        limit: int,
        period: timedelta
    ) -> bool:
        """
        设置配额限制

        Args:
            user_id: 用户ID
            quota_type: 配额类型
            limit: 限制数量
            period: 周期

        Returns:
            是否成功设置
        """
        try:
            cache_key = f"{user_id}_{quota_type.value}"

            quota_limit = QuotaLimit(
                user_id=user_id,
                quota_type=quota_type,
                limit=limit,
                period=period
            )

            await self._save_quota_limit(quota_limit)
            self._quota_cache[cache_key] = quota_limit

            logger.info(f"设置配额限制成功: {user_id} {quota_type.value} = {limit}")
            return True

        except Exception as e:
            logger.error(f"设置配额限制失败: {e}")
            return False

    async def reset_quota(
        self,
        user_id: str,
        quota_type: Optional[QuotaType] = None
    ) -> bool:
        """
        重置配额

        Args:
            user_id: 用户ID
            quota_type: 配额类型（可选，None表示重置所有）

        Returns:
            是否成功重置
        """
        try:
            if quota_type:
                cache_key = f"{user_id}_{quota_type.value}"
                if cache_key in self._quota_cache:
                    self._quota_cache[cache_key].reset_period()
                    await self._save_quota_limit(self._quota_cache[cache_key])
            else:
                # 重置所有配额
                for key, quota_limit in self._quota_cache.items():
                    if key.startswith(user_id + "_"):
                        quota_limit.reset_period()
                        await self._save_quota_limit(quota_limit)

            logger.info(f"重置配额成功: {user_id}")
            return True

        except Exception as e:
            logger.error(f"重置配额失败: {e}")
            return False

    async def get_quota_violations(
        self,
        user_id: str,
        days: int = 30
    ) -> List[QuotaViolation]:
        """
        获取配额违规记录

        Args:
            user_id: 用户ID
            days: 查询天数

        Returns:
            违规记录列表
        """
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)

            # 从缓存中筛选
            violations = [
                v for v in self._violation_cache
                if v.user_id == user_id and start_date <= v.violation_time <= end_date
            ]

            return violations

        except Exception as e:
            logger.error(f"获取配额违规记录失败: {e}")
            return []

    # 私有方法

    async def _get_quota_limit(
        self,
        user_id: str,
        quota_type: QuotaType,
        user_plan: str = "free"
    ) -> QuotaLimit:
        """获取配额限制"""
        cache_key = f"{user_id}_{quota_type.value}"

        # 先从缓存查找
        if cache_key in self._quota_cache:
            return self._quota_cache[cache_key]

        # 从数据库查找
        quota_limit = await self._load_quota_limit(user_id, quota_type)
        if not quota_limit:
            # 创建默认配额限制
            default_limit = self.default_limits.get(quota_type, {}).get(user_plan, 0)
            period = self._get_default_period(quota_type)

            quota_limit = QuotaLimit(
                user_id=user_id,
                quota_type=quota_type,
                limit=default_limit,
                period=period
            )

            # 保存到数据库
            await self._save_quota_limit(quota_limit)

        # 更新缓存
        self._quota_cache[cache_key] = quota_limit
        return quota_limit

    def _get_default_period(self, quota_type: QuotaType) -> timedelta:
        """获取默认周期"""
        period_mapping = {
            QuotaType.API_CALLS: timedelta(days=30),
            QuotaType.REQUESTS_PER_MINUTE: timedelta(minutes=1),
            QuotaType.REQUESTS_PER_HOUR: timedelta(hours=1),
            QuotaType.TOKENS: timedelta(days=30),
            QuotaType.STORAGE: timedelta(days=30),
            QuotaType.BANDWIDTH: timedelta(days=30)
        }
        return period_mapping.get(quota_type, timedelta(days=30))

    async def _check_pay_as_you_go(self, user_id: str, user_plan: str) -> bool:
        """检查是否支持按量付费"""
        # 只有企业用户支持按量付费
        return user_plan == "enterprise"

    async def _save_quota_limit(self, quota_limit: QuotaLimit) -> None:
        """保存配额限制到数据库"""
        # TODO: 实现数据库保存
        pass

    async def _load_quota_limit(
        self,
        user_id: str,
        quota_type: QuotaType
    ) -> Optional[QuotaLimit]:
        """从数据库加载配额限制"""
        # TODO: 实现数据库查询
        return None

    async def _record_violation(self, violation: QuotaViolation) -> None:
        """记录配额违规"""
        self._violation_cache.append(violation)
        # TODO: 保存到数据库

    async def _background_cleanup(self) -> None:
        """后台清理任务"""
        while self._running:
            try:
                await asyncio.sleep(300)  # 5分钟清理一次
                await self._cleanup_expired_quotas()
                await self._cleanup_old_violations()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"后台清理任务失败: {e}")

    async def _cleanup_expired_quotas(self) -> None:
        """清理过期的配额限制"""
        now = datetime.now(timezone.utc)
        expired_keys = []

        for key, quota_limit in self._quota_cache.items():
            if quota_limit.is_expired:
                expired_keys.append(key)

        for key in expired_keys:
            del self._quota_cache[key]

        if expired_keys:
            logger.debug(f"清理了 {len(expired_keys)} 个过期配额限制")

    async def _cleanup_old_violations(self) -> None:
        """清理旧的违规记录"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        original_count = len(self._violation_cache)

        self._violation_cache = [
            v for v in self._violation_cache
            if v.violation_time > cutoff_date
        ]

        cleaned_count = original_count - len(self._violation_cache)
        if cleaned_count > 0:
            logger.debug(f"清理了 {cleaned_count} 个旧的违规记录")