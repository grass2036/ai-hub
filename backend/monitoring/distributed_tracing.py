"""
分布式追踪系统
Week 5 Day 5: 系统监控和运维增强 - 分布式追踪
"""

import asyncio
import uuid
import time
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from contextlib import asynccontextmanager
import threading
from collections import defaultdict

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SpanStatus(Enum):
    """Span状态"""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class SpanKind(Enum):
    """Span类型"""
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    INTERNAL = "internal"


@dataclass
class SpanEvent:
    """Span事件"""
    timestamp: datetime
    name: str
    attributes: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "name": self.name,
            "attributes": self.attributes
        }


@dataclass
class SpanLink:
    """Span链接"""
    trace_id: str
    span_id: str
    attributes: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "attributes": self.attributes
        }


@dataclass
class Span:
    """追踪Span"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime]
    status: SpanStatus
    kind: SpanKind
    service_name: str
    resource: Dict[str, Any]
    attributes: Dict[str, Any]
    events: List[SpanEvent]
    links: List[SpanLink]
    tags: Dict[str, str]

    def __post_init__(self):
        if not self.events:
            self.events = []
        if not self.links:
            self.links = []
        if not self.tags:
            self.tags = {}

    @property
    def duration_ms(self) -> Optional[float]:
        """获取持续时间（毫秒）"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "kind": self.kind.value,
            "service_name": self.service_name,
            "resource": self.resource,
            "attributes": self.attributes,
            "events": [event.to_dict() for event in self.events],
            "links": [link.to_dict() for link in self.links],
            "tags": self.tags
        }


@dataclass
class Trace:
    """追踪"""
    trace_id: str
    spans: List[Span]
    start_time: datetime
    end_time: Optional[datetime]
    status: SpanStatus
    services: List[str]
    duration_ms: Optional[float]

    def __post_init__(self):
        if not self.spans:
            self.spans = []
        if not self.services:
            self.services = []

    @property
    def span_count(self) -> int:
        """Span数量"""
        return len(self.spans)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_count": self.span_count,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "services": self.services,
            "spans": [span.to_dict() for span in self.spans]
        }


class TraceContext:
    """追踪上下文"""

    _local = threading.local()

    def __init__(self, trace_id: str, span_id: str, parent_span_id: Optional[str] = None):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.baggage_items: Dict[str, str] = {}

    @classmethod
    def current(cls) -> Optional['TraceContext']:
        """获取当前上下文"""
        return getattr(cls._local, 'context', None)

    @classmethod
    def set_current(cls, context: 'TraceContext'):
        """设置当前上下文"""
        cls._local.context = context

    @classmethod
    def clear(cls):
        """清除当前上下文"""
        cls._local.context = None

    def with_baggage(self, key: str, value: str) -> 'TraceContext':
        """添加行李项"""
        new_context = TraceContext(self.trace_id, self.span_id, self.parent_span_id)
        new_context.baggage_items = self.baggage_items.copy()
        new_context.baggage_items[key] = value
        return new_context


