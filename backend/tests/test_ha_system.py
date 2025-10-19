"""
高可用系统测试
Week 6 Day 5: 负载均衡和高可用配置测试

测试负载均衡器、健康检查、故障转移和集群管理功能
"""

import asyncio
import pytest
import time
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from backend.core.ha.load_balancer import (
    LoadBalancer, LoadBalancingConfig, LoadBalancingStrategy,
    BackendServer, BackendStatus, MultiRegionLoadBalancer
)
from backend.core.ha.health_check import (
    HealthChecker, HealthCheckConfig, CheckType, HealthStatus
)
from backend.core.ha.failover import (
    FailoverManager, FailoverConfig, FailoverStrategy, FailoverEvent
)
from backend.core.ha.cluster_management import (
    ClusterManager, ClusterConfig, Node, NodeRole, NodeStatus
)
from backend.core.ha.setup import HAConfig, HASetup


class TestLoadBalancer:
    """负载均衡器测试"""

    @pytest.fixture
    def config(self):
        """负载均衡配置"""
        return LoadBalancingConfig(
            strategy=LoadBalancingStrategy.ROUND_ROBIN,
            health_check_interval=5,
            health_check_timeout=2,
            max_retries=2,
            retry_delay=0.1
        )

    @pytest.fixture
    def backends(self):
        """测试后端服务器"""
        return [
            BackendServer(
                id="backend-1",
                host="localhost",
                port=8001,
                weight=1,
                max_connections=10
            ),
            BackendServer(
                id="backend-2",
                host="localhost",
                port=8002,
                weight=2,
                max_connections=10
            ),
            BackendServer(
                id="backend-3",
                host="localhost",
                port=8003,
                weight=3,
                max_connections=10
            )
        ]

    @pytest.fixture
    async def load_balancer(self, config, backends):
        """初始化负载均衡器"""
        lb = LoadBalancer(config)
        for backend in backends:
            lb.add_backend(backend)
        return lb

    @pytest.mark.asyncio
    async def test_round_robin_selection(self, load_balancer):
        """测试轮询选择"""
        backend_ids = []

        # 选择10次，验证轮询顺序
        for _ in range(10):
            backend = await load_balancer.select_backend()
            backend_ids.append(backend.id)

        # 验证轮询顺序
        expected_order = ["backend-1", "backend-2", "backend-3"] * 3 + ["backend-1"]
        assert backend_ids == expected_order

    @pytest.mark.asyncio
    async def test_weighted_round_robin_selection(self, load_balancer):
        """测试加权轮询选择"""
        load_balancer.config.strategy = LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN

        # 统计选择次数
        selection_counts = {"backend-1": 0, "backend-2": 0, "backend-3": 0}

        for _ in range(60):  # 60次选择，权重比例应该接近 1:2:3
            backend = await load_balancer.select_backend()
            selection_counts[backend.id] += 1

        # 验证权重分布（容差范围内）
        total_selections = sum(selection_counts.values())
        ratio_1 = selection_counts["backend-1"] / total_selections
        ratio_2 = selection_counts["backend-2"] / total_selections
        ratio_3 = selection_counts["backend-3"] / total_selections

        assert 0.1 <= ratio_1 <= 0.2  # 约1/6
        assert 0.2 <= ratio_2 <= 0.4  # 约2/6
        assert 0.4 <= ratio_3 <= 0.6  # 约3/6

    @pytest.mark.asyncio
    async def test_least_connections_selection(self, load_balancer):
        """测试最少连接选择"""
        load_balancer.config.strategy = LoadBalancingStrategy.LEAST_CONNECTIONS

        # 模拟不同的连接数
        load_balancer.backends["backend-1"].current_connections = 5
        load_balancer.backends["backend-2"].current_connections = 2
        load_balancer.backends["backend-3"].current_connections = 8

        # 应该选择连接数最少的backend-2
        backend = await load_balancer.select_backend()
        assert backend.id == "backend-2"

    @pytest.mark.asyncio
    async def test_ip_hash_selection(self, load_balancer):
        """测试IP哈希选择"""
        load_balancer.config.strategy = LoadBalancingStrategy.IP_HASH

        # 相同的IP应该选择相同的后端
        context = {"client_ip": "192.168.1.100"}

        backend1 = await load_balancer.select_backend(context)
        backend2 = await load_balancer.select_backend(context)

        assert backend1.id == backend2.id

        # 不同的IP可能选择不同的后端
        context_diff = {"client_ip": "192.168.1.200"}
        backend3 = await load_balancer.select_backend(context_diff)

        # 不一定不同，但通常应该不同
        assert isinstance(backend3, BackendServer)

    @pytest.mark.asyncio
    async def test_backend_availability_filter(self, load_balancer):
        """测试后端可用性过滤"""
        # 将一个后端标记为不健康
        load_balancer.backends["backend-2"].status = BackendStatus.UNHEALTHY

        # 可用的后端应该只有backend-1和backend-3
        backend = await load_balancer.select_backend()
        assert backend.id in ["backend-1", "backend-3"]

    @pytest.mark.asyncio
    async def test_no_available_backends(self, load_balancer):
        """测试没有可用后端的情况"""
        # 将所有后端标记为不可用
        for backend in load_balancer.backends.values():
            backend.status = BackendStatus.UNHEALTHY

        # 应该返回None
        backend = await load_balancer.select_backend()
        assert backend is None

    @pytest.mark.asyncio
    async def test_backend_statistics(self, load_balancer):
        """测试后端统计信息"""
        stats = load_balancer.get_statistics()

        assert stats["total_backends"] == 3
        assert stats["healthy_backends"] == 3
        assert stats["strategy"] == LoadBalancingStrategy.ROUND_ROBIN.value
        assert "backends" in stats
        assert len(stats["backends"]) == 3

    def test_backend_weight_update(self, load_balancer):
        """测试后端权重更新"""
        success = load_balancer.update_backend_weight("backend-1", 5)
        assert success
        assert load_balancer.backends["backend-1"].weight == 5

        # 测试不存在的后端
        success = load_balancer.update_backend_weight("nonexistent", 5)
        assert not success

    def test_backend_status_management(self, load_balancer):
        """测试后端状态管理"""
        # 测试设置排空状态
        success = load_balancer.drain_backend("backend-1")
        assert success
        assert load_balancer.backends["backend-1"].status == BackendStatus.DRAINING

        # 测试设置维护状态
        success = load_balancer.enable_backend_maintenance("backend-2")
        assert success
        assert load_balancer.backends["backend-2"].status == BackendStatus.MAINTENANCE


