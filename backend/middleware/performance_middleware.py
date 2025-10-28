"""
API性能优化中间件
实现异步处理优化、响应压缩、请求分析和性能监控
"""

import asyncio
import time
import json
import zlib
import gzip
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import io

from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class CompressionType(Enum):
    """压缩类型"""
    GZIP = "gzip"
    DEFLATE = "deflate"
    BROTLI = "brotli"
    NONE = "none"


@dataclass
class PerformanceMetrics:
    """性能指标"""
    request_id: str
    method: str
    path: str
    status_code: int
    start_time: float
    end_time: float
    duration: float
    request_size: int = 0
    response_size: int = 0
    compressed_response_size: int = 0
    compression_type: Optional[str] = None
    compression_ratio: float = 0.0
    concurrent_requests: int = 0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    database_queries: int = 0
    database_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    error: Optional[str] = None

    @property
    def throughput_mb_per_sec(self) -> float:
        """吞吐量 MB/s"""
        if self.duration > 0:
            return (self.response_size / (1024 * 1024)) / self.duration
        return 0.0


class AsyncTaskPool:
    """异步任务池管理器"""

    def __init__(self, max_workers: int = 100, max_concurrent_tasks: int = 50):
        self.max_workers = max_workers
        self.max_concurrent_tasks = max_concurrent_tasks
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.active_tasks: Set[asyncio.Task] = set()
        self.completed_tasks = 0
        self.failed_tasks = 0

    async def submit_task(self, coro, priority: int = 0):
        """提交异步任务"""
        async def wrapped_task():
            async with self.semaphore:
                try:
                    result = await coro
                    self.completed_tasks += 1
                    return result
                except Exception as e:
                    self.failed_tasks += 1
                    logger.error(f"Async task failed: {e}")
                    raise

        task = asyncio.create_task(wrapped_task())
        self.active_tasks.add(task)
        task.add_done_callback(lambda t: self.active_tasks.discard(t))
        return task

    async def gather_results(self, tasks: List[asyncio.Task], timeout: Optional[float] = None):
        """收集任务结果"""
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        except asyncio.TimeoutError:
            logger.warning(f"Tasks timed out after {timeout}s")
            return None

    def get_stats(self) -> Dict:
        """获取任务池统计"""
        return {
            "active_tasks": len(self.active_tasks),
            "max_workers": self.max_workers,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.completed_tasks / max(1, self.completed_tasks + self.failed_tasks)
        }


