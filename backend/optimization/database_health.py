"""
数据库健康监控系统 - Database Health Monitoring System
提供全面的数据库健康状态监控、预警和诊断功能
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable, Set
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics
import psutil
import asyncpg

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text

from .read_write_split import get_read_write_engine, DatabaseNode

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"


class MetricType(Enum):
    """指标类型枚举"""
    CONNECTION = "connection"
    PERFORMANCE = "performance"
    RESOURCE = "resource"
    REPLICATION = "replication"
    STORAGE = "storage"


@dataclass
class HealthMetric:
    """健康指标"""
    name: str
    metric_type: MetricType
    value: float
    threshold_warning: float
    threshold_critical: float
    unit: str
    status: HealthStatus = HealthStatus.HEALTHY
    description: str = ""
    timestamp: float = field(default_factory=time.time)

    def calculate_status(self):
        """计算指标状态"""
        if self.value >= self.threshold_critical:
            self.status = HealthStatus.CRITICAL
        elif self.value >= self.threshold_warning:
            self.status = HealthStatus.WARNING
        else:
            self.status = HealthStatus.HEALTHY


@dataclass
class HealthAlert:
    """健康告警"""
    id: str
    node_id: str
    metric_name: str
    status: HealthStatus
    message: str
    value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    resolved_timestamp: Optional[float] = None


@dataclass
class DatabaseHealthReport:
    """数据库健康报告"""
    node_id: str
    overall_status: HealthStatus
    metrics: Dict[str, HealthMetric]
    alerts: List[HealthAlert]
    last_check: float = field(default_factory=time.time)
    uptime: float = 0.0
    version: str = ""
    connections: Dict[str, int] = field(default_factory=dict)


class DatabaseHealthMonitor:
    """数据库健康监控器"""

    def __init__(
        self,
        check_interval: int = 60,
        alert_cooldown: int = 300,
        metrics_retention_hours: int = 24,
        enable_auto_recovery: bool = True
    ):
        self.check_interval = check_interval
        self.alert_cooldown = alert_cooldown
        self.metrics_retention_hours = metrics_retention_hours
        self.enable_auto_recovery = enable_auto_recovery

        # 监控状态
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None

        # 健康数据
        self.health_reports: Dict[str, DatabaseHealthReport] = {}
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1440))  # 24小时，每分钟一个数据点
        self.active_alerts: Dict[str, HealthAlert] = {}
        self.alert_history: deque = deque(maxlen=1000)

        # 告警处理
        self.alert_handlers: List[Callable[[HealthAlert], None]] = []
        self.last_alert_time: Dict[str, float] = defaultdict(float)

        # 监控指标配置
        self._setup_metrics_config()

        logger.info("DatabaseHealthMonitor initialized")

    def _setup_metrics_config(self):
        """设置监控指标配置"""
        self.metrics_config = {
            # 连接指标
            "connection_pool_usage": {
                "type": MetricType.CONNECTION,
                "warning": 80.0,
                "critical": 95.0,
                "unit": "%",
                "description": "连接池使用率"
            },
            "active_connections": {
                "type": MetricType.CONNECTION,
                "warning": 80.0,
                "critical": 95.0,
                "unit": "%",
                "description": "活跃连接数比例"
            },
            "connection_errors": {
                "type": MetricType.CONNECTION,
                "warning": 1.0,
                "critical": 5.0,
                "unit": "errors/min",
                "description": "连接错误率"
            },

            # 性能指标
            "query_response_time": {
                "type": MetricType.PERFORMANCE,
                "warning": 1000.0,
                "critical": 5000.0,
                "unit": "ms",
                "description": "查询平均响应时间"
            },
            "slow_queries": {
                "type": MetricType.PERFORMANCE,
                "warning": 5.0,
                "critical": 20.0,
                "unit": "queries/min",
                "description": "慢查询数量"
            },
            "query_throughput": {
                "type": MetricType.PERFORMANCE,
                "warning": 100.0,
                "critical": 50.0,
                "unit": "queries/min",
                "description": "查询吞吐量"
            },
            "lock_wait_time": {
                "type": MetricType.PERFORMANCE,
                "warning": 100.0,
                "critical": 1000.0,
                "unit": "ms",
                "description": "锁等待时间"
            },

            # 资源指标
            "cpu_usage": {
                "type": MetricType.RESOURCE,
                "warning": 70.0,
                "critical": 90.0,
                "unit": "%",
                "description": "CPU使用率"
            },
            "memory_usage": {
                "type": MetricType.RESOURCE,
                "warning": 80.0,
                "critical": 95.0,
                "unit": "%",
                "description": "内存使用率"
            },
            "disk_usage": {
                "type": MetricType.RESOURCE,
                "warning": 80.0,
                "critical": 95.0,
                "unit": "%",
                "description": "磁盘使用率"
            },
            "disk_io_usage": {
                "type": MetricType.RESOURCE,
                "warning": 70.0,
                "critical": 90.0,
                "unit": "%",
                "description": "磁盘I/O使用率"
            },

            # 复制指标（仅从库）
            "replication_lag": {
                "type": MetricType.REPLICATION,
                "warning": 10.0,
                "critical": 60.0,
                "unit": "seconds",
                "description": "复制延迟"
            },
            "replication_sync": {
                "type": MetricType.REPLICATION,
                "warning": 95.0,
                "critical": 80.0,
                "unit": "%",
                "description": "复制同步率"
            },

            # 存储指标
            "table_size_growth": {
                "type": MetricType.STORAGE,
                "warning": 10.0,
                "critical": 50.0,
                "unit": "MB/hour",
                "description": "表大小增长率"
            },
            "index_usage": {
                "type": MetricType.STORAGE,
                "warning": 90.0,
                "critical": 95.0,
                "unit": "%",
                "description": "索引使用率"
            }
        }

    async def start_monitoring(self):
        """启动监控"""
        if self.is_monitoring:
            logger.warning("Health monitoring is already running")
            return

        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Database health monitoring started")

    async def stop_monitoring(self):
        """停止监控"""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Database health monitoring stopped")

    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                logger.info("Health monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Health monitoring loop error: {e}")
                await asyncio.sleep(10)  # 错误时短暂等待后继续

    async def _perform_health_checks(self):
        """执行健康检查"""
        engine = get_read_write_engine()
        if not engine:
            logger.warning("ReadWriteSplitEngine not available for health monitoring")
            return

        all_nodes = [engine.master_node] + engine.replica_nodes + engine.analytics_nodes

        for node in all_nodes:
            try:
                await self._check_node_health(node)
            except Exception as e:
                logger.error(f"Health check failed for node {node.id}: {e}")

    async def _check_node_health(self, node: DatabaseNode):
        """检查单个节点的健康状态"""
        db_engine = engine.engines.get(node.id)
        if not db_engine:
            return

        # 收集各项指标
        metrics = await self._collect_metrics(node, db_engine)

        # 计算整体健康状态
        overall_status = self._calculate_overall_status(metrics)

        # 检查告警
        alerts = await self._check_alerts(node, metrics)

        # 生成健康报告
        report = DatabaseHealthReport(
            node_id=node.id,
            overall_status=overall_status,
            metrics=metrics,
            alerts=alerts,
            last_check=time.time()
        )

        # 获取额外信息
        await self._enrich_health_report(node, db_engine, report)

        # 保存报告
        self.health_reports[node.id] = report

        # 保存指标历史
        for metric in metrics.values():
            self.metrics_history[f"{node.id}_{metric.name}"].append(metric)

        # 处理告警
        await self._handle_alerts(alerts)

        logger.debug(f"Health check completed for node {node.id}: {overall_status.value}")

    async def _collect_metrics(self, node: DatabaseNode, db_engine: AsyncEngine) -> Dict[str, HealthMetric]:
        """收集健康指标"""
        metrics = {}

        try:
            # 连接指标
            metrics.update(await self._collect_connection_metrics(node, db_engine))

            # 性能指标
            metrics.update(await self._collect_performance_metrics(db_engine))

            # 资源指标
            metrics.update(await self._collect_resource_metrics(db_engine))

            # 复制指标（仅从库）
            if node.role.value in ["replica", "analytics"]:
                metrics.update(await self._collect_replication_metrics(db_engine))

            # 存储指标
            metrics.update(await self._collect_storage_metrics(db_engine))

        except Exception as e:
            logger.error(f"Failed to collect metrics for node {node.id}: {e}")

        return metrics

    async def _collect_connection_metrics(self, node: DatabaseNode, db_engine: AsyncEngine) -> Dict[str, HealthMetric]:
        """收集连接指标"""
        metrics = {}

        try:
            # 连接池使用率
            pool = db_engine.pool
            pool_size = pool.size()
            checked_in = pool.checkedin()
            checked_out = pool.checkedout()

            pool_usage = (checked_out / pool_size) * 100 if pool_size > 0 else 0
            metrics["connection_pool_usage"] = HealthMetric(
                name="connection_pool_usage",
                metric_type=MetricType.CONNECTION,
                value=pool_usage,
                **self.metrics_config["connection_pool_usage"]
            )

            # 活跃连接数（从数据库获取）
            async with db_engine.begin() as conn:
                result = await conn.execute(text("""
                    SELECT count(*) as active_connections
                    FROM pg_stat_activity
                    WHERE state = 'active'
                """))
                active_count = result.scalar()

                max_connections = 100  # 默认值，应该从配置获取
                active_usage = (active_count / max_connections) * 100

                metrics["active_connections"] = HealthMetric(
                    name="active_connections",
                    metric_type=MetricType.CONNECTION,
                    value=active_usage,
                    **self.metrics_config["active_connections"]
                )

        except Exception as e:
            logger.error(f"Failed to collect connection metrics: {e}")

        return metrics

    async def _collect_performance_metrics(self, db_engine: AsyncEngine) -> Dict[str, HealthMetric]:
        """收集性能指标"""
        metrics = {}

        try:
            async with db_engine.begin() as conn:
                # 查询平均响应时间
                result = await conn.execute(text("""
                    SELECT
                        avg(mean_exec_time) as avg_response_time,
                        sum(calls) as total_calls
                    FROM pg_stat_statements
                    WHERE calls > 0
                """))
                row = result.first()

                if row and row.total_calls > 0:
                    metrics["query_response_time"] = HealthMetric(
                        name="query_response_time",
                        metric_type=MetricType.PERFORMANCE,
                        value=row.avg_response_time,
                        **self.metrics_config["query_response_time"]
                    )

                # 慢查询数量
                result = await conn.execute(text("""
                    SELECT count(*) as slow_queries
                    FROM pg_stat_statements
                    WHERE mean_exec_time > 1000 AND calls > 0
                """))
                slow_count = result.scalar() or 0

                metrics["slow_queries"] = HealthMetric(
                    name="slow_queries",
                    metric_type=MetricType.PERFORMANCE,
                    value=slow_count,
                    **self.metrics_config["slow_queries"]
                )

                # 锁等待时间
                result = await conn.execute(text("""
                    SELECT
                        COALESCE(avg(EXTRACT(EPOCH FROM (now() - query_start))), 0) * 1000 as avg_wait_time
                    FROM pg_locks l
                    JOIN pg_stat_activity a ON l.pid = a.pid
                    WHERE l.granted = false AND a.wait_event_type = 'Lock'
                """))
                avg_wait = result.scalar() or 0

                metrics["lock_wait_time"] = HealthMetric(
                    name="lock_wait_time",
                    metric_type=MetricType.PERFORMANCE,
                    value=avg_wait,
                    **self.metrics_config["lock_wait_time"]
                )

        except Exception as e:
            logger.error(f"Failed to collect performance metrics: {e}")

        return metrics

    async def _collect_resource_metrics(self, db_engine: AsyncEngine) -> Dict[str, HealthMetric]:
        """收集资源指标"""
        metrics = {}

        try:
            # 系统资源指标
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            metrics["cpu_usage"] = HealthMetric(
                name="cpu_usage",
                metric_type=MetricType.RESOURCE,
                value=cpu_percent,
                **self.metrics_config["cpu_usage"]
            )

            metrics["memory_usage"] = HealthMetric(
                name="memory_usage",
                metric_type=MetricType.RESOURCE,
                value=memory.percent,
                **self.metrics_config["memory_usage"]
            )

            disk_usage_percent = (disk.used / disk.total) * 100
            metrics["disk_usage"] = HealthMetric(
                name="disk_usage",
                metric_type=MetricType.RESOURCE,
                value=disk_usage_percent,
                **self.metrics_config["disk_usage"]
            )

            # 磁盘I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                # 简化的I/O使用率计算
                metrics["disk_io_usage"] = HealthMetric(
                    name="disk_io_usage",
                    metric_type=MetricType.RESOURCE,
                    value=50.0,  # 简化值，实际应该基于历史数据计算
                    **self.metrics_config["disk_io_usage"]
                )

        except Exception as e:
            logger.error(f"Failed to collect resource metrics: {e}")

        return metrics

    async def _collect_replication_metrics(self, db_engine: AsyncEngine) -> Dict[str, HealthMetric]:
        """收集复制指标"""
        metrics = {}

        try:
            async with db_engine.begin() as conn:
                # 复制延迟
                result = await conn.execute(text("""
                    SELECT
                        COALESCE(EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())), 0) as lag_seconds
                """))
                lag = result.scalar() or 0

                metrics["replication_lag"] = HealthMetric(
                    name="replication_lag",
                    metric_type=MetricType.REPLICATION,
                    value=lag,
                    **self.metrics_config["replication_lag"]
                )

                # 复制同步率（简化计算）
                metrics["replication_sync"] = HealthMetric(
                    name="replication_sync",
                    metric_type=MetricType.REPLICATION,
                    value=99.5,  # 简化值，实际应该基于WAL位置计算
                    **self.metrics_config["replication_sync"]
                )

        except Exception as e:
            logger.error(f"Failed to collect replication metrics: {e}")

        return metrics

    async def _collect_storage_metrics(self, db_engine: AsyncEngine) -> Dict[str, HealthMetric]:
        """收集存储指标"""
        metrics = {}

        try:
            async with db_engine.begin() as conn:
                # 表大小增长率（简化计算）
                result = await conn.execute(text("""
                    SELECT
                        sum(pg_total_relation_size(schemaname||'.'||tablename)) as total_size
                    FROM pg_tables
                    WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                """))
                total_size = result.scalar() or 0

                # 基于历史数据计算增长率（简化为固定值）
                metrics["table_size_growth"] = HealthMetric(
                    name="table_size_growth",
                    metric_type=MetricType.STORAGE,
                    value=5.0,  # MB/hour，实际应该基于历史数据计算
                    **self.metrics_config["table_size_growth"]
                )

                # 索引使用率
                result = await conn.execute(text("""
                    SELECT
                        CASE
                            WHEN sum(seq_scan + idx_scan) = 0 THEN 100
                            ELSE (sum(idx_scan) * 100.0 / sum(seq_scan + idx_scan))
                        END as index_usage_rate
                    FROM pg_stat_user_tables
                """))
                usage_rate = result.scalar() or 0

                metrics["index_usage"] = HealthMetric(
                    name="index_usage",
                    metric_type=MetricType.STORAGE,
                    value=usage_rate,
                    **self.metrics_config["index_usage"]
                )

        except Exception as e:
            logger.error(f"Failed to collect storage metrics: {e}")

        return metrics

    def _calculate_overall_status(self, metrics: Dict[str, HealthMetric]) -> HealthStatus:
        """计算整体健康状态"""
        if not metrics:
            return HealthStatus.DOWN

        # 如果有CRITICAL指标，整体状态为CRITICAL
        if any(metric.status == HealthStatus.CRITICAL for metric in metrics.values()):
            return HealthStatus.CRITICAL

        # 如果有WARNING指标，整体状态为WARNING
        if any(metric.status == HealthStatus.WARNING for metric in metrics.values()):
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY

    async def _check_alerts(self, node: DatabaseNode, metrics: Dict[str, HealthMetric]) -> List[HealthAlert]:
        """检查告警条件"""
        alerts = []
        current_time = time.time()

        for metric in metrics.values():
            # 计算指标状态
            metric.calculate_status()

            # 如果状态不是健康，创建告警
            if metric.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
                alert_key = f"{node.id}_{metric.name}"

                # 检查告警冷却时间
                last_time = self.last_alert_time.get(alert_key, 0)
                if current_time - last_time < self.alert_cooldown:
                    continue

                alert = HealthAlert(
                    id=f"{alert_key}_{int(current_time)}",
                    node_id=node.id,
                    metric_name=metric.name,
                    status=metric.status,
                    message=f"{metric.description}: {metric.value:.2f}{metric.unit} (阈值: {metric.threshold_warning}{metric.unit})",
                    value=metric.value,
                    threshold=metric.threshold_warning if metric.status == HealthStatus.WARNING else metric.threshold_critical
                )

                alerts.append(alert)
                self.last_alert_time[alert_key] = current_time

        return alerts

    async def _enrich_health_report(self, node: DatabaseNode, db_engine: AsyncEngine, report: DatabaseHealthReport):
        """丰富健康报告信息"""
        try:
            async with db_engine.begin() as conn:
                # 获取数据库版本
                result = await conn.execute(text("SELECT version()"))
                version = result.scalar()
                report.version = version

                # 获取连接统计
                result = await conn.execute(text("""
                    SELECT
                        count(*) as total,
                        sum(CASE WHEN state = 'active' THEN 1 ELSE 0 END) as active,
                        sum(CASE WHEN state = 'idle' THEN 1 ELSE 0 END) as idle,
                        sum(CASE WHEN state = 'idle in transaction' THEN 1 ELSE 0 END) as idle_in_transaction
                    FROM pg_stat_activity
                """))
                row = result.first()
                if row:
                    report.connections = {
                        "total": row.total,
                        "active": row.active,
                        "idle": row.idle,
                        "idle_in_transaction": row.idle_in_transaction
                    }

        except Exception as e:
            logger.error(f"Failed to enrich health report: {e}")

    async def _handle_alerts(self, alerts: List[HealthAlert]):
        """处理告警"""
        for alert in alerts:
            # 添加到活跃告警
            self.active_alerts[alert.id] = alert
            self.alert_history.append(alert)

            # 调用告警处理器
            for handler in self.alert_handlers:
                try:
                    await asyncio.create_task(asyncio.coroutine(handler)(alert))
                except Exception as e:
                    logger.error(f"Alert handler error: {e}")

            logger.warning(f"Health alert generated: {alert.message}")

    def add_alert_handler(self, handler: Callable[[HealthAlert], None]):
        """添加告警处理器"""
        self.alert_handlers.append(handler)

    def remove_alert_handler(self, handler: Callable[[HealthAlert], None]):
        """移除告警处理器"""
        if handler in self.alert_handlers:
            self.alert_handlers.remove(handler)

    async def resolve_alert(self, alert_id: str):
        """解决告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_timestamp = time.time()
            del self.active_alerts[alert_id]
            logger.info(f"Alert resolved: {alert_id}")

    async def get_health_summary(self) -> Dict[str, Any]:
        """获取健康状态摘要"""
        if not self.health_reports:
            return {"status": "no_data", "message": "No health data available"}

        total_nodes = len(self.health_reports)
        healthy_nodes = sum(1 for report in self.health_reports.values() if report.overall_status == HealthStatus.HEALTHY)
        warning_nodes = sum(1 for report in self.health_reports.values() if report.overall_status == HealthStatus.WARNING)
        critical_nodes = sum(1 for report in self.health_reports.values() if report.overall_status == HealthStatus.CRITICAL)
        down_nodes = sum(1 for report in self.health_reports.values() if report.overall_status == HealthStatus.DOWN)

        # 活跃告警统计
        active_alerts_count = len(self.active_alerts)
        critical_alerts = sum(1 for alert in self.active_alerts.values() if alert.status == HealthStatus.CRITICAL)
        warning_alerts = sum(1 for alert in self.active_alerts.values() if alert.status == HealthStatus.WARNING)

        return {
            "overall_status": self._calculate_overall_system_status(),
            "total_nodes": total_nodes,
            "node_status": {
                "healthy": healthy_nodes,
                "warning": warning_nodes,
                "critical": critical_nodes,
                "down": down_nodes
            },
            "active_alerts": active_alerts_count,
            "alert_summary": {
                "critical": critical_alerts,
                "warning": warning_alerts
            },
            "last_check": max(report.last_check for report in self.health_reports.values()),
            "monitoring_active": self.is_monitoring
        }

    def _calculate_overall_system_status(self) -> str:
        """计算整体系统状态"""
        if not self.health_reports:
            return "unknown"

        # 如果有任何节点DOWN，系统状态为DOWN
        if any(report.overall_status == HealthStatus.DOWN for report in self.health_reports.values()):
            return "down"

        # 如果有任何CRITICAL节点，系统状态为CRITICAL
        if any(report.overall_status == HealthStatus.CRITICAL for report in self.health_reports.values()):
            return "critical"

        # 如果有任何WARNING节点，系���状态为WARNING
        if any(report.overall_status == HealthStatus.WARNING for report in self.health_reports.values()):
            return "warning"

        return "healthy"

    async def get_node_health(self, node_id: str) -> Optional[Dict[str, Any]]:
        """获取特定节点的健康状态"""
        report = self.health_reports.get(node_id)
        if not report:
            return None

        # 转换为字典格式
        metrics_dict = {}
        for name, metric in report.metrics.items():
            metrics_dict[name] = {
                "value": metric.value,
                "status": metric.status.value,
                "unit": metric.unit,
                "threshold_warning": metric.threshold_warning,
                "threshold_critical": metric.threshold_critical,
                "description": metric.description,
                "timestamp": metric.timestamp
            }

        alerts_dict = []
        for alert in report.alerts:
            alerts_dict.append({
                "id": alert.id,
                "status": alert.status.value,
                "message": alert.message,
                "value": alert.value,
                "threshold": alert.threshold,
                "timestamp": alert.timestamp,
                "resolved": alert.resolved,
                "resolved_timestamp": alert.resolved_timestamp
            })

        return {
            "node_id": report.node_id,
            "overall_status": report.overall_status.value,
            "last_check": report.last_check,
            "uptime": report.uptime,
            "version": report.version,
            "connections": report.connections,
            "metrics": metrics_dict,
            "alerts": alerts_dict
        }

    async def get_metrics_history(self, node_id: str, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """获取指标历史数据"""
        key = f"{node_id}_{metric_name}"
        history = list(self.metrics_history.get(key, []))

        # 过滤时间范围
        cutoff_time = time.time() - (hours * 3600)
        filtered_history = [m for m in history if m.timestamp >= cutoff_time]

        return [
            {
                "value": m.value,
                "status": m.status.value,
                "timestamp": m.timestamp
            }
            for m in filtered_history
        ]

    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        return [
            {
                "id": alert.id,
                "node_id": alert.node_id,
                "metric_name": alert.metric_name,
                "status": alert.status.value,
                "message": alert.message,
                "value": alert.value,
                "threshold": alert.threshold,
                "timestamp": alert.timestamp
            }
            for alert in self.active_alerts.values()
        ]


# 全局健康监控器实例
_health_monitor: Optional[DatabaseHealthMonitor] = None


def get_health_monitor() -> Optional[DatabaseHealthMonitor]:
    """获取健康监控器实例"""
    return _health_monitor


async def initialize_health_monitor(**kwargs) -> DatabaseHealthMonitor:
    """初始化健康监控器"""
    global _health_monitor
    _health_monitor = DatabaseHealthMonitor(**kwargs)
    return _health_monitor


async def cleanup_health_monitor():
    """清理健康监控器"""
    global _health_monitor
    if _health_monitor:
        await _health_monitor.stop_monitoring()
        _health_monitor = None