class TestMultiRegionLoadBalancer:
    """多区域负载均衡器测试"""

    @pytest.fixture
    def config(self):
        """多区域负载均衡配置"""
        return LoadBalancingConfig(
            strategy=LoadBalancingStrategy.ROUND_ROBIN,
            health_check_interval=10
        )

    @pytest.fixture
    async def multi_region_lb(self, config):
        """初始化多区域负载均衡器"""
        mr_lb = MultiRegionLoadBalancer(config)

        # 添加区域
        region1_lb = LoadBalancer(config)
        region1_lb.add_backend(BackendServer("us-east-1", "localhost", 8001))

        region2_lb = LoadBalancer(config)
        region2_lb.add_backend(BackendServer("us-west-1", "localhost", 8002))

        mr_lb.add_region("us-east-1", region1_lb, weight=1.0)
        mr_lb.add_region("us-west-1", region2_lb, weight=2.0)

        return mr_lb

    @pytest.mark.asyncio
    async def test_region_selection(self, multi_region_lb):
        """测试区域选择"""
        regions = []

        # 选择多次，验证区域分布
        for _ in range(30):
            region = await multi_region_lb.select_region()
            regions.append(region)

        # 验证区域权重分布（us-west-1权重更高）
        east_count = regions.count("us-east-1")
        west_count = regions.count("us-west-1")

        assert east_count > 0
        assert west_count > 0
        # west应该被选择更多次（权重更高）
        assert west_count > east_count

    def test_region_statistics(self, multi_region_lb):
        """测试区域统计信息"""
        stats = multi_region_lb.get_region_statistics()

        assert "us-east-1" in stats
        assert "us-west-1" in stats
        assert stats["us-east-1"]["total_backends"] == 1
        assert stats["us-west-1"]["total_backends"] == 1


