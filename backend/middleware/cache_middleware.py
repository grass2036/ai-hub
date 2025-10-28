"""
API缓存中间件 - FastAPI请求和响应缓存
支持基于路径、参数、用户的多维度缓存策略
"""

import asyncio
import json
import hashlib
import time
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from functools import wraps
from dataclasses import dataclass
from enum import Enum

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from backend.core.cache.multi_level_cache import get_cache_manager, CacheLevel

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """缓存策略"""
    NONE = "none"                    # 不缓存
    MEMORY_ONLY = "memory_only"      # 仅内存缓存
    REDIS_ONLY = "redis_only"        # 仅Redis缓存
    MULTI_LEVEL = "multi_level"      # 多级缓存
    AGGRESSIVE = "aggressive"        # 激进缓存策略


class CacheKeyStrategy(Enum):
    """缓存键生成策略"""
    PATH_ONLY = "path_only"          # 仅路径
    PATH_PARAMS = "path_params"      # 路径+查询参数
    PATH_HEADERS = "path_headers"    # 路径+请求头
    PATH_USER = "path_user"          # 路径+用户信息
    FULL = "full"                    # 路径+参数+头+用户


@dataclass
class CacheRule:
    """缓存规则"""
    path_pattern: str                    # 路径模式 (支持通配符)
    methods: List[str]                   # HTTP方法
    cache_ttl: int = 300                # 缓存时间(秒)
    strategy: CacheStrategy = CacheStrategy.MULTI_LEVEL
    key_strategy: CacheKeyStrategy = CacheKeyStrategy.PATH_PARAMS
    max_response_size: int = 1024 * 1024  # 最大响应大小(1MB)
    vary_headers: List[str] = None        # 根据这些头变化缓存
    exclude_headers: List[str] = None     # 排除这些头
    include_headers: List[str] = None      # 包含这些头
    user_specific: bool = False            # 用户特定缓存
    status_codes: List[int] = None        # 缓存的响应状态码
    tags: List[str] = None                # 缓存标签

    def __post_init__(self):
        if self.vary_headers is None:
            self.vary_headers = ["Authorization", "Accept-Language"]
        if self.exclude_headers is None:
            self.exclude_headers = ["set-cookie", "authorization"]
        if self.include_headers is None:
            self.include_headers = ["content-type", "cache-control"]
        if self.status_codes is None:
            self.status_codes = [200, 201, 204, 301, 302]
        if self.tags is None:
            self.tags = []


