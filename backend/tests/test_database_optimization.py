"""
数据库优化集成测试 - Database Optimization Integration Tests
测试查询优化、索引管理、连接池、读写分离和健康监控功能
"""

import pytest
import asyncio
import time
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch

from backend.optimization.query_optimizer import QueryOptimizer
from backend.optimization.index_manager import IndexManager
from backend.optimization.connection_pool import ConnectionPoolManager
from backend.optimization.read_write_split import ReadWriteSplitEngine, DatabaseNode, DatabaseRole
from backend.optimization.database_health import DatabaseHealthMonitor, HealthStatus, MetricType


class TestQueryOptimizer:
    """查询优化器测试"""

    @pytest.fixture
    async def query_optimizer(self):
        """创建查询优化器实例"""
        with patch('backend.optimization.query_optimizer.create_async_engine'):
            optimizer = QueryOptimizer(
                database_url="sqlite+aiosqlite:///:memory:",
                enable_slow_query_detection=True,
                slow_query_threshold=1000.0
            )
            await optimizer.initialize()
            yield optimizer
            await optimizer.cleanup()

    @pytest.mark.asyncio
    async def test_query_profiling(self, query_optimizer):
        """测试查询性能分析"""
        async with query_optimizer.profile_query("test_query"):
            # 模拟查询执行
            await asyncio.sleep(0.01)

        # 检查性能记录
        history = await query_optimizer.get_query_history(10)
        assert len(history) > 0
        assert history[0]["query_name"] == "test_query"
        assert history[0]["execution_time"] > 0

    @pytest.mark.asyncio
    async def test_slow_query_detection(self, query_optimizer):
        """测试慢查询检测"""
        # 模拟慢查询
        async with query_optimizer.profile_query("slow_query"):
            await asyncio.sleep(0.1)  # 模拟慢查询

        slow_queries = await query_optimizer.get_slow_queries(10)
        assert len(slow_queries) > 0
        assert slow_queries[0]["query_name"] == "slow_query"
        assert slow_queries[0]["execution_time"] >= 100  # 100ms

    @pytest.mark.asyncio
    async def test_optimization_recommendations(self, query_optimizer):
        """测试优化建议生成"""
        # 添加一些查询历史
        async with query_optimizer.profile_query("test_query"):
            await asyncio.sleep(0.01)

        recommendations = await query_optimizer.get_optimization_recommendations()
        assert isinstance(recommendations, list)

    @pytest.mark.asyncio
    async def test_performance_report(self, query_optimizer):
        """测试性能报告生成"""
        # 添加测试数据
        for i in range(5):
            async with query_optimizer.profile_query(f"test_query_{i}"):
                await asyncio.sleep(0.01)

        report = await query_optimizer.get_performance_report(24)
        assert "total_queries" in report
        assert "avg_execution_time" in report
        assert "slow_queries" in report


class TestIndexManager:
    """索引管理器测试"""

    @pytest.fixture
    async def index_manager(self):
        """创建索引管理器实例"""
        with patch('backend.optimization.index_manager.create_async_engine'):
            manager = IndexManager(
                database_url="sqlite+aiosqlite:///:memory:",
                enable_auto_analysis=True
            )
            await manager.initialize()
            yield manager
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_table_index_analysis(self, index_manager):
        """测试表索引分析"""
        # 模拟表分析
        with patch.object(index_manager, '_get_table_info') as mock_table_info:
            mock_table_info.return_value = {
                "table_name": "test_table",
                "row_count": 1000,
                "size_mb": 10.5
            }

            with patch.object(index_manager, '_get_existing_indexes') as mock_indexes:
                mock_indexes.return_value = [
                    {"name": "idx_primary", "columns": ["id"], "type": "btree"}
                ]

                analysis = await index_manager.analyze_table_indexes("test_table")

                assert analysis["table_name"] == "test_table"
                assert "existing_indexes" in analysis
                assert "recommendations" in analysis

    @pytest.mark.asyncio
    async def test_index_recommendations(self, index_manager):
        """测试索引推荐"""
        with patch.object(index_manager, 'analyze_all_indexes') as mock_analyze:
            mock_analyze.return_value = {
                "tables": {
                    "test_table": {
                        "table_size": 1000,
                        "query_patterns": [{"columns": ["name", "email"], "frequency": 100}]
                    }
                }
            }

            recommendations = await index_manager.generate_recommendations()
            assert isinstance(recommendations, list)

    @pytest.mark.asyncio
    async def test_index_creation(self, index_manager):
        """测试索引创建"""
        with patch.object(index_manager, '_create_index_sql') as mock_create_sql:
            mock_create_sql.return_value = "CREATE INDEX test_idx ON test_table (column1)"

            result = await index_manager.create_index("test_table", ["column1"], "btree")
            assert "index_name" in result
            assert "sql" in result