class Tracer:
    """追踪器"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.active_spans: Dict[str, Span] = {}
        self.traces: Dict[str, Trace] = {}
        self.sampler: Sampler = Sampler()

    def start_span(
        self,
        operation_name: str,
        parent_span: Optional[Span] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        links: Optional[List[SpanLink]] = None,
        start_time: Optional[datetime] = None
    ) -> Span:
        """开始新的Span"""
        trace_id = parent_span.trace_id if parent_span else str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        parent_span_id = parent_span.span_id if parent_span else None

        # 采样决策
        if not parent_span and not self.sampler.should_sample(trace_id):
            # 不采样，返回空Span
            return self._create_noop_span(trace_id, span_id, operation_name)

        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=start_time or datetime.utcnow(),
            end_time=None,
            status=SpanStatus.OK,
            kind=kind,
            service_name=self.service_name,
            resource=self._get_resource(),
            attributes=attributes or {},
            events=[],
            links=links or [],
            tags={}
        )

        self.active_spans[span_id] = span

        # 如果没有父Span，创建新的Trace
        if not parent_span:
            self.traces[trace_id] = Trace(
                trace_id=trace_id,
                spans=[],
                start_time=span.start_time,
                end_time=None,
                status=SpanStatus.OK,
                services=[self.service_name],
                duration_ms=None
            )

        return span

    def finish_span(self, span: Span, end_time: Optional[datetime] = None, status: SpanStatus = SpanStatus.OK):
        """结束Span"""
        span.end_time = end_time or datetime.utcnow()
        span.status = status

        # 从活跃Span中移除
        if span.span_id in self.active_spans:
            del self.active_spans[span.span_id]

        # 添加到Trace
        if span.trace_id in self.traces:
            trace = self.traces[span.trace_id]
            trace.spans.append(span)

            # 更新Trace信息
            if span.service_name not in trace.services:
                trace.services.append(span.service_name)

            # 更新Trace的结束时间和状态
            if trace.end_time is None or span.end_time > trace.end_time:
                trace.end_time = span.end_time
                trace.duration_ms = (trace.end_time - trace.start_time).total_seconds() * 1000

            if status == SpanStatus.ERROR:
                trace.status = SpanStatus.ERROR

    def add_span_event(self, span: Span, name: str, attributes: Optional[Dict[str, Any]] = None):
        """添加Span事件"""
        event = SpanEvent(
            timestamp=datetime.utcnow(),
            name=name,
            attributes=attributes or {}
        )
        span.events.append(event)

    def set_span_attribute(self, span: Span, key: str, value: Any):
        """设置Span属性"""
        span.attributes[key] = value

    def set_span_tag(self, span: Span, key: str, value: str):
        """设置Span标签"""
        span.tags[key] = value

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """获取Trace"""
        return self.traces.get(trace_id)

    def get_active_span(self, span_id: str) -> Optional[Span]:
        """获取活跃Span"""
        return self.active_spans.get(span_id)

    def _get_resource(self) -> Dict[str, Any]:
        """获取资源信息"""
        return {
            "service.name": self.service_name,
            "service.version": "1.0.0",
            "host.name": "localhost",
            "process.pid": os.getpid(),
            "telemetry.sdk.name": "aihub-tracer",
            "telemetry.sdk.version": "1.0.0"
        }

    def _create_noop_span(self, trace_id: str, span_id: str, operation_name: str) -> Span:
        """创建空操作Span（不采样时使用）"""
        return Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=None,
            operation_name=operation_name,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            status=SpanStatus.OK,
            kind=SpanKind.INTERNAL,
            service_name=self.service_name,
            resource={},
            attributes={},
            events=[],
            links=[],
            tags={}
        )


class Sampler:
    """采样器"""

    def __init__(self, sample_rate: float = 0.1):
        self.sample_rate = max(0.0, min(1.0, sample_rate))

    def should_sample(self, trace_id: str) -> bool:
        """决定是否采样"""
        if self.sample_rate >= 1.0:
            return True
        if self.sample_rate <= 0.0:
            return False

        # 基于trace_id的确定性采样
        hash_value = int(hashlib.md5(trace_id.encode()).hexdigest(), 16)
        return (hash_value % 10000) < (self.sample_rate * 10000)


class TraceCollector:
    """追踪收集器"""

    def __init__(self):
        self.traces: Dict[str, Trace] = {}
        self.max_traces = 10000
        self.retention_hours = 24

    def collect_trace(self, trace: Trace):
        """收集Trace"""
        self.traces[trace.trace_id] = trace

        # 限制存储数量
        if len(self.traces) > self.max_traces:
            # 删除最旧的Trace
            oldest_trace_id = min(
                self.traces.keys(),
                key=lambda tid: self.traces[tid].start_time
            )
            del self.traces[oldest_trace_id]

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """获取Trace"""
        return self.traces.get(trace_id)

    def search_traces(
        self,
        service_name: Optional[str] = None,
        operation_name: Optional[str] = None,
        status: Optional[SpanStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_duration_ms: Optional[float] = None,
        max_duration_ms: Optional[float] = None,
        limit: int = 100
    ) -> List[Trace]:
        """搜索Trace"""
        filtered_traces = []

        for trace in self.traces.values():
            # 服务名过滤
            if service_name and service_name not in trace.services:
                continue

            # 状态过滤
            if status and trace.status != status:
                continue

            # 时间过滤
            if start_time and trace.start_time < start_time:
                continue
            if end_time and trace.start_time > end_time:
                continue

            # 持续时间过滤
            if trace.duration_ms:
                if min_duration_ms and trace.duration_ms < min_duration_ms:
                    continue
                if max_duration_ms and trace.duration_ms > max_duration_ms:
                    continue

            # 操作名过滤
            if operation_name:
                if not any(span.operation_name == operation_name for span in trace.spans):
                    continue

            filtered_traces.append(trace)

        # 按开始时间排序
        filtered_traces.sort(key=lambda t: t.start_time, reverse=True)
        return filtered_traces[:limit]

    def get_service_statistics(self, hours: int = 1) -> Dict[str, Any]:
        """获取服务统计"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        stats = {
            "total_traces": 0,
            "total_spans": 0,
            "error_rate": 0.0,
            "avg_duration_ms": 0.0,
            "services": {}
        }

        service_data = defaultdict(lambda: {
            "trace_count": 0,
            "span_count": 0,
            "error_count": 0,
            "total_duration": 0.0,
            "operations": defaultdict(int)
        })

        total_traces = 0
        total_spans = 0
        total_errors = 0
        total_duration = 0.0

        for trace in self.traces.values():
            if trace.start_time < cutoff_time:
                continue

            total_traces += 1
            total_spans += len(trace.spans)

            if trace.status == SpanStatus.ERROR:
                total_errors += 1

            if trace.duration_ms:
                total_duration += trace.duration_ms

            # 按服务分组统计
            for service in trace.services:
                service_data[service]["trace_count"] += 1
                service_data[service]["span_count"] += len(trace.spans)
                service_data[service]["total_duration"] += trace.duration_ms or 0

                if trace.status == SpanStatus.ERROR:
                    service_data[service]["error_count"] += 1

                # 操作统计
                for span in trace.spans:
                    if span.service_name == service:
                        service_data[service]["operations"][span.operation_name] += 1

        stats["total_traces"] = total_traces
        stats["total_spans"] = total_spans
        stats["error_rate"] = (total_errors / total_traces * 100) if total_traces > 0 else 0
        stats["avg_duration_ms"] = (total_duration / total_traces) if total_traces > 0 else 0

        # 转换服务数据
        for service, data in service_data.items():
            stats["services"][service] = {
                "trace_count": data["trace_count"],
                "span_count": data["span_count"],
                "error_rate": (data["error_count"] / data["trace_count"] * 100) if data["trace_count"] > 0 else 0,
                "avg_duration_ms": (data["total_duration"] / data["trace_count"]) if data["trace_count"] > 0 else 0,
                "operations": dict(data["operations"])
            }

        return stats

    def cleanup_old_traces(self):
        """清理旧Trace"""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)

        old_trace_ids = [
            trace_id for trace_id, trace in self.traces.items()
            if trace.start_time < cutoff_time
        ]

        for trace_id in old_trace_ids:
            del self.traces[trace_id]

        logger.info(f"Cleaned up {len(old_trace_ids)} old traces")


