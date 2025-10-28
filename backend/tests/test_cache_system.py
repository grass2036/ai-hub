"""
缓存系统完整测试套件
测试多级缓存管理器、API中间件、预热机制和监控系统
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from backend.core.cache.multi_level_cache import (
    CacheConfig, CacheLevel, CacheEntry, MemoryCache,
    RedisCache, PersistentCache, MultiLevelCacheManager
)
from backend.middleware.cache_middleware import (
    APICacheMiddleware, CacheRule, CacheStrategy, CacheKeyStrategy
)
from backend.core.cache.cache_warmup import (
    CacheWarmupManager, WarmupTask, WarmupPriority, WarmupStrategy
)
from backend.core.cache.cache_monitor import (
    CacheMetricsCollector, CachePerformanceAnalyzer, CacheMonitoringSystem,
    MetricPoint, PerformanceAlert, AlertSeverity
)


class TestCacheConfig:
    """缓存配置测试"""

    def test_cache_config_defaults(self):
        """测试缓存配置默认值"""
        config = CacheConfig()

        assert config.l1_max_size == 1000
        assert config.l1_ttl == 300
        assert config.l2_host == "localhost"
        assert config.l2_port == 6379
        assert config.compression_enabled == True
        assert config.serialization_method == "json"

    def test_cache_config_custom(self):
        """测试自定义缓存配置"""
        config = CacheConfig(
            l1_max_size=2000,
            l2_ttl=7200,
            compression_enabled=False,
            serialization_method="pickle"
        )

        assert config.l1_max_size == 2000
        assert config.l2_ttl == 7200
        assert config.compression_enabled == False
        assert config.serialization_method == "pickle"


class TestCacheEntry:
    """缓存条目���试"""

    def test_cache_entry_creation(self):
        """测试缓存条目创建"""
        entry = CacheEntry(
            key="test_key",
            value={"data": "test"},
            level=CacheLevel.L1_MEMORY,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl=300
        )

        assert entry.key == "test_key"
        assert entry.value == {"data": "test"}
        assert entry.level == CacheLevel.L1_MEMORY
        assert entry.ttl == 300
        assert entry.access_count == 0

    def test_cache_entry_expiration(self):
        """测试缓存条目过期"""
        past_time = time.time() - 400  # 400秒前

        entry = CacheEntry(
            key="expired_key",
            value="expired_data",
            level=CacheLevel.L1_MEMORY,
            created_at=past_time,
            last_accessed=time.time(),
            ttl=300
        )

        assert entry.is_expired() == True

    def test_cache_entry_not_expired(self):
        """测试缓存条目未过期"""
        recent_time = time.time() - 100  # 100秒前

        entry = CacheEntry(
            key="valid_key",
            value="valid_data",
            level=CacheLevel.L1_MEMORY,
            created_at=recent_time,
            last_accessed=time.time(),
            ttl=300
        )

        assert entry.is_expired() == False

    def test_cache_entry_access_update(self):
        """测试缓存条目访问更新"""
        entry = CacheEntry(
            key="access_key",
            value="access_data",
            level=CacheLevel.L1_MEMORY,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl=300
        )

        original_count = entry.access_count
        entry.update_access()

        assert entry.access_count == original_count + 1
        assert entry.last_accessed > entry.created_at


class TestMemoryCache:
    """内存缓存测试"""

    @pytest.fixture
    async def memory_cache(self):
        """创建内存缓存实例"""
        cache = MemoryCache(max_size=5, default_ttl=1)
        return cache

    @pytest.mark.asyncio
    async def test_memory_cache_set_and_get(self, memory_cache):
        """测试内存缓存设置和获取"""
        key = "test_key"
        value = {"test": "data"}

        # 设置缓存
        result = await memory_cache.set(key, value)
        assert result == True

        # 获取缓存
        entry = await memory_cache.get(key)
        assert entry is not None
        assert entry.value == value
        assert entry.access_count == 1

    @pytest.mark.asyncio
    async def test_memory_cache_not_found(self, memory_cache):
        """测试内存缓存未找到"""
        entry = await memory_cache.get("nonexistent_key")
        assert entry is None

    @pytest.mark.asyncio
    async def test_memory_cache_expiration(self, memory_cache):
        """测试内存缓存过期"""
        key = "expire_key"
        value = "expire_data"

        # 设置很短的TTL
        await memory_cache.set(key, value, ttl=0.1)  # 0.1秒

        # 立即获取应该成功
        entry = await memory_cache.get(key)
        assert entry is not None

        # 等待过期后获取应该失败
        await asyncio.sleep(0.2)
        entry = await memory_cache.get(key)
        assert entry is None

    @pytest.mark.asyncio
    async def test_memory_cache_eviction(self, memory_cache):
        """测试内存缓存淘汰"""
        # 填满缓存
        for i in range(5):
            await memory_cache.set(f"key_{i}", f"value_{i}")

        # 添加第6个项应该淘汰最老的
        await memory_cache.set("key_5", "value_5")

        # 检查最老的项是否被淘汰
        entry = await memory_cache.get("key_0")
        assert entry is None

        # 检查新项是否成功添加
        entry = await memory_cache.get("key_5")
        assert entry is not None
        assert entry.value == "value_5"

    @pytest.mark.asyncio
    async def test_memory_cache_delete(self, memory_cache):
        """测试内存缓存删除"""
        key = "delete_key"
        await memory_cache.set(key, "delete_value")

        # 删除缓存
        result = await memory_cache.delete(key)
        assert result == True

        # 确认删除成功
        entry = await memory_cache.get(key)
        assert entry is None

    @pytest.mark.asyncio
    async def test_memory_cache_stats(self, memory_cache):
        """测试内存缓存统计"""
        # 添加一些缓存项
        await memory_cache.set("key1", "value1")
        await memory_cache.set("key2", "value2")

        stats = await memory_cache.get_stats()

        assert stats["entries_count"] == 2
        assert stats["max_size"] == 5
        assert stats["total_size_bytes"] > 0


class TestMultiLevelCacheManager:
    """多级缓存管理器测试"""

    @pytest.fixture
    async def mock_cache_manager(self):
        """创建模拟的多级缓存管理器"""
        config = CacheConfig(
            l1_max_size=10,
            l1_ttl=60,
            l2_host="localhost",
            l2_port=6379,
            l3_enabled=False  # 禁用持久化缓存以简化测试
        )

        manager = MultiLevelCacheManager(config)

        # 模拟初始化
        manager.l2_cache = Mock()
        manager.l2_cache.get = AsyncMock(return_value=None)
        manager.l2_cache.set = AsyncMock(return_value=True)
        manager.l2_cache.delete = AsyncMock(return_value=True)

        return manager

    @pytest.mark.asyncio
    async def test_multilevel_cache_set_and_get(self, mock_cache_manager):
        """测试多级缓存设置和获取"""
        key = "multilevel_key"
        value = {"complex": "data", "timestamp": time.time()}

        # 设置到多级缓存
        await mock_cache_manager.set(key, value, ttl=300)

        # 从L1获取
        entry = await mock_cache_manager.l1_cache.get(key)
        assert entry is not None
        assert entry.value == value

        # 从管理器获取
        result = await mock_cache_manager.get(key)
        assert result == value

    @pytest.mark.asyncio
    async def test_multilevel_cache_miss(self, mock_cache_manager):
        """测试多级缓存未命中"""
        result = await mock_cache_manager.get("nonexistent_key")
        assert result is None

        # 检查统计
        assert mock_cache_manager.stats["misses"] == 1

    @pytest.mark.asyncio
    async def test_multilevel_cache_delete(self, mock_cache_manager):
        """测试多级缓存删除"""
        key = "delete_key"
        await mock_cache_manager.set(key, "delete_value")

        # 删除
        result = await mock_cache_manager.delete(key)
        assert result == True

        # 确认删除成功
        cached_value = await mock_cache_manager.get(key)
        assert cached_value is None

    @pytest.mark.asyncio
    async def test_multilevel_cache_stats(self, mock_cache_manager):
        """测试多级缓存统计"""
        # 执行一些操作
        await mock_cache_manager.set("key1", "value1")
        await mock_cache_manager.get("key1")  # L1命中
        await mock_cache_manager.get("nonexistent")  # 未命中

        stats = await mock_cache_manager.get_comprehensive_stats()

        assert "overall" in stats
        assert stats["overall"]["l1_hits"] >= 1
        assert stats["overall"]["misses"] >= 1
        assert stats["overall"]["hit_rate"] >= 0


class TestAPICacheMiddleware:
    """API缓存中间件测试"""

    @pytest.fixture
    def cache_rules(self):
        """创建缓存规则"""
        return [
            CacheRule(
                path_pattern="/api/v1/test/*",
                methods=["GET"],
                cache_ttl=300,
                strategy=CacheStrategy.MULTI_LEVEL
            )
        ]

    @pytest.fixture
    def cache_middleware(self, cache_rules):
        """创建缓存中间件"""
        return APICacheMiddleware(None, cache_rules)

    def test_find_matching_rule(self, cache_middleware):
        """测试查找匹配规则"""
        from fastapi import Request

        # 模拟请求对象
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url = Mock()
        mock_request.url.path = "/api/v1/test/users"

        rule = cache_middleware._find_matching_rule(mock_request)

        assert rule is not None
        assert rule.path_pattern == "/api/v1/test/*"
        assert "GET" in rule.methods

    def test_pattern_matching(self):
        """测试路径模式匹配"""
        middleware = APICacheMiddleware(None, [])

        # 测试完全匹配
        assert middleware._pattern_matches("/api/v1/users", "/api/v1/users") == True

        # 测试通配符匹配
        assert middleware._pattern_matches("/api/v1/users/123", "/api/v1/users/*") == True

        # 测试不匹配
        assert middleware._pattern_matches("/api/v1/posts", "/api/v1/users/*") == False

    def test_cache_key_generation(self, cache_middleware):
        """测试缓存键生成"""
        from fastapi import Request, Headers

        # 模拟请求
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/api/v1/test/data"
        mock_request.query_params = {}
        mock_request.headers = Headers({})

        rule = CacheRule(
            path_pattern="/api/v1/test/*",
            methods=["GET"],
            key_strategy=CacheKeyStrategy.PATH_PARAMS
        )

        cache_key = cache_middleware._generate_cache_key(mock_request, rule)

        assert "api_cache" in cache_key
        assert "get" in cache_key
        assert "/api/v1/test/data" in cache_key


class TestCacheWarmupManager:
    """缓存预热管理器测试"""

    @pytest.fixture
    async def warmup_manager(self):
        """创建预热管理器"""
        manager = CacheWarmupManager()

        # 模拟缓存管理器
        manager.cache_manager = Mock()
        manager.cache_manager.get = AsyncMock(return_value=None)
        manager.cache_manager.set = AsyncMock(return_value=True)

        return manager

    @pytest.mark.asyncio
    async def test_add_warmup_task(self, warmup_manager):
        """测试添加预热任务"""
        warmup_manager.warmup_queue = asyncio.Queue(maxsize=10)

        task = WarmupTask(
            id="test_task",
            key="test_key",
            data_generator=AsyncMock(return_value={"data": "test"}),
            priority=WarmupPriority.MEDIUM,
            strategy=WarmupStrategy.MANUAL
        )

        result = await warmup_manager.add_warmup_task(task)
        assert result == True

        # 检查队列中的任务
        queued_task = await warmup_manager.warmup_queue.get()
        assert queued_task.id == task.id

    @pytest.mark.asyncio
    async def test_record_access(self, warmup_manager):
        """测试记录访问"""
        key = "test_access_key"
        user_id = "user123"

        await warmup_manager.record_access(
            key=key,
            user_id=user_id,
            generation_time=0.1,
            response_size=1024,
            hit=True
        )

        # 检查访问模式是否被记录
        assert key in warmup_manager.access_patterns
        pattern = warmup_manager.access_patterns[key]
        assert pattern.access_count == 1
        assert user_id in pattern.user_segments
        assert pattern.generation_time == 0.1
        assert pattern.response_size == 1024

    def test_access_pattern_priority_score(self):
        """测试访问模式优先级分数计算"""
        from backend.core.cache.cache_warmup import AccessPattern

        pattern = AccessPattern(
            key_pattern="test_key",
            access_count=100,
            avg_interval=30,  # 30秒间隔
            generation_time=0.5,  # 0.5秒生成时间
            hit_rate=0.3,  # 30%命中率
            peak_hours=[14, 15, 16]  # 当前为峰值时间
        )

        score = pattern.get_priority_score()
        assert score > 0
        assert isinstance(score, float)


class TestCacheMonitoringSystem:
    """缓存监控系统测试"""

    @pytest.fixture
    def monitoring_system(self):
        """创建监控系统"""
        system = CacheMonitoringSystem()
        return system

    def test_metrics_collection_counter(self, monitoring_system):
        """测试计数器指标收集"""
        metric_name = "test.counter"

        monitoring_system.metrics_collector.record_counter(metric_name, 5)
        monitoring_system.metrics_collector.record_counter(metric_name, 3)

        # 检查计数器值
        assert monitoring_system.metrics_collector.counters[metric_name] == 8

        # 检查指标点
        assert len(monitoring_system.metrics_collector.metrics[metric_name]) == 2

    def test_metrics_collection_gauge(self, monitoring_system):
        """测试仪表盘指标收集"""
        metric_name = "test.gauge"

        monitoring_system.metrics_collector.record_gauge(metric_name, 75.5)
        monitoring_system.metrics_collector.record_gauge(metric_name, 80.2)

        # 检查仪表盘值（应该是最后的值）
        assert monitoring_system.metrics_collector.gauges[metric_name] == 80.2

    def test_metrics_collection_timer(self, monitoring_system):
        """测试计时器指标收集"""
        metric_name = "test.timer"

        monitoring_system.metrics_collector.record_timer(metric_name, 0.1)
        monitoring_system.metrics_collector.record_timer(metric_name, 0.2)
        monitoring_system.metrics_collector.record_timer(metric_name, 0.15)

        # 检查计时器记录
        timer_values = list(monitoring_system.metrics_collector.timers[metric_name])
        assert len(timer_values) == 3
        assert 0.1 in timer_values
        assert 0.2 in timer_values
        assert 0.15 in timer_values

    def test_metrics_summary(self, monitoring_system):
        """测试指标摘要计算"""
        metric_name = "test.summary"

        # 添加一些指标数据
        values = [10, 20, 30, 40, 50]
        for value in values:
            monitoring_system.metrics_collector.record_gauge(metric_name, value)

        summary = monitoring_system.metrics_collector.get_metrics_summary(metric_name)

        assert summary["count"] == len(values)
        assert summary["min"] == min(values)
        assert summary["max"] == max(values)
        assert summary["avg"] == sum(values) / len(values)
        assert summary["sum"] == sum(values)

    def test_performance_analysis_rules(self):
        """测试性能分析规则"""
        metrics_collector = CacheMetricsCollector()
        analyzer = CachePerformanceAnalyzer(metrics_collector)

        assert len(analyzer.analysis_rules) > 0

        # 检查规则格式
        for rule in analyzer.analysis_rules:
            assert "name" in rule
            assert "metric" in rule
            assert "condition" in rule
            assert "threshold" in rule
            assert "severity" in rule
            assert "message" in rule

    @pytest.mark.asyncio
    async def test_performance_analysis(self):
        """测试性能分析"""
        metrics_collector = CacheMetricsCollector()
        analyzer = CachePerformanceAnalyzer(metrics_collector)

        # 模拟一些指标数据
        metrics_collector.record_gauge("cache.overall_hit_rate", 0.65)  # 低于阈值

        analysis = await analyzer.analyze_performance()

        assert "timestamp" in analysis
        assert "overall_score" in analysis
        assert "alerts" in analysis
        assert "recommendations" in analysis
        assert "metrics_summary" in analysis

        # 由于命中率低，应该有告警
        if analysis["alerts"]:
            alert = analysis["alerts"][0]
            assert isinstance(alert, PerformanceAlert)
            assert alert.severity in [AlertSeverity.LOW, AlertSeverity.MEDIUM,
                                   AlertSeverity.HIGH, AlertSeverity.CRITICAL]


class TestCacheSystemIntegration:
    """缓存系统集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_cache_flow(self):
        """端到端缓存流程测试"""
        # 创建配置
        config = CacheConfig(
            l1_max_size=5,
            l1_ttl=1,
            l3_enabled=False
        )

        # 创建管理器（使用模拟Redis）
        manager = MultiLevelCacheManager(config)

        # 模拟Redis缓存
        manager.l2_cache = Mock()
        manager.l2_cache.get = AsyncMock(return_value=None)
        manager.l2_cache.set = AsyncMock(return_value=True)
        manager.l2_cache.delete = AsyncMock(return_value=True)
        manager.l2_cache.initialize = AsyncMock()

        # 模拟初始化
        await manager.l2_cache.initialize()

        try:
            # 测试完整流程
            key = "integration_key"
            value = {"test": "integration", "data": list(range(100))}

            # 1. 设置缓存
            await manager.set(key, value, ttl=300)

            # 2. 获取缓存（应该从L1命中）
            cached_value = await manager.get(key)
            assert cached_value == value

            # 3. 检查统计
            assert manager.stats["l1_hits"] >= 1
            assert manager.stats["sets"] >= 1

            # 4. 删除缓存
            result = await manager.delete(key)
            assert result == True

            # 5. 确认删除成功
            cached_value = await manager.get(key)
            assert cached_value is None

            # 6. 获取综合统计
            stats = await manager.get_comprehensive_stats()
            assert "overall" in stats
            assert "l1_memory" in stats

        finally:
            await manager.close()

    @pytest.mark.asyncio
    async def test_cache_middleware_integration(self):
        """缓存中间件集成测试"""
        # 创建测试规则
        rules = [
            CacheRule(
                path_pattern="/test/api/*",
                methods=["GET"],
                cache_ttl=60,
                strategy=CacheStrategy.MEMORY_ONLY
            )
        ]

        middleware = APICacheMiddleware(None, rules)

        # 模拟缓存管理器
        middleware.cache_manager = Mock()
        middleware.cache_manager.get = AsyncMock(return_value=None)
        middleware.cache_manager.set = AsyncMock(return_value=True)

        # 模拟请求
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/test/api/users"
        mock_request.query_params = {}
        mock_request.headers = {}

        # 模拟下一个处理函数
        async def mock_call_next(request):
            # 模拟响应
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.body = '{"users": []}'.encode()
            return mock_response

        # 测试中间件处理
        response = await middleware.dispatch(mock_request, mock_call_next)

        # 验证结果
        assert response is not None
        assert hasattr(response, 'headers')
        assert response.headers.get("X-Cache") in ["HIT", "MISS", "ERROR"]