class ResponseCompressor:
    """响应压缩器"""

    def __init__(self, min_size: int = 1024, compression_level: int = 6):
        self.min_size = min_size
        self.compression_level = compression_level
        self.compression_stats = {
            "total_requests": 0,
            "compressed_requests": 0,
            "total_original_bytes": 0,
            "total_compressed_bytes": 0
        }

    def should_compress(self, request: Request, response_data: bytes) -> bool:
        """判断是否应该压缩"""
        # 检查请求头中的压缩支持
        accept_encoding = request.headers.get("accept-encoding", "")
        if not any(enc in accept_encoding.lower() for enc in ["gzip", "deflate", "br"]):
            return False

        # 检查响应大小
        if len(response_data) < self.min_size:
            return False

        # 检查响应类型
        content_type = response.headers.get("content-type", "")
        compressible_types = [
            "application/json",
            "text/",
            "application/javascript",
            "application/xml",
            "text/html",
            "text/plain",
            "text/css"
        ]

        if not any(ct in content_type for ct in compressible_types):
            return False

        return True

    def compress_response(self, request: Request, response_data: bytes) -> tuple[bytes, str, float]:
        """压缩响应数据"""
        self.compression_stats["total_requests"] += 1
        original_size = len(response_data)
        self.compression_stats["total_original_bytes"] += original_size

        if not self.should_compress(request, response_data):
            self.compression_stats["compressed_requests"] += 0
            return response_data, CompressionType.NONE.value, 1.0

        # 获取支持的压缩算法
        accept_encoding = request.headers.get("accept-encoding", "").lower()

        # 优先选择Brotli，然后Gzip，最后Deflate
        if "br" in accept_encoding:
            try:
                compressed_data = self._compress_brotli(response_data)
                if compressed_data:
                    self.compression_stats["compressed_requests"] += 1
                    self.compression_stats["total_compressed_bytes"] += len(compressed_data)
                    ratio = len(compressed_data) / original_size
                    return compressed_data, CompressionType.BROTLI.value, ratio
            except ImportError:
                logger.warning("Brotli not available, falling back to gzip")

        if "gzip" in accept_encoding:
            compressed_data = self._compress_gzip(response_data)
            if compressed_data:
                self.compression_stats["compressed_requests"] += 1
                self.compression_stats["total_compressed_bytes"] += len(compressed_data)
                ratio = len(compressed_data) / original_size
                return compressed_data, CompressionType.GZIP.value, ratio

        if "deflate" in accept_encoding:
            compressed_data = self._compress_deflate(response_data)
            if compressed_data:
                self.compression_stats["compressed_requests"] += 1
                self.compression_stats["total_compressed_bytes"] += len(compressed_data)
                ratio = len(compressed_data) / original_size
                return compressed_data, CompressionType.DEFLATE.value, ratio

        return response_data, CompressionType.NONE.value, 1.0

    def _compress_gzip(self, data: bytes) -> Optional[bytes]:
        """Gzip压缩"""
        try:
            buffer = io.BytesIO()
            with gzip.GzipFile(fileobj=buffer, mode='wb', compresslevel=self.compression_level) as gz_file:
                gz_file.write(data)
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Gzip compression failed: {e}")
            return None

    def _compress_deflate(self, data: bytes) -> Optional[bytes]:
        """Deflate压缩"""
        try:
            return zlib.compress(data, level=self.compression_level)
        except Exception as e:
            logger.error(f"Deflate compression failed: {e}")
            return None

    def _compress_brotli(self, data: bytes) -> Optional[bytes]:
        """Brotli压缩"""
        try:
            import brotli
            return brotli.compress(data, quality=self.compression_level)
        except ImportError:
            return None
        except Exception as e:
            logger.error(f"Brotli compression failed: {e}")
            return None

    def get_compression_stats(self) -> Dict:
        """获取压缩统计"""
        original_bytes = self.compression_stats["total_original_bytes"]
        compressed_bytes = self.compression_stats["total_compressed_bytes"]

        return {
            "total_requests": self.compression_stats["total_requests"],
            "compressed_requests": self.compression_stats["compressed_requests"],
            "compression_rate": (
                self.compression_stats["compressed_requests"] /
                max(1, self.compression_stats["total_requests"])
            ),
            "total_original_bytes": original_bytes,
            "total_compressed_bytes": compressed_bytes,
            "average_compression_ratio": (
                compressed_bytes / max(1, original_bytes)
            ) if compressed_bytes > 0 else 1.0,
            "space_saved_bytes": max(0, original_bytes - compressed_bytes)
        }


