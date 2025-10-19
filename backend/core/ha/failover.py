"""
故障转移系统
Week 6 Day 5: 负载均衡和高可用配置

提供自动故障检测、转移和恢复功能
"""

import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import redis
from .load_balancer import BackendServer, BackendStatus

class FailoverStrategy(Enum):
    """故障转移策略"""
    ACTIVE_PASSIVE = "active_passive"     # 主备模式
    ACTIVE_ACTIVE = "active_active"      双活模式
    MULTI_ACTIVE = "multi_active"         多活模式
    GEO_REDUNDANT = "geo_redundant"       地理冗余

class FailoverState(Enum):
    """故障转移状态"""
    NORMAL = "normal"                     # 正常状态
    FAILING = "failing"                   # 故障检测中
    FAILED = "failed"                     # 已故障
    FAILOVER_IN_PROGRESS = "failover_in_progress"  # 故障转移中
    FAILOVER_COMPLETED = "failover_completed"      # 故障转移完成
    RECOVERING = "recovering"             # 恢复中
    RECOVERED = "recovered"               # 已恢复

class FailoverTrigger(Enum):
    """故障转移触发器"""
    HEALTH_CHECK_FAILURE = "health_check_failure"
    TIMEOUT = "timeout"
    ERROR_RATE_HIGH = "error_rate_high"
    MANUAL = "manual"
    SCHEDULED = "scheduled"

@dataclass
class FailoverEvent:
    """故障转移事件"""
    id: str
    timestamp: datetime
    state: FailoverState
    trigger: FailoverTrigger
    source_node: str
    target_node: Optional[str]
    details: Dict[str, Any] = None
    message: str = ""

@dataclass
class FailoverConfig:
    """故障转移配置"""
    strategy: FailoverStrategy
    health_check_interval: int = 10
    failure_detection_threshold: int = 3  # 连续失败次数阈值
    failover_timeout: int = 30             # 故障转移超时时间
    recovery_check_interval: int = 30      # 恢复检查间隔
    auto_recovery: bool = True             # 自动恢复
    max_failover_attempts: int = 3        # 最大故障转移尝试次数
    enable_sticky_sessions: bool = True    # 启用会话粘性
    session_affinity_timeout: int = 3600   # 会话亲和性超时

@dataclass
class Node:
    """节点"""
    id: str
    host: str
    port: int
    role: str  # primary, secondary, active, standby
    status: BackendStatus
    last_heartbeat: datetime
    failure_count: int = 0
    last_failover: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

