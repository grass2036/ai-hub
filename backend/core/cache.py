"""
API Response Cache System
Week 4 Day 26: Performance Optimization and Security Hardening
"""

import json
import hashlib
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Union, Callable
from functools import wraps
import redis.asyncio as redis
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class CacheManager:
    """高级缓存管理器"""

    def __init__(self):
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
        self.local_cache: Dict[str, Any] = {}
        self.local_cache_timestamps: Dict[str, datetime] = {}
        self.max_local_cache_size = 1000

    async def initialize(self):
        """初始化缓存系统"""
        if self.redis_client:
            return

        try:
            self.redis_client = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # 测试连接
            await self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis not available, using local cache only: {e}")
            self.redis_client = None

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """生成缓存键"""
        # 创建一个确定性的字符串用于哈希
        key_data = {
            "prefix": prefix,
            **{k: v for k, v in sorted(kwargs.items()) if v is not None}
        }
        key_string = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        key_hash = hashlib.sha256(key_string.encode('utf-8')).hexdigest()[:16]
        return f"{prefix}:{key_hash}"

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            # 首先尝试本地缓存
            if key in self.local_cache:
                timestamp = self.local_cache_timestamps.get(key)
                if timestamp and timestamp > datetime.utcnow() - timedelta(minutes=5):
                    return self.local_cache[key]
                else:
                    # 本地缓存过期，删除
                    del self.local_cache[key]
                    if key in self.local_cache_timestamps:
                        del self.local_cache_timestamps[key]

            # 尝试Redis缓存
            if self.redis_client:
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    try:
                        data = json.loads(cached_data)
                        # 同时更新本地缓存
                        await self._set_local_cache(key, data)
                        return data
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode cached data for key: {key}")
                        await self.redis_client.delete(key)

            return None

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None,
        tags: Optional[list] = None
    ) -> bool:
        """设置缓存值"""
        try:
            # 设置本地缓存
            await self._set_local_cache(key, value)

            # 设置Redis缓存
            if self.redis_client:
                try:
                    serialized_data = json.dumps(value, ensure_ascii=False)

                    # 使用pipeline提高性能
                    pipe = self.redis_client.pipeline()
                    pipe.set(key, serialized_data, ex=expire or 300)  # 默认5分钟过期

                    # 添加标签
                    if tags:
                        for tag in tags:
                            tag_key = f"tag:{tag}"
                            pipe.sadd(tag_key, key)
                            pipe.expire(tag_key, expire or 300)

                    await pipe.execute()
                    return True

                except Exception as e:
                    logger.error(f"Redis cache set error for key {key}: {e}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def _set_local_cache(self, key: str, value: Any):
        """设置本地缓存"""
        # 如果缓存已满，删除最旧的条目
        if len(self.local_cache) >= self.max_local_cache_size:
            oldest_key = min(
                self.local_cache_timestamps.keys(),
                key=lambda k: self.local_cache_timestamps[k]
            )
            del self.local_cache[oldest_key]
            del self.local_cache_timestamps[oldest_key]

        self.local_cache[key] = value
        self.local_cache_timestamps[key] = datetime.utcnow()

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            # 删除本地缓存
            if key in self.local_cache:
                del self.local_cache[key]
            if key in self.local_cache_timestamps:
                del self.local_cache_timestamps[key]

            # 删除Redis缓存
            if self.redis_client:
                await self.redis_client.delete(key)

            return True

        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def delete_by_tag(self, tag: str) -> int:
        """通过标签删除缓存"""
        try:
            deleted_count = 0

            # 删除本地缓存中匹配的条目
            keys_to_delete = []
            for key in self.local_cache.keys():
                if tag in key:
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self.local_cache[key]
                if key in self.local_cache_timestamps:
                    del self.local_cache_timestamps[key]
                deleted_count += 1

            # 删除Redis缓存中匹配的条目
            if self.redis_client:
                tag_key = f"tag:{tag}"
                keys = await self.redis_client.smembers(tag_key)
                if keys:
                    pipe = self.redis_client.pipeline()
                    for key in keys:
                        pipe.delete(key)
                    await pipe.execute()
                    deleted_count += len(keys)
                    await self.redis_client.delete(tag_key)

            return deleted_count

        except Exception as e:
            logger.error(f"Cache delete by tag error for tag {tag}: {e}")
            return 0

    async def clear_all(self) -> bool:
        """清空所有缓存"""
        try:
            # 清空本地缓存
            self.local_cache.clear()
            self.local_cache_timestamps.clear()

            # 清空Redis缓存
            if self.redis_client:
                await self.redis_client.flushdb()

            return True

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            stats = {
                "local_cache_size": len(self.local_cache),
                "redis_available": self.redis_client is not None
            }

            if self.redis_client:
                redis_info = await self.redis_client.info()
                stats.update({
                    "redis_memory_usage": redis_info.get("used_memory_human"),
                    "redis_connected_clients": redis_info.get("connected_clients"),
                    "redis_total_commands_processed": redis_info.get("total_commands_processed")
                })

            return stats

        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"error": str(e)}


