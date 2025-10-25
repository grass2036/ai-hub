"""
数据库连接池管理器
提供高性能的数据库连接池管理、监控和优化功能
"""
import asyncio
import time
import json
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager, asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import logging
from collections import deque, defaultdict
import psutil

logger = logging.getLogger(__name__)

@dataclass
class ConnectionPoolStats:
    """连接池统计信息"""
    pool_size: int
    checked_in: int
    checked_out: int
    overflow: int
    invalid: int
    total_connections: int
    creation_time: datetime
    last_check_time: datetime
    avg_checkout_time: float
    max_checkout_time: float
    checkout_requests: int
    checkout_failures: int

@dataclass
class ConnectionMetrics:
    """连接性能指标"""
    connection_id: str
    created_at: datetime
    last_used: datetime
    usage_count: int
    total_query_time: float
    query_count: int
    avg_query_time: float
    max_query_time: float
    is_active: bool
    database: str
    user_id: Optional[str]
    session_id: Optional[str]

class ConnectionPoolManager:
    """连接池管理器"""

    def __init__(self, database_url: str, pool_config: Dict[str, Any] = None):
        self.database_url = database_url
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[sessionmaker] = None
        self.pool_stats: Dict[str, ConnectionPoolStats] = {}
        self.connection_metrics: Dict[str, ConnectionMetrics] = {}
        self.active_connections: Dict[str, Dict] = {}

        # 默认配置
        self.default_config = {
            'pool_size': 20,  # 基础连接数
            'max_overflow': 30,  # 溢出连接数
            'pool_timeout': 30,  # 获取连接超时时间（秒）
            'pool_recycle': 3600,  # 连接回收时间（秒）
            'pool_pre_ping': True,  # 连接前ping检查
            'pool_reset_on_return': 'rollback',  # 连接返回时的操作
            'echo': False,  # SQL日志
            'future': True,  # 使用Future API
            'isolation_level': 'READ_COMMITTED',
            'poolclass': QueuePool,
            'connect_args': {
                'connect_timeout': 10,
                'command_timeout': 30,
                'server_settings': {
                    'application_name': 'ai-hub-pool',
                    'timezone': 'UTC'
                }
            },
            'pool_reset_on_return': 'commit'
        }

        # 合并用户配置
        self.config = {**self.default_config, **(pool_config or {})}

        # 性能监控
        self.monitoring_enabled = True
        self.performance_history = deque(maxlen=1000)
        self.connection_timeout_threshold = 60.0  # 连接超时阈值
        self.long_query_threshold = 10.0  # 长查询阈值（秒）

        # 自适应调整
        self.adaptive_scaling = True
        self.scaling_history = deque(maxlen=100)
        self.auto_scale_threshold = {
            'scale_up': 0.8,  # 80%连接率时扩容
            'scale_down': 0.3,  # 30%连接率时缩容
            'check_interval': 300  # 5分钟检查一次
        }

    async def initialize_pool(self) -> bool:
        """初始化连接池"""
        try:
            logger.info("Initializing database connection pool...")

            # 创建异步引擎
            self.engine = create_async_engine(
                self.database_url,
                **self.config
            )

            # 创建session工厂
            self.session_factory = sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False
            )

            # 测试连接
            await self._test_connection()

            # 启动监控
            if self.monitoring_enabled:
                asyncio.create_task(self._monitor_pool())
                asyncio.create_task(self._monitor_adaptive_scaling())
                asyncio.create_task(self._monitor_system_resources())

            logger.info(f"Database connection pool initialized successfully")
            logger.info(f"Pool configuration: size={self.config['pool_size']}, max_overflow={self.config['max_overflow']}")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            return False

    async def _test_connection(self):
        """测试数据库连接"""
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
        except Exception as e:
            raise Exception(f"Database connection test failed: {e}")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话"""
        if not self.session_factory:
            raise RuntimeError("Connection pool not initialized")

        start_time = time.time()
        session_id = f"session_{int(time.time() * 1000)}_{id(asyncio.current_task())}"

        try:
            # 创建会话
            session = self.session_factory()
            session_id = f"session_{int(time.time() * 1000)}_{id(asyncio.current_task())}"

            # 记录连接开始
            await self._record_connection_start(session_id, session)

            yield session

        except Exception as e:
            logger.error(f"Failed to get database session: {e}")
            raise
        finally:
            # 记录连接结束
            checkout_time = (time.time() - start_time) * 1000
            await self._record_connection_end(session_id, checkout_time)

    async def _record_connection_start(self, session_id: str, session: AsyncSession):
        """记录连接开始"""
        if not self.monitoring_enabled:
            return

        self.active_connections[session_id] = {
            'session': session,
            'start_time': datetime.utcnow(),
            'query_count': 0,
            'total_query_time': 0.0,
            'max_query_time': 0.0
        }

    async def _record_connection_end(self, session_id: str, checkout_time: float):
        """记录连接结束"""
        if not self.monitoring_enabled or session_id not in self.active_connections:
            return

        conn_info = self.active_connections[session_id]
        duration = (datetime.utcnow() - conn_info['start_time']).total_seconds()

        # 更新连接指标
        if session_id not in self.connection_metrics:
            self.connection_metrics[session_id] = ConnectionMetrics(
                connection_id=session_id,
                created_at=conn_info['start_time'],
                last_used=datetime.utcnow(),
                usage_count=1,
                total_query_time=conn_info['total_query_time'],
                query_count=conn_info['query_count'],
                avg_query_time=conn_info['total_query_time'] / max(conn_info['query_count'], 1),
                max_query_time=conn_info['max_query_time'],
                is_active=False
            )
        else:
            metrics = self.connection_metrics[session_id]
            metrics.usage_count += 1
            metrics.last_used = datetime.utcnow()
            metrics.is_active = False

        # 记录性能历史
        self.performance_history.append({
            'session_id': session_id,
            'checkout_time_ms': checkout_time,
            'session_duration_s': duration,
            'query_count': conn_info['query_count'],
            'avg_query_time_ms': conn_info['total_query_time'] / max(conn_info['query_count'], 1),
            'max_query_time_ms': conn_info['max_query_time'],
            'timestamp': datetime.utcnow()
        })

        # 清理活跃连接记录
        del self.active_connections[session_id]

    async def _monitor_pool(self):
        """监控连接池状态"""
        if not self.monitoring_enabled:
            return

        while True:
            try:
                await self._update_pool_stats()
                await self._check_pool_health()
                await self._log_pool_performance()

                # 每30秒检查一次
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in pool monitoring: {e}")
                await asyncio.sleep(60)  # 错误时等待更长时间

    async def _update_pool_stats(self):
        """更新连接池统计"""
        if not self.engine:
            return

        try:
            pool = self.engine.pool
            pool_name = "default"

            stats = ConnectionPool_size = ConnectionPoolStats(
                pool_size=pool.size(),
                checked_in=pool.checkedin(),
                checked_out=pool.checkedout(),
                overflow=pool.overflow(),
                invalid=pool.invalid(),
                total_connections=pool.size() + pool.overflow(),
                creation_time=datetime.utcnow(),  # 实际应该从配置中获取
                last_check_time=datetime.utcnow(),
                avg_checkout_time=0.0,  # 需要从历史数据计算
                max_checkout_time=0.0,
                checkout_requests=0,
                checkout_failures=0
            )

            self.pool_stats[pool_name] = stats

        except Exception as e:
            logger.error(f"Error updating pool stats: {e}")

    async def _check_pool_health(self):
        """检查连接池健康状态"""
        if not self.engine:
            return

        try:
            pool = self.engine.pool
            pool_name = "default"

            # 检查连接池健康指标
            stats = self.pool_stats.get(pool_name)
            if not stats:
                return

            # 连接池使用率
            utilization_rate = stats.checked_out / stats.total_connections if stats.total_connections > 0 else 0

            # 检查��否需要告警
            if utilization_rate > 0.9:
                logger.warning(f"Pool utilization high: {utilization_rate:.2f} (checked_out={stats.checked_out}, total={stats.total_connections})")

            if stats.overflow > 0:
                logger.warning(f"Pool overflow detected: {stats.overflow} overflow connections")

            if stats.invalid > 0:
                logger.warning(f"Invalid connections detected: {stats.invalid}")

            # 检查连接超时
            timeout_count = len([
                m for m in self.performance_history
                if m['checkout_time_ms'] > self.connection_timeout_threshold * 1000
            ])

            if timeout_count > 5:
                logger.warning(f"High connection timeout count: {timeout_count} in last {len(self.performance_history)} sessions")

        except Exception as e:
            logger.error(f"Error checking pool health: {e}")

    async def _log_pool_performance(self):
        """记录连接池性能"""
        if not self.engine:
            return

        try:
            pool = self.engine.pool
            pool_name = "default"
            stats = self.pool_stats.get(pool_name)

            if not stats or len(self.performance_history) < 10:
                return

            # 计算平均连接时间
            recent_sessions = list(self.performance_history)[-10:]
            avg_checkout_time = sum(m['checkout_time_ms'] for m in recent_sessions) / len(recent_sessions)

            # 记录性能日志
            logger.info(f"Pool Performance - "
                          f"Size: {stats.pool_size}, "
                          f"Used: {stats.checked_out}, "
                          f"Avg Checkout: {avg_checkout_time:.2f}ms, "
                          f"Overflow: {stats.overflow}")

        except Exception as e:
            logger.error(f"Error logging pool performance: {e}")

    async def _monitor_adaptive_scaling(self):
        """监控并执行自适应扩缩容"""
        if not self.adaptive_scaling or not self.engine:
            return

        while True:
            try:
                await self._check_scaling_need()
                await asyncio.sleep(self.auto_scale_threshold['check_interval'])

            except Exception as e:
                logger.error(f"Error in adaptive scaling: {e}")
                await asyncio.sleep(60)

    async def _check_scaling_need(self):
        """检查是否需要扩缩容"""
        try:
            pool = self.engine.pool
            current_size = pool.size()
            current_overflow = pool.overflow()
            checked_out = pool.checkedout()

            total_connections = current_size + current_overflow
            utilization_rate = checked_out / total_connections if total_connections > 0 else 0

            # 记录历史数据
            self.scaling_history.append({
                'timestamp': datetime.utcnow(),
                'pool_size': current_size,
                'overflow': current_overflow,
                'utilization_rate': utilization_rate,
                'total_connections': total_connections
            })

            # 保持历史记录在合理范围内
            if len(self.scaling_history) > 100:
                self.scaling_history.popleft()

            # 检查是否需要扩容
            if utilization_rate > self.auto_scale_threshold['scale_up']:
                await self._scale_up_pool()

            # 检查是否需要缩容
            elif utilization_rate < self.auto_scale_threshold['scale_down'] and current_size > self.config['pool_size']:
                await self._scale_down_pool()

        except Exception as e:
            logger.error(f"Error checking scaling need: {e}")

    async def _scale_up_pool(self):
        """扩容连接池"""
        try:
            pool = self.engine.pool
            current_size = pool.size()
            max_size = self.config['max_overflow'] + self.config['pool_size']

            if current_size < max_size:
                new_size = min(current_size + 5, max_size)
                logger.info(f"Scaling up pool from {current_size} to {new_size}")
                # 实际的扩容需要重新创建引擎
                # 这是一个复杂操作，需要谨慎处理

        except Exception as e:
            logger.error(f"Error scaling up pool: {e}")

    async def _scale_down_pool(self):
        """缩容连接池"""
        try:
            pool = self.engine.pool
            current_size = pool.size()
            min_size = self.config['pool_size']

            if current_size > min_size:
                new_size = max(current_size - 2, min_size)
                logger.info(f"Scaling down pool from {current_size} to {new_size}")
                # 实际的缩容需要重新创建引擎
                # 这是一个复杂操作，需要谨慎处理

        except Exception as e:
            logger.error(f"Error scaling down pool: {e}")

    async def _monitor_system_resources(self):
        """监控系统资源"""
        if not self.monitoring_enabled:
            return

        while True:
            try:
                # 获取系统资源使用情况
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_info = psutil.virtual_memory()
                memory_percent = memory_info.percent

                # 获取连接池信息
                pool = self.engine.pool if self.engine else None
                pool_info = {}
                if pool:
                    pool_info = {
                        'size': pool.size(),
                        'used': pool.checkedout(),
                        'overflow': pool.overflow(),
                        'invalid': pool.invalid()
                    }

                # 记录资源监控数据
                resource_data = {
                    'timestamp': datetime.utcnow(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'memory_used_mb': memory_info.used / (1024 * 1024),
                    'memory_total_mb': memory_info.total / (1024 * 1024),
                    'pool_info': pool_info
                }

                # 检查资源使用是否影响连接池
                if cpu_percent > 80 or memory_percent > 85:
                    logger.warning(f"High system resource usage - CPU: {cpu_percent}%, Memory: {memory_percent}%")

                # 每5分钟检查一次
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Error monitoring system resources: {e}")
                await asyncio.sleep(300)

    def get_pool_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        if not self.engine:
            return {'error': 'Pool not initialized'}

        try:
            pool = self.engine.pool
            pool_name = "default"
            stats = self.pool_stats.get(pool_name)

            return {
                'pool_name': pool_name,
                'status': 'active',
                'config': {
                    'pool_size': self.config['pool_size'],
                    'max_overflow': self.config['max_overflow'],
                    'pool_timeout': self.config['pool_timeout'],
                    'pool_recycle': self.config['pool_recycle'],
                    'pool_pre_ping': self.config['pool_pre_ping']
                },
                'current_stats': asdict(stats) if stats else None,
                'active_connections': len(self.active_connections),
                'total_metrics': len(self.connection_metrics),
                'performance_history_size': len(self.performance_history),
                'adaptive_scaling': self.adaptive_scaling,
                'monitoring_enabled': self.monitoring_enabled
            }

        except Exception as e:
            return {'error': f'Failed to get pool stats: {str(e)}'}

    def get_connection_metrics(self) -> List[Dict[str, Any]]:
        """获取连接性能指标"""
        if not self.connection_metrics:
            return []

        return [
            {
                'connection_id': conn.connection_id,
                'created_at': conn.created_at.isoformat(),
                'last_used': conn.last_used.isoformat(),
                'usage_count': conn.usage_count,
                'total_query_time': conn.total_query_time,
                'query_count': conn.query_count,
                'avg_query_time': conn.avg_query_time,
                'max_query_time': conn.max_query_time,
                'is_active': conn.is_active
            }
            for conn in self.connection_metrics.values()
        ]

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.performance_history:
            return {'error': 'No performance data available'}

        recent_sessions = list(self.performance_history)[-100:]

        # 计算统计数据
        total_sessions = len(recent_sessions)
        avg_checkout_time = sum(m['checkout_time_ms'] for m in recent_sessions) / total_sessions if total_sessions > 0 else 0
        max_checkout_time = max(m['checkout_time_ms'] for m in recent_sessions) if recent_sessions else 0
        avg_query_time = sum(m['avg_query_time_ms'] for m in recent_sessions) / total_sessions if total_sessions > 0 else 0
        max_query_time = sum(m['max_query_time_ms'] for m in recent_sessions) / total_sessions if total_sessions > 0 else 0

        # 计算超时统计
        timeout_count = len([m for m in recent_sessions if m['checkout_time_ms'] > self.connection_timeout_threshold * 1000])
        long_query_count = len([m for m in recent_sessions if m['max_query_time_ms'] > self.long_query_threshold * 1000])

        return {
            'summary_period': 'Last 100 sessions',
            'total_sessions': total_sessions,
            'avg_checkout_time_ms': round(avg_checkout_time, 2),
            'max_checkout_time_ms': round(max_checkout_time, 2),
            'avg_query_time_ms': round(avg_query_time, 2),
            'max_query_time_ms': round(max_query_time, 2),
            'timeout_sessions': timeout_count,
            'long_query_sessions': long_query_count,
            'timeout_rate_percent': round((timeout_count / total_sessions) * 100, 2) if total_sessions > 0 else 0,
            'long_query_rate_percent': round((long_query_count / total_sessions) * 100, 2) if total_sessions > 0 else 0
        }

    async def close_pool(self):
        """关闭连接池"""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None
            logger.info("Database connection pool closed")

    async def optimize_pool_settings(self, new_config: Dict[str, Any]) -> bool:
        """优化连接池设置"""
        try:
            # 备份当前配置
            old_config = self.config.copy()

            # 更新配置
            self.config.update(new_config)

            # 需要重新创建引擎来应用新配置
            await self.close_pool()

            # 使用新配置重新初始化
            success = await self.initialize_pool()

            if success:
                logger.info("Pool settings optimized successfully")
                logger.info(f"Old config: {old_config}")
                logger.info(f"New config: {self.config}")
            else:
                # 恢复旧配置
                self.config = old_config
                await self.initialize_pool()
                logger.warning("Failed to apply new settings, reverted to old config")

            return success

        except Exception as e:
            logger.error(f"Failed to optimize pool settings: {e}")
            return False

    async def force_cleanup_connections(self) -> int:
        """强制清理连接"""
        try:
            if not self.engine:
                return 0

            pool = self.engine.pool

            # 关闭所有连接
            await pool.dispose()

            cleaned = pool.size() + pool.overflow()

            # 重新创建连接池
            await pool.recreate()

            logger.info(f"Force cleaned up {cleaned} connections")
            return cleaned

        except Exception as e:
            logger.error(f"Failed to cleanup connections: {e}")
            return 0

# 全局连接池管理器实例
connection_pool_manager = None

async def get_connection_manager(database_url: str, config: Dict[str, Any] = None) -> ConnectionPoolManager:
    """获取连接池管理器实例"""
    global connection_pool_manager
    if connection_pool_manager is None:
        connection_pool_manager = ConnectionPoolManager(database_url, config)
        await connection_pool_manager.initialize_pool()
    return connection_pool_manager