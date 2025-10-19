"""
智能缓存系统
Week 5 Day 4: 高级AI功能 - 智能缓存系统
"""

import asyncio
import hashlib
import json
import time
import pickle
import gzip
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from abc import ABC, abstractmethod

import redis
from cachetools import TTLCache, LFUCache, LRUCache
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "lru"           # 最近最少使用
    LFU = "lfu"           # 最少使用频率
    TTL = "ttl"           # 时间过期
    ADAPTIVE = "adaptive" # 自适应策略


class CacheLevel(Enum):
    """缓存级别"""
    MEMORY = "memory"     # 内存缓存
    REDIS = "redis"       # Redis缓存
    DISTRIBUTED = "distributed"  # 分布式缓存


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl: Optional[int] = None
    size_bytes: int = 0
    tags: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return datetime.utcnow() > self.created_at + timedelta(seconds=self.ttl)

    def touch(self):
        """更新访问时间"""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "key": self.key,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "ttl": self.ttl,
            "size_bytes": self.size_bytes,
            "tags": self.tags,
            "metadata": self.metadata
        }


@dataclass
class CacheStats:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0

    @property
    def hit_rate(self) -> float:
        """命中率"""
        total_requests = self.hits + self.misses
        return (self.hits / total_requests * 100) if total_requests > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "total_size_bytes": self.total_size_bytes,
            "entry_count": self.entry_count,
            "hit_rate": self.hit_rate
        }


class CacheBackend(ABC):
    """缓存后端接口"""

    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        """获取缓存条目"""
        pass

    @abstractmethod
    async def set(self, entry: CacheEntry) -> bool:
        """设置缓存条目"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存条目"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """清空缓存"""
        pass

    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """获取键列表"""
        pass


class MemoryCacheBackend(CacheBackend):
    """内存缓存后端"""

    def __init__(self, max_size: int = 1000, strategy: CacheStrategy = CacheStrategy.LRU):
        self.max_size = max_size
        self.strategy = strategy

        if strategy == CacheStrategy.LRU:
            self.cache = LRUCache(maxsize=max_size)
        elif strategy == CacheStrategy.LFU:
            self.cache = LFUCache(maxsize=max_size)
        elif strategy == CacheStrategy.TTL:
            self.cache = TTLCache(maxsize=max_size, ttl=3600)
        else:
            self.cache = LRUCache(maxsize=max_size)

        self.stats = CacheStats()

    async def get(self, key: str) -> Optional[CacheEntry]:
        """获取缓存条目"""
        try:
            entry = self.cache.get(key)
            if entry:
                if entry.is_expired:
                    await self.delete(key)
                    self.stats.misses += 1
                    return None

                entry.touch()
                self.stats.hits += 1
                return entry
            else:
                self.stats.misses += 1
                return None
        except Exception as e:
            logger.error(f"Memory cache get error: {e}")
            self.stats.misses += 1
            return None

    async def set(self, entry: CacheEntry) -> bool:
        """设置缓存条目"""
        try:
            self.cache[entry.key] = entry
            self.stats.sets += 1
            self.stats.total_size_bytes += entry.size_bytes
            return True
        except Exception as e:
            logger.error(f"Memory cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存条目"""
        try:
            if key in self.cache:
                del self.cache[key]
                self.stats.deletes += 1
                return True
            return False
        except Exception as e:
            logger.error(f"Memory cache delete error: {e}")
            return False

    async def clear(self) -> bool:
        """清空缓存"""
        try:
            self.cache.clear()
            self.stats = CacheStats()
            return True
        except Exception as e:
            logger.error(f"Memory cache clear error: {e}")
            return False

    async def keys(self, pattern: str = "*") -> List[str]:
        """获取键列表"""
        return list(self.cache.keys())


