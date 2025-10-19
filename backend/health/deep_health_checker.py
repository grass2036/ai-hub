"""
深度健康检查系统
Week 5 Day 5: 系统监控和运维增强 - 深度健康检查
"""

import asyncio
import aiohttp
import asyncpg
import redis
import psutil
import socket
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from backend.config.settings import get_settings
from backend.database import get_db

logger = logging.getLogger(__name__)
settings = get_settings()


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class CheckType(Enum):
    """检查类型"""
    BASIC = "basic"           # 基础检查
    DEEP = "deep"           # 深度检查
    INTEGRATION = "integration"  # 集成检查
    PERFORMANCE = "performance"  # 性能检查
    SECURITY = "security"   # 安全检查


class CheckSeverity(Enum):
    """检查严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """健康检查定义"""
    check_id: str
    name: str
    description: str
    check_type: CheckType
    severity: CheckSeverity
    timeout: float
    interval: int  # 检查间隔（秒）
    enabled: bool = True
    dependencies: List[str] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['check_type'] = self.check_type.value
        data['severity'] = self.severity.value
        return data


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    check_id: str
    status: HealthStatus
    message: str
    response_time: float
    timestamp: datetime
    details: Dict[str, Any] = None
    error: Optional[str] = None
    metrics: Dict[str, float] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.metrics is None:
            self.metrics = {}

    @property
    def is_healthy(self) -> bool:
        return self.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        data['timestamp'] = self.timestamp.isoformat()
        data['is_healthy'] = self.is_healthy
        return data


@dataclass
class ComponentHealth:
    """组件健康状态"""
    component_id: str
    name: str
    status: HealthStatus
    last_check: datetime
    uptime_percentage: float
    total_checks: int
    successful_checks: int
    failed_checks: int
    avg_response_time: float
    last_error: Optional[str] = None
    dependencies: List[str] = None
    metrics: Dict[str, float] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.metrics is None:
            self.metrics = {}

    @property
    def success_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return (self.successful_checks / self.total_checks) * 100

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        data['last_check'] = self.last_check.isoformat()
        data['success_rate'] = self.success_rate
        return data


class HealthCheckExecutor:
    """健康检查执行器"""

    def __init__(self):
        self.check_functions: Dict[str, Callable] = {}
        self._register_default_checks()

    def _register_default_checks(self):
        """注册默认检查函数"""
        self.check_functions.update({
            'database_connection': self._check_database_connection,
            'redis_connection': self._check_redis_connection,
            'disk_space': self._check_disk_space,
            'memory_usage': self._check_memory_usage,
            'cpu_usage': self._check_cpu_usage,
            'network_connectivity': self._check_network_connectivity,
            'external_apis': self._check_external_apis,
            'file_system': self._check_file_system,
            'process_health': self._check_process_health,
            'ssl_certificates': self._check_ssl_certificates,
            'security_headers': self._check_security_headers,
            'log_system': self._check_log_system,
            'cache_performance': self._check_cache_performance,
            'database_performance': self._check_database_performance
        })

    async def execute_check(self, health_check: HealthCheck) -> HealthCheckResult:
        """执行健康检查"""
        start_time = time.time()

        try:
            # 获取检查函数
            check_function = self.check_functions.get(health_check.check_id)
            if not check_function:
                return HealthCheckResult(
                    check_id=health_check.check_id,
                    status=HealthStatus.UNKNOWN,
                    message=f"Check function not found: {health_check.check_id}",
                    response_time=time.time() - start_time,
                    timestamp=datetime.utcnow(),
                    error="Check function not implemented"
                )

            # 执行检查（带超时）
            try:
                result = await asyncio.wait_for(
                    check_function(),
                    timeout=health_check.timeout
                )

                response_time = time.time() - start_time

                if isinstance(result, HealthCheckResult):
                    result.response_time = response_time
                    result.timestamp = datetime.utcnow()
                    return result
                else:
                    return HealthCheckResult(
                        check_id=health_check.check_id,
                        status=HealthStatus.HEALTHY,
                        message="Check completed successfully",
                        response_time=response_time,
                        timestamp=datetime.utcnow(),
                        details={"result": result} if isinstance(result, dict) else {}
                    )

            except asyncio.TimeoutError:
                return HealthCheckResult(
                    check_id=health_check.check_id,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check timed out after {health_check.timeout}s",
                    response_time=health_check.timeout,
                    timestamp=datetime.utcnow(),
                    error="Timeout"
                )

        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"Health check {health_check.check_id} failed: {e}")

            return HealthCheckResult(
                check_id=health_check.check_id,
                status=HealthStatus.CRITICAL,
                message=f"Check failed: {str(e)}",
                response_time=response_time,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    # 基础检查函数
    async def _check_database_connection(self) -> HealthCheckResult:
        """检查数据库连接"""
        try:
            db = next(get_db())
            start_time = time.time()

            # 执行简单查询
            result = db.execute("SELECT 1 as test")
            result.fetchone()

            response_time = time.time() - start_time

            # 检查连接池状态
            pool_info = {
                "checked": True,
                "query_time": response_time
            }

            return HealthCheckResult(
                check_id="database_connection",
                status=HealthStatus.HEALTHY if response_time < 1.0 else HealthStatus.DEGRADED,
                message=f"Database connection OK (response time: {response_time:.3f}s)",
                response_time=response_time,
                timestamp=datetime.utcnow(),
                details=pool_info,
                metrics={"query_time": response_time}
            )

        except Exception as e:
            return HealthCheckResult(
                check_id="database_connection",
                status=HealthStatus.CRITICAL,
                message=f"Database connection failed: {str(e)}",
                response_time=0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def _check_redis_connection(self) -> HealthCheckResult:
        """检查Redis连接"""
        try:
            if not settings.redis_url:
                return HealthCheckResult(
                    check_id="redis_connection",
                    status=HealthStatus.UNKNOWN,
                    message="Redis not configured",
                    response_time=0,
                    timestamp=datetime.utcnow()
                )

            redis_client = redis.from_url(settings.redis_url)
            start_time = time.time()

            # 执行ping命令
            result = redis_client.ping()

            response_time = time.time() - start_time

            if result:
                # 获取Redis信息
                info = redis_client.info()

                return HealthCheckResult(
                    check_id="redis_connection",
                    status=HealthStatus.HEALTHY if response_time < 0.5 else HealthStatus.DEGRADED,
                    message=f"Redis connection OK (response time: {response_time:.3f}s)",
                    response_time=response_time,
                    timestamp=datetime.utcnow(),
                    details={
                        "redis_version": info.get("redis_version"),
                        "connected_clients": info.get("connected_clients"),
                        "used_memory": info.get("used_memory_human")
                    },
                    metrics={
                        "response_time": response_time,
                        "connected_clients": info.get("connected_clients", 0)
                    }
                )
            else:
                return HealthCheckResult(
                    check_id="redis_connection",
                    status=HealthStatus.UNHEALTHY,
                    message="Redis ping failed",
                    response_time=response_time,
                    timestamp=datetime.utcnow()
                )

        except Exception as e:
            return HealthCheckResult(
                check_id="redis_connection",
                status=HealthStatus.CRITICAL,
                message=f"Redis connection failed: {str(e)}",
                response_time=0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def _check_disk_space(self) -> HealthCheckResult:
        """检查磁盘空间"""
        try:
            disk_usage = psutil.disk_usage('/')

            total_gb = disk_usage.total / (1024**3)
            used_gb = disk_usage.used / (1024**3)
            free_gb = disk_usage.free / (1024**3)
            usage_percent = (used_gb / total_gb) * 100

            # 确定状态
            if usage_percent < 80:
                status = HealthStatus.HEALTHY
            elif usage_percent < 90:
                status = HealthStatus.DEGRADED
            elif usage_percent < 95:
                status = HealthStatus.UNHEALTHY
            else:
                status = HealthStatus.CRITICAL

            return HealthCheckResult(
                check_id="disk_space",
                status=status,
                message=f"Disk usage: {usage_percent:.1f}% ({free_gb:.1f}GB free)",
                response_time=0.1,
                timestamp=datetime.utcnow(),
                details={
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "usage_percent": round(usage_percent, 2)
                },
                metrics={
                    "usage_percent": usage_percent,
                    "free_gb": free_gb
                }
            )

        except Exception as e:
            return HealthCheckResult(
                check_id="disk_space",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check disk space: {str(e)}",
                response_time=0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def _check_memory_usage(self) -> HealthCheckResult:
        """检查内存使用"""
        try:
            memory = psutil.virtual_memory()

            total_gb = memory.total / (1024**3)
            used_gb = memory.used / (1024**3)
            available_gb = memory.available / (1024**3)
            usage_percent = memory.percent

            # 确定状态
            if usage_percent < 80:
                status = HealthStatus.HEALTHY
            elif usage_percent < 90:
                status = HealthStatus.DEGRADED
            elif usage_percent < 95:
                status = HealthStatus.UNHEALTHY
            else:
                status = HealthStatus.CRITICAL

            return HealthCheckResult(
                check_id="memory_usage",
                status=status,
                message=f"Memory usage: {usage_percent:.1f}% ({available_gb:.1f}GB available)",
                response_time=0.05,
                timestamp=datetime.utcnow(),
                details={
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "available_gb": round(available_gb, 2),
                    "usage_percent": round(usage_percent, 2)
                },
                metrics={
                    "usage_percent": usage_percent,
                    "available_gb": available_gb
                }
            )

        except Exception as e:
            return HealthCheckResult(
                check_id="memory_usage",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check memory usage: {str(e)}",
                response_time=0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def _check_cpu_usage(self) -> HealthCheckResult:
        """检查CPU使用"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            load_avg = psutil.getloadavg()

            # 确定状态
            if cpu_percent < 70:
                status = HealthStatus.HEALTHY
            elif cpu_percent < 85:
                status = HealthStatus.DEGRADED
            elif cpu_percent < 95:
                status = HealthStatus.UNHEALTHY
            else:
                status = HealthStatus.CRITICAL

            return HealthCheckResult(
                check_id="cpu_usage",
                status=status,
                message=f"CPU usage: {cpu_percent:.1f}% (load avg: {load_avg[0]:.2f})",
                response_time=1.0,
                timestamp=datetime.utcnow(),
                details={
                    "cpu_percent": round(cpu_percent, 2),
                    "load_avg_1m": round(load_avg[0], 2),
                    "load_avg_5m": round(load_avg[1], 2),
                    "load_avg_15m": round(load_avg[2], 2),
                    "cpu_count": psutil.cpu_count()
                },
                metrics={
                    "cpu_percent": cpu_percent,
                    "load_avg_1m": load_avg[0]
                }
            )

        except Exception as e:
            return HealthCheckResult(
                check_id="cpu_usage",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check CPU usage: {str(e)}",
                response_time=0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def _check_network_connectivity(self) -> HealthCheckResult:
        """检查网络连接"""
        try:
            # 检查DNS解析
            start_time = time.time()
            socket.gethostbyname('google.com')
            dns_time = time.time() - start_time

            # 检查外部连接
            start_time = time.time()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection('google.com', 80),
                timeout=5
            )
            connection_time = time.time() - start_time
            writer.close()
            await writer.wait_closed()

            total_time = dns_time + connection_time

            # 确定状态
            if total_time < 2:
                status = HealthStatus.HEALTHY
            elif total_time < 5:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY

            return HealthCheckResult(
                check_id="network_connectivity",
                status=status,
                message=f"Network connectivity OK (DNS: {dns_time:.3f}s, Connection: {connection_time:.3f}s)",
                response_time=total_time,
                timestamp=datetime.utcnow(),
                details={
                    "dns_resolution_time": round(dns_time, 3),
                    "connection_time": round(connection_time, 3),
                    "total_time": round(total_time, 3)
                },
                metrics={
                    "dns_time": dns_time,
                    "connection_time": connection_time
                }
            )

        except Exception as e:
            return HealthCheckResult(
                check_id="network_connectivity",
                status=HealthStatus.CRITICAL,
                message=f"Network connectivity check failed: {str(e)}",
                response_time=0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def _check_external_apis(self) -> HealthCheckResult:
        """检查外部API服务"""
        try:
            # 检查OpenRouter API
            if settings.openrouter_api_key:
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bearer {settings.openrouter_api_key}"}
                    async with session.get(
                        "https://openrouter.ai/api/v1/models",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        response_time = time.time() - start_time

                        if response.status == 200:
                            status = HealthStatus.HEALTHY if response_time < 5 else HealthStatus.DEGRADED
                            message = f"OpenRouter API OK (response time: {response_time:.3f}s)"
                        else:
                            status = HealthStatus.UNHEALTHY
                            message = f"OpenRouter API returned status {response.status}"

                        return HealthCheckResult(
                            check_id="external_apis",
                            status=status,
                            message=message,
                            response_time=response_time,
                            timestamp=datetime.utcnow(),
                            details={
                                "openrouter_status": response.status,
                                "response_time": round(response_time, 3)
                            },
                            metrics={"openrouter_response_time": response_time}
                        )
            else:
                return HealthCheckResult(
                    check_id="external_apis",
                    status=HealthStatus.UNKNOWN,
                    message="OpenRouter API key not configured",
                    response_time=0,
                    timestamp=datetime.utcnow()
                )

        except Exception as e:
            return HealthCheckResult(
                check_id="external_apis",
                status=HealthStatus.CRITICAL,
                message=f"External API check failed: {str(e)}",
                response_time=0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def _check_file_system(self) -> HealthCheckResult:
        """检查文件系统"""
        try:
            # 检查关键目录
            critical_dirs = ['/tmp', '/var/log', '.', 'backend']
            dir_results = {}

            for dir_path in critical_dirs:
                try:
                    import os
                    if os.path.exists(dir_path):
                        # 检查读写权限
                        test_file = os.path.join(dir_path, '.health_check_test')

                        # 测试写入
                        with open(test_file, 'w') as f:
                            f.write('test')

                        # 测试读取
                        with open(test_file, 'r') as f:
                            content = f.read()

                        # 清理
                        os.remove(test_file)

                        dir_results[dir_path] = "OK"
                    else:
                        dir_results[dir_path] = "NOT_FOUND"
                except Exception as e:
                    dir_results[dir_path] = f"ERROR: {str(e)}"

            # 检查inode使用（Linux系统）
            inode_info = {}
            try:
                statvfs = os.statvfs('.')
                total_inodes = statvfs.f_files
                free_inodes = statvfs.f_ffree
                inode_usage = ((total_inodes - free_inodes) / total_inodes) * 100
                inode_info = {
                    "total_inodes": total_inodes,
                    "free_inodes": free_inodes,
                    "usage_percent": round(inode_usage, 2)
                }
            except:
                pass

            return HealthCheckResult(
                check_id="file_system",
                status=HealthStatus.HEALTHY,
                message="File system checks passed",
                response_time=0.2,
                timestamp=datetime.utcnow(),
                details={
                    "directory_checks": dir_results,
                    "inode_info": inode_info
                }
            )

        except Exception as e:
            return HealthCheckResult(
                check_id="file_system",
                status=HealthStatus.CRITICAL,
                message=f"File system check failed: {str(e)}",
                response_time=0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def _check_process_health(self) -> HealthCheckResult:
        """检查进程健康"""
        try:
            current_process = psutil.Process()

            # 获取进程信息
            process_info = {
                "pid": current_process.pid,
                "name": current_process.name(),
                "status": current_process.status(),
                "create_time": datetime.fromtimestamp(current_process.create_time()).isoformat(),
                "cpu_percent": current_process.cpu_percent(),
                "memory_percent": current_process.memory_percent(),
                "num_threads": current_process.num_threads(),
                "open_files": len(current_process.open_files()),
                "connections": len(current_process.connections())
            }

            # 检查进程状态
            if current_process.status() in [psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING]:
                status = HealthStatus.HEALTHY
            elif current_process.status() == psutil.STATUS_ZOMBIE:
                status = HealthStatus.CRITICAL
            else:
                status = HealthStatus.DEGRADED

            return HealthCheckResult(
                check_id="process_health",
                status=status,
                message=f"Process {current_process.name()} is {current_process.status()}",
                response_time=0.1,
                timestamp=datetime.utcnow(),
                details=process_info,
                metrics={
                    "cpu_percent": process_info["cpu_percent"],
                    "memory_percent": process_info["memory_percent"],
                    "open_files": process_info["open_files"],
                    "connections": process_info["connections"]
                }
            )

        except Exception as e:
            return HealthCheckResult(
                check_id="process_health",
                status=HealthStatus.UNKNOWN,
                message=f"Process health check failed: {str(e)}",
                response_time=0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def _check_ssl_certificates(self) -> HealthCheckResult:
        """检查SSL证书"""
        try:
            import ssl
            import socket
            from datetime import datetime

            # 检查常用域名的SSL证书
            domains = ['google.com', 'github.com']
            cert_results = {}

            for domain in domains:
                try:
                    context = ssl.create_default_context()
                    with socket.create_connection((domain, 443), timeout=5) as sock:
                        with context.wrap_socket(sock, server_hostname=domain) as ssock:
                            cert = ssock.getpeercert()

                            if cert:
                                # 解析证书过期时间
                                expiry_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                                days_until_expiry = (expiry_date - datetime.utcnow()).days

                                cert_results[domain] = {
                                    "status": "OK",
                                    "expiry_date": expiry_date.isoformat(),
                                    "days_until_expiry": days_until_expiry,
                                    "issuer": cert.get('issuer', [{}])[0].get('organizationName', 'Unknown')
                                }
                            else:
                                cert_results[domain] = {"status": "NO_CERT"}
                except Exception as e:
                    cert_results[domain] = {"status": "ERROR", "error": str(e)}

            # 检查是否有即将过期的证书
            min_days = min([r.get("days_until_expiry", 999) for r in cert_results.values() if "days_until_expiry" in r], default=999)

            if min_days < 7:
                status = HealthStatus.CRITICAL
            elif min_days < 30:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY

            return HealthCheckResult(
                check_id="ssl_certificates",
                status=status,
                message=f"SSL certificates checked (min days until expiry: {min_days})",
                response_time=2.0,
                timestamp=datetime.utcnow(),
                details=cert_results,
                metrics={"min_days_until_expiry": min_days}
            )

        except Exception as e:
            return HealthCheckResult(
                check_id="ssl_certificates",
                status=HealthStatus.UNKNOWN,
                message=f"SSL certificate check failed: {str(e)}",
                response_time=0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def _check_security_headers(self) -> HealthCheckResult:
        """检查安全头"""
        try:
            # 检查本地服务的安全头
            test_url = "http://localhost:8001/api/v1/status"

            async with aiohttp.ClientSession() as session:
                async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    headers = dict(response.headers)

                    # 检查重要的安全头
                    security_headers = {
                        "X-Content-Type-Options": headers.get("X-Content-Type-Options"),
                        "X-Frame-Options": headers.get("X-Frame-Options"),
                        "X-XSS-Protection": headers.get("X-XSS-Protection"),
                        "Strict-Transport-Security": headers.get("Strict-Transport-Security"),
                        "Content-Security-Policy": headers.get("Content-Security-Policy")
                    }

                    missing_headers = [h for h, v in security_headers.items() if not v]

                    if len(missing_headers) == 0:
                        status = HealthStatus.HEALTHY
                        message = "All security headers present"
                    elif len(missing_headers) <= 2:
                        status = HealthStatus.DEGRADED
                        message = f"Missing security headers: {', '.join(missing_headers)}"
                    else:
                        status = HealthStatus.UNHEALTHY
                        message = f"Many security headers missing: {', '.join(missing_headers)}"

                    return HealthCheckResult(
                        check_id="security_headers",
                        status=status,
                        message=message,
                        response_time=1.0,
                        timestamp=datetime.utcnow(),
                        details={
                            "security_headers": security_headers,
                            "missing_headers": missing_headers
                        },
                        metrics={"missing_headers_count": len(missing_headers)}
                    )

        except Exception as e:
            return HealthCheckResult(
                check_id="security_headers",
                status=HealthStatus.UNKNOWN,
                message=f"Security headers check failed: {str(e)}",
                response_time=0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def _check_log_system(self) -> HealthCheckResult:
        """检查日志系统"""
        try:
            # 检查日志目录
            import os
            log_dir = "logs"

            if not os.path.exists(log_dir):
                return HealthCheckResult(
                    check_id="log_system",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Log directory not found: {log_dir}",
                    response_time=0.1,
                    timestamp=datetime.utcnow()
                )

            # 检查日志文件
            log_files = []
            try:
                for file in os.listdir(log_dir):
                    if file.endswith('.log'):
                        file_path = os.path.join(log_dir, file)
                        stat = os.stat(file_path)
                        log_files.append({
                            "name": file,
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
            except Exception as e:
                return HealthCheckResult(
                    check_id="log_system",
                    status=HealthStatus.DEGRADED,
                    message=f"Failed to read log directory: {str(e)}",
                    response_time=0.2,
                    timestamp=datetime.utcnow()
                )

            # 检查磁盘空间
            disk_usage = psutil.disk_usage(log_dir)
            available_space_gb = disk_usage.free / (1024**3)

            status = HealthStatus.HEALTHY
            if available_space_gb < 1:
                status = HealthStatus.CRITICAL
            elif available_space_gb < 5:
                status = HealthStatus.UNHEALTHY

            return HealthCheckResult(
                check_id="log_system",
                status=status,
                message=f"Log system OK ({len(log_files)} log files, {available_space_gb:.1f}GB free)",
                response_time=0.3,
                timestamp=datetime.utcnow(),
                details={
                    "log_directory": log_dir,
                    "log_files": log_files,
                    "available_space_gb": round(available_space_gb, 2)
                },
                metrics={
                    "log_files_count": len(log_files),
                    "available_space_gb": available_space_gb
                }
            )

        except Exception as e:
            return HealthCheckResult(
                check_id="log_system",
                status=HealthStatus.UNKNOWN,
                message=f"Log system check failed: {str(e)}",
                response_time=0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def _check_cache_performance(self) -> HealthCheckResult:
        """检查缓存性能"""
        try:
            if not settings.redis_url:
                return HealthCheckResult(
                    check_id="cache_performance",
                    status=HealthStatus.UNKNOWN,
                    message="Redis not configured for caching",
                    response_time=0,
                    timestamp=datetime.utcnow()
                )

            redis_client = redis.from_url(settings.redis_url)

            # 测试缓存性能
            test_key = "health_check_cache_test"
            test_value = f"test_value_{int(time.time())}"

            # 测试写入性能
            start_time = time.time()
            redis_client.set(test_key, test_value, ex=60)
            write_time = time.time() - start_time

            # 测试读取性能
            start_time = time.time()
            retrieved_value = redis_client.get(test_key)
            read_time = time.time() - start_time

            # 清理
            redis_client.delete(test_key)

            # 获取Redis信息
            info = redis_client.info()
            hit_rate = info.get("keyspace_hits", 0) / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100

            # 确定状态
            avg_time = (write_time + read_time) / 2
            if avg_time < 0.01 and hit_rate > 50:
                status = HealthStatus.HEALTHY
            elif avg_time < 0.05 and hit_rate > 20:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY

            return HealthCheckResult(
                check_id="cache_performance",
                status=status,
                message=f"Cache performance OK (write: {write_time:.4f}s, read: {read_time:.4f}s, hit rate: {hit_rate:.1f}%)",
                response_time=avg_time,
                timestamp=datetime.utcnow(),
                details={
                    "write_time": round(write_time, 4),
                    "read_time": round(read_time, 4),
                    "hit_rate": round(hit_rate, 2),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory": info.get("used_memory_human")
                },
                metrics={
                    "write_time": write_time,
                    "read_time": read_time,
                    "hit_rate": hit_rate
                }
            )

        except Exception as e:
            return HealthCheckResult(
                check_id="cache_performance",
                status=HealthStatus.CRITICAL,
                message=f"Cache performance check failed: {str(e)}",
                response_time=0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def _check_database_performance(self) -> HealthCheckResult:
        """检查数据库性能"""
        try:
            db = next(get_db())

            # 测试查询性能
            start_time = time.time()
            result = db.execute("SELECT COUNT(*) FROM sqlite_master")
            result.fetchone()
            query_time = time.time() - start_time

            # 测试连接池
            pool_status = {
                "checked": True,
                "query_time": query_time
            }

            # 确定状态
            if query_time < 0.1:
                status = HealthStatus.HEALTHY
            elif query_time < 0.5:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY

            return HealthCheckResult(
                check_id="database_performance",
                status=status,
                message=f"Database performance OK (query time: {query_time:.3f}s)",
                response_time=query_time,
                timestamp=datetime.utcnow(),
                details=pool_status,
                metrics={"query_time": query_time}
            )

        except Exception as e:
            return HealthCheckResult(
                check_id="database_performance",
                status=HealthStatus.CRITICAL,
                message=f"Database performance check failed: {str(e)}",
                response_time=0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    def register_check(self, check_id: str, check_function: Callable):
        """注册自定义检查函数"""
        self.check_functions[check_id] = check_function


class DeepHealthChecker:
    """深度健康检查器"""

    def __init__(self):
        self.executor = HealthCheckExecutor()
        self.health_checks: Dict[str, HealthCheck] = {}
        self.component_health: Dict[str, ComponentHealth] = {}
        self.check_history: List[HealthCheckResult] = []
        self.max_history = 10000
        self._register_default_checks()

    def _register_default_checks(self):
        """注册默认健康检查"""
        default_checks = [
            HealthCheck(
                check_id="database_connection",
                name="Database Connection",
                description="Check database connectivity and basic query performance",
                check_type=CheckType.BASIC,
                severity=CheckSeverity.HIGH,
                timeout=5.0,
                interval=60,
                tags=["database", "critical"]
            ),
            HealthCheck(
                check_id="redis_connection",
                name="Redis Connection",
                description="Check Redis connectivity and performance",
                check_type=CheckType.BASIC,
                severity=CheckSeverity.MEDIUM,
                timeout=3.0,
                interval=60,
                tags=["cache", "redis"]
            ),
            HealthCheck(
                check_id="disk_space",
                name="Disk Space",
                description="Check disk space usage",
                check_type=CheckType.BASIC,
                severity=CheckSeverity.HIGH,
                timeout=2.0,
                interval=300,
                tags=["storage", "system"]
            ),
            HealthCheck(
                check_id="memory_usage",
                name="Memory Usage",
                description="Check system memory usage",
                check_type=CheckType.BASIC,
                severity=CheckSeverity.MEDIUM,
                timeout=1.0,
                interval=60,
                tags=["system", "performance"]
            ),
            HealthCheck(
                check_id="cpu_usage",
                name="CPU Usage",
                description="Check CPU usage and load",
                check_type=CheckType.BASIC,
                severity=CheckSeverity.MEDIUM,
                timeout=2.0,
                interval=60,
                tags=["system", "performance"]
            ),
            HealthCheck(
                check_id="network_connectivity",
                name="Network Connectivity",
                description="Check network connectivity to external services",
                check_type=CheckType.BASIC,
                severity=CheckSeverity.MEDIUM,
                timeout=10.0,
                interval=300,
                tags=["network", "external"]
            ),
            HealthCheck(
                check_id="external_apis",
                name="External APIs",
                description="Check connectivity to external API services",
                check_type=CheckType.INTEGRATION,
                severity=CheckSeverity.HIGH,
                timeout=15.0,
                interval=300,
                dependencies=["network_connectivity"],
                tags=["external", "api"]
            ),
            HealthCheck(
                check_id="file_system",
                name="File System",
                description="Check file system integrity and permissions",
                check_type=CheckType.DEEP,
                severity=CheckSeverity.MEDIUM,
                timeout=5.0,
                interval=600,
                tags=["system", "storage"]
            ),
            HealthCheck(
                check_id="process_health",
                name="Process Health",
                description="Check application process health",
                check_type=CheckType.BASIC,
                severity=CheckSeverity.HIGH,
                timeout=2.0,
                interval=60,
                tags=["application", "process"]
            ),
            HealthCheck(
                check_id="ssl_certificates",
                name="SSL Certificates",
                description="Check SSL certificate validity",
                check_type=CheckType.SECURITY,
                severity=CheckSeverity.LOW,
                timeout=10.0,
                interval=3600,
                dependencies=["network_connectivity"],
                tags=["security", "ssl"]
            ),
            HealthCheck(
                check_id="security_headers",
                name="Security Headers",
                description="Check security headers configuration",
                check_type=CheckType.SECURITY,
                severity=CheckSeverity.LOW,
                timeout=5.0,
                interval=600,
                tags=["security", "web"]
            ),
            HealthCheck(
                check_id="log_system",
                name="Log System",
                description="Check logging system functionality",
                check_type=CheckType.DEEP,
                severity=CheckSeverity.MEDIUM,
                timeout=3.0,
                interval=300,
                tags=["logging", "system"]
            ),
            HealthCheck(
                check_id="cache_performance",
                name="Cache Performance",
                description="Check cache system performance",
                check_type=CheckType.PERFORMANCE,
                severity=CheckSeverity.MEDIUM,
                timeout=5.0,
                interval=300,
                dependencies=["redis_connection"],
                tags=["performance", "cache"]
            ),
            HealthCheck(
                check_id="database_performance",
                name="Database Performance",
                description="Check database query performance",
                check_type=CheckType.PERFORMANCE,
                severity=CheckSeverity.MEDIUM,
                timeout=5.0,
                interval=300,
                dependencies=["database_connection"],
                tags=["performance", "database"]
            )
        ]

        for check in default_checks:
            self.health_checks[check.check_id] = check
            self.component_health[check.check_id] = ComponentHealth(
                component_id=check.check_id,
                name=check.name,
                status=HealthStatus.UNKNOWN,
                last_check=datetime.utcnow(),
                uptime_percentage=0.0,
                total_checks=0,
                successful_checks=0,
                failed_checks=0,
                avg_response_time=0.0,
                dependencies=check.dependencies
            )

    async def run_check(self, check_id: str) -> Optional[HealthCheckResult]:
        """运行单个健康检查"""
        health_check = self.health_checks.get(check_id)
        if not health_check:
            logger.error(f"Health check not found: {check_id}")
            return None

        if not health_check.enabled:
            logger.debug(f"Health check disabled: {check_id}")
            return None

        # 检查依赖
        for dependency in health_check.dependencies:
            dep_health = self.component_health.get(dependency)
            if not dep_health or not dep_health.is_healthy:
                logger.warning(f"Skipping check {check_id} due to unhealthy dependency: {dependency}")
                return HealthCheckResult(
                    check_id=check_id,
                    status=HealthStatus.UNKNOWN,
                    message=f"Skipped due to unhealthy dependency: {dependency}",
                    response_time=0,
                    timestamp=datetime.utcnow()
                )

        # 执行检查
        result = await self.executor.execute_check(health_check)

        # 更新组件健康状态
        await self._update_component_health(check_id, result)

        # 记录历史
        self.check_history.append(result)
        if len(self.check_history) > self.max_history:
            self.check_history = self.check_history[-self.max_history:]

        return result

    async def run_all_checks(self, check_type: Optional[CheckType] = None) -> Dict[str, HealthCheckResult]:
        """运行所有健康检查"""
        results = {}

        # 过滤检查类型
        checks_to_run = self.health_checks.values()
        if check_type:
            checks_to_run = [c for c in checks_to_run if c.check_type == check_type]

        # 并发执行检查
        tasks = []
        for health_check in checks_to_run:
            if health_check.enabled:
                task = asyncio.create_task(self.run_check(health_check.check_id))
                tasks.append(task)

        if tasks:
            check_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in check_results:
                if isinstance(result, Exception):
                    logger.error(f"Health check failed: {result}")
                elif result:
                    results[result.check_id] = result

        return results

    async def _update_component_health(self, check_id: str, result: HealthCheckResult):
        """更新组件健康状态"""
        component = self.component_health.get(check_id)
        if not component:
            return

        component.last_check = result.timestamp
        component.total_checks += 1

        if result.is_healthy:
            component.successful_checks += 1
            component.status = result.status
        else:
            component.failed_checks += 1
            # 如果连续失败次数过多，降级状态
            if component.failed_checks > 5:
                if component.failed_checks > 20:
                    component.status = HealthStatus.CRITICAL
                else:
                    component.status = HealthStatus.UNHEALTHY

        # 更新平均响应时间
        if component.total_checks == 1:
            component.avg_response_time = result.response_time
        else:
            component.avg_response_time = (
                (component.avg_response_time * (component.total_checks - 1) + result.response_time) /
                component.total_checks
            )

        # 更新最后错误
        if not result.is_healthy and result.error:
            component.last_error = result.error

        # 计算正常运行时间（简化计算）
        if component.total_checks > 0:
            component.uptime_percentage = component.success_rate

    async def get_overall_health(self) -> Dict[str, Any]:
        """获取整体健康状态"""
        if not self.component_health:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "message": "No health checks configured",
                "timestamp": datetime.utcnow().isoformat(),
                "components": {}
            }

        # 统计各状态组件数量
        status_counts = {}
        for component in self.component_health.values():
            status = component.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # 确定整体状态
        if status_counts.get(HealthStatus.CRITICAL.value, 0) > 0:
            overall_status = HealthStatus.CRITICAL
        elif status_counts.get(HealthStatus.UNHEALTHY.value, 0) > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif status_counts.get(HealthStatus.DEGRADED.value, 0) > 0:
            overall_status = HealthStatus.DEGRADED
        elif status_counts.get(HealthStatus.HEALTHY.value, 0) > 0:
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN

        # 计算整体指标
        total_checks = sum(c.total_checks for c in self.component_health.values())
        successful_checks = sum(c.successful_checks for c in self.component_health.values())
        avg_response_time = sum(c.avg_response_time for c in self.component_health.values()) / len(self.component_health)

        return {
            "status": overall_status.value,
            "message": f"System is {overall_status.value} ({status_counts})",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {cid: comp.to_dict() for cid, comp in self.component_health.items()},
            "summary": {
                "total_components": len(self.component_health),
                "status_counts": status_counts,
                "overall_success_rate": (successful_checks / total_checks * 100) if total_checks > 0 else 0,
                "avg_response_time": round(avg_response_time, 3)
            }
        }

    async def get_health_history(
        self,
        hours: int = 24,
        check_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取健康检查历史"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        history = self.check_history
        if check_id:
            history = [h for h in history if h.check_id == check_id]

        history = [h for h in history if h.timestamp >= cutoff_time]

        return [h.to_dict() for h in history]

    async def get_component_health(self, component_id: str) -> Optional[Dict[str, Any]]:
        """获取组件健康状态"""
        component = self.component_health.get(component_id)
        return component.to_dict() if component else None

    def add_health_check(self, health_check: HealthCheck):
        """添加健康检查"""
        self.health_checks[health_check.check_id] = health_check

        # 初始化组件健康状态
        if health_check.check_id not in self.component_health:
            self.component_health[health_check.check_id] = ComponentHealth(
                component_id=health_check.check_id,
                name=health_check.name,
                status=HealthStatus.UNKNOWN,
                last_check=datetime.utcnow(),
                uptime_percentage=0.0,
                total_checks=0,
                successful_checks=0,
                failed_checks=0,
                avg_response_time=0.0,
                dependencies=health_check.dependencies
            )

    def remove_health_check(self, check_id: str) -> bool:
        """移除健康检查"""
        if check_id in self.health_checks:
            del self.health_checks[check_id]
        if check_id in self.component_health:
            del self.component_health[check_id]
        return True

    def enable_check(self, check_id: str, enabled: bool = True):
        """启用/禁用健康检查"""
        if check_id in self.health_checks:
            self.health_checks[check_id].enabled = enabled

    async def start_continuous_monitoring(self):
        """启动持续监控"""
        logger.info("Starting continuous health monitoring...")

        async def monitoring_loop():
            while True:
                try:
                    # 运行所有基础检查
                    await self.run_all_checks(CheckType.BASIC)

                    # 等待下一次检查
                    await asyncio.sleep(60)  # 每分钟检查一次基础健康

                except Exception as e:
                    logger.error(f"Health monitoring loop error: {e}")
                    await asyncio.sleep(60)

        asyncio.create_task(monitoring_loop())

        # 启动深度检查（每15分钟）
        async def deep_check_loop():
            while True:
                try:
                    await self.run_all_checks(CheckType.DEEP)
                    await asyncio.sleep(900)  # 每15分钟
                except Exception as e:
                    logger.error(f"Deep health check loop error: {e}")
                    await asyncio.sleep(900)

        asyncio.create_task(deep_check_loop())

        logger.info("Continuous health monitoring started")


# 全局深��健康检查器
deep_health_checker = DeepHealthChecker()


async def get_deep_health_checker() -> DeepHealthChecker:
    """获取深度健康检查器"""
    return deep_health_checker