# 性能测试
class TestCachePerformance:
    """缓存性能测试"""

    @pytest.mark.asyncio
    async def test_cache_performance_benchmark(self):
        """缓存性能基准测试"""
        config = CacheConfig(l1_max_size=1000, l3_enabled=False)
        manager = MultiLevelCacheManager(config)

        # 模拟Redis
        manager.l2_cache = Mock()
        manager.l2_cache.get = AsyncMock(return_value=None)
        manager.l2_cache.set = AsyncMock(return_value=True)
        manager.l2_cache.initialize = AsyncMock()

        await manager.l2_cache.initialize()

        try:
            # 性能测试参数
            num_operations = 1000
            data_size = 100  # 100字符数据

            test_data = "x" * data_size
            keys = [f"perf_key_{i}" for i in range(num_operations)]

            # 测试写入性能
            start_time = time.time()
            for i, key in enumerate(keys):
                await manager.set(key, f"{test_data}_{i}")
            set_time = time.time() - start_time

            # 测试读取性能
            start_time = time.time()
            for key in keys:
                await manager.get(key)
            get_time = time.time() - start_time

            # 计算性能指标
            set_ops_per_sec = num_operations / set_time
            get_ops_per_sec = num_operations / get_time

            # 验证性能要求
            assert set_ops_per_sec > 1000  # 至少1000 ops/sec
            assert get_ops_per_sec > 5000   # 至少5000 ops/sec (内存读取应该更快)

            print(f"Set performance: {set_ops_per_sec:.0f} ops/sec")
            print(f"Get performance: {get_ops_per_sec:.0f} ops/sec")

        finally:
            await manager.close()


# 运行测试的辅助函数
async def run_cache_tests():
    """运行所有缓存测试"""
    import pytest

    # 运行测试
    test_args = [
        "backend/tests/test_cache_system.py",
        "-v",
        "--tb=short",
        "--disable-warnings"
    ]

    result = pytest.main(test_args)
    return result == 0


if __name__ == "__main__":
    # 如果直接运行此文件，执行测试
    asyncio.run(run_cache_tests())