class TestHealthChecker:
    """健康检查器测试"""

    @pytest.fixture
    def config(self):
        """健康检查配置"""
        return HealthCheckConfig(
            check_type=CheckType.HTTP_ENDPOINT,
            target="http://localhost:8001/health",
            interval=5,
            timeout=2,
            failure_threshold=2,
            success_threshold=1
        )

    @pytest.fixture
    async def health_checker(self, config):
        """初始化健康检查器"""
        checker = HealthChecker(config)
        return checker

    @pytest.mark.asyncio
    async def test_http_health_check_success(self, health_checker):
        """测试HTTP健康检查成功"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # 模拟成功响应
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await health_checker._check_http_endpoint(health_checker.config)

            assert result.status == HealthStatus.HEALTHY
            assert result.response_time > 0
            assert "success" in result.message.lower()

    @pytest.mark.asyncio
    async def test_http_health_check_failure(self, health_checker):
        """测试HTTP健康检查失败"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # 模拟失败响应
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await health_checker._check_http_endpoint(health_checker.config)

            assert result.status == HealthStatus.UNHEALTHY
            assert "500" in result.message

    @pytest.mark.asyncio
    async def test_tcp_health_check_success(self, health_checker):
        """测试TCP健康检查成功"""
        health_checker.config.check_type = CheckType.TCP_PORT
        health_checker.config.target = "localhost:8001"

        with patch('asyncio.open_connection') as mock_connect:
            # 模拟成功连接
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_connect.return_value = (mock_reader, mock_writer)

            result = await health_checker._check_tcp_port(health_checker.config)

            assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_database_health_check(self, health_checker):
        """测试数据库健康检查"""
        health_checker.config.check_type = CheckType.DATABASE
        health_checker.config.target = "postgresql://user:pass@localhost/db"

        with patch('asyncpg.connect') as mock_connect:
            # 模拟成功数据库连接
            mock_connection = AsyncMock()
            mock_connect.return_value = mock_connection

            result = await health_checker._check_database(health_checker.config)

            assert result.status == HealthStatus.HEALTHY

    def test_health_check_configuration(self):
        """测试健康检查配置"""
        config = HealthCheckConfig(
            check_type=CheckType.CUSTOM_SCRIPT,
            target="/path/to/script.sh",
            interval=10,
            timeout=5
        )

        assert config.check_type == CheckType.CUSTOM_SCRIPT
        assert config.target == "/path/to/script.sh"
        assert config.interval == 10
        assert config.timeout == 5


