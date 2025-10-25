"""
读写分离架构 - Database Read-Write Splitting Architecture
支持主从分离、负载均衡、故障转移的数据库访问层
"""

import asyncio
import time
import random
import logging
from typing import Dict, List, Any, Optional, Union, Callable, AsyncGenerator
from enum import Enum
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import defaultdict, deque
import statistics

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import text
import asyncpg

from .connection_pool import ConnectionPoolManager

logger = logging.getLogger(__name__)


class DatabaseRole(Enum):
    """数据库角色枚举"""
    MASTER = "master"      # 主库（写操作）
    REPLICA = "replica"    # 从库（读操作）
    ANALYTICS = "analytics"  # 分析库（复杂查询）


class QueryType(Enum):
    """查询类型枚举"""
    READ = "read"          # 读查询（SELECT）
    WRITE = "write"        # 写查询（INSERT, UPDATE, DELETE）
    TRANSACTION = "transaction"  # 事务操作
    ANALYTICS = "analytics"  # 分析查询（复杂SELECT）


@dataclass
class DatabaseNode:
    """数据库节点信息"""
    id: str
    role: DatabaseRole
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int = 10
    max_overflow: int = 20
    is_available: bool = True
    last_health_check: float = field(default_factory=time.time)
    response_time: float = 0.0
    error_count: int = 0
    connection_count: int = 0
    weight: int = 1  # 负载均衡权重

    def get_connection_url(self) -> str:
        """获取数据库连接URL"""
        return (
            f"postgresql+asyncpg://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )


@dataclass
class QueryStats:
    """查询统计信息"""
    query_type: QueryType
    node_id: str
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class LoadBalanceStats:
    """负载均衡统计"""
    node_id: str
    request_count: int
    avg_response_time: float
    error_rate: float
    current_connections: int
    last_used: float = field(default_factory=time.time)


class LoadBalanceStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"      # 轮询
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"  # 加权轮询
    LEAST_CONNECTIONS = "least_connections"  # 最少连接
    RESPONSE_TIME = "response_time"  # 响应时间
    RANDOM = "random"               # 随机


class ReadWriteSplitEngine:
    """读写分离引擎"""

    def __init__(
        self,
        master_node: DatabaseNode,
        replica_nodes: List[DatabaseNode],
        analytics_nodes: Optional[List[DatabaseNode]] = None,
        load_balance_strategy: LoadBalanceStrategy = LoadBalanceStrategy.LEAST_CONNECTIONS,
        health_check_interval: int = 30,
        failure_detection_threshold: int = 3,
        max_retry_attempts: int = 3
    ):
        self.master_node = master_node
        self.replica_nodes = replica_nodes or []
        self.analytics_nodes = analytics_nodes or []
        self.load_balance_strategy = load_balance_strategy
        self.health_check_interval = health_check_interval
        self.failure_detection_threshold = failure_detection_threshold
        self.max_retry_attempts = max_retry_attempts

        # 连接引擎
        self.engines: Dict[str, AsyncEngine] = {}
        self.session_factories: Dict[str, sessionmaker] = {}

        # 负载均衡
        self.round_robin_index = defaultdict(int)
        self.weighted_round_robin_weight = defaultdict(int)

        # 统计和监控
        self.query_history: deque = deque(maxlen=10000)
        self.load_balance_stats: Dict[str, LoadBalanceStats] = {}
        self.node_health: Dict[str, bool] = {}
        self.node_response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # 健康检查任务
        self.health_check_task: Optional[asyncio.Task] = None

        # 初始化统计
        self._initialize_stats()

        logger.info(f"ReadWriteSplitEngine initialized with {len(replica_nodes)} replicas")

    def _initialize_stats(self):
        """初始化统计信息"""
        all_nodes = [self.master_node] + self.replica_nodes + self.analytics_nodes
        for node in all_nodes:
            self.node_health[node.id] = True
            self.load_balance_stats[node.id] = LoadBalanceStats(
                node_id=node.id,
                request_count=0,
                avg_response_time=0.0,
                error_rate=0.0,
                current_connections=0
            )

    async def initialize(self):
        """初始化所有数据库连接"""
        try:
            # 初始化主库连接
            await self._initialize_node(self.master_node)

            # 初始化从库连接
            for node in self.replica_nodes:
                await self._initialize_node(node)

            # 初始化分析库连接
            for node in self.analytics_nodes:
                await self._initialize_node(node)

            # 启动健康检查任务
            self.health_check_task = asyncio.create_task(self._health_check_loop())

            logger.info("ReadWriteSplitEngine initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize ReadWriteSplitEngine: {e}")
            raise

    async def _initialize_node(self, node: DatabaseNode):
        """初始化单个数据库节点"""
        try:
            # 创建异步引擎
            engine = create_async_engine(
                node.get_connection_url(),
                pool_size=node.pool_size,
                max_overflow=node.max_overflow,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600
            )

            # 创建会话工厂
            session_factory = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )

            self.engines[node.id] = engine
            self.session_factories[node.id] = session_factory

            # 测试连接
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            logger.info(f"Database node {node.id} initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize node {node.id}: {e}")
            node.is_available = False
            self.node_health[node.id] = False
            raise

    def _classify_query(self, query_text: str) -> QueryType:
        """分类查询类型"""
        query_upper = query_text.strip().upper()

        # 事务操作
        if any(keyword in query_upper for keyword in ['BEGIN', 'START TRANSACTION', 'COMMIT', 'ROLLBACK']):
            return QueryType.TRANSACTION

        # 写操作
        elif any(keyword in query_upper for keyword in ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']):
            return QueryType.WRITE

        # 分析查询（复杂SELECT）
        elif any(keyword in query_upper for keyword in ['GROUP BY', 'HAVING', 'WINDOW', 'WITH', 'OVER']):
            return QueryType.ANALYTICS

        # 读查询
        else:
            return QueryType.READ

    def _select_node_for_read(self, query_type: QueryType = QueryType.READ) -> DatabaseNode:
        """为读操作选择最优节点"""
        available_nodes = []

        if query_type == QueryType.ANALYTICS and self.analytics_nodes:
            available_nodes = [
                node for node in self.analytics_nodes
                if node.is_available and self.node_health[node.id]
            ]
        else:
            available_nodes = [
                node for node in self.replica_nodes
                if node.is_available and self.node_health[node.id]
            ]

        # 如果没有可用的从库，回退到主库
        if not available_nodes:
            logger.warning("No available replica nodes, falling back to master")
            return self.master_node

        # 根据负载均衡策略选择节点
        if self.load_balance_strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._round_robin_select(available_nodes)
        elif self.load_balance_strategy == LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_select(available_nodes)
        elif self.load_balance_strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(available_nodes)
        elif self.load_balance_strategy == LoadBalanceStrategy.RESPONSE_TIME:
            return self._response_time_select(available_nodes)
        elif self.load_balance_strategy == LoadBalanceStrategy.RANDOM:
            return self._random_select(available_nodes)
        else:
            return available_nodes[0]

    def _round_robin_select(self, nodes: List[DatabaseNode]) -> DatabaseNode:
        """轮询选择节点"""
        node_ids = [node.id for node in nodes]
        current_index = self.round_robin_index["read"] % len(nodes)
        self.round_robin_index["read"] += 1
        return nodes[current_index]

    def _weighted_round_robin_select(self, nodes: List[DatabaseNode]) -> DatabaseNode:
        """加权轮询选择节点"""
        total_weight = sum(node.weight for node in nodes)
        if total_weight == 0:
            return nodes[0]

        current_weight = self.weighted_round_robin_weight["read"] % total_weight
        self.weighted_round_robin_weight["read"] += 1

        for node in nodes:
            current_weight -= node.weight
            if current_weight < 0:
                return node

        return nodes[0]

    def _least_connections_select(self, nodes: List[DatabaseNode]) -> DatabaseNode:
        """最少连接选择节点"""
        return min(nodes, key=lambda node: self.load_balance_stats[node.id].current_connections)

    def _response_time_select(self, nodes: List[DatabaseNode]) -> DatabaseNode:
        """响应时间选择节点"""
        return min(nodes, key=lambda node: self.load_balance_stats[node.id].avg_response_time)

    def _random_select(self, nodes: List[DatabaseNode]) -> DatabaseNode:
        """随机选择节点"""
        return random.choice(nodes)

    @asynccontextmanager
    async def get_session(
        self,
        query_text: Optional[str] = None,
        force_master: bool = False
    ) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话（自动路由）"""
        if query_text:
            query_type = self._classify_query(query_text)
        else:
            query_type = QueryType.READ

        # 选择节点
        if force_master or query_type in [QueryType.WRITE, QueryType.TRANSACTION]:
            node = self.master_node
        else:
            node = self._select_node_for_read(query_type)

        # 获取会话工厂
        session_factory = self.session_factories.get(node.id)
        if not session_factory:
            raise RuntimeError(f"No session factory available for node {node.id}")

        # 创建会话并执行查询
        start_time = time.time()
        session_id = f"session_{int(time.time() * 1000)}_{id(asyncio.current_task())}"

        try:
            session = session_factory()
            await self._record_connection_start(node.id, session_id)

            yield session

            # 记录成功统计
            execution_time = (time.time() - start_time) * 1000
            await self._record_query_stats(node.id, query_type, execution_time, True)

        except Exception as e:
            # 记录失败统计
            execution_time = (time.time() - start_time) * 1000
            await self._record_query_stats(node.id, query_type, execution_time, False, str(e))

            # 如果是从库失败，尝试重试到主库
            if node.role == DatabaseRole.REPLICA and not force_master:
                logger.warning(f"Replica {node.id} failed, retrying on master: {e}")
                async with self.get_session(query_text, force_master=True) as master_session:
                    yield master_session
            else:
                raise

        finally:
            await self._record_connection_end(node.id, session_id)
            if 'session' in locals():
                await session.close()

    async def _record_connection_start(self, node_id: str, session_id: str):
        """记录连接开始"""
        self.load_balance_stats[node_id].current_connections += 1
        self.load_balance_stats[node_id].last_used = time.time()

    async def _record_connection_end(self, node_id: str, session_id: str):
        """记录连接结束"""
        self.load_balance_stats[node_id].current_connections = max(
            0, self.load_balance_stats[node_id].current_connections - 1
        )

    async def _record_query_stats(
        self,
        node_id: str,
        query_type: QueryType,
        execution_time: float,
        success: bool,
        error_message: Optional[str] = None
    ):
        """记录查询统计"""
        # 更新负载均衡统计
        stats = self.load_balance_stats[node_id]
        stats.request_count += 1
        stats.last_used = time.time()

        # 更新平均响应时间
        if stats.avg_response_time == 0:
            stats.avg_response_time = execution_time
        else:
            stats.avg_response_time = (stats.avg_response_time * 0.9 + execution_time * 0.1)

        # 更新错误率
        if not success:
            node = self._get_node_by_id(node_id)
            if node:
                node.error_count += 1

        # 记录查询历史
        query_stats = QueryStats(
            query_type=query_type,
            node_id=node_id,
            execution_time=execution_time,
            success=success,
            error_message=error_message
        )
        self.query_history.append(query_stats)

        # 更新响应时间历史
        self.node_response_times[node_id].append(execution_time)

    def _get_node_by_id(self, node_id: str) -> Optional[DatabaseNode]:
        """根据ID获取节点"""
        all_nodes = [self.master_node] + self.replica_nodes + self.analytics_nodes
        for node in all_nodes:
            if node.id == node_id:
                return node
        return None

    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    async def _perform_health_checks(self):
        """执行健康检查"""
        all_nodes = [self.master_node] + self.replica_nodes + self.analytics_nodes

        for node in all_nodes:
            try:
                await self._check_node_health(node)
            except Exception as e:
                logger.error(f"Health check failed for node {node.id}: {e}")

    async def _check_node_health(self, node: DatabaseNode):
        """检查单个节点健康状态"""
        engine = self.engines.get(node.id)
        if not engine:
            return

        start_time = time.time()

        try:
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()

            response_time = (time.time() - start_time) * 1000
            node.response_time = response_time
            node.last_health_check = time.time()

            # 如果之前不健康，现在恢复健康
            if not self.node_health[node.id]:
                logger.info(f"Node {node.id} is back to healthy")
                self.node_health[node.id] = True
                node.is_available = True

            # 重置错误计数
            node.error_count = 0

        except Exception as e:
            logger.warning(f"Health check failed for node {node.id}: {e}")
            node.error_count += 1
            node.last_health_check = time.time()

            # 如果错误次数超过阈值，标记为不健康
            if node.error_count >= self.failure_detection_threshold:
                logger.error(f"Node {node.id} marked as unhealthy after {node.error_count} failures")
                self.node_health[node.id] = False
                node.is_available = False

    async def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        total_queries = len(self.query_history)
        recent_queries = [q for q in self.query_history if time.time() - q.timestamp < 3600]

        # 按查询类型统计
        query_type_stats = defaultdict(int)
        success_rate = 0

        for query in recent_queries:
            query_type_stats[query.query_type.value] += 1

        if recent_queries:
            success_count = sum(1 for q in recent_queries if q.success)
            success_rate = (success_count / len(recent_queries)) * 100

        # 节点统计
        node_stats = {}
        for node_id, stats in self.load_balance_stats.items():
            node = self._get_node_by_id(node_id)
            if node:
                node_stats[node_id] = {
                    "role": node.role.value,
                    "host": f"{node.host}:{node.port}",
                    "is_available": node.is_available,
                    "request_count": stats.request_count,
                    "avg_response_time": stats.avg_response_time,
                    "current_connections": stats.current_connections,
                    "error_count": node.error_count,
                    "last_used": stats.last_used
                }

        return {
            "total_queries": total_queries,
            "recent_queries_1h": len(recent_queries),
            "success_rate": round(success_rate, 2),
            "query_type_distribution": dict(query_type_stats),
            "node_stats": node_stats,
            "load_balance_strategy": self.load_balance_strategy.value,
            "healthy_nodes": sum(1 for healthy in self.node_health.values() if healthy),
            "total_nodes": len(self.node_health)
        }

    async def get_query_performance(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取查询性能数据"""
        recent_queries = list(self.query_history)[-limit:]

        return [
            {
                "query_type": q.query_type.value,
                "node_id": q.node_id,
                "execution_time": q.execution_time,
                "success": q.success,
                "error_message": q.error_message,
                "timestamp": q.timestamp
            }
            for q in recent_queries
        ]

    async def analyze_performance(self) -> Dict[str, Any]:
        """分析性能数据"""
        if not self.query_history:
            return {"error": "No query history available"}

        # 响应时间分析
        execution_times = [q.execution_time for q in self.query_history]

        # 按节点分析
        node_performance = defaultdict(list)
        for q in self.query_history:
            node_performance[q.node_id].append(q.execution_time)

        node_analysis = {}
        for node_id, times in node_performance.items():
            node_analysis[node_id] = {
                "count": len(times),
                "avg_time": statistics.mean(times),
                "min_time": min(times),
                "max_time": max(times),
                "median_time": statistics.median(times)
            }

        # 按查询类型分析
        type_performance = defaultdict(list)
        for q in self.query_history:
            type_performance[q.query_type.value].append(q.execution_time)

        type_analysis = {}
        for query_type, times in type_performance.items():
            type_analysis[query_type] = {
                "count": len(times),
                "avg_time": statistics.mean(times),
                "min_time": min(times),
                "max_time": max(times),
                "median_time": statistics.median(times)
            }

        return {
            "overall": {
                "total_queries": len(execution_times),
                "avg_time": statistics.mean(execution_times),
                "min_time": min(execution_times),
                "max_time": max(execution_times),
                "median_time": statistics.median(execution_times),
                "p95_time": execution_times[int(len(execution_times) * 0.95)],
                "p99_time": execution_times[int(len(execution_times) * 0.99)]
            },
            "by_node": node_analysis,
            "by_query_type": type_analysis
        }

    async def cleanup(self):
        """清理资源"""
        try:
            # 停止健康检查任务
            if self.health_check_task:
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass

            # 关闭所有引擎
            for engine in self.engines.values():
                await engine.dispose()

            logger.info("ReadWriteSplitEngine cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# 全局读写分离引擎实例
_read_write_engine: Optional[ReadWriteSplitEngine] = None


async def initialize_read_write_split(
    master_config: Dict[str, Any],
    replica_configs: List[Dict[str, Any]],
    analytics_configs: Optional[List[Dict[str, Any]]] = None,
    **kwargs
) -> ReadWriteSplitEngine:
    """初始化读写分离引擎"""
    global _read_write_engine

    # 创建主库节点
    master_node = DatabaseNode(
        id=master_config["id"],
        role=DatabaseRole.MASTER,
        **master_config
    )

    # 创建从库节点
    replica_nodes = []
    for config in replica_configs:
        replica_node = DatabaseNode(
            role=DatabaseRole.REPLICA,
            **config
        )
        replica_nodes.append(replica_node)

    # 创建分析库节点
    analytics_nodes = []
    if analytics_configs:
        for config in analytics_configs:
            analytics_node = DatabaseNode(
                role=DatabaseRole.ANALYTICS,
                **config
            )
            analytics_nodes.append(analytics_node)

    # 创建并初始化引擎
    _read_write_engine = ReadWriteSplitEngine(
        master_node=master_node,
        replica_nodes=replica_nodes,
        analytics_nodes=analytics_nodes,
        **kwargs
    )

    await _read_write_engine.initialize()

    return _read_write_engine


def get_read_write_engine() -> Optional[ReadWriteSplitEngine]:
    """获取读写分离引擎实例"""
    return _read_write_engine


async def cleanup_read_write_split():
    """清理读写分离引擎"""
    global _read_write_engine
    if _read_write_engine:
        await _read_write_engine.cleanup()
        _read_write_engine = None