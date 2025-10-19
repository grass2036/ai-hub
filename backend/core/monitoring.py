"""
System Monitoring and Logging
Week 4 Day 26: Performance Optimization and Security Hardening
"""

import os
import sys
import json
import time
import psutil
import logging
import asyncio
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import redis.asyncio as redis

from backend.config.settings import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@dataclass
class MetricsData:
    """指标数据"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str]
    unit: str = "count"


@dataclass
class AlertData:
    """告警数据"""
    alert_id: str
    alert_type: str
    severity: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.redis_client: Optional[redis.Redis] = None

    async def initialize(self):
        """初始化Redis连接"""
        try:
            settings = get_settings()
            self.redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Metrics Redis connection established")
        except Exception as e:
            logger.warning(f"Redis not available for metrics: {e}")
            self.redis_client = None

    def increment_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """增加计数器"""
        key = self._make_key(name, tags)
        self.counters[key] += value
        self._record_metric(name, value, tags or {}, "counter")

    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """设置仪表值"""
        key = self._make_key(name, tags)
        self.gauges[key] = value
        self._record_metric(name, value, tags or {}, "gauge")

    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录直方图数据"""
        key = self._make_key(name, tags)
        self.histograms[key].append(value)
        # 保持最近1000个值
        if len(self.histograms[key]) > 1000:
            self.histograms[key] = self.histograms[key][-1000:]
        self._record_metric(name, value, tags or {}, "histogram")

    def _make_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """生成指标键"""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{tag_str}}}"

    def _record_metric(self, name: str, value: float, tags: Dict[str, str], metric_type: str):
        """记录指标"""
        metric = MetricsData(
            timestamp=datetime.utcnow(),
            metric_name=name,
            value=value,
            tags=tags,
            unit=metric_type
        )
        self.metrics[name].append(metric)

        # 异步发送到Redis
        if self.redis_client:
            asyncio.create_task(self._send_to_redis(metric))

    async def _send_to_redis(self, metric: MetricsData):
        """发送指标到Redis"""
        try:
            key = f"metrics:{metric.metric_name}"
            data = {
                "timestamp": metric.timestamp.isoformat(),
                "value": metric.value,
                "tags": metric.tags,
                "unit": metric.unit
            }
            await self.redis_client.lpush(key, json.dumps(data))
            # 保持最近1000个记录
            await self.redis_client.ltrim(key, 0, 999)
        except Exception as e:
            logger.error(f"Failed to send metric to Redis: {e}")

    def get_metric_summary(self, name: str, minutes: int = 5) -> Dict[str, Any]:
        """获取指标摘要"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self.metrics[name]
            if m.timestamp >= cutoff_time
        ]

        if not recent_metrics:
            return {"count": 0}

        values = [m.value for m in recent_metrics]
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "latest": values[-1] if values else 0
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {
                key: {
                    "count": len(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values) if values else 0
                }
                for key, values in self.histograms.items()
            }
        }


class SystemMonitor:
    """系统监控器"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None

    async def start_monitoring(self, interval: int = 30):
        """开始监控"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("System monitoring started")

    async def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("System monitoring stopped")

    async def _monitor_loop(self, interval: int):
        """监控循环"""
        while self.monitoring:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(interval)

    async def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU指标
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics_collector.set_gauge("system_cpu_percent", cpu_percent)

            # 内存指标
            memory = psutil.virtual_memory()
            self.metrics_collector.set_gauge("system_memory_percent", memory.percent)
            self.metrics_collector.set_gauge("system_memory_used_mb", memory.used / 1024 / 1024)
            self.metrics_collector.set_gauge("system_memory_available_mb", memory.available / 1024 / 1024)

            # 磁盘指标
            disk = psutil.disk_usage('/')
            self.metrics_collector.set_gauge("system_disk_percent", disk.percent)
            self.metrics_collector.set_gauge("system_disk_used_gb", disk.used / 1024 / 1024 / 1024)
            self.metrics_collector.set_gauge("system_disk_free_gb", disk.free / 1024 / 1024 / 1024)

            # 网络指标
            network = psutil.net_io_counters()
            self.metrics_collector.set_gauge("system_network_bytes_sent", network.bytes_sent)
            self.metrics_collector.set_gauge("system_network_bytes_recv", network.bytes_recv)

            # 进程指标
            process = psutil.Process()
            self.metrics_collector.set_gauge("process_memory_mb", process.memory_info().rss / 1024 / 1024)
            self.metrics_collector.set_gauge("process_cpu_percent", process.cpu_percent())
            self.metrics_collector.set_gauge("process_threads", process.num_threads())
            self.metrics_collector.set_gauge("process_fds", process.num_fds())

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")


class AlertManager:
    """告警管理器"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alerts: Dict[str, AlertData] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.alert_callbacks: List[Callable] = []
        self.redis_client: Optional[redis.Redis] = None

    async def initialize(self):
        """初始化告警管理器"""
        try:
            settings = get_settings()
            self.redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Alert Redis connection established")
        except Exception as e:
            logger.warning(f"Redis not available for alerts: {e}")

        # 设置默认告警规则
        self._setup_default_rules()

    def _setup_default_rules(self):
        """设置默认告警规则"""
        self.alert_rules = [
            {
                "name": "high_cpu_usage",
                "metric": "system_cpu_percent",
                "condition": "gt",
                "threshold": 80,
                "duration": 300,  # 5分钟
                "severity": "warning",
                "message": "CPU使用率过高: {value}%"
            },
            {
                "name": "high_memory_usage",
                "metric": "system_memory_percent",
                "condition": "gt",
                "threshold": 85,
                "duration": 300,
                "severity": "warning",
                "message": "内存使用率过高: {value}%"
            },
            {
                "name": "high_disk_usage",
                "metric": "system_disk_percent",
                "condition": "gt",
                "threshold": 90,
                "duration": 600,  # 10分钟
                "severity": "critical",
                "message": "磁盘使用率过高: {value}%"
            },
            {
                "name": "process_memory_high",
                "metric": "process_memory_mb",
                "condition": "gt",
                "threshold": 1024,  # 1GB
                "duration": 300,
                "severity": "warning",
                "message": "进程内存使用过高: {value}MB"
            }
        ]

    def add_alert_rule(self, rule: Dict[str, Any]):
        """添加告警规则"""
        self.alert_rules.append(rule)

    async def check_alerts(self):
        """检查告警"""
        current_time = datetime.utcnow()

        for rule in self.alert_rules:
            try:
                await self._check_rule(rule, current_time)
            except Exception as e:
                logger.error(f"Error checking alert rule {rule['name']}: {e}")

    async def _check_rule(self, rule: Dict[str, Any], current_time: datetime):
        """检查单个告警规则"""
        metric_name = rule["metric"]
        condition = rule["condition"]
        threshold = rule["threshold"]
        duration = rule["duration"]

        # 获取指标值
        metric_summary = self.metrics_collector.get_metric_summary(
            metric_name,
            minutes=duration // 60
        )

        if metric_summary["count"] == 0:
            return

        avg_value = metric_summary["avg"]
        triggered = False

        # 检查条件
        if condition == "gt" and avg_value > threshold:
            triggered = True
        elif condition == "lt" and avg_value < threshold:
            triggered = True
        elif condition == "eq" and abs(avg_value - threshold) < 0.001:
            triggered = True

        alert_id = rule["name"]
        existing_alert = self.alerts.get(alert_id)

        if triggered and not existing_alert:
            # 创建新告警
            await self._create_alert(rule, avg_value, current_time)
        elif not triggered and existing_alert and not existing_alert.resolved:
            # 解决告警
            await self._resolve_alert(alert_id, current_time)

    async def _create_alert(self, rule: Dict[str, Any], value: float, timestamp: datetime):
        """创建告警"""
        alert_id = rule["name"]
        alert = AlertData(
            alert_id=alert_id,
            alert_type=rule["metric"],
            severity=rule["severity"],
            message=rule["message"].format(value=value),
            timestamp=timestamp
        )

        self.alerts[alert_id] = alert
        logger.warning(f"Alert created: {alert.message}")

        # 发送通知
        await self._send_notification(alert)

    async def _resolve_alert(self, alert_id: str, timestamp: datetime):
        """解决告警"""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            self.alerts[alert_id].resolved_at = timestamp
            logger.info(f"Alert resolved: {alert_id}")

    async def _send_notification(self, alert: AlertData):
        """发送告警通知"""
        # 调用注册的回调函数
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Alert notification callback error: {e}")

        # 发送到Redis (用于外部系统消费)
        if self.redis_client:
            try:
                await self.redis_client.publish(
                    "alerts",
                    json.dumps(asdict(alert), default=str)
                )
            except Exception as e:
                logger.error(f"Failed to publish alert to Redis: {e}")

    def add_alert_callback(self, callback: Callable):
        """添加告警回调函数"""
        self.alert_callbacks.append(callback)

    def get_active_alerts(self) -> List[AlertData]:
        """获取活跃告警"""
        return [alert for alert in self.alerts.values() if not alert.resolved]

    def get_all_alerts(self) -> List[AlertData]:
        """获取所有告警"""
        return list(self.alerts.values())


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector

    def monitor_function(self, metric_name: str = None, tags: Dict[str, str] = None):
        """函数性能监控装饰器"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                function_name = metric_name or f"{func.__module__}.{func.__name__}"

                try:
                    result = await func(*args, **kwargs)
                    success = True
                except Exception as e:
                    success = False
                    raise
                finally:
                    duration = time.time() - start_time

                    # 记录性能指标
                    self.metrics_collector.record_histogram(
                        f"{function_name}_duration",
                        duration,
                        {**(tags or {}), "success": str(success)}
                    )

                    # 如果执行时间过长，记录告警
                    if duration > 5.0:  # 5秒
                        logger.warning(f"Slow function: {function_name} took {duration:.2f}s")

                return result
            return wrapper
        return decorator

    @asynccontextmanager
    async def monitor_operation(self, operation_name: str, tags: Dict[str, str] = None):
        """操作性能监控上下文管理器"""
        start_time = time.time()
        try:
            yield
            success = True
        except Exception as e:
            success = False
            raise
        finally:
            duration = time.time() - start_time

            self.metrics_collector.record_histogram(
                f"{operation_name}_duration",
                duration,
                {**(tags or {}), "success": str(success)}
            )


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _log_structured(self, level: str, message: str, **kwargs):
        """记录结构化日志"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }

        if level == "error":
            self.logger.error(json.dumps(log_data))
        elif level == "warning":
            self.logger.warning(json.dumps(log_data))
        elif level == "info":
            self.logger.info(json.dumps(log_data))
        else:
            self.logger.debug(json.dumps(log_data))

    def info(self, message: str, **kwargs):
        """记录信息日志"""
        self._log_structured("info", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        self._log_structured("warning", message, **kwargs)

    def error(self, message: str, **kwargs):
        """记录错误日志"""
        self._log_structured("error", message, **kwargs)

    def debug(self, message: str, **kwargs):
        """记录调试日志"""
        self._log_structured("debug", message, **kwargs)

    def log_request(self, request_id: str, method: str, path: str,
                   status_code: int, duration: float, **kwargs):
        """记录请求日志"""
        self.info(
            "API Request",
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            duration=duration,
            **kwargs
        )

    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """记录错误日志"""
        self.error(
            "Application Error",
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            context=context or {}
        )


# 全局监控实例
metrics_collector = MetricsCollector()
system_monitor = SystemMonitor(metrics_collector)
alert_manager = AlertManager(metrics_collector)
performance_monitor = PerformanceMonitor(metrics_collector)


async def get_metrics_collector() -> MetricsCollector:
    """获取指标收集器实例"""
    await metrics_collector.initialize()
    return metrics_collector


async def get_system_monitor() -> SystemMonitor:
    """获取系统监控器实例"""
    return system_monitor


async def get_alert_manager() -> AlertManager:
    """获取告警管理器实例"""
    await alert_manager.initialize()
    return alert_manager


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器实例"""
    return performance_monitor


def get_structured_logger(name: str) -> StructuredLogger:
    """获取结构化日志记录器"""
    return StructuredLogger(name)