# 全局缓存管理器实例
cache_manager = CacheManager()


async def get_cache_manager() -> CacheManager:
    """获取缓存管理器实例"""
    await cache_manager.initialize()
    return cache_manager


def cached_response(
    expire: int = 300,
    key_prefix: str = "api_response",
    vary_on: Optional[list] = None,
    tags: Optional[list] = None
):
    """缓存响应装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None

            # 从参数中提取request对象
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            # 如果没有request对象，直接执行函数
            if not request:
                return await func(*args, **kwargs)

            # 生成缓存键
            cache_key_data = {
                "method": request.method,
                "url": str(request.url),
                "query_params": dict(request.query_params),
            }

            # 添加vary_on参数
            if vary_on:
                for param in vary_on:
                    if param in kwargs:
                        cache_key_data[param] = kwargs[param]
                    elif hasattr(request, param):
                        cache_key_data[param] = getattr(request, param)

            cache_key = cache_manager._generate_cache_key(key_prefix, **cache_key_data)

            # 尝试获取缓存
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for key: {cache_key}")
                return JSONResponse(
                    content=cached_result["content"],
                    status_code=cached_result.get("status_code", 200),
                    headers=cached_result.get("headers", {})
                )

            # 执行原函数
            result = await func(*args, **kwargs)

            # 缓存结果
            if isinstance(result, JSONResponse):
                cache_data = {
                    "content": json.loads(result.body.decode('utf-8')),
                    "status_code": result.status_code,
                    "headers": dict(result.headers)
                }
            else:
                cache_data = {
                    "content": result,
                    "status_code": 200,
                    "headers": {}
                }

            await cache_manager.set(cache_key, cache_data, expire=expire, tags=tags)
            logger.debug(f"Cache set for key: {cache_key}")

            return result

        return wrapper
    return decorator


class RateLimitCache:
    """限流缓存"""

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager

    async def is_rate_limited(
        self,
        identifier: str,
        limit: int,
        window: int,
        key_prefix: str = "rate_limit"
    ) -> tuple[bool, Dict[str, Any]]:
        """检查是否超过限流"""
        current_time = datetime.utcnow()
        window_start = current_time - timedelta(seconds=window)

        key = f"{key_prefix}:{identifier}"

        # 获取当前窗口内的请求记录
        requests_data = await self.cache_manager.get(key) or {"requests": [], "count": 0}

        # 清理过期的请求记录
        requests_data["requests"] = [
            req_time for req_time in requests_data["requests"]
            if datetime.fromisoformat(req_time) > window_start
        ]

        # 检查是否超过限制
        if len(requests_data["requests"]) >= limit:
            # 计算重置时间
            oldest_request = min(requests_data["requests"])
            reset_time = datetime.fromisoformat(oldest_request) + timedelta(seconds=window)

            return True, {
                "limit": limit,
                "remaining": 0,
                "reset": reset_time.isoformat(),
                "retry_after": int((reset_time - current_time).total_seconds())
            }

        # 记录新请求
        requests_data["requests"].append(current_time.isoformat())
        requests_data["count"] = len(requests_data["requests"])

        # 更新缓存
        await self.cache_manager.set(key, requests_data, expire=window)

        return False, {
            "limit": limit,
            "remaining": limit - len(requests_data["requests"]),
            "reset": (current_time + timedelta(seconds=window)).isoformat(),
            "retry_after": 0
        }


async def get_rate_limit_cache() -> RateLimitCache:
    """获取限流缓存实例"""
    cache_mgr = await get_cache_manager()
    return RateLimitCache(cache_mgr)