class RequestAnalyzer:
    """请求分析器"""

    def __init__(self):
        self.request_stats = {
            "total_requests": 0,
            "total_response_time": 0.0,
            "slow_requests": 0,
            "error_requests": 0,
            "method_distribution": {},
            "path_distribution": {},
            "status_distribution": {},
            "size_distribution": {"small": 0, "medium": 0, "large": 0}
        }

    def analyze_request(self, metrics: PerformanceMetrics):
        """分析单个请求"""
        self.request_stats["total_requests"] += 1
        self.request_stats["total_response_time"] += metrics.duration

        # 分析响应时间
        if metrics.duration > 1.0:  # 慢请求阈值1秒
            self.request_stats["slow_requests"] += 1

        # 分析错误
        if metrics.status_code >= 400:
            self.request_stats["error_requests"] += 1

        # 分析方法分布
        method = metrics.method
        self.request_stats["method_distribution"][method] = (
            self.request_stats["method_distribution"].get(method, 0) + 1
        )

        # 分析路径分布
        path = metrics.path
        # 提取主要路径段
        path_parts = path.strip("/").split("/")
        if path_parts and path_parts[0]:
            main_path = path_parts[0]
            self.request_stats["path_distribution"][main_path] = (
                self.request_stats["path_distribution"].get(main_path, 0) + 1
            )

        # 分析状态码分布
        status = str(metrics.status_code)
        self.request_stats["status_distribution"][status] = (
            self.request_stats["status_distribution"].get(status, 0) + 1
        )

        # 分析响应大小分布
        if metrics.response_size < 10 * 1024:  # < 10KB
            self.request_stats["size_distribution"]["small"] += 1
        elif metrics.response_size < 100 * 1024:  # < 100KB
            self.request_stats["size_distribution"]["medium"] += 1
        else:
            self.request_stats["size_distribution"]["large"] += 1

    def get_analysis_report(self) -> Dict:
        """获取分析报告"""
        total_requests = self.request_stats["total_requests"]
        if total_requests == 0:
            return {}

        avg_response_time = (
            self.request_stats["total_response_time"] / total_requests
        )

        return {
            "total_requests": total_requests,
            "average_response_time": avg_response_time,
            "slow_request_rate": (
                self.request_stats["slow_requests"] / total_requests
            ),
            "error_rate": (
                self.request_stats["error_requests"] / total_requests
            ),
            "method_distribution": self.request_stats["method_distribution"],
            "path_distribution": dict(sorted(
                self.request_stats["path_distribution"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]  # Top 10 paths
            ),
            "status_distribution": self.request_stats["status_distribution"],
            "size_distribution": self.request_stats["size_distribution"]
        }


class PerformanceOptimizationMiddleware(BaseHTTPMiddleware):
    """性能优化中间件"""

    def __init__(
        self,
        app,
        enable_compression: bool = True,
        enable_async_pool: bool = True,
        max_concurrent_tasks: int = 50,
        min_compression_size: int = 1024,
        compression_level: int = 6,
        slow_request_threshold: float = 1.0
    ):
        super().__init__(app)
        self.enable_compression = enable_compression
        self.enable_async_pool = enable_async_pool
        self.slow_request_threshold = slow_request_threshold

        # 初始化组件
        self.compressor = ResponseCompressor(min_compression_size, compression_level)
        self.request_analyzer = RequestAnalyzer()
        self.task_pool = AsyncTaskPool(max_concurrent_tasks=max_concurrent_tasks)

        # 性能指标存储
        self.recent_metrics: List[PerformanceMetrics] = []
        self.max_metrics_history = 1000

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """中间件主逻辑"""
        # 生成请求ID
        request_id = self._generate_request_id()
        start_time = time.time()

        # 记录请求数据
        request_size = int(request.headers.get("content-length", 0))

        # 获取当前并发请求数
        concurrent_requests = len(self.task_pool.active_tasks) + 1

        try:
            # 处理请求
            response = await self._process_request(
                request, call_next, request_id, start_time, request_size, concurrent_requests
            )

            # 记录性能指标
            await self._record_metrics(request, response, request_id, start_time)

            return response

        except Exception as e:
            # 记录错误指标
            end_time = time.time()
            error_response = Response(
                content="Internal Server Error",
                status_code=500
            )
            await self._record_metrics(request, error_response, request_id, start_time, str(e))
            raise

    async def _process_request(
        self,
        request: Request,
        call_next: Callable,
        request_id: str,
        start_time: float,
        request_size: int,
        concurrent_requests: int
    ) -> Response:
        """处理请求"""

        # 调用下一个中间件或路由处理器
        response = await call_next(request)

        # 如果启用了压缩，尝试压缩响应
        if self.enable_compression and self._should_compress_response(response):
            compressed_response = await self._compress_response(request, response)
            return compressed_response

        return response

    def _should_compress_response(self, response: Response) -> bool:
        """检查是否应该压缩响应"""
        # 跳过已经压缩的响应
        content_encoding = response.headers.get("content-encoding", "")
        if content_encoding:
            return False

        # 检查内容长度头
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) < self.compressor.min_size:
            return False

        return True

    async def _compress_response(self, request: Request, response: Response) -> Response:
        """压缩响应"""
        try:
            # 获取响应体
            if hasattr(response, 'body'):
                response_data = response.body
            elif hasattr(response, 'content'):
                if isinstance(response.content, str):
                    response_data = response.content.encode('utf-8')
                else:
                    response_data = response.content
            else:
                # 对于StreamingResponse，不进行压缩
                return response

            # 压缩数据
            compressed_data, compression_type, compression_ratio = (
                self.compressor.compress_response(request, response_data)
            )

            # 创建新的响应
            headers = dict(response.headers)
            headers["content-encoding"] = compression_type
            headers["content-length"] = str(len(compressed_data))

            # 添加压缩信息头
            headers["X-Compression-Type"] = compression_type
            headers["X-Compression-Ratio"] = str(1 - compression_ratio)

            return Response(
                content=compressed_data,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type
            )

        except Exception as e:
            logger.error(f"Response compression failed: {e}")
            return response

    async def _record_metrics(
        self,
        request: Request,
        response: Response,
        request_id: str,
        start_time: float,
        error: Optional[str] = None
    ):
        """记录性能指标"""
        end_time = time.time()
        duration = end_time - start_time

        # 获取响应大小
        response_size = 0
        if hasattr(response, 'body'):
            if isinstance(response.body, (bytes, str)):
                response_size = len(response.body if isinstance(response.body, bytes) else response.body.encode())
        elif hasattr(response, 'content'):
            if isinstance(response.content, (bytes, str)):
                response_size = len(response.content if isinstance(response.content, bytes) else response.content.encode())

        # 获取压缩信息
        compression_type = response.headers.get("content-encoding", "none")
        compression_ratio = 0.0
        if "X-Compression-Ratio" in response.headers:
            try:
                compression_ratio = float(response.headers["X-Compression-Ratio"])
            except ValueError:
                pass

        # 创建性能指标
        metrics = PerformanceMetrics(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            request_size=request_size,
            response_size=response_size,
            compression_type=compression_type,
            compression_ratio=compression_ratio,
            concurrent_requests=len(self.task_pool.active_tasks),
            error=error
        )

        # 添加到历史记录
        self.recent_metrics.append(metrics)
        if len(self.recent_metrics) > self.max_metrics_history:
            self.recent_metrics.pop(0)

        # 分析请求
        self.request_analyzer.analyze_request(metrics)

        # 记录慢请求
        if duration > self.slow_request_threshold:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"- {duration:.3f}s (ID: {request_id})"
            )

    def _generate_request_id(self) -> str:
        """生成请求ID"""
        import uuid
        return str(uuid.uuid4())[:8]

    def get_performance_stats(self) -> Dict:
        """获取性能统计"""
        if not self.recent_metrics:
            return {}

        total_requests = len(self.recent_metrics)

        # 计算基本统计
        durations = [m.duration for m in self.recent_metrics]
        response_sizes = [m.response_size for m in self.recent_metrics]
        error_count = sum(1 for m in self.recent_metrics if m.status_code >= 400)
        slow_count = sum(1 for m in self.recent_metrics if m.duration > self.slow_request_threshold)

        # 计算百分位数
        sorted_durations = sorted(durations)
        p50 = sorted_durations[len(sorted_durations) // 2] if sorted_durations else 0
        p95 = sorted_durations[int(len(sorted_durations) * 0.95)] if sorted_durations else 0
        p99 = sorted_durations[int(len(sorted_durations) * 0.99)] if sorted_durations else 0

        return {
            "total_requests": total_requests,
            "average_response_time": sum(durations) / len(durations),
            "median_response_time": p50,
            "p95_response_time": p95,
            "p99_response_time": p99,
            "min_response_time": min(durations),
            "max_response_time": max(durations),
            "average_response_size": sum(response_sizes) / len(response_sizes),
            "error_rate": error_count / total_requests,
            "slow_request_rate": slow_count / total_requests,
            "compression_stats": self.compressor.get_compression_stats(),
            "task_pool_stats": self.task_pool.get_stats(),
            "request_analysis": self.request_analyzer.get_analysis_report()
        }

    def get_recent_metrics(self, limit: int = 100) -> List[Dict]:
        """获取最近的性能指标"""
        recent = self.recent_metrics[-limit:] if limit > 0 else self.recent_metrics
        return [asdict(metric) for metric in recent]

    def reset_stats(self):
        """重置统计"""
        self.recent_metrics.clear()
        self.request_analyzer = RequestAnalyzer()
        self.compressor.compression_stats = {
            "total_requests": 0,
            "compressed_requests": 0,
            "total_original_bytes": 0,
            "total_compressed_bytes": 0
        }


# 全局中间件实例
_performance_middleware: Optional[PerformanceOptimizationMiddleware] = None


def get_performance_middleware() -> PerformanceOptimizationMiddleware:
    """获取全局性能中间件实例"""
    global _performance_middleware
    if _performance_middleware is None:
        _performance_middleware = PerformanceOptimizationMiddleware(None)
    return _performance_middleware


def configure_performance_middleware(
    app,
    enable_compression: bool = True,
    enable_async_pool: bool = True,
    max_concurrent_tasks: int = 50,
    min_compression_size: int = 1024,
    compression_level: int = 6,
    slow_request_threshold: float = 1.0
) -> PerformanceOptimizationMiddleware:
    """配置性能优化中间件"""
    middleware = PerformanceOptimizationMiddleware(
        app=app,
        enable_compression=enable_compression,
        enable_async_pool=enable_async_pool,
        max_concurrent_tasks=max_concurrent_tasks,
        min_compression_size=min_compression_size,
        compression_level=compression_level,
        slow_request_threshold=slow_request_threshold
    )

    global _performance_middleware
    _performance_middleware = middleware

    return middleware