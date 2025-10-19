"""
缓存系统配置和优化模块
Week 6 Day 2: 性能优化和调优 - 缓存系统优化
实现多层缓存、智能失效、分布式缓存、缓存预热等功能
"""

import asyncio
import json
import time
import hashlib
import logging
import pickle
import gzip
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from contextlib import asynccontextmanager
import aioredis
import aiomcache
from cachetools import TTLCache, LRUCache
from functools import wraps
import numpy as np

from backend.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class CacheLevel(Enum):
    """缓存层级"""
    L1_MEMORY = "L1_MEMORY"  # 内存缓存
    L2_REDIS = "L2_REDIS"    # Redis缓存
    L3_DISTRIBUTED = "L3_DISTRIBUTED"  # 分布式缓存

class CachePolicy(Enum):
    """缓存策略"""
    LRU = "LRU"  # 最近最少使用
    LFU = "LFU"  # 最少使用频率
    TTL = "TTL"  # 生存时间
    FIFO = "FIFO"  # 先进先出

@dataclass
class CacheConfig:
    """缓存配置"""
    ttl: int = 300  # 生存时间（秒）
    max_size: int = 1000  # 最大条目数
    compression: bool = True  # 是否压缩
    serialization: str = "json"  # 序列化方式
    cache_levels: List[CacheLevel] = field(default_factory=lambda: [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS])
    eviction_policy: CachePolicy = CachePolicy.LRU
    enable_stats: bool = True

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    compressed: bool = False
    version: int = 1

@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0