class RedisCacheBackend(CacheBackend):
    """Redis缓存后端"""

    def __init__(self, redis_url: str = None, key_prefix: str = "aihub:cache:"):
        self.redis_url = redis_url or settings.redis_url
        self.key_prefix = key_prefix
        self.redis_client = None
        self.stats = CacheStats()
        self._init_redis()

    def _init_redis(self):
        """初始化Redis连接"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=False)
            # 测试连接
            self.redis_client.ping()
            logger.info("Redis cache backend initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            self.redis_client = None

    def _make_key(self, key: str) -> str:
        """生成Redis键"""
        return f"{self.key_prefix}{key}"

    def _serialize_entry(self, entry: CacheEntry) -> bytes:
        """序列化缓存条目"""
        data = {
            'key': entry.key,
            'value': entry.value,
            'created_at': entry.created_at.isoformat(),
            'last_accessed': entry.last_accessed.isoformat(),
            'access_count': entry.access_count,
            'ttl': entry.ttl,
            'size_bytes': entry.size_bytes,
            'tags': entry.tags,
            'metadata': entry.metadata
        }
        serialized = pickle.dumps(data)
        return gzip.compress(serialized)

    def _deserialize_entry(self, data: bytes) -> CacheEntry:
        """反序列化缓存条目"""
        decompressed = gzip.decompress(data)
        cache_data = pickle.loads(decompressed)
        return CacheEntry(
            key=cache_data['key'],
            value=cache_data['value'],
            created_at=datetime.fromisoformat(cache_data['created_at']),
            last_accessed=datetime.fromisoformat(cache_data['last_accessed']),
            access_count=cache_data['access_count'],
            ttl=cache_data['ttl'],
            size_bytes=cache_data['size_bytes'],
            tags=cache_data['tags'],
            metadata=cache_data['metadata']
        )

    async def get(self, key: str) -> Optional[CacheEntry]:
        """获取缓存条目"""
        if not self.redis_client:
            return None

        try:
            redis_key = self._make_key(key)
            data = self.redis_client.get(redis_key)

            if data:
                entry = self._deserialize_entry(data)
                if entry.is_expired:
                    await self.delete(key)
                    self.stats.misses += 1
                    return None

                # 异步更新访问统计
                asyncio.create_task(self._update_access_stats(redis_key, entry))
                self.stats.hits += 1
                return entry
            else:
                self.stats.misses += 1
                return None
        except Exception as e:
            logger.error(f"Redis cache get error: {e}")
            self.stats.misses += 1
            return None

    async def _update_access_stats(self, redis_key: str, entry: CacheEntry):
        """更新访问统计"""
        try:
            entry.touch()
            serialized = self._serialize_entry(entry)
            self.redis_client.set(redis_key, serialized, ex=entry.ttl)
        except Exception as e:
            logger.error(f"Failed to update access stats: {e}")

    async def set(self, entry: CacheEntry) -> bool:
        """设置缓存条目"""
        if not self.redis_client:
            return False

        try:
            redis_key = self._make_key(entry)
            serialized = self._serialize_entry(entry)

            if entry.ttl:
                self.redis_client.setex(redis_key, entry.ttl, serialized)
            else:
                self.redis_client.set(redis_key, serialized)

            self.stats.sets += 1
            self.stats.total_size_bytes += entry.size_bytes
            return True
        except Exception as e:
            logger.error(f"Redis cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存条目"""
        if not self.redis_client:
            return False

        try:
            redis_key = self._make_key(key)
            result = self.redis_client.delete(redis_key) > 0
            if result:
                self.stats.deletes += 1
            return result
        except Exception as e:
            logger.error(f"Redis cache delete error: {e}")
            return False

    async def clear(self) -> bool:
        """清空缓存"""
        if not self.redis_client:
            return False

        try:
            pattern = self._make_key("*")
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            self.stats = CacheStats()
            return True
        except Exception as e:
            logger.error(f"Redis cache clear error: {e}")
            return False

    async def keys(self, pattern: str = "*") -> List[str]:
        """获取键列表"""
        if not self.redis_client:
            return []

        try:
            redis_pattern = self._make_key(pattern)
            redis_keys = self.redis_client.keys(redis_pattern)
            # 移除前缀
            prefix_len = len(self.key_prefix)
            return [key.decode('utf-8')[prefix_len:] for key in redis_keys]
        except Exception as e:
            logger.error(f"Redis cache keys error: {e}")
            return []


