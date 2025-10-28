"""
性能资源管理器
实现连接池优化、资源管理、负载均衡和资源监控
"""

import asyncio
import time
import logging
import psutil
import gc
from typing import Any, Dict, List, Optional, Set, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import threading
import weakref

import aioredis
import asyncpg
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """资源类型"""
    DATABASE = "database"
    REDIS = "redis"
    HTTP_CLIENT = "http_client"
    AI_SERVICE = "ai_service"
    FILE_HANDLE = "file_handle"
    MEMORY = "memory"
    CPU = "cpu"


class ResourceStatus(Enum):
    """资源状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OVERLOADED = "overloaded"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


@dataclass
class ResourceMetrics:
    """资源指标"""
    resource_id: str
    resource_type: ResourceType
    status: ResourceStatus
    created_at: float
    last_used: float
    usage_count: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0
    current_connections: int = 0
    max_connections: int = 0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    last_health_check: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def update_usage(self, response_time: float, success: bool = True):
        """更新使用统计"""
        self.last_used = time.time()
        self.usage_count += 1

        if not success:
            self.error_count += 1

        # 计算移动平均响应时间
        self.avg_response_time = (
            (self.avg_response_time * (self.usage_count - 1) + response_time) /
            self.usage_count
        )

    def get_error_rate(self) -> float:
        """获取错误率"""
        if self.usage_count == 0:
            return 0.0
        return self.error_count / self.usage_count

    def get_health_score(self) -> float:
        """获取健康分数 (0-100)"""
        # 基于错误率、响应时间等计算健康分数
        error_penalty = self.get_error_rate() * 100
        response_penalty = min(50, self.avg_response_time * 10)

        score = max(0, 100 - error_penalty - response_penalty)
        return score


class DatabaseConnectionPool:
    """数据库连接池管理器"""

    def __init__(
        self,
        dsn: str,
        min_size: int = 5,
        max_size: int = 20,
        max_inactive_time: int = 300,
        max_queries: int = 50000,
        command_timeout: float = 60.0
    ):
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.max_inactive_time = max_inactive_time
        self.max_queries = max_queries
        self.command_timeout = command_timeout

        self.pool: Optional[asyncpg.Pool] = None
        self.metrics = ResourceMetrics(
            resource_id=f"db_pool_{hash(dsn) % 10000:04d}",
            resource_type=ResourceType.DATABASE,
            status=ResourceStatus.FAILED,
            created_at=time.time(),
            last_used=time.time()
        )
        self._lock = asyncio.Lock()

    async def initialize(self):
        """初始化连接池"""
        if self.pool is not None:
            return

        async with self._lock:
            if self.pool is not None:
                return

            try:
                self.pool = await asyncpg.create_pool(
                    self.dsn,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    command_timeout=self.command_timeout,
                    max_inactive_connection_lifetime=self.max_inactive_time,
                    max_queries_per_connection=self.max_queries
                )

                self.metrics.status = ResourceStatus.HEALTHY
                self.metrics.last_health_check = time.time()
                logger.info(f"Database connection pool initialized: {self.metrics.resource_id}")

            except Exception as e:
                self.metrics.status = ResourceStatus.FAILED
                self.metrics.last_health_check = time.time()
                logger.error(f"Failed to initialize database pool: {e}")
                raise

    async def execute_query(self, query: str, *args, timeout: Optional[float] = None) -> Any:
        """执行数据库查询"""
        if self.pool is None:
            await self.initialize()

        start_time = time.time()
        success = True

        try:
            async with self.pool.acquire(timeout=timeout or self.command_timeout) as conn:
                result = await conn.fetch(query, *args)
                self.metrics.current_connections = self.pool.get_size()
                return result

        except Exception as e:
            success = False
            self.metrics.error_count += 1
            logger.error(f"Database query failed: {e}")
            raise

        finally:
            response_time = time.time() - start_time
            self.metrics.update_usage(response_time, success)

    async def close(self):
        """关闭连接池"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info(f"Database connection pool closed: {self.metrics.resource_id}")

    def get_metrics(self) -> ResourceMetrics:
        """获取连接池指标"""
        if self.pool:
            self.metrics.current_connections = self.pool.get_size()
            self.metrics.max_connections = self.pool.get_max_size()
            self.metrics.last_health_check = time.time()

        return self.metrics


