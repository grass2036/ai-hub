"""
指标收集器
Week 6 Day 4: 系统监控和日志配置

提供应用性能、错误追踪和使用情况指标收集
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
import uuid
import traceback
import inspect
from functools import wraps

class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

class ErrorSeverity(Enum):
    """错误严重级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class MetricData:
    """指标数据"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    tags: Dict[str, str] = None
    unit: str = ""

@dataclass
class ErrorData:
    """错误数据"""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    error_type: str
    message: str
    stack_trace: str
    context: Dict[str, Any] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    module: str = ""
    function: str = ""

@dataclass
class PerformanceData:
    """性能数据"""
    operation_id: str
    operation_name: str
    duration_ms: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    context: Dict[str, Any] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None

@dataclass
class UsageData:
    """使用数据"""
    timestamp: datetime
    user_id: str
    session_id: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    request_size: int
    response_size: int
    user_agent: str = ""
    ip_address: str = ""

class MetricsBuffer:
    """指标缓冲区"""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.metrics = deque(maxlen=max_size)
        self.lock = threading.Lock()

    def add_metric(self, metric: MetricData) -> None:
        """添加指标"""
        with self.lock:
            self.metrics.append(metric)

    def get_metrics(self, limit: Optional[int] = None) -> List[MetricData]:
        """获取指标"""
        with self.lock:
            metrics = list(self.metrics)
            if limit:
                return metrics[-limit:]
            return metrics

    def clear(self) -> None:
        """清空指标"""
        with self.lock:
            self.metrics.clear()

    def get_size(self) -> int:
        """获取缓冲区大小"""
        with self.lock:
            return len(self.metrics)

class PerformanceTracker:
    """性能追踪器"""

    def __init__(self, buffer_size: int = 5000):
        self.buffer_size = buffer_size
        self.operations = deque(maxlen=buffer_size)
        self.operation_stats = defaultdict(lambda: {
            'count': 0,
            'total_duration': 0.0,
            'success_count': 0,
            'error_count': 0,
            'min_duration': float('inf'),
            'max_duration': 0.0
        })
        self.lock = threading.Lock()

    def record_operation(self, performance_data: PerformanceData) -> None:
        """记录操作性能"""
        with self.lock:
            self.operations.append(performance_data)

            # 更新统计信息
            stats = self.operation_stats[performance_data.operation_name]
            stats['count'] += 1
            stats['total_duration'] += performance_data.duration_ms

            if performance_data.success:
                stats['success_count'] += 1
            else:
                stats['error_count'] += 1

            stats['min_duration'] = min(stats['min_duration'], performance_data.duration_ms)
            stats['max_duration'] = max(stats['max_duration'], performance_data.duration_ms)

    def get_operation_stats(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """获取操作统计"""
        with self.lock:
            if operation_name:
                if operation_name in self.operation_stats:
                    stats = self.operation_stats[operation_name]
                    return {
                        'operation_name': operation_name,
                        'count': stats['count'],
                        'avg_duration_ms': stats['total_duration'] / stats['count'] if stats['count'] > 0 else 0,
                        'success_rate': stats['success_count'] / stats['count'] if stats['count'] > 0 else 0,
                        'error_rate': stats['error_count'] / stats['count'] if stats['count'] > 0 else 0,
                        'min_duration_ms': stats['min_duration'] if stats['min_duration'] != float('inf') else 0,
                        'max_duration_ms': stats['max_duration']
                    }
                else:
                    return {}
            else:
                return {
                    name: {
                        'count': stats['count'],
                        'avg_duration_ms': stats['total_duration'] / stats['count'] if stats['count'] > 0 else 0,
                        'success_rate': stats['success_count'] / stats['count'] if stats['count'] > 0 else 0,
                        'error_rate': stats['error_count'] / stats['count'] if stats['count'] > 0 else 0,
                        'min_duration_ms': stats['min_duration'] if stats['min_duration'] != float('inf') else 0,
                        'max_duration_ms': stats['max_duration']
                    }
                    for name, stats in self.operation_stats.items()
                }

    def get_slow_operations(self, threshold_ms: float = 1000, limit: int = 50) -> List[PerformanceData]:
        """获取慢操作"""
        with self.lock:
            slow_ops = [op for op in self.operations if op.duration_ms > threshold_ms]
            return sorted(slow_ops, key=lambda x: x.duration_ms, reverse=True)[:limit]

    def get_recent_operations(self, minutes: int = 60, limit: int = 100) -> List[PerformanceData]:
        """获取最近操作"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        with self.lock:
            recent_ops = [op for op in self.operations if op.timestamp >= cutoff_time]
            return sorted(recent_ops, key=lambda x: x.timestamp, reverse=True)[:limit]

