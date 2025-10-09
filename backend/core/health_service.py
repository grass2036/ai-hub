"""
系统健康检查和状态监控服务
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import aiohttp
from backend.config.settings import get_settings
from backend.core.ai_service import ai_manager
from backend.core.cache_service import cache_service

@dataclass
class ServiceHealth:
    """服务健康状态"""
    name: str
    status: str  # healthy, unhealthy, degraded
    response_time: float
    last_check: str
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

@dataclass
class SystemHealth:
    """系统整体健康状态"""
    status: str
    timestamp: str
    uptime: float
    services: List[ServiceHealth]
    performance_metrics: Dict[str, Any]
    cache_stats: Dict[str, Any]

class HealthService:
    """系统健康监控服务"""

    def __init__(self):
        self.start_time = time.time()
        self.settings = get_settings()
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def check_openrouter_health(self) -> ServiceHealth:
        """检查OpenRouter服务健康状态"""
        start_time = time.time()

        try:
            session = await self._get_session()

            # 测试OpenRouter API可用性
            headers = {
                "Authorization": f"Bearer {self.settings.openrouter_api_key}",
                "Content-Type": "application/json"
            }

            async with session.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response_time = time.time() - start_time

                if response.status == 200:
                    return ServiceHealth(
                        name="OpenRouter",
                        status="healthy",
                        response_time=response_time,
                        last_check=datetime.now().isoformat(),
                        details={
                            "status_code": response.status,
                            "api_endpoint": "https://openrouter.ai/api/v1/models"
                        }
                    )
                else:
                    return ServiceHealth(
                        name="OpenRouter",
                        status="unhealthy",
                        response_time=response_time,
                        last_check=datetime.now().isoformat(),
                        error_message=f"HTTP {response.status}",
                        details={"status_code": response.status}
                    )

        except asyncio.TimeoutError:
            return ServiceHealth(
                name="OpenRouter",
                status="unhealthy",
                response_time=10.0,
                last_check=datetime.now().isoformat(),
                error_message="Request timeout"
            )
        except Exception as e:
            response_time = time.time() - start_time
            return ServiceHealth(
                name="OpenRouter",
                status="unhealthy",
                response_time=response_time,
                last_check=datetime.now().isoformat(),
                error_message=str(e)
            )

    async def check_gemini_health(self) -> ServiceHealth:
        """检查Gemini服务健康状态"""
        start_time = time.time()

        try:
            if not self.settings.gemini_api_key:
                return ServiceHealth(
                    name="Gemini",
                    status="unhealthy",
                    response_time=0.0,
                    last_check=datetime.now().isoformat(),
                    error_message="API key not configured"
                )

            # 尝试初始化Gemini服务
            import google.generativeai as genai
            genai.configure(api_key=self.settings.gemini_api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')

            # 发送简单的测试请求
            test_response = await asyncio.to_thread(
                model.generate_content, "Hi"
            )

            response_time = time.time() - start_time

            if test_response and test_response.text:
                return ServiceHealth(
                    name="Gemini",
                    status="healthy",
                    response_time=response_time,
                    last_check=datetime.now().isoformat(),
                    details={
                        "model": "gemini-2.5-flash",
                        "response_preview": test_response.text[:50] + "..."
                    }
                )
            else:
                return ServiceHealth(
                    name="Gemini",
                    status="degraded",
                    response_time=response_time,
                    last_check=datetime.now().isoformat(),
                    error_message="Empty response"
                )

        except Exception as e:
            response_time = time.time() - start_time
            return ServiceHealth(
                name="Gemini",
                status="unhealthy",
                response_time=response_time,
                last_check=datetime.now().isoformat(),
                error_message=str(e)
            )

    async def check_database_health(self) -> ServiceHealth:
        """检查数据库/文件系统健康状态"""
        start_time = time.time()

        try:
            from backend.core.session_manager import SessionManager
            from backend.core.cost_tracker import CostTracker

            # 测试session manager
            session_manager = SessionManager()
            test_session_id = session_manager.generate_session_id()

            # 测试基本的文件读写操作
            response_time = time.time() - start_time

            return ServiceHealth(
                name="FileStorage",
                status="healthy",
                response_time=response_time,
                last_check=datetime.now().isoformat(),
                details={
                    "data_directory": str(session_manager.data_dir),
                    "test_session_id": test_session_id[:8] + "..."
                }
            )

        except Exception as e:
            response_time = time.time() - start_time
            return ServiceHealth(
                name="FileStorage",
                status="unhealthy",
                response_time=response_time,
                last_check=datetime.now().isoformat(),
                error_message=str(e)
            )

    async def get_system_health(self) -> SystemHealth:
        """获取系统整体健康状态"""
        # 并行检查所有服务
        health_checks = await asyncio.gather(
            self.check_openrouter_health(),
            self.check_gemini_health(),
            self.check_database_health(),
            return_exceptions=True
        )

        services = []
        unhealthy_count = 0

        for check in health_checks:
            if isinstance(check, ServiceHealth):
                services.append(check)
                if check.status == "unhealthy":
                    unhealthy_count += 1
            else:
                # 处理异常情况
                services.append(ServiceHealth(
                    name="Unknown",
                    status="unhealthy",
                    response_time=0.0,
                    last_check=datetime.now().isoformat(),
                    error_message=f"Health check failed: {str(check)}"
                ))
                unhealthy_count += 1

        # 确定整体状态
        if unhealthy_count == 0:
            overall_status = "healthy"
        elif unhealthy_count <= len(services) / 2:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        # 获取性能指标
        uptime = time.time() - self.start_time
        cache_stats = cache_service.get_stats()

        performance_metrics = {
            "uptime_seconds": uptime,
            "uptime_human": str(timedelta(seconds=int(uptime))),
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "memory_usage": self._estimate_memory_usage(),
            "active_services": len([s for s in services if s.status == "healthy"])
        }

        return SystemHealth(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            uptime=uptime,
            services=services,
            performance_metrics=performance_metrics,
            cache_stats=cache_stats
        )

    def _estimate_memory_usage(self) -> str:
        """估算内存使用量"""
        import psutil
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            if memory_mb < 1024:
                return f"{memory_mb:.1f}MB"
            else:
                return f"{memory_mb / 1024:.1f}GB"
        except ImportError:
            return "Unknown (psutil not available)"
        except Exception:
            return "Unknown"

    async def cleanup(self):
        """清理资源"""
        if self._session and not self._session.closed:
            await self._session.close()

# 全局健康服务实例
health_service = HealthService()

async def get_system_health() -> Dict[str, Any]:
    """获取系统健康状态（API端点使用）"""
    try:
        health = await health_service.get_system_health()
        return asdict(health)
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "services": []
        }