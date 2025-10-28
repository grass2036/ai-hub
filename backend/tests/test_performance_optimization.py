"""
性能优化系统完整测试套件
测试性能中间件、资源管理、分析器、优化引擎等功能
"""

import pytest
import asyncio
import time
import json
import logging
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from backend.middleware.performance_middleware import (
    PerformanceOptimizationMiddleware, AsyncTaskPool, ResponseCompressor,
    RequestAnalyzer, PerformanceMetrics
)
from backend.core.performance.resource_manager import (
    ResourceManager, DatabaseConnectionPool, RedisConnectionPool, ResourceMetrics
)
from backend.core.performance.performance_analyzer import (
    IntelligentPerformanceAnalyzer, PerformanceIssue, PerformanceIssueType
)
from backend.core.performance.optimization_engine import (
    PerformanceOptimizationEngine, OptimizationSuggestion, OptimizationType
)

logger = logging.getLogger(__name__)


class TestPerformanceMiddleware:
    """性能中间件测试"""

    @pytest.fixture
    def middleware(self):
        """创建性能中间件实例"""
        return PerformanceOptimizationMiddleware(
            None,
            enable_compression=True,
            enable_async_pool=True,
            max_concurrent_tasks=10,
            min_compression_size=1024,
            compression_level=6
        )

    @pytest.mark.asyncio
    async def test_response_compression(self, middleware):
        """测试响应压缩"""
        compressor = ResponseCompressor(min_size=100, compression_level=6)

        # 测试应该压缩的响应
        mock_request = Mock()
        mock_request.headers.get.return_value = "gzip, deflate, br"
        mock_request.method = "GET"

        test_data = json.dumps({"test": "data" * 100}).encode()
        compressed_data, compression_type, ratio = compressor.compress_response(
            mock_request, test_data
        )

        assert compression_type in ["gzip", "deflate"], f"Unknown compression type: {compression_type}"
        assert compressed_data != test_data
        assert ratio < 1.0, f"Compression ratio should be < 1.0, got {ratio}"

        # 测试不应该压缩的响应
        mock_request_small = Mock()
        mock_request_small.headers.get.return_value = ""
        small_data = b"small"

        compressed_data, compression_type, ratio = compressor.compress_response(
            mock_request_small, small_data
        )

        assert compression_type == "none", f"Should not compress small data, got {compression_type}"
        assert ratio == 1.0, f"Should have ratio 1.0 for uncompressed, got {ratio}"

        logger.info("✓ Response compression tests passed")

    @pytest.mark.asyncio
    async def test_async_task_pool(self, middleware):
        """测试异步任务池"""
        pool = middleware.task_pool

        # 提交任务
        async def test_task(value: int):
            await asyncio.sleep(0.01)
            return value * 2

        tasks = [pool.submit_task(test_task(i)) for i in range(10)]
        results = await pool.gather_results(tasks)

        assert len(results) == 10, f"Expected 10 results, got {len(results)}"
        assert sum(results) == sum(i * 2 for i in range(10)), f"Task results incorrect"

        # 检查统计
        stats = pool.get_stats()
        assert stats["completed_tasks"] == 10, f"Expected 10 completed tasks, got {stats['completed_tasks']}"
        assert stats["success_rate"] == 1.0, f"Expected success rate 1.0, got {stats['success_rate']}"

        logger.info("✓ Async task pool tests passed")

    @pytest.mark.asyncio
    async def test_request_analysis(self, middleware):
        """测试请求分析器"""
        analyzer = middleware.request_analyzer

        # 添加一些测试数据
        test_metrics = [
            PerformanceMetrics(
                request_id="test1",
                method="GET",
                path="/api/users",
                status_code=200,
                start_time=time.time(),
                end_time=time.time() + 0.1,
                duration=0.1,
                response_size=1024,
                request_size=100
            ),
            PerformanceMetrics(
                request_id="test2",
                method="POST",
                path="/api/orders",
                status_code=404,
                start_time=time.time(),
                end_time=time.time() + 0.05,
                duration=0.05,
                response_size=512,
                request_size=2048
            ),
            PerformanceMetrics(
                request_id="test3",
                method="GET",
                path="/api/products",
                status_code=500,
                start_time=time.time(),
                end_time=time.time() + 2.0,
                duration=2.0,
                response_size=0,
                request_size=0,
                error="Internal Server Error"
            )
        ]

        for metric in test_metrics:
            analyzer.analyze_request(metric)

        # 获取分析报告
        report = analyzer.get_analysis_report()

        assert report["total_requests"] == 3
        assert report["error_rate"] == 2/3  # 2个错误
        assert "POST" in report["method_distribution"]
        assert report["size_distribution"]["small"] >= 1  # 至少一个小响应
        assert report["status_distribution"]["500"] == 1  # 一个5xx错误

        logger.info("✓ Request analyzer tests passed")

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, middleware):
        """测试性能指标收集"""
        # 添加一些测试指标
        middleware._record_metrics(
            request=Mock(method="GET", url=Mock(path="/test1")),
            response=Mock(status_code=200, headers={}, body=b"test data"),
            request_id="test1",
            start_time=time.time(),
            end_time=time.time() + 0.1
            error=None
        )

        # 检查指标
        stats = middleware.get_performance_stats()
        recent_metrics = middleware.get_recent_metrics()

        assert len(recent_metrics) == 1
        assert recent_metrics[0]["request_id"] == "test1"
        assert recent_metrics[0]["duration"] == 0.1
        assert recent_metrics[0]["status_code"] == 200

        logger.info("✓ Performance metrics collection tests passed")


