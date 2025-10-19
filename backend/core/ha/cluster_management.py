"""
集群管理系统
Week 6 Day 5: 负载均衡和高可用配置

提供节点管理、��群状态同步和协调功能
"""

import asyncio
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import redis
from .failover import Node, BackendStatus

class NodeRole(Enum):
    """节点角色"""
    LEADER = "leader"
    FOLLOWER = "follower"
    CANDIDATE = "candidate"

class ClusterState(Enum):
    """集群状态"""
    STABLE = "stable"
    ELECTING = "electing"
    PARTITIONED = "partitioned"
    DEGRADED = "degraded"

@dataclass
class ClusterConfig:
    """集群配置"""
    cluster_name: str
    node_id: str
    election_timeout: int = 10
    heartbeat_interval: int = 2
    lease_timeout: int = 15
    max_nodes: int = 7
    quorum_size: int = 3
    auto_rejoin: bool = True
    enable_lease: bool = True

@dataclass
class ClusterNode:
    """集群节点"""
    id: str
    host: str
    port: int
    role: NodeRole
    status: BackendStatus
    last_heartbeat: datetime
    term: int = 0
    lease_expires: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "host": self.host,
            "port": self.port,
            "role": self.role.value,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "term": self.term,
            "lease_expires": self.lease_expires.isoformat() if self.lease_expires else None,
            "metadata": self.metadata or {}
        }

