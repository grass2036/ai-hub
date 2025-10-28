"""
多级缓存管理器 - Redis多层缓存架构
支持L1(内存) -> L2(Redis) -> L3(持久化)三级缓存
"""

import asyncio
import json
import pickle
import time
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import zlib
from abc import ABC, abstractmethod

import aioredis
from aioredis import Redis
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别"""
    L1_MEMORY = "l1_memory"  # 内存缓存 - 最快
    L2_REDIS = "l2_redis"    # Redis缓存 - 快
    L3_PERSISTENT = "l3_persistent"  # 持久化缓存 - 中等


class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "lru"                    # 最近最少使用
    LFU = "lfu"                    # 最少使用频率
    TTL = "ttl"                    # 生存时间
    WRITE_THROUGH = "write_through"  # 写穿透
    WRITE_BACK = "write_back"        # 写回
    WRITE_BEHIND = "write_behind"    # 异步写回


@dataclass
class CacheConfig:
    """缓存配置"""
    # L1 内存缓存配置
    l1_max_size: int = 1000
    l1_ttl: int = 300  # 5分钟

    # L2 Redis缓存配置
    l2_host: str = "localhost"
    l2_port: int = 6379
    l2_db: int = 0
    l2_ttl: int = 3600  # 1小时
    l2_password: Optional[str] = None
    l2_max_connections: int = 20

    # L3 持久化缓存配置
    l3_enabled: bool = True
    l3_storage_path: str = "data/cache"
    l3_ttl: int = 86400  # 24小时

    # 通用配置
    compression_enabled: bool = True
    serialization_method: str = "json"  # json, pickle
    key_prefix: str = "aihub_cache:"
    default_ttl: int = 3600
    max_retry_attempts: int = 3


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    level: CacheLevel
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: int = 0
    size_bytes: int = 0
    compressed: bool = False
    metadata: Optional[Dict] = None

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl <= 0:
            return False
        return time.time() - self.created_at > self.ttl

    def update_access(self):
        """更新访问信息"""
        self.last_accessed = time.time()
        self.access_count += 1


class MemoryCache:
    """L1 内存缓存实现"""

    def __init__(self, max_size: int, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[CacheEntry]:
        """获取缓存条目"""
        async with self._lock:
            entry = self.cache.get(key)
            if entry:
                if entry.is_expired():
                    await self._remove(key)
                    return None
                entry.update_access()
                self._update_access_order(key)
            return entry

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """设置缓存条目"""
        ttl = ttl or self.default_ttl

        async with self._lock:
            # 检查是否需要清理空间
            if len(self.cache) >= self.max_size and key not in self.cache:
                await self._evict_lru()

            # 计算值的大小
            try:
                if isinstance(value, (dict, list)):
                    size_bytes = len(json.dumps(value).encode())
                else:
                    size_bytes = len(str(value).encode())
            except:
                size_bytes = 100  # 默认大小

            entry = CacheEntry(
                key=key,
                value=value,
                level=CacheLevel.L1_MEMORY,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                ttl=ttl,
                size_bytes=size_bytes
            )

            self.cache[key] = entry
            self._update_access_order(key)
            return True

    async def delete(self, key: str) -> bool:
        """删除缓存条目"""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
                return True
            return False

    async def clear(self):
        """清空缓存"""
        async with self._lock:
            self.cache.clear()
            self.access_order.clear()

    async def get_stats(self) -> Dict:
        """获取缓存统计"""
        async with self._lock:
            total_size = sum(entry.size_bytes for entry in self.cache.values())
            expired_count = sum(1 for entry in self.cache.values() if entry.is_expired())

            return {
                "entries_count": len(self.cache),
                "max_size": self.max_size,
                "total_size_bytes": total_size,
                "expired_count": expired_count,
                "hit_rate": self._calculate_hit_rate()
            }

    async def _evict_lru(self):
        """淘汰最近最少使用的条目"""
        if self.access_order:
            lru_key = self.access_order.pop(0)
            if lru_key in self.cache:
                del self.cache[lru_key]

    async def _remove(self, key: str):
        """移除缓存条目"""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_order:
            self.access_order.remove(key)

    def _update_access_order(self, key: str):
        """更新访问顺序"""
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

    def _calculate_hit_rate(self) -> float:
        """计算命中率"""
        if not self.cache:
            return 0.0
        total_accesses = sum(entry.access_count for entry in self.cache.values())
        return min(1.0, (total_accesses - len(self.cache)) / max(1, total_accesses))


class RedisCache:
    """L2 Redis缓存实现"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.redis: Optional[Redis] = None
        self._connection_pool = None
        self._initialized = False

    async def initialize(self):
        """初始化Redis连接"""
        if self._initialized:
            return

        try:
            self._connection_pool = aioredis.ConnectionPool.from_url(
                f"redis://{self.config.l2_host}:{self.config.l2_port}/{self.config.l2_db}",
                password=self.config.l2_password,
                max_connections=self.config.l2_max_connections,
                retry_on_timeout=True
            )

            self.redis = Redis(connection_pool=self._connection_pool)

            # 测试连接
            await self.redis.ping()
            self._initialized = True
            logger.info(f"Redis cache initialized: {self.config.l2_host}:{self.config.l2_port}")

        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            self._initialized = False
            raise

    async def get(self, key: str) -> Optional[CacheEntry]:
        """获取缓存条目"""
        if not self._initialized or not self.redis:
            return None

        try:
            data = await self.redis.get(key)
            if data:
                entry_data = self._deserialize(data)
                if entry_data and not entry_data.is_expired():
                    entry_data.update_access()
                    return entry_data
                else:
                    # 过期条目删除
                    await self.redis.delete(key)
            return None

        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """设置缓存条目"""
        if not self._initialized or not self.redis:
            return False

        ttl = ttl or self.config.l2_ttl

        try:
            entry = CacheEntry(
                key=key,
                value=value,
                level=CacheLevel.L2_REDIS,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                ttl=ttl,
                compressed=self.config.compression_enabled
            )

            serialized_data = self._serialize(entry)
            await self.redis.setex(key, ttl, serialized_data)
            return True

        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存条目"""
        if not self._initialized or not self.redis:
            return False

        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False

    async def clear(self):
        """清空缓存"""
        if not self._initialized or not self.redis:
            return

        try:
            pattern = f"{self.config.key_prefix}*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

    async def get_stats(self) -> Dict:
        """获取Redis统计信息"""
        if not self._initialized or not self.redis:
            return {}

        try:
            info = await self.redis.info()
            keyspace_info = await self.redis.info("keyspace")

            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_redis_hit_rate(info),
                "total_keys": sum(int(ks.split("=")[1].split(",")[0]) if "=" in ks else 0
                                for ks in keyspace_info.keys())
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {}

    def _calculate_redis_hit_rate(self, info: Dict) -> float:
        """计算Redis命中率"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        return hits / max(1, total)

    def _serialize(self, entry: CacheEntry) -> bytes:
        """序列化缓存条目"""
        if self.config.serialization_method == "pickle":
            data = pickle.dumps(asdict(entry))
        else:
            # JSON序列化
            data = json.dumps(asdict(entry), default=str).encode()

        # 压缩
        if self.config.compression_enabled:
            data = zlib.compress(data)

        return data

    def _deserialize(self, data: bytes) -> Optional[CacheEntry]:
        """反序列化缓存条目"""
        try:
            # 解压缩
            if self.config.compression_enabled:
                data = zlib.decompress(data)

            if self.config.serialization_method == "pickle":
                entry_dict = pickle.loads(data)
            else:
                entry_dict = json.loads(data.decode())

            return CacheEntry(**entry_dict)

        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            return None

    async def close(self):
        """关闭连接"""
        if self.redis:
            await self.redis.close()
        if self._connection_pool:
            await self._connection_pool.disconnect()


