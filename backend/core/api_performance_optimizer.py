"""
API性能优化模块
Week 6 Day 2: 性能优化和调优 - API响应时间和缓存机���优化
实现API缓存、响应优化、连接池管理等功能
"""

import asyncio
import time
import hashlib
import json
import logging
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps, lru_cache
from contextlib import asynccontextmanager
import aiohttp
import aioredis
from fastapi import Request, Response, HTTPException
from fastapi.concurrency import run_in_threadpool
import psutil

from backend.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

@dataclass
class APIMetrics:
    """API性能指标"""
    endpoint: str
    method: str
    response_time: float
    status_code: int
    response_size: int
    timestamp: datetime
    user_id: Optional[str] = None
    cache_hit: bool = False

@dataclass
class CacheConfig:
    """缓存配置"""
    ttl: int = 300  # 默认5分钟
    max_size: int = 1000
    key_prefix: str = "api_cache"
    enabled: bool = True
    vary_on_user: bool = False
    vary_on_params: List[str] = field(default_factory=list)

@dataclass
class PerformanceThresholds:
    """性能阈值配置"""
    response_time_warning: float = 1.0  # 秒
    response_time_critical: float = 3.0  # 秒
    memory_usage_warning: float = 80.0  # 百分比
    cpu_usage_warning: float = 80.0  # 百分比
    error_rate_warning: float = 5.0  # 百分比

class APICacheManager:
    """API缓存管理器"""

    def __init__(self):
        self.redis_client = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0
        }
        self._setup_redis()

    async def _setup_redis(self):
        """设置Redis连接"""
        try:
            self.redis_client = await aioredis.from_url(
                f"redis://{getattr(settings, 'redis_host', 'localhost')}:{getattr(settings, 'redis_port', 6379)}",
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Redis连接成功，启用分布式缓存")
        except Exception as e:
            logger.warning(f"Redis连接失败，使用内存缓存: {e}")
            self.redis_client = None

    def _generate_cache_key(self, request: Request, config: CacheConfig) -> str:
        """生成缓存键"""
        # 基础键
        key_parts = [config.key_prefix, request.method, request.url.path]

        # 添加参数
        if config.vary_on_params:
            query_params = dict(request.query_params)
            for param in config.vary_on_params:
                if param in query_params:
                    key_parts.append(f"{param}={query_params[param]}")

        # 添加用户差异
        if config.vary_on_user:
            # 从请求中获取用户ID（需要根据实际认证方式调整）
            user_id = getattr(request.state, 'user_id', None)
            if user_id:
                key_parts.append(f"user={user_id}")

        # 生成最终键
        key_string = ":".join(str(part) for part in key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{config.key_prefix}:{key_hash}"

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        # 尝试Redis
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    self.cache_stats["hits"] += 1
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Redis缓存读取失败: {e}")

        # 回退到内存缓存
        if key in self.memory_cache:
            cache_entry = self.memory_cache[key]
            if cache_entry["expires_at"] > datetime.now():
                self.cache_stats["hits"] += 1
                return cache_entry["data"]
            else:
                # 过期，删除
                del self.memory_cache[key]
                self.cache_stats["evictions"] += 1

        self.cache_stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: int = 300):
        """设置缓存"""
        # 尝试Redis
        if self.redis_client:
            try:
                await self.redis_client.setex(key, ttl, json.dumps(value, default=str))
                self.cache_stats["sets"] += 1
                return
            except Exception as e:
                logger.warning(f"Redis缓存写入失败: {e}")

        # 回退到内存缓存
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self.memory_cache[key] = {
            "data": value,
            "expires_at": expires_at
        }
        self.cache_stats["sets"] += 1

        # 检查内存缓存大小
        if len(self.memory_cache) > 1000:  # 限制内存缓存大小
            self._evict_oldest_entries()

    def _evict_oldest_entries(self):
        """清理最旧的缓存条目"""
        # 按过期时间排序，删除最旧的20%
        sorted_entries = sorted(
            self.memory_cache.items(),
            key=lambda x: x[1]["expires_at"]
        )

        evict_count = len(sorted_entries) // 5
        for i in range(evict_count):
            key = sorted_entries[i][0]
            del self.memory_cache[key]
            self.cache_stats["evictions"] += 1

    async def delete(self, key: str):
        """删除缓存"""
        if self.redis_client:
            try:
                await self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis缓存删除失败: {e}")

        if key in self.memory_cache:
            del self.memory_cache[key]

    async def clear_pattern(self, pattern: str):
        """按模式清理缓存"""
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis模式清理失败: {e}")

        # 清理内存缓存
        keys_to_delete = [k for k in self.memory_cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.memory_cache[key]
            self.cache_stats["evictions"] += 1

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "cache_type": "redis" if self.redis_client else "memory",
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "hit_rate_percent": round(hit_rate, 2),
            "total_cached_items": len(self.memory_cache),
            "evictions": self.cache_stats["evictions"]
        }

class APIPerformanceOptimizer:
    """API性能优化器"""

    def __init__(self):
        self.cache_manager = APICacheManager()
        self.metrics: List[APIMetrics] = []
        self.thresholds = PerformanceThresholds()
        self.performance_stats = {
            "total_requests": 0,
            "avg_response_time": 0.0,
            "error_count": 0,
            "slow_requests": 0
        }

    @asynccontextmanager
    async def measure_request(self, request: Request):
        """测量请求性能的上下文管理器"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss

        try:
            yield
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss

            # 记录指标
            response_time = end_time - start_time
            memory_usage = (end_memory - start_memory) / 1024 / 1024  # MB

            # 这里需要从响应中获取状态码和大小
            # 在实际使用中，这些会从middleware中获取
            status_code = getattr(request.state, 'status_code', 200)
            response_size = getattr(request.state, 'response_size', 0)

            metric = APIMetrics(
                endpoint=request.url.path,
                method=request.method,
                response_time=response_time,
                status_code=status_code,
                response_size=response_size,
                timestamp=datetime.now(),
                user_id=getattr(request.state, 'user_id', None),
                cache_hit=getattr(request.state, 'cache_hit', False)
            )

            self.metrics.append(metric)
            self._update_performance_stats(metric)

            # 检查性能阈值
            await self._check_performance_thresholds(metric)

    def _update_performance_stats(self, metric: APIMetrics):
        """更新性能统计"""
        self.performance_stats["total_requests"] += 1

        # 更新平均响应时间
        total = self.performance_stats["total_requests"]
        current_avg = self.performance_stats["avg_response_time"]
        new_avg = (current_avg * (total - 1) + metric.response_time) / total
        self.performance_stats["avg_response_time"] = new_avg

        # 更新错误计数
        if metric.status_code >= 400:
            self.performance_stats["error_count"] += 1

        # 更新慢请求计数
        if metric.response_time > self.thresholds.response_time_warning:
            self.performance_stats["slow_requests"] += 1

    async def _check_performance_thresholds(self, metric: APIMetrics):
        """检查性能阈值"""
        if metric.response_time > self.thresholds.response_time_critical:
            logger.critical(
                f"API响应时间过长: {metric.endpoint} - {metric.response_time:.3f}s"
            )
        elif metric.response_time > self.thresholds.response_time_warning:
            logger.warning(
                f"API响应时间较慢: {metric.endpoint} - {metric.response_time:.3f}s"
            )

        # 检查错误率
        if self.performance_stats["total_requests"] > 100:
            error_rate = (
                self.performance_stats["error_count"] /
                self.performance_stats["total_requests"] * 100
            )
            if error_rate > self.thresholds.error_rate_warning:
                logger.warning(f"API错误率过高: {error_rate:.2f}%")

    def cache_response(self, config: CacheConfig):
        """API响应缓存装饰器"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 尝试从request参数获取请求对象
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

                if not request or not config.enabled:
                    return await func(*args, **kwargs)

                # 生成缓存键
                cache_key = self.cache_manager._generate_cache_key(request, config)

                # 尝试获取缓存
                cached_response = await self.cache_manager.get(cache_key)
                if cached_response:
                    request.state.cache_hit = True
                    return cached_response

                # 执行原函数
                response = await func(*args, **kwargs)

                # 缓存响应（只缓存成功响应）
                if hasattr(response, 'status_code') and response.status_code == 200:
                    await self.cache_manager.set(cache_key, response, config.ttl)

                return response

            return wrapper
        return decorator

    async def invalidate_cache_pattern(self, pattern: str):
        """按模式失效缓存"""
        await self.cache_manager.clear_pattern(f"{self.cache_manager.cache_stats['key_prefix']}:{pattern}")

    def get_performance_report(self, minutes: int = 60) -> Dict[str, Any]:
        """生成性能报告"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [m for m in self.metrics if m.timestamp > cutoff_time]

        if not recent_metrics:
            return {"status": "no_data", "message": "暂无性能数据"}

        # 计算统计数据
        response_times = [m.response_time for m in recent_metrics]
        status_codes = [m.status_code for m in recent_metrics]

        # 按端点分组统计
        endpoint_stats = {}
        for metric in recent_metrics:
            endpoint = metric.endpoint
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {
                    "count": 0,
                    "response_times": [],
                    "status_codes": [],
                    "cache_hits": 0
                }

            endpoint_stats[endpoint]["count"] += 1
            endpoint_stats[endpoint]["response_times"].append(metric.response_time)
            endpoint_stats[endpoint]["status_codes"].append(metric.status_code)
            if metric.cache_hit:
                endpoint_stats[endpoint]["cache_hits"] += 1

        # 计算每个端点的统计
        for endpoint, stats in endpoint_stats.items():
            times = stats["response_times"]
            stats["avg_response_time"] = sum(times) / len(times)
            stats["max_response_time"] = max(times)
            stats["min_response_time"] = min(times)
            stats["cache_hit_rate"] = (
                stats["cache_hits"] / stats["count"] * 100
            )

        return {
            "summary": {
                "total_requests": len(recent_metrics),
                "avg_response_time": sum(response_times) / len(response_times),
                "max_response_time": max(response_times),
                "min_response_time": min(response_times),
                "error_rate": (
                    len([s for s in status_codes if s >= 400]) / len(status_codes) * 100
                ),
                "period_minutes": minutes
            },
            "endpoint_stats": endpoint_stats,
            "cache_stats": self.cache_manager.get_cache_stats(),
            "slow_requests": [
                {
                    "endpoint": m.endpoint,
                    "method": m.method,
                    "response_time": m.response_time,
                    "timestamp": m.timestamp.isoformat()
                }
                for m in sorted(recent_metrics, key=lambda x: x.response_time, reverse=True)[:10]
                if m.response_time > self.thresholds.response_time_warning
            ],
            "performance_thresholds": {
                "response_time_warning": self.thresholds.response_time_warning,
                "response_time_critical": self.thresholds.response_time_critical
            }
        }

    def clear_old_metrics(self, hours: int = 24):
        """清理旧的性能指标"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        original_count = len(self.metrics)

        self.metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
        cleaned_count = original_count - len(self.metrics)

        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 条旧的API性能指标")

class ConnectionPoolOptimizer:
    """连接池优化器"""

    def __init__(self):
        self.aiohttp_session: Optional[aiohttp.ClientSession] = None

    async def get_optimized_session(self) -> aiohttp.ClientSession:
        """获取优化的HTTP会话"""
        if self.aiohttp_session is None or self.aiohttp_session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,  # 总连接池大小
                limit_per_host=30,  # 每个主机的连接数
                ttl_dns_cache=300,  # DNS缓存时间
                use_dns_cache=True,
                keepalive_timeout=60,  # 保持连接时间
                enable_cleanup_closed=True
            )

            timeout = aiohttp.ClientTimeout(
                total=30,  # 总超时时间
                connect=10,  # 连接超时
                sock_read=10  # 读取超时
            )

            self.aiohttp_session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )

        return self.aiohttp_session

    async def close(self):
        """关闭连接池"""
        if self.aiohttp_session and not self.aiohttp_session.closed:
            await self.aiohttp_session.close()