class ClusterManager:
    """集群管理器"""

    def __init__(self, config: ClusterConfig):
        self.config = config
        self.nodes: Dict[str, ClusterNode] = {}
        self.current_term = 0
        self.current_leader: Optional[str] = None
        self.lease_holder: Optional[str] = None
        self.state = ClusterState.STABLE
        self.redis_client: Optional[redis.Redis] = None
        self.is_running = False

        # 当前节点信息
        self.is_leader = False
        self.lease_expires: Optional[datetime] = None

        # 选举相关
        self.election_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.lease_task: Optional[asyncio.Task] = None

        # 回调
        self.leadership_callbacks: List[Callable[[str, int], None]] = []
        self.state_change_callbacks: List[Callable[[ClusterState], None]] = []

    async def initialize(self, redis_client: Optional[redis.Redis] = None) -> None:
        """初始化集群管理器"""
        self.redis_client = redis_client

        # 添加当前节点到集群
        current_node = ClusterNode(
            id=self.config.node_id,
            host="localhost",  # 应该从配置获取
            port=8001,      # 应该从配置获取
            role=NodeRole.FOLLOWER,
            status=BackendStatus.HEALTHY,
            last_heartbeat=datetime.utcnow(),
            term=0
        )
        self.nodes[self.config.node_id] = current_node

        # 从Redis加载集群信息
        await self._load_cluster_state()

        # 启动集群管理
        await self._start_cluster_management()

        self.is_running = True
        logging.info(f"Cluster manager initialized for cluster: {self.config.cluster_name}")

    def add_leadership_callback(self, callback: Callable[[str, int], None]) -> None:
        """添加领导权变更回调"""
        self.leadership_callbacks.append(callback)

    def add_state_change_callback(self, callback: Callable[[ClusterState], None]) -> None:
        """添加状态变更回调"""
        self.state_change_callbacks.append(callback)

    async def _start_cluster_management(self) -> None:
        """启动集群管理"""
        # 启动心跳
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # 启动选举
        self.election_task = asyncio.create_task(self._election_loop())

        # 启动租约管理
        if self.config.enable_lease:
            self.lease_task = asyncio.create_task(self._lease_loop())

        # 启动节点清理
        asyncio.create_task(self._node_cleanup_loop())

    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while self.is_running:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(self.config.heartbeat_interval)
            except Exception as e:
                logging.error(f"Heartbeat loop error: {str(e)}")
                await asyncio.sleep(self.config.heartbeat_interval)

    async def _election_loop(self) -> None:
        """选举循环"""
        while self.is_running:
            try:
                await self._check_election_conditions()
                await asyncio.sleep(self.config.election_timeout)
            except Exception as e:
                logging.error(f"Election loop error: {str(e)}")
                await asyncio.sleep(self.config.election_timeout)

    async def _lease_loop(self) -> None:
        """租约循环"""
        while self.is_running:
            try:
                if self.is_leader:
                    await self._renew_lease()
                else:
                    await self._check_lease()
                await asyncio.sleep(5)  # 5秒检查间隔
            except Exception as e:
                logging.error(f"Lease loop error: {str(e)}")
                await asyncio.sleep(5)

    async def _send_heartbeat(self) -> None:
        """发送心跳"""
        current_node = self.nodes[self.config.node_id]
        current_node.last_heartbeat = datetime.utcnow()
        current_node.term = self.current_term

        # 更新Redis中的节点信息
        await self._save_node_state(current_node)

        # 更新其他节点的心跳信息
        await self._update_other_nodes()

    async def _check_election_conditions(self) -> None:
        """检查选举条件"""
        current_time = datetime.utcnow()

        # 检查是否有领导者
        if not self.current_leader:
            await self._start_election()
            return

        # 检查领导者是否超时
        leader_node = self.nodes.get(self.current_leader)
        if leader_node:
            if (current_time - leader_node.last_heartbeat).total_seconds() > self.config.election_timeout:
                logging.warning(f"Leader {self.current_leader} heartbeat timeout, starting election")
                await self._start_election()
                return

        # 检查租约
        if self.config.enable_lease and self.lease_holder:
            if self.lease_holder != self.current_leader:
                logging.warning(f"Lease holder {self.lease_holder} != current leader {self.current_leader}")
                await self._start_election()
                return

        # 检查节点数量和法定人数
        healthy_nodes = [
            node for node in self.nodes.values()
            if node.status == BackendStatus.HEALTHY
        ]

        if len(healthy_nodes) < self.config.quorum_size:
            if self.state != ClusterState.PARTITIONED:
                await self._change_state(ClusterState.PARTITIONED)
            return

        if self.state == ClusterState.PARTITIONED:
            await self._change_state(ClusterState.STABLE)

    async def _start_election(self) -> None:
        """开始选举"""
        if self.state == ClusterState.ELECTING:
            return

        await self._change_state(ClusterState.ELECTING)

        # 增加任期
        self.current_term += 1

        # 候选领导者
        await self._campaign_for_leadership()

    async def _campaign_for_leadership(self) -> None:
        """候选领导者"""
        current_node = self.nodes[self.config.node_id]
        current_node.role = NodeRole.CANDIDATE

        # 投票给自己
        votes = {self.config.node_id}

        # 请求其他节点投票
        for node_id, node in self.nodes.items():
            if node_id != self.config.node_id and node.status == BackendStatus.HEALTHY:
                try:
                    vote = await self._request_vote(node, current_node.term)
                    if vote:
                        votes.add(vote)
                except Exception as e:
                    logging.error(f"Failed to request vote from {node_id}: {str(e)}")

        # 检查是否获得多数票
        if len(votes) >= self.config.quorum_size:
            await self._become_leader(votes)
        else:
            await self._become_follower()

    async def _request_vote(self, node: ClusterNode, term: int) -> Optional[str]:
        """请求投票"""
        try:
            # 这里应该通过RPC或HTTP请求来请求投票
            # 简化实现，返回节点ID表示投票
            if node.term < term:
                return node.id
            return None
        except Exception:
            return None

    async def _become_leader(self, votes: Set[str]) -> None:
        """成为领导者"""
        current_node = self.nodes[self.config.node_id]
        current_node.role = NodeRole.LEADER
        self.current_leader = self.config.node_id
        self.is_leader = True

        if self.config.enable_lease:
            await self._acquire_lease()

        await self._change_state(ClusterState.STABLE)

        logging.info(f"Node {self.config.node_id} became leader with {len(votes)} votes")

        # 通知领导权变更
        for callback in self.leadership_callbacks:
            try:
                callback(self.config.node_id, self.current_term)
            except Exception as e:
                logging.error(f"Leadership callback error: {str(e)}")

    async def _become_follower(self) -> None:
        """成为跟随者"""
        current_node = self.nodes[self.config.node_id]
        current_node.role = NodeRole.FOLLOWER
        self.is_leader = False

        await self._change_state(ClusterState.STABLE)

        logging.info(f"Node {self.config.node_id} became follower")

    async def _acquire_lease(self) -> None:
        """获取租约"""
        if not self.redis_client:
            return

        try:
            lease_key = f"cluster:{self.config.cluster_name}:lease"
            lease_value = json.dumps({
                "node_id": self.config.node_id,
                "term": self.current_term,
                "acquired_at": datetime.utcnow().isoformat()
            })

            # 使用SETNX命令获取租约
            success = self.redis_client.set(
                lease_key,
                lease_value,
                nx=True,
                ex=self.config.lease_timeout
            )

            if success:
                self.lease_holder = self.config.node_id
                self.lease_expires = datetime.utcnow() + timedelta(seconds=self.config.lease_timeout)

                # 更新当前节点的租约信息
                current_node = self.nodes[self.config.node_id]
                current_node.lease_expires = self.lease_expires

                logging.info(f"Lease acquired by {self.config.node_id}")
            else:
                logging.warning(f"Failed to acquire lease, current holder: {self.lease_holder}")

        except Exception as e:
            logging.error(f"Failed to acquire lease: {str(e)}")

    async def _renew_lease(self) -> None:
        """续租约"""
        if not self.is_leader or not self.lease_expires:
            return

        # 检查租约是否即将过期（5秒内）
        if (datetime.utcnow() - self.lease_expires).total_seconds() > -5:
            await self._acquire_lease()

    async def _check_lease(self) -> None:
        """检查租约"""
        if not self.redis_client:
            return

        try:
            lease_key = f"cluster:{self.config.cluster_name}:lease"
            lease_data = self.redis_client.get(lease_key)

            if lease_data:
                lease_info = json.loads(lease_data)
                self.lease_holder = lease_info["node_id"]
            else:
                self.lease_holder = None

        except Exception as e:
            logging.error(f"Failed to check lease: {str(e)}")

    async def _update_other_nodes(self) -> None:
        """更新其他节点信息"""
        if not self.redis_client:
            return

        try:
            # 从Redis获取所有节点信息
            cluster_key = f"cluster:{self.config.cluster_name}:nodes"
            nodes_data = self.redis_client.hgetall(cluster_key)

            for node_id, node_json in nodes_data.items():
                if node_id != self.config.node_id:
                    try:
                        node_info = json.loads(node_json)
                        node = ClusterNode(
                            id=node_info["id"],
                            host=node_info["host"],
                            port=node_info["port"],
                            role=NodeRole(node_info["role"]),
                            status=BackendStatus(node_info["status"]),
                            last_heartbeat=datetime.fromisoformat(node_info["last_heartbeat"]),
                            term=node_info["term"],
                            lease_expires=datetime.fromisoformat(node_info["lease_expires"]) if node_info.get("lease_expires") else None,
                            metadata=node_info.get("metadata", {})
                        )
                        self.nodes[node_id] = node
                    except Exception as e:
                        logging.error(f"Failed to parse node data for {node_id}: {str(e)}")

        except Exception as e:
            logging.error(f"Failed to update other nodes: {str(e)}")

    async def _save_node_state(self, node: ClusterNode) -> None:
        """保存节点状态"""
        if not self.redis_client:
            return

        try:
            cluster_key = f"cluster:{self.config.cluster_name}:nodes"
            self.redis_client.hset(cluster_key, node.id, json.dumps(node.to_dict()))

            # 设置过期时间
            self.redis_client.expire(cluster_key, 300)  # 5分钟

        except Exception as e:
            logging.error(f"Failed to save node state: {str(e)}")

    async def _load_cluster_state(self) -> None:
        """加载集群状态"""
        if not self.redis_client:
            return

        try:
            # 加载集群信息
            cluster_key = f"cluster:{self.config.cluster_name}:info"
            cluster_info = self.redis_client.hgetall(cluster_key)

            if cluster_info:
                self.current_term = int(cluster_info.get("current_term", 0))
                self.current_leader = cluster_info.get("current_leader")
                self.lease_holder = cluster_info.get("lease_holder")

            # 加载节点信息
            await self._update_other_nodes()

        except Exception as e:
            logging.error(f"Failed to load cluster state: {str(e)}")

    async def _change_state(self, new_state: ClusterState) -> None:
        """改变集群状态"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state

            logging.info(f"Cluster state changed: {old_state.value} -> {new_state.value}")

            # 通知状态变更
            for callback in self.state_change_callbacks:
                try:
                    callback(new_state)
                except Exception as e:
                    logging.error(f"State change callback error: {str(e)}")

            # 保存状态到Redis
            await self._save_cluster_state()

    async def _save_cluster_state(self) -> None:
        """保存集群状态"""
        if not self.redis_client:
            return

        try:
            cluster_key = f"cluster:{self.config.cluster_name}:info"
            cluster_info = {
                "current_term": self.current_term,
                "current_leader": self.current_leader,
                "lease_holder": self.lease_holder,
                "state": self.state.value,
                "updated_at": datetime.utcnow().isoformat()
            }

            self.redis_client.hset(cluster_key, mapping=cluster_info)
            self.redis_client.expire(cluster_key, 300)  # 5分钟

        except Exception as e:
            logging.error(f"Failed to save cluster state: {str(e)}")

    async def _node_cleanup_loop(self) -> None:
        """节点清理循环"""
        while self.is_running:
            try:
                await self._cleanup_stale_nodes()
                await asyncio.sleep(60)  # 每分钟清理一次
            except Exception as e:
                logging.error(f"Node cleanup loop error: {str(e)}")
                await asyncio.sleep(60)

    async def _cleanup_stale_nodes(self) -> None:
        """清理过期的节点"""
        current_time = datetime.utcnow()
        nodes_to_remove = []

        for node_id, node in self.nodes.items():
            # 如果节点超过5分钟没有心跳，标记为不健康
            if (current_time - node.last_heartbeat).total_seconds() > 300:
                if node.status != BackendStatus.UNHEALTHY:
                    node.status = BackendStatus.UNHEALTHY
                    logging.warning(f"Node {node_id} marked as unhealthy due to stale heartbeat")

            # 如果节点超过1小时没有心跳，从集群中移除
            if (current_time - node.last_heartbeat).total_seconds() > 3600:
                nodes_to_remove.append(node_id)

        for node_id in nodes_to_remove:
            del self.nodes[node_id]
            logging.info(f"Removed stale node: {node_id}")

            # 从Redis中移除
            if self.redis_client:
                try:
                    cluster_key = f"cluster:{self.config.cluster_name}:nodes"
                    self.redis_client.hdel(cluster_key, node_id)
                except Exception as e:
                    logging.error(f"Failed to remove stale node from Redis: {str(e)}")

    def get_cluster_status(self) -> Dict[str, Any]:
        """获取集群状态"""
        healthy_nodes = len([
            node for node in self.nodes.values()
            if node.status == BackendStatus.HEALTHY
        ])

        return {
            "cluster_name": self.config.cluster_name,
            "state": self.state.value,
            "current_term": self.current_term,
            "current_leader": self.current_leader,
            "lease_holder": self.lease_holder,
            "is_leader": self.is_leader,
            "total_nodes": len(self.nodes),
            "healthy_nodes": healthy_nodes,
            "quorum_size": self.config.quorum_size,
            "has_quorum": healthy_nodes >= self.config.quorum_size,
            "nodes": {
                node_id: node.to_dict()
                for node_id, node in self.nodes.values()
            }
        }

    def get_leader_info(self) -> Optional[Dict[str, Any]]:
        """获取领导者信息"""
        if not self.current_leader:
            return None

        leader_node = self.nodes.get(self.current_leader)
        if not leader_node:
            return None

        return {
            "node_id": leader_node.id,
            "host": leader_node.host,
            "port": leader_node.port,
            "role": leader_node.role.value,
            "status": leader_node.status.value,
            "term": leader_node.term,
            "last_heartbeat": leader_node.last_heartbeat.isoformat(),
            "lease_expires": leader_node.lease_expires.isoformat() if leader_node.lease_expires else None
        }

    async def transfer_leadership(self, target_node_id: str) -> bool:
        """转移领导权"""
        if not self.is_leader:
            return False

        target_node = self.nodes.get(target_node_id)
        if not target_node:
            logging.error(f"Target node not found: {target_node_id}")
            return False

        if target_node.status != BackendStatus.HEALTHY:
            logging.error(f"Target node is not healthy: {target_node_id}")
            return False

        # 释放领导权
        self.is_leader = False
        self.current_leader = None

        if self.config.enable_lease:
            await self._release_lease()

        logging.info(f"Leadership transferred from {self.config.node_id} to {target_node_id}")
        return True

    async def _release_lease(self) -> None:
        """释放租约"""
        if not self.redis_client:
            return

        try:
            lease_key = f"cluster:{self.config.cluster_name}:lease"
            self.redis_client.delete(lease_key)
            self.lease_holder = None
            self.lease_expires = None

            # 更新当前节点的租约信息
            current_node = self.nodes[self.config.node_id]
            current_node.lease_expires = None

        except Exception as e:
            logging.error(f"Failed to release lease: {str(e)}")

    async def cleanup(self) -> None:
        """清理资源"""
        self.is_running = False

        if self.election_task:
            self.election_task.cancel()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.lease_task:
            self.lease_task.cancel()

        logging.info("Cluster manager cleaned up")