class PersistentCache:
    """L3 持久化缓存实现"""

    def __init__(self, storage_path: str, default_ttl: int = 86400):
        self.storage_path = storage_path
        self.default_ttl = default_ttl
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self):
        """初始化持久化缓存"""
        import os
        os.makedirs(self.storage_path, exist_ok=True)
        self._initialized = True
        logger.info(f"Persistent cache initialized: {self.storage_path}")

    async def get(self, key: str) -> Optional[CacheEntry]:
        """获取缓存条目"""
        if not self._initialized:
            return None

        async with self._lock:
            try:
                file_path = self._get_file_path(key)
                if not os.path.exists(file_path):
                    return None

                with open(file_path, 'r', encoding='utf-8') as f:
                    entry_data = json.load(f)

                entry = CacheEntry(**entry_data)
                if entry.is_expired():
                    os.remove(file_path)
                    return None

                entry.update_access()
                return entry

            except Exception as e:
                logger.error(f"Persistent cache get error for key {key}: {e}")
                return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """设置缓存条目"""
        if not self._initialized:
            return False

        ttl = ttl or self.default_ttl

        async with self._lock:
            try:
                file_path = self._get_file_path(key)

                entry = CacheEntry(
                    key=key,
                    value=value,
                    level=CacheLevel.L3_PERSISTENT,
                    created_at=time.time(),
                    last_accessed=time.time(),
                    access_count=1,
                    ttl=ttl
                )

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(asdict(entry), f, default=str, indent=2)

                return True

            except Exception as e:
                logger.error(f"Persistent cache set error for key {key}: {e}")
                return False

    async def delete(self, key: str) -> bool:
        """删除缓存条目"""
        if not self._initialized:
            return False

        async with self._lock:
            try:
                file_path = self._get_file_path(key)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    return True
                return False

            except Exception as e:
                logger.error(f"Persistent cache delete error for key {key}: {e}")
                return False

    async def clear(self):
        """清空缓存"""
        if not self._initialized:
            return

        async with self._lock:
            try:
                import shutil
                if os.path.exists(self.storage_path):
                    shutil.rmtree(self.storage_path)
                    os.makedirs(self.storage_path, exist_ok=True)

            except Exception as e:
                logger.error(f"Persistent cache clear error: {e}")

    async def get_stats(self) -> Dict:
        """获取持久化缓存统计"""
        if not self._initialized:
            return {}

        async with self._lock:
            try:
                import os
                files = os.listdir(self.storage_path)
                total_size = 0
                expired_count = 0

                for filename in files:
                    if filename.endswith('.json'):
                        file_path = os.path.join(self.storage_path, filename)
                        total_size += os.path.getsize(file_path)

                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                entry_data = json.load(f)
                            entry = CacheEntry(**entry_data)
                            if entry.is_expired():
                                expired_count += 1
                        except:
                            continue

                return {
                    "files_count": len(files),
                    "total_size_bytes": total_size,
                    "expired_count": expired_count
                }

            except Exception as e:
                logger.error(f"Persistent cache stats error: {e}")
                return {}

    def _get_file_path(self, key: str) -> str:
        """获取缓存文件路径"""
        # 使用MD5哈希作为文件名
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.storage_path, f"{hash_key}.json")


