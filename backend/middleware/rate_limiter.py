"""
Rate Limiting and Security Middleware
Week 4 Day 26: Performance Optimization and Security Hardening
"""

import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Set, List
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis.asyncio as redis
import hashlib
import ipaddress
from collections import defaultdict, deque

from backend.core.cache import get_rate_limit_cache, RateLimitCache
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""

    def __init__(
        self,
        app: ASGIApp,
        default_limits: Dict[str, Dict[str, int]] = None,
        whitelist_ips: List[str] = None,
        blacklist_ips: List[str] = None
    ):
        super().__init__(app)
        self.settings = get_settings()

        # 默认限流配置
        self.default_limits = default_limits or {
            "default": {"requests": 100, "window": 60},  # 每分钟100次
            "auth": {"requests": 10, "window": 60},       # 认证接口更严格
            "chat": {"requests": 20, "window": 60},       # 聊天接口
            "api": {"requests": 1000, "window": 3600},    # API接口每小时1000次
        }

        # IP白名单和黑名单
        self.whitelist_ips = set(whitelist_ips or [])
        self.blacklist_ips = set(blacklist_ips or [])

        # 内存缓存 (用于Redis不可用时)
        self.memory_cache: Dict[str, deque] = defaultdict(lambda: deque())
        self.cache_cleanup_task: Optional[asyncio.Task] = None

        # 安全配置
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        self.blocked_user_agents: Set[str] = set()
        self.suspicious_ips: Dict[str, Dict] = {}

        # 启动后台任务
        self._start_background_tasks()

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # 检查IP黑名单
        if self._is_ip_blocked(client_ip):
            return self._create_blocked_response("IP地址被阻止", status.HTTP_403_FORBIDDEN)

        # 检查User-Agent黑名单
        if self._is_user_agent_blocked(user_agent):
            return self._create_blocked_response("请求被阻止", status.HTTP_403_FORBIDDEN)

        # 检查请求大小
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            return self._create_blocked_response("请求体过大", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        # 检查可疑行为
        if self._is_suspicious_request(request, client_ip):
            logger.warning(f"Suspicious request detected from IP: {client_ip}")
            await self._handle_suspicious_request(client_ip, request)

        # 应用限流
        rate_limit_result = await self._check_rate_limit(request, client_ip)
        if rate_limit_result["blocked"]:
            return self._create_rate_limit_response(rate_limit_result)

        # 处理请求
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # 添加响应头
        self._add_rate_limit_headers(response, rate_limit_result)
        self._add_security_headers(response)

        # 记录请求日志
        await self._log_request(request, response, process_time, client_ip)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # 取第一个IP (原始客户端IP)
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        # 回退到直接连接的IP
        if hasattr(request, 'client') and request.client:
            return request.client.host

        return "unknown"

    def _is_ip_blocked(self, ip: str) -> bool:
        """检查IP是否被阻止"""
        # 检查白名单
        if self.whitelist_ips and ip in self.whitelist_ips:
            return False

        # 检查黑名单
        if ip in self.blacklist_ips:
            return True

        # 检查可疑IP
        if ip in self.suspicious_ips:
            suspicious_data = self.suspicious_ips[ip]
            if suspicious_data.get("blocked", False):
                return True

        return False

    def _is_user_agent_blocked(self, user_agent: str) -> bool:
        """检查User-Agent是否被阻止"""
        blocked_agents = [
            "bot", "crawler", "spider", "scraper", "curl", "wget",
            "python-requests", "httpie", "postman"
        ]

        user_agent_lower = user_agent.lower()
        return any(agent in user_agent_lower for agent in blocked_agents)

    def _is_suspicious_request(self, request: Request, client_ip: str) -> bool:
        """检测可疑请求"""
        suspicious_indicators = []

        # 检查请求频率
        current_time = time.time()
        if client_ip in self.suspicious_ips:
            last_request_time = self.suspicious_ips[client_ip].get("last_request", 0)
            if current_time - last_request_time < 0.1:  # 100ms内多个请求
                suspicious_indicators.append("high_frequency")

        # 检查异常请求头
        suspicious_headers = ["x-attack", "x-hack", "x-exploit"]
        for header in suspicious_headers:
            if header in request.headers:
                suspicious_indicators.append("malicious_header")
                break

        # 检查SQL注入模式
        query_string = str(request.query_params)
        sql_patterns = ["union", "select", "insert", "update", "delete", "drop", "exec", "script"]
        if any(pattern in query_string.lower() for pattern in sql_patterns):
            suspicious_indicators.append("sql_injection_attempt")

        # 检查XSS模式
        xss_patterns = ["<script", "javascript:", "onerror=", "onload=", "alert("]
        if any(pattern in query_string.lower() for pattern in xss_patterns):
            suspicious_indicators.append("xss_attempt")

        # 检查路径遍历
        path = request.url.path
        if ".." in path or path.count("/") > 20:
            suspicious_indicators.append("path_traversal")

        return len(suspicious_indicators) > 0

    async def _handle_suspicious_request(self, ip: str, request: Request):
        """处理可疑请求"""
        if ip not in self.suspicious_ips:
            self.suspicious_ips[ip] = {
                "first_seen": datetime.utcnow(),
                "suspicious_count": 0,
                "last_request": time.time(),
                "blocked": False
            }

        suspicious_data = self.suspicious_ips[ip]
        suspicious_data["suspicious_count"] += 1
        suspicious_data["last_request"] = time.time()

        # 如果可疑次数过多，阻止IP
        if suspicious_data["suspicious_count"] > 10:
            suspicious_data["blocked"] = True
            logger.warning(f"IP {ip} blocked due to suspicious activity")

            # 可以在这里添加通知逻辑
            # await self._notify_security_team(ip, suspicious_data)

    async def _check_rate_limit(self, request: Request, client_ip: str) -> Dict[str, Any]:
        """检查限流"""
        path = request.url.path
        method = request.method

        # 确定适用的限流规则
        limit_config = self._get_limit_config(path, method)

        try:
            rate_limit_cache = await get_rate_limit_cache()

            # 生成标识符
            identifier = f"{client_ip}:{path}:{method}"

            # 检查限流
            is_limited, limit_info = await rate_limit_cache.is_rate_limited(
                identifier=identifier,
                limit=limit_config["requests"],
                window=limit_config["window"],
                key_prefix="rate_limit"
            )

            return {
                "blocked": is_limited,
                "limit": limit_info["limit"],
                "remaining": limit_info["remaining"],
                "reset": limit_info["reset"],
                "retry_after": limit_info["retry_after"],
                "window": limit_config["window"]
            }

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # 降级到内存限流
            return self._memory_rate_limit_check(identifier, limit_config)

    def _get_limit_config(self, path: str, method: str) -> Dict[str, int]:
        """获取限流配置"""
        # 根据路径确定适用的限流规则
        if "/auth" in path:
            return self.default_limits["auth"]
        elif "/chat" in path:
            return self.default_limits["chat"]
        elif "/api" in path:
            return self.default_limits["api"]
        else:
            return self.default_limits["default"]

    def _memory_rate_limit_check(self, identifier: str, limit_config: Dict[str, int]) -> Dict[str, Any]:
        """内存限流检查 (降级方案)"""
        current_time = time.time()
        window = limit_config["window"]

        # 清理过期记录
        cutoff_time = current_time - window
        requests_queue = self.memory_cache[identifier]

        # 移除过期请求
        while requests_queue and requests_queue[0] < cutoff_time:
            requests_queue.popleft()

        # 检查是否超过限制
        requests_in_window = len(requests_queue)
        remaining = max(0, limit_config["requests"] - requests_in_window)
        reset_time = current_time + window

        if requests_in_window >= limit_config["requests"]:
            retry_after = int(min(requests_queue[0] + window - current_time, window))
            return {
                "blocked": True,
                "limit": limit_config["requests"],
                "remaining": 0,
                "reset": datetime.fromtimestamp(reset_time).isoformat(),
                "retry_after": retry_after,
                "window": window
            }

        # 记录新请求
        requests_queue.append(current_time)

        return {
            "blocked": False,
            "limit": limit_config["requests"],
            "remaining": remaining - 1,
            "reset": datetime.fromtimestamp(reset_time).isoformat(),
            "retry_after": 0,
            "window": window
        }

    def _create_rate_limit_response(self, rate_limit_result: Dict[str, Any]) -> JSONResponse:
        """创建限流响应"""
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "message": "请求过于频繁，请稍后再试",
                "limit": rate_limit_result["limit"],
                "window": rate_limit_result["window"],
                "retry_after": rate_limit_result["retry_after"]
            },
            headers={
                "Retry-After": str(rate_limit_result["retry_after"]),
                "X-RateLimit-Limit": str(rate_limit_result["limit"]),
                "X-RateLimit-Remaining": str(rate_limit_result["remaining"]),
                "X-RateLimit-Reset": rate_limit_result["reset"]
            }
        )

    def _create_blocked_response(self, message: str, status_code: int) -> JSONResponse:
        """创建阻止响应"""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": "Access denied",
                "message": message
            }
        )

    def _add_rate_limit_headers(self, response: Response, rate_limit_result: Dict[str, Any]):
        """添加限流响应头"""
        response.headers["X-RateLimit-Limit"] = str(rate_limit_result["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_result["remaining"])
        response.headers["X-RateLimit-Reset"] = rate_limit_result["reset"]

    def _add_security_headers(self, response: Response):
        """添加安全响应头"""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }

        for header, value in security_headers.items():
            response.headers[header] = value

    async def _log_request(self, request: Request, response: Response, process_time: float, client_ip: str):
        """记录请求日志"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params),
            "status_code": response.status_code,
            "process_time": round(process_time, 4),
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent", ""),
            "content_length": request.headers.get("content-length", "0")
        }

        # 根据状态码选择日志级别
        if response.status_code >= 500:
            logger.error(f"Server Error: {log_data}")
        elif response.status_code >= 400:
            logger.warning(f"Client Error: {log_data}")
        elif process_time > 2.0:  # 超过2秒的慢请求
            logger.warning(f"Slow Request: {log_data}")
        else:
            logger.info(f"Request: {log_data}")

    def _start_background_tasks(self):
        """启动后台任务"""
        # 定期清理内存缓存
        if not self.cache_cleanup_task or self.cache_cleanup_task.done():
            self.cache_cleanup_task = asyncio.create_task(self._cleanup_memory_cache())

    async def _cleanup_memory_cache(self):
        """清理内存缓存"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                current_time = time.time()
                cutoff_time = current_time - 3600  # 1小时前

                # 清理过期的请求记录
                keys_to_remove = []
                for key, requests_queue in self.memory_cache.items():
                    while requests_queue and requests_queue[0] < cutoff_time:
                        requests_queue.popleft()

                    # 如果队列为空，标记删除
                    if not requests_queue:
                        keys_to_remove.append(key)

                for key in keys_to_remove:
                    del self.memory_cache[key]

                # 清理可疑IP记录 (超过24小时)
                cutoff_datetime = datetime.utcnow() - timedelta(hours=24)
                ips_to_remove = []

                for ip, data in self.suspicious_ips.items():
                    if data["first_seen"] < cutoff_datetime and data["suspicious_count"] < 5:
                        ips_to_remove.append(ip)

                for ip in ips_to_remove:
                    del self.suspicious_ips[ip]

                logger.debug(f"Memory cache cleanup completed. Removed {len(keys_to_remove)} cache entries and {len(ips_to_remove)} suspicious IPs.")

            except Exception as e:
                logger.error(f"Memory cache cleanup error: {e}")


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next):
        """安全检查"""
        # 检查请求方法
        if request.method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]:
            return JSONResponse(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                content={"error": "Method not allowed"}
            )

        # 检查Content-Type (对于POST/PUT请求)
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if not content_type.startswith(("application/json", "application/x-www-form-urlencoded", "multipart/form-data")):
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={"error": "Unsupported media type"}
                )

        # 处理请求
        response = await call_next(request)

        return response