class TestFailoverManager:
    """故障转移管理器测试"""

    @pytest.fixture
    def config(self):
        """故障转移配置"""
        return FailoverConfig(
            strategy=FailoverStrategy.ACTIVE_PASSIVE,
            detection_timeout=5,
            failover_timeout=10,
            recovery_check_interval=10,
            max_failures=3
        )

    @pytest.fixture
    def nodes(self):
        """测试节点"""
        return {
            "node-1": Node(
                id="node-1",
                host="localhost",
                port=8001,
                role=NodeRole.PRIMARY,
                status=NodeStatus.HEALTHY
            ),
            "node-2": Node(
                id="node-2",
                host="localhost",
                port=8002,
                role=NodeRole.SECONDARY,
                status=NodeStatus.HEALTHY
            )
        }

    @pytest.fixture
    async def failover_manager(self, config, nodes):
        """初始化故障转移管理器"""
        manager = FailoverManager(config)
        manager.nodes = nodes
        manager._lock = asyncio.Lock()
        return manager

    @pytest.mark.asyncio
    async def test_failure_detection(self, failover_manager):
        """测试故障检测"""
        # 模拟主节点故障
        primary_node = failover_manager.nodes["node-1"]
        primary_node.last_heartbeat = datetime.now() - timedelta(seconds=10)

        # 检测故障
        failed_nodes = await failover_manager._detect_failures()

        assert "node-1" in failed_nodes
        assert failed_nodes["node-1"] == "heartbeat_timeout"

    @pytest.mark.asyncio
    async def test_active_passive_failover(self, failover_manager):
        """测试主备故障转移"""
        primary_node = failover_manager.nodes["node-1"]
        secondary_node = failover_manager.nodes["node-2"]

        # 模拟主节点故障
        failover_event = FailoverEvent(
            failed_node_id="node-1",
            reason="heartbeat_timeout",
            timestamp=datetime.now()
        )

        # 执行故障转移
        success = await failover_manager._active_passive_failover(primary_node, failover_event)

        assert success
        assert secondary_node.role == NodeRole.PRIMARY
        assert primary_node.role == NodeRole.SECONDARY
        assert primary_node.status == NodeStatus.FAILED

    @pytest.mark.asyncio
    async def test_recovery_detection(self, failover_manager):
        """测试恢复检测"""
        # 标记节点为故障
        failed_node = failover_manager.nodes["node-1"]
        failed_node.status = NodeStatus.FAILED

        # 模拟节点恢复
        failed_node.status = NodeStatus.HEALTHY
        failed_node.last_heartbeat = datetime.now()

        # 检测恢复
        recovered_nodes = await failover_manager._detect_recovery()

        assert "node-1" in recovered_nodes

    def test_failover_configuration(self):
        """测试故障转移配置"""
        config = FailoverConfig(
            strategy=FailoverStrategy.ACTIVE_ACTIVE,
            detection_timeout=10,
            max_failures=5
        )

        assert config.strategy == FailoverStrategy.ACTIVE_ACTIVE
        assert config.detection_timeout == 10
        assert config.max_failures == 5


class TestClusterManager:
    """集群管理器测试"""

    @pytest.fixture
    def config(self):
        """集群配置"""
        return ClusterConfig(
            node_id="node-1",
            discovery_servers=["localhost:8001", "localhost:8002"],
            heartbeat_interval=5,
            election_timeout=10,
            quorum_size=2
        )

    @pytest.fixture
    async def cluster_manager(self, config):
        """初始化集群管理器"""
        manager = ClusterManager(config)
        manager._lock = asyncio.Lock()
        return manager

    @pytest.mark.asyncio
    async def test_leader_election(self, cluster_manager):
        """测试领导者选举"""
        # 添加其他节点
        cluster_manager.nodes["node-2"] = Node(
            id="node-2",
            host="localhost",
            port=8002,
            role=NodeRole.FOLLOWER,
            status=NodeStatus.HEALTHY
        )

        # 开始选举
        await cluster_manager._campaign_for_leadership()

        # 验证选举结果
        assert cluster_manager.current_node.role == NodeRole.LEADER
        assert cluster_manager.current_node.term > 0

    @pytest.mark.asyncio
    async def test_quorum_check(self, cluster_manager):
        """测试法定人数检查"""
        # 添加健康节点
        cluster_manager.nodes["node-2"] = Node(
            id="node-2",
            host="localhost",
            port=8002,
            role=NodeRole.FOLLOWER,
            status=NodeStatus.HEALTHY
        )
        cluster_manager.nodes["node-3"] = Node(
            id="node-3",
            host="localhost",
            port=8003,
            role=NodeRole.FOLLOWER,
            status=NodeStatus.HEALTHY
        )

        # 检查法定人数
        has_quorum = cluster_manager._has_quorum()
        assert has_quorum

    @pytest.mark.asyncio
    async def test_node_discovery(self, cluster_manager):
        """测试节点发现"""
        discovered_nodes = await cluster_manager._discover_nodes()

        # 验证发现的节点
        assert isinstance(discovered_nodes, list)
        # 在测试环境中，可能没有实际发现其他节点

    def test_cluster_configuration(self):
        """测试集群配置"""
        config = ClusterConfig(
            node_id="test-node",
            quorum_size=3,
            election_timeout=15
        )

        assert config.node_id == "test-node"
        assert config.quorum_size == 3
        assert config.election_timeout == 15