class APICacheMiddleware(BaseHTTPMiddleware):
    """API缓存中间件"""

    def __init__(self, app, rules: List[CacheRule] = None):
        super().__init__(app)
        self.rules = rules or self._default_rules()
        self.cache_manager = None
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_sets": 0,
            "cache_errors": 0,
            "bytes_saved": 0
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """中间件主逻辑"""
        start_time = time.time()
        self.stats["total_requests"] += 1

        try:
            # 初始化缓存管理器
            if self.cache_manager is None:
                self.cache_manager = await get_cache_manager()

            # 查找匹配的缓存规则
            rule = self._find_matching_rule(request)

            if not rule or rule.strategy == CacheStrategy.NONE:
                # 不缓存，直接处理请求
                response = await call_next(request)
                return response

            # 生成缓存键
            cache_key = self._generate_cache_key(request, rule)

            # 尝试从缓存获取响应
            cached_response = await self._get_cached_response(cache_key, rule)
            if cached_response:
                self.stats["cache_hits"] += 1
                processing_time = time.time() - start_time
                cached_response.headers["X-Cache"] = "HIT"
                cached_response.headers["X-Cache-Time"] = f"{processing_time:.3f}s"
                logger.debug(f"Cache HIT for {request.method} {request.url.path}")
                return cached_response

            self.stats["cache_misses"] += 1
            logger.debug(f"Cache MISS for {request.method} {request.url.path}")

            # 执行原始请求
            response = await call_next(request)

            # 检查是否应该缓存响应
            if self._should_cache_response(response, rule):
                await self._cache_response(cache_key, response, rule)
                self.stats["cache_sets"] += 1

            processing_time = time.time() - start_time
            response.headers["X-Cache"] = "MISS"
            response.headers["X-Cache-Time"] = f"{processing_time:.3f}s"

            return response

        except Exception as e:
            self.stats["cache_errors"] += 1
            logger.error(f"Cache middleware error: {e}")
            # 出错时继续处理请求
            response = await call_next(request)
            response.headers["X-Cache"] = "ERROR"
            return response

    def _default_rules(self) -> List[CacheRule]:
        """默认缓存规则"""
        return [
            # 静态资源和配置
            CacheRule(
                path_pattern="/api/v1/models",
                methods=["GET"],
                cache_ttl=1800,  # 30分钟
                strategy=CacheStrategy.MULTI_LEVEL
            ),

            # 统计信息
            CacheRule(
                path_pattern="/api/v1/stats/*",
                methods=["GET"],
                cache_ttl=300,   # 5分钟
                strategy=CacheStrategy.MULTI_LEVEL
            ),

            # 会话列表（只读操作）
            CacheRule(
                path_pattern="/api/v1/sessions",
                methods=["GET"],
                cache_ttl=120,   # 2分钟
                strategy=CacheStrategy.MULTI_LEVEL,
                user_specific=True
            ),

            # 健康检查
            CacheRule(
                path_pattern="/api/v1/health",
                methods=["GET"],
                cache_ttl=60,    # 1分钟
                strategy=CacheStrategy.MEMORY_ONLY
            ),

            # 系统配置
            CacheRule(
                path_pattern="/api/v1/config/*",
                methods=["GET"],
                cache_ttl=3600,  # 1小时
                strategy=CacheStrategy.MULTI_LEVEL
            ),

            # 监控数据
            CacheRule(
                path_pattern="/api/v1/monitoring/*",
                methods=["GET"],
                cache_ttl=300,   # 5分钟
                strategy=CacheStrategy.MULTI_LEVEL
            ),

            # 缓存统计
            CacheRule(
                path_pattern="/api/v1/cache/*",
                methods=["GET"],
                cache_ttl=60,    # 1分钟
                strategy=CacheStrategy.MEMORY_ONLY
            ),

            # 企业信息（读取）
            CacheRule(
                path_pattern="/api/v1/organizations/*",
                methods=["GET"],
                cache_ttl=900,   # 15分钟
                strategy=CacheStrategy.MULTI_LEVEL,
                user_specific=True
            ),

            # API密钥验证
            CacheRule(
                path_pattern="/api/v1/verify-key",
                methods=["POST"],
                cache_ttl=300,   # 5分钟
                strategy=CacheStrategy.REDIS_ONLY,
                key_strategy=CacheKeyStrategy.PATH_USER
            )
        ]

    def _find_matching_rule(self, request: Request) -> Optional[CacheRule]:
        """查找匹配的缓存规则"""
        path = request.url.path
        method = request.method

        for rule in self.rules:
            if method not in rule.methods:
                continue

            # 简单的模式匹配
            if self._pattern_matches(rule.path_pattern, path):
                return rule

        return None

    def _pattern_matches(self, pattern: str, path: str) -> bool:
        """检查路径是否匹配模式"""
        if pattern == path:
            return True

        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return path.startswith(prefix)

        # 支持更复杂的模式（如 /api/v1/sessions/{id}）
        pattern_parts = pattern.split("/")
        path_parts = path.split("/")

        if len(pattern_parts) != len(path_parts):
            return False

        for p_part, path_part in zip(pattern_parts, path_parts):
            if p_part.startswith("{") and p_part.endswith("}"):
                continue  # 参数部分匹配
            if p_part != path_part:
                return False

        return True

    def _generate_cache_key(self, request: Request, rule: CacheRule) -> str:
        """生成缓存键"""
        components = ["api_cache", request.method.lower(), request.url.path]

        # 根据键生成策略添加组件
        if rule.key_strategy in [CacheKeyStrategy.PATH_PARAMS, CacheKeyStrategy.FULL]:
            if request.query_params:
                query_string = str(sorted(request.query_params.items()))
                components.append(f"query:{hashlib.md5(query_string.encode()).hexdigest()[:8]}")

        if rule.key_strategy in [CacheKeyStrategy.PATH_HEADERS, CacheKeyStrategy.FULL]:
            # 添加重要的请求头
            header_values = []
            for header in rule.vary_headers:
                value = request.headers.get(header.lower())
                if value:
                    header_values.append(f"{header}:{value}")
            if header_values:
                header_string = "|".join(header_values)
                components.append(f"headers:{hashlib.md5(header_string.encode()).hexdigest()[:8]}")

        if rule.key_strategy in [CacheKeyStrategy.PATH_USER, CacheKeyStrategy.FULL] or rule.user_specific:
            # 添加用户信息
            user_id = request.headers.get("x-user-id")
            auth_header = request.headers.get("authorization")

            if user_id:
                components.append(f"user:{user_id}")
            elif auth_header:
                # 使用token的前8位作为用户标识
                token_hash = hashlib.md5(auth_header.encode()).hexdigest()[:8]
                components.append(f"token:{token_hash}")

        # 添加标签
        if rule.tags:
            components.append("tags:" + ",".join(sorted(rule.tags)))

        cache_key = ":".join(components)
        logger.debug(f"Generated cache key: {cache_key}")
        return cache_key

    async def _get_cached_response(self, cache_key: str, rule: CacheRule) -> Optional[Response]:
        """从缓存获取响应"""
        try:
            levels = self._get_cache_levels(rule.strategy)
            cached_data = await self.cache_manager.get(cache_key, levels)

            if not cached_data:
                return None

            # 从缓存数据重建响应
            response_data = cached_data.get("response")
            if not response_data:
                return None

            # 创建响应
            status_code = response_data.get("status_code", 200)
            headers = response_data.get("headers", {})
            body = response_data.get("body", "")

            # 确保不缓存敏感头
            headers = {k: v for k, v in headers.items()
                      if k.lower() not in ["set-cookie", "authorization"]}

            response = Response(
                content=body.encode() if isinstance(body, str) else body,
                status_code=status_code,
                headers=headers
            )

            # 添加缓存信息头
            response.headers["X-Cache-Age"] = str(int(time.time() - cached_data.get("cached_at", 0)))
            response.headers["X-Cache-TTL"] = str(rule.cache_ttl)

            return response

        except Exception as e:
            logger.error(f"Error getting cached response: {e}")
            return None

    def _should_cache_response(self, response: Response, rule: CacheRule) -> bool:
        """检查是否应该缓存响应"""
        # 检查状态码
        if response.status_code not in rule.status_codes:
            return False

        # 检查响应大小
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > rule.max_response_size:
            return False

        # 检查响应头
        cache_control = response.headers.get("cache-control", "")
        if "no-store" in cache_control or "private" in cache_control:
            return False

        # 检查内容类型
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith(("application/json", "text/html", "text/plain")):
            return False

        return True

    async def _cache_response(self, cache_key: str, response: Response, rule: CacheRule):
        """缓存响应"""
        try:
            # 读取响应体
            if hasattr(response, 'body'):
                body = response.body
            else:
                # 对于StreamingResponse，不进行缓存
                if isinstance(response, StreamingResponse):
                    return
                body = b""

            # 准备缓存数据
            cache_data = {
                "response": {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": body.decode('utf-8', errors='ignore') if body else ""
                },
                "cached_at": time.time(),
                "rule": {
                    "path_pattern": rule.path_pattern,
                    "strategy": rule.strategy.value
                }
            }

            # 设置缓存
            levels = self._get_cache_levels(rule.strategy)
            await self.cache_manager.set(cache_key, cache_data, rule.cache_ttl, levels)

            # 计算节省的字节数
            self.stats["bytes_saved"] += len(body)

        except Exception as e:
            logger.error(f"Error caching response: {e}")

    def _get_cache_levels(self, strategy: CacheStrategy) -> List[CacheLevel]:
        """根据策略获取缓存级别"""
        if strategy == CacheStrategy.MEMORY_ONLY:
            return [CacheLevel.L1_MEMORY]
        elif strategy == CacheStrategy.REDIS_ONLY:
            return [CacheLevel.L2_REDIS]
        elif strategy == CacheStrategy.AGGRESSIVE:
            return [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_PERSISTENT]
        else:  # MULTI_LEVEL
            return [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS]

    async def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        hit_rate = self.stats["cache_hits"] / max(1, self.stats["total_requests"])

        cache_system_stats = {}
        if self.cache_manager:
            cache_system_stats = await self.cache_manager.get_comprehensive_stats()

        return {
            "middleware_stats": {
                "total_requests": self.stats["total_requests"],
                "cache_hits": self.stats["cache_hits"],
                "cache_misses": self.stats["cache_misses"],
                "cache_sets": self.stats["cache_sets"],
                "cache_errors": self.stats["cache_errors"],
                "hit_rate": hit_rate,
                "bytes_saved": self.stats["bytes_saved"]
            },
            "cache_system_stats": cache_system_stats,
            "rules_count": len(self.rules)
        }

    def add_rule(self, rule: CacheRule):
        """添加缓存规则"""
        self.rules.append(rule)
        logger.info(f"Added cache rule: {rule.path_pattern} ({rule.strategy.value})")

    def remove_rule(self, path_pattern: str):
        """移除缓存规则"""
        self.rules = [rule for rule in self.rules if rule.path_pattern != path_pattern]
        logger.info(f"Removed cache rule: {path_pattern}")