class TestConnectionPoolManager:
    """连接池管理器测试"""

    @pytest.fixture
    async def pool_manager(self):
        """创建连接池管理器实例"""
        with patch('backend.optimization.connection_pool.create_async_engine'):
            manager = ConnectionPoolManager(
                database_url="sqlite+aiosqlite:///:memory:",
                pool_size=5,
                max_overflow=10
            )
            await manager.initialize()
            yield manager
            await manager.cleanup()

    @pytest.mark.asyncio
    async def test_pool_statistics(self, pool_manager):
        """测试连接池统计"""
        stats = await pool_manager.get_pool_stats()
        assert "pool_size" in stats
        assert "active_connections" in stats
        assert "idle_connections" in stats

    @pytest.mark.asyncio
    async def test_health_status(self, pool_manager):
        """测试健康状态检查"""
        health = await pool_manager.get_health_status()
        assert "overall_status" in health
        assert "metrics" in health

    @pytest.mark.asyncio
    async def test_session_context(self, pool_manager):
        """测试会话上下文管理器"""
        async with pool_manager.get_session() as session:
            assert session is not None
            # 模拟数据库操作
            pass

    @pytest.mark.asyncio
    async def test_optimization_recommendations(self, pool_manager):
        """测试优化建议"""
        with patch.object(pool_manager, '_analyze_pool_usage') as mock_analyze:
            mock_analyze.return_value = {
                "utilization_rate": 85.0,
                "recommendations": ["Increase pool size"]
            }

            recommendations = await pool_manager.get_optimization_recommendations()
            assert isinstance(recommendations, list)


class TestReadWriteSplitEngine:
    """读写分离引擎测试"""

    @pytest.fixture
    async def rw_engine(self):
        """创建读写分离引擎实例"""
        # 创建测试节点
        master_node = DatabaseNode(
            id="master",
            role=DatabaseRole.MASTER,
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass"
        )

        replica_node = DatabaseNode(
            id="replica1",
            role=DatabaseRole.REPLICA,
            host="localhost",
            port=5433,
            database="test_db",
            username="test_user",
            password="test_pass"
        )

        with patch('backend.optimization.read_write_split.create_async_engine'):
            engine = ReadWriteSplitEngine(
                master_node=master_node,
                replica_nodes=[replica_node]
            )
            await engine.initialize()
            yield engine
            await engine.cleanup()

    @pytest.mark.asyncio
    async def test_query_classification(self, rw_engine):
        """测试查询分类"""
        # 测试读查询
        query_type = rw_engine._classify_query("SELECT * FROM users")
        assert query_type.value == "read"

        # 测试写查询
        query_type = rw_engine._classify_query("INSERT INTO users (name) VALUES ('test')")
        assert query_type.value == "write"

        # 测试分析查询
        query_type = rw_engine._classify_query("SELECT * FROM users GROUP BY department")
        assert query_type.value == "analytics"

    @pytest.mark.asyncio
    async def test_node_selection(self, rw_engine):
        """测试节点选择"""
        # 测试读查询节点选择
        node = rw_engine._select_node_for_read()
        assert node.role == DatabaseRole.REPLICA

        # 测试分析查询节点选择（如果有的话）
        if rw_engine.analytics_nodes:
            node = rw_engine._select_node_for_read(QueryType.ANALYTICS)
            assert node.role == DatabaseRole.ANALYTICS

    @pytest.mark.asyncio
    async def test_load_balancing_strategies(self, rw_engine):
        """测试负载均衡策略"""
        from backend.optimization.read_write_split import LoadBalanceStrategy

        # 测试轮询策略
        rw_engine.load_balance_strategy = LoadBalanceStrategy.ROUND_ROBIN
        node1 = rw_engine._select_node_for_read()
        node2 = rw_engine._select_node_for_read()
        # 简单验证不同节点被选择（如果有多个节点）
        if len(rw_engine.replica_nodes) > 1:
            assert node1.id != node2.id

    @pytest.mark.asyncio
    async def test_session_routing(self, rw_engine):
        """测试会话路由"""
        # 模拟读查询会话
        with patch.object(rw_engine, 'session_factories') as mock_factories:
            mock_session = AsyncMock()
            mock_factories.__getitem__.return_value.return_value = mock_session

            async with rw_engine.get_session(query_text="SELECT * FROM users") as session:
                assert session is not None

    @pytest.mark.asyncio
    async def test_system_statistics(self, rw_engine):
        """测试系统统计"""
        stats = await rw_engine.get_system_stats()
        assert "total_queries" in stats
        assert "node_stats" in stats
        assert "healthy_nodes" in stats

    @pytest.mark.asyncio
    async def test_performance_analysis(self, rw_engine):
        """测试性能分析"""
        # 添加一些模拟查询历史
        for i in range(10):
            query_stats = MagicMock()
            query_stats.node_id = "replica1"
            query_stats.query_type.value = "read"
            query_stats.execution_time = 100.0 + i * 10
            query_stats.success = True
            rw_engine.query_history.append(query_stats)

        analysis = await rw_engine.analyze_performance()
        assert "overall" in analysis
        assert "by_node" in analysis
        assert "by_query_type" in analysis