class ErrorTracker:
    """错误追踪器"""

    def __init__(self, buffer_size: int = 2000):
        self.buffer_size = buffer_size
        self.errors = deque(maxlen=buffer_size)
        self.error_patterns = defaultdict(int)
        self.error_by_type = defaultdict(int)
        self.error_by_module = defaultdict(int)
        self.lock = threading.Lock()

    def record_error(self, error_data: ErrorData) -> None:
        """记录错误"""
        with self.lock:
            self.errors.append(error_data)

            # 更新错误统计
            self.error_patterns[error_data.message] += 1
            self.error_by_type[error_data.error_type] += 1
            self.error_by_module[error_data.module] += 1

    def get_error_statistics(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """获取错误统计"""
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)

        with self.lock:
            recent_errors = [e for e in self.errors if e.timestamp >= cutoff_time]

            # 按严重级别统计
            severity_stats = defaultdict(int)
            for error in recent_errors:
                severity_stats[error.severity.value] += 1

            # 按类型统计
            type_stats = defaultdict(int)
            for error in recent_errors:
                type_stats[error.error_type] += 1

            # 错误趋势（按小时）
            hourly_errors = defaultdict(int)
            for error in recent_errors:
                hour = error.timestamp.replace(minute=0, second=0, microsecond=0)
                hourly_errors[hour] += 1

            return {
                'total_errors': len(recent_errors),
                'severity_distribution': dict(severity_stats),
                'type_distribution': dict(type_stats),
                'hourly_trend': {hour.isoformat(): count for hour, count in hourly_errors.items()},
                'most_common_errors': dict(sorted(self.error_patterns.items(), key=lambda x: x[1], reverse=True)[:10]),
                'most_error_prone_modules': dict(sorted(self.error_by_module.items(), key=lambda x: x[1], reverse=True)[:10])
            }

    def get_critical_errors(self, hours: int = 24) -> List[ErrorData]:
        """获取严重错误"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self.lock:
            critical_errors = [
                e for e in self.errors
                if e.timestamp >= cutoff_time and e.severity == ErrorSeverity.CRITICAL
            ]
            return sorted(critical_errors, key=lambda x: x.timestamp, reverse=True)

    def get_error_trend(self, hours: int = 24) -> Dict[str, List[int]]:
        """获取错误趋势"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self.lock:
            recent_errors = [e for e in self.errors if e.timestamp >= cutoff_time]

            # 按小时和严重级别分组
            hourly_severity = defaultdict(lambda: defaultdict(int))
            for error in recent_errors:
                hour = error.timestamp.replace(minute=0, second=0, microsecond=0)
                hourly_severity[hour][error.severity.value] += 1

            return {
                hour.isoformat(): dict(severity_counts)
                for hour, severity_counts in hourly_severity.items()
            }

