"""
性能监控和告警服务
Week 5 Day 3: 系统监控和运维自动化
"""

import time
import asyncio
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json
import redis
from sqlalchemy.orm import Session

from backend.config.settings import get_settings
from backend.models.developer import APIUsageRecord, DeveloperAPIKey
from backend.database import get_db
from backend.core.notification_service import (
    notification_service,
    NotificationMessage,
    NotificationChannel,
    NotificationSeverity,
    NotificationPriority
)

logger = logging.getLogger(__name__)

settings = get_settings()


class MetricType(Enum):
    """监控指标类型"""
    COUNTER = "counter"      # 计数器
    GAUGE = "gauge"          # 仪表盘
    HISTOGRAM = "histogram"  # 直方图
    TIMER = "timer"          # 计时器


class AlertSeverity(Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """监控指标数据结构"""
    name: str
    value: float
    labels: Dict[str, str]
    timestamp: datetime
    metric_type: MetricType

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat(),
            "type": self.metric_type.value
        }


@dataclass
class AlertRule:
    """告警规则"""
    id: str
    name: str
    metric_name: str
    condition: str  # gt, lt, eq, ne
    threshold: float
    severity: AlertSeverity
    duration: int  # 持续时间（秒）
    enabled: bool = True
    labels: Dict[str, str] = None

    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