def cached_response(
    ttl: int = 300,
    strategy: CacheStrategy = CacheStrategy.MULTI_LEVEL,
    key_strategy: CacheKeyStrategy = CacheKeyStrategy.PATH_PARAMS,
    user_specific: bool = False,
    tags: List[str] = None
):
    """缓存响应装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 这里需要配合中间件使用，或者独立实现装饰器逻辑
            return await func(*args, **kwargs)

        # 添加缓存元数据
        wrapper._cache_config = {
            "ttl": ttl,
            "strategy": strategy,
            "key_strategy": key_strategy,
            "user_specific": user_specific,
            "tags": tags or []
        }

        return wrapper
    return decorator


class CacheInvalidationManager:
    """缓存失效管理器"""

    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.invalidation_patterns = {}

    async def invalidate_by_pattern(self, pattern: str):
        """根据模式失效缓存"""
        try:
            # 这里需要实现模式匹配失效逻辑
            # 可能需要维护一个缓存键的索引
            pass
        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")

    async def invalidate_by_tags(self, tags: List[str]):
        """根据标签失效缓存"""
        try:
            # 实现标签失效逻辑
            pass
        except Exception as e:
            logger.error(f"Error invalidating cache by tags {tags}: {e}")

    async def invalidate_user_cache(self, user_id: str):
        """失效用户特定缓存"""
        try:
            # 失效特定用户的所有缓存
            pattern = f"user:{user_id}"
            await self.invalidate_by_pattern(pattern)
        except Exception as e:
            logger.error(f"Error invalidating user cache for {user_id}: {e}")

    async def invalidate_endpoint_cache(self, path: str, method: str = "GET"):
        """失效特定端点缓存"""
        try:
            pattern = f"api_cache:{method.lower()}:{path}"
            await self.invalidate_by_pattern(pattern)
        except Exception as e:
            logger.error(f"Error invalidating endpoint cache {path}: {e}")


# 全局缓存中间件实例
_cache_middleware: Optional[APICacheMiddleware] = None


def get_cache_middleware() -> APICacheMiddleware:
    """获取全局缓存中间件实例"""
    global _cache_middleware
    if _cache_middleware is None:
        _cache_middleware = APICacheMiddleware(None)  # 会在FastAPI应用中初始化
    return _cache_middleware


def configure_caching(rules: List[CacheRule] = None) -> APICacheMiddleware:
    """配置API缓存"""
    global _cache_middleware
    _cache_middleware = APICacheMiddleware(None, rules)
    return _cache_middleware