class FailoverManager:
    """故障转移管理器"""

    def __init__(self, config: FailoverConfig):
        self.config = config
        self.nodes: Dict[str, Node] = {}
        self.current_primary: Optional[str] = None
        self.state = FailoverState.NORMAL
        self.failover_events: List[FailoverEvent] = []
        self.redis_client: Optional[redis.Redis] = None
        self.is_running = False

        # 回调函数
        self.failover_callbacks: List[Callable[[FailoverEvent], None]] = []
        self.recovery_callbacks: List[Callable[[FailoverEvent], None]] = []

        # 统计信息
        self.total_failovers = 0
        self.total_recoveries = 0
        self.last_failover_time: Optional[datetime] = None
        self.last_recovery_time: Optional[datetime] = None

    async def initialize(self, redis_client: Optional[redis.Redis] = None) -> None:
        """初始化故障转移管理器"""
        self.redis_client = redis_client

        # 从Redis加载节点信息
        await self._load_nodes_from_redis()

        # 选择初始主节点
        await self._select_initial_primary()

        # 启动故障转移监控
        await self._start_failover_monitoring()

        self.is_running = True
        logging.info("Failover manager initialized")

    def add_node(self, node: Node) -> None:
        """添加节点"""
        self.nodes[node.id] = node
        logging.info(f"Added node: {node.id} ({node.url})")

    def remove_node(self, node_id: str) -> bool:
        """移除节点"""
        if node_id in self.nodes:
            del self.nodes[node_id]
            logging.info(f"Removed node: {node_id}")
            return True
        return False

    def add_failover_callback(self, callback: Callable[[FailoverEvent], None]) -> None:
        """添加故障转移回调"""
        self.failover_callbacks.append(callback)

    def add_recovery_callback(self, callback: Callable[[FailoverEvent], None]) -> None:
        """添加恢复回调"""
        self.recovery_callbacks.append(callback)

    async def _start_failover_monitoring(self) -> None:
        """启动故障转移监控"""
        # 启动健康检查监控
        asyncio.create_task(self._health_check_loop())

        # 启动心跳监控
        asyncio.create_task(self._heartbeat_loop())

        # 启动恢复检查
        if self.config.auto_recovery:
            asyncio.create_task(self._recovery_check_loop())

    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self.is_running:
            try:
                await self._check_node_health()
                await asyncio.sleep(self.config.health_check_interval)
            except Exception as e:
                logging.error(f"Health check loop error: {str(e)}")
                await asyncio.sleep(self.config.health_check_interval)

    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while self.is_running:
            try:
                await self._update_heartbeats()
                await asyncio.sleep(5)  # 5秒心跳间隔
            except Exception as e:
                logging.error(f"Heartbeat loop error: {str(e)}")
                await asyncio.sleep(5)

    async def _recovery_check_loop(self) -> None:
        """恢复检查循环"""
        while self.is_running:
            try:
                await self._check_recovery_conditions()
                await asyncio.sleep(self.config.recovery_check_interval)
            except Exception as e:
                logging.error(f"Recovery check loop error: {str(e)}")
                await asyncio.sleep(self.config.recovery_check_interval)

    async def _check_node_health(self) -> None:
        """检查节点健康状态"""
        for node in self.nodes.values():
            try:
                # 检查节点是否响应
                is_healthy = await self._ping_node(node)

                if is_healthy:
                    if node.status == BackendStatus.UNHEALTHY:
                        node.status = BackendStatus.HEALTHY
                        node.failure_count = 0
                        logging.info(f"Node {node.id} is now healthy")

                    node.last_heartbeat = datetime.now()
                else:
                    node.failure_count += 1
                    node.status = BackendStatus.UNHEALTHY
                    logging.warning(f"Node {node.id} is unhealthy (failure count: {node.failure_count})")

                    # 检查是否需要故障转移
                    if (node.role == "primary" and
                        node.failure_count >= self.config.failure_detection_threshold):
                        await self._trigger_failover(node, FailoverTrigger.HEALTH_CHECK_FAILURE)

            except Exception as e:
                logging.error(f"Health check failed for node {node.id}: {str(e)}")
                node.failure_count += 1
                node.status = BackendStatus.UNHEALTHY

    async def _update_heartbeats(self) -> None:
        """更新心跳"""
        current_time = datetime.utcnow()

        for node in self.nodes.values():
            # 检查心跳超时
            if (current_time - node.last_heartbeat).total_seconds() > 30:
                node.status = BackendStatus.UNHEALTHY
                logging.warning(f"Node {node.id} heartbeat timeout")

                # 如果是主节点心跳超时，触发故障转移
                if (node.role == "primary" and
                    self.state == FailoverState.NORMAL):
                    await self._trigger_failover(node, FailoverTrigger.TIMEOUT)

    async def _check_recovery_conditions(self) -> None:
        """检查恢复条件"""
        unhealthy_nodes = [
            node for node in self.nodes.values()
            if node.status == BackendStatus.UNHEALTHY and node.role != "primary"
        ]

        for node in unhealthy_nodes:
            try:
                is_healthy = await self._ping_node(node)
                if is_healthy:
                    await self._recover_node(node)

            except Exception as e:
                logging.error(f"Recovery check failed for node {node.id}: {str(e)}")

    async def _ping_node(self, node: Node) -> bool:
        """ping节点"""
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{node.url}/health") as response:
                    return response.status == 200
        except Exception:
            return False

    async def _trigger_failover(self, failed_node: Node, trigger: FailoverTrigger) -> None:
        """触发故障转移"""
        if self.state in [FailoverState.FAILOVER_IN_PROGRESS, FailoverState.FAILED]:
            logging.warning(f"Failover already in progress, ignoring trigger for {failed_node.id}")
            return

        logging.error(f"Triggering failover for node {failed_node.id} (role: {failed_node.role})")

        # 更新状态
        self.state = FailoverState.FAILOVER_IN_PROGRESS

        # 创建故障转移事件
        event = FailoverEvent(
            id=str(int(time.time() * 1000)),
            timestamp=datetime.utcnow(),
            state=self.state,
            trigger=trigger,
            source_node=failed_node.id,
            details={
                "failure_count": failed_node.failure_count,
                "last_heartbeat": failed_node.last_heartbeat.isoformat(),
                "strategy": self.config.strategy.value
            },
            message=f"Failover triggered for node {failed_node.id}"
        )

        # 执行故障转移
        success = await self._execute_failover(failed_node, event)

        if success:
            self.state = FailoverState.FAILOVER_COMPLETED
            event.state = self.state
            self.total_failovers += 1
            self.last_failover_time = datetime.utcnow()
        else:
            self.state = FailoverState.FAILED
            event.state = self.state

        # 记录事件
        self.failover_events.append(event)
        await self._store_failover_event(event)

        # 调用回调
        for callback in self.failover_callbacks:
            try:
                callback(event)
            except Exception as e:
                logging.error(f"Failover callback error: {str(e)}")

    async def _execute_failover(self, failed_node: Node, event: FailoverEvent) -> bool:
        """执行故障转移"""
        try:
            if self.config.strategy == FailoverStrategy.ACTIVE_PASSIVE:
                return await self._active_passive_failover(failed_node, event)
            elif self.config.strategy == FailoverStrategy.ACTIVE_ACTIVE:
                return await self._active_active_failover(failed_node, event)
            elif self.config.strategy == FailoverStrategy.MULTI_ACTIVE:
                return await self._multi_active_failover(failed_node, event)
            else:
                logging.error(f"Unsupported failover strategy: {self.config.strategy}")
                return False

        except Exception as e:
            logging.error(f"Failover execution failed: {str(e)}")
            return False

    async def _active_passive_failover(self, failed_node: Node, event: FailoverEvent) -> bool:
        """主备模式故障转移"""
        # 查找备用节点
        backup_nodes = [
            node for node in self.nodes.values()
            if node.role == "secondary" and node.status == BackendStatus.HEALTHY
        ]

        if not backup_nodes:
            logging.error("No healthy backup nodes available for failover")
            return False

        # 选择备用节点
        new_primary = backup_nodes[0]

        # 更新节点角色
        new_primary.role = "primary"
        failed_node.role = "secondary"

        # 更新当前主节点
        self.current_primary = new_primary.id

        logging.info(f"Failover completed: {failed_node.id} -> {new_primary.id}")
        event.target_node = new_primary.id
        event.message = f"Failover completed: {failed_node.id} -> {new_primary.id}"

        # 保存到Redis
        await self._save_nodes_to_redis()

        return True

    async def _active_active_failover(self, failed_node: Node, event: FailoverEvent) -> bool:
        """双活模式故障转移"""
        # 在双活模式中，将流量重新分配给其他活跃节点
        healthy_active_nodes = [
            node for node in self.nodes.values()
            if node.role == "active" and node.status == BackendStatus.HEALTHY and node.id != failed_node.id
        ]

        if not healthy_active_nodes:
            logging.error("No healthy active nodes available")
            return False

        logging.info(f"Redirecting traffic from {failed_node.id} to other active nodes")
        event.message = f"Traffic redirected from {failed_node.id}"

        return True

    async def _multi_active_failover(self, failed_node: Node, event: FailoverEvent) -> bool:
        """多活模式故障转移"""
        # 在多活模式中，重新分配流量
        healthy_nodes = [
            node for node in self.nodes.values()
            if node.status == BackendStatus.HEALTHY and node.id != failed_node.id
        ]

        if not healthy_nodes:
            logging.error("No healthy nodes available")
            return False

        logging.info(f"Redistributing traffic from {failed_node.id} to other nodes")
        event.message = f"Traffic redistributed from {failed_node.id}"

        return True

    async def _recover_node(self, node: Node) -> None:
        """恢复节点"""
        node.status = BackendStatus.HEALTHY
        node.failure_count = 0
        node.last_failover = datetime.utcnow()

        # 创建恢复事件
        event = FailoverEvent(
            id=str(int(time.time() * 1000)),
            timestamp=datetime.utcnow(),
            state=FailoverState.RECOVERED,
            trigger=FailoverTrigger.HEALTH_CHECK_FAILURE,
            source_node=node.id,
            details={
                "recovery_time": node.last_failover.isoformat(),
                "previous_failures": node.failure_count
            },
            message=f"Node {node.id} recovered"
        )

        # 记录事件
        self.failover_events.append(event)
        await self._store_failover_event(event)

        # 更新状态
        self.total_recoveries += 1
        self.last_recovery_time = datetime.utcnow()

        # 如果是正常状态且主节点已恢复，恢复主节点
        if (self.state == FailoverState.NORMAL and
            node.role == "primary" and
            self.current_primary != node.id):
            await self._restore_primary(node)

        # 调用恢复回调
        for callback in self.recovery_callbacks:
            try:
                callback(event)
            except Exception as e:
                logging.error(f"Recovery callback error: {str(e)}")

        logging.info(f"Node {node.id} recovered successfully")

    async def _restore_primary(self, node: Node) -> None:
        """恢复主节点"""
        # 通知其他节点恢复从属关系
        for other_node in self.nodes.values():
            if other_node.id != node.id and other_node.role == "secondary":
                # 这里可以发送通知给其他节点
                pass

        self.current_primary = node.id
        logging.info(f"Primary node restored: {node.id}")

    async def _select_initial_primary(self) -> None:
        """选择初始主节点"""
        primary_nodes = [
            node for node in self.nodes.values()
            if node.role in ["primary", "active"]
        ]

        if primary_nodes:
            # 选择健康的主节点
            healthy_primary_nodes = [n for n in primary_nodes if n.status == BackendStatus.HEALTHY]
            if healthy_primary_nodes:
                self.current_primary = healthy_primary_nodes[0].id
            else:
                self.current_primary = primary_nodes[0].id
        else:
            # 如果没有主节点，选择第一个健康节点作为主节点
            healthy_nodes = [n for n in self.nodes.values() if n.status == BackendStatus.HEALTHY]
            if healthy_nodes:
                healthy_nodes[0].role = "primary"
                self.current_primary = healthy_nodes[0].id

    def manual_failover(self, source_node_id: str, target_node_id: Optional[str] = None) -> bool:
        """手动故障转移"""
        source_node = self.nodes.get(source_node_id)
        if not source_node:
            logging.error(f"Source node not found: {source_node_id}")
            return False

        if target_node_id:
            target_node = self.nodes.get(target_node_id)
            if not target_node:
                logging.error(f"Target node not found: {target_node_id}")
                return False

        # 创建手动故障转移事件
        event = FailoverEvent(
            id=str(int(time.time() * 1000)),
            timestamp=datetime.utcnow(),
            state=FailoverState.FAILOVER_IN_PROGRESS,
            trigger=FailoverTrigger.MANUAL,
            source_node=source_node_id,
            target_node=target_node_id,
            message=f"Manual failover: {source_node_id} -> {target_node_id or 'auto'}"
        )

        # 异步执行故障转移
        asyncio.create_task(self._execute_failover(source_node, event))

        return True

    def get_failover_status(self) -> Dict[str, Any]:
        """获取故障转移状态"""
        events = self.failover_events[-10:]  # 最近10个事件

        return {
            "state": self.state.value,
            "strategy": self.config.strategy.value,
            "current_primary": self.current_primary,
            "total_failovers": self.total_failovers,
            "total_recoveries": self.total_recoveries,
            "last_failover_time": self.last_failover_time.isoformat() if self.last_failover_time else None,
            "last_recovery_time": self.last_recovery_time.isoformat() if self.last_recovery_time else None,
            "nodes": {
                node_id: {
                    "id": node.id,
                    "url": node.url,
                    "role": node.role,
                    "status": node.status.value,
                    "last_heartbeat": node.last_heartbeat.isoformat(),
                    "failure_count": node.failure_count,
                    "last_failover": node.last_failover.isoformat() if node.last_failover else None
                }
                for node_id, node in self.nodes.items()
            },
            "recent_events": [event.__dict__ for event in events]
        }

    async def _load_nodes_from_redis(self) -> None:
        """从Redis加载节点信息"""
        if not self.redis_client:
            return

        try:
            nodes_data = self.redis_client.hgetall("failover_nodes")
            for node_id, node_json in nodes_data.items():
                node_data = json.loads(node_json)
                node = Node(
                    id=node_data["id"],
                    host=node_data["host"],
                    port=node_data["port"],
                    role=node_data["role"],
                    status=BackendStatus(node_data["status"]),
                    last_heartbeat=datetime.fromisoformat(node_data["last_heartbeat"]),
                    failure_count=node_data.get("failure_count", 0),
                    metadata=node_data.get("metadata", {})
                )
                self.nodes[node_id] = node
        except Exception as e:
            logging.error(f"Failed to load nodes from Redis: {str(e)}")

    async def _save_nodes_to_redis(self) -> None:
        """保存节点信息到Redis"""
        if not self.redis_client:
            return

        try:
            nodes_data = {}
            for node in self.nodes.values():
                nodes_data[node.id] = json.dumps({
                    "id": node.id,
                    "host": node.host,
                    "port": node.port,
                    "role": node.role,
                    "status": node.status.value,
                    "last_heartbeat": node.last_heartbeat.isoformat(),
                    "failure_count": node.failure_count,
                    "metadata": node.metadata or {}
                })

            if nodes_data:
                self.redis_client.hset("failover_nodes", mapping=nodes_data)
        except Exception as e:
            logging.error(f"Failed to save nodes to Redis: {str(e)}")

    async def _store_failover_event(self, event: FailoverEvent) -> None:
        """存储故障转移事件"""
        if not self.redis_client:
            return

        try:
            event_data = json.dumps({
                "id": event.id,
                "timestamp": event.timestamp.isoformat(),
                "state": event.state.value,
                "trigger": event.trigger.value,
                "source_node": event.source_node,
                "target_node": event.target_node,
                "details": event.details or {},
                "message": event.message
            })

            self.redis_client.lpush("failover_events", event_data)
            self.redis_client.ltrim("failover_events", 0, 999)  # 保留最近1000个事件
        except Exception as e:
            logging.error(f"Failed to store failover event to Redis: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        self.is_running = False
        logging.info("Failover manager cleaned up")