"""
缓存系统快速测试脚本
验证缓存系统���本功能和API接口
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_cache_basic_functionality():
    """测试缓存基本功能"""
    logger.info("🚀 Testing Cache System Basic Functionality...")

    try:
        # 导入缓存模块
        from backend.core.cache.multi_level_cache import (
            CacheConfig, MultiLevelCacheManager, get_cache_manager
        )
        from backend.core.cache.cache_warmup import (
            get_warmup_manager, WarmupPriority
        )
        from backend.core.cache.cache_monitor import (
            get_monitoring_system, record_cache_operation
        )

        # 测试缓存配置
        logger.info("📊 Testing Cache Configuration...")
        config = CacheConfig(
            l1_max_size=100,
            l1_ttl=60,
            l2_host="localhost",
            l2_port=6379,
            l3_enabled=False  # 简化测试
        )
        logger.info(f"✅ Cache config created: L1 size={config.l1_max_size}")

        # 测试缓存管理器
        logger.info("💾 Testing Cache Manager...")
        cache_manager = MultiLevelCacheManager(config)

        # 模拟Redis连接（避免真实Redis依赖）
        import unittest.mock
        with unittest.mock.patch('aioredis.Redis'):
            await cache_manager.initialize()
            logger.info("✅ Cache manager initialized successfully")

        # 测试缓存操作
        test_key = "test_quick_key"
        test_value = {"message": "Hello Cache!", "timestamp": time.time()}

        # 设置缓存
        await cache_manager.set(test_key, test_value, ttl=300)
        logger.info("✅ Cache set operation successful")

        # 获取缓存
        cached_value = await cache_manager.get(test_key)
        assert cached_value == test_value, f"Expected {test_value}, got {cached_value}"
        logger.info("✅ Cache get operation successful")

        # 获取统计信息
        stats = await cache_manager.get_comprehensive_stats()
        logger.info(f"✅ Cache stats retrieved: L1 hits={stats.get('overall', {}).get('l1_hits', 0)}")

        await cache_manager.close()

    except Exception as e:
        logger.error(f"❌ Cache functionality test failed: {e}")
        return False

    return True


async def test_cache_warmup_system():
    """测试缓存预热系统"""
    logger.info("🔥 Testing Cache Warmup System...")

    try:
        from backend.core.cache.cache_warmup import (
            get_warmup_manager, WarmupPriority, WarmupStrategy
        )

        warmup_manager = await get_warmup_manager()

        # 模拟预热任务
        test_keys = ["warmup_test_1", "warmup_test_2", "warmup_test_3"]

        # 强制预热
        scheduled_count = await warmup_manager.force_warmup(test_keys, WarmupPriority.MEDIUM)
        logger.info(f"✅ Scheduled {scheduled_count} warmup tasks")

        # 获取预热统计
        warmup_stats = await warmup_manager.get_warmup_stats()
        logger.info(f"✅ Warmup stats: queue_size={warmup_stats.get('queue_size', 0)}")

    except Exception as e:
        logger.error(f"❌ Cache warmup test failed: {e}")
        return False

    return True


async def test_cache_monitoring_system():
    """测试缓存监控系统"""
    logger.info("📈 Testing Cache Monitoring System...")

    try:
        from backend.core.cache.cache_monitor import (
            get_monitoring_system, MetricType
        )

        monitoring_system = await get_monitoring_system()

        # 记录一些缓存操作
        await record_cache_operation("get", "l1_memory", 0.001, hit=True)
        await record_cache_operation("set", "l1_memory", 0.002, key_size=100)
        await record_cache_operation("get", "l2_redis", 0.005, hit=False)

        logger.info("✅ Recorded cache operations for monitoring")

        # 获取监控仪表盘
        dashboard = await monitoring_system.get_monitoring_dashboard()
        logger.info(f"✅ Monitoring dashboard retrieved: score={dashboard.get('performance_score', 0)}")

    except Exception as e:
        logger.error(f"❌ Cache monitoring test failed: {e}")
        return False

    return True


async def test_cache_api_endpoints():
    """测试缓存API端点"""
    logger.info("🔌 Testing Cache API Endpoints...")

    try:
        from backend.api.v1.cache import router, CacheStatsResponse
        from fastapi import FastAPI

        # 创建测试应用
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        logger.info("✅ Cache API router created successfully")

        # 测试API响应模型
        test_response = CacheStatsResponse(
            success=True,
            message="Test successful",
            data={"test": "data"}
        )

        assert test_response.success == True
        assert test_response.data["test"] == "data"
        logger.info("✅ Cache API response model working")

    except Exception as e:
        logger.error(f"❌ Cache API test failed: {e}")
        return False

    return True


async def test_cache_middleware():
    """测试缓存中间件"""
    logger.info("⚙️ Testing Cache Middleware...")

    try:
        from backend.middleware.cache_middleware import (
            APICacheMiddleware, CacheRule, CacheStrategy, CacheKeyStrategy
        )

        # 创建测试规则
        test_rules = [
            CacheRule(
                path_pattern="/test/api/*",
                methods=["GET"],
                cache_ttl=300,
                strategy=CacheStrategy.MULTI_LEVEL,
                key_strategy=CacheKeyStrategy.PATH_PARAMS
            )
        ]

        # 创建中间件
        middleware = APICacheMiddleware(None, test_rules)

        # 测试规则匹配
        from unittest.mock import Mock
        mock_request = Mock()
        mock_request.method = "GET"
        mock_request.url.path = "/test/api/users"
        mock_request.url = Mock()
        mock_request.url.path = "/test/api/users"
        mock_request.query_params = {}
        mock_request.headers = {}

        rule = middleware._find_matching_rule(mock_request)
        assert rule is not None, "Should find matching rule"
        logger.info("✅ Cache middleware rule matching working")

        # 测试缓存键生成
        cache_key = middleware._generate_cache_key(mock_request, rule)
        assert "api_cache" in cache_key, "Cache key should contain api_cache prefix"
        logger.info("✅ Cache key generation working")

    except Exception as e:
        logger.error(f"❌ Cache middleware test failed: {e}")
        return False

    return True


async def test_cache_performance():
    """测试缓存性能"""
    logger.info("⚡ Testing Cache Performance...")

    try:
        from backend.core.cache.multi_level_cache import CacheConfig, MultiLevelCacheManager
        import time

        config = CacheConfig(l1_max_size=1000, l3_enabled=False)
        manager = MultiLevelCacheManager(config)

        # 模拟Redis
        import unittest.mock
        with unittest.mock.patch('aioredis.Redis'):
            await manager.initialize()

        # 性能测试
        num_operations = 100
        test_data = {"performance": "test", "data": list(range(10))}

        # 测试写入性能
        start_time = time.time()
        for i in range(num_operations):
            await manager.set(f"perf_key_{i}", f"{test_data}_{i}")
        set_time = time.time() - start_time
        set_ops = num_operations / set_time

        # 测试读取性能
        start_time = time.time()
        for i in range(num_operations):
            await manager.get(f"perf_key_{i}")
        get_time = time.time() - start_time
        get_ops = num_operations / get_time

        logger.info(f"✅ Performance results:")
        logger.info(f"   Set: {set_ops:.0f} ops/sec ({set_time:.3f}s)")
        logger.info(f"   Get: {get_ops:.0f} ops/sec ({get_time:.3f}s)")

        # 性能要求检查
        assert set_ops > 100, f"Set performance too low: {set_ops:.0f} ops/sec"
        assert get_ops > 1000, f"Get performance too low: {get_ops:.0f} ops/sec"

        await manager.close()

    except Exception as e:
        logger.error(f"❌ Cache performance test failed: {e}")
        return False

    return True


async def test_cache_integration():
    """测试缓存系统集成"""
    logger.info("🔗 Testing Cache System Integration...")

    try:
        from backend.core.cache.multi_level_cache import get_cache_manager
        from backend.core.cache.cache_warmup import get_warmup_manager
        from backend.core.cache.cache_monitor import get_monitoring_system

        # 获取所有系统组件
        cache_manager = await get_cache_manager()
        warmup_manager = await get_warmup_manager()
        monitoring_system = await get_monitoring_system()

        logger.info("✅ All cache system components initialized")

        # 测试组件间协作
        test_key = "integration_test"
        test_value = {"integration": "test", "timestamp": time.time()}

        # 通过缓存管理器设置
        await cache_manager.set(test_key, test_value)

        # 记录访问到监控系统
        await monitoring_system.record_cache_operation(
            "get", "l1_memory", 0.001, hit=True
        )

        # 获取缓存值
        cached_value = await cache_manager.get(test_key)
        assert cached_value == test_value

        logger.info("✅ Cache system integration working correctly")

    except Exception as e:
        logger.error(f"❌ Cache integration test failed: {e}")
        return False

    return True


async def run_all_cache_tests():
    """运行所有缓存测试"""
    logger.info("🎯 Starting Comprehensive Cache System Tests...")
    logger.info("=" * 60)

    test_functions = [
        ("Basic Functionality", test_cache_basic_functionality),
        ("Warmup System", test_cache_warmup_system),
        ("Monitoring System", test_cache_monitoring_system),
        ("API Endpoints", test_cache_api_endpoints),
        ("Cache Middleware", test_cache_middleware),
        ("Performance Test", test_cache_performance),
        ("Integration Test", test_cache_integration)
    ]

    passed = 0
    total = len(test_functions)

    for test_name, test_func in test_functions:
        logger.info(f"\n🧪 Running {test_name} Test...")
        logger.info("-" * 40)

        try:
            result = await test_func()
            if result:
                logger.info(f"✅ {test_name} Test PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} Test FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} Test ERROR: {e}")

        logger.info("-" * 40)

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info(f"📊 Test Summary: {passed}/{total} tests passed")
    logger.info(f"🏆 Success Rate: {(passed/total)*100:.1f}%")

    if passed == total:
        logger.info("🎉 All cache system tests PASSED!")
        return True
    else:
        logger.error(f"💥 {total - passed} cache system tests FAILED!")
        return False


async def main():
    """主函数"""
    print("🚀 AI Hub Platform - Cache System Quick Test")
    print("=" * 60)

    try:
        success = await run_all_cache_tests()
        if success:
            print("\n🎊 Cache System is ready for production!")
            exit(0)
        else:
            print("\n⚠️  Cache System needs attention before production use.")
            exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())