class MultiLevelCacheManager:
    """多级缓存管理器"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.l1_cache = MemoryCache(config.l1_max_size, config.l1_ttl)
        self.l2_cache = RedisCache(config)
        self.l3_cache = PersistentCache(config.l3_storage_path, config.l3_ttl) if config.l3_enabled else None

        self.stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }

        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self):
        """初始化缓存管理器"""
        if self._initialized:
            return

        try:
            await self.l2_cache.initialize()
            if self.l3_cache:
                await self.l3_cache.initialize()

            self._initialized = True
            logger.info("Multi-level cache manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize cache manager: {e}")
            raise

    async def get(self, key: str, use_levels: List[CacheLevel] = None) -> Optional[Any]:
        """获取缓存值（多级查找）"""
        if use_levels is None:
            use_levels = [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_PERSISTENT]

        # L1 缓存查找
        if CacheLevel.L1_MEMORY in use_levels:
            entry = await self.l1_cache.get(key)
            if entry:
                self.stats["l1_hits"] += 1
                await self._promote_to_l1_if_needed(key, entry)
                return entry.value

        # L2 缓存查找
        if CacheLevel.L2_REDIS in use_levels:
            entry = await self.l2_cache.get(key)
            if entry:
                self.stats["l2_hits"] += 1
                # 提升到L1
                await self.l1_cache.set(key, entry.value, self.config.l1_ttl)
                return entry.value

        # L3 缓存查找
        if self.l3_cache and CacheLevel.L3_PERSISTENT in use_levels:
            entry = await self.l3_cache.get(key)
            if entry:
                self.stats["l3_hits"] += 1
                # 提升到L2和L1
                await self.l2_cache.set(key, entry.value, self.config.l2_ttl)
                await self.l1_cache.set(key, entry.value, self.config.l1_ttl)
                return entry.value

        # 未命中
        self.stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: int = None, levels: List[CacheLevel] = None):
        """设置缓存值（多级存储）"""
        if levels is None:
            levels = [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_PERSISTENT]

        self.stats["sets"] += 1

        # 设置到指定级别的缓存
        if CacheLevel.L1_MEMORY in levels:
            await self.l1_cache.set(key, value, ttl or self.config.l1_ttl)

        if CacheLevel.L2_REDIS in levels:
            await self.l2_cache.set(key, value, ttl or self.config.l2_ttl)

        if self.l3_cache and CacheLevel.L3_PERSISTENT in levels:
            await self.l3_cache.set(key, value, ttl or self.config.l3_ttl)

    async def delete(self, key: str, levels: List[CacheLevel] = None) -> bool:
        """删除缓存值（从多级删除）"""
        if levels is None:
            levels = [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_PERSISTENT]

        self.stats["deletes"] += 1
        results = []

        if CacheLevel.L1_MEMORY in levels:
            results.append(await self.l1_cache.delete(key))

        if CacheLevel.L2_REDIS in levels:
            results.append(await self.l2_cache.delete(key))

        if self.l3_cache and CacheLevel.L3_PERSISTENT in levels:
            results.append(await self.l3_cache.delete(key))

        return any(results)

    async def clear(self, levels: List[CacheLevel] = None):
        """清空缓存"""
        if levels is None:
            levels = [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_PERSISTENT]

        tasks = []

        if CacheLevel.L1_MEMORY in levels:
            tasks.append(self.l1_cache.clear())

        if CacheLevel.L2_REDIS in levels:
            tasks.append(self.l2_cache.clear())

        if self.l3_cache and CacheLevel.L3_PERSISTENT in levels:
            tasks.append(self.l3_cache.clear())

        await asyncio.gather(*tasks, return_exceptions=True)

    async def get_comprehensive_stats(self) -> Dict:
        """获取综合统计信息"""
        l1_stats = await self.l1_cache.get_stats()
        l2_stats = await self.l2_cache.get_stats()
        l3_stats = await self.l3_cache.get_stats() if self.l3_cache else {}

        total_requests = sum([
            self.stats["l1_hits"],
            self.stats["l2_hits"],
            self.stats["l3_hits"],
            self.stats["misses"]
        ])

        overall_hit_rate = (
            (self.stats["l1_hits"] + self.stats["l2_hits"] + self.stats["l3_hits"]) /
            max(1, total_requests)
        )

        return {
            "overall": {
                "total_requests": total_requests,
                "hit_rate": overall_hit_rate,
                "l1_hits": self.stats["l1_hits"],
                "l2_hits": self.stats["l2_hits"],
                "l3_hits": self.stats["l3_hits"],
                "misses": self.stats["misses"],
                "sets": self.stats["sets"],
                "deletes": self.stats["deletes"]
            },
            "l1_memory": l1_stats,
            "l2_redis": l2_stats,
            "l3_persistent": l3_stats
        }

    async def _promote_to_l1_if_needed(self, key: str, entry: CacheEntry):
        """根据需要提升到L1缓存"""
        # 如果访问频率高，保持在L1缓存
        if entry.access_count > 5:
            await self.l1_cache.set(key, entry.value, self.config.l1_ttl)

    async def close(self):
        """关闭缓存管理器"""
        if self.l2_cache:
            await self.l2_cache.close()


# 全局缓存管理器实例
_cache_manager: Optional[MultiLevelCacheManager] = None


async def get_cache_manager() -> MultiLevelCacheManager:
    """获取全局缓存管理器实例"""
    global _cache_manager

    if _cache_manager is None:
        from backend.config.settings import get_settings
        settings = get_settings()

        config = CacheConfig(
            l1_max_size=getattr(settings, 'CACHE_L1_MAX_SIZE', 1000),
            l1_ttl=getattr(settings, 'CACHE_L1_TTL', 300),
            l2_host=getattr(settings, 'REDIS_HOST', 'localhost'),
            l2_port=getattr(settings, 'REDIS_PORT', 6379),
            l2_db=getattr(settings, 'REDIS_DB', 0),
            l2_ttl=getattr(settings, 'CACHE_L2_TTL', 3600),
            l2_password=getattr(settings, 'REDIS_PASSWORD', None),
            compression_enabled=getattr(settings, 'CACHE_COMPRESSION_ENABLED', True),
            serialization_method=getattr(settings, 'CACHE_SERIALIZATION_METHOD', 'json')
        )

        _cache_manager = MultiLevelCacheManager(config)
        await _cache_manager.initialize()

    return _cache_manager


def cache_key(*parts: str) -> str:
    """生成缓存键"""
    return ":".join(str(part) for part in parts)