class TestHASetup:
    """高可用系统设置测试"""

    @pytest.fixture
    def ha_config(self):
        """高可用配置"""
        return HAConfig(
            enable_load_balancer=True,
            enable_health_checker=True,
            enable_failover_manager=True,
            enable_cluster_manager=True,
            redis_url="redis://localhost:6379/1"
        )

    @pytest.mark.asyncio
    async def test_ha_setup_initialization(self, ha_config):
        """测试高可用系统初始化"""
        setup = HASetup(ha_config)

        with patch('redis.Redis') as mock_redis:
            # 模拟Redis连接
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client

            await setup.initialize()

            assert setup.redis_client is not None
            assert setup.load_balancer is not None
            assert setup.health_checker is not None
            assert setup.failover_manager is not None
            assert setup.cluster_manager is not None

    @pytest.mark.asyncio
    async def test_ha_status_monitoring(self, ha_config):
        """测试高可用状态监控"""
        setup = HASetup(ha_config)

        with patch('redis.Redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client

            await setup.initialize()
            status = await setup.get_ha_status()

            assert "load_balancer" in status
            assert "health_checker" in status
            assert "failover_manager" in status
            assert "cluster_manager" in status
            assert "system_time" in status

    @pytest.mark.asyncio
    async def test_component_graceful_shutdown(self, ha_config):
        """测试组件优雅关闭"""
        setup = HASetup(ha_config)

        with patch('redis.Redis') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client

            await setup.initialize()

            # 模拟关闭
            await setup.shutdown()

            # 验证组件已关闭
            assert setup.load_balancer is None
            assert setup.health_checker is None
            assert setup.failover_manager is None
            assert setup.cluster_manager is None


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_load_balancer_with_health_check(self):
        """测试负载均衡器与健康检查集成"""
        # 创建负载均衡器
        lb_config = LoadBalancingConfig(strategy=LoadBalancingStrategy.ROUND_ROBIN)
        load_balancer = LoadBalancer(lb_config)

        # 添加后端
        backend = BackendServer("test-backend", "localhost", 8001)
        load_balancer.add_backend(backend)

        # 创建健康检查器
        health_config = HealthCheckConfig(
            check_type=CheckType.HTTP_ENDPOINT,
            target="http://localhost:8001/health",
            interval=1
        )
        health_checker = HealthChecker(health_config)

        # 模拟健康检查失败
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await health_checker._check_http_endpoint(health_config)

            # 健康检查失败后，后端应该被标记为不健康
            if result.status == HealthStatus.UNHEALTHY:
                backend.status = BackendStatus.UNHEALTHY

        # 验证后端不可用
        selected = await load_balancer.select_backend()
        assert selected is None

    @pytest.mark.asyncio
    async def test_failover_with_cluster_management(self):
        """测试故障转移与集群管理集成"""
        # 创建集群配置
        cluster_config = ClusterConfig(
            node_id="test-node",
            quorum_size=1
        )

        # 创建故障转移配置
        failover_config = FailoverConfig(
            strategy=FailoverStrategy.ACTIVE_PASSIVE
        )

        cluster_manager = ClusterManager(cluster_config)
        failover_manager = FailoverManager(failover_config)

        # 添加节点
        node = Node(
            id="test-node",
            host="localhost",
            port=8001,
            role=NodeRole.PRIMARY,
            status=NodeStatus.HEALTHY
        )

        cluster_manager.current_node = node
        failover_manager.nodes["test-node"] = node

        # 模拟节点故障
        node.status = NodeStatus.FAILED

        # 检测故障
        failed_nodes = await failover_manager._detect_failures()

        # 验证故障检测
        assert "test-node" in failed_nodes

        # 在实际集群中，这会触发重新选举


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])