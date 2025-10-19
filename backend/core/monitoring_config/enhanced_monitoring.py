"""
增强的生产环境监控系统
Week 6 Day 4: 系统监控和日志配置

提供全面的系统、应用和业务指标监控
"""

import asyncio
import time
import psutil
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import logging
import redis
import aiofiles
from prometheus_client import CollectorRegistry, Gauge, Counter, Histogram, generate_latest

class MetricType(Enum):
    """指标类型枚举"""
    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

@dataclass
class MetricDefinition:
    """指标定义"""
    name: str
    description: str
    metric_type: MetricType
    labels: List[str] = None
    unit: str = ""
    thresholds: Dict[str, float] = None

@dataclass
class SystemMetrics:
    """系统指标数据"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    process_count: int
    load_average: List[float]
    uptime: float

@dataclass
class ApplicationMetrics:
    """应用指标数据"""
    timestamp: datetime
    request_count: int
    error_count: int
    response_time_avg: float
    response_time_p95: float
    active_connections: int
    database_connections: int
    cache_hit_rate: float
    queue_size: int

@dataclass
class BusinessMetrics:
    """业务指标数据"""
    timestamp: datetime
    active_users: int
    total_requests: int
    api_revenue: float
    conversion_rate: float
    user_satisfaction: float
    service_availability: float

class CustomMetricsRegistry:
    """自定义指标注册器"""

    def __init__(self):
        self.metrics: Dict[str, Any] = {}
        self.collectors: List[Callable] = []
        self.registry = CollectorRegistry()

    def register_metric(self, definition: MetricDefinition) -> bool:
        """注册指标"""
        try:
            if definition.metric_type == MetricType.GAUGE:
                metric = Gauge(
                    definition.name,
                    definition.description,
                    definition.labels or [],
                    registry=self.registry
                )
            elif definition.metric_type == MetricType.COUNTER:
                metric = Counter(
                    definition.name,
                    definition.description,
                    definition.labels or [],
                    registry=self.registry
                )
            elif definition.metric_type == MetricType.HISTOGRAM:
                metric = Histogram(
                    definition.name,
                    definition.description,
                    definition.labels or [],
                    registry=self.registry
                )
            else:
                raise ValueError(f"Unsupported metric type: {definition.metric_type}")

            self.metrics[definition.name] = {
                'definition': definition,
                'metric': metric,
                'values': defaultdict(float)
            }

            return True

        except Exception as e:
            logging.error(f"Failed to register metric {definition.name}: {str(e)}")
            return False

    def update_metric(self, name: str, value: float, labels: Dict[str, str] = None) -> bool:
        """更新指标值"""
        if name not in self.metrics:
            return False

        try:
            metric_info = self.metrics[name]
            metric = metric_info['metric']

            if labels:
                metric.labels(**labels).set(value)
            else:
                metric.set(value)

            # 记录历史值
            labels_key = json.dumps(labels or {}, sort_keys=True)
            metric_info['values'][labels_key] = value

            return True

        except Exception as e:
            logging.error(f"Failed to update metric {name}: {str(e)}")
            return False

    def increment_metric(self, name: str, value: float = 1, labels: Dict[str, str] = None) -> bool:
        """递增计数器指标"""
        if name not in self.metrics:
            return False

        try:
            metric_info = self.metrics[name]
            metric = metric_info['metric']

            if labels:
                metric.labels(**labels).inc(value)
            else:
                metric.inc(value)

            return True

        except Exception as e:
            logging.error(f"Failed to increment metric {name}: {str(e)}")
            return False

    def observe_metric(self, name: str, value: float, labels: Dict[str, str] = None) -> bool:
        """观察直方图指标"""
        if name not in self.metrics:
            return False

        try:
            metric_info = self.metrics[name]
            metric = metric_info['metric']

            if labels:
                metric.labels(**labels).observe(value)
            else:
                metric.observe(value)

            return True

        except Exception as e:
            logging.error(f"Failed to observe metric {name}: {str(e)}")
            return False

    def get_metrics_as_json(self) -> str:
        """获取指标JSON格式数据"""
        return generate_latest(self.registry).decode('utf-8')

    def get_metric_history(self, name: str, labels: Dict[str, str] = None) -> Dict[str, float]:
        """获取指标历史数据"""
        if name not in self.metrics:
            return {}

        labels_key = json.dumps(labels or {}, sort_keys=True)
        return dict(self.metrics[name]['values'][labels_key])

class SystemMonitor:
    """系统监控器"""

    def __init__(self, update_interval: int = 30):
        self.update_interval = update_interval
        self.metrics_history = deque(maxlen=1000)
        self.alerts = []
        self.is_running = False
        self._monitor_thread = None

        # 系统指标定义
        self.metric_definitions = [
            MetricDefinition(
                "system_cpu_usage",
                "System CPU usage percentage",
                MetricType.GAUGE,
                unit="percent",
                thresholds={"warning": 70, "critical": 90}
            ),
            MetricDefinition(
                "system_memory_usage",
                "System memory usage percentage",
                MetricType.GAUGE,
                unit="percent",
                thresholds={"warning": 80, "critical": 95}
            ),
            MetricDefinition(
                "system_disk_usage",
                "System disk usage percentage",
                MetricType.GAUGE,
                unit="percent",
                thresholds={"warning": 85, "critical": 95}
            ),
            MetricDefinition(
                "system_network_io",
                "System network I/O bytes",
                MetricType.GAUGE,
                labels=["direction", "interface"],
                unit="bytes"
            )
        ]

    async def collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)

            # 内存使用率
            memory = psutil.virtual_memory()
            memory_usage = memory.percent

            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100

            # 网络I/O
            net_io = psutil.net_io_counters()
            network_io = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }

            # 进程数量
            process_count = len(psutil.pids())

            # 负载平均值
            load_avg = list(psutil.getloadavg())

            # 系统运行时间
            uptime = time.time() - psutil.boot_time()

            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io=network_io,
                process_count=process_count,
                load_average=load_avg,
                uptime=uptime
            )

            return metrics

        except Exception as e:
            logging.error(f"Failed to collect system metrics: {str(e)}")
            raise

    def check_thresholds(self, metrics: SystemMetrics) -> List[Dict]:
        """检查阈值告警"""
        alerts = []

        for definition in self.metric_definitions:
            if definition.thresholds:
                value = getattr(metrics, definition.name.split('_', 1)[1], None)

                if value is not None:
                    if value >= definition.thresholds.get("critical", 100):
                        alerts.append({
                            "level": "critical",
                            "metric": definition.name,
                            "value": value,
                            "threshold": definition.thresholds["critical"],
                            "timestamp": datetime.now(),
                            "message": f"Critical: {definition.name} is {value:.2f}%"
                        })
                    elif value >= definition.thresholds.get("warning", 100):
                        alerts.append({
                            "level": "warning",
                            "metric": definition.name,
                            "value": value,
                            "threshold": definition.thresholds["warning"],
                            "timestamp": datetime.now(),
                            "message": f"Warning: {definition.name} is {value:.2f}%"
                        })

        return alerts

    def start_monitoring(self) -> None:
        """启动监控"""
        if self.is_running:
            return

        self.is_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logging.info("System monitoring started")

    def stop_monitoring(self) -> None:
        """停止监控"""
        self.is_running = False
        if self._monitor_thread:
            self._monitor_thread.join()
        logging.info("System monitoring stopped")

    def _monitor_loop(self) -> None:
        """监控循环"""
        while self.is_running:
            try:
                # 收集指标
                metrics = asyncio.run(self.collect_system_metrics())
                self.metrics_history.append(metrics)

                # 检查告警
                new_alerts = self.check_thresholds(metrics)
                self.alerts.extend(new_alerts)

                # 只保留最近100个告警
                if len(self.alerts) > 100:
                    self.alerts = self.alerts[-100:]

                time.sleep(self.update_interval)

            except Exception as e:
                logging.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(self.update_interval)

    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """获取当前指标"""
        return self.metrics_history[-1] if self.metrics_history else None

    def get_metrics_history(self, minutes: int = 60) -> List[SystemMetrics]:
        """获取历史指标"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [m for m in self.metrics_history if m.timestamp >= cutoff_time]

