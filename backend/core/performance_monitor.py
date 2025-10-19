"""
系统监控和性能分析模块
Week 6 Day 2: 性能优化和调优 - 系统监控和性能分析
实现实时监控、性能分析、资源监控、告警系统等功能
"""

import asyncio
import time
import logging
import json
import psutil
import threading
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import numpy as np
import matplotlib.pyplot as plt
import io
import base64

from backend.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """告警级别"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"      # 计数器
    GAUGE = "gauge"          # 仪表盘
    HISTOGRAM = "histogram"  # 直方图
    TIMER = "timer"          # 计时器

@dataclass
class SystemMetric:
    """系统指标"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    metric_type: MetricType
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceAlert:
    """性能告警"""
    id: str
    level: AlertLevel
    title: str
    message: str
    metric_name: str
    current_value: float
    threshold: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None

@dataclass
class ResourceUsage:
    """资源使用情况"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_usage_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_processes: int
    timestamp: datetime

class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.metrics: Dict[str, deque] = {}  # 指标历史数据
        self.max_history = 1000  # 最大历史记录数
        self.collection_interval = 5  # 收集间隔（秒）
        self.running = False
        self.collection_task = None

    async def start_collection(self):
        """开始收集指标"""
        if self.running:
            return

        self.running = True
        self.collection_task = asyncio.create_task(self._collection_loop())
        logger.info("指标收集器已启动")

    async def stop_collection(self):
        """停止收集指标"""
        self.running = False
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        logger.info("指标收集器已停止")

    async def _collection_loop(self):
        """指标收集循环"""
        while self.running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"指标收集失败: {e}")
                await asyncio.sleep(5)

    async def _collect_system_metrics(self):
        """收集系统指标"""
        timestamp = datetime.now()

        # CPU指标
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)

        # 内存指标
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # 磁盘指标
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()

        # 网络指标
        network = psutil.net_io_counters()
        network_connections = len(psutil.net_connections())

        # 进程指标
        processes = len(psutil.pids())

        # 记录指标
        metrics = [
            SystemMetric("cpu_percent", cpu_percent, "%", timestamp, MetricType.GAUGE,
                       {"cpu_count": str(cpu_count)}),
            SystemMetric("cpu_freq", cpu_freq.current if cpu_freq else 0, "MHz", timestamp, MetricType.GAUGE),
            SystemMetric("load_avg_1m", load_avg[0], "", timestamp, MetricType.GAUGE),
            SystemMetric("memory_percent", memory.percent, "%", timestamp, MetricType.GAUGE),
            SystemMetric("memory_used_gb", memory.used / 1024**3, "GB", timestamp, MetricType.GAUGE),
            SystemMetric("swap_percent", swap.percent, "%", timestamp, MetricType.GAUGE),
            SystemMetric("disk_usage_percent", disk.percent, "%", timestamp, MetricType.GAUGE),
            SystemMetric("disk_used_gb", disk.used / 1024**3, "GB", timestamp, MetricType.GAUGE),
            SystemMetric("network_bytes_sent", network.bytes_sent, "bytes", timestamp, MetricType.COUNTER),
            SystemMetric("network_bytes_recv", network.bytes_recv, "bytes", timestamp, MetricType.COUNTER),
            SystemMetric("active_processes", processes, "count", timestamp, MetricType.GAUGE),
            SystemMetric("network_connections", network_connections, "count", timestamp, MetricType.GAUGE),
        ]

        if disk_io:
            metrics.extend([
                SystemMetric("disk_read_bytes", disk_io.read_bytes, "bytes", timestamp, MetricType.COUNTER),
                SystemMetric("disk_write_bytes", disk_io.write_bytes, "bytes", timestamp, MetricType.COUNTER),
            ])

        for metric in metrics:
            self.add_metric(metric)

    def add_metric(self, metric: SystemMetric):
        """添加指标"""
        if metric.name not in self.metrics:
            self.metrics[metric.name] = deque(maxlen=self.max_history)

        self.metrics[metric.name].append(metric)

    def get_metrics(self, metric_name: str, minutes: int = 60) -> List[SystemMetric]:
        """获取指标历史数据"""
        if metric_name not in self.metrics:
            return []

        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [m for m in self.metrics[metric_name] if m.timestamp > cutoff_time]

    def get_current_metrics(self) -> Dict[str, float]:
        """获取当前指标"""
        current_metrics = {}
        for name, metric_deque in self.metrics.items():
            if metric_deque:
                current_metrics[name] = metric_deque[-1].value
        return current_metrics

class AlertManager:
    """告警管理器"""

    def __init__(self):
        self.alerts: Dict[str, PerformanceAlert] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.alert_callbacks: List[Callable] = []
        self.running = False
        self.evaluation_task = None

    def add_alert_rule(self, name: str, metric_name: str, threshold: float,
                      operator: str = ">", level: AlertLevel = AlertLevel.WARNING,
                      duration: int = 300, message_template: str = None):
        """添加告警规则"""
        rule = {
            "name": name,
            "metric_name": metric_name,
            "threshold": threshold,
            "operator": operator,
            "level": level,
            "duration": duration,
            "message_template": message_template or f"{metric_name} {operator} {threshold}",
            "triggered_at": None
        }
        self.alert_rules.append(rule)
        logger.info(f"添加告警规则: {name}")

    def remove_alert_rule(self, name: str):
        """删除告警规则"""
        self.alert_rules = [r for r in self.alert_rules if r["name"] != name]
        logger.info(f"删除告警规则: {name}")

    def add_alert_callback(self, callback: Callable):
        """添加告警回调"""
        self.alert_callbacks.append(callback)

    async def start_evaluation(self):
        """开始告警评估"""
        if self.running:
            return

        self.running = True
        self.evaluation_task = asyncio.create_task(self._evaluation_loop())
        logger.info("告警评估器已启动")

    async def stop_evaluation(self):
        """停止告警评估"""
        self.running = False
        if self.evaluation_task:
            self.evaluation_task.cancel()
            try:
                await self.evaluation_task
            except asyncio.CancelledError:
                pass
        logger.info("告警评估器已停止")

    async def _evaluation_loop(self):
        """告警评估循环"""
        while self.running:
            try:
                await self._evaluate_rules()
                await asyncio.sleep(30)  # 每30秒评估一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"告警评估失败: {e}")
                await asyncio.sleep(30)

    async def _evaluate_rules(self, metrics_collector: MetricsCollector = None):
        """评估告警规则"""
        if not metrics_collector:
            return

        current_metrics = metrics_collector.get_current_metrics()

        for rule in self.alert_rules:
            metric_name = rule["metric_name"]
            if metric_name not in current_metrics:
                continue

            current_value = current_metrics[metric_name]
            threshold = rule["threshold"]
            operator = rule["operator"]

            # 评估条件
            triggered = False
            if operator == ">" and current_value > threshold:
                triggered = True
            elif operator == "<" and current_value < threshold:
                triggered = True
            elif operator == ">=" and current_value >= threshold:
                triggered = True
            elif operator == "<=" and current_value <= threshold:
                triggered = True
            elif operator == "==" and current_value == threshold:
                triggered = True

            alert_id = f"{rule['name']}_{metric_name}"

            if triggered:
                if rule["triggered_at"] is None:
                    rule["triggered_at"] = datetime.now()
                elif (datetime.now() - rule["triggered_at"]).total_seconds() >= rule["duration"]:
                    # 触发告警
                    if alert_id not in self.alerts:
                        await self._trigger_alert(rule, current_value, alert_id)
            else:
                # 恢复正常
                if rule["triggered_at"] is not None:
                    rule["triggered_at"] = None

                if alert_id in self.alerts:
                    await self._resolve_alert(alert_id)

    async def _trigger_alert(self, rule: Dict[str, Any], current_value: float, alert_id: str):
        """触发告警"""
        alert = PerformanceAlert(
            id=alert_id,
            level=rule["level"],
            title=f"告警: {rule['name']}",
            message=rule["message_template"].format(
                metric=rule["metric_name"],
                value=current_value,
                threshold=rule["threshold"]
            ),
            metric_name=rule["metric_name"],
            current_value=current_value,
            threshold=rule["threshold"],
            timestamp=datetime.now()
        )

        self.alerts[alert_id] = alert
        logger.warning(f"触发告警: {alert.title} - {alert.message}")

        # 调用回调函数
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"告警回调执行失败: {e}")

    async def _resolve_alert(self, alert_id: str):
        """解决告警"""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now()

            logger.info(f"告警已解决: {alert.title}")

            # 调用回调函数
            for callback in self.alert_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(alert)
                    else:
                        callback(alert)
                except Exception as e:
                    logger.error(f"告警回调执行失败: {e}")

    def get_active_alerts(self) -> List[PerformanceAlert]:
        """获取活跃告警"""
        return [alert for alert in self.alerts.values() if not alert.resolved]

    def get_alert_history(self, hours: int = 24) -> List[PerformanceAlert]:
        """获取告警历史"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alerts.values()
            if alert.timestamp > cutoff_time or
            (alert.resolved_at and alert.resolved_at > cutoff_time)
        ]

