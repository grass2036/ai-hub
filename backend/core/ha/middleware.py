"""
高可用中间件
Week 6 Day 5: 负载均衡和高可用配置

提供FastAPI中间件集成，自动处理负载均衡、健康检查和故障转移
"""

import asyncio
import time
import uuid
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .load_balancer import LoadBalancer, LoadBalancingConfig, BackendServer
from .health_check import HealthChecker, HealthCheckConfig, CheckType
from .failover import FailoverManager, FailoverConfig, FailoverStrategy
from .cluster_management import ClusterManager, ClusterConfig
from .setup import HAConfig, HASetup


class HAMiddleware(BaseHTTPMiddleware):
    """高可用中间件"""

    def __init__(
        self,
        app: ASGIApp,
        ha_config: HAConfig,
        load_balancer_config: LoadBalancingConfig = None,
        health_check_config: HealthCheckConfig = None,
        failover_config: FailoverConfig = None,
        cluster_config: ClusterConfig = None
    ):
        super().__init__(app)
        self.ha_config = ha_config
        self.load_balancer_config = load_balancer_config
        self.health_check_config = health_check_config
        self.failover_config = failover_config
        self.cluster_config = cluster_config

        self.ha_setup: Optional[HASetup] = None
        self._initialized = False

    async def initialize(self):
        """初始化高可用组件"""
        if self._initialized:
            return

        self.ha_setup = HASetup(self.ha_config)
        await self.ha_setup.initialize()
        self._initialized = True

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理HTTP请求"""
        if not self._initialized:
            await self.initialize()

        start_time = time.time()
        request_id = str(uuid.uuid4())

        # 添加请求上下文
        request_context = {
            "request_id": request_id,
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "method": request.method,
            "url": str(request.url),
            "timestamp": datetime.now()
        }

        try:
            # 检查系统健康状态
            if not await self._check_system_health():
                return self._create_service_unavailable_response(
                    "System is undergoing maintenance"
                )

            # 执行请求
            response = await call_next(request)

            # 记录请求统计
            await self._record_request_stats(request_context, response, time.time() - start_time)

            # 添加HA相关头信息
            response.headers["X-Request-ID"] = request_id
            response.headers["X-HA-Node"] = self.ha_setup.cluster_manager.config.node_id
            response.headers["X-HA-Timestamp"] = datetime.now().isoformat()

            return response

        except Exception as e:
            # 记录错误统计
            await self._record_error_stats(request_context, str(e), time.time() - start_time)

            # 尝试故障转移
            if await self._should_attempt_failover(e):
                return await self._attempt_failover(request, call_next, request_context)

            # 返回错误响应
            return self._create_error_response(e)

    async def _check_system_health(self) -> bool:
        """检查系统健康状态"""
        if not self.ha_setup:
            return True

        try:
            # 检查集群状态
            cluster_status = await self.ha_setup.cluster_manager.get_cluster_status()
            if not cluster_status.get("is_healthy", True):
                return False

            # 检查负载均衡器状态
            if self.ha_setup.load_balancer:
                stats = self.ha_setup.load_balancer.get_statistics()
                if stats.get("healthy_backends", 0) == 0:
                    return False

            return True

        except Exception:
            # 如果健康检查失败，假设系统不健康
            return False

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # 回退到直接连接IP
        return request.client.host if request.client else "127.0.0.1"

    async def _record_request_stats(
        self,
        request_context: Dict[str, Any],
        response: Response,
        response_time: float
    ):
        """记录请求统计信息"""
        try:
            if self.ha_setup and self.ha_setup.redis_client:
                stats_key = f"ha:stats:requests:{datetime.now().strftime('%Y%m%d')}"

                stats_data = {
                    "request_id": request_context["request_id"],
                    "method": request_context["method"],
                    "url": request_context["url"],
                    "client_ip": request_context["client_ip"],
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "timestamp": request_context["timestamp"].isoformat(),
                    "node": self.ha_setup.cluster_manager.config.node_id
                }

                # 使用Redis列表存储统计信息
                await self.ha_setup.redis_client.lpush(stats_key, json.dumps(stats_data))

                # 设置过期时间（7天）
                await self.ha_setup.redis_client.expire(stats_key, 7 * 24 * 3600)

        except Exception as e:
            # 记录统计失败不应该影响主要功能
            print(f"Failed to record request stats: {e}")

    async def _record_error_stats(
        self,
        request_context: Dict[str, Any],
        error: str,
        response_time: float
    ):
        """记录错误统计信息"""
        try:
            if self.ha_setup and self.ha_setup.redis_client:
                error_key = f"ha:stats:errors:{datetime.now().strftime('%Y%m%d')}"

                error_data = {
                    "request_id": request_context["request_id"],
                    "method": request_context["method"],
                    "url": request_context["url"],
                    "client_ip": request_context["client_ip"],
                    "error": error,
                    "response_time": response_time,
                    "timestamp": request_context["timestamp"].isoformat(),
                    "node": self.ha_setup.cluster_manager.config.node_id
                }

                await self.ha_setup.redis_client.lpush(error_key, json.dumps(error_data))
                await self.ha_setup.redis_client.expire(error_key, 7 * 24 * 3600)

        except Exception as e:
            print(f"Failed to record error stats: {e}")

    async def _should_attempt_failover(self, error: Exception) -> bool:
        """判断是否应该尝试故障转移"""
        if not self.ha_setup or not self.ha_setup.failover_manager:
            return False

        # 检查错误类型
        if isinstance(error, (ConnectionError, TimeoutError)):
            return True

        # 检查HTTP状态码
        if isinstance(error, HTTPException):
            if error.status_code >= 500:
                return True

        # 检查系统负载
        if await self._is_system_overloaded():
            return True

        return False

    async def _is_system_overloaded(self) -> bool:
        """检查系统是否过载"""
        try:
            if not self.ha_setup.load_balancer:
                return False

            stats = self.ha_setup.load_balancer.get_statistics()

            # 检查连接数
            total_connections = stats.get("total_connections", 0)
            if total_connections > 1000:  # 可配置的阈值
                return True

            # 检查失败率
            success_rate = stats.get("success_rate", 1.0)
            if success_rate < 0.8:  # 失败率超过20%
                return True

            return False

        except Exception:
            return False

    async def _attempt_failover(
        self,
        request: Request,
        call_next: Callable,
        request_context: Dict[str, Any]
    ) -> Response:
        """尝试故障转移"""
        try:
            if not self.ha_setup.failover_manager:
                return self._create_service_unavailable_response("Failover not available")

            # 触发故障转移检查
            await self.ha_setup.failover_manager.check_failover_conditions()

            # 重试请求
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    # 等待一小段时间让故障转移生效
                    await asyncio.sleep(0.1 * (attempt + 1))

                    response = await call_next(request)

                    # 记录成功恢复
                    await self._record_recovery_stats(request_context, attempt + 1)

                    return response

                except Exception as e:
                    if attempt == max_retries - 1:
                        # 最后一次尝试失败
                        return self._create_service_unavailable_response(
                            f"Failover failed after {max_retries} attempts"
                        )

        except Exception:
            return self._create_service_unavailable_response("Failover error")

    async def _record_recovery_stats(self, request_context: Dict[str, Any], attempt: int):
        """记录恢复统计信息"""
        try:
            if self.ha_setup and self.ha_setup.redis_client:
                recovery_key = f"ha:stats:recovery:{datetime.now().strftime('%Y%m%d')}"

                recovery_data = {
                    "request_id": request_context["request_id"],
                    "method": request_context["method"],
                    "url": request_context["url"],
                    "client_ip": request_context["client_ip"],
                    "attempt": attempt,
                    "timestamp": datetime.now().isoformat(),
                    "node": self.ha_setup.cluster_manager.config.node_id
                }

                await self.ha_setup.redis_client.lpush(recovery_key, json.dumps(recovery_data))
                await self.ha_setup.redis_client.expire(recovery_key, 7 * 24 * 3600)

        except Exception as e:
            print(f"Failed to record recovery stats: {e}")

    def _create_service_unavailable_response(self, message: str) -> JSONResponse:
        """创建服务不可用响应"""
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "Service Unavailable",
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "retry_after": 30
            }
        )

    def _create_error_response(self, error: Exception) -> JSONResponse:
        """创建错误响应"""
        if isinstance(error, HTTPException):
            return JSONResponse(
                status_code=error.status_code,
                content={
                    "error": "Request Failed",
                    "message": str(error),
                    "timestamp": datetime.now().isoformat()
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def shutdown(self):
        """关闭中间件"""
        if self.ha_setup:
            await self.ha_setup.shutdown()


class LoadBalancingMiddleware(BaseHTTPMiddleware):
    """负载均衡中间件"""

    def __init__(
        self,
        app: ASGIApp,
        load_balancer: LoadBalancer,
        backend_selector: Callable[[Request], Dict[str, Any]] = None
    ):
        super().__init__(app)
        self.load_balancer = load_balancer
        self.backend_selector = backend_selector or self._default_backend_selector

    def _default_backend_selector(self, request: Request) -> Dict[str, Any]:
        """默认后端选择器"""
        return {
            "client_ip": request.client.host if request.client else "127.0.0.1",
            "url": str(request.url.path),
            "method": request.method,
            "user_agent": request.headers.get("user-agent", "")
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并应用负载均衡"""
        # 选择后端
        request_context = self.backend_selector(request)
        backend = await self.load_balancer.select_backend(request_context)

        if not backend:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"error": "No available backend servers"}
            )

        # 添加后端信息到请求头
        request.headers.update({
            "X-Backend-ID": backend.id,
            "X-Backend-URL": backend.url
        })

        # 执行请求
        response = await call_next(request)

        # 添加后端信息到响应头
        response.headers["X-Backend-ID"] = backend.id
        response.headers["X-Backend-Response-Time"] = str(backend.response_time)

        return response


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """健康检查中间件"""

    def __init__(
        self,
        app: ASGIApp,
        health_checker: HealthChecker,
        health_path: str = "/health"
    ):
        super().__init__(app)
        self.health_checker = health_checker
        self.health_path = health_path

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理健康检查请求"""
        if request.url.path == self.health_path:
            try:
                # 执行健康检查
                result = await self.health_checker.execute_check()

                status_code = 200 if result.is_healthy else 503

                return JSONResponse(
                    status_code=status_code,
                    content={
                        "status": result.status.value,
                        "message": result.message,
                        "timestamp": result.timestamp.isoformat(),
                        "response_time": result.response_time,
                        "details": result.details
                    }
                )

            except Exception as e:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unhealthy",
                        "message": f"Health check failed: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    }
                )

        # 非健康检查请求，正常处理
        return await call_next(request)


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """熔断器中间件"""

    def __init__(
        self,
        app: ASGIApp,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        super().__init__(app)
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并应用熔断逻辑"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "error": "Circuit Breaker Open",
                        "message": "Service temporarily unavailable",
                        "retry_after": self.recovery_timeout
                    }
                )

        try:
            response = await call_next(request)

            if self.state == "HALF_OPEN":
                self._reset_circuit()

            return response

        except self.expected_exception as e:
            self._record_failure()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.last_failure_time = time.time()

            if isinstance(e, HTTPException):
                raise e
            else:
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "error": "Service Error",
                        "message": "Internal service error",
                        "circuit_state": self.state
                    }
                )

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置熔断器"""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def _record_failure(self):
        """记录失败"""
        self.failure_count += 1

    def _reset_circuit(self):
        """重置熔断器"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"