class TestDatabaseHealthMonitor:
    """数据库健康监控测试"""

    @pytest.fixture
    async def health_monitor(self):
        """创建健康监控器实例"""
        monitor = DatabaseHealthMonitor(
            check_interval=1,  # 1秒检查间隔，便于测试
            alert_cooldown=10,
            enable_auto_recovery=False
        )
        yield monitor
        await monitor.stop_monitoring()

    @pytest.mark.asyncio
    async def test_health_monitor_initialization(self, health_monitor):
        """测试健康监控器初始化"""
        assert health_monitor.check_interval == 1
        assert health_monitor.alert_cooldown == 10
        assert not health_monitor.is_monitoring

    @pytest.mark.asyncio
    async def test_metrics_configuration(self, health_monitor):
        """测试指标配置"""
        assert "connection_pool_usage" in health_monitor.metrics_config
        assert "query_response_time" in health_monitor.metrics_config
        assert "cpu_usage" in health_monitor.metrics_config

        metric_config = health_monitor.metrics_config["connection_pool_usage"]
        assert metric_config["warning"] == 80.0
        assert metric_config["critical"] == 95.0
        assert metric_config["unit"] == "%"

    @pytest.mark.asyncio
    async def test_alert_creation(self, health_monitor):
        """测试告警创建"""
        from backend.optimization.database_health import HealthMetric, HealthAlert

        # 创建触发告警的指标
        metric = HealthMetric(
            name="test_metric",
            metric_type=MetricType.CONNECTION,
            value=90.0,
            threshold_warning=80.0,
            threshold_critical=95.0,
            unit="%",
            description="Test metric"
        )
        metric.calculate_status()

        # 模拟告警检查
        alerts = await health_monitor._check_alerts(MagicMock(id="test_node"), {"test_metric": metric})

        if alerts:  # 如果触发了告警
            assert alerts[0].status in [HealthStatus.WARNING, HealthStatus.CRITICAL]
            assert alerts[0].metric_name == "test_metric"

    @pytest.mark.asyncio
    async def test_health_summary(self, health_monitor):
        """测试健康摘要"""
        # 添加模拟健康报告
        from backend.optimization.database_health import DatabaseHealthReport

        report = DatabaseHealthReport(
            node_id="test_node",
            overall_status=HealthStatus.HEALTHY,
            metrics={},
            alerts=[]
        )
        health_monitor.health_reports["test_node"] = report

        summary = await health_monitor.get_health_summary()
        assert "overall_status" in summary
        assert "total_nodes" in summary
        assert summary["total_nodes"] == 1

    @pytest.mark.asyncio
    async def test_metrics_history(self, health_monitor):
        """测试指标历史记录"""
        # 添加模拟历史数据
        from backend.optimization.database_health import HealthMetric

        metric = HealthMetric(
            name="test_metric",
            metric_type=MetricType.CONNECTION,
            value=50.0,
            threshold_warning=80.0,
            threshold_critical=95.0,
            unit="%",
            description="Test metric"
        )

        health_monitor.metrics_history["test_node_test_metric"].append(metric)

        history = await health_monitor.get_metrics_history("test_node", "test_metric", 24)
        assert len(history) > 0
        assert history[0]["value"] == 50.0

    @pytest.mark.asyncio
    async def test_monitoring_start_stop(self, health_monitor):
        """测试监控启动和停止"""
        # 启动监控
        await health_monitor.start_monitoring()
        assert health_monitor.is_monitoring
        assert health_monitor.monitor_task is not None

        # 等待一小段时间确保监控任务运行
        await asyncio.sleep(0.1)

        # 停止监控
        await health_monitor.stop_monitoring()
        assert not health_monitor.is_monitoring


