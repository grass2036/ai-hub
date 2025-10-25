"""
系统监控模块
收集CPU、内存、磁盘、网络等系统性能指标
"""
import psutil
import asyncio
import platform
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """系统指标数据结构"""
    timestamp: datetime
    host_name: str
    cpu: Dict
    memory: Dict
    disk: Dict
    network: Dict
    process_info: Dict

class SystemMonitor:
    """系统监控器"""

    def __init__(self):
        self.metrics_history: List[SystemMetrics] = []
        self.alerts: List[Dict] = []
        self.monitoring_active = False
        self.collection_interval = 30  # 30秒采集一次
        self.max_history_size = 1000

    async def start_monitoring(self):
        """启动系统监控"""
        self.monitoring_active = True
        logger.info("System monitoring started")

        while self.monitoring_active:
            try:
                metrics = await self.collect_system_metrics()
                self.metrics_history.append(metrics)

                # 保持历史记录在合理范围内
                if len(self.metrics_history) > self.max_history_size:
                    self.metrics_history = self.metrics_history[-self.max_history_size:]

                # 检查告警条件
                await self.check_alert_conditions(metrics)

            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")

            await asyncio.sleep(self.collection_interval)

    def stop_monitoring(self):
        """停止系统监控"""
        self.monitoring_active = False
        logger.info("System monitoring stopped")

    async def collect_system_metrics(self) -> SystemMetrics:
        """收集系统性能指标"""
        timestamp = datetime.utcnow()
        host_name = platform.node()

        # CPU信息
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)

        cpu_info = {
            'usage_percent': cpu_percent,
            'count': cpu_count,
            'frequency_current': cpu_freq.current if cpu_freq else 0,
            'frequency_min': cpu_freq.min if cpu_freq else 0,
            'frequency_max': cpu_freq.max if cpu_freq else 0,
            'load_avg_1m': load_avg[0],
            'load_avg_5m': load_avg[1],
            'load_avg_15m': load_avg[2]
        }

        # 内存信息
        virtual_memory = psutil.virtual_memory()
        swap_memory = psutil.swap_memory()

        memory_info = {
            'total': virtual_memory.total,
            'available': virtual_memory.available,
            'used': virtual_memory.used,
            'free': virtual_memory.free,
            'percent': virtual_memory.percent,
            'buffers': getattr(virtual_memory, 'buffers', 0),
            'cached': getattr(virtual_memory, 'cached', 0),
            'swap_total': swap_memory.total,
            'swap_used': swap_memory.used,
            'swap_free': swap_memory.free,
            'swap_percent': swap_memory.percent
        }

        # 磁盘信息
        disk_usage = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()

        disk_info = {
            'total': disk_usage.total,
            'used': disk_usage.used,
            'free': disk_usage.free,
            'percent': disk_usage.percent,
            'read_count': disk_io.read_count if disk_io else 0,
            'write_count': disk_io.write_count if disk_io else 0,
            'read_bytes': disk_io.read_bytes if disk_io else 0,
            'write_bytes': disk_io.write_bytes if disk_io else 0,
            'read_time': disk_io.read_time if disk_io else 0,
            'write_time': disk_io.write_time if disk_io else 0
        }

        # 网络信息
        net_io = psutil.net_io_counters()
        net_connections = len(psutil.net_connections())

        network_info = {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errin': net_io.errin,
            'errout': net_io.errout,
            'dropin': net_io.dropin,
            'dropout': net_io.dropout,
            'connections_count': net_connections
        }

        # 进程信息
        current_process = psutil.Process()
        process_info = {
            'pid': current_process.pid,
            'name': current_process.name(),
            'cpu_percent': current_process.cpu_percent(),
            'memory_percent': current_process.memory_percent(),
            'memory_info': current_process.memory_info()._asdict(),
            'create_time': current_process.create_time(),
            'status': current_process.status(),
            'num_threads': current_process.num_threads(),
            'num_fds': current_process.num_fds() if hasattr(current_process, 'num_fds') else 0
        }

        return SystemMetrics(
            timestamp=timestamp,
            host_name=host_name,
            cpu=cpu_info,
            memory=memory_info,
            disk=disk_info,
            network=network_info,
            process_info=process_info
        )

    async def check_alert_conditions(self, metrics: SystemMetrics):
        """检查告警条件"""
        alerts = []

        # CPU告警
        if metrics.cpu['usage_percent'] > 90:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'critical',
                'message': f"CPU使用率过高: {metrics.cpu['usage_percent']:.1f}%",
                'timestamp': metrics.timestamp,
                'value': metrics.cpu['usage_percent'],
                'threshold': 90
            })
        elif metrics.cpu['usage_percent'] > 80:
            alerts.append({
                'type': 'cpu_warning',
                'severity': 'warning',
                'message': f"CPU使用率较高: {metrics.cpu['usage_percent']:.1f}%",
                'timestamp': metrics.timestamp,
                'value': metrics.cpu['usage_percent'],
                'threshold': 80
            })

        # 内存告警
        if metrics.memory['percent'] > 90:
            alerts.append({
                'type': 'memory_high',
                'severity': 'critical',
                'message': f"内存使用率过高: {metrics.memory['percent']:.1f}%",
                'timestamp': metrics.timestamp,
                'value': metrics.memory['percent'],
                'threshold': 90
            })
        elif metrics.memory['percent'] > 80:
            alerts.append({
                'type': 'memory_warning',
                'severity': 'warning',
                'message': f"内存使用率较高: {metrics.memory['percent']:.1f}%",
                'timestamp': metrics.timestamp,
                'value': metrics.memory['percent'],
                'threshold': 80
            })

        # 磁盘告警
        if metrics.disk['percent'] > 95:
            alerts.append({
                'type': 'disk_critical',
                'severity': 'critical',
                'message': f"磁盘空间严重不足: {metrics.disk['percent']:.1f}%",
                'timestamp': metrics.timestamp,
                'value': metrics.disk['percent'],
                'threshold': 95
            })
        elif metrics.disk['percent'] > 85:
            alerts.append({
                'type': 'disk_warning',
                'severity': 'warning',
                'message': f"磁盘空间较低: {metrics.disk['percent']:.1f}%",
                'timestamp': metrics.timestamp,
                'value': metrics.disk['percent'],
                'threshold': 85
            })

        # 添加到告警列表
        if alerts:
            self.alerts.extend(alerts)
            logger.warning(f"Generated {len(alerts)} system alerts")

    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        """获取最新的系统指标"""
        return self.metrics_history[-1] if self.metrics_history else None

    def get_metrics_history(self, hours: int = 1) -> List[SystemMetrics]:
        """获取指定时间范围内的历史指标"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            metrics for metrics in self.metrics_history
            if metrics.timestamp >= cutoff_time
        ]

    def get_average_metrics(self, hours: int = 1) -> Optional[Dict]:
        """获取平均指标"""
        history = self.get_metrics_history(hours)
        if not history:
            return None

        avg_cpu = sum(m.cpu['usage_percent'] for m in history) / len(history)
        avg_memory = sum(m.memory['percent'] for m in history) / len(history)
        avg_disk = sum(m.disk['percent'] for m in history) / len(history)

        return {
            'period_hours': hours,
            'sample_count': len(history),
            'cpu_usage_percent': round(avg_cpu, 2),
            'memory_usage_percent': round(avg_memory, 2),
            'disk_usage_percent': round(avg_disk, 2),
            'time_range': {
                'start': history[0].timestamp.isoformat(),
                'end': history[-1].timestamp.isoformat()
            }
        }

    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """获取最近的告警"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            alert for alert in self.alerts
            if datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00')) >= cutoff_time
        ]

    def export_metrics(self, filename: str, hours: int = 24):
        """导出指标到文件"""
        history = self.get_metrics_history(hours)
        data = [asdict(metrics) for metrics in history]

        # 转换datetime对象为字符串
        for item in data:
            item['timestamp'] = item['timestamp'].isoformat()

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported {len(data)} metrics records to {filename}")

    def get_system_info(self) -> Dict:
        """获取系统基本信息"""
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.utcnow() - boot_time

        return {
            'hostname': platform.node(),
            'platform': platform.platform(),
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'boot_time': boot_time.isoformat(),
            'uptime_hours': uptime.total_seconds() / 3600,
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'disk_total': psutil.disk_usage('/').total
        }

# 全局系统监控器实例
system_monitor = SystemMonitor()