class RedisConnectionPool:
    """Redis连接池管理器"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 20,
        retry_on_timeout: bool = True,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.retry_on_timeout = retry_on_timeout
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout

        self.pool: Optional[aioredis.ConnectionPool] = None
        self.redis: Optional[aioredis.Redis] = None
        self.metrics = ResourceMetrics(
            resource_id=f"redis_pool_{hash(f'{host}:{port}:{db}') % 10000:04d}",
            resource_type=ResourceType.REDIS,
            status=ResourceStatus.FAILED,
            created_at=time.time(),
            last_used=time.time()
        )
        self._lock = asyncio.Lock()

    async def initialize(self):
        """初始化Redis连接池"""
        if self.pool is not None:
            return

        async with self._lock:
            if self.pool is not None:
                return

            try:
                self.pool = aioredis.ConnectionPool.from_url(
                    f"redis://{self.host}:{self.port}/{self.db}",
                    password=self.password,
                    max_connections=self.max_connections,
                    retry_on_timeout=self.retry_on_timeout,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout
                )

                self.redis = aioredis.Redis(connection_pool=self.pool)

                # 测试连接
                await self.redis.ping()

                self.metrics.status = ResourceStatus.HEALTHY
                self.metrics.last_health_check = time.time()
                logger.info(f"Redis connection pool initialized: {self.metrics.resource_id}")

            except Exception as e:
                self.metrics.status = ResourceStatus.FAILED
                self.metrics.last_health_check = time.time()
                logger.error(f"Failed to initialize Redis pool: {e}")
                raise

    async def execute_command(self, command: str, *args, timeout: Optional[float] = None) -> Any:
        """执行Redis命令"""
        if self.redis is None:
            await self.initialize()

        start_time = time.time()
        success = True

        try:
            if timeout:
                result = await asyncio.wait_for(
                    self.redis.execute_command(command, *args),
                    timeout=timeout
                )
            else:
                result = await self.redis.execute_command(command, *args)

            return result

        except Exception as e:
            success = False
            self.metrics.error_count += 1
            logger.error(f"Redis command failed: {e}")
            raise

        finally:
            response_time = time.time() - start_time
            self.metrics.update_usage(response_time, success)

    async def close(self):
        """关闭Redis连接池"""
        if self.redis:
            await self.redis.close()
        if self.pool:
            await self.pool.disconnect()
        self.redis = None
        self.pool = None
        logger.info(f"Redis connection pool closed: {self.metrics.resource_id}")

    def get_metrics(self) -> ResourceMetrics:
        """获取Redis连接池指标"""
        self.metrics.last_health_check = time.time()
        return self.metrics


class ResourceManager:
    """资源管理器"""

    def __init__(self):
        self.resources: Dict[str, ResourceMetrics] = {}
        self.pools: Dict[str, Union[DatabaseConnectionPool, RedisConnectionPool]] = {}
        self.resource_configs: Dict[str, Dict] = {}

        # 监控配置
        self.monitoring_interval = 30  # 30秒
        self.health_check_interval = 60  # 1分钟
        self.auto_cleanup_interval = 300  # 5分钟

        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """初始化资源管理器"""
        # 启动监控任务
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("Resource manager initialized")

    async def shutdown(self):
        """关闭资源管理器"""
        # 取消监控任务
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()

        # 关闭所有连接池
        for pool in self.pools.values():
            if hasattr(pool, 'close'):
                await pool.close()

        logger.info("Resource manager shutdown")

    async def create_database_pool(
        self,
        pool_id: str,
        dsn: str,
        min_size: int = 5,
        max_size: int = 20,
        **kwargs
    ) -> DatabaseConnectionPool:
        """创建数据库连接池"""
        pool = DatabaseConnectionPool(
            dsn=dsn,
            min_size=min_size,
            max_size=max_size,
            **kwargs
        )

        await pool.initialize()
        self.pools[pool_id] = pool
        self.resources[pool_id] = pool.get_metrics()

        logger.info(f"Database pool created: {pool_id}")
        return pool

    async def create_redis_pool(
        self,
        pool_id: str,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 20,
        **kwargs
    ) -> RedisConnectionPool:
        """创建Redis连接池"""
        pool = RedisConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            max_connections=max_connections,
            **kwargs
        )

        await pool.initialize()
        self.pools[pool_id] = pool
        self.resources[pool_id] = pool.get_metrics()

        logger.info(f"Redis pool created: {pool_id}")
        return pool

    async def get_pool(self, pool_id: str) -> Optional[Union[DatabaseConnectionPool, RedisConnectionPool]]:
        """获取连接池"""
        return self.pools.get(pool_id)

    def get_resource_metrics(self, resource_id: str) -> Optional[ResourceMetrics]:
        """获取资源指标"""
        return self.resources.get(resource_id)

    async def _monitoring_loop(self):
        """监控循环"""
        while True:
            try:
                await asyncio.sleep(self.monitoring_interval)
                await self._collect_system_metrics()
                await self._check_resource_health()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(5)

    async def _cleanup_loop(self):
        """清理循环"""
        while True:
            try:
                await asyncio.sleep(self.auto_cleanup_interval)
                await self._cleanup_resources()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resource cleanup error: {e}")
                await asyncio.sleep(5)

    async def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()

            # 更新系统资源指标
            self.resources["system_cpu"] = ResourceMetrics(
                resource_id="system_cpu",
                resource_type=ResourceType.CPU,
                status=ResourceStatus.HEALTHY,
                created_at=time.time(),
                last_used=time.time(),
                cpu_usage=cpu_percent,
                metadata={"cpu_count": psutil.cpu_count()}
            )

            self.resources["system_memory"] = ResourceMetrics(
                resource_id="system_memory",
                resource_type=ResourceType.MEMORY,
                status=ResourceStatus.HEALTHY,
                created_at=time.time(),
                last_used=time.time(),
                memory_usage=memory_info.percent,
                metadata={
                    "total_memory": memory_info.total,
                    "available_memory": memory_info.available,
                    "used_memory": memory_info.used
                }
            )

        except Exception as e:
            logger.error(f"System metrics collection error: {e}")

    async def _check_resource_health(self):
        """检查资源健康状态"""
        for pool_id, pool in self.pools.items():
            try:
                # 执行健康检查
                if hasattr(pool, 'redis'):
                    # Redis健康检查
                    await pool.redis.ping()
                elif hasattr(pool, 'pool'):
                    # 数据库健康检查
                    async with pool.pool.acquire() as conn:
                        await conn.fetch("SELECT 1")

                # 更新健康状态
                metrics = pool.get_metrics()
                metrics.status = ResourceStatus.HEALTHY
                metrics.last_health_check = time.time()

            except Exception as e:
                # 标记为失败状态
                metrics = pool.get_metrics()
                if metrics.health_score() < 30:
                    metrics.status = ResourceStatus.FAILED
                else:
                    metrics.status = ResourceStatus.DEGRADED

                metrics.last_health_check = time.time()
                logger.warning(f"Resource health check failed for {pool_id}: {e}")

    async def _cleanup_resources(self):
        """清理未使用的资源"""
        current_time = time.time()
        cleanup_threshold = 1800  # 30分钟未使用

        for pool_id, pool in list(self.pools.items()):
            metrics = pool.get_metrics()

            # 检查是否长时间未使用
            if current_time - metrics.last_used > cleanup_threshold:
                if metrics.health_score() > 70:  # 只清理健康的资源
                    logger.info(f"Cleaning up unused resource: {pool_id}")
                    await pool.close()
                    del self.pools[pool_id]
                    del self.resources[pool_id]

        # 垃圾回收
        try:
            collected = gc.collect()
            if collected > 0:
                logger.debug(f"Garbage collected: {collected} objects")
        except Exception as e:
            logger.error(f"Garbage collection error: {e}")

    def get_comprehensive_stats(self) -> Dict:
        """获取综合统计"""
        stats = {
            "timestamp": time.time(),
            "total_resources": len(self.resources),
            "total_pools": len(self.pools),
            "resource_types": defaultdict(int),
            "resource_statuses": defaultdict(int),
            "system_metrics": {},
            "pool_details": {}
        }

        # 统计资源类型和状态
        for resource in self.resources.values():
            stats["resource_types"][resource.resource_type.value] += 1
            stats["resource_statuses"][resource.status.value] += 1

        # 获取系统指标
        if "system_cpu" in self.resources:
            stats["system_metrics"]["cpu_usage"] = self.resources["system_cpu"].cpu_usage
        if "system_memory" in self.resources:
            stats["system_metrics"]["memory_usage"] = self.resources["system_memory"].memory_usage

        # 获取连接池详情
        for pool_id, pool in self.pools.items():
            metrics = pool.get_metrics()
            stats["pool_details"][pool_id] = {
                "type": metrics.resource_type.value,
                "status": metrics.status.value,
                "usage_count": metrics.usage_count,
                "error_rate": metrics.get_error_rate(),
                "avg_response_time": metrics.avg_response_time,
                "health_score": metrics.get_health_score(),
                "current_connections": metrics.current_connections,
                "max_connections": metrics.max_connections
            }

        return stats

    async def optimize_resource_usage(self):
        """优化资源使用"""
        optimization_suggestions = []

        # 分析连接池使用情况
        for pool_id, pool in self.pools.items():
            metrics = pool.get_metrics()

            # 检查错误率
            error_rate = metrics.get_error_rate()
            if error_rate > 0.1:  # 错误率超过10%
                optimization_suggestions.append({
                    "resource_id": pool_id,
                    "type": "high_error_rate",
                    "severity": "high",
                    "message": f"Resource {pool_id} has high error rate: {error_rate:.2%}",
                    "suggestion": "Check resource health and consider scaling or replacement"
                })

            # 检查响应时间
            if metrics.avg_response_time > 1.0:  # 平均响应时间超过1秒
                optimization_suggestions.append({
                    "resource_id": pool_id,
                    "type": "slow_response",
                    "severity": "medium",
                    "message": f"Resource {pool_id} has slow response time: {metrics.avg_response_time:.3f}s",
                    "suggestion": "Consider optimizing queries or scaling resources"
                })

            # 检查连接数
            if hasattr(metrics, 'current_connections') and hasattr(metrics, 'max_connections'):
                utilization = metrics.current_connections / max(1, metrics.max_connections)
                if utilization > 0.8:  # 连接池使用率超过80%
                    optimization_suggestions.append({
                        "resource_id": pool_id,
                        "type": "high_utilization",
                        "severity": "medium",
                        "message": f"Resource {pool_id} has high utilization: {utilization:.1%}",
                        "suggestion": "Consider increasing pool size or optimizing connection usage"
                    })

        # 分析系统资源
        if "system_memory" in self.resources:
            memory_metrics = self.resources["system_memory"]
            if memory_metrics.memory_usage > 80:  # 内存使用率超过80%
                optimization_suggestions.append({
                    "resource_id": "system_memory",
                    "type": "high_memory_usage",
                    "severity": "high",
                    "message": f"High memory usage: {memory_metrics.memory_usage:.1f}%",
                    "suggestion": "Consider memory optimization or scaling"
                })

        return optimization_suggestions


# 全局资源管理器实例
_resource_manager: Optional[ResourceManager] = None


async def get_resource_manager() -> ResourceManager:
    """获取全局资源管理器实例"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
        await _resource_manager.initialize()
    return _resource_manager


# 便捷函数
async def create_database_pool(
    pool_id: str,
    dsn: str,
    min_size: int = 5,
    max_size: int = 20,
    **kwargs
) -> DatabaseConnectionPool:
    """创建数据库连接池"""
    manager = await get_resource_manager()
    return await manager.create_database_pool(
        pool_id, dsn, min_size, max_size, **kwargs
    )


async def create_redis_pool(
    pool_id: str,
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
    max_connections: int = 20,
    **kwargs
) -> RedisConnectionPool:
    """创建Redis连接池"""
    manager = await get_resource_manager()
    return await manager.create_redis_pool(
        pool_id, host, port, db, password, max_connections, **kwargs
    )


async def get_resource_stats() -> Dict:
    """获取资源统计"""
    manager = await get_resource_manager()
    return manager.get_comprehensive_stats()