class ProductionMonitor:
    """生产环境监控管理器"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.system_monitor = SystemMonitor()
        self.custom_metrics = CustomMetricsRegistry()
        self.is_initialized = False

        # 应用指标定义
        self._setup_application_metrics()

        # 业务指标定义
        self._setup_business_metrics()

    def _setup_application_metrics(self) -> None:
        """设置应用指标"""
        app_metrics = [
            MetricDefinition(
                "http_requests_total",
                "Total HTTP requests",
                MetricType.COUNTER,
                labels=["method", "endpoint", "status"]
            ),
            MetricDefinition(
                "http_request_duration_seconds",
                "HTTP request duration",
                MetricType.HISTOGRAM,
                labels=["method", "endpoint"]
            ),
            MetricDefinition(
                "active_connections_total",
                "Active connections",
                MetricType.GAUGE
            ),
            MetricDefinition(
                "database_connections_active",
                "Active database connections",
                MetricType.GAUGE
            ),
            MetricDefinition(
                "cache_hit_rate",
                "Cache hit rate",
                MetricType.GAUGE,
                unit="percent"
            ),
            MetricDefinition(
                "error_rate",
                "Error rate",
                MetricType.GAUGE,
                unit="percent"
            )
        ]

        for metric_def in app_metrics:
            self.custom_metrics.register_metric(metric_def)

    def _setup_business_metrics(self) -> None:
        """设置业务指标"""
        business_metrics = [
            MetricDefinition(
                "active_users_total",
                "Total active users",
                MetricType.GAUGE
            ),
            MetricDefinition(
                "api_revenue_total",
                "Total API revenue",
                MetricType.GAUGE,
                unit="dollars"
            ),
            MetricDefinition(
                "user_satisfaction_score",
                "User satisfaction score",
                MetricType.GAUGE,
                unit="score"
            ),
            MetricDefinition(
                "service_availability",
                "Service availability",
                MetricType.GAUGE,
                unit="percent"
            )
        ]

        for metric_def in business_metrics:
            self.custom_metrics.register_metric(metric_def)

    async def initialize(self) -> None:
        """初始化监控系统"""
        if self.is_initialized:
            return

        try:
            # 启动系统监控
            self.system_monitor.start_monitoring()

            # 设置Redis连接（如果提供）
            if self.redis_client:
                await self._setup_redis_metrics()

            self.is_initialized = True
            logging.info("Production monitoring system initialized")

        except Exception as e:
            logging.error(f"Failed to initialize monitoring: {str(e)}")
            raise

    async def _setup_redis_metrics(self) -> None:
        """设置Redis指标收集"""
        try:
            # Redis信息
            info = self.redis_client.info()

            # 内存使用
            self.custom_metrics.update_metric(
                "redis_memory_usage",
                info.get("used_memory", 0),
                {"instance": "main"}
            )

            # 连接数
            self.custom_metrics.update_metric(
                "redis_connected_clients",
                info.get("connected_clients", 0),
                {"instance": "main"}
            )

            # 命令执行数
            self.custom_metrics.update_metric(
                "redis_total_commands_processed",
                info.get("total_commands_processed", 0),
                {"instance": "main"}
            )

        except Exception as e:
            logging.error(f"Failed to setup Redis metrics: {str(e)}")

    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float) -> None:
        """记录HTTP请求指标"""
        # 请求计数
        self.custom_metrics.increment_metric(
            "http_requests_total",
            labels={
                "method": method,
                "endpoint": endpoint,
                "status": str(status_code)
            }
        )

        # 请求耗时
        self.custom_metrics.observe_metric(
            "http_request_duration_seconds",
            duration,
            labels={
                "method": method,
                "endpoint": endpoint
            }
        )

        # 错误率计算
        if status_code >= 400:
            self.custom_metrics.increment_metric(
                "http_errors_total",
                labels={
                    "method": method,
                    "endpoint": endpoint,
                    "status": str(status_code)
                }
            )

    def update_active_connections(self, count: int) -> None:
        """更新活跃连接数"""
        self.custom_metrics.update_metric("active_connections_total", count)

    def update_database_connections(self, count: int) -> None:
        """更新数据库连接数"""
        self.custom_metrics.update_metric("database_connections_active", count)

    def update_cache_hit_rate(self, rate: float) -> None:
        """更新缓存命中率"""
        self.custom_metrics.update_metric("cache_hit_rate", rate)

    def update_business_metrics(self, metrics: BusinessMetrics) -> None:
        """更新业务指标"""
        self.custom_metrics.update_metric("active_users_total", metrics.active_users)
        self.custom_metrics.update_metric("api_revenue_total", metrics.api_revenue)
        self.custom_metrics.update_metric("user_satisfaction_score", metrics.user_satisfaction)
        self.custom_metrics.update_metric("service_availability", metrics.service_availability)

    async def collect_all_metrics(self) -> Dict[str, Any]:
        """收集所有指标"""
        try:
            # 系统指标
            system_metrics = self.system_monitor.get_current_metrics()

            # 自定义指标
            custom_metrics_json = self.custom_metrics.get_metrics_as_json()

            # 告警信息
            alerts = self.system_monitor.alerts

            return {
                "timestamp": datetime.now().isoformat(),
                "system_metrics": asdict(system_metrics) if system_metrics else None,
                "custom_metrics": custom_metrics_json,
                "alerts": [asdict(alert) for alert in alerts[-10:]],  # 最近10个告警
                "monitoring_status": {
                    "system_monitor_active": self.system_monitor.is_running,
                    "custom_metrics_count": len(self.custom_metrics.metrics)
                }
            }

        except Exception as e:
            logging.error(f"Failed to collect metrics: {str(e)}")
            return {"error": str(e)}

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        try:
            # 系统指标历史
            system_history = self.system_monitor.get_metrics_history(60)  # 最近1小时

            # 当前状态
            current_system = self.system_monitor.get_current_metrics()

            # 告警统计
            recent_alerts = self.system_monitor.alerts[-20:]  # 最近20个告警
            critical_alerts = [a for a in recent_alerts if a["level"] == "critical"]
            warning_alerts = [a for a in recent_alerts if a["level"] == "warning"]

            return {
                "system_status": {
                    "cpu_usage": current_system.cpu_usage if current_system else 0,
                    "memory_usage": current_system.memory_usage if current_system else 0,
                    "disk_usage": current_system.disk_usage if current_system else 0,
                    "uptime": current_system.uptime if current_system else 0
                },
                "alerts_summary": {
                    "critical": len(critical_alerts),
                    "warning": len(warning_alerts),
                    "total": len(recent_alerts)
                },
                "recent_alerts": recent_alerts[:5],  # 最近5个告警
                "metrics_history": [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "cpu_usage": m.cpu_usage,
                        "memory_usage": m.memory_usage,
                        "disk_usage": m.disk_usage
                    } for m in system_history
                ]
            }

        except Exception as e:
            logging.error(f"Failed to get dashboard data: {str(e)}")
            return {"error": str(e)}

    async def cleanup(self) -> None:
        """清理资源"""
        try:
            self.system_monitor.stop_monitoring()
            logging.info("Production monitor cleaned up")
        except Exception as e:
            logging.error(f"Error during cleanup: {str(e)}")

# 监控装饰器
def monitor_performance(metric_name: str = None):
    """性能监控装饰器"""
    def decorator(func):
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # 记录成功指标
                if hasattr(async_wrapper, '_monitor'):
                    async_wrapper._monitor.custom_metrics.observe_metric(
                        metric_name or f"{func.__module__}.{func.__name__}_duration",
                        duration,
                        labels={"status": "success"}
                    )

                return result

            except Exception as e:
                duration = time.time() - start_time

                # 记录失败指标
                if hasattr(async_wrapper, '_monitor'):
                    async_wrapper._monitor.custom_metrics.observe_metric(
                        metric_name or f"{func.__module__}.{func.__name__}_duration",
                        duration,
                        labels={"status": "error"}
                    )
                    async_wrapper._monitor.custom_metrics.increment_metric(
                        f"{func.__module__}.{func.__name__}_errors",
                        labels={"error_type": type(e).__name__}
                    )

                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # 记录成功指标
                if hasattr(sync_wrapper, '_monitor'):
                    sync_wrapper._monitor.custom_metrics.observe_metric(
                        metric_name or f"{func.__module__}.{func.__name__}_duration",
                        duration,
                        labels={"status": "success"}
                    )

                return result

            except Exception as e:
                duration = time.time() - start_time

                # 记录失败指标
                if hasattr(sync_wrapper, '_monitor'):
                    sync_wrapper._monitor.custom_metrics.observe_metric(
                        metric_name or f"{func.__module__}.{func.__name__}_duration",
                        duration,
                        labels={"status": "error"}
                    )
                    sync_wrapper._monitor.custom_metrics.increment_metric(
                        f"{func.__module__}.{func.__name__}_errors",
                        labels={"error_type": type(e).__name__}
                    )

                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator