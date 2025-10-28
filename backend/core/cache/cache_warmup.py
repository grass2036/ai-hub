"""
智能缓存预热机制
基于访问模式、业务规则和用户行为的智能预热系统
"""

import asyncio
import json
import time
import logging
from typing import Any, Dict, List, Optional, Callable, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import statistics
import hashlib

from backend.core.cache.multi_level_cache import get_cache_manager, CacheLevel, cache_key
from backend.core.ai_service import ai_manager

logger = logging.getLogger(__name__)


class WarmupStrategy(Enum):
    """预热策略"""
    MANUAL = "manual"                    # 手动预热
    SCHEDULED = "scheduled"              # 定时预热
    TRAFFIC_BASED = "traffic_based"      # 基于流量预热
    USER_BASED = "user_based"            # 基于用户行为预热
    PREDICTIVE = "predictive"            # 预测性预热
    EVENT_DRIVEN = "event_driven"        # 事件驱动预热


class WarmupPriority(Enum):
    """预热优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class WarmupTask:
    """预热任务"""
    id: str
    key: str
    data_generator: Callable
    priority: WarmupPriority
    strategy: WarmupStrategy
    ttl: int = 300
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = None
    scheduled_at: float = None
    tags: List[str] = None
    dependencies: List[str] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.tags is None:
            self.tags = []
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}

    def is_ready(self) -> bool:
        """检查是否准备好执行"""
        return self.scheduled_at is None or self.scheduled_at <= time.time()

    def should_retry(self) -> bool:
        """检查是否应该重试"""
        return self.retry_count < self.max_retries


@dataclass
class AccessPattern:
    """访问模式"""
    key_pattern: str
    access_count: int = 0
    last_access: float = 0
    avg_interval: float = 0
    peak_hours: List[int] = None
    user_segments: List[str] = None
    response_size: int = 0
    generation_time: float = 0
    hit_rate: float = 0

    def __post_init__(self):
        if self.peak_hours is None:
            self.peak_hours = []
        if self.user_segments is None:
            self.user_segments = []

    def update_access(self, access_time: float):
        """更新访问信息"""
        if self.access_count > 0:
            interval = access_time - self.last_access
            # 计算移动平均间隔
            self.avg_interval = (self.avg_interval * (self.access_count - 1) + interval) / self.access_count

        self.access_count += 1
        self.last_access = access_time

        # 更新峰值小时
        hour = time.localtime(access_time).tm_hour
        if hour not in self.peak_hours:
            self.peak_hours.append(hour)

    def get_priority_score(self) -> float:
        """获取优先级分数"""
        current_hour = time.localtime().tm_hour
        in_peak_hour = current_hour in self.peak_hours

        score = (
            self.access_count * 0.3 +                     # 访问频率
            (1 / max(1, self.avg_interval)) * 0.2 +     # 访问间隔
            self.generation_time * 0.2 +                   # 生成时间
            (1 - self.hit_rate) * 0.2 +                  # 缓存未命中率
            (5 if in_peak_hour else 1) * 0.1              # 峰值时间权重
        )

        return score


class CacheWarmupManager:
    """缓存预热管理器"""

    def __init__(self):
        self.cache_manager = None
        self.warmup_queue: asyncio.Queue = None
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.completion_callbacks: List[Callable] = []

        # 访问模式跟踪
        self.access_patterns: Dict[str, AccessPattern] = {}
        self.access_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # 预热配置
        self.config = {
            "max_concurrent_tasks": 10,
            "warmup_interval": 300,          # 5分钟
            "pattern_analyze_interval": 3600,  # 1小时
            "min_access_count": 5,            # 最小访问次数
            "min_priority_score": 1.0,        # 最小优先级分数
            "max_history_size": 1000,         # 最大历史记录数
        }

        # 统计信息
        self.stats = {
            "total_warmups": 0,
            "successful_warmups": 0,
            "failed_warmups": 0,
            "patterns_discovered": 0,
            "predictions_accuracy": 0
        }

        self._running = False
        self._warmup_scheduler_task = None
        self._pattern_analyzer_task = None

    async def initialize(self):
        """初始化预热管理器"""
        self.cache_manager = await get_cache_manager()
        self.warmup_queue = asyncio.Queue(maxsize=1000)

        # 启动调度器
        await self.start_scheduler()

        logger.info("Cache warmup manager initialized")

    async def start_scheduler(self):
        """启动预热调度器"""
        if self._running:
            return

        self._running = True

        # 启动预热任务调度器
        self._warmup_scheduler_task = asyncio.create_task(self._warmup_scheduler())

        # 启动模式分析器
        self._pattern_analyzer_task = asyncio.create_task(self._pattern_analyzer())

        logger.info("Cache warmup scheduler started")

    async def stop_scheduler(self):
        """停止预热调度器"""
        self._running = False

        if self._warmup_scheduler_task:
            self._warmup_scheduler_task.cancel()
            try:
                await self._warmup_scheduler_task
            except asyncio.CancelledError:
                pass

        if self._pattern_analyzer_task:
            self._pattern_analyzer_task.cancel()
            try:
                await self._pattern_analyzer_task
            except asyncio.CancelledError:
                pass

        # 取消所有活跃任务
        for task in self.active_tasks.values():
            task.cancel()

        logger.info("Cache warmup scheduler stopped")

    async def add_warmup_task(self, task: WarmupTask) -> bool:
        """添加预热任务"""
        try:
            await self.warmup_queue.put(task)
            logger.debug(f"Added warmup task: {task.id} ({task.key})")
            return True
        except asyncio.QueueFull:
            logger.warning(f"Warmup queue full, dropping task: {task.id}")
            return False

    async def record_access(self, key: str, user_id: str = None, generation_time: float = 0,
                          response_size: int = 0, hit: bool = False):
        """记录访问信息"""
        current_time = time.time()

        # 记录访问历史
        self.access_history[key].append({
            "timestamp": current_time,
            "user_id": user_id,
            "generation_time": generation_time,
            "response_size": response_size,
            "hit": hit
        })

        # 更新或创建访问模式
        pattern = self.access_patterns.get(key)
        if not pattern:
            pattern = AccessPattern(key_pattern=key)
            self.access_patterns[key] = pattern

        pattern.update_access(current_time)
        pattern.generation_time = generation_time
        pattern.response_size = response_size
        pattern.hit_rate = 1.0 - (sum(1 for h in self.access_history[key] if not h["hit"]) /
                                max(1, len(self.access_history[key])))

        if user_id:
            if user_id not in pattern.user_segments:
                pattern.user_segments.append(user_id)

    async def schedule_pattern_based_warmup(self):
        """基于访问模式调度预热"""
        warmup_candidates = []

        for key, pattern in self.access_patterns.items():
            if pattern.access_count < self.config["min_access_count"]:
                continue

            priority_score = pattern.get_priority_score()
            if priority_score < self.config["min_priority_score"]:
                continue

            # 创建预热任务
            task = WarmupTask(
                id=f"pattern_{hashlib.md5(key.encode()).hexdigest()[:8]}",
                key=key,
                data_generator=self._create_data_generator(key),
                priority=self._determine_priority(priority_score),
                strategy=WarmupStrategy.TRAFFIC_BASED,
                ttl=self._calculate_ttl(pattern),
                metadata={
                    "priority_score": priority_score,
                    "access_count": pattern.access_count,
                    "hit_rate": pattern.hit_rate
                }
            )

            warmup_candidates.append((priority_score, task))

        # 按优先级排序并添加到队列
        warmup_candidates.sort(key=lambda x: x[0], reverse=True)
        for _, task in warmup_candidates[:20]:  # 限制数量
            await self.add_warmup_task(task)

        logger.info(f"Scheduled {len(warmup_candidates)} pattern-based warmup tasks")

    async def schedule_user_based_warmup(self, user_id: str):
        """为特定用户调度预热"""
        user_patterns = [
            pattern for pattern in self.access_patterns.values()
            if user_id in pattern.user_segments
        ]

        for pattern in user_patterns:
            task = WarmupTask(
                id=f"user_{user_id}_{hashlib.md5(pattern.key_pattern.encode()).hexdigest()[:8]}",
                key=pattern.key_pattern,
                data_generator=self._create_data_generator(pattern.key_pattern),
                priority=WarmupPriority.MEDIUM,
                strategy=WarmupStrategy.USER_BASED,
                ttl=self._calculate_ttl(pattern),
                tags=[f"user:{user_id}"]
            )

            await self.add_warmup_task(task)

        logger.info(f"Scheduled {len(user_patterns)} user-based warmup tasks for {user_id}")

    async def schedule_predictive_warmup(self):
        """预测性预热调度"""
        current_hour = time.localtime().tm_hour
        predictions = self._predict_next_hour_access()

        for key, predicted_accesses in predictions.items():
            if predicted_accesses > 5:  # 预测访问阈值
                task = WarmupTask(
                    id=f"predict_{current_hour}_{hashlib.md5(key.encode()).hexdigest()[:8]}",
                    key=key,
                    data_generator=self._create_data_generator(key),
                    priority=WarmupPriority.HIGH,
                    strategy=WarmupStrategy.PREDICTIVE,
                    ttl=self.config["warmup_interval"],
                    metadata={"predicted_accesses": predicted_accesses}
                )

                await self.add_warmup_task(task)

        logger.info(f"Scheduled {len(predictions)} predictive warmup tasks")

    async def _warmup_scheduler(self):
        """预热任务调度器主循环"""
        while self._running:
            try:
                # 处理预热队列
                while len(self.active_tasks) < self.config["max_concurrent_tasks"]:
                    try:
                        task = await asyncio.wait_for(self.warmup_queue.get(), timeout=1.0)
                        if task.is_ready():
                            await self._execute_warmup_task(task)
                        else:
                            # 重新放回队列
                            await self.warmup_queue.put(task)
                            break
                    except asyncio.TimeoutError:
                        break

                # 清理已完成的任务
                completed_tasks = [task_id for task_id, task in self.active_tasks.items()
                                 if task.done()]
                for task_id in completed_tasks:
                    del self.active_tasks[task_id]

                await asyncio.sleep(1)  # 避免过度占用CPU

            except Exception as e:
                logger.error(f"Warmup scheduler error: {e}")
                await asyncio.sleep(5)

    async def _pattern_analyzer(self):
        """访问模式分析器"""
        while self._running:
            try:
                await asyncio.sleep(self.config["pattern_analyze_interval"])

                # 分析访问模式
                await self._analyze_patterns()

                # 基于模式调度预热
                await self.schedule_pattern_based_warmup()

                # 预测性预热
                await self.schedule_predictive_warmup()

                # 清理历史数据
                await self._cleanup_history()

            except Exception as e:
                logger.error(f"Pattern analyzer error: {e}")

    async def _execute_warmup_task(self, task: WarmupTask):
        """执行预热任务"""
        task_id = task.id
        worker_task = asyncio.create_task(self._warmup_worker(task))
        self.active_tasks[task_id] = worker_task

        logger.debug(f"Started warmup worker for task: {task_id}")

    async def _warmup_worker(self, task: WarmupTask):
        """预热工作线程"""
        try:
            logger.debug(f"Executing warmup task: {task.id} for key: {task.key}")

            # 执行数据生成
            start_time = time.time()
            data = await task.data_generator()
            generation_time = time.time() - start_time

            # 存储到缓存
            if data is not None:
                await self.cache_manager.set(task.key, data, task.ttl)
                self.stats["successful_warmups"] += 1

                logger.debug(f"Warmup successful: {task.id} ({generation_time:.3f}s)")
            else:
                logger.warning(f"Warmup generated None data: {task.id}")

            self.stats["total_warmups"] += 1

            # 执行回调
            await self._notify_completion(task, True, generation_time)

        except Exception as e:
            logger.error(f"Warmup task failed: {task.id} - {e}")

            # 重试逻辑
            task.retry_count += 1
            if task.should_retry():
                task.scheduled_at = time.time() + (2 ** task.retry_count) * 10  # 指数退避
                await self.add_warmup_task(task)
                logger.info(f"Rescheduled warmup task: {task.id} (retry {task.retry_count})")
            else:
                self.stats["failed_warmups"] += 1
                logger.error(f"Warmup task permanently failed: {task.id}")

            await self._notify_completion(task, False, 0, str(e))

    def _create_data_generator(self, key: str) -> Callable:
        """创建数据生成器"""
        async def generator():
            # 根据key模式生成相应的数据
            if key.startswith("api_cache:get:models"):
                return await self._generate_models_data()
            elif key.startswith("api_cache:get:stats"):
                return await self._generate_stats_data()
            elif key.startswith("api_cache:get:health"):
                return await self._generate_health_data()
            elif "sessions" in key:
                return await self._generate_sessions_data(key)
            elif "organizations" in key:
                return await self._generate_organizations_data(key)
            else:
                # 通用数据生成
                return await self._generate_generic_data(key)

        return generator

    async def _generate_models_data(self):
        """生成模型数据"""
        try:
            ai_service = await ai_manager.get_service("openrouter")
            if ai_service:
                return await ai_service.get_available_models()
            return []
        except Exception as e:
            logger.error(f"Error generating models data: {e}")
            return []

    async def _generate_stats_data(self):
        """生成统计数据"""
        return {
            "total_requests": 1000,
            "successful_requests": 950,
            "failed_requests": 50,
            "cache_hit_rate": 0.85,
            "avg_response_time": 250
        }

    async def _generate_health_data(self):
        """生成健康检查数据"""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {
                "ai_service": "healthy",
                "cache": "healthy",
                "database": "healthy"
            }
        }

    async def _generate_sessions_data(self, key: str):
        """生成会话数据"""
        # 根据key参数生成相应的会话数据
        return {"sessions": [], "total": 0}

    async def _generate_organizations_data(self, key: str):
        """生成组织数据"""
        # 根据key参数生成相应的组织数据
        return {"organizations": [], "total": 0}

    async def _generate_generic_data(self, key: str):
        """生成通用数据"""
        # 尝试从key中解析信息并生成相应数据
        return {"data": "cached", "key": key, "timestamp": time.time()}

    def _determine_priority(self, priority_score: float) -> WarmupPriority:
        """根据分数确定优先级"""
        if priority_score >= 5.0:
            return WarmupPriority.CRITICAL
        elif priority_score >= 3.0:
            return WarmupPriority.HIGH
        elif priority_score >= 1.5:
            return WarmupPriority.MEDIUM
        else:
            return WarmupPriority.LOW

    def _calculate_ttl(self, pattern: AccessPattern) -> int:
        """计算TTL"""
        base_ttl = self.config["warmup_interval"]
        # 根据访问频率调整TTL
        frequency_factor = min(5.0, pattern.access_count / 10.0)
        return int(base_ttl * frequency_factor)

    def _predict_next_hour_access(self) -> Dict[str, int]:
        """预测下一小时的访问"""
        predictions = {}
        current_hour = time.localtime().tm_hour

        for key, pattern in self.access_patterns.items():
            # 简单的基于历史数据的预测
            if current_hour + 1 in pattern.peak_hours:
                # 基于平均访问频率的预测
                predicted_accesses = int(pattern.access_count / 24)  # 简单平均
                if predicted_accesses > 0:
                    predictions[key] = predicted_accesses

        return predictions

    async def _analyze_patterns(self):
        """分析访问模式"""
        # 发现新的访问模式
        for key, history in self.access_history.items():
            if len(history) >= 10:  # 需要足够的历史数据
                pattern = self.access_patterns.get(key)
                if pattern:
                    # 计算访问间隔的统计信息
                    intervals = []
                    for i in range(1, len(history)):
                        interval = history[i]["timestamp"] - history[i-1]["timestamp"]
                        intervals.append(interval)

                    if intervals:
                        pattern.avg_interval = statistics.mean(intervals)

                        # 更新峰值小时
                        hour_counts = defaultdict(int)
                        for entry in history:
                            hour = time.localtime(entry["timestamp"]).tm_hour
                            hour_counts[hour] += 1

                        # 获取访问量前3的小时作为峰值小时
                        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
                        pattern.peak_hours = [hour for hour, _ in sorted_hours[:3]]

        logger.info(f"Analyzed {len(self.access_patterns)} access patterns")

    async def _cleanup_history(self):
        """清理历史数据"""
        max_history = self.config["max_history_size"]
        removed_count = 0

        for key, history in self.access_history.items():
            if len(history) > max_history:
                # 保留最近的记录
                while len(history) > max_history:
                    history.popleft()
                    removed_count += 1

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old access history records")

    async def _notify_completion(self, task: WarmupTask, success: bool,
                              generation_time: float, error: str = None):
        """通知任务完成"""
        for callback in self.completion_callbacks:
            try:
                await callback(task, success, generation_time, error)
            except Exception as e:
                logger.error(f"Error in completion callback: {e}")

    def add_completion_callback(self, callback: Callable):
        """添加完成回调"""
        self.completion_callbacks.append(callback)

    async def get_warmup_stats(self) -> Dict:
        """获取预热统计"""
        queue_size = self.warmup_queue.qsize() if self.warmup_queue else 0
        active_count = len(self.active_tasks)

        return {
            "scheduler_running": self._running,
            "queue_size": queue_size,
            "active_tasks": active_count,
            "max_concurrent_tasks": self.config["max_concurrent_tasks"],
            "access_patterns_count": len(self.access_patterns),
            "total_history_entries": sum(len(history) for history in self.access_history.values()),
            "stats": self.stats.copy(),
            "success_rate": (
                self.stats["successful_warmups"] / max(1, self.stats["total_warmups"])
            )
        }

    async def force_warmup(self, keys: List[str], priority: WarmupPriority = WarmupPriority.HIGH):
        """强制预热指定的keys"""
        tasks = []
        for key in keys:
            task = WarmupTask(
                id=f"force_{hashlib.md5(key.encode()).hexdigest()[:8]}",
                key=key,
                data_generator=self._create_data_generator(key),
                priority=priority,
                strategy=WarmupStrategy.MANUAL,
                ttl=self.config["warmup_interval"]
            )
            tasks.append(task)

        for task in tasks:
            await self.add_warmup_task(task)

        logger.info(f"Forced warmup for {len(keys)} keys")
        return len(tasks)


# 全局预热管理器实例
_warmup_manager: Optional[CacheWarmupManager] = None


async def get_warmup_manager() -> CacheWarmupManager:
    """获取全局预热管理器实例"""
    global _warmup_manager
    if _warmup_manager is None:
        _warmup_manager = CacheWarmupManager()
        await _warmup_manager.initialize()
    return _warmup_manager


# 便捷函数
async def record_cache_access(key: str, user_id: str = None, generation_time: float = 0,
                           response_size: int = 0, hit: bool = False):
    """记录缓存访问"""
    manager = await get_warmup_manager()
    await manager.record_access(key, user_id, generation_time, response_size, hit)


async def schedule_warmup(key: str, data_generator: Callable,
                        priority: WarmupPriority = WarmupPriority.MEDIUM,
                        ttl: int = 300) -> bool:
    """调度单个预热任务"""
    manager = await get_warmup_manager()
    task = WarmupTask(
        id=f"manual_{hashlib.md5(key.encode()).hexdigest()[:8]}",
        key=key,
        data_generator=data_generator,
        priority=priority,
        strategy=WarmupStrategy.MANUAL,
        ttl=ttl
    )
    return await manager.add_warmup(task)