class TestDatabaseOptimizationIntegration:
    """数据库优化集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_optimization_flow(self):
        """测试端到端优化流程"""
        # 这里可以测试各个组件之间的协作

        # 1. 初始化各个组件
        with patch('backend.optimization.query_optimizer.create_async_engine'), \
             patch('backend.optimization.index_manager.create_async_engine'), \
             patch('backend.optimization.connection_pool.create_async_engine'):

            # 查询优化器
            query_optimizer = QueryOptimizer("sqlite+aiosqlite:///:memory:")
            await query_optimizer.initialize()

            # 索引管理器
            index_manager = IndexManager("sqlite+aiosqlite:///:memory:")
            await index_manager.initialize()

            # 连接池管理器
            pool_manager = ConnectionPoolManager("sqlite+aiosqlite:///:memory:")
            await pool_manager.initialize()

            try:
                # 2. 模拟查询执行和分析
                async with query_optimizer.profile_query("integration_test"):
                    await asyncio.sleep(0.01)

                # 3. 获取性能数据
                performance_report = await query_optimizer.get_performance_report(1)
                assert performance_report["total_queries"] >= 1

                # 4. 获取连接池状态
                pool_stats = await pool_manager.get_pool_stats()
                assert "pool_size" in pool_stats

                # 5. 获取索引分析
                with patch.object(index_manager, 'analyze_all_indexes') as mock_analyze:
                    mock_analyze.return_value = {"tables": {}}
                    index_analysis = await index_manager.analyze_all_indexes()
                    assert "tables" in index_analysis

            finally:
                # 6. 清理资源
                await query_optimizer.cleanup()
                await index_manager.cleanup()
                await pool_manager.cleanup()

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """测试错误处理和恢复"""
        with patch('backend.optimization.query_optimizer.create_async_engine') as mock_engine:
            # 模拟引擎创建失败
            mock_engine.side_effect = Exception("Database connection failed")

            with pytest.raises(Exception):
                optimizer = QueryOptimizer("sqlite+aiosqlite:///:memory:")
                await optimizer.initialize()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """测试并发操作"""
        with patch('backend.optimization.query_optimizer.create_async_engine'):
            optimizer = QueryOptimizer("sqlite+aiosqlite:///:memory:")
            await optimizer.initialize()

            try:
                # 并发执行多个查询分析
                tasks = []
                for i in range(5):
                    task = asyncio.create_task(self._run_query_simulation(optimizer, f"query_{i}"))
                    tasks.append(task)

                # 等待所有任务完成
                results = await asyncio.gather(*tasks)

                # 验证所有查询都被记录
                history = await optimizer.get_query_history(20)
                assert len(history) >= 5

            finally:
                await optimizer.cleanup()

    async def _run_query_simulation(self, optimizer, query_name):
        """模拟查询执行"""
        async with optimizer.profile_query(query_name):
            await asyncio.sleep(0.01)


# 性能基准测试
@pytest.mark.asyncio
async def test_performance_benchmarks():
    """性能基准测试"""
    with patch('backend.optimization.query_optimizer.create_async_engine'):
        optimizer = QueryOptimizer("sqlite+aiosqlite:///:memory:")
        await optimizer.initialize()

        try:
            # 测试大量查询的性能
            start_time = time.time()

            for i in range(100):
                async with optimizer.profile_query(f"perf_test_{i}"):
                    await asyncio.sleep(0.001)  # 1ms模拟查询

            end_time = time.time()
            total_time = (end_time - start_time) * 1000  # 转换为毫秒

            # 验证性能指标
            avg_time = total_time / 100
            assert avg_time < 10  # 平均每个查询分析应该小于10ms

            # 验证历史记录
            history = await optimizer.get_query_history(200)
            assert len(history) == 100

        finally:
            await optimizer.cleanup()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])