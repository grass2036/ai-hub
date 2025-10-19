"""
负载均衡器
Week 6 Day 5: 负载均衡和高可用配置

提供多种负载均衡策略和智能流量分发
"""

import asyncio
import time
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import aiohttp
import redis

class LoadBalancingStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    IP_HASH = "ip_hash"
    URL_HASH = "url_hash"
    RANDOM = "random"
    CONSISTENT_HASH = "consistent_hash"

class BackendStatus(Enum):
    """后端服务器状态"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    MAINTENANCE = "maintenance"

@dataclass
class BackendServer:
    """后端服务器"""
    id: str
    host: str
    port: int
    weight: int = 1
    max_connections: int = 1000
    current_connections: int = 0
    status: BackendStatus = BackendStatus.HEALTHY
    response_time: float = 0.0
    success_rate: float = 1.0
    last_health_check: Optional[datetime] = None
    total_requests: int = 0
    failed_requests: int = 0
    metadata: Dict[str, Any] = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def is_available(self) -> bool:
        return (self.status == BackendStatus.HEALTHY and
                self.current_connections < self.max_connections)

    def update_stats(self, success: bool, response_time: float) -> None:
        """更新服务器统计信息"""
        self.total_requests += 1
        if not success:
            self.failed_requests += 1

        # 更新响应时间（指数移动平均）
        alpha = 0.3
        self.response_time = alpha * response_time + (1 - alpha) * self.response_time

        # 更新成功率
        self.success_rate = (self.total_requests - self.failed_requests) / self.total_requests

@dataclass
class LoadBalancingConfig:
    """负载均衡配置"""
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    health_check_interval: int = 30
    health_check_timeout: int = 5
    health_check_path: str = "/health"
    max_retries: int = 3
    retry_delay: float = 1.0
    sticky_sessions: bool = False
    session_affinity_timeout: int = 3600
    connection_timeout: int = 30
    read_timeout: int = 60

class LoadBalancer:
    """负载均衡器"""

    def __init__(self, config: LoadBalancingConfig):
        self.config = config
        self.backends: Dict[str, BackendServer] = {}
        self.current_index = 0
        self.session_affinity: Dict[str, str] = {}  # session_id -> backend_id
        self.redis_client: Optional[redis.Redis] = None
        self._lock = asyncio.Lock()

        # 统计信息
        self.total_requests = 0
        self.total_failures = 0

    async def initialize(self, redis_client: Optional[redis.Redis] = None) -> None:
        """初始化负载均衡器"""
        self.redis_client = redis_client

        # 启动健康检查
        asyncio.create_task(self._health_check_loop())

        # 启动会话亲和性清理
        asyncio.create_task(self._session_cleanup_loop())

    def add_backend(self, backend: BackendServer) -> None:
        """添加后端服务器"""
        self.backends[backend.id] = backend
        logging.info(f"Added backend server: {backend.id} ({backend.url})")

    def remove_backend(self, backend_id: str) -> bool:
        """移除后端服务器"""
        if backend_id in self.backends:
            del self.backends[backend_id]
            logging.info(f"Removed backend server: {backend_id}")
            return True
        return False

    async def select_backend(self, request_context: Dict[str, Any] = None) -> Optional[BackendServer]:
        """选择后端服务器"""
        if not self.backends:
            return None

        # 过滤可用的后端服务器
        available_backends = [
            backend for backend in self.backends.values()
            if backend.is_available
        ]

        if not available_backends:
            return None

        # 根据策略选择后端
        if self.config.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return await self._round_robin_select(available_backends)
        elif self.config.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return await self._weighted_round_robin_select(available_backends)
        elif self.config.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return await self._least_connections_select(available_backends)
        elif self.config.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            return await self._least_response_time_select(available_backends)
        elif self.config.strategy == LoadBalancingStrategy.IP_HASH:
            return await self._ip_hash_select(available_backends, request_context)
        elif self.config.strategy == LoadBalancingStrategy.URL_HASH:
            return await self._url_hash_select(available_backends, request_context)
        elif self.config.strategy == LoadBalancingStrategy.RANDOM:
            return await self._random_select(available_backends)
        elif self.config.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
            return await self._consistent_hash_select(available_backends, request_context)
        else:
            return available_backends[0]

    async def _round_robin_select(self, backends: List[BackendServer]) -> BackendServer:
        """轮询选择"""
        async with self._lock:
            backend = backends[self.current_index % len(backends)]
            self.current_index += 1
            return backend

    async def _weighted_round_robin_select(self, backends: List[BackendServer]) -> BackendServer:
        """加权轮询选择"""
        total_weight = sum(backend.weight for backend in backends)
        if total_weight == 0:
            return backends[0]

        # 计算累积权重
        cumulative_weights = []
        current_weight = 0
        for backend in backends:
            current_weight += backend.weight
            cumulative_weights.append((backend, current_weight))

        # 随机选择
        random_weight = random.randint(1, total_weight)
        for backend, cumulative_weight in cumulative_weights:
            if random_weight <= cumulative_weight:
                return backend

        return backends[-1]

    async def _least_connections_select(self, backends: List[BackendServer]) -> BackendServer:
        """最少连接选择"""
        return min(backends, key=lambda b: b.current_connections)

    async def _least_response_time_select(self, backends: List[BackendServer]) -> BackendServer:
        """最短响应时间选择"""
        # 只考虑成功率 > 80% 的服务器
        healthy_backends = [b for b in backends if b.success_rate > 0.8]
        if not healthy_backends:
            return min(backends, key=lambda b: b.response_time)

        return min(healthy_backends, key=lambda b: b.response_time)

    async def _ip_hash_select(self, backends: List[BackendServer], context: Dict[str, Any]) -> BackendServer:
        """IP哈希选择"""
        client_ip = context.get("client_ip", "127.0.0.1")
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        backend_index = hash_value % len(backends)
        return backends[backend_index]

    async def _url_hash_select(self, backends: List[BackendServer], context: Dict[str, Any]) -> BackendServer:
        """URL哈希选择"""
        url = context.get("url", "/")
        hash_value = int(hashlib.md5(url.encode()).hexdigest(), 16)
        backend_index = hash_value % len(backends)
        return backends[backend_index]

    async def _random_select(self, backends: List[BackendServer]) -> BackendServer:
        """随机选择"""
        return random.choice(backends)

    async def _consistent_hash_select(self, backends: List[BackendServer], context: Dict[str, Any]) -> BackendServer:
        """一致性哈希选择"""
        # 简化的一致性哈希实现
        identifier = context.get("session_id") or context.get("client_ip", "127.0.0.1")
        hash_value = int(hashlib.sha256(identifier.encode()).hexdigest(), 16)
        backend_index = hash_value % len(backends)
        return backends[backend_index]

    async def make_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str] = None,
        data: Any = None,
        params: Dict[str, str] = None,
        request_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发起请求到后端服务器"""
        request_context = request_context or {}
        self.total_requests += 1

        # 检查会话亲和性
        if self.config.sticky_sessions:
            session_id = request_context.get("session_id")
            if session_id and session_id in self.session_affinity:
                backend_id = self.session_affinity[session_id]
                backend = self.backends.get(backend_id)
                if backend and backend.is_available:
                    return await self._make_request_to_backend(
                        backend, method, url, headers, data, params
                    )

        # 选择后端服务器
        backend = await self.select_backend(request_context)
        if not backend:
            raise Exception("No available backend servers")

        # 记录会话亲和性
        if self.config.sticky_sessions and request_context.get("session_id"):
            self.session_affinity[request_context["session_id"]] = backend.id

        # 发起请求
        try:
            backend.current_connections += 1
            result = await self._make_request_to_backend(
                backend, method, url, headers, data, params
            )
            return result
        finally:
            backend.current_connections -= 1

    async def _make_request_to_backend(
        self,
        backend: BackendServer,
        method: str,
        url: str,
        headers: Dict[str, str] = None,
        data: Any = None,
        params: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """向特定后端服务器发起请求"""
        start_time = time.time()
        last_exception = None

        for attempt in range(self.config.max_retries):
            try:
                # 构建完整URL
                full_url = f"{backend.url}{url}"

                # 发起HTTP请求
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(
                        connect=self.config.connection_timeout,
                        total=self.config.read_timeout
                    )
                ) as session:
                    async with session.request(
                        method,
                        full_url,
                        headers=headers,
                        json=data if isinstance(data, dict) else None,
                        params=params
                    ) as response:
                        response_time = time.time() - start_time
                        response_data = {
                            "status_code": response.status,
                            "headers": dict(response.headers),
                            "body": await response.text(),
                            "response_time": response_time,
                            "backend_id": backend.id,
                            "attempt": attempt + 1
                        }

                        # 更新服务器统计
                        success = 200 <= response.status < 400
                        backend.update_stats(success, response_time)

                        if success:
                            return response_data
                        else:
                            last_exception = Exception(f"HTTP {response.status}: {response_data['body']}")

            except Exception as e:
                last_exception = e
                backend.update_stats(False, time.time() - start_time)

                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)

        # 所有重试都失败
        self.total_failures += 1
        raise last_exception or Exception("Request failed after all retries")

    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.config.health_check_interval)
            except Exception as e:
                logging.error(f"Health check error: {str(e)}")
                await asyncio.sleep(self.config.health_check_interval)

    async def _perform_health_checks(self) -> None:
        """执行健康检查"""
        for backend in self.backends.values():
            try:
                is_healthy = await self._check_backend_health(backend)
                old_status = backend.status

                if is_healthy:
                    if backend.status == BackendStatus.UNHEALTHY:
                        backend.status = BackendStatus.HEALTHY
                        logging.info(f"Backend {backend.id} is now healthy")
                else:
                    if backend.status == BackendStatus.HEALTHY:
                        backend.status = BackendStatus.UNHEALTHY
                        logging.warning(f"Backend {backend.id} is now unhealthy")

                backend.last_health_check = datetime.now()

            except Exception as e:
                logging.error(f"Health check failed for backend {backend.id}: {str(e)}")
                backend.status = BackendStatus.UNHEALTHY

    async def _check_backend_health(self, backend: BackendServer) -> bool:
        """检查后端服务器健康状态"""
        try:
            health_url = f"{backend.url}{self.config.health_check_path}"

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.health_check_timeout)
            ) as session:
                async with session.get(health_url) as response:
                    return response.status == 200

        except Exception:
            return False

    async def _session_cleanup_loop(self) -> None:
        """会话亲和性清理循环"""
        while True:
            try:
                # 清理过期的会话亲和性记录
                current_time = datetime.now()
                expired_sessions = [
                    session_id for session_id, timestamp in self.session_affinity.items()
                    if isinstance(timestamp, datetime) and
                    (current_time - timestamp).seconds > self.config.session_affinity_timeout
                ]

                for session_id in expired_sessions:
                    del self.session_affinity[session_id]

                await asyncio.sleep(300)  # 每5分钟清理一次

            except Exception as e:
                logging.error(f"Session cleanup error: {str(e)}")
                await asyncio.sleep(300)

    def get_statistics(self) -> Dict[str, Any]:
        """获取负载均衡统计信息"""
        healthy_backends = len([
            b for b in self.backends.values() if b.status == BackendStatus.HEALTHY
        ])

        total_connections = sum(b.current_connections for b in self.backends.values())

        avg_response_time = 0
        if self.backends:
            response_times = [b.response_time for b in self.backends.values() if b.response_time > 0]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)

        return {
            "total_backends": len(self.backends),
            "healthy_backends": healthy_backends,
            "unhealthy_backends": len(self.backends) - healthy_backends,
            "total_connections": total_connections,
            "strategy": self.config.strategy.value,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "success_rate": (self.total_requests - self.total_failures) / max(self.total_requests, 1),
            "average_response_time": avg_response_time,
            "backends": {
                backend_id: {
                    "host": backend.host,
                    "port": backend.port,
                    "status": backend.status.value,
                    "connections": backend.current_connections,
                    "max_connections": backend.max_connections,
                    "response_time": backend.response_time,
                    "success_rate": backend.success_rate,
                    "total_requests": backend.total_requests,
                    "failed_requests": backend.failed_requests,
                    "weight": backend.weight,
                    "last_health_check": backend.last_health_check.isoformat() if backend.last_health_check else None
                }
                for backend_id, backend in self.backends.items()
            }
        }

    def update_backend_weight(self, backend_id: str, weight: int) -> bool:
        """更新后端服务器权重"""
        if backend_id in self.backends:
            self.backends[backend_id].weight = max(1, weight)
            logging.info(f"Updated weight for backend {backend_id} to {weight}")
            return True
        return False

    def set_backend_status(self, backend_id: str, status: BackendStatus) -> bool:
        """设置后端服务器状态"""
        if backend_id in self.backends:
            old_status = self.backends[backend_id].status
            self.backends[backend_id].status = status
            logging.info(f"Backend {backend_id} status changed from {old_status.value} to {status.value}")
            return True
        return False

    def drain_backend(self, backend_id: str) -> bool:
        """排空后端服务器（停止接收新请求）"""
        return self.set_backend_status(backend_id, BackendStatus.DRAINING)

    def enable_backend_maintenance(self, backend_id: str) -> bool:
        """启用后端维护模式"""
        return self.set_backend_status(backend_id, BackendStatus.MAINTENANCE)

