"""
使用量跟踪器

提供API调用跟踪、使用量统计、成本计算等功能。
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
import json
import logging

logger = logging.getLogger(__name__)


class UsageType(Enum):
    """使用量类型"""
    API_CALL = "api_call"
    TOKEN_USAGE = "token_usage"
    MODEL_REQUEST = "model_request"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"


class ModelType(Enum):
    """模型类型"""
    GPT_35_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"
    CLAUDE_INSTANT = "claude-instant"
    CLAUDE_SONNET = "claude-3-sonnet"
    CLAUDE_OPUSS = "claude-3-opus"
    GEMINI_PRO = "gemini-pro"
    CUSTOM = "custom"


@dataclass
class UsageRecord:
    """使用量记录"""
    id: str
    user_id: str
    api_key_id: Optional[str]
    usage_type: UsageType
    timestamp: datetime
    endpoint: str
    method: str
    model: Optional[ModelType]
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    request_size: int = 0  # bytes
    response_size: int = 0  # bytes
    response_time_ms: int = 0
    status_code: int = 200
    error_message: Optional[str] = None
    cost: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "api_key_id": self.api_key_id,
            "usage_type": self.usage_type.value,
            "timestamp": self.timestamp.isoformat(),
            "endpoint": self.endpoint,
            "method": self.method,
            "model": self.model.value if self.model else None,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "request_size": self.request_size,
            "response_size": self.response_size,
            "response_time_ms": self.response_time_ms,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "cost": self.cost,
            "metadata": self.metadata
        }


@dataclass
class UsageStats:
    """使用量统计"""
    user_id: str
    period_start: datetime
    period_end: datetime
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0
    model_usage: Dict[str, Dict[str, Any]] = None
    endpoint_usage: Dict[str, int] = None
    hourly_usage: Dict[str, int] = None
    average_response_time: float = 0.0
    p95_response_time: float = 0.0
    error_rate: float = 0.0

    def __post_init__(self):
        if self.model_usage is None:
            self.model_usage = {}
        if self.endpoint_usage is None:
            self.endpoint_usage = {}
        if self.hourly_usage is None:
            self.hourly_usage = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "total_tokens": self.total_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_cost": self.total_cost,
            "model_usage": self.model_usage,
            "endpoint_usage": self.endpoint_usage,
            "hourly_usage": self.hourly_usage,
            "average_response_time": self.average_response_time,
            "p95_response_time": self.p95_response_time,
            "error_rate": self.error_rate
        }


class UsageTracker:
    """使用量跟踪器"""

    def __init__(self, storage_backend=None):
        """
        初始化使用量跟踪器

        Args:
            storage_backend: 存储后端（数据库/缓存）
        """
        self.storage = storage_backend

        # 模型定价配置
        self.model_pricing = {
            ModelType.GPT_35_TURBO: {
                "input_cost_per_token": 0.0000015,  # $0.0015 per 1K tokens
                "output_cost_per_token": 0.000002,   # $0.002 per 1K tokens
                "currency": "USD"
            },
            ModelType.GPT_4: {
                "input_cost_per_token": 0.00003,     # $0.03 per 1K tokens
                "output_cost_per_token": 0.00006,    # $0.06 per 1K tokens
                "currency": "USD"
            },
            ModelType.CLAUDE_INSTANT: {
                "input_cost_per_token": 0.0000008,   # $0.0008 per 1K tokens
                "output_cost_per_token": 0.0000024,  # $0.0024 per 1K tokens
                "currency": "USD"
            },
            ModelType.CLAUDE_SONNET: {
                "input_cost_per_token": 0.000003,    # $0.003 per 1K tokens
                "output_cost_per_token": 0.000015,   # $0.015 per 1K tokens
                "currency": "USD"
            },
            ModelType.CLAUDE_OPUSS: {
                "input_cost_per_token": 0.000015,    # $0.015 per 1K tokens
                "output_cost_per_token": 0.000075,   # $0.075 per 1K tokens
                "currency": "USD"
            },
            ModelType.GEMINI_PRO: {
                "input_cost_per_token": 0.0000005,   # $0.0005 per 1K tokens
                "output_cost_per_token": 0.0000015,  # $0.0015 per 1K tokens
                "currency": "USD"
            }
        }

        # 内存缓存（用于临时存储）
        self._usage_cache: List[UsageRecord] = []
        self._stats_cache: Dict[str, UsageStats] = {}

        # 批量处理配置
        self.batch_size = 100
        self.flush_interval = 60  # 秒

        # 启动后台任务
        self._background_task = None
        self._running = False

    async def start(self) -> None:
        """启动使用量跟踪器"""
        if not self._running:
            self._running = True
            self._background_task = asyncio.create_task(self._background_flush())
            logger.info("使用量跟踪器已启动")

    async def stop(self) -> None:
        """停止使用量跟踪器"""
        self._running = False
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        # 刷新剩余缓存
        await self._flush_cache()
        logger.info("使用量跟踪器已停止")

    async def track_usage(
        self,
        user_id: str,
        api_key_id: Optional[str],
        usage_type: UsageType,
        endpoint: str,
        method: str,
        model: Optional[ModelType] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        request_size: int = 0,
        response_size: int = 0,
        response_time_ms: int = 0,
        status_code: int = 200,
        error_message: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        跟踪使用量

        Args:
            user_id: 用户ID
            api_key_id: API密钥ID
            usage_type: 使用量类型
            endpoint: API端点
            method: HTTP方法
            model: AI模型
            input_tokens: 输入token数量
            output_tokens: 输出token数量
            request_size: 请求大小（字节）
            response_size: 响应大小（字节）
            response_time_ms: 响应时间（毫秒）
            status_code: HTTP状态码
            error_message: 错误消息
            metadata: 元数据

        Returns:
            使用记录ID
        """
        try:
            # 计算总token数
            total_tokens = input_tokens + output_tokens

            # 计算成本
            cost = self._calculate_cost(model, input_tokens, output_tokens)

            # 创建使用记录
            usage_record = UsageRecord(
                id=self._generate_usage_id(),
                user_id=user_id,
                api_key_id=api_key_id,
                usage_type=usage_type,
                timestamp=datetime.now(timezone.utc),
                endpoint=endpoint,
                method=method,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                request_size=request_size,
                response_size=response_size,
                response_time_ms=response_time_ms,
                status_code=status_code,
                error_message=error_message,
                cost=cost,
                metadata=metadata or {}
            )

            # 添加到缓存
            self._usage_cache.append(usage_record)

            # 更新统计缓存
            await self._update_stats_cache(usage_record)

            # 如果缓存满了，立即刷新
            if len(self._usage_cache) >= self.batch_size:
                await self._flush_cache()

            return usage_record.id

        except Exception as e:
            logger.error(f"跟踪使用量失败: {e}")
            raise

    async def get_usage_stats(
        self,
        user_id: str,
        period_start: datetime,
        period_end: datetime,
        usage_type: Optional[UsageType] = None
    ) -> UsageStats:
        """
        获取使用量统计

        Args:
            user_id: 用户ID
            period_start: 开始时间
            period_end: 结束时间
            usage_type: 使用量类型过滤

        Returns:
            使用量统计
        """
        cache_key = f"{user_id}_{period_start.strftime('%Y%m%d')}_{period_end.strftime('%Y%m%d')}"

        # 先从缓存查找
        if cache_key in self._stats_cache:
            cached_stats = self._stats_cache[cache_key]
            # 检查时间范围是否匹配
            if (cached_stats.period_start <= period_start and
                cached_stats.period_end >= period_end):
                return cached_stats

        # 从数据库查询
        stats = await self._query_usage_stats(
            user_id, period_start, period_end, usage_type
        )

        # 更新缓存
        self._stats_cache[cache_key] = stats

        return stats

    async def get_user_monthly_usage(
        self,
        user_id: str,
        year: int,
        month: int
    ) -> UsageStats:
        """
        获取用户月度使用量

        Args:
            user_id: 用户ID
            year: 年份
            month: 月份

        Returns:
            月度使用量统计
        """
        period_start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            period_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            period_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        return await self.get_usage_stats(user_id, period_start, period_end)

    async def get_usage_trends(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取使用量趋势

        Args:
            user_id: 用户ID
            days: 天数

        Returns:
            使用量趋势数据
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # 查询每日使用量
        daily_usage = await self._query_daily_usage(user_id, start_date, end_date)

        # 计算趋势
        total_requests = sum(day.get("total_requests", 0) for day in daily_usage)
        total_cost = sum(day.get("total_cost", 0.0) for day in daily_usage)
        avg_daily_requests = total_requests / days if days > 0 else 0
        avg_daily_cost = total_cost / days if days > 0 else 0

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "summary": {
                "total_requests": total_requests,
                "total_cost": total_cost,
                "avg_daily_requests": avg_daily_requests,
                "avg_daily_cost": avg_daily_cost
            },
            "daily_usage": daily_usage,
            "trends": {
                "requests_trend": self._calculate_trend([day.get("total_requests", 0) for day in daily_usage]),
                "cost_trend": self._calculate_trend([day.get("total_cost", 0.0) for day in daily_usage])
            }
        }

    def _calculate_cost(
        self,
        model: Optional[ModelType],
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        计算使用成本

        Args:
            model: AI模型
            input_tokens: 输入token数量
            output_tokens: 输出token数量

        Returns:
            成本
        """
        if not model or model not in self.model_pricing:
            return 0.0

        pricing = self.model_pricing[model]

        # 计算输入成本（每1000个token的价格）
        input_cost = (input_tokens / 1000.0) * pricing["input_cost_per_token"]

        # 计算输出成本（每1000个token的价格）
        output_cost = (output_tokens / 1000.0) * pricing["output_cost_per_token"]

        total_cost = input_cost + output_cost

        return round(total_cost, 6)  # 保留6位小数

    def _generate_usage_id(self) -> str:
        """生成使用记录ID"""
        import uuid
        return f"usage_{uuid.uuid4().hex[:16]}"

    async def _update_stats_cache(self, usage_record: UsageRecord) -> None:
        """更新统计缓存"""
        # 这里可以实现实时的统计更新逻辑
        # 暂时跳过实现
        pass

    async def _flush_cache(self) -> None:
        """刷新缓存到数据库"""
        if not self._usage_cache:
            return

        try:
            # 批量保存使用记录
            await self._save_usage_records(self._usage_cache)

            # 清空缓存
            self._usage_cache.clear()

            logger.debug(f"刷新使用量缓存，保存了 {len(self._usage_cache)} 条记录")

        except Exception as e:
            logger.error(f"刷新使用量缓存失败: {e}")

    async def _background_flush(self) -> None:
        """后台定期刷新任务"""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"后台刷新任务失败: {e}")

    # 数据库操作方法（需要根据实际存储后端实现）

    async def _save_usage_records(self, records: List[UsageRecord]) -> None:
        """保存使用记录到数据库"""
        # TODO: 实现数据库批量插入
        for record in records:
            await self._save_usage_record(record)

    async def _save_usage_record(self, record: UsageRecord) -> None:
        """保存单个使用记录到数据库"""
        # TODO: 实现数据库插入
        pass

    async def _query_usage_stats(
        self,
        user_id: str,
        period_start: datetime,
        period_end: datetime,
        usage_type: Optional[UsageType] = None
    ) -> UsageStats:
        """查询使用量统计"""
        # TODO: 实现数据库查询
        # 返回示例数据
        return UsageStats(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            total_tokens=0,
            input_tokens=0,
            output_tokens=0,
            total_cost=0.0
        )

    async def _query_daily_usage(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """查询每日使用量"""
        # TODO: 实现数据库查询
        # 返回示例数据
        daily_usage = []
        current_date = start_date
        while current_date < end_date:
            daily_usage.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "total_requests": 0,
                "total_cost": 0.0,
                "total_tokens": 0
            })
            current_date += timedelta(days=1)
        return daily_usage

    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return "stable"

        # 简单的线性回归计算趋势
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))

        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)

        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"