"""
缓存性能监控和分析系统
实时监控缓存性能指标，提供详细的性能分析和优化建议
"""

import asyncio
import time
import json
import logging
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import statistics
import threading

from backend.core.cache.multi_level_cache import get_cache_manager, CacheLevel

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(Enum):
    """告警严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: float
    value: float
    tags: Dict[str, str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


@dataclass
class PerformanceAlert:
    """性能告警"""
    id: str
    metric_name: str
    severity: AlertSeverity
    message: str
    threshold_value: float
    actual_value: float
    timestamp: float
    resolved: bool = False
    resolved_at: Optional[float] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class CacheMetricsCollector:
    """缓存指标收集器"""

    def __init__(self):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        self.collection_interval = 30  # 30秒收集一次
        self._collecting = False
        self._collection_task = None

    async def start_collection(self):
        """开始指标收集"""
        if self._collecting:
            return

        self._collecting = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("Cache metrics collection started")

    async def stop_collection(self):
        """停止指标收集"""
        self._collecting = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Cache metrics collection stopped")

    async def _collection_loop(self):
        """指标收集循环"""
        while self._collecting:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(5)

    async def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            cache_manager = await get_cache_manager()
            stats = await cache_manager.get_comprehensive_stats()

            current_time = time.time()

            # 收集L1缓存指标
            l1_stats = stats.get("l1_memory", {})
            if l1_stats:
                self.record_gauge("cache.l1.entries_count", l1_stats.get("entries_count", 0))
                self.record_gauge("cache.l1.total_size_bytes", l1_stats.get("total_size_bytes", 0))
                self.record_gauge("cache.l1.hit_rate", l1_stats.get("hit_rate", 0))
                self.record_gauge("cache.l1.expired_count", l1_stats.get("expired_count", 0))

            # 收集L2缓存指标
            l2_stats = stats.get("l2_redis", {})
            if l2_stats:
                self.record_gauge("cache.l2.connected_clients", l2_stats.get("connected_clients", 0))
                self.record_gauge("cache.l2.used_memory", l2_stats.get("used_memory", 0))
                self.record_gauge("cache.l2.total_keys", l2_stats.get("total_keys", 0))
                self.record_gauge("cache.l2.hit_rate", l2_stats.get("hit_rate", 0))

            # 收集总体指标
            overall = stats.get("overall", {})
            if overall:
                self.record_counter("cache.total_requests", overall.get("total_requests", 0))
                self.record_counter("cache.l1_hits", overall.get("l1_hits", 0))
                self.record_counter("cache.l2_hits", overall.get("l2_hits", 0))
                self.record_counter("cache.l3_hits", overall.get("l3_hits", 0))
                self.record_counter("cache.misses", overall.get("misses", 0))
                self.record_counter("cache.sets", overall.get("sets", 0))
                self.record_counter("cache.deletes", overall.get("deletes", 0))

                total_requests = overall.get("total_requests", 0)
                hits = overall.get("l1_hits", 0) + overall.get("l2_hits", 0) + overall.get("l3_hits", 0)
                if total_requests > 0:
                    hit_rate = hits / total_requests
                    self.record_gauge("cache.overall_hit_rate", hit_rate)

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

    def record_counter(self, name: str, value: float = 1, tags: Dict[str, str] = None):
        """记录计数器指标"""
        self.counters[name] += value
        self._record_metric(name, value, tags)

    def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录仪表盘指标"""
        self.gauges[name] = value
        self._record_metric(name, value, tags)

    def record_timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        """记录计时器指标"""
        self.timers[name].append(duration)
        self._record_metric(name, duration, tags)

    def _record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录指标数据点"""
        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            tags=tags or {}
        )
        self.metrics[name].append(point)

    def get_metrics_summary(self, name: str, duration_minutes: int = 5) -> Dict:
        """获取指标摘要"""
        if name not in self.metrics:
            return {}

        cutoff_time = time.time() - (duration_minutes * 60)
        recent_points = [p for p in self.metrics[name] if p.timestamp >= cutoff_time]

        if not recent_points:
            return {}

        values = [p.value for p in recent_points]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "median": statistics.median(values),
            "sum": sum(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
            "recent_value": values[-1] if values else None,
            "trend": self._calculate_trend(values) if len(values) > 1 else 0
        }

    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return "stable"

        # 简单的线性回归计算趋势
        x = list(range(len(values)))
        n = len(values)

        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)

        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"


class CachePerformanceAnalyzer:
    """缓存性能分析器"""

    def __init__(self, metrics_collector: CacheMetricsCollector):
        self.metrics_collector = metrics_collector
        self.analysis_rules = self._init_analysis_rules()
        self.recommendations = []

    def _init_analysis_rules(self) -> List[Dict]:
        """初始化分析规则"""
        return [
            {
                "name": "low_hit_rate",
                "metric": "cache.overall_hit_rate",
                "condition": "<",
                "threshold": 0.7,
                "severity": AlertSeverity.HIGH,
                "message": "Cache hit rate is too low",
                "recommendation": "Review caching strategy and TTL settings"
            },
            {
                "name": "high_memory_usage",
                "metric": "cache.l1.total_size_bytes",
                "condition": ">",
                "threshold": 100 * 1024 * 1024,  # 100MB
                "severity": AlertSeverity.MEDIUM,
                "message": "L1 cache memory usage is high",
                "recommendation": "Consider increasing L1 cache size or optimizing eviction policy"
            },
            {
                "name": "slow_response_time",
                "metric": "cache.get_duration",
                "condition": ">",
                "threshold": 0.1,  # 100ms
                "severity": AlertSeverity.HIGH,
                "message": "Cache response time is slow",
                "recommendation": "Check Redis performance and network connectivity"
            },
            {
                "name": "high_miss_rate",
                "metric": "cache.misses",
                "condition": ">",
                "threshold": 1000,  # 1000 misses in collection period
                "severity": AlertSeverity.MEDIUM,
                "message": "High cache miss rate",
                "recommendation": "Review cache keys and implement better caching strategy"
            },
            {
                "name": "redis_memory_high",
                "metric": "cache.l2.used_memory",
                "condition": ">",
                "threshold": 512 * 1024 * 1024,  # 512MB
                "severity": AlertSeverity.MEDIUM,
                "message": "Redis memory usage is high",
                "recommendation": "Consider Redis memory optimization or upgrade"
            }
        ]

    async def analyze_performance(self) -> Dict:
        """分析性能并生成报告"""
        analysis = {
            "timestamp": time.time(),
            "overall_score": 0,
            "alerts": [],
            "recommendations": [],
            "metrics_summary": {},
            "trends": {}
        }

        total_score = 0
        rule_count = len(self.analysis_rules)

        for rule in self.analysis_rules:
            metric_name = rule["metric"]
            metric_summary = self.metrics_collector.get_metrics_summary(metric_name, 5)

            if not metric_summary:
                continue

            analysis["metrics_summary"][metric_name] = metric_summary

            # 应用规则
            alert = self._evaluate_rule(rule, metric_summary)
            if alert:
                analysis["alerts"].append(alert)
                # 计算分数影响
                score_impact = self._calculate_score_impact(rule, alert)
                total_score += score_impact

                # 添加推荐
                recommendation = self._generate_recommendation(rule, alert, metric_summary)
                if recommendation:
                    analysis["recommendations"].append(recommendation)

        # 计算总体分数
        analysis["overall_score"] = max(0, 100 - total_score)

        # 分析趋势
        analysis["trends"] = self._analyze_trends()

        return analysis

    def _evaluate_rule(self, rule: Dict, metric_summary: Dict) -> Optional[PerformanceAlert]:
        """评估规则并生成告警"""
        recent_value = metric_summary.get("recent_value")
        if recent_value is None:
            return None

        threshold = rule["threshold"]
        condition = rule["condition"]

        triggered = False
        if condition == ">" and recent_value > threshold:
            triggered = True
        elif condition == "<" and recent_value < threshold:
            triggered = True
        elif condition == ">=" and recent_value >= threshold:
            triggered = True
        elif condition == "<=" and recent_value <= threshold:
            triggered = True

        if triggered:
            alert_id = f"{rule['name']}_{int(time.time())}"
            return PerformanceAlert(
                id=alert_id,
                metric_name=rule["metric"],
                severity=rule["severity"],
                message=rule["message"],
                threshold_value=threshold,
                actual_value=recent_value,
                timestamp=time.time()
            )

        return None

    def _calculate_score_impact(self, rule: Dict, alert: PerformanceAlert) -> float:
        """计算告警对分数的影响"""
        severity_impacts = {
            AlertSeverity.LOW: 5,
            AlertSeverity.MEDIUM: 15,
            AlertSeverity.HIGH: 25,
            AlertSeverity.CRITICAL: 40
        }

        base_impact = severity_impacts.get(alert.severity, 10)

        # 根据偏离程度调整影响
        deviation_factor = abs(alert.actual_value - alert.threshold_value) / max(1, abs(alert.threshold_value))
        adjusted_impact = base_impact * min(2.0, deviation_factor)

        return adjusted_impact

    def _generate_recommendation(self, rule: Dict, alert: PerformanceAlert,
                              metric_summary: Dict) -> Optional[Dict]:
        """生成优化建议"""
        base_recommendation = rule.get("recommendation", "")

        # 根据具体指标添加详细建议
        if "hit_rate" in rule["metric"]:
            hit_rate = metric_summary.get("recent_value", 0)
            if hit_rate < 0.5:
                return {
                    "type": "caching_strategy",
                    "priority": "high",
                    "title": "Improve Caching Strategy",
                    "description": base_recommendation,
                    "actions": [
                        "Review cache key patterns",
                        "Adjust TTL values",
                        "Implement cache warming for frequently accessed data",
                        "Consider multi-level caching"
                    ]
                }

        elif "memory" in rule["metric"]:
            return {
                "type": "resource_optimization",
                "priority": "medium",
                "title": "Optimize Memory Usage",
                "description": base_recommendation,
                "actions": [
                    "Review cache eviction policy",
                    "Increase cache size if needed",
                    "Implement cache compression",
                    "Monitor memory growth patterns"
                ]
            }

        elif "response_time" in rule["metric"] or "duration" in rule["metric"]:
            return {
                "type": "performance_optimization",
                "priority": "high",
                "title": "Improve Response Time",
                "description": base_recommendation,
                "actions": [
                    "Check network latency to Redis",
                    "Optimize cache key lookup",
                    "Review cache connection pooling",
                    "Consider Redis clustering"
                ]
            }

        return {
            "type": "general",
            "priority": "medium",
            "title": "General Optimization",
            "description": base_recommendation,
            "actions": ["Review system performance metrics"]
        }

    def _analyze_trends(self) -> Dict[str, str]:
        """分析趋势"""
        trends = {}
        metric_names = [
            "cache.overall_hit_rate",
            "cache.l1.total_size_bytes",
            "cache.l2.used_memory",
            "cache.total_requests"
        ]

        for metric_name in metric_names:
            summary = self.metrics_collector.get_metrics_summary(metric_name, 30)  # 30分钟
            if summary:
                trends[metric_name] = summary.get("trend", "stable")

        return trends


class CacheMonitoringSystem:
    """缓存监控系统"""

    def __init__(self):
        self.metrics_collector = CacheMetricsCollector()
        self.performance_analyzer = CachePerformanceAnalyzer(self.metrics_collector)
        self.alert_handlers: List[Callable] = []
        self.alert_history: List[PerformanceAlert] = []
        self.monitoring_active = False

        # 配置
        self.analysis_interval = 300  # 5分钟分析一次
        self.max_alert_history = 1000

    async def start_monitoring(self):
        """开始监控"""
        if self.monitoring_active:
            return

        await self.metrics_collector.start_collection()
        self.monitoring_active = True

        # 启动定期分析
        asyncio.create_task(self._periodic_analysis())

        logger.info("Cache monitoring system started")

    async def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
        await self.metrics_collector.stop_collection()
        logger.info("Cache monitoring system stopped")

    async def _periodic_analysis(self):
        """定期性能分析"""
        while self.monitoring_active:
            try:
                analysis = await self.performance_analyzer.analyze_performance()

                # 处理告警
                await self._handle_alerts(analysis.get("alerts", []))

                # 记录分析结果
                logger.info(f"Performance analysis completed. Score: {analysis.get('overall_score', 0):.1f}")

                await asyncio.sleep(self.analysis_interval)

            except Exception as e:
                logger.error(f"Error in periodic analysis: {e}")
                await asyncio.sleep(60)

    async def _handle_alerts(self, alerts: List[PerformanceAlert]):
        """处理告警"""
        for alert in alerts:
            # 检查是否为重复告警
            if self._is_duplicate_alert(alert):
                continue

            self.alert_history.append(alert)

            # 限制历史记录数量
            if len(self.alert_history) > self.max_alert_history:
                self.alert_history.pop(0)

            # 调用告警处理器
            await self._notify_alert_handlers(alert)

            logger.warning(f"Cache performance alert: {alert.message} "
                         f"({alert.actual_value} {alert.threshold_value})")

    def _is_duplicate_alert(self, new_alert: PerformanceAlert) -> bool:
        """检查是否为重复告警"""
        for existing_alert in self.alert_history[-10:]:  # 检查最近10个告警
            if (existing_alert.metric_name == new_alert.metric_name and
                existing_alert.severity == new_alert.severity and
                not existing_alert.resolved and
                new_alert.timestamp - existing_alert.timestamp < 300):  # 5分钟内
                return True
        return False

    async def _notify_alert_handlers(self, alert: PerformanceAlert):
        """通知告警处理器"""
        for handler in self.alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")

    def add_alert_handler(self, handler: Callable):
        """添加告警处理器"""
        self.alert_handlers.append(handler)

    async def record_cache_operation(self, operation: str, level: str, duration: float,
                                 hit: bool = None, key_size: int = 0):
        """记录缓存操作"""
        # 记录操作计数
        self.metrics_collector.record_counter(f"cache.{operation}.{level}")

        # 记录耗时
        if duration > 0:
            self.metrics_collector.record_timer(f"cache.{operation}_duration.{level}", duration)

        # 记录命中状态
        if hit is not None:
            hit_value = 1 if hit else 0
            self.metrics_collector.record_counter(f"cache.{operation}_hit.{level}", hit_value)
            self.metrics_collector.record_counter(f"cache.{operation}_miss.{level}", 1 - hit_value)

        # 记录键大小
        if key_size > 0:
            self.metrics_collector.record_gauge(f"cache.{operation}_key_size.{level}", key_size)

    async def get_monitoring_dashboard(self) -> Dict:
        """获取监控仪表盘数据"""
        current_time = time.time()

        # 获取关键指标的实时数据
        key_metrics = {}
        metric_names = [
            "cache.overall_hit_rate",
            "cache.l1.hit_rate",
            "cache.l2.hit_rate",
            "cache.total_requests",
            "cache.l1.total_size_bytes",
            "cache.l2.used_memory"
        ]

        for metric_name in metric_names:
            summary = self.metrics_collector.get_metrics_summary(metric_name, 5)
            if summary:
                key_metrics[metric_name] = summary["recent_value"]

        # 获取最近的性能分析
        recent_analysis = await self.performance_analyzer.analyze_performance()

        # 获取活跃告警
        active_alerts = [alert for alert in self.alert_history if not alert.resolved][-10:]

        return {
            "timestamp": current_time,
            "key_metrics": key_metrics,
            "performance_score": recent_analysis.get("overall_score", 0),
            "active_alerts": len(active_alerts),
            "recent_alerts": [alert.to_dict() for alert in active_alerts],
            "recommendations": recent_analysis.get("recommendations", [])[:5],
            "trends": recent_analysis.get("trends", {}),
            "monitoring_active": self.monitoring_active
        }

    async def get_detailed_metrics(self, metric_name: str = None,
                                duration_minutes: int = 60) -> Dict:
        """获取详细指标数据"""
        if metric_name:
            summary = self.metrics_collector.get_metrics_summary(metric_name, duration_minutes)
            return {metric_name: summary}
        else:
            # 返回所有指标摘要
            all_metrics = {}
            for name in list(self.metrics_collector.metrics.keys())[:20]:  # 限制数量
                summary = self.metrics_collector.get_metrics_summary(name, duration_minutes)
                if summary:
                    all_metrics[name] = summary
            return all_metrics

    async def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        for alert in self.alert_history:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = time.time()
                logger.info(f"Resolved cache alert: {alert_id}")
                return True
        return False

    async def get_alert_history(self, limit: int = 50) -> List[Dict]:
        """获取告警历史"""
        alerts = sorted(self.alert_history, key=lambda x: x.timestamp, reverse=True)
        return [alert.to_dict() for alert in alerts[:limit]]


# 全局监控系统实例
_monitoring_system: Optional[CacheMonitoringSystem] = None


async def get_monitoring_system() -> CacheMonitoringSystem:
    """获取全局监控系统实例"""
    global _monitoring_system
    if _monitoring_system is None:
        _monitoring_system = CacheMonitoringSystem()
    return _monitoring_system


# 便捷函数
async def record_cache_operation(operation: str, level: str, duration: float,
                              hit: bool = None, key_size: int = 0):
    """记录缓存操作"""
    system = await get_monitoring_system()
    await system.record_cache_operation(operation, level, duration, hit, key_size)


async def get_cache_dashboard() -> Dict:
    """获取缓存监控仪表盘"""
    system = await get_monitoring_system()
    return await system.get_monitoring_dashboard()


# 默认告警处理器
async def log_alert_handler(alert: PerformanceAlert):
    """日志告警处理器"""
    logger.warning(f"Cache Alert [{alert.severity.value.upper()}]: {alert.message}")
    logger.warning(f"  Metric: {alert.metric_name}")
    logger.warning(f"  Threshold: {alert.threshold_value}, Actual: {alert.actual_value}")