class MemoryCache:
    """内存缓存实现"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order = []  # LRU访问顺序
        self.stats = CacheStats()
        self._lock = asyncio.Lock()

    def _generate_cache_key(self, key: str, version: int = 1) -> str:
        """生成缓存键"""
        return f"{key}:v{version}"

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        async with self._lock:
            entry = self.cache.get(key)
            if entry is None:
                self.stats.misses += 1
                return None

            # 检查是否过期
            if datetime.now() > entry.expires_at:
                await self.delete(key)
                self.stats.misses += 1
                return None

            # 更新访问信息
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            self._update_access_order(key)

            self.stats.hits += 1
            return self._deserialize_value(entry.value, entry.compressed)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        async with self._lock:
            try:
                current_time = datetime.now()
                actual_ttl = ttl or self.config.ttl
                expires_at = current_time + timedelta(seconds=actual_ttl)

                # 序列化值
                serialized_value, compressed = self._serialize_value(value)

                entry = CacheEntry(
                    key=key,
                    value=serialized_value,
                    created_at=current_time,
                    expires_at=expires_at,
                    size_bytes=len(serialized_value),
                    compressed=compressed
                )

                # 检查容量限制
                if len(self.cache) >= self.config.max_size:
                    await self._evict_entries()

                self.cache[key] = entry
                self._update_access_order(key)

                self.stats.sets += 1
                self.stats.entry_count = len(self.cache)
                self.stats.size_bytes += entry.size_bytes

                return True

            except Exception as e:
                logger.error(f"内存缓存设置失败: {e}")
                return False

    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        async with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                del self.cache[key]
                self.access_order.remove(key)
                self.stats.deletes += 1
                self.stats.entry_count = len(self.cache)
                self.stats.size_bytes -= entry.size_bytes
                return True
            return False

    async def clear(self) -> bool:
        """清空缓存"""
        async with self._lock:
            self.cache.clear()
            self.access_order.clear()
            self.stats = CacheStats()
            return True

    def _update_access_order(self, key: str):
        """更新访问顺序"""
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

    async def _evict_entries(self):
        """驱逐缓存条目"""
        if not self.access_order:
            return

        if self.config.eviction_policy == CachePolicy.LRU:
            # 删除最少使用的条目
            evict_count = max(1, len(self.cache) // 10)  # 删除10%
            for _ in range(evict_count):
                if self.access_order:
                    key_to_evict = self.access_order.pop(0)
                    if key_to_evict in self.cache:
                        entry = self.cache[key_to_evict]
                        del self.cache[key_to_evict]
                        self.stats.evictions += 1
                        self.stats.size_bytes -= entry.size_bytes

        elif self.config.eviction_policy == CachePolicy.FIFO:
            # 删除最旧的条目
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].created_at)
            entry = self.cache[oldest_key]
            del self.cache[oldest_key]
            self.access_order.remove(oldest_key)
            self.stats.evictions += 1
            self.stats.size_bytes -= entry.size_bytes

    def _serialize_value(self, value: Any) -> Tuple[bytes, bool]:
        """序列化值"""
        try:
            if self.config.serialization == "json":
                serialized = json.dumps(value, default=str).encode('utf-8')
            elif self.config.serialization == "pickle":
                serialized = pickle.dumps(value)
            else:
                serialized = str(value).encode('utf-8')

            # 压缩
            if self.config.compression and len(serialized) > 1024:  # 只压缩大于1KB的数据
                compressed = gzip.compress(serialized)
                if len(compressed) < len(serialized):  # 只在压缩有效时使用
                    return compressed, True

            return serialized, False

        except Exception as e:
            logger.error(f"序列化失败: {e}")
            return str(value).encode('utf-8'), False

    def _deserialize_value(self, serialized: bytes, compressed: bool) -> Any:
        """反序列化值"""
        try:
            # 解压缩
            if compressed:
                serialized = gzip.decompress(serialized)

            if self.config.serialization == "json":
                return json.loads(serialized.decode('utf-8'))
            elif self.config.serialization == "pickle":
                return pickle.loads(serialized)
            else:
                return serialized.decode('utf-8')

        except Exception as e:
            logger.error(f"反序列化失败: {e}")
            return serialized.decode('utf-8', errors='ignore')

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.stats.hits + self.stats.misses
        hit_rate = (self.stats.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "type": "memory",
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "hit_rate_percent": round(hit_rate, 2),
            "sets": self.stats.sets,
            "deletes": self.stats.deletes,
            "evictions": self.stats.evictions,
            "entry_count": self.stats.entry_count,
            "size_bytes": self.stats.size_bytes,
            "max_size": self.config.max_size
        }

class RedisCache:
    """Redis缓存实现"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.redis_client: Optional[aioredis.Redis] = None
        self.stats = CacheStats()
        self._lock = asyncio.Lock()

    async def _get_client(self) -> aioredis.Redis:
        """获取Redis客户端"""
        if self.redis_client is None:
            await self._connect()
        return self.redis_client

    async def _connect(self):
        """连接Redis"""
        try:
            self.redis_client = await aioredis.from_url(
                f"redis://{getattr(settings, 'redis_host', 'localhost')}:{getattr(settings, 'redis_port', 6379)}",
                encoding="utf-8",
                decode_responses=False  # 使用二进制数据
            )
            await self.redis_client.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            client = await self._get_client()
            serialized = await client.get(key)

            if serialized is None:
                self.stats.misses += 1
                return None

            # 解析元数据
            metadata_length = int.from_bytes(serialized[:4], byteorder='big')
            metadata = json.loads(serialized[4:4+metadata_length].decode('utf-8'))
            value_bytes = serialized[4+metadata_length:]

            # 检查是否过期
            if datetime.now() > datetime.fromisoformat(metadata['expires_at']):
                await self.delete(key)
                self.stats.misses += 1
                return None

            self.stats.hits += 1
            return self._deserialize_value(value_bytes, metadata.get('compressed', False))

        except Exception as e:
            logger.error(f"Redis获取失败: {e}")
            self.stats.misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            client = await self._get_client()
            actual_ttl = ttl or self.config.ttl
            expires_at = datetime.now() + timedelta(seconds=actual_ttl)

            # 序列化值
            value_bytes, compressed = self._serialize_value(value)

            # 构建元数据
            metadata = {
                'expires_at': expires_at.isoformat(),
                'compressed': compressed,
                'created_at': datetime.now().isoformat(),
                'version': 1
            }
            metadata_bytes = json.dumps(metadata).encode('utf-8')
            metadata_length = len(metadata_bytes).to_bytes(4, byteorder='big')

            # 组合数据
            serialized = metadata_length + metadata_bytes + value_bytes

            success = await client.setex(key, actual_ttl, serialized)
            if success:
                self.stats.sets += 1
                return True

        except Exception as e:
            logger.error(f"Redis设置失败: {e}")

        return False

    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            client = await self._get_client()
            result = await client.delete(key)
            if result > 0:
                self.stats.deletes += 1
                return True
        except Exception as e:
            logger.error(f"Redis删除失败: {e}")

        return False

    async def clear_pattern(self, pattern: str) -> int:
        """按模式删除缓存"""
        try:
            client = await self._get_client()
            keys = await client.keys(pattern)
            if keys:
                deleted_count = await client.delete(*keys)
                self.stats.deletes += deleted_count
                return deleted_count
        except Exception as e:
            logger.error(f"Redis模式删除失败: {e}")

        return 0

    def _serialize_value(self, value: Any) -> Tuple[bytes, bool]:
        """序列化值（与MemoryCache相同）"""
        try:
            if self.config.serialization == "json":
                serialized = json.dumps(value, default=str).encode('utf-8')
            elif self.config.serialization == "pickle":
                serialized = pickle.dumps(value)
            else:
                serialized = str(value).encode('utf-8')

            if self.config.compression and len(serialized) > 1024:
                compressed = gzip.compress(serialized)
                if len(compressed) < len(serialized):
                    return compressed, True

            return serialized, False

        except Exception as e:
            logger.error(f"序列化失败: {e}")
            return str(value).encode('utf-8'), False

    def _deserialize_value(self, serialized: bytes, compressed: bool) -> Any:
        """反序列化值（与MemoryCache相同）"""
        try:
            if compressed:
                serialized = gzip.decompress(serialized)

            if self.config.serialization == "json":
                return json.loads(serialized.decode('utf-8'))
            elif self.config.serialization == "pickle":
                return pickle.loads(serialized)
            else:
                return serialized.decode('utf-8')

        except Exception as e:
            logger.error(f"反序列化失败: {e}")
            return serialized.decode('utf-8', errors='ignore')

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.stats.hits + self.stats.misses
        hit_rate = (self.stats.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "type": "redis",
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "hit_rate_percent": round(hit_rate, 2),
            "sets": self.stats.sets,
            "deletes": self.stats.deletes,
            "connected": self.redis_client is not None
        }