class UsageTracker:
    """使用追踪器"""

    def __init__(self, buffer_size: int = 10000):
        self.buffer_size = buffer_size
        self.usage_records = deque(maxlen=buffer_size)
        self.user_stats = defaultdict(lambda: {
            'request_count': 0,
            'total_response_time': 0.0,
            'error_count': 0,
            'total_bytes_sent': 0,
            'total_bytes_received': 0
        })
        self.endpoint_stats = defaultdict(lambda: {
            'request_count': 0,
            'total_response_time': 0.0,
            'error_count': 0
        })
        self.lock = threading.Lock()

    def record_usage(self, usage_data: UsageData) -> None:
        """记录使用数据"""
        with self.lock:
            self.usage_records.append(usage_data)

            # 更新用户统计
            user_stat = self.user_stats[usage_data.user_id]
            user_stat['request_count'] += 1
            user_stat['total_response_time'] += usage_data.response_time_ms
            user_stat['total_bytes_sent'] += usage_data.request_size
            user_stat['total_bytes_received'] += usage_data.response_size
            if usage_data.status_code >= 400:
                user_stat['error_count'] += 1

            # 更新端点统计
            endpoint_key = f"{usage_data.method} {usage_data.endpoint}"
            endpoint_stat = self.endpoint_stats[endpoint_key]
            endpoint_stat['request_count'] += 1
            endpoint_stat['total_response_time'] += usage_data.response_time_ms
            if usage_data.status_code >= 400:
                endpoint_stat['error_count'] += 1

    def get_user_statistics(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户统计"""
        with self.lock:
            user_stats = []
            for user_id, stats in self.user_stats.items():
                user_stats.append({
                    'user_id': user_id,
                    'request_count': stats['request_count'],
                    'avg_response_time_ms': stats['total_response_time'] / stats['request_count'] if stats['request_count'] > 0 else 0,
                    'error_rate': stats['error_count'] / stats['request_count'] if stats['request_count'] > 0 else 0,
                    'total_bytes_sent': stats['total_bytes_sent'],
                    'total_bytes_received': stats['total_bytes_received']
                })

            return sorted(user_stats, key=lambda x: x['request_count'], reverse=True)[:limit]

    def get_endpoint_statistics(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取端点统计"""
        with self.lock:
            endpoint_stats = []
            for endpoint, stats in self.endpoint_stats.items():
                endpoint_stats.append({
                    'endpoint': endpoint,
                    'request_count': stats['request_count'],
                    'avg_response_time_ms': stats['total_response_time'] / stats['request_count'] if stats['request_count'] > 0 else 0,
                    'error_rate': stats['error_count'] / stats['request_count'] if stats['request_count'] > 0 else 0
                })

            return sorted(endpoint_stats, key=lambda x: x['request_count'], reverse=True)[:limit]

    def get_usage_trends(self, hours: int = 24) -> Dict[str, Any]:
        """获取使用趋势"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self.lock:
            recent_usage = [u for u in self.usage_records if u.timestamp >= cutoff_time]

            # 按小时统计
            hourly_requests = defaultdict(int)
            hourly_errors = defaultdict(int)
            hourly_response_times = defaultdict(list)

            for usage in recent_usage:
                hour = usage.timestamp.replace(minute=0, second=0, microsecond=0)
                hourly_requests[hour] += 1
                if usage.status_code >= 400:
                    hourly_errors[hour] += 1
                hourly_response_times[hour].append(usage.response_time_ms)

            # 计算平均响应时间
            hourly_avg_response_time = {}
            for hour, times in hourly_response_times.items():
                hourly_avg_response_time[hour] = sum(times) / len(times) if times else 0

            return {
                'hourly_requests': {hour.isoformat(): count for hour, count in hourly_requests.items()},
                'hourly_errors': {hour.isoformat(): count for hour, count in hourly_errors.items()},
                'hourly_avg_response_time': {hour.isoformat(): rt for hour, rt in hourly_avg_response_time.items()},
                'total_requests': len(recent_usage),
                'total_errors': len([u for u in recent_usage if u.status_code >= 400]),
                'error_rate': len([u for u in recent_usage if u.status_code >= 400]) / len(recent_usage) if recent_usage else 0
            }

class MetricsCollector:
    """指标收集器主类"""

    def __init__(self):
        self.metrics_buffer = MetricsBuffer()
        self.performance_tracker = PerformanceTracker()
        self.error_tracker = ErrorTracker()
        self.usage_tracker = UsageTracker()
        self.is_collecting = False
        self._collection_thread = None

    def start_collection(self) -> None:
        """开始收集指标"""
        if self.is_collecting:
            return

        self.is_collecting = True
        self._collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._collection_thread.start()

    def stop_collection(self) -> None:
        """停止收集指标"""
        self.is_collecting = False
        if self._collection_thread:
            self._collection_thread.join()

    def _collection_loop(self) -> None:
        """收集循环"""
        while self.is_collecting:
            try:
                # 收集系统指标
                self._collect_system_metrics()
                time.sleep(30)  # 每30秒收集一次
            except Exception as e:
                print(f"Error in metrics collection: {str(e)}")
                time.sleep(30)

    def _collect_system_metrics(self) -> None:
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric("system_cpu_usage", cpu_percent, MetricType.GAUGE, unit="percent")

            # 内存使用率
            memory = psutil.virtual_memory()
            self.record_metric("system_memory_usage", memory.percent, MetricType.GAUGE, unit="percent")
            self.record_metric("system_memory_used", memory.used, MetricType.GAUGE, unit="bytes")

            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.record_metric("system_disk_usage", disk_percent, MetricType.GAUGE, unit="percent")

            # 网络I/O
            net_io = psutil.net_io_counters()
            self.record_metric("system_network_bytes_sent", net_io.bytes_sent, MetricType.COUNTER, unit="bytes")
            self.record_metric("system_network_bytes_recv", net_io.bytes_recv, MetricType.COUNTER, unit="bytes")

        except Exception as e:
            print(f"Error collecting system metrics: {str(e)}")

    def record_metric(self, name: str, value: float, metric_type: MetricType, tags: Dict[str, str] = None, unit: str = "") -> None:
        """记录指标"""
        metric = MetricData(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=datetime.now(),
            tags=tags or {},
            unit=unit
        )
        self.metrics_buffer.add_metric(metric)

    def record_performance(self, operation_name: str, duration_ms: float, success: bool = True, error_message: str = None, context: Dict[str, Any] = None, **kwargs) -> None:
        """记录性能数据"""
        performance_data = PerformanceData(
            operation_id=str(uuid.uuid4()),
            operation_name=operation_name,
            duration_ms=duration_ms,
            timestamp=datetime.now(),
            success=success,
            error_message=error_message,
            context=context or {},
            user_id=kwargs.get('user_id'),
            request_id=kwargs.get('request_id')
        )
        self.performance_tracker.record_operation(performance_data)

    def record_error(self, error: Exception, severity: ErrorSeverity = ErrorSeverity.MEDIUM, context: Dict[str, Any] = None, **kwargs) -> None:
        """记录错误"""
        error_data = ErrorData(
            error_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            severity=severity,
            error_type=type(error).__name__,
            message=str(error),
            stack_trace=traceback.format_exc(),
            context=context or {},
            user_id=kwargs.get('user_id'),
            request_id=kwargs.get('request_id'),
            session_id=kwargs.get('session_id'),
            module=kwargs.get('module', ''),
            function=kwargs.get('function', '')
        )
        self.error_tracker.record_error(error_data)

    def record_usage(self, endpoint: str, method: str, status_code: int, response_time_ms: float, request_size: int = 0, response_size: int = 0, **kwargs) -> None:
        """记录使用数据"""
        usage_data = UsageData(
            timestamp=datetime.now(),
            user_id=kwargs.get('user_id', 'anonymous'),
            session_id=kwargs.get('session_id', ''),
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            request_size=request_size,
            response_size=response_size,
            user_agent=kwargs.get('user_agent', ''),
            ip_address=kwargs.get('ip_address', '')
        )
        self.usage_tracker.record_usage(usage_data)

    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """获取综合指标"""
        return {
            "system_metrics": {
                "recent_metrics": [asdict(m) for m in self.metrics_buffer.get_metrics(100)],
                "buffer_size": self.metrics_buffer.get_size()
            },
            "performance_metrics": self.performance_tracker.get_operation_stats(),
            "slow_operations": [asdict(op) for op in self.performance_tracker.get_slow_operations()],
            "error_metrics": self.error_tracker.get_error_statistics(),
            "critical_errors": [asdict(e) for e in self.error_tracker.get_critical_errors()],
            "usage_metrics": {
                "user_stats": self.usage_tracker.get_user_statistics(20),
                "endpoint_stats": self.usage_tracker.get_endpoint_statistics(20),
                "usage_trends": self.usage_tracker.get_usage_trends()
            }
        }

# 全局指标收集器实例
metrics_collector = MetricsCollector()

# 装饰器函数
def track_performance(operation_name: str = None):
    """性能追踪装饰器"""
    def decorator(func):
        name = operation_name or f"{func.__module__}.{func.__name__}"

        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    metrics_collector.record_performance(name, duration_ms, success=True)
                    return result
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    metrics_collector.record_performance(name, duration_ms, success=False, error_message=str(e))
                    metrics_collector.record_error(e, context={"operation": name})
                    raise

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    metrics_collector.record_performance(name, duration_ms, success=True)
                    return result
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    metrics_collector.record_performance(name, duration_ms, success=False, error_message=str(e))
                    metrics_collector.record_error(e, context={"operation": name})
                    raise

            return sync_wrapper

    return decorator

def track_errors(severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """错误追踪装饰器"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # 获取调用信息
                frame = inspect.currentframe()
                try:
                    # 向上查找调用栈
                    while frame:
                        frame = frame.f_back
                        if frame and frame.f_code.co_name != 'async_wrapper':
                            break

                    module = frame.f_globals.get('__name__', '') if frame else ''
                    function = frame.f_code.co_name if frame else ''
                finally:
                    del frame

                metrics_collector.record_error(
                    e,
                    severity=severity,
                    context={"function": func.__name__},
                    module=module,
                    function=function,
                    **kwargs
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 获取调用信息
                frame = inspect.currentframe()
                try:
                    # 向上查找调用栈
                    while frame:
                        frame = frame.f_back
                        if frame and frame.f_code.co_name != 'sync_wrapper':
                            break

                    module = frame.f_globals.get('__name__', '') if frame else ''
                    function = frame.f_code.co_name if frame else ''
                finally:
                    del frame

                metrics_collector.record_error(
                    e,
                    severity=severity,
                    context={"function": func.__name__},
                    module=module,
                    function=function,
                    **kwargs
                )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

def count_metric(metric_name: str, metric_type: MetricType = MetricType.COUNTER, tags: Dict[str, str] = None):
    """指标计数装饰器"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                if metric_type == MetricType.COUNTER:
                    metrics_collector.record_metric(metric_name, 1, metric_type, tags)
                return result
            except Exception as e:
                metrics_collector.record_metric(f"{metric_name}_errors", 1, MetricType.COUNTER, tags)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                if metric_type == MetricType.COUNTER:
                    metrics_collector.record_metric(metric_name, 1, metric_type, tags)
                return result
            except Exception as e:
                metrics_collector.record_metric(f"{metric_name}_errors", 1, MetricType.COUNTER, tags)
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator