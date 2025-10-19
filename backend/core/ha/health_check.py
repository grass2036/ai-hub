"""
健康检查系统
Week 6 Day 5: 负载均衡和高可用配置

提供全面的服务健康检查和监控功能
"""

import asyncio
import time
import json
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import redis
import psutil

class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"

class CheckType(Enum):
    """检查类型"""
    HTTP_ENDPOINT = "http_endpoint"
    TCP_PORT = "tcp_port"
    DATABASE = "database"
    REDIS = "redis"
    DISK_SPACE = "disk_space"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    CUSTOM = "custom"

@dataclass
class HealthCheckResult:
    """健康检查结果"""
    check_id: str
    check_name: str
    check_type: CheckType
    status: HealthStatus
    message: str
    details: Dict[str, Any] = None
    response_time: float = 0.0
    timestamp: datetime = None
    consecutive_failures: int = 0
    last_success: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "check_name": self.check_name,
            "check_type": self.check_type.value,
            "status": self.status.value,
            "message": self.message,
            "details": self.details or {},
            "response_time": self.response_time,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "consecutive_failures": self.consecutive_failures,
            "last_success": self.last_success.isoformat() if self.last_success else None
        }

@dataclass
class HealthCheckConfig:
    """健康检查配置"""
    check_name: str
    check_type: CheckType
    target: str  # URL, host:port, 或其他目标
    interval: int = 30  # 检查间隔（秒）
    timeout: int = 10  # 超时时间（秒）
    retries: int = 3  # 重试次数
    retry_delay: float = 1.0  # 重试延迟
    failure_threshold: int = 3  # 连续失败阈值
    success_threshold: int = 2  # 成功恢复阈值
    enabled: bool = True
    params: Dict[str, Any] = None