class TestResourceManager:
    """资源管理器测试"""

    @pytest.fixture
    async def resource_manager(self):
        """创建资源管理器实例"""
        manager = ResourceManager()
        await manager.initialize()
        return manager

    @pytest.mark.asyncio
    async def test_database_pool_creation(self, resource_manager):
        """测试数据库连接池创建"""
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            pool = await resource_manager.create_database_pool(
                pool_id="test_db_pool",
                dsn="postgresql://test:test@localhost:5432/testdb",
                min_size=2,
                max_size=10
            )

            assert pool is not None
            assert resource_manager.get_pool("test_db_pool") == pool

            # 检查指标
            metrics = pool.get_metrics()
            assert metrics.resource_id == "test_db_pool"
            assert metrics.resource_type.value == "database"

        logger.info("✓ Database pool creation tests passed")

    @pytest.mark.asyncio
    async def test_redis_pool_creation(self, resource_manager):
        """测试Redis连接池创建"""
        with patch('aioredis.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.ping.return_value = True

            with patch('aioredis.ConnectionPool.from_url') as mock_create_pool:
                mock_pool = AsyncMock()
                mock_create_pool.return_value = mock_pool

                pool = await resource_manager.create_redis_pool(
                    pool_id="test_redis_pool",
                    host="localhost",
                    port=6379
                    max_connections=15
                )

                assert pool is not None
                assert resource_manager.get_pool("test_redis_pool") == pool

        logger.info("✓ Redis pool creation tests passed")

    @pytest.mark.asyncio
    async def test_resource_monitoring(self, resource_manager):
        """测试资源监控"""
        # 模拟一些系统指标
        with patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory:

            mock_cpu.return_value = 75.5
            memory_info = Mock()
            memory_info.total = 8 * 1024 * 1024 * 1024  # 8GB
            memory_info.available = 2 * 1024 * 1024 * 1024  # 2GB
            memory_info.used = 6 * 1024 * 1024 * 1024  # 6GB
            memory_info.percent = 75.0
            mock_memory.return_value = memory_info

            # 等待监控循环运行
            await asyncio.sleep(0.1)

            stats = resource_manager.get_comprehensive_stats()

            assert "system_cpu" in stats
            assert "system_memory" in stats
            assert stats["system_metrics"]["cpu_usage"] == 75.5
            assert stats["system_metrics"]["memory_usage"] == 75.0

        logger.info("✓ Resource monitoring tests passed")

    @pytest.mark.asyncio
    async def test_pool_health_check(self, resource_manager):
        """测试连接池健康检查"""
        pool = await resource_manager.create_database_pool(
            "health_test_pool",
            "postgresql://test:test@localhost:5432/testdb",
            min_size=2,
            max_size=5
        )

        # 等待健康检查
        await asyncio.sleep(0.2)

        stats = resource_manager.get_comprehensive_stats()
        pool_details = stats.get("pool_details", {})

        assert "health_test_pool" in pool_details
        assert pool_details["health_test_pool"]["status"] in ["healthy", "degraded"]

        logger.info("✓ Pool health check tests passed")


class TestIntelligentPerformanceAnalyzer:
    """智能性能分析器测试"""

    @pytest.fixture
    async def analyzer(self):
        """创建性能分析器实例"""
        analyzer = IntelligentPerformanceAnalyzer()
        await analyzer.start_analysis()
        return analyzer

    @pytest.mark.asyncio
    async def test_performance_analysis(self, analyzer):
        """测试性能分析"""
        # 添加一些测试指标
        test_data = [
            {
                "endpoint": "/api/users",
                "response_time": 0.15,
                "response_size": 2048,
                "error_rate": 0.02,
                "cache_hit_rate": 0.85,
                "concurrent_requests": 25,
                "database_query_time": 0.05,
                "cpu_usage": 60.0,
                "memory_usage": 70.0
            },
            {
                "endpoint": "/api/orders",
                "response_time": 0.8,
                "response_size": 512,
                "error_rate": 0.05,
                "cache_hit_rate": 0.75,
                "concurrent_requests": 30,
                "database_query_time": 0.15,
                "cpu_usage": 45.0,
                "memory_usage": 55.0
            },
            {
                "endpoint": "/api/products",
                "response_time": 2.5,
                "response_size": 8192,
                "error_rate": 0.15,
                "cache_hit_rate": 0.4,
                "concurrent_requests": 40,
                "database_query_time": 0.3,
                "cpu_usage": 80.0,
                "memory_usage": 85.0
            }
        ]

        # 添加指标数据
        for data in test_data:
            await analyzer.add_metrics("/api/users", data)
            await analyzer.add_metrics("/api/orders", data)
            await analyzer.add_metrics("/api/products", data)

        # 等待分析完成
        await asyncio.sleep(0.5)

        analysis = await analyzer.analyze_performance()

        # 验证分析结果
        assert "endpoints" in analysis
        assert len(analysis["endpoints"]) == 3

        # 检查是否检测到问题
        system_health = analysis["system_health"]
        assert system_health["critical_issues"] >= 1  # /api/products 应该检测到慢响应
        assert system_health["warnings"] >= 1  # /api/products 应该检测到低缓存

        logger.info("✓ Performance analysis tests passed")

    @pytest.mark.asyncio
    async def test_anomaly_detection(self, analyzer):
        """测试异常检测"""
        # 创建明显的异常数据
        normal_data = [0.1] * 20
        anomaly_data = normal_data + [2.5]  # 明显的异常值

        # 混合数据
        all_data = normal_data + anomaly_data

        # 训练模型
        test_metrics = [{"response_time": v} for v in all_data]
        success = await analyzer.ml_analyzer.train_models(test_metrics)

        assert success, "ML model training should succeed"

        # 检测异常
        anomalies = await analyzer.ml_analyzer.detect_anomalies(test_metrics)

        assert len(anomalies) == 20  # 正常数据
        assert anomalies[-len(anomaly_data):] == [True] * len(anomaly_data)  # 异常数据

        logger.info("✓ Anomaly detection tests passed")

    @pytest.mark.asyncio
    async def test_pattern_discovery(self, analyzer):
        """测试模式发现"""
        # 足够多的测试数据
        test_metrics = [
            {"response_time": 0.1, "error_rate": 0.01},  # 模式1
            {"response_time": 0.1, "error_rate": 0.01},  # 模式1
            {"response_time": 0.5, "error_rate": 0.02},  # 模式2
            {"response_time": 0.5, "error_rate": 0.02},  # 模式2
            {"response_time": 2.0, "error_rate": 0.1},  # 模式3
        ]

        # 添加指标数据
        for data in test_metrics:
            await analyzer.add_metrics("test_endpoint", data)

        # 等待模式发现
        await asyncio.sleep(0.3)

        analysis = await analyzer.analyze_performance()
        patterns = analyzer.get_performance_patterns()

        # 验证发现了模式
        assert len(patterns) >= 2  # 应该发现不同的模式

        # 验证模式特征
        pattern_types = [p["pattern_type"] for p in patterns]
        assert "normal_behavior" in pattern_types

        logger.info("✓ Pattern discovery tests passed")


class TestPerformanceOptimizationEngine:
    """性能优化引擎测试"""

    @pytest.fixture
    async def optimization_engine(self):
        """创建优化引擎实例"""
        engine = PerformanceOptimizationEngine()
        return engine

    @pytest.mark.asyncio
    async def test_suggestion_generation(self, optimization_engine):
        """测试优化建议生成"""
        # 模拟分析数据
        analysis_data = {
            "global_issues": [
                PerformanceIssue(
                    issue_id="test1",
                    type=PerformanceIssueType.SLOW_RESPONSE,
                    severity=3,  # HIGH
                    title="Slow Response",
                    affected_endpoints=["/api/slow"],
                    metrics={"p95_response_time": 1.5}
                )
            ],
            "endpoints": {
                "/api/slow": {
                    "response_time": {"p95": 1.5, "p99": 2.0},
                    "error_rate": 0.1
                },
                "/api/low_cache": {
                    "cache_hit_rate": 0.3,
                    "avg_response_time": 0.8
                }
            }
        }

        # 生成建议
        suggestions = await optimization_engine.analyze_and_suggest(analysis_data)

        assert len(suggestions) >= 1, "Should generate at least one suggestion"

        # 验证建议类型
        suggestion_types = [s.get("type") for s in suggestions]
        assert PerformanceIssueType.SLOW_RESPONSE in suggestion_types, "Should detect slow response issue"
        assert PerformanceIssueType.CACHE_EFFICIENCY in suggestion_types, "Should detect cache efficiency issue"

        # 验证建议优先级
        priorities = [s.get("priority").value for s in suggestions]
        assert max(priorities) <= 4, "Max priority should be CRITICAL"

        logger.info("✓ Suggestion generation tests passed")

    @pytest.mark.asyncio
    async def test_optimization_application(self, optimization_engine):
        """测试优化应用"""
        # 创建测试建议
        test_suggestion = OptimizationSuggestion(
            suggestion_id="test_opt",
            title="Test Optimization",
            description="Test optimization for unit testing",
            category="test_category",
            type=OptimizationType.DATABASE,
            priority=3,  # HIGH
            impact_score=80.0,
            effort_score=50.0,
            auto_executable=True,
            actions=["test_action1", "test_action2"]
        )

        # 手动添加建议到引擎
        optimization_engine.suggestion_history.append(test_suggestion)

        # 测试应用优化
        success = await optimization_engine.apply_optimization("test_opt", {"param": "value"})

        assert success, "Optimization application should succeed"

        # 验证应用记录
        analytics = optimization_engine.get_suggestion_analytics()
        assert "test_opt" in analytics["execution_history"]
        assert analytics["execution_history"]["test_opt"]["success"]

        logger.info("✓ Optimization application tests passed")

    @pytest.mark.asyncio
    async def test_suggestion_analytics(self, optimization_engine):
        """测试建议分析"""
        # 添加一些测试建议
        test_suggestions = [
            OptimizationSuggestion(
                suggestion_id="test1",
                title="Test 1",
                type=OptimizationType.DATABASE,
                auto_executable=True,
                success_rate=1.0,
                applied_count=5
            ),
            OptimizationSuggestion(
                suggestion_id="test2",
                title="Test 2",
                type=OptimizationType.CACHE,
                auto_executable=False,
                success_rate=0.5,
                applied_count=2
            )
        ]

        optimization_engine.suggestion_history = test_suggestions

        analytics = optimization_engine.get_suggestion_analytics()

        # 验证分析结果
        assert analytics["total_suggestions"] == 2
        assert analytics["applied_suggestions"] == 2
        assert analytics["application_rate"] == 1.0
        assert analytics["success_rates_by_type"]["database"] == 1.0
        assert analytics["success_rates_by_type"]["cache"] == 0.5

        logger.info("✓ Suggestion analytics tests passed")


class TestPerformanceIntegration:
    """性能优化集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_performance_pipeline(self):
        """端到端性能管道测试"""
        # 创建测试数据
        test_requests = [
            {"method": "GET", "path": "/api/users", "status_code": 200, "duration": 0.1},
            {"method": "POST", "path": "/api/orders", "status_code": 201, "duration": 0.2},
            {"method": "GET", "path": "/api/products", "status_code": 500, "duration": 1.5}
        ]

        # 模拟性能监控
        middleware = PerformanceOptimizationMiddleware(None)
        for i, req in enumerate(test_requests):
            await middleware._record_metrics(
                request=Mock(method=req["method"], url=Mock(path=req["path"])),
                response=Mock(status_code=req["status_code"], headers={}, body=b"test"),
                request_id=f"test_{i}",
                start_time=time.time(),
                end_time=time.time() + req["duration"]
            )

        # 测试分析器
        analyzer = await get_performance_analyzer()
        analysis = await analyzer.analyze_performance()

        # 测试优化引擎
        engine = await get_optimization_engine()
        suggestions = await engine.analyze_and_suggest(analysis)

        # 验证管道结果
        assert len(suggestions) >= 1, "Should generate optimization suggestions"
        assert analysis["system_health"]["critical_issues"] >= 1, "Should detect performance issues"

        # 测试性能统计
        stats = middleware.get_performance_stats()
        assert stats["middleware_stats"]["total_requests"] == 4
        assert stats["middleware_stats"]["slow_request_rate"] == 0.25  # 1个慢请求

        logger.info("✓ End-to-end performance pipeline tests passed")

    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """性能压力测试"""
        middleware = PerformanceOptimizationMiddleware(None, max_concurrent_tasks=20)

        async def simulate_load_requests(num_requests: int):
            tasks = []
            for i in range(num_requests):
                async def single_request():
                    start_time = time.time()
                    await asyncio.sleep(0.01)  # 模拟处理时间
                    end_time = time.time()
                    return end_time - start_time

                tasks.append(single_request)

            return await asyncio.gather(*tasks)

        # 执行负载测试
        start_time = time.time()
        results = await simulate_load_requests(50)
        end_time = time.time()

        # 验证性能指标
        total_time = end_time - start_time
        avg_time = sum(results) / len(results)
        max_time = max(results)

        assert avg_time < 0.05, f"Average response time should be < 0.05s, got {avg_time}"
        assert max_time < 0.1, f"Max response time should be < 0.1s, got {max_time}"

        # 验证任务池统计
        pool_stats = middleware.task_pool.get_stats()
        assert pool_stats["completed_tasks"] == 50
        assert pool_stats["success_rate"] == 1.0

        logger.info("✓ Performance under load tests passed")


# 运行测试
async def run_performance_tests():
    """运行所有性能优化测试"""
    import pytest

    test_args = [
        "backend/tests/test_performance_optimization.py",
        "-v",
        "--tb=short",
        "--disable-warnings"
    ]

    result = pytest.main(test_args)
    return result == 0


if __name__ == "__main__":
    success = asyncio.run(run_performance_tests)
    exit(0 if success else 1)