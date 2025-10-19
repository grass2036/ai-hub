"""
系统健康检查服务
Week 5 Day 3: 系统监控和运维自动化
"""

import asyncio
import aiohttp
import aioredis
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import subprocess
import socket
import json
import logging

from backend.config.settings import get_settings
from backend.database import get_db
from backend.models.developer import Developer, DeveloperAPIKey

logger = logging.getLogger(__name__)

settings = get_settings()


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentType(Enum):
    """��件类型"""
    DATABASE = "database"
    REDIS = "redis"
    API_SERVICE = "api_service"
    AI_SERVICE = "ai_service"
    DISK_SPACE = "disk_space"
    MEMORY = "memory"
    CPU = "cpu"
    NETWORK = "network"
    EXTERNAL_API = "external_api"


@dataclass
class HealthCheck:
    """健康检查结果"""
    component: str
    component_type: ComponentType
    status: HealthStatus
    message: str
    details: Dict[str, Any] = None
    response_time_ms: float = 0.0
    timestamp: datetime = None
    tags: List[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "component": self.component,
            "component_type": self.component_type.value,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "response_time_ms": self.response_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags
        }


class HealthChecker:
    """健康检查器"""

    def __init__(self):
        self.checks: Dict[str, HealthCheck] = {}
        self.check_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        self.external_services = {
            "openrouter": {
                "url": "https://openrouter.ai/api/v1/models",
                "timeout": 10,
                "method": "GET"
            },
            "google_gemini": {
                "url": "https://generativelanguage.googleapis.com/v1/models",
                "timeout": 10,
                "method": "GET"
            }
        }

    async def run_all_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        start_time = time.time()
        results = {}

        # 并发执行所有检查
        check_tasks = [
            self.check_database(),
            self.check_redis(),
            self.check_disk_space(),
            self.check_memory(),
            self.check_cpu(),
            self.check_network(),
            self.check_api_service(),
            self.check_ai_services()
        ]

        try:
            # 等待所有检查完成
            check_results = await asyncio.gather(*check_tasks, return_exceptions=True)

            # 处理结果
            for i, result in enumerate(check_results):
                if isinstance(result, Exception):
                    logger.error(f"Health check failed: {result}")
                    continue

                if result:
                    self.checks[result.component] = result
                    results[result.component] = result.to_dict()

        except Exception as e:
            logger.error(f"Error running health checks: {e}")

        # 计算总体健康状态
        overall_status = self._calculate_overall_status()
        total_response_time = (time.time() - start_time) * 1000

        # 记录到历史
        history_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": overall_status.value,
            "total_response_time_ms": total_response_time,
            "checks": results,
            "summary": self._generate_summary()
        }

        self._add_to_history(history_entry)

        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": total_response_time,
            "checks": results,
            "summary": history_entry["summary"]
        }

    async def check_database(self) -> HealthCheck:
        """检查数据库连接"""
        start_time = time.time()
        component = "postgresql"
        details = {}

        try:
            # 测试数据库连接
            db = next(get_db())

            # 执行简单查询
            result = db.execute("SELECT 1")
            result.fetchone()

            # 检查连接数
            connection_result = db.execute("SELECT count(*) FROM pg_stat_activity")
            active_connections = connection_result.scalar()

            # 检查数据库大小
            size_result = db.execute("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as size
            """)
            db_size = size_result.scalar()

            db.close()

            details.update({
                "active_connections": active_connections,
                "database_size": db_size,
                "connection_successful": True
            })

            status = HealthStatus.HEALTHY
            message = "Database connection successful"

        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Database connection failed: {str(e)}"
            details["error"] = str(e)
            details["connection_successful"] = False

        response_time = (time.time() - start_time) * 1000

        return HealthCheck(
            component=component,
            component_type=ComponentType.DATABASE,
            status=status,
            message=message,
            details=details,
            response_time_ms=response_time,
            tags=["core", "persistence"]
        )

    async def check_redis(self) -> HealthCheck:
        """检查Redis连接"""
        start_time = time.time()
        component = "redis"
        details = {}

        try:
            if not settings.redis_url:
                return HealthCheck(
                    component=component,
                    component_type=ComponentType.REDIS,
                    status=HealthStatus.UNKNOWN,
                    message="Redis not configured",
                    details={"configured": False}
                )

            # 测试Redis连接
            redis_client = aioredis.from_url(settings.redis_url)

            # 测试基本操作
            await redis_client.ping()
            test_key = f"health_check_{int(time.time())}"
            await redis_client.setex(test_key, 60, "test_value")
            test_value = await redis_client.get(test_key)
            await redis_client.delete(test_key)

            # 获取Redis信息
            info = await redis_client.info()
            await redis_client.close()

            details.update({
                "connected": True,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
                "test_value": test_value.decode() if test_value else None
            })

            status = HealthStatus.HEALTHY
            message = "Redis connection successful"

        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Redis connection failed: {str(e)}"
            details["error"] = str(e)
            details["connected"] = False

        response_time = (time.time() - start_time) * 1000

        return HealthCheck(
            component=component,
            component_type=ComponentType.REDIS,
            status=status,
            message=message,
            details=details,
            response_time_ms=response_time,
            tags=["core", "cache"]
        )

    async def check_disk_space(self) -> HealthCheck:
        """检查磁盘空间"""
        start_time = time.time()
        component = "disk_space"
        details = {}

        try:
            # 获取磁盘使用情况
            disk_usage = psutil.disk_usage('/')
            total_gb = disk_usage.total / (1024**3)
            used_gb = disk_usage.used / (1024**3)
            free_gb = disk_usage.free / (1024**3)
            usage_percent = (disk_usage.used / disk_usage.total) * 100

            details.update({
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "usage_percent": round(usage_percent, 2),
                "mount_point": "/"
            })

            # 根据使用率确定状态
            if usage_percent < 80:
                status = HealthStatus.HEALTHY
                message = f"Disk space OK ({usage_percent:.1f}% used)"
            elif usage_percent < 90:
                status = HealthStatus.DEGRADED
                message = f"Disk space low ({usage_percent:.1f}% used)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Disk space critical ({usage_percent:.1f}% used)"

        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Failed to check disk space: {str(e)}"
            details["error"] = str(e)

        response_time = (time.time() - start_time) * 1000

        return HealthCheck(
            component=component,
            component_type=ComponentType.DISK_SPACE,
            status=status,
            message=message,
            details=details,
            response_time_ms=response_time,
            tags=["system", "storage"]
        )

    async def check_memory(self) -> HealthCheck:
        """检查内存使用"""
        start_time = time.time()
        component = "memory"
        details = {}

        try:
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024**2)
            used_mb = memory.used / (1024**2)
            total_mb = memory.total / (1024**2)
            usage_percent = memory.percent

            details.update({
                "total_mb": round(total_mb, 2),
                "used_mb": round(used_mb, 2),
                "available_mb": round(available_mb, 2),
                "usage_percent": round(usage_percent, 2),
                "percent": memory.percent
            })

            # 根据使用率确定状态
            if usage_percent < 85:
                status = HealthStatus.HEALTHY
                message = f"Memory usage OK ({usage_percent:.1f}% used)"
            elif usage_percent < 95:
                status = HealthStatus.DEGRADED
                message = f"Memory usage high ({usage_percent:.1f}% used)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Memory usage critical ({usage_percent:.1f}% used)"

        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Failed to check memory: {str(e)}"
            details["error"] = str(e)

        response_time = (time.time() - start_time) * 1000

        return HealthCheck(
            component=component,
            component_type=ComponentType.MEMORY,
            status=status,
            message=message,
            details=details,
            response_time_ms=response_time,
            tags=["system", "resource"]
        )

    async def check_cpu(self) -> HealthCheck:
        """检查CPU使用"""
        start_time = time.time()
        component = "cpu"
        details = {}

        try:
            # 获取CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg()

            details.update({
                "usage_percent": round(cpu_percent, 2),
                "cpu_count": cpu_count,
                "load_avg_1m": round(load_avg[0], 2),
                "load_avg_5m": round(load_avg[1], 2),
                "load_avg_15m": round(load_avg[2], 2)
            })

            # 根据使用率确定状态
            if cpu_percent < 70:
                status = HealthStatus.HEALTHY
                message = f"CPU usage OK ({cpu_percent:.1f}% used)"
            elif cpu_percent < 90:
                status = HealthStatus.DEGRADED
                message = f"CPU usage high ({cpu_percent:.1f}% used)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"CPU usage critical ({cpu_percent:.1f}% used)"

        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Failed to check CPU: {str(e)}"
            details["error"] = str(e)

        response_time = (time.time() - start_time) * 1000

        return HealthCheck(
            component=component,
            component_type=ComponentType.CPU,
            status=status,
            message=message,
            details=details,
            response_time_ms=response_time,
            tags=["system", "resource"]
        )

    async def check_network(self) -> HealthCheck:
        """检查网络连接"""
        start_time = time.time()
        component = "network"
        details = {}

        try:
            # 测试网络连接
            test_hosts = ["8.8.8.8", "1.1.1.1"]
            connected_hosts = []
            failed_hosts = []

            for host in test_hosts:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, 53))
                    sock.close()

                    if result == 0:
                        connected_hosts.append(host)
                    else:
                        failed_hosts.append(host)
                except Exception:
                    failed_hosts.append(host)

            # 获取网络IO统计
            net_io = psutil.net_io_counters()

            details.update({
                "connected_hosts": connected_hosts,
                "failed_hosts": failed_hosts,
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            })

            # 根据连接结果确定状态
            if len(connected_hosts) == len(test_hosts):
                status = HealthStatus.HEALTHY
                message = f"Network connectivity OK ({len(connected_hosts)}/{len(test_hosts)} hosts reachable)"
            elif len(connected_hosts) > 0:
                status = HealthStatus.DEGRADED
                message = f"Network connectivity degraded ({len(connected_hosts)}/{len(test_hosts)} hosts reachable)"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Network connectivity failed (0/{len(test_hosts)} hosts reachable)"

        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Failed to check network: {str(e)}"
            details["error"] = str(e)

        response_time = (time.time() - start_time) * 1000

        return HealthCheck(
            component=component,
            component_type=ComponentType.NETWORK,
            status=status,
            message=message,
            details=details,
            response_time_ms=response_time,
            tags=["system", "network"]
        )

    async def check_api_service(self) -> HealthCheck:
        """检查API服务"""
        start_time = time.time()
        component = "api_service"
        details = {}

        try:
            # 测试本地API端点
            base_url = f"http://localhost:{8001 if settings.environment == 'development' else 8000}"
            endpoints = ["/health", "/api/v1/status"]

            results = {}
            for endpoint in endpoints:
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                        async with session.get(f"{base_url}{endpoint}") as response:
                            results[endpoint] = {
                                "status_code": response.status,
                                "response_time_ms": (time.time() - start_time) * 1000
                            }

                            if response.status == 200:
                                results[endpoint]["success"] = True
                                results[endpoint]["data"] = await response.json()
                            else:
                                results[endpoint]["success"] = False
                                results[endpoint]["error"] = await response.text()

                except Exception as e:
                    results[endpoint] = {
                        "success": False,
                        "error": str(e)
                    }

            # 检查所有端点的结果
            successful_endpoints = sum(1 for r in results.values() if r.get("success", False))
            total_endpoints = len(results)

            details.update({
                "endpoints": results,
                "successful_endpoints": successful_endpoints,
                "total_endpoints": total_endpoints,
                "base_url": base_url
            })

            if successful_endpoints == total_endpoints:
                status = HealthStatus.HEALTHY
                message = f"All API endpoints healthy ({successful_endpoints}/{total_endpoints})"
            elif successful_endpoints > 0:
                status = HealthStatus.DEGRADED
                message = f"Some API endpoints degraded ({successful_endpoints}/{total_endpoints})"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"All API endpoints failed (0/{total_endpoints})"

        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Failed to check API service: {str(e)}"
            details["error"] = str(e)

        response_time = (time.time() - start_time) * 1000

        return HealthCheck(
            component=component,
            component_type=ComponentType.API_SERVICE,
            status=status,
            message=message,
            details=details,
            response_time_ms=response_time,
            tags=["core", "api"]
        )

    async def check_ai_services(self) -> HealthCheck:
        """检查AI服务"""
        start_time = time.time()
        component = "ai_services"
        details = {}

        try:
            ai_keys = settings.validate_ai_keys()
            results = {}

            for service, is_configured in ai_keys.items():
                if not is_configured:
                    results[service] = {
                        "configured": False,
                        "status": "not_configured"
                    }
                    continue

                service_config = self.external_services.get(service)
                if not service_config:
                    continue

                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=service_config["timeout"])) as session:
                        headers = {}
                        if service == "openrouter":
                            headers["Authorization"] = f"Bearer {settings.openrouter_api_key}"
                        elif service == "google_gemini":
                            headers["Authorization"] = f"Bearer {settings.gemini_api_key}"

                        async with session.request(service_config["method"], service_config["url"], headers=headers) as response:
                            results[service] = {
                                "configured": True,
                                "status_code": response.status,
                                "response_time_ms": (time.time() - start_time) * 1000,
                                "success": response.status == 200
                            }

                            if response.status == 200:
                                data = await response.json()
                                results[service]["data"] = {
                                    "models_count": len(data.get("data", [])),
                                    "has_data": bool(data.get("data"))
                                }

                except asyncio.TimeoutError:
                    results[service] = {
                        "configured": True,
                        "success": False,
                        "error": "timeout"
                    }
                except Exception as e:
                    results[service] = {
                        "configured": True,
                        "success": False,
                        "error": str(e)
                    }

            # 统计结果
            configured_services = sum(1 for r in results.values() if r.get("configured", False))
            healthy_services = sum(1 for r in results.values() if r.get("success", False))

            details.update({
                "services": results,
                "configured_services": configured_services,
                "healthy_services": healthy_services
            })

            if configured_services == 0:
                status = HealthStatus.DEGRADED
                message = "No AI services configured"
            elif healthy_services == configured_services:
                status = HealthStatus.HEALTHY
                message = f"All AI services healthy ({healthy_services}/{configured_services})"
            elif healthy_services > 0:
                status = HealthStatus.DEGRADED
                message = f"Some AI services degraded ({healthy_services}/{configured_services})"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"All AI services failed (0/{configured_services})"

        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"Failed to check AI services: {str(e)}"
            details["error"] = str(e)

        response_time = (time.time() - start_time) * 1000

        return HealthCheck(
            component=component,
            component_type=ComponentType.AI_SERVICE,
            status=status,
            message=message,
            details=details,
            response_time_ms=response_time,
            tags=["core", "ai"]
        )

    def _calculate_overall_status(self) -> HealthStatus:
        """计算总体健康状态"""
        if not self.checks:
            return HealthStatus.UNKNOWN

        statuses = [check.status for check in self.checks.values()]

        if all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        elif any(status == HealthStatus.UNHEALTHY for status in statuses):
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.DEGRADED

    def _generate_summary(self) -> Dict[str, Any]:
        """生成健康检查摘要"""
        if not self.checks:
            return {"total_checks": 0}

        summary = {
            "total_checks": len(self.checks),
            "healthy_checks": 0,
            "degraded_checks": 0,
            "unhealthy_checks": 0,
            "unknown_checks": 0,
            "by_component_type": {},
            "average_response_time_ms": 0.0
        }

        total_response_time = 0

        for check in self.checks.values():
            # 统计状态
            if check.status == HealthStatus.HEALTHY:
                summary["healthy_checks"] += 1
            elif check.status == HealthStatus.DEGRADED:
                summary["degraded_checks"] += 1
            elif check.status == HealthStatus.UNHEALTHY:
                summary["unhealthy_checks"] += 1
            else:
                summary["unknown_checks"] += 1

            # 按组件类型统计
            component_type = check.component_type.value
            if component_type not in summary["by_component_type"]:
                summary["by_component_type"][component_type] = {
                    "healthy": 0, "degraded": 0, "unhealthy": 0, "unknown": 0
                }

            if check.status == HealthStatus.HEALTHY:
                summary["by_component_type"][component_type]["healthy"] += 1
            elif check.status == HealthStatus.DEGRADED:
                summary["by_component_type"][component_type]["degraded"] += 1
            elif check.status == HealthStatus.UNHEALTHY:
                summary["by_component_type"][component_type]["unhealthy"] += 1
            else:
                summary["by_component_type"][component_type]["unknown"] += 1

            total_response_time += check.response_time_ms

        if self.checks:
            summary["average_response_time_ms"] = total_response_time / len(self.checks)

        return summary

    def _add_to_history(self, entry: Dict[str, Any]):
        """添加到历史记录"""
        self.check_history.append(entry)

        # 保持历史记录大小
        if len(self.check_history) > self.max_history_size:
            self.check_history = self.check_history[-self.max_history_size:]

    async def get_health_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取健康检查历史"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return [
            entry for entry in self.check_history
            if datetime.fromisoformat(entry["timestamp"]) >= cutoff_time
        ]

    async def run_specific_check(self, component: str) -> HealthCheck:
        """运行特定的健康检查"""
        check_methods = {
            "database": self.check_database,
            "redis": self.check_redis,
            "disk_space": self.check_disk_space,
            "memory": self.check_memory,
            "cpu": self.check_cpu,
            "network": self.check_network,
            "api_service": self.check_api_service,
            "ai_services": self.check_ai_services
        }

        method = check_methods.get(component)
        if method:
            return await method()
        else:
            return HealthCheck(
                component=component,
                component_type=ComponentType.API_SERVICE,
                status=HealthStatus.UNKNOWN,
                message=f"Unknown component: {component}"
            )


# 全局健康检查器实例
health_checker = HealthChecker()


async def start_health_monitoring():
    """启动健康监控"""
    logger.info("Starting health monitoring...")

    while True:
        try:
            await health_checker.run_all_checks()
            await asyncio.sleep(60)  # 每分钟检查一次
        except Exception as e:
            logger.error(f"Error in health monitoring: {e}")
            await asyncio.sleep(60)