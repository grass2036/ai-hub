"""
数据库优化功能简单测试 - Simple Database Optimization Tests
快速验证数据库优化组件的基本功能
"""

import asyncio
import time
import logging
import sys
import os
from typing import Dict, Any
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_query_optimizer_basic():
    """测试查询优化器基本功能"""
    logger.info("🧪 Testing Query Optimizer Basic Functionality...")

    try:
        with patch('backend.optimization.query_optimizer.create_async_engine'):
            from backend.optimization.query_optimizer import QueryOptimizer

            optimizer = QueryOptimizer(
                database_url="sqlite+aiosqlite:///:memory:",
                enable_slow_query_detection=True,
                slow_query_threshold=50.0  # 50ms阈值
            )
            await optimizer.initialize()

            # 测试查询性能分析
            async with optimizer.profile_query("test_basic_query"):
                await asyncio.sleep(0.01)  # 模拟10ms查询

            # 检查查询历史
            history = await optimizer.get_query_history(5)
            assert len(history) > 0
            logger.info(f"✅ Query history recorded: {len(history)} queries")

            # 测试慢查询检测
            async with optimizer.profile_query("test_slow_query"):
                await asyncio.sleep(0.1)  # 模拟100ms慢查询

            slow_queries = await optimizer.get_slow_queries(5)
            logger.info(f"✅ Slow queries detected: {len(slow_queries)} queries")

            # 测试性能报告
            report = await optimizer.get_performance_report(1)
            assert "total_queries" in report
            logger.info(f"✅ Performance report generated: {report['total_queries']} total queries")

            await optimizer.cleanup()
            logger.info("✅ Query Optimizer tests passed!")

    except Exception as e:
        logger.error(f"❌ Query Optimizer test failed: {e}")
        return False

    return True


async def test_index_manager_basic():
    """测试索引管理器基本功能"""
    logger.info("🧪 Testing Index Manager Basic Functionality...")

    try:
        with patch('backend.optimization.index_manager.create_async_engine'):
            from backend.optimization.index_manager import IndexManager

            manager = IndexManager(
                database_url="sqlite+aiosqlite:///:memory:",
                enable_auto_analysis=True
            )
            await manager.initialize()

            # 模拟表索引分析
            with patch.object(manager, '_get_table_info') as mock_table_info:
                mock_table_info.return_value = {
                    "table_name": "users",
                    "row_count": 1000,
                    "size_mb": 15.5
                }

                with patch.object(manager, '_get_existing_indexes') as mock_indexes:
                    mock_indexes.return_value = [
                        {"name": "users_pkey", "columns": ["id"], "type": "btree"}
                    ]

                    analysis = await manager.analyze_table_indexes("users")
                    assert analysis["table_name"] == "users"
                    logger.info(f"✅ Table index analysis completed for: {analysis['table_name']}")

            # 测试索引推荐
            with patch.object(manager, 'analyze_all_indexes') as mock_analyze:
                mock_analyze.return_value = {
                    "tables": {
                        "users": {
                            "table_size": 1000,
                            "query_patterns": [
                                {"columns": ["email", "status"], "frequency": 50}
                            ]
                        }
                    }
                }

                recommendations = await manager.generate_recommendations(["users"])
                logger.info(f"✅ Index recommendations generated: {len(recommendations)} recommendations")

            await manager.cleanup()
            logger.info("✅ Index Manager tests passed!")

    except Exception as e:
        logger.error(f"❌ Index Manager test failed: {e}")
        return False

    return True


async def test_connection_pool_basic():
    """测试连接池管理器基本功能"""
    logger.info("🧪 Testing Connection Pool Manager Basic Functionality...")

    try:
        with patch('backend.optimization.connection_pool.create_async_engine'):
            from backend.optimization.connection_pool import ConnectionPoolManager

            manager = ConnectionPoolManager(
                database_url="sqlite+aiosqlite:///:memory:",
                pool_size=5,
                max_overflow=10
            )
            await manager.initialize()

            # 测试连接池统计
            stats = await manager.get_pool_stats()
            assert "pool_size" in stats
            logger.info(f"✅ Pool stats retrieved: pool_size={stats.get('pool_size')}")

            # 测试健康状态
            health = await manager.get_health_status()
            assert "overall_status" in health
            logger.info(f"✅ Health status retrieved: {health['overall_status']}")

            # 测试会话获取
            async with manager.get_session() as session:
                assert session is not None
                logger.info("✅ Database session obtained successfully")

            await manager.cleanup()
            logger.info("✅ Connection Pool Manager tests passed!")

    except Exception as e:
        logger.error(f"❌ Connection Pool Manager test failed: {e}")
        return False

    return True


