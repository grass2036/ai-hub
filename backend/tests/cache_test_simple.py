#!/usr/bin/env python3
"""
Simple cache system test - avoid unicode issues
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_cache_basic():
    """Test basic cache functionality"""
    print("=" * 50)
    print("Cache System Quick Test")
    print("=" * 50)

    try:
        # Test basic cache imports
        print("Testing imports...")
        from backend.core.cache.multi_level_cache import CacheConfig, MultiLevelCacheManager
        from backend.core.cache.cache_warmup import get_warmup_manager
        from backend.core.cache.cache_monitor import get_monitoring_system
        print("✓ All imports successful")

        # Test cache configuration
        print("Testing cache configuration...")
        config = CacheConfig(l1_max_size=100, l1_ttl=60, l3_enabled=False)
        print(f"✓ Cache config created: L1 size={config.l1_max_size}")

        # Test cache manager creation
        print("Testing cache manager...")
        manager = MultiLevelCacheManager(config)
        print("✓ Cache manager created")

        # Mock Redis for testing
        import unittest.mock
        with unittest.mock.patch('aioredis.Redis'):
            await manager.initialize()
            print("✓ Cache manager initialized (with mock Redis)")

        # Test basic cache operations
        print("Testing cache operations...")
        test_key = "test_key_simple"
        test_value = {"message": "Hello Cache!", "timestamp": time.time()}

        # Set operation
        await manager.set(test_key, test_value, ttl=300)
        print("✓ Cache set operation successful")

        # Get operation
        cached_value = await manager.get(test_key)
        assert cached_value == test_value, f"Expected {test_value}, got {cached_value}"
        print("✓ Cache get operation successful")

        # Get statistics
        stats = await manager.get_comprehensive_stats()
        print(f"✓ Cache stats retrieved: L1 hits={stats.get('overall', {}).get('l1_hits', 0)}")

        await manager.close()
        print("✓ Cache manager closed")

        print("\n" + "=" * 50)
        print("All basic cache tests PASSED!")
        print("✅ Cache System is working correctly!")
        print("=" * 50)

        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_cache_components():
    """Test individual cache components"""
    print("\nTesting individual components...")

    try:
        # Test Memory Cache
        print("Testing MemoryCache...")
        from backend.core.cache.multi_level_cache import MemoryCache

        memory_cache = MemoryCache(max_size=10, default_ttl=1)
        await memory_cache.set("mem_key", "mem_value")
        entry = await memory_cache.get("mem_key")
        assert entry is not None and entry.value == "mem_value"
        print("✓ MemoryCache working")

        # Test Cache Entry
        print("Testing CacheEntry...")
        from backend.core.cache.multi_level_cache import CacheEntry, CacheLevel

        entry = CacheEntry(
            key="test_entry",
            value="test_value",
            level=CacheLevel.L1_MEMORY,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl=300
        )
        assert not entry.is_expired()
        print("✓ CacheEntry working")

        return True

    except Exception as e:
        print(f"❌ Component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_structure():
    """Test API structure"""
    print("\nTesting API structure...")

    try:
        # Test API router import
        print("Testing API imports...")
        from backend.api.v1.cache import router
        print("✓ Cache API router imported")

        # Test middleware import
        from backend.middleware.cache_middleware import APICacheMiddleware
        print("✓ Cache middleware imported")

        # Test response model
        from backend.api.v1.cache import CacheStatsResponse
        response = CacheStatsResponse(
            success=True,
            message="Test",
            data={"test": "data"}
        )
        assert response.success == True
        print("✓ Cache API response model working")

        return True

    except Exception as e:
        print(f"❌ API structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("Starting cache system tests...")

    tests = [
        ("Basic Cache Functionality", test_cache_basic),
        ("Individual Components", test_cache_components),
        ("API Structure", test_api_structure)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = await test_func()
            if result:
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")

    print(f"\n{'='*60}")
    print(f"Test Summary: {passed}/{total} tests passed")
    print(f"Success Rate: {(passed/total)*100:.1f}%")

    if passed == total:
        print("🎉 All cache system tests PASSED!")
        print("Cache System is ready for use!")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed!")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        exit(1)