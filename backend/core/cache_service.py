"""
缓存服务
"""

import json
import time
import hashlib
from typing import Any, Optional, Dict, Union
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class CacheItem:
    """缓存项"""
    value: Any
    expires_at: Optional[float] = None
    created_at: float = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def get_age(self) -> float:
        """获取缓存年龄（秒）"""
        return time.time() - self.created_at


class CacheService:
    """内存缓存服务"""

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: Dict[str, CacheItem] = {}
        self._access_times: Dict[str, float] = {}
        self._hits = 0
        self._misses = 0

    def _make_key(self, key: str, *args, **kwargs) -> str:
        """生成缓存键"""
        if args or kwargs:
            # 将参数序列化为字符串
            params = str(args) + str(sorted(kwargs.items()))
            return f"{key}:{hashlib.md5(params.encode()).hexdigest()}"
        return key

    def _evict_if_needed(self):
        """如果需要，驱逐最旧的缓存项"""
        if len(self._cache) < self.max_size:
            return

        # 找到最久未访问的项
        oldest_key = min(self._access_times.keys(),
                        key=lambda k: self._access_times[k])

        del self._cache[oldest_key]
        del self._access_times[oldest_key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None,
            *args, **kwargs) -> str:
        """设置缓存"""
        cache_key = self._make_key(key, *args, **kwargs)

        # 计算过期时间
        expires_at = None
        if ttl is not None:
            expires_at = time.time() + ttl
        elif self.default_ttl > 0:
            expires_at = time.time() + self.default_ttl

        # 驱逐旧缓存
        self._evict_if_needed()

        # 设置新缓存
        self._cache[cache_key] = CacheItem(
            value=value,
            expires_at=expires_at
        )
        self._access_times[cache_key] = time.time()

        return cache_key

    def get(self, key: str, *args, **kwargs) -> Optional[Any]:
        """获取缓存"""
        cache_key = self._make_key(key, *args, **kwargs)

        if cache_key not in self._cache:
            self._misses += 1
            return None

        item = self._cache[cache_key]

        # 检查是否过期
        if item.is_expired():
            del self._cache[cache_key]
            del self._access_times[cache_key]
            self._misses += 1
            return None

        # 更新访问时间
        self._access_times[cache_key] = time.time()
        self._hits += 1

        return item.value

    def delete(self, key: str, *args, **kwargs):
        """删除缓存"""
        cache_key = self._make_key(key, *args, **kwargs)

        if cache_key in self._cache:
            del self._cache[cache_key]
            del self._access_times[cache_key]

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._access_times.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests) if total_requests > 0 else 0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "total_items": len(self._cache),
            "max_size": self.max_size,
            "memory_usage": self._estimate_memory_usage()
        }

    def _estimate_memory_usage(self) -> str:
        """估算内存使用量"""
        total_size = 0
        for key, item in self._cache.items():
            total_size += len(key.encode())
            total_size += len(str(item.value).encode())

        # 转换为人类可读格式
        if total_size < 1024:
            return f"{total_size}B"
        elif total_size < 1024 * 1024:
            return f"{total_size / 1024:.1f}KB"
        else:
            return f"{total_size / (1024 * 1024):.1f}MB"

    def cleanup_expired(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []

        for key, item in self._cache.items():
            if item.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]
            del self._access_times[key]

        return len(expired_keys)


# 全局缓存实例
cache_service = CacheService(default_ttl=300, max_size=500)


def cache_result(ttl: int = 300, key_prefix: str = ""):
    """缓存装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}"

            # 尝试从缓存获取
            cached_result = cache_service.get(cache_key, *args, **kwargs)
            if cached_result is not None:
                return cached_result

            # 执行函数
            result = await func(*args, **kwargs)

            # 存入缓存
            cache_service.set(cache_key, result, ttl, *args, **kwargs)

            return result

        return wrapper
    return decorator


def cache_stats():
    """获取缓存统计信息"""
    return cache_service.get_stats()


def clear_cache():
    """清空缓存"""
    cache_service.clear()


def cleanup_expired_cache():
    """清理过期缓存"""
    return cache_service.cleanup_expired()