class HealthChecker:
    """健康检查器"""

    def __init__(self):
        self.checks: Dict[str, HealthCheckConfig] = {}
        self.results: Dict[str, HealthCheckResult] = {}
        self.check_tasks: Dict[str, asyncio.Task] = {}
        self.callbacks: List[Callable[[HealthCheckResult], None]] = []
        self.is_running = False

    def add_check(self, config: HealthCheckConfig) -> str:
        """添加健康检查"""
        check_id = str(int(time.time() * 1000)) + "_" + str(len(self.checks))
        self.checks[check_id] = config

        # 初始化结果
        self.results[check_id] = HealthCheckResult(
            check_id=check_id,
            check_name=config.check_name,
            check_type=config.check_type,
            status=HealthStatus.UNKNOWN,
            message="Waiting for first check",
            timestamp=datetime.utcnow()
        )

        # 如果检查器正在运行，启动检查任务
        if self.is_running and config.enabled:
            self.check_tasks[check_id] = asyncio.create_task(
                self._check_loop(check_id)
            )

        logging.info(f"Added health check: {config.check_name} ({check_id})")
        return check_id

    def remove_check(self, check_id: str) -> bool:
        """移除健康检查"""
        if check_id in self.checks:
            # 取消检查任务
            if check_id in self.check_tasks:
                self.check_tasks[check_id].cancel()
                del self.check_tasks[check_id]

            del self.checks[check_id]
            del self.results[check_id]

            logging.info(f"Removed health check: {check_id}")
            return True
        return False

    def add_callback(self, callback: Callable[[HealthCheckResult], None]) -> None:
        """添加状态变更回调"""
        self.callbacks.append(callback)

    async def start(self) -> None:
        """启动健康检查"""
        if self.is_running:
            return

        self.is_running = True

        # 启动所有启用的检查
        for check_id, config in self.checks.items():
            if config.enabled:
                self.check_tasks[check_id] = asyncio.create_task(
                    self._check_loop(check_id)
                )

        logging.info("Health checker started")

    async def stop(self) -> None:
        """停止健康检查"""
        self.is_running = False

        # 取消所有检查任务
        for task in self.check_tasks.values():
            task.cancel()

        # 等待所有任务完成
        if self.check_tasks:
            await asyncio.gather(*self.check_tasks.values(), return_exceptions=True)

        self.check_tasks.clear()
        logging.info("Health checker stopped")

    async def _check_loop(self, check_id: str) -> None:
        """健康检查循环"""
        config = self.checks[check_id]

        while self.is_running and config.enabled:
            try:
                # 执行健康检查
                result = await self._execute_check(config)

                # 更新结果
                await self._update_result(check_id, result)

                # 等待下次检查
                await asyncio.sleep(config.interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Health check loop error for {check_id}: {str(e)}")
                await asyncio.sleep(config.interval)

    async def _execute_check(self, config: HealthCheckConfig) -> HealthCheckResult:
        """执行健康检查"""
        start_time = time.time()
        last_result = self.results.get(config.check_id)

        try:
            if config.check_type == CheckType.HTTP_ENDPOINT:
                result = await self._check_http_endpoint(config)
            elif config.check_type == CheckType.TCP_PORT:
                result = await self._check_tcp_port(config)
            elif config.check_type == CheckType.DATABASE:
                result = await self._check_database(config)
            elif config.check_type == CheckType.REDIS:
                result = await self._check_redis(config)
            elif config.check_type == CheckType.DISK_SPACE:
                result = await self._check_disk_space(config)
            elif config.check_type == CheckType.MEMORY_USAGE:
                result = await self._check_memory_usage(config)
            elif config.check_type == CheckType.CPU_USAGE:
                result = await self._check_cpu_usage(config)
            elif config.check_type == CheckType.CUSTOM:
                result = await self._check_custom(config)
            else:
                result = HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.UNKNOWN,
                    message=f"Unsupported check type: {config.check_type.value}"
                )

            result.response_time = time.time() - start_time
            result.timestamp = datetime.utcnow()

            return result

        except Exception as e:
            return HealthCheckResult(
                check_id="",
                check_name=config.check_name,
                check_type=config.check_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                response_time=time.time() - start_time,
                timestamp=datetime.utcnow()
            )

    async def _update_result(self, check_id: str, new_result: HealthCheckResult) -> None:
        """更新检查结果"""
        old_result = self.results.get(check_id)

        # 继承之前的失败次数
        if old_result:
            if new_result.status == HealthStatus.HEALTHY:
                new_result.consecutive_failures = 0
                new_result.last_success = new_result.timestamp
            else:
                new_result.consecutive_failures = old_result.consecutive_failures + 1
                if old_result.last_success:
                    new_result.last_success = old_result.last_success

        # 检查状态变更
        if old_result and old_result.status != new_result.status:
            logging.info(
                f"Health check '{new_result.check_name}' status changed: "
                f"{old_result.status.value} -> {new_result.status.value}"
            )

            # 调用回调
            for callback in self.callbacks:
                try:
                    callback(new_result)
                except Exception as e:
                    logging.error(f"Health check callback error: {str(e)}")

        # 更新结果
        self.results[check_id] = new_result

    async def _check_http_endpoint(self, config: HealthCheckConfig) -> HealthCheckResult:
        """HTTP端点健康检查"""
        params = config.params or {}
        method = params.get("method", "GET")
        headers = params.get("headers", {})
        expected_status = params.get("expected_status", 200)
        expected_content = params.get("expected_content")

        for attempt in range(config.retries + 1):
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=config.timeout)
                ) as session:
                    async with session.request(
                        method,
                        config.target,
                        headers=headers
                    ) as response:
                        if response.status == expected_status:
                            if expected_content:
                                content = await response.text()
                                if expected_content in content:
                                    return HealthCheckResult(
                                        check_id="",
                                        check_name=config.check_name,
                                        check_type=config.check_type,
                                        status=HealthStatus.HEALTHY,
                                        message=f"HTTP {response.status} - OK",
                                        details={
                                            "status_code": response.status,
                                            "response_headers": dict(response.headers),
                                            "attempt": attempt + 1
                                        }
                                    )
                                else:
                                    return HealthCheckResult(
                                        check_id="",
                                        check_name=config.check_name,
                                        check_type=config.check_type,
                                        status=HealthStatus.UNHEALTHY,
                                        message=f"Expected content not found",
                                        details={
                                            "status_code": response.status,
                                            "expected_content": expected_content,
                                            "attempt": attempt + 1
                                        }
                                    )
                            else:
                                return HealthCheckResult(
                                    check_id="",
                                    check_name=config.check_name,
                                    check_type=config.check_type,
                                    status=HealthStatus.HEALTHY,
                                    message=f"HTTP {response.status} - OK",
                                    details={
                                        "status_code": response.status,
                                        "response_headers": dict(response.headers),
                                        "attempt": attempt + 1
                                    }
                                )
                        else:
                            return HealthCheckResult(
                                check_id="",
                                check_name=config.check_name,
                                check_type=config.check_type,
                                status=HealthStatus.UNHEALTHY,
                                message=f"HTTP {response.status} - Expected {expected_status}",
                                details={
                                    "status_code": response.status,
                                    "expected_status": expected_status,
                                    "attempt": attempt + 1
                                }
                            )

            except Exception as e:
                if attempt < config.retries:
                    await asyncio.sleep(config.retry_delay)
                else:
                    return HealthCheckResult(
                        check_id="",
                        check_name=config.check_name,
                        check_type=config.check_type,
                        status=HealthStatus.UNHEALTHY,
                        message=f"HTTP request failed: {str(e)}",
                        details={"attempt": attempt + 1}
                    )

        return HealthCheckResult(
            check_id="",
            check_name=config.check_name,
            check_type=config.check_type,
            status=HealthStatus.UNKNOWN,
            message="No attempts made"
        )

    async def _check_tcp_port(self, config: HealthCheckConfig) -> HealthCheckResult:
        """TCP端口健康检查"""
        host, port = config.target.split(":")
        port = int(port)

        for attempt in range(config.retries + 1):
            try:
                future = asyncio.open_connection(host, port)
                reader, writer = await asyncio.wait_for(
                    future,
                    timeout=config.timeout
                )
                writer.close()
                await writer.wait_closed()

                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.HEALTHY,
                    message=f"TCP port {port} is reachable",
                    details={"host": host, "port": port, "attempt": attempt + 1}
                )

            except Exception as e:
                if attempt < config.retries:
                    await asyncio.sleep(config.retry_delay)
                else:
                    return HealthCheckResult(
                        check_id="",
                        check_name=config.check_name,
                        check_type=config.check_type,
                        status=HealthStatus.UNHEALTHY,
                        message=f"TCP port {port} is not reachable: {str(e)}",
                        details={"host": host, "port": port, "attempt": attempt + 1}
                    )

        return HealthCheckResult(
            check_id="",
            check_name=config.check_name,
            check_type=config.check_type,
            status=HealthStatus.UNKNOWN,
            message="No attempts made"
        )

    async def _check_database(self, config: HealthCheckConfig) -> HealthCheckResult:
        """数据库健康检查"""
        params = config.params or {}
        connection_string = params.get("connection_string")

        if not connection_string:
            return HealthCheckResult(
                check_id="",
                check_name=config.check_name,
                check_type=config.check_type,
                status=HealthStatus.UNHEALTHY,
                message="Database connection string not provided"
            )

        try:
            # 这里应该根据实际的数据库类型进行检查
            # 示例实现，假设使用PostgreSQL
            import asyncpg

            conn = await asyncio.wait_for(
                asyncpg.connect(connection_string),
                timeout=config.timeout
            )

            # 执行简单查询
            result = await conn.fetchval("SELECT 1")
            await conn.close()

            if result == 1:
                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.HEALTHY,
                    message="Database connection successful",
                    details={"connection_time": "fast"}
                )
            else:
                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.UNHEALTHY,
                    message="Database query returned unexpected result"
                )

        except Exception as e:
            return HealthCheckResult(
                check_id="",
                check_name=config.check_name,
                check_type=config.check_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}"
            )

    async def _check_redis(self, config: HealthCheckConfig) -> HealthCheckResult:
        """Redis健康检查"""
        params = config.params or {}
        host = params.get("host", "localhost")
        port = params.get("port", 6379)
        password = params.get("password")
        db = params.get("db", 0)

        try:
            redis_client = redis.Redis(
                host=host,
                port=port,
                password=password,
                db=db,
                socket_timeout=config.timeout
            )

            # 执行ping命令
            result = redis_client.ping()

            if result:
                # 获取Redis信息
                info = redis_client.info()
                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.HEALTHY,
                    message="Redis connection successful",
                    details={
                        "redis_version": info.get("redis_version"),
                        "used_memory": info.get("used_memory_human"),
                        "connected_clients": info.get("connected_clients")
                    }
                )
            else:
                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.UNHEALTHY,
                    message="Redis ping failed"
                )

        except Exception as e:
            return HealthCheckResult(
                check_id="",
                check_name=config.check_name,
                check_type=config.check_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection failed: {str(e)}"
            )

    async def _check_disk_space(self, config: HealthCheckConfig) -> HealthCheckResult:
        """磁盘空间健康检查"""
        params = config.params or {}
        path = params.get("path", "/")
        warning_threshold = params.get("warning_threshold", 80)  # 80%
        critical_threshold = params.get("critical_threshold", 90)  # 90%

        try:
            disk_usage = psutil.disk_usage(path)
            usage_percent = (disk_usage.used / disk_usage.total) * 100

            details = {
                "path": path,
                "total": disk_usage.total,
                "used": disk_usage.used,
                "free": disk_usage.free,
                "usage_percent": usage_percent
            }

            if usage_percent >= critical_threshold:
                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.CRITICAL,
                    message=f"Disk usage critically high: {usage_percent:.1f}%",
                    details=details
                )
            elif usage_percent >= warning_threshold:
                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.DEGRADED,
                    message=f"Disk usage high: {usage_percent:.1f}%",
                    details=details
                )
            else:
                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.HEALTHY,
                    message=f"Disk usage normal: {usage_percent:.1f}%",
                    details=details
                )

        except Exception as e:
            return HealthCheckResult(
                check_id="",
                check_name=config.check_name,
                check_type=config.check_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check disk space: {str(e)}"
            )

    async def _check_memory_usage(self, config: HealthCheckConfig) -> HealthCheckResult:
        """内存使用健康检查"""
        params = config.params or {}
        warning_threshold = params.get("warning_threshold", 80)  # 80%
        critical_threshold = params.get("critical_threshold", 90)  # 90%

        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent

            details = {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "usage_percent": usage_percent,
                "cached": memory.cached
            }

            if usage_percent >= critical_threshold:
                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.CRITICAL,
                    message=f"Memory usage critically high: {usage_percent:.1f}%",
                    details=details
                )
            elif usage_percent >= warning_threshold:
                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.DEGRADED,
                    message=f"Memory usage high: {usage_percent:.1f}%",
                    details=details
                )
            else:
                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.HEALTHY,
                    message=f"Memory usage normal: {usage_percent:.1f}%",
                    details=details
                )

        except Exception as e:
            return HealthCheckResult(
                check_id="",
                check_name=config.check_name,
                check_type=config.check_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check memory usage: {str(e)}"
            )

    async def _check_cpu_usage(self, config: HealthCheckConfig) -> HealthCheckResult:
        """CPU使用健康检查"""
        params = config.params or {}
        warning_threshold = params.get("warning_threshold", 80)  # 80%
        critical_threshold = params.get("critical_threshold", 90)  # 90%
        interval = params.get("interval", 1)  # 采样间隔（秒）

        try:
            cpu_percent = psutil.cpu_percent(interval=interval)

            details = {
                "cpu_percent": cpu_percent,
                "interval": interval,
                "cpu_count": psutil.cpu_count()
            }

            if cpu_percent >= critical_threshold:
                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.CRITICAL,
                    message=f"CPU usage critically high: {cpu_percent:.1f}%",
                    details=details
                )
            elif cpu_percent >= warning_threshold:
                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.DEGRADED,
                    message=f"CPU usage high: {cpu_percent:.1f}%",
                    details=details
                )
            else:
                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.HEALTHY,
                    message=f"CPU usage normal: {cpu_percent:.1f}%",
                    details=details
                )

        except Exception as e:
            return HealthCheckResult(
                check_id="",
                check_name=config.check_name,
                check_type=config.check_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check CPU usage: {str(e)}"
            )

    async def _check_custom(self, config: HealthCheckConfig) -> HealthCheckResult:
        """自定义健康检查"""
        params = config.params or {}
        check_function = params.get("check_function")

        if not check_function:
            return HealthCheckResult(
                check_id="",
                check_name=config.check_name,
                check_type=config.check_type,
                status=HealthStatus.UNHEALTHY,
                message="Custom check function not provided"
            )

        try:
            # 执行自定义检查函数
            if callable(check_function):
                result = await check_function(config)
                return result
            else:
                return HealthCheckResult(
                    check_id="",
                    check_name=config.check_name,
                    check_type=config.check_type,
                    status=HealthStatus.UNHEALTHY,
                    message="Invalid check function"
                )

        except Exception as e:
            return HealthCheckResult(
                check_id="",
                check_name=config.check_name,
                check_type=config.check_type,
                status=HealthStatus.UNHEALTHY,
                message=f"Custom check failed: {str(e)}"
            )

    def get_all_results(self) -> List[HealthCheckResult]:
        """获取所有健康检查结果"""
        return list(self.results.values())

    def get_healthy_checks(self) -> List[HealthCheckResult]:
        """获取健康的检查结果"""
        return [r for r in self.results.values() if r.status == HealthStatus.HEALTHY]

    def get_unhealthy_checks(self) -> List[HealthCheckResult]:
        """获取不健康的检查结果"""
        return [r for r in self.results.values() if r.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]]

    def get_overall_status(self) -> HealthStatus:
        """获取整体健康状态"""
        if not self.results:
            return HealthStatus.UNKNOWN

        statuses = [r.status for r in self.results.values()]

        if any(s == HealthStatus.CRITICAL for s in statuses):
            return HealthStatus.CRITICAL
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def get_health_summary(self) -> Dict[str, Any]:
        """获取健康检查摘要"""
        all_results = self.get_all_results()
        healthy_count = len(self.get_healthy_checks())
        unhealthy_count = len(self.get_unhealthy_checks())
        degraded_count = len([r for r in all_results if r.status == HealthStatus.DEGRADED])

        overall_status = self.get_overall_status()

        return {
            "overall_status": overall_status.value,
            "total_checks": len(all_results),
            "healthy_checks": healthy_count,
            "degraded_checks": degraded_count,
            "unhealthy_checks": unhealthy_count,
            "health_score": (healthy_count / len(all_results)) * 100 if all_results else 0,
            "last_updated": max((r.timestamp for r in all_results), default=datetime.utcnow()).isoformat(),
            "checks": {
                result.check_id: result.to_dict()
                for result in all_results
            }
        }

# 全局健康检查器实例
global_health_checker: Optional[HealthChecker] = None

def get_health_checker() -> HealthChecker:
    """获取全局健康检查器"""
    global global_health_checker
    if global_health_checker is None:
        global_health_checker = HealthChecker()
    return global_health_checker