@dataclass
class Alert:
    """告警事件"""
    id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    labels: Dict[str, str] = None

    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.metrics = {}
        self.counters = {}
        self.gauges = {}
        self.histograms = {}

    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """增加计数器"""
        key = self._make_key(name, labels or {})
        self.counters[key] = self.counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """设置仪表盘值"""
        key = self._make_key(name, labels or {})
        self.gauges[key] = value

    def record_timer(self, name: str, duration: float, labels: Dict[str, str] = None):
        """记录计时器"""
        key = self._make_key(name, labels or {})
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(duration)

    def _make_key(self, name: str, labels: Dict[str, str]) -> str:
        """生成指标键"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_all_metrics(self) -> List[Metric]:
        """获取所有指标"""
        metrics = []
        timestamp = datetime.utcnow()

        # 转换计数器
        for key, value in self.counters.items():
            name, labels = self._parse_key(key)
            metrics.append(Metric(name, value, labels, timestamp, MetricType.COUNTER))

        # 转换仪表盘
        for key, value in self.gauges.items():
            name, labels = self._parse_key(key)
            metrics.append(Metric(name, value, labels, timestamp, MetricType.GAUGE))

        # 转换直方图
        for key, values in self.histograms.items():
            name, labels = self._parse_key(key)
            if values:
                avg_value = sum(values) / len(values)
                metrics.append(Metric(f"{name}_avg", avg_value, labels, timestamp, MetricType.GAUGE))
                metrics.append(Metric(f"{name}_count", len(values), labels, timestamp, MetricType.COUNTER))

        return metrics

    def _parse_key(self, key: str) -> tuple[str, Dict[str, str]]:
        """解析指标键"""
        if '{' in key and '}' in key:
            name_part, labels_part = key.split('{', 1)
            name = name_part
            labels_str = labels_part.rstrip('}')
            labels = {}
            for pair in labels_str.split(','):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    labels[k] = v
            return name, labels
        return key, {}


class MonitoringService:
    """监控服务主类"""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.redis_client = None
        self._init_redis()
        self._load_default_rules()

    def _init_redis(self):
        """初始化Redis连接"""
        try:
            if settings.redis_url:
                self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
                logger.info("Redis monitoring connection established")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for monitoring: {e}")

    def _load_default_rules(self):
        """加载默认告警规则"""
        default_rules = [
            AlertRule(
                id="high_cpu_usage",
                name="CPU使用率过高",
                metric_name="system_cpu_usage",
                condition="gt",
                threshold=80.0,
                severity=AlertSeverity.WARNING,
                duration=300,
                labels={"component": "system"}
            ),
            AlertRule(
                id="high_memory_usage",
                name="内存使用率过高",
                metric_name="system_memory_usage",
                condition="gt",
                threshold=85.0,
                severity=AlertSeverity.WARNING,
                duration=300,
                labels={"component": "system"}
            ),
            AlertRule(
                id="api_error_rate",
                name="API错误率过高",
                metric_name="api_error_rate",
                condition="gt",
                threshold=5.0,
                severity=AlertSeverity.ERROR,
                duration=60,
                labels={"component": "api"}
            ),
            AlertRule(
                id="slow_response_time",
                name="API响应时间过慢",
                metric_name="api_response_time_avg",
                condition="gt",
                threshold=2000.0,
                severity=AlertSeverity.WARNING,
                duration=120,
                labels={"component": "api"}
            ),
            AlertRule(
                id="disk_space_low",
                name="磁盘空间不足",
                metric_name="system_disk_usage",
                condition="gt",
                threshold=90.0,
                severity=AlertSeverity.CRITICAL,
                duration=180,
                labels={"component": "system"}
            )
        ]

        for rule in default_rules:
            self.alert_rules[rule.id] = rule

    async def collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics_collector.set_gauge("system_cpu_usage", cpu_percent)

            # 内存使用率
            memory = psutil.virtual_memory()
            self.metrics_collector.set_gauge("system_memory_usage", memory.percent)
            self.metrics_collector.set_gauge("system_memory_used_mb", memory.used / 1024 / 1024)
            self.metrics_collector.set_gauge("system_memory_total_mb", memory.total / 1024 / 1024)

            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.metrics_collector.set_gauge("system_disk_usage", disk_percent)
            self.metrics_collector.set_gauge("system_disk_used_gb", disk.used / 1024 / 1024 / 1024)
            self.metrics_collector.set_gauge("system_disk_total_gb", disk.total / 1024 / 1024 / 1024)

            # 网络IO
            net_io = psutil.net_io_counters()
            self.metrics_collector.set_gauge("system_network_bytes_sent", net_io.bytes_sent)
            self.metrics_collector.set_gauge("system_network_bytes_recv", net_io.bytes_recv)

            # 进程数量
            process_count = len(psutil.pids())
            self.metrics_collector.set_gauge("system_process_count", process_count)

            logger.debug("System metrics collected successfully")

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")

    async def collect_api_metrics(self):
        """收集API指标"""
        try:
            db = next(get_db())

            # 统计最近5分钟的API请求
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)

            # 总请求数
            total_requests = db.query(APIUsageRecord).filter(
                APIUsageRecord.created_at >= five_minutes_ago
            ).count()
            self.metrics_collector.set_gauge("api_requests_total_5m", total_requests, {"window": "5m"})

            # 错误请求数
            error_requests = db.query(APIUsageRecord).filter(
                APIUsageRecord.created_at >= five_minutes_ago,
                APIUsageRecord.status_code >= 400
            ).count()
            self.metrics_collector.set_gauge("api_errors_total_5m", error_requests, {"window": "5m"})

            # 错误率
            error_rate = (error_requests / total_requests * 100) if total_requests > 0 else 0
            self.metrics_collector.set_gauge("api_error_rate", error_rate, {"window": "5m"})

            # 平均响应时间
            recent_records = db.query(APIUsageRecord).filter(
                APIUsageRecord.created_at >= five_minutes_ago,
                APIUsageRecord.response_time_ms.isnot(None)
            ).all()

            if recent_records:
                avg_response_time = sum(record.response_time_ms for record in recent_records) / len(recent_records)
                self.metrics_collector.set_gauge("api_response_time_avg", avg_response_time, {"window": "5m"})

                # 响应时间分布
                p95_response_time = sorted([record.response_time_ms for record in recent_records])[int(len(recent_records) * 0.95)]
                self.metrics_collector.set_gauge("api_response_time_p95", p95_response_time, {"window": "5m"})

            # 活跃API密钥数量
            active_keys = db.query(DeveloperAPIKey).filter(
                DeveloperAPIKey.is_active == True
            ).count()
            self.metrics_collector.set_gauge("api_active_keys", active_keys)

            db.close()
            logger.debug("API metrics collected successfully")

        except Exception as e:
            logger.error(f"Failed to collect API metrics: {e}")

    async def check_alerts(self):
        """检查告警规则"""
        current_metrics = {metric.name: metric for metric in self.metrics_collector.get_all_metrics()}

        for rule_id, rule in self.alert_rules.items():
            if not rule.enabled:
                continue

            metric = current_metrics.get(rule.metric_name)
            if not metric:
                continue

            should_alert = self._evaluate_condition(metric.value, rule.condition, rule.threshold)

            if should_alert:
                await self._handle_alert_trigger(rule, metric)
            else:
                await self._handle_alert_resolve(rule_id)

    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """评估告警条件"""
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "eq":
            return value == threshold
        elif condition == "ne":
            return value != threshold
        return False

    async def _handle_alert_trigger(self, rule: AlertRule, metric: Metric):
        """处理告警触发"""
        alert_key = f"{rule.id}:{rule.metric_name}"

        # 检查是否已经存在活跃告警
        if alert_key not in self.active_alerts:
            alert = Alert(
                id=f"alert_{int(time.time())}_{rule.id}",
                rule_id=rule.id,
                rule_name=rule.name,
                severity=rule.severity,
                message=f"{rule.name}: {metric.name} = {metric.value} (阈值: {rule.threshold})",
                timestamp=datetime.utcnow(),
                labels={**rule.labels, **metric.labels}
            )

            self.active_alerts[alert_key] = alert

            # 存储到Redis
            if self.redis_client:
                try:
                    self.redis_client.setex(
                        f"alert:{alert_key}",
                        3600,  # 1小时过期
                        json.dumps(asdict(alert), default=str)
                    )
                except Exception as e:
                    logger.error(f"Failed to store alert to Redis: {e}")

            # 发送通知
            await self._send_alert_notification(alert)

            logger.warning(f"Alert triggered: {alert.message}")

    async def _handle_alert_resolve(self, rule_id: str):
        """处理告警解决"""
        keys_to_remove = []

        for alert_key, alert in self.active_alerts.items():
            if alert.rule_id == rule_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()

                # 更新Redis
                if self.redis_client:
                    try:
                        self.redis_client.setex(
                            f"alert:{alert_key}",
                            3600,
                            json.dumps(asdict(alert), default=str)
                        )
                    except Exception as e:
                        logger.error(f"Failed to update resolved alert to Redis: {e}")

                keys_to_remove.append(alert_key)
                logger.info(f"Alert resolved: {alert.message}")

        for key in keys_to_remove:
            del self.active_alerts[key]

    async def _send_alert_notification(self, alert: Alert):
        """发送告警通知"""
        try:
            # 映射告警严重级别到通知严重级别
            severity_mapping = {
                AlertSeverity.INFO: NotificationSeverity.INFO,
                AlertSeverity.WARNING: NotificationSeverity.WARNING,
                AlertSeverity.ERROR: NotificationSeverity.ERROR,
                AlertSeverity.CRITICAL: NotificationSeverity.CRITICAL
            }

            # 映射告警严重级别到通知优先级
            priority_mapping = {
                AlertSeverity.INFO: NotificationPriority.LOW,
                AlertSeverity.WARNING: NotificationPriority.MEDIUM,
                AlertSeverity.ERROR: NotificationPriority.HIGH,
                AlertSeverity.CRITICAL: NotificationPriority.URGENT
            }

            notification = NotificationMessage(
                id=f"alert_{alert.id}",
                title=f"[{alert.severity.value.upper()}] {alert.rule_name}",
                content=alert.message,
                channel=NotificationChannel.IN_APP,  # 默认应用内通知
                severity=severity_mapping.get(alert.severity, NotificationSeverity.WARNING),
                priority=priority_mapping.get(alert.severity, NotificationPriority.MEDIUM),
                metadata={
                    "alert_id": alert.id,
                    "rule_id": alert.rule_id,
                    "rule_name": alert.rule_name,
                    "labels": alert.labels,
                    "resolved": alert.resolved,
                    "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
                },
                tags=["alert", "monitoring", alert.severity.value]
            )

            # 发送通知
            success = await notification_service.send_notification(notification)

            if success:
                logger.info(f"Alert notification sent successfully: {alert.rule_name}")
            else:
                logger.error(f"Failed to send alert notification: {alert.rule_name}")

        except Exception as e:
            logger.error(f"Error sending alert notification: {e}")

    async def get_metrics_history(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """获取指标历史数据"""
        if not self.redis_client:
            return []

        try:
            # 从Redis获取历史数据
            end_time = int(time.time())
            start_time = end_time - (hours * 3600)

            keys = []
            for timestamp in range(start_time, end_time, 60):  # 每分钟一个数据点
                keys.append(f"metric:{metric_name}:{timestamp}")

            if not keys:
                return []

            values = self.redis_client.mget(keys)
            history = []

            for i, value in enumerate(values):
                if value:
                    try:
                        data = json.loads(value)
                        data["timestamp"] = start_time + (i * 60)
                        history.append(data)
                    except json.JSONDecodeError:
                        continue

            return history

        except Exception as e:
            logger.error(f"Failed to get metrics history: {e}")
            return []

    async def store_metrics(self):
        """存储指标到Redis"""
        if not self.redis_client:
            return

        try:
            current_time = int(time.time())
            pipe = self.redis_client.pipeline()

            for metric in self.metrics_collector.get_all_metrics():
                key = f"metric:{metric.name}:{current_time}"
                value = json.dumps(metric.to_dict(), default=str)
                pipe.setex(key, 7 * 24 * 3600, value)  # 保留7天

            pipe.execute()

        except Exception as e:
            logger.error(f"Failed to store metrics to Redis: {e}")

    async def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())

    async def add_alert_rule(self, rule: AlertRule) -> bool:
        """添加告警规则"""
        try:
            self.alert_rules[rule.id] = rule
            logger.info(f"Alert rule added: {rule.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add alert rule: {e}")
            return False

    async def remove_alert_rule(self, rule_id: str) -> bool:
        """删除告警规则"""
        try:
            if rule_id in self.alert_rules:
                del self.alert_rules[rule_id]
                logger.info(f"Alert rule removed: {rule_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove alert rule: {e}")
            return False


# 全局监控服务实例
monitoring_service = MonitoringService()


async def start_monitoring():
    """启动监控服务"""
    logger.info("Starting monitoring service...")

    while True:
        try:
            # 收集系统指标
            await monitoring_service.collect_system_metrics()

            # 收集API指标
            await monitoring_service.collect_api_metrics()

            # 存储指标
            await monitoring_service.store_metrics()

            # 检查告警
            await monitoring_service.check_alerts()

            # 等待下一次收集（60秒）
            await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            await asyncio.sleep(60)


# 性能监控装饰器
def monitor_performance(operation_name: str = None):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            operation = operation_name or f"{func.__module__}.{func.__name__}"

            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = (time.time() - start_time) * 1000  # 转换为毫秒

                # 记录性能指标
                monitoring_service.metrics_collector.record_timer(
                    f"operation_duration_ms",
                    duration,
                    {"operation": operation, "success": str(success)}
                )

                # 记录操作计数
                monitoring_service.metrics_collector.increment_counter(
                    f"operation_total",
                    1.0,
                    {"operation": operation, "success": str(success)}
                )

        return wrapper
    return decorator