class MultiLevelCache:
    """多层缓存系统"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.caches = {}
        self.stats = CacheStats()

        # 初始化缓存层级
        for level in config.cache_levels:
            if level == CacheLevel.L1_MEMORY:
                self.caches[level] = MemoryCache(config)
            elif level == CacheLevel.L2_REDIS:
                self.caches[level] = RedisCache(config)

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值（按层级查找）"""
        for level in self.config.cache_levels:
            if level in self.caches:
                cache = self.caches[level]
                value = await cache.get(key)
                if value is not None:
                    # 将值回填到更高级的缓存
                    await self._backfill_higher_levels(key, value, level)
                    self.stats.hits += 1
                    return value

        self.stats.misses += 1
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值（设置到所有层级）"""
        success = True
        for cache in self.caches.values():
            result = await cache.set(key, value, ttl)
            success = success and result

        if success:
            self.stats.sets += 1

        return success

    async def delete(self, key: str) -> bool:
        """删除缓存值（从所有层级删除）"""
        success = True
        for cache in self.caches.values():
            result = await cache.delete(key)
            success = success and result

        if success:
            self.stats.deletes += 1

        return success

    async def clear_pattern(self, pattern: str) -> Dict[CacheLevel, int]:
        """按模式清理缓存"""
        results = {}
        for level, cache in self.caches.items():
            if hasattr(cache, 'clear_pattern'):
                count = await cache.clear_pattern(pattern)
                results[level] = count
            else:
                results[level] = 0

        return results

    async def _backfill_higher_levels(self, key: str, value: Any, found_level: CacheLevel):
        """将值回填到更高级的缓存"""
        found_index = self.config.cache_levels.index(found_level)
        for i in range(found_index):
            higher_level = self.config.cache_levels[i]
            if higher_level in self.caches:
                await self.caches[higher_level].set(key, value, self.config.ttl // 2)  # 更短的TTL

    def get_stats(self) -> Dict[str, Any]:
        """获取多层缓存统计"""
        total_requests = self.stats.hits + self.stats.misses
        hit_rate = (self.stats.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "multi_level": {
                "hits": self.stats.hits,
                "misses": self.stats.misses,
                "hit_rate_percent": round(hit_rate, 2),
                "sets": self.stats.sets,
                "deletes": self.stats.deletes
            },
            "levels": {
                level.value: cache.get_stats()
                for level, cache in self.caches.items()
            }
        }

class CacheManager:
    """缓存管理器"""

    def __init__(self):
        self.caches: Dict[str, MultiLevelCache] = {}
        self.default_config = CacheConfig()

    def register_cache(self, name: str, config: CacheConfig = None) -> MultiLevelCache:
        """注册缓存实例"""
        if config is None:
            config = self.default_config

        cache = MultiLevelCache(config)
        self.caches[name] = cache
        logger.info(f"注册缓存实例: {name}")
        return cache

    def get_cache(self, name: str) -> Optional[MultiLevelCache]:
        """获取缓存实例"""
        return self.caches.get(name)

    async def warm_up_cache(self, cache_name: str, data_loader: Callable, keys: List[str]):
        """缓存预热"""
        cache = self.get_cache(cache_name)
        if not cache:
            logger.error(f"缓存实例不存在: {cache_name}")
            return

        logger.info(f"开始预热缓存: {cache_name}, 条目数: {len(keys)}")

        tasks = []
        for key in keys:
            task = self._load_and_cache(cache, data_loader, key)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if not isinstance(r, Exception))

        logger.info(f"缓存预热完成: {cache_name}, 成功: {success_count}/{len(keys)}")

    async def _load_and_cache(self, cache: MultiLevelCache, data_loader: Callable, key: str):
        """加载并缓存单个条目"""
        try:
            value = await data_loader(key)
            if value is not None:
                await cache.set(key, value)
        except Exception as e:
            logger.error(f"缓存预热失败 {key}: {e}")

    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有缓存统计"""
        return {
            name: cache.get_stats()
            for name, cache in self.caches.items()
        }