class PerformanceAnalyzer:
    """性能分析器"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector

    def analyze_trends(self, metric_name: str, hours: int = 24) -> Dict[str, Any]:
        """分析指标趋势"""
        metrics = self.metrics_collector.get_metrics(metric_name, hours)
        if not metrics:
            return {"status": "no_data"}

        values = [m.value for m in metrics]
        timestamps = [m.timestamp for m in metrics]

        # 基本统计
        mean_value = np.mean(values)
        std_value = np.std(values)
        min_value = np.min(values)
        max_value = np.max(values)

        # 趋势分析（简单线性回归）
        if len(values) > 1:
            x = np.arange(len(values))
            slope, intercept = np.polyfit(x, values, 1)
            trend = "increasing" if slope > 0.01 else "decreasing" if slope < -0.01 else "stable"
        else:
            slope = 0
            trend = "stable"

        # 异常检测（基于标准差）
        threshold = mean_value + 2 * std_value
        anomalies = [m for m in metrics if m.value > threshold]

        return {
            "metric_name": metric_name,
            "period_hours": hours,
            "data_points": len(values),
            "statistics": {
                "mean": float(mean_value),
                "std": float(std_value),
                "min": float(min_value),
                "max": float(max_value),
                "trend_slope": float(slope),
                "trend": trend
            },
            "anomalies": {
                "count": len(anomalies),
                "threshold": float(threshold),
                "data": [
                    {
                        "timestamp": a.timestamp.isoformat(),
                        "value": a.value,
                        "severity": "high" if a.value > mean_value + 3 * std_value else "medium"
                    }
                    for a in anomalies
                ]
            }
        }

    def generate_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """生成性能报告"""
        current_metrics = self.metrics_collector.get_current_metrics()

        # 分析关键指标
        key_metrics = ["cpu_percent", "memory_percent", "disk_usage_percent"]
        analyses = {}
        for metric in key_metrics:
            if metric in self.metrics_collector.metrics:
                analyses[metric] = self.analyze_trends(metric, hours)

        # 计算整体性能评分
        performance_score = self._calculate_performance_score(current_metrics)

        # 生成建议
        recommendations = self._generate_recommendations(analyses, current_metrics)

        return {
            "generated_at": datetime.now().isoformat(),
            "period_hours": hours,
            "current_metrics": current_metrics,
            "performance_score": performance_score,
            "analyses": analyses,
            "recommendations": recommendations,
            "summary": {
                "data_points_collected": sum(len(deque) for deque in self.metrics_collector.metrics.values()),
                "active_alerts": len(alert_manager.get_active_alerts()),
                "system_health": "healthy" if performance_score > 80 else "warning" if performance_score > 60 else "critical"
            }
        }

    def _calculate_performance_score(self, current_metrics: Dict[str, float]) -> float:
        """计算性能评分"""
        score = 100.0

        # CPU评分
        cpu_percent = current_metrics.get("cpu_percent", 0)
        if cpu_percent > 90:
            score -= 30
        elif cpu_percent > 70:
            score -= 15
        elif cpu_percent > 50:
            score -= 5

        # 内存评分
        memory_percent = current_metrics.get("memory_percent", 0)
        if memory_percent > 90:
            score -= 30
        elif memory_percent > 70:
            score -= 15
        elif memory_percent > 50:
            score -= 5

        # 磁盘评分
        disk_percent = current_metrics.get("disk_usage_percent", 0)
        if disk_percent > 95:
            score -= 20
        elif disk_percent > 80:
            score -= 10

        return max(0, score)

    def _generate_recommendations(self, analyses: Dict[str, Any], current_metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """生成性能优化建议"""
        recommendations = []

        # CPU建议
        cpu_percent = current_metrics.get("cpu_percent", 0)
        if cpu_percent > 80:
            recommendations.append({
                "category": "cpu",
                "priority": "high",
                "title": "CPU使用率过高",
                "description": f"当前CPU使用率为{cpu_percent:.1f}%，建议检查高CPU消耗的进程",
                "actions": [
                    "检查运行的进程和服务",
                    "考虑优化代码或增加CPU资源",
                    "使用性能分析工具定位瓶颈"
                ]
            })

        # 内存建议
        memory_percent = current_metrics.get("memory_percent", 0)
        if memory_percent > 80:
            recommendations.append({
                "category": "memory",
                "priority": "high",
                "title": "内存使用率过高",
                "description": f"当前内存使用率为{memory_percent:.1f}%，建议释放内存或增加内存",
                "actions": [
                    "检查内存泄漏",
                    "优化数据结构",
                    "增加物理内存或使用swap"
                ]
            })

        # 磁盘建议
        disk_percent = current_metrics.get("disk_usage_percent", 0)
        if disk_percent > 85:
            recommendations.append({
                "category": "disk",
                "priority": "medium",
                "title": "磁盘空间不足",
                "description": f"当前磁盘使用率为{disk_percent:.1f}%，建议清理磁盘",
                "actions": [
                    "清理临时文件和日志",
                    "压缩或删除不必要的数据",
                    "扩展磁盘容量"
                ]
            })

        return recommendations

class PerformanceMonitor:
    """性能监控主类"""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.analyzer = PerformanceAnalyzer(self.metrics_collector)

        # 设置默认告警规则
        self._setup_default_alert_rules()

    def _setup_default_alert_rules(self):
        """设置默认告警规则"""
        self.alert_manager.add_alert_rule(
            "high_cpu", "cpu_percent", 80, ">", AlertLevel.WARNING, 300,
            "CPU使用率过高: {value:.1f}% > {threshold}%"
        )
        self.alert_manager.add_alert_rule(
            "critical_cpu", "cpu_percent", 95, ">", AlertLevel.CRITICAL, 60,
            "CPU使用率严重过高: {value:.1f}% > {threshold}%"
        )
        self.alert_manager.add_alert_rule(
            "high_memory", "memory_percent", 85, ">", AlertLevel.WARNING, 300,
            "内存使用率过高: {value:.1f}% > {threshold}%"
        )
        self.alert_manager.add_alert_rule(
            "critical_memory", "memory_percent", 95, ">", AlertLevel.CRITICAL, 60,
            "内存使用率严重过高: {value:.1f}% > {threshold}%"
        )
        self.alert_manager.add_alert_rule(
            "disk_full", "disk_usage_percent", 90, ">", AlertLevel.ERROR, 600,
            "磁盘空间不足: {value:.1f}% > {threshold}%"
        )

    async def start(self):
        """启动性能监控"""
        await self.metrics_collector.start_collection()
        await self.alert_manager.start_evaluation()
        logger.info("性能监控系统已启动")

    async def stop(self):
        """停止性能监控"""
        await self.metrics_collector.stop_collection()
        await self.alert_manager.stop_evaluation()
        logger.info("性能监控系统已停止")

    def get_dashboard_data(self, hours: int = 1) -> Dict[str, Any]:
        """获取仪表板数据"""
        current_metrics = self.metrics_collector.get_current_metrics()
        active_alerts = self.alert_manager.get_active_alerts()

        # 获取时间序列数据
        time_series_data = {}
        for metric_name in ["cpu_percent", "memory_percent", "disk_usage_percent"]:
            metrics = self.metrics_collector.get_metrics(metric_name, hours)
            if metrics:
                time_series_data[metric_name] = [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "value": m.value
                    }
                    for m in metrics
                ]

        return {
            "current_metrics": current_metrics,
            "active_alerts": [asdict(alert) for alert in active_alerts],
            "time_series_data": time_series_data,
            "timestamp": datetime.now().isoformat()
        }

# 全局性能监控实例
performance_monitor = PerformanceMonitor()

# 默认告警回调函数
async def default_alert_callback(alert: PerformanceAlert):
    """默认告警回调"""
    logger.warning(f"[{alert.level.value}] {alert.title}: {alert.message}")

# 注册默认回调
performance_monitor.alert_manager.add_alert_callback(default_alert_callback)

# 测试函数
async def test_performance_monitoring():
    """测试性能监控功能"""
    print("🚀 测试性能监控系统...")

    # 启动监控
    await performance_monitor.start()

    # 收集一些数据
    print("收集系统指标...")
    await asyncio.sleep(10)

    # 获取仪表板数据
    dashboard_data = performance_monitor.get_dashboard_data()
    print(f"\n📊 当前系统指标:")
    for name, value in dashboard_data["current_metrics"].items():
        print(f"{name}: {value:.2f}")

    # 生成性能报告
    report = performance_monitor.analyzer.generate_performance_report(0.1)  # 0.1小时 = 6分钟
    print(f"\n📈 性能评分: {report['performance_score']:.1f}/100")
    print(f"系统健康状态: {report['summary']['system_health']}")

    if report['recommendations']:
        print(f"\n💡 优化建议:")
        for rec in report['recommendations']:
            print(f"- {rec['title']}: {rec['description']}")

    # 停止监控
    await performance_monitor.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_performance_monitoring())