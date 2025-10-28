"""
指标收集器
Metrics Collector Module

提供企业级指标收集功能，包括：
- 实时指标收集
- 定时指标聚合
- 多数据源整合
- 指标预处理和清洗
- 指标存储和缓存
- 指标质量监控
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import uuid
from collections import defaultdict
import time

from backend.config.settings import get_settings
from backend.core.cache.multi_level_cache import cache_manager

settings = get_settings()
logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"  # 计数器
    GAUGE = "gauge"      # 仪表盘
    HISTOGRAM = "histogram"  # 直方图
    TIMER = "timer"      # 计时器


class MetricSource(Enum):
    """数据源枚举"""
    API_ENDPOINTS = "api_endpoints"
    DATABASE = "database"
    CACHE = "cache"
    SYSTEM = "system"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_API = "external_api"


@dataclass
class MetricDefinition:
    """指标定义"""
    metric_id: str
    name: str
    description: str
    metric_type: MetricType
    source: MetricSource
    unit: str
    tags: Dict[str, str]
    collection_interval: int  # 收集间隔（秒）
    aggregation_method: str  # 聚合方法: sum, avg, max, min, count
    enabled: bool


@dataclass
class MetricData:
    """指标数据"""
    metric_id: str
    timestamp: datetime
    value: Union[int, float]
    labels: Dict[str, str]
    source: MetricSource
    quality_score: float  # 数据质量评分 0-1


@dataclass
class MetricAggregation:
    """指标聚合结果"""
    metric_id: str
    aggregation_period: str  # 1m, 5m, 15m, 1h, 1d
    timestamp: datetime
    aggregated_value: float
    sample_count: int
    min_value: float
    max_value: float
    avg_value: float
    sum_value: float


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.cache_key_prefix = "metrics_collector"
        self.data_dir = Path("data/analytics/metrics")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 存储路径
        self.metrics_data_path = self.data_dir / "raw_metrics.jsonl"
        self.aggregations_path = self.data_dir / "aggregations.jsonl"
        self.definitions_path = self.data_dir / "metric_definitions.json"

        # 运行时状态
        self.metric_definitions: Dict[str, MetricDefinition] = {}
        self.collection_tasks: Dict[str, asyncio.Task] = {}
        self.aggregation_tasks: Dict[str, asyncio.Task] = {}
        self.is_running = False

        # 默认指标定义
        self.default_metrics = self._create_default_metrics()

        # 数据收集器
        self.collectors: Dict[MetricSource, Callable] = {
            MetricSource.API_ENDPOINTS: self._collect_api_metrics,
            MetricSource.DATABASE: self._collect_database_metrics,
            MetricSource.CACHE: self._collect_cache_metrics,
            MetricSource.SYSTEM: self._collect_system_metrics,
            MetricSource.BUSINESS_LOGIC: self._collect_business_metrics,
            MetricSource.EXTERNAL_API: self._collect_external_api_metrics
        }

    async def start(self):
        """启动指标收集器"""
        try:
            if self.is_running:
                logger.warning("Metrics collector is already running")
                return

            logger.info("Starting metrics collector")

            # 加载指标定义
            await self._load_metric_definitions()

            # 启动数据收集任务
            await self._start_collection_tasks()

            # 启动聚合任务
            await self._start_aggregation_tasks()

            self.is_running = True
            logger.info("Metrics collector started successfully")

        except Exception as e:
            logger.error(f"Error starting metrics collector: {e}")
            raise

    async def stop(self):
        """停止指标收集器"""
        try:
            if not self.is_running:
                return

            logger.info("Stopping metrics collector")

            # 停止收集任务
            for task_id, task in self.collection_tasks.items():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # 停止聚合任务
            for task_id, task in self.aggregation_tasks.items():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            self.collection_tasks.clear()
            self.aggregation_tasks.clear()
            self.is_running = False

            logger.info("Metrics collector stopped")

        except Exception as e:
            logger.error(f"Error stopping metrics collector: {e}")

    async def register_metric(self, definition: MetricDefinition):
        """注册指标定义"""
        try:
            self.metric_definitions[definition.metric_id] = definition
            await self._save_metric_definitions()

            # 如果收集器正在运行，启动该指标的收集任务
            if self.is_running and definition.enabled:
                await self._start_metric_collection(definition)

            logger.info(f"Metric registered: {definition.metric_id}")

        except Exception as e:
            logger.error(f"Error registering metric {definition.metric_id}: {e}")

    async def collect_metric(self, metric_id: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """手动收集指标"""
        try:
            if metric_id not in self.metric_definitions:
                logger.warning(f"Unknown metric: {metric_id}")
                return

            definition = self.metric_definitions[metric_id]

            metric_data = MetricData(
                metric_id=metric_id,
                timestamp=datetime.now(),
                value=value,
                labels=labels or {},
                source=definition.source,
                quality_score=self._calculate_data_quality(value, definition)
            )

            # 保存指标数据
            await self._save_metric_data(metric_data)

            # 更新实时缓存
            await self._update_realtime_cache(metric_data)

            logger.debug(f"Collected metric: {metric_id} = {value}")

        except Exception as e:
            logger.error(f"Error collecting metric {metric_id}: {e}")

    async def get_metrics(
        self,
        metric_ids: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        aggregation_period: Optional[str] = None
    ) -> List[Union[MetricData, MetricAggregation]]:
        """
        获取指标数据

        Args:
            metric_ids: 指标ID列表
            start_time: 开始时间
            end_time: 结束时间
            aggregation_period: 聚合周期

        Returns:
            List[Union[MetricData, MetricAggregation]]: 指标数据列表
        """
        try:
            if not start_time:
                start_time = datetime.now() - timedelta(hours=1)
            if not end_time:
                end_time = datetime.now()

            # 尝试从缓存获取
            cache_key = f"{self.cache_key_prefix}:query:{hash(str(metric_ids) + str(start_time) + str(end_time) + str(aggregation_period))}"
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                return [
                    MetricData(**item) if item.get("metric_id") and not item.get("aggregation_period")
                    else MetricAggregation(**item)
                    for item in cached_result
                ]

            # 从存储加载
            if aggregation_period:
                metrics = await self._load_aggregated_metrics(metric_ids, start_time, end_time, aggregation_period)
            else:
                metrics = await self._load_raw_metrics(metric_ids, start_time, end_time)

            # 缓存结果（缓存5分钟）
            await cache_manager.set(
                cache_key,
                [asdict(metric) for metric in metrics],
                expire_seconds=300
            )

            return metrics

        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return []

    async def get_metric_summary(self, metric_id: str, period: str = "1h") -> Dict[str, float]:
        """获取指标摘要"""
        try:
            end_time = datetime.now()
            start_time = self._parse_period(period, end_time)

            metrics = await self.get_metrics([metric_id], start_time, end_time)
            if not metrics:
                return {}

            values = [metric.value for metric in metrics if isinstance(metric, MetricData)]

            if not values:
                return {}

            return {
                "count": len(values),
                "sum": sum(values),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "latest": values[-1] if values else 0
            }

        except Exception as e:
            logger.error(f"Error getting metric summary for {metric_id}: {e}")
            return {}

    # 私有方法

    def _create_default_metrics(self) -> Dict[str, MetricDefinition]:
        """创建默认指标定义"""
        metrics = {}

        # API相关指标
        metrics["api_requests_total"] = MetricDefinition(
            metric_id="api_requests_total",
            name="API请求总数",
            description="API端点接收到的总请求数",
            metric_type=MetricType.COUNTER,
            source=MetricSource.API_ENDPOINTS,
            unit="requests",
            tags={"service": "api", "type": "counter"},
            collection_interval=60,
            aggregation_method="sum",
            enabled=True
        )

        metrics["api_response_time"] = MetricDefinition(
            metric_id="api_response_time",
            name="API响应时间",
            description="API端点平均响应时间",
            metric_type=MetricType.GAUGE,
            source=MetricSource.API_ENDPOINTS,
            unit="milliseconds",
            tags={"service": "api", "type": "gauge"},
            collection_interval=60,
            aggregation_method="avg",
            enabled=True
        )

        metrics["api_error_rate"] = MetricDefinition(
            metric_id="api_error_rate",
            name="API错误率",
            description="API端点错误率",
            metric_type=MetricType.GAUGE,
            source=MetricSource.API_ENDPOINTS,
            unit="percentage",
            tags={"service": "api", "type": "gauge"},
            collection_interval=60,
            aggregation_method="avg",
            enabled=True
        )

        # 业务相关指标
        metrics["active_users_total"] = MetricDefinition(
            metric_id="active_users_total",
            name="活跃用户总数",
            description="当前活跃用户数量",
            metric_type=MetricType.GAUGE,
            source=MetricSource.BUSINESS_LOGIC,
            unit="users",
            tags={"service": "business", "type": "gauge"},
            collection_interval=300,
            aggregation_method="max",
            enabled=True
        )

        metrics["revenue_daily"] = MetricDefinition(
            metric_id="revenue_daily",
            name="日收入",
            description="每日产生的收入",
            metric_type=MetricType.GAUGE,
            source=MetricSource.BUSINESS_LOGIC,
            unit="dollars",
            tags={"service": "business", "type": "gauge"},
            collection_interval=3600,
            aggregation_method="sum",
            enabled=True
        )

        # 系统相关指标
        metrics["system_cpu_usage"] = MetricDefinition(
            metric_id="system_cpu_usage",
            name="系统CPU使用率",
            description="系统CPU使用百分比",
            metric_type=MetricType.GAUGE,
            source=MetricSource.SYSTEM,
            unit="percentage",
            tags={"service": "system", "type": "gauge"},
            collection_interval=60,
            aggregation_method="avg",
            enabled=True
        )

        metrics["system_memory_usage"] = MetricDefinition(
            metric_id="system_memory_usage",
            name="系统内存使用率",
            description="系统内存使用百分比",
            metric_type=MetricType.GAUGE,
            source=MetricSource.SYSTEM,
            unit="percentage",
            tags={"service": "system", "type": "gauge"},
            collection_interval=60,
            aggregation_method="avg",
            enabled=True
        )

        return metrics

    async def _load_metric_definitions(self):
        """加载指标定义"""
        try:
            # 加载默认指标
            self.metric_definitions.update(self.default_metrics)

            # 从文件加载自定义指标
            if self.definitions_path.exists():
                with open(self.definitions_path, 'r') as f:
                    definitions_data = json.load(f)

                for metric_id, definition_data in definitions_data.items():
                    definition_data["metric_type"] = MetricType(definition_data["metric_type"])
                    definition_data["source"] = MetricSource(definition_data["source"])
                    self.metric_definitions[metric_id] = MetricDefinition(**definition_data)

            logger.info(f"Loaded {len(self.metric_definitions)} metric definitions")

        except Exception as e:
            logger.error(f"Error loading metric definitions: {e}")

    async def _save_metric_definitions(self):
        """保存指标定义"""
        try:
            definitions_data = {}
            for metric_id, definition in self.metric_definitions.items():
                def_data = asdict(definition)
                def_data["metric_type"] = definition.metric_type.value
                def_data["source"] = definition.source.value
                definitions_data[metric_id] = def_data

            with open(self.definitions_path, 'w') as f:
                json.dump(definitions_data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving metric definitions: {e}")

    async def _start_collection_tasks(self):
        """启动数据收集任务"""
        for metric_id, definition in self.metric_definitions.items():
            if definition.enabled:
                await self._start_metric_collection(definition)

    async def _start_metric_collection(self, definition: MetricDefinition):
        """启动单个指标的收集任务"""
        try:
            if definition.metric_id in self.collection_tasks:
                return

            task = asyncio.create_task(
                self._collect_metric_loop(definition)
            )
            self.collection_tasks[definition.metric_id] = task

            logger.debug(f"Started collection task for metric: {definition.metric_id}")

        except Exception as e:
            logger.error(f"Error starting collection for {definition.metric_id}: {e}")

    async def _collect_metric_loop(self, definition: MetricDefinition):
        """指标收集循环"""
        while self.is_running:
            try:
                start_time = time.time()

                # 收集指标
                await self._collect_from_source(definition)

                # 计算下次执行时间
                elapsed = time.time() - start_time
                sleep_time = max(0, definition.collection_interval - elapsed)

                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in collection loop for {definition.metric_id}: {e}")
                await asyncio.sleep(definition.collection_interval)

    async def _collect_from_source(self, definition: MetricDefinition):
        """从数据源收集指标"""
        try:
            collector = self.collectors.get(definition.source)
            if collector:
                metrics = await collector(definition)
                for metric_data in metrics:
                    await self._save_metric_data(metric_data)
                    await self._update_realtime_cache(metric_data)
            else:
                logger.warning(f"No collector found for source: {definition.source}")

        except Exception as e:
            logger.error(f"Error collecting from source {definition.source}: {e}")

    async def _collect_api_metrics(self, definition: MetricDefinition) -> List[MetricData]:
        """收集API指标"""
        metrics = []

        try:
            # TODO: 实现实际的API指标收集逻辑
            # 这里返回模拟数据

            if definition.metric_id == "api_requests_total":
                metrics.append(MetricData(
                    metric_id=definition.metric_id,
                    timestamp=datetime.now(),
                    value=1000 + (hash(datetime.now().isoformat()) % 100),
                    labels={"endpoint": "/api/v1/chat"},
                    source=definition.source,
                    quality_score=1.0
                ))

            elif definition.metric_id == "api_response_time":
                metrics.append(MetricData(
                    metric_id=definition.metric_id,
                    timestamp=datetime.now(),
                    value=150 + (hash(datetime.now().isoformat()) % 50),
                    labels={"endpoint": "/api/v1/chat"},
                    source=definition.source,
                    quality_score=1.0
                ))

            elif definition.metric_id == "api_error_rate":
                metrics.append(MetricData(
                    metric_id=definition.metric_id,
                    timestamp=datetime.now(),
                    value=2.0 + (hash(datetime.now().isoformat()) % 5),
                    labels={"endpoint": "/api/v1/chat"},
                    source=definition.source,
                    quality_score=1.0
                ))

        except Exception as e:
            logger.error(f"Error collecting API metrics: {e}")

        return metrics

    async def _collect_database_metrics(self, definition: MetricDefinition) -> List[MetricData]:
        """收集数据库指标"""
        # TODO: 实现数据库指标收集
        return []

    async def _collect_cache_metrics(self, definition: MetricDefinition) -> List[MetricData]:
        """收集缓存指标"""
        try:
            metrics = []
            # TODO: 从实际的缓存系统获取指标
            # 这里返回模拟数据

            if definition.metric_id == "cache_hit_rate":
                metrics.append(MetricData(
                    metric_id=definition.metric_id,
                    timestamp=datetime.now(),
                    value=85.0 + (hash(datetime.now().isoformat()) % 10),
                    labels={"cache": "redis"},
                    source=definition.source,
                    quality_score=1.0
                ))

            return metrics

        except Exception as e:
            logger.error(f"Error collecting cache metrics: {e}")
            return []

    async def _collect_system_metrics(self, definition: MetricDefinition) -> List[MetricData]:
        """收集系统指标"""
        try:
            metrics = []
            # TODO: 实现实际的系统指标收集
            # 这里返回模拟数据

            if definition.metric_id == "system_cpu_usage":
                metrics.append(MetricData(
                    metric_id=definition.metric_id,
                    timestamp=datetime.now(),
                    value=30.0 + (hash(datetime.now().isoformat()) % 40),
                    labels={"host": "server-1"},
                    source=definition.source,
                    quality_score=1.0
                ))

            elif definition.metric_id == "system_memory_usage":
                metrics.append(MetricData(
                    metric_id=definition.metric_id,
                    timestamp=datetime.now(),
                    value=60.0 + (hash(datetime.now().isoformat()) % 20),
                    labels={"host": "server-1"},
                    source=definition.source,
                    quality_score=1.0
                ))

            return metrics

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return []

    async def _collect_business_metrics(self, definition: MetricDefinition) -> List[MetricData]:
        """收集业务指标"""
        try:
            metrics = []
            # TODO: 从业务逻辑收集实际指标

            if definition.metric_id == "active_users_total":
                metrics.append(MetricData(
                    metric_id=definition.metric_id,
                    timestamp=datetime.now(),
                    value=500 + (hash(datetime.now().isoformat()) % 100),
                    labels={},
                    source=definition.source,
                    quality_score=1.0
                ))

            elif definition.metric_id == "revenue_daily":
                metrics.append(MetricData(
                    metric_id=definition.metric_id,
                    timestamp=datetime.now(),
                    value=1000.0 + (hash(datetime.now().isoformat()) % 500),
                    labels={},
                    source=definition.source,
                    quality_score=1.0
                ))

            return metrics

        except Exception as e:
            logger.error(f"Error collecting business metrics: {e}")
            return []

    async def _collect_external_api_metrics(self, definition: MetricDefinition) -> List[MetricData]:
        """收集外部API指标"""
        # TODO: 实现外部API指标收集
        return []

    async def _start_aggregation_tasks(self):
        """启动聚合任务"""
        # 定义聚合周期
        aggregation_periods = ["1m", "5m", "15m", "1h", "1d"]

        for period in aggregation_periods:
            task = asyncio.create_task(
                self._aggregation_loop(period)
            )
            self.aggregation_tasks[period] = task

    async def _aggregation_loop(self, period: str):
        """聚合循环"""
        while self.is_running:
            try:
                # 计算聚合间隔
                interval_seconds = self._parse_aggregation_period(period)
                await asyncio.sleep(interval_seconds)

                # 执行聚合
                await self._aggregate_metrics(period)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in aggregation loop for period {period}: {e}")

    async def _aggregate_metrics(self, period: str):
        """聚合指标"""
        try:
            # 计算聚合时间窗口
            end_time = datetime.now()
            start_time = end_time - timedelta(seconds=self._parse_aggregation_period(period))

            # 获取需要聚合的指标
            for metric_id, definition in self.metric_definitions.items():
                if definition.enabled:
                    await self._aggregate_metric(metric_id, start_time, end_time, period)

        except Exception as e:
            logger.error(f"Error aggregating metrics for period {period}: {e}")

    async def _aggregate_metric(self, metric_id: str, start_time: datetime, end_time: datetime, period: str):
        """聚合单个指标"""
        try:
            # 获取原始数据
            raw_metrics = await self._load_raw_metrics([metric_id], start_time, end_time)
            if not raw_metrics:
                return

            values = [metric.value for metric in raw_metrics]
            if not values:
                return

            # 计算聚合结果
            aggregation = MetricAggregation(
                metric_id=metric_id,
                aggregation_period=period,
                timestamp=end_time,
                aggregated_value=self._apply_aggregation_method(values, self.metric_definitions[metric_id].aggregation_method),
                sample_count=len(values),
                min_value=min(values),
                max_value=max(values),
                avg_value=sum(values) / len(values),
                sum_value=sum(values)
            )

            # 保存聚合结果
            await self._save_aggregation(aggregation)

        except Exception as e:
            logger.error(f"Error aggregating metric {metric_id}: {e}")

    def _parse_aggregation_period(self, period: str) -> int:
        """解析聚合周期为秒数"""
        mapping = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "1d": 86400
        }
        return mapping.get(period, 60)

    def _parse_period(self, period: str, end_time: datetime) -> datetime:
        """解析时间周期"""
        if period.endswith("m"):
            minutes = int(period[:-1])
            return end_time - timedelta(minutes=minutes)
        elif period.endswith("h"):
            hours = int(period[:-1])
            return end_time - timedelta(hours=hours)
        elif period.endswith("d"):
            days = int(period[:-1])
            return end_time - timedelta(days=days)
        else:
            return end_time - timedelta(hours=1)

    def _apply_aggregation_method(self, values: List[float], method: str) -> float:
        """应用聚合方法"""
        if not values:
            return 0.0

        if method == "sum":
            return sum(values)
        elif method == "avg":
            return sum(values) / len(values)
        elif method == "max":
            return max(values)
        elif method == "min":
            return min(values)
        elif method == "count":
            return len(values)
        else:
            return sum(values) / len(values)

    def _calculate_data_quality(self, value: Union[int, float], definition: MetricDefinition) -> float:
        """计算数据质量评分"""
        try:
            # 基本的质量检查
            if value is None:
                return 0.0

            if isinstance(value, (int, float)):
                if value < 0 and definition.metric_type == MetricType.COUNTER:
                    return 0.5  # 计数器不应该有负值

                # 检查异常值
                if abs(value) > 10 ** 9:  # 过大的值
                    return 0.3

            return 1.0

        except Exception:
            return 0.0

    async def _save_metric_data(self, metric_data: MetricData):
        """保存指标数据"""
        try:
            # 保存到文件
            data_dict = asdict(metric_data)
            data_dict["timestamp"] = metric_data.timestamp.isoformat()
            data_dict["source"] = metric_data.source.value

            with open(self.metrics_data_path, 'a') as f:
                f.write(json.dumps(data_dict) + '\n')

        except Exception as e:
            logger.error(f"Error saving metric data: {e}")

    async def _save_aggregation(self, aggregation: MetricAggregation):
        """保存聚合结果"""
        try:
            data_dict = asdict(aggregation)
            data_dict["timestamp"] = aggregation.timestamp.isoformat()

            with open(self.aggregations_path, 'a') as f:
                f.write(json.dumps(data_dict) + '\n')

        except Exception as e:
            logger.error(f"Error saving aggregation: {e}")

    async def _update_realtime_cache(self, metric_data: MetricData):
        """更新实时缓存"""
        try:
            cache_key = f"{self.cache_key_prefix}:realtime:{metric_data.metric_id}"
            await cache_manager.set(
                cache_key,
                asdict(metric_data),
                expire_seconds=300  # 5分钟过期
            )
        except Exception as e:
            logger.error(f"Error updating realtime cache: {e}")

    async def _load_raw_metrics(
        self,
        metric_ids: Optional[List[str]],
        start_time: datetime,
        end_time: datetime
    ) -> List[MetricData]:
        """加载原始指标数据"""
        try:
            if not self.metrics_data_path.exists():
                return []

            metrics = []
            with open(self.metrics_data_path, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        timestamp = datetime.fromisoformat(data["timestamp"])

                        if start_time <= timestamp <= end_time:
                            if not metric_ids or data["metric_id"] in metric_ids:
                                data["timestamp"] = timestamp
                                data["source"] = MetricSource(data["source"])
                                metrics.append(MetricData(**data))
                    except Exception as e:
                        logger.debug(f"Error parsing metric data line: {e}")
                        continue

            return metrics

        except Exception as e:
            logger.error(f"Error loading raw metrics: {e}")
            return []

    async def _load_aggregated_metrics(
        self,
        metric_ids: Optional[List[str]],
        start_time: datetime,
        end_time: datetime,
        period: str
    ) -> List[MetricAggregation]:
        """加载聚合指标数据"""
        try:
            if not self.aggregations_path.exists():
                return []

            metrics = []
            with open(self.aggregations_path, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        timestamp = datetime.fromisoformat(data["timestamp"])

                        if (start_time <= timestamp <= end_time and
                            data["aggregation_period"] == period):
                            if not metric_ids or data["metric_id"] in metric_ids:
                                data["timestamp"] = timestamp
                                metrics.append(MetricAggregation(**data))
                    except Exception as e:
                        logger.debug(f"Error parsing aggregation data line: {e}")
                        continue

            return metrics

        except Exception as e:
            logger.error(f"Error loading aggregated metrics: {e}")
            return []


# 全局实例
metrics_collector = MetricsCollector()