# 全局缓存管理器
cache_manager = CacheManager()

# 装饰器函数
def cache_result(
    cache_name: str = "default",
    ttl: int = None,
    key_generator: Callable = None,
    unless: Callable = None
):
    """缓存结果装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 检查条件
            if unless and unless(*args, **kwargs):
                return await func(*args, **kwargs)

            # 生成缓存键
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

            # 获取缓存
            cache = cache_manager.get_cache(cache_name)
            if cache:
                cached_result = await cache.get(cache_key)
                if cached_result is not None:
                    return cached_result

            # 执行函数
            result = await func(*args, **kwargs)

            # 缓存结果
            if cache:
                await cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator

# 测试函数
async def test_cache_system():
    """测试缓存系统功能"""
    print("🚀 测试缓存系统功能...")

    # 注册缓存实例
    default_cache = cache_manager.register_cache("default", CacheConfig(ttl=60, max_size=100))
    user_cache = cache_manager.register_cache("users", CacheConfig(ttl=300, max_size=500))

    # 测试基本缓存操作
    await default_cache.set("test_key", {"data": "test_value", "timestamp": datetime.now().isoformat()})
    cached_value = await default_cache.get("test_key")
    print(f"缓存测试 - 获取值: {cached_value}")

    # 测试多层缓存
    await user_cache.set("user:123", {"name": "张三", "age": 30})
    user_data = await user_cache.get("user:123")
    print(f"用户缓存测试: {user_data}")

    # 测试缓存装饰器
    @cache_result(cache_name="default", ttl=120)
    async def expensive_function(n: int) -> int:
        await asyncio.sleep(0.1)  # 模拟耗时操作
        return n * n

    # 第一次调用（无缓存）
    start_time = time.time()
    result1 = await expensive_function(10)
    time1 = time.time() - start_time

    # 第二次调用（有缓存）
    start_time = time.time()
    result2 = await expensive_function(10)
    time2 = time.time() - start_time

    print(f"\n装饰器测试:")
    print(f"第一次调用耗时: {time1:.3f}秒，结果: {result1}")
    print(f"第二次调用耗时: {time2:.3f}秒，结果: {result2}")
    print(f"性能提升: {((time1 - time2) / time1 * 100):.1f}%")

    # 获取缓存统计
    stats = cache_manager.get_all_stats()
    print(f"\n📊 缓存统计:")
    for name, stat in stats.items():
        print(f"{name}: 命中率 {stat['multi_level']['hit_rate_percent']:.1f}%")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_cache_system())