class SmartCache:
    """智能缓存管理器"""

    def __init__(self):
        self.backends: Dict[CacheLevel, CacheBackend] = {}
        self.global_stats = CacheStats()
        self.cache_policies: Dict[str, Dict] = {}
        self.warmup_tasks: List[asyncio.Task] = []
        self._init_backends()

    def _init_backends(self):
        """初始化缓存后端"""
        # 内存缓存 - L1缓存
        self.backends[CacheLevel.MEMORY] = MemoryCacheBackend(
            max_size=1000,
            strategy=CacheStrategy.LRU
        )

        # Redis缓存 - L2缓存
        if settings.redis_url:
            self.backends[CacheLevel.REDIS] = RedisCacheBackend()
            logger.info("Redis cache backend enabled")
        else:
            logger.warning("Redis not available, only memory cache enabled")

    def _generate_cache_key(self, prefix: str, data: Any, *args, **kwargs) -> str:
        """生成缓存键"""
        # 组合所有输入数据
        key_data = {
            'prefix': prefix,
            'data': data,
            'args': args,
            'kwargs': sorted(kwargs.items())
        }

        # 生成哈希
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        hash_key = hashlib.md5(key_string.encode()).hexdigest()

        return f"{prefix}:{hash_key}"

    async def get(self, key: str, levels: List[CacheLevel] = None) -> Optional[CacheEntry]:
        """获取缓存值"""
        if levels is None:
            levels = [CacheLevel.MEMORY, CacheLevel.REDIS]

        for level in levels:
            if level not in self.backends:
                continue

            entry = await self.backends[level].get(key)
            if entry:
                # 如果从低级别缓存获取到，需要提升到高级别缓存
                if level != levels[0]:
                    await self.set(entry, [levels[0]])
                return entry

        self.global_stats.misses += 1
        return None

    async def set(
        self,
        entry: CacheEntry,
        levels: List[CacheLevel] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """设置缓存值"""
        if levels is None:
            levels = [CacheLevel.MEMORY, CacheLevel.REDIS]

        # 设置TTL
        if ttl:
            entry.ttl = ttl

        success_count = 0
        for level in levels:
            if level not in self.backends:
                continue

            if await self.backends[level].set(entry):
                success_count += 1

        if success_count > 0:
            self.global_stats.sets += 1
            return True

        return False

    async def delete(self, key: str, levels: List[CacheLevel] = None) -> bool:
        """删除缓存值"""
        if levels is None:
            levels = [CacheLevel.MEMORY, CacheLevel.REDIS]

        success_count = 0
        for level in levels:
            if level not in self.backends:
                continue

            if await self.backends[level].delete(key):
                success_count += 1

        if success_count > 0:
            self.global_stats.deletes += 1
            return True

        return False

    async def clear(self, level: CacheLevel = None) -> bool:
        """清空缓存"""
        if level:
            if level in self.backends:
                return await self.backends[level].clear()
            return False
        else:
            # 清空所有级别
            success = True
            for backend in self.backends.values():
                if not await backend.clear():
                    success = False
            return success

    def cache_function(
        self,
        prefix: str,
        ttl: int = 3600,
        levels: List[CacheLevel] = None,
        key_generator: Callable = None,
        condition: Callable[[Any], bool] = None
    ):
        """函数缓存装饰器"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # 检查缓存条件
                if condition and not condition(*args, **kwargs):
                    return await func(*args, **kwargs)

                # 生成缓存键
                if key_generator:
                    cache_key = key_generator(prefix, *args, **kwargs)
                else:
                    cache_key = self._generate_cache_key(prefix, args, kwargs)

                # 尝试从缓存获取
                cached_entry = await self.get(cache_key, levels)
                if cached_entry:
                    return cached_entry.value

                # 执行函数
                start_time = time.time()
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time

                # 存储到缓存
                try:
                    # 计算结果大小
                    result_size = len(pickle.dumps(result))

                    entry = CacheEntry(
                        key=cache_key,
                        value=result,
                        created_at=datetime.utcnow(),
                        last_accessed=datetime.utcnow(),
                        ttl=ttl,
                        size_bytes=result_size,
                        metadata={
                            'function': func.__name__,
                            'execution_time': execution_time
                        }
                    )

                    await self.set(entry, levels)
                except Exception as e:
                    logger.error(f"Failed to cache function result: {e}")

                return result

            # 保留原函数信息
            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            wrapper._cached_function = True

            return wrapper
        return decorator

    async def invalidate_by_tag(self, tag: str) -> int:
        """根据标签失效缓存"""
        invalidated_count = 0

        for level, backend in self.backends.items():
            try:
                keys = await backend.keys("*")
                for key in keys:
                    entry = await backend.get(key)
                    if entry and tag in entry.tags:
                        if await backend.delete(key):
                            invalidated_count += 1
            except Exception as e:
                logger.error(f"Failed to invalidate cache by tag {tag} on level {level}: {e}")

        return invalidated_count

    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        stats = {
            "global": self.global_stats.to_dict(),
            "backends": {}
        }

        for level, backend in self.backends.items():
            backend_stats = getattr(backend, 'stats', CacheStats())
            stats["backends"][level.value] = backend_stats.to_dict()

        return stats

    async def warmup_cache(self, warmup_data: List[Dict[str, Any]]):
        """缓存预热"""
        logger.info(f"Starting cache warmup with {len(warmup_data)} items")

        tasks = []
        for item in warmup_data:
            task = asyncio.create_task(self._warmup_item(item))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for result in results if not isinstance(result, Exception))
        logger.info(f"Cache warmup completed: {success_count}/{len(warmup_data)} items")

    async def _warmup_item(self, item: Dict[str, Any]):
        """预热单个缓存项"""
        try:
            key = item['key']
            value = item['value']
            ttl = item.get('ttl', 3600)
            tags = item.get('tags', [])

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                ttl=ttl,
                size_bytes=len(pickle.dumps(value)),
                tags=tags
            )

            await self.set(entry, [CacheLevel.MEMORY, CacheLevel.REDIS])
        except Exception as e:
            logger.error(f"Failed to warmup cache item {item.get('key', 'unknown')}: {e}")

    async def cleanup_expired(self) -> int:
        """清理过期缓存"""
        cleaned_count = 0

        for level, backend in self.backends.items():
            try:
                keys = await backend.keys("*")
                for key in keys:
                    entry = await backend.get(key)
                    if entry and entry.is_expired:
                        if await backend.delete(key):
                            cleaned_count += 1
            except Exception as e:
                logger.error(f"Failed to cleanup expired cache on level {level}: {e}")

        logger.info(f"Cleaned up {cleaned_count} expired cache entries")
        return cleaned_count

    def get_cache_policy(self, key_prefix: str) -> Optional[Dict[str, Any]]:
        """获取缓存策略"""
        return self.cache_policies.get(key_prefix)

    def set_cache_policy(self, key_prefix: str, policy: Dict[str, Any]):
        """设置缓存策略"""
        self.cache_policies[key_prefix] = policy

    async def get_optimal_ttl(self, key_prefix: str) -> int:
        """根据访问模式获取最优TTL"""
        policy = self.get_cache_policy(key_prefix)
        if policy and 'ttl' in policy:
            return policy['ttl']

        # 基于历史访问数据的智能TTL计算
        # 这里可以实现更复杂的算法
        return 3600  # 默认1小时


# 全局智能缓存实例
smart_cache = SmartCache()


def cache_ai_response(
    ttl: int = 3600,
    levels: List[CacheLevel] = None,
    condition: Callable = None
):
    """AI响应缓存装饰器"""
    return smart_cache.cache_function(
        prefix="ai_response",
        ttl=ttl,
        levels=levels,
        condition=condition
    )


def cache_model_metrics(
    ttl: int = 300,
    levels: List[CacheLevel] = None
):
    """模型指标缓存装饰器"""
    return smart_cache.cache_function(
        prefix="model_metrics",
        ttl=ttl,
        levels=levels
    )


async def get_smart_cache() -> SmartCache:
    """获取智能缓存实例"""
    return smart_cache


# 缓存预热配置
CACHE_WARMUP_DATA = [
    {
        "key": "system:config",
        "value": {"version": "1.0", "features": ["chat", "monitoring"]},
        "ttl": 86400,
        "tags": ["system", "config"]
    },
    {
        "key": "models:default_list",
        "value": ["grok-4-fast:free", "deepseek-chat-v3.1:free"],
        "ttl": 3600,
        "tags": ["models", "default"]
    }
]


async def init_cache_system():
    """初始化缓存系统"""
    logger.info("Initializing smart cache system...")

    # 设置缓存策略
    smart_cache.set_cache_policy("ai_response", {
        "ttl": 3600,
        "levels": [CacheLevel.MEMORY, CacheLevel.REDIS],
        "compression": True
    })

    smart_cache.set_cache_policy("model_metrics", {
        "ttl": 300,
        "levels": [CacheLevel.MEMORY],
        "compression": False
    })

    # 预热缓存
    await smart_cache.warmup_cache(CACHE_WARMUP_DATA)

    # 启动定期清理任务
    asyncio.create_task(periodic_cache_cleanup())

    logger.info("Smart cache system initialized successfully")


async def periodic_cache_cleanup():
    """定期缓存清理"""
    while True:
        try:
            await asyncio.sleep(3600)  # 每小时清理一次
            await smart_cache.cleanup_expired()
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")