async def test_read_write_split_basic():
    """测试读写分离引擎基本功能"""
    logger.info("🧪 Testing Read-Write Split Engine Basic Functionality...")

    try:
        with patch('backend.optimization.read_write_split.create_async_engine'):
            from backend.optimization.read_write_split import (
                ReadWriteSplitEngine, DatabaseNode, DatabaseRole, QueryType
            )

            # 创建测试节点
            master_node = DatabaseNode(
                id="test_master",
                role=DatabaseRole.MASTER,
                host="localhost",
                port=5432,
                database="test_db",
                username="test_user",
                password="test_pass"
            )

            replica_node = DatabaseNode(
                id="test_replica",
                role=DatabaseRole.REPLICA,
                host="localhost",
                port=5433,
                database="test_db",
                username="test_user",
                password="test_pass"
            )

            engine = ReadWriteSplitEngine(
                master_node=master_node,
                replica_nodes=[replica_node]
            )
            await engine.initialize()

            # 测试查询分类
            read_type = engine._classify_query("SELECT * FROM users")
            write_type = engine._classify_query("INSERT INTO users (name) VALUES ('test')")

            assert read_type == QueryType.READ
            assert write_type == QueryType.WRITE
            logger.info(f"✅ Query classification working: READ={read_type.value}, WRITE={write_type.value}")

            # 测试节点选择
            read_node = engine._select_node_for_read(QueryType.READ)
            assert read_node.role == DatabaseRole.REPLICA
            logger.info(f"✅ Node selection working: selected {read_node.role.value} for read")

            # 测试系统统计
            stats = await engine.get_system_stats()
            assert "total_nodes" in stats
            logger.info(f"✅ System stats retrieved: {stats['total_nodes']} nodes")

            await engine.cleanup()
            logger.info("✅ Read-Write Split Engine tests passed!")

    except Exception as e:
        logger.error(f"❌ Read-Write Split Engine test failed: {e}")
        return False

    return True


async def test_health_monitor_basic():
    """测试数据库健康监控基本功能"""
    logger.info("🧪 Testing Database Health Monitor Basic Functionality...")

    try:
        from backend.optimization.database_health import (
            DatabaseHealthMonitor, HealthMetric, MetricType, HealthStatus
        )

        monitor = DatabaseHealthMonitor(
            check_interval=1,
            alert_cooldown=10,
            enable_auto_recovery=False
        )

        # 测试指标配置
        assert "connection_pool_usage" in monitor.metrics_config
        assert "query_response_time" in monitor.metrics_config
        logger.info("✅ Metrics configuration loaded successfully")

        # 测试健康状态计算
        from backend.optimization.database_health import DatabaseHealthReport

        # 创建测试指标
        healthy_metric = HealthMetric(
            name="test_healthy",
            metric_type=MetricType.CONNECTION,
            value=50.0,
            threshold_warning=80.0,
            threshold_critical=95.0,
            unit="%",
            description="Test healthy metric"
        )
        healthy_metric.calculate_status()
        assert healthy_metric.status == HealthStatus.HEALTHY

        # 创建警告指标
        warning_metric = HealthMetric(
            name="test_warning",
            metric_type=MetricType.CONNECTION,
            value=85.0,
            threshold_warning=80.0,
            threshold_critical=95.0,
            unit="%",
            description="Test warning metric"
        )
        warning_metric.calculate_status()
        assert warning_metric.status == HealthStatus.WARNING

        logger.info("✅ Health status calculation working correctly")

        # 测试健康摘要
        test_report = DatabaseHealthReport(
            node_id="test_node",
            overall_status=HealthStatus.HEALTHY,
            metrics={"test_healthy": healthy_metric},
            alerts=[]
        )
        monitor.health_reports["test_node"] = test_report

        summary = await monitor.get_health_summary()
        assert "overall_status" in summary
        assert summary["total_nodes"] == 1
        logger.info(f"✅ Health summary generated: {summary['overall_status']}")

        await monitor.stop_monitoring()
        logger.info("✅ Database Health Monitor tests passed!")

    except Exception as e:
        logger.error(f"❌ Database Health Monitor test failed: {e}")
        return False

    return True


async def test_integration_flow():
    """测试集成流程"""
    logger.info("🧪 Testing Database Optimization Integration Flow...")

    try:
        # 启动计时
        start_time = time.time()

        # 并发运行所有基本测试
        tasks = [
            test_query_optimizer_basic(),
            test_index_manager_basic(),
            test_connection_pool_basic(),
            test_read_write_split_basic(),
            test_health_monitor_basic()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        passed = sum(1 for result in results if result is True)
        failed = len(results) - passed

        end_time = time.time()
        total_time = end_time - start_time

        logger.info(f"🎯 Integration Flow Results:")
        logger.info(f"   Passed: {passed}")
        logger.info(f"   Failed: {failed}")
        logger.info(f"   Total Time: {total_time:.2f}s")

        if failed == 0:
            logger.info("✅ All integration tests passed!")
            return True
        else:
            logger.error(f"❌ {failed} integration tests failed")
            return False

    except Exception as e:
        logger.error(f"❌ Integration flow test failed: {e}")
        return False


async def main():
    """主测试函数"""
    logger.info("🚀 Starting Database Optimization Tests...")
    logger.info("=" * 60)

    # 运行集成测试
    success = await test_integration_flow()

    logger.info("=" * 60)
    if success:
        logger.info("🎉 All Database Optimization Tests Completed Successfully!")
        logger.info("📋 Test Summary:")
        logger.info("   ✅ Query Optimizer - Performance analysis and slow query detection")
        logger.info("   ✅ Index Manager - Index analysis and recommendations")
        logger.info("   ✅ Connection Pool - Pool statistics and health monitoring")
        logger.info("   ✅ Read-Write Split - Query routing and load balancing")
        logger.info("   ✅ Health Monitor - System health tracking and alerting")
        logger.info("   ✅ Integration Flow - End-to-end component coordination")
    else:
        logger.error("💥 Some Database Optimization Tests Failed!")
        return 1

    return 0


if __name__ == "__main__":
    # 运行测试
    exit_code = asyncio.run(main())
    exit(exit_code)