class DistributedTracingManager:
    """分布式追踪管理器"""

    def __init__(self):
        self.tracers: Dict[str, Tracer] = {}
        self.collector = TraceCollector()
        self.sample_rate = getattr(settings, 'TRACE_SAMPLE_RATE', 0.1)

    def get_tracer(self, service_name: str) -> Tracer:
        """获取追踪器"""
        if service_name not in self.tracers:
            self.tracers[service_name] = Tracer(service_name)
        return self.tracers[service_name]

    @asynccontextmanager
    async def trace_span(
        self,
        operation_name: str,
        service_name: str = "aihub-backend",
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """追踪Span上下文管理器"""
        tracer = self.get_tracer(service_name)

        # 获取当前上下文
        current_context = TraceContext.current()
        parent_span = None

        if current_context:
            # 查找父Span
            for tracer_instance in self.tracers.values():
                parent_span = tracer_instance.get_active_span(current_context.span_id)
                if parent_span:
                    break

        span = tracer.start_span(
            operation_name=operation_name,
            parent_span=parent_span,
            kind=kind,
            attributes=attributes
        )

        # 设置新的上下文
        new_context = TraceContext(span.trace_id, span.span_id, span.parent_span_id)
        if current_context:
            # 继承行李项
            new_context.baggage_items = current_context.baggage_items.copy()
        TraceContext.set_current(new_context)

        try:
            yield span
            tracer.finish_span(span, status=SpanStatus.OK)
        except Exception as e:
            tracer.finish_span(span, status=SpanStatus.ERROR)
            tracer.set_span_attribute(span, "error.message", str(e))
            raise
        finally:
            # 恢复之前的上下文
            TraceContext.set_current(current_context)

            # 收集完成的Trace
            if span.trace_id in tracer.traces:
                self.collector.collect_trace(tracer.traces[span.trace_id])

    def inject_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """注入追踪头"""
        current_context = TraceContext.current()
        if not current_context:
            return headers

        headers = headers.copy()
        headers["X-Trace-Id"] = current_context.trace_id
        headers["X-Parent-Span-Id"] = current_context.span_id

        # 注入行李项
        for key, value in current_context.baggage_items.items():
            headers[f"X-Baggage-{key}"] = value

        return headers

    def extract_headers(self, headers: Dict[str, str]) -> Optional[TraceContext]:
        """提取追踪头"""
        trace_id = headers.get("X-Trace-Id")
        parent_span_id = headers.get("X-Parent-Span-Id")

        if not trace_id or not parent_span_id:
            return None

        context = TraceContext(trace_id, parent_span_id)

        # 提取行李项
        baggage_items = {}
        for key, value in headers.items():
            if key.startswith("X-Baggage-"):
                baggage_key = key[10:]  # 移除 "X-Baggage-" 前缀
                baggage_items[baggage_key] = value

        context.baggage_items = baggage_items
        return context

    async def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """获取Trace"""
        trace = self.collector.get_trace(trace_id)
        return trace.to_dict() if trace else None

    async def search_traces(self, **kwargs) -> List[Dict[str, Any]]:
        """搜索Trace"""
        traces = self.collector.search_traces(**kwargs)
        return [trace.to_dict() for trace in traces]

    async def get_service_statistics(self, hours: int = 1) -> Dict[str, Any]:
        """获取服务统计"""
        return self.collector.get_service_statistics(hours)

    def start_background_tasks(self):
        """启动后台任务"""
        # 定期清理旧Trace
        async def cleanup_task():
            while True:
                try:
                    await asyncio.sleep(3600)  # 每小时清理一次
                    self.collector.cleanup_old_traces()
                except Exception as e:
                    logger.error(f"Trace cleanup error: {e}")

        asyncio.create_task(cleanup_task())


# 全局分布式追踪管理器
distributed_tracing = DistributedTracingManager()


def get_tracer(service_name: str = "aihub-backend") -> Tracer:
    """获取追踪器"""
    return distributed_tracing.get_tracer(service_name)


def trace_span(
    operation_name: str,
    service_name: str = "aihub-backend",
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
):
    """追踪装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with distributed_tracing.trace_span(
                operation_name=operation_name,
                service_name=service_name,
                kind=kind,
                attributes=attributes
            ) as span:
                # 添加函数参数作为属性
                if hasattr(span, 'set_span_attribute'):
                    span.set_span_attribute("function.name", func.__name__)
                    span.set_span_attribute("function.module", func.__module__)

                try:
                    result = await func(*args, **kwargs)

                    # 添加结果信息
                    if hasattr(span, 'set_span_attribute'):
                        span.set_span_attribute("function.success", True)
                        if isinstance(result, dict):
                            span.set_span_attribute("result.type", "dict")
                        elif isinstance(result, str):
                            span.set_span_attribute("result.type", "string")
                            span.set_span_attribute("result.length", len(result))

                    return result

                except Exception as e:
                    if hasattr(span, 'set_span_attribute'):
                        span.set_span_attribute("function.success", False)
                        span.set_span_attribute("error.type", type(e).__name__)
                    raise

        return wrapper
    return decorator


# 导入缺失的模块
import os
import hashlib