# 全局实例
api_performance_optimizer = APIPerformanceOptimizer()
connection_pool_optimizer = ConnectionPoolOptimizer()

# 装饰器工厂函数
def cache_api_response(
    ttl: int = 300,
    max_size: int = 1000,
    vary_on_user: bool = False,
    vary_on_params: List[str] = None
):
    """API响应缓存装饰器"""
    config = CacheConfig(
        ttl=ttl,
        max_size=max_size,
        vary_on_user=vary_on_user,
        vary_on_params=vary_on_params or []
    )
    return api_performance_optimizer.cache_response(config)

# 性能监控装饰器
def monitor_performance(func: Callable):
    """性能监控装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            execution_time = end_time - start_time

            if execution_time > api_performance_optimizer.thresholds.response_time_warning:
                logger.warning(f"函数 {func.__name__} 执行时间过长: {execution_time:.3f}s")

    return wrapper

# 批量请求优化器
class BatchRequestOptimizer:
    """批量请求优化器"""

    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_batch_requests(
        self,
        requests: List[Callable],
        timeout: Optional[float] = None
    ) -> List[Any]:
        """执行批量请求"""
        async def execute_single(request_func):
            async with self.semaphore:
                try:
                    if timeout:
                        return await asyncio.wait_for(request_func(), timeout=timeout)
                    else:
                        return await request_func()
                except Exception as e:
                    logger.error(f"批量请求执行失败: {e}")
                    return None

        tasks = [execute_single(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r for r in results if r is not None]

# 测试函数
async def test_api_performance_optimization():
    """测试API性能优化功能"""
    print("🚀 测试API性能优化功能...")

    # 测试缓存功能
    @cache_api_response(ttl=60, vary_on_params=["user_id"])
    async def test_api_function(user_id: str, data: str):
        await asyncio.sleep(0.1)  # 模拟API调用
        return {"user_id": user_id, "data": data, "timestamp": datetime.now().isoformat()}

    # 第一次调用（无缓存）
    start_time = time.time()
    result1 = await test_api_function("user123", "test_data")
    time1 = time.time() - start_time

    # 第二次调用（有缓存）
    start_time = time.time()
    result2 = await test_api_function("user123", "test_data")
    time2 = time.time() - start_time

    print(f"第一次调用耗时: {time1:.3f}秒")
    print(f"第二次调用耗时: {time2:.3f}秒")
    print(f"性能提升: {((time1 - time2) / time1 * 100):.1f}%")

    # 获取性能报告
    report = api_performance_optimizer.get_performance_report()
    print(f"\n📊 性能报告:")
    print(f"总请求数: {report['summary']['total_requests']}")
    print(f"平均响应时间: {report['summary']['avg_response_time']:.3f}秒")
    print(f"缓存命中率: {report['cache_stats']['hit_rate_percent']:.1f}%")

    # 获取缓存统计
    cache_stats = api_performance_optimizer.cache_manager.get_cache_stats()
    print(f"\n💾 缓存统计:")
    print(f"缓存类型: {cache_stats['cache_type']}")
    print(f"命中次数: {cache_stats['hits']}")
    print(f"未命中次数: {cache_stats['misses']}")
    print(f"命中率: {cache_stats['hit_rate_percent']:.1f}%")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_api_performance_optimization())