class MultiRegionLoadBalancer:
    """多区域负载均衡器"""

    def __init__(self, config: LoadBalancingConfig):
        self.config = config
        self.regions: Dict[str, LoadBalancer] = {}
        self.region_weights: Dict[str, float] = {}
        self.current_region_index = 0

    def add_region(self, region_name: str, load_balancer: LoadBalancer, weight: float = 1.0) -> None:
        """添加区域"""
        self.regions[region_name] = load_balancer
        self.region_weights[region_name] = weight
        logging.info(f"Added region: {region_name} with weight {weight}")

    async def select_region(self, request_context: Dict[str, Any] = None) -> Optional[str]:
        """选择区域"""
        if not self.regions:
            return None

        # 简单的加权随机选择
        total_weight = sum(self.region_weights.values())
        if total_weight == 0:
            return list(self.regions.keys())[0]

        random_weight = random.random() * total_weight
        current_weight = 0

        for region_name, weight in self.region_weights.items():
            current_weight += weight
            if random_weight <= current_weight:
                return region_name

        return list(self.regions.keys())[-1]

    async def make_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str] = None,
        data: Any = None,
        params: Dict[str, str] = None,
        request_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发起跨区域请求"""
        region_name = await self.select_region(request_context)
        if not region_name or region_name not in self.regions:
            raise Exception("No available regions")

        load_balancer = self.regions[region_name]
        result = await load_balancer.make_request(method, url, headers, data, params, request_context)
        result["region"] = region_name
        return result

    def get_region_statistics(self) -> Dict[str, Any]:
        """获取区域统计信息"""
        return {
            region_name: load_balancer.get_statistics()
            for region_name, load_balancer in self.regions.items()
        }