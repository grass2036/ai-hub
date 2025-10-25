"""
智能路由系统
Smart Routing System

实现基于地理位置、性能和负载的智能路由
Implements intelligent routing based on geography, performance, and load
"""

import logging
import json
import asyncio
import time
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import aiohttp
import geoip2.database
import geoip2.errors

logger = logging.getLogger(__name__)

class RoutingStrategy(Enum):
    """路由策略"""
    GEOGRAPHIC = "geographic"      # 基于地理位置
    PERFORMANCE = "performance"    # 基于性能
    LOAD_BALANCED = "load_balanced"  # 基于负载均衡
    COST_OPTIMIZED = "cost_optimized"  # 基于成本优化
    HYBRID = "hybrid"              # 混合策略

class RegionStatus(Enum):
    """区域状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"

@dataclass
class RegionEndpoint:
    """区域端点"""
    region_code: str
    endpoint_url: str
    backup_urls: List[str]
    priority: int
    weight: int
    location: Dict[str, str]  # {country: str, city: str, lat: float, lon: float}
    capacity: Dict[str, int]  # {max_connections: int, max_bandwidth: int}
    current_load: Dict[str, float]  # {connections: int, bandwidth: float}
    health_score: float  # 0-100
    latency_ms: float
    cost_per_request: float
    status: RegionStatus

@dataclass
class RoutingRule:
    """路由规则"""
    rule_id: str
    name: str
    strategy: RoutingStrategy
    conditions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    priority: int
    enabled: bool

@dataclass
class RoutingMetrics:
    """路由指标"""
    region_code: str
    timestamp: datetime
    response_time_ms: float
    success_rate: float
    error_count: int
    request_count: int
    bandwidth_mb: float

class SmartRouter:
    """智能路由器"""

    def __init__(self, config_path: str = "config/smart_routing.json"):
        self.config_path = Path(config_path)
        self.config = {}
        self.endpoints: Dict[str, RegionEndpoint] = {}
        self.rules: List[RoutingRule] = []
        self.metrics_history: Dict[str, List[RoutingMetrics]] = {}
        self.geoip_reader = None

        # 初始化配置
        self._load_config()
        self._initialize_geoip()
        self._initialize_endpoints()
        self._initialize_rules()

        # 启动后台任务
        self._start_background_tasks()

        logger.info("Smart router initialized")

    def _load_config(self):
        """加载配置"""
        default_config = {
            "geoip_database_path": "data/GeoLite2-City.mmdb",
            "regions": {
                "us-east": {
                    "region_code": "us-east",
                    "endpoint_url": "https://api.ai-hub.com/us-east",
                    "backup_urls": [
                        "https://api-backup.ai-hub.com/us-east",
                        "https://api-secondary.ai-hub.com/us-east"
                    ],
                    "priority": 1,
                    "weight": 100,
                    "location": {
                        "country": "US",
                        "city": "Virginia",
                        "lat": 37.5407,
                        "lon": -77.6363
                    },
                    "capacity": {
                        "max_connections": 10000,
                        "max_bandwidth": 10000  # Mbps
                    },
                    "cost_per_request": 0.001,
                    "health_check_interval": 30,
                    "health_check_timeout": 5
                },
                "eu-west": {
                    "region_code": "eu-west",
                    "endpoint_url": "https://api.ai-hub.com/eu-west",
                    "backup_urls": [
                        "https://api-backup.ai-hub.com/eu-west"
                    ],
                    "priority": 2,
                    "weight": 80,
                    "location": {
                        "country": "IE",
                        "city": "Dublin",
                        "lat": 53.3498,
                        "lon": -6.2603
                    },
                    "capacity": {
                        "max_connections": 8000,
                        "max_bandwidth": 8000
                    },
                    "cost_per_request": 0.0012,
                    "health_check_interval": 30,
                    "health_check_timeout": 5
                },
                "ap-southeast": {
                    "region_code": "ap-southeast",
                    "endpoint_url": "https://api.ai-hub.com/ap-southeast",
                    "backup_urls": [
                        "https://api-backup.ai-hub.com/ap-southeast"
                    ],
                    "priority": 3,
                    "weight": 70,
                    "location": {
                        "country": "SG",
                        "city": "Singapore",
                        "lat": 1.3521,
                        "lon": 103.8198
                    },
                    "capacity": {
                        "max_connections": 6000,
                        "max_bandwidth": 6000
                    },
                    "cost_per_request": 0.0015,
                    "health_check_interval": 30,
                    "health_check_timeout": 5
                }
            },
            "routing": {
                "default_strategy": "hybrid",
                "health_check_enabled": True,
                "metrics_retention_days": 30,
                "failover_enabled": True,
                "failover_timeout": 10
            },
            "performance_thresholds": {
                "max_response_time_ms": 500,
                "min_success_rate": 0.99,
                "max_error_rate": 0.01,
                "max_load_percentage": 80
            }
        }

        # 创建配置目录
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # 加载或创建配置文件
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = default_config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)

    def _initialize_geoip(self):
        """初始化GeoIP数据库"""
        try:
            geoip_path = Path(self.config["geoip_database_path"])
            if geoip_path.exists():
                self.geoip_reader = geoip2.database.Reader(str(geoip_path))
                logger.info("GeoIP database loaded successfully")
            else:
                logger.warning(f"GeoIP database not found at {geoip_path}")
                # 可以在这里添加下载GeoIP数据库的逻辑
        except Exception as e:
            logger.error(f"Failed to initialize GeoIP: {e}")

    def _initialize_endpoints(self):
        """初始化区域端点"""
        for region_code, region_config in self.config["regions"].items():
            endpoint = RegionEndpoint(
                region_code=region_code,
                endpoint_url=region_config["endpoint_url"],
                backup_urls=region_config["backup_urls"],
                priority=region_config["priority"],
                weight=region_config["weight"],
                location=region_config["location"],
                capacity=region_config["capacity"],
                current_load={"connections": 0, "bandwidth": 0.0},
                health_score=100.0,
                latency_ms=0.0,
                cost_per_request=region_config["cost_per_request"],
                status=RegionStatus.HEALTHY
            )
            self.endpoints[region_code] = endpoint

    def _initialize_rules(self):
        """初始化路由规则"""
        default_rules = [
            RoutingRule(
                rule_id="geographic_priority",
                name="Geographic Priority",
                strategy=RoutingStrategy.GEOGRAPHIC,
                conditions=[
                    {"type": "geo_location", "operator": "in", "values": ["US", "CA"]},
                    {"type": "health_status", "operator": "equals", "value": "healthy"}
                ],
                actions=[
                    {"type": "route_to", "regions": ["us-east"]},
                    {"type": "fallback", "regions": ["eu-west", "ap-southeast"]}
                ],
                priority=1,
                enabled=True
            ),
            RoutingRule(
                rule_id="european_users",
                name="European Users",
                strategy=RoutingStrategy.GEOGRAPHIC,
                conditions=[
                    {"type": "geo_location", "operator": "in", "values": ["DE", "FR", "GB", "IE", "NL"]},
                    {"type": "health_status", "operator": "equals", "value": "healthy"}
                ],
                actions=[
                    {"type": "route_to", "regions": ["eu-west"]},
                    {"type": "fallback", "regions": ["us-east", "ap-southeast"]}
                ],
                priority=2,
                enabled=True
            ),
            RoutingRule(
                rule_id="asia_pacific_users",
                name="Asia Pacific Users",
                strategy=RoutingStrategy.GEOGRAPHIC,
                conditions=[
                    {"type": "geo_location", "operator": "in", "values": ["SG", "JP", "KR", "AU", "IN"]},
                    {"type": "health_status", "operator": "equals", "value": "healthy"}
                ],
                actions=[
                    {"type": "route_to", "regions": ["ap-southeast"]},
                    {"type": "fallback", "regions": ["us-east", "eu-west"]}
                ],
                priority=3,
                enabled=True
            ),
            RoutingRule(
                rule_id="performance_optimized",
                name="Performance Optimized",
                strategy=RoutingStrategy.PERFORMANCE,
                conditions=[
                    {"type": "performance_tier", "operator": "equals", "value": "premium"}
                ],
                actions=[
                    {"type": "route_to_best_performance"},
                    {"type": "max_latency", "value": 200}
                ],
                priority=4,
                enabled=True
            ),
            RoutingRule(
                rule_id="cost_optimized",
                name="Cost Optimized",
                strategy=RoutingStrategy.COST_OPTIMIZED,
                conditions=[
                    {"type": "user_tier", "operator": "equals", "value": "free"}
                ],
                actions=[
                    {"type": "route_to_cheapest"},
                    {"type": "max_cost_per_request", "value": 0.001}
                ],
                priority=5,
                enabled=True
            )
        ]

        self.rules = sorted(default_rules, key=lambda x: x.priority)

    def _start_background_tasks(self):
        """启动后台任务"""
        if self.config["routing"]["health_check_enabled"]:
            asyncio.create_task(self._health_check_loop())

        asyncio.create_task(self._metrics_cleanup_loop())

    async def route_request(self, client_ip: str = None,
                          user_agent: str = None,
                          request_path: str = None,
                          headers: Dict[str, str] = None,
                          user_context: Dict[str, Any] = None) -> Optional[str]:
        """路由请求到最佳端点"""
        try:
            # 获取客户端地理位置
            geo_info = await self._get_geo_info(client_ip) if client_ip else None

            # 评估路由规则
            matching_rules = await self._evaluate_rules(
                geo_info, user_agent, request_path, headers, user_context
            )

            # 根据规则确定路由
            if matching_rules:
                selected_endpoint = await self._apply_rules(matching_rules, geo_info, user_context)
            else:
                # 使用默认策略
                selected_endpoint = await self._default_routing(geo_info, user_context)

            if selected_endpoint:
                # 更新负载信息
                await self._update_load(selected_endpoint.region_code, "increment")
                logger.info(f"Routed request to {selected_endpoint.region_code}")
                return selected_endpoint.endpoint_url

            return None

        except Exception as e:
            logger.error(f"Routing failed: {e}")
            return None

    async def _get_geo_info(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """获取IP地理位置信息"""
        try:
            if not self.geoip_reader:
                return None

            ip_obj = ipaddress.ip_address(ip_address)

            # 检查是否为私有IP
            if ip_obj.is_private:
                return {"country": "US", "city": "Unknown"}  # 默认美国

            response = self.geoip_reader.city(ip_address)
            return {
                "country": response.country.iso_code,
                "city": response.city.name,
                "lat": response.location.latitude,
                "lon": response.location.longitude,
                "continent": response.continent.code
            }

        except (geoip2.errors.AddressNotFoundError, ValueError):
            logger.warning(f"GeoIP lookup failed for IP: {ip_address}")
            return None
        except Exception as e:
            logger.error(f"GeoIP error: {e}")
            return None

    async def _evaluate_rules(self, geo_info: Dict[str, Any] = None,
                            user_agent: str = None,
                            request_path: str = None,
                            headers: Dict[str, str] = None,
                            user_context: Dict[str, Any] = None) -> List[RoutingRule]:
        """评估路由规则"""
        matching_rules = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            # 检查规则条件
            conditions_met = await self._check_rule_conditions(
                rule.conditions, geo_info, user_agent, request_path, headers, user_context
            )

            if conditions_met:
                matching_rules.append(rule)

        return matching_rules

    async def _check_rule_conditions(self, conditions: List[Dict[str, Any]],
                                   geo_info: Dict[str, Any] = None,
                                   user_agent: str = None,
                                   request_path: str = None,
                                   headers: Dict[str, str] = None,
                                   user_context: Dict[str, Any] = None) -> bool:
        """检查规则条件"""
        for condition in conditions:
            condition_type = condition["type"]
            operator = condition["operator"]
            expected_value = condition.get("value")
            expected_values = condition.get("values", [])

            if condition_type == "geo_location":
                if not geo_info or geo_info.get("country") not in expected_values:
                    return False

            elif condition_type == "health_status":
                expected_status = RegionStatus(expected_value)
                healthy_regions = [
                    region for region, endpoint in self.endpoints.items()
                    if endpoint.status == expected_status
                ]
                if not healthy_regions:
                    return False

            elif condition_type == "performance_tier":
                user_tier = user_context.get("performance_tier") if user_context else None
                if user_tier != expected_value:
                    return False

            elif condition_type == "user_tier":
                user_tier = user_context.get("tier") if user_context else None
                if user_tier != expected_value:
                    return False

            # 可以添加更多条件类型...

        return True

    async def _apply_rules(self, rules: List[RoutingRule],
                         geo_info: Dict[str, Any] = None,
                         user_context: Dict[str, Any] = None) -> Optional[RegionEndpoint]:
        """应用路由规则"""
        for rule in rules:
            try:
                if rule.strategy == RoutingStrategy.GEOGRAPHIC:
                    endpoint = await self._geographic_routing(rule.actions, geo_info)
                elif rule.strategy == RoutingStrategy.PERFORMANCE:
                    endpoint = await self._performance_routing(rule.actions, geo_info)
                elif rule.strategy == RoutingStrategy.COST_OPTIMIZED:
                    endpoint = await self._cost_routing(rule.actions)
                elif rule.strategy == RoutingStrategy.LOAD_BALANCED:
                    endpoint = await self._load_balanced_routing(rule.actions)
                elif rule.strategy == RoutingStrategy.HYBRID:
                    endpoint = await self._hybrid_routing(rule.actions, geo_info, user_context)
                else:
                    continue

                if endpoint:
                    return endpoint

            except Exception as e:
                logger.error(f"Failed to apply rule {rule.rule_id}: {e}")
                continue

        return None

    async def _geographic_routing(self, actions: List[Dict[str, Any]],
                                geo_info: Dict[str, Any] = None) -> Optional[RegionEndpoint]:
        """地理路由"""
        try:
            for action in actions:
                if action["type"] == "route_to":
                    regions = action["regions"]
                    for region_code in regions:
                        if region_code in self.endpoints:
                            endpoint = self.endpoints[region_code]
                            if endpoint.status == RegionStatus.HEALTHY:
                                return endpoint

                elif action["type"] == "fallback":
                    # 回退到其他区域
                    continue

            return None

        except Exception as e:
            logger.error(f"Geographic routing failed: {e}")
            return None

    async def _performance_routing(self, actions: List[Dict[str, Any]],
                                 geo_info: Dict[str, Any] = None) -> Optional[RegionEndpoint]:
        """性能路由"""
        try:
            # 获取健康的端点
            healthy_endpoints = [
                endpoint for endpoint in self.endpoints.values()
                if endpoint.status == RegionStatus.HEALTHY
            ]

            if not healthy_endpoints:
                return None

            # 按性能排序
            sorted_endpoints = sorted(
                healthy_endpoints,
                key=lambda x: (x.latency_ms, 100 - x.health_score)
            )

            # 检查性能限制
            for action in actions:
                if action["type"] == "max_latency" and sorted_endpoints:
                    max_latency = action["value"]
                    for endpoint in sorted_endpoints:
                        if endpoint.latency_ms <= max_latency:
                            return endpoint

            # 返回最佳性能端点
            return sorted_endpoints[0]

        except Exception as e:
            logger.error(f"Performance routing failed: {e}")
            return None

    async def _cost_routing(self, actions: List[Dict[str, Any]]) -> Optional[RegionEndpoint]:
        """成本优化路由"""
        try:
            # 获取健康的端点
            healthy_endpoints = [
                endpoint for endpoint in self.endpoints.values()
                if endpoint.status == RegionStatus.HEALTHY
            ]

            if not healthy_endpoints:
                return None

            # 按成本排序
            sorted_endpoints = sorted(
                healthy_endpoints,
                key=lambda x: x.cost_per_request
            )

            # 检查成本限制
            for action in actions:
                if action["type"] == "max_cost_per_request" and sorted_endpoints:
                    max_cost = action["value"]
                    for endpoint in sorted_endpoints:
                        if endpoint.cost_per_request <= max_cost:
                            return endpoint

            # 返回最便宜的端点
            return sorted_endpoints[0]

        except Exception as e:
            logger.error(f"Cost routing failed: {e}")
            return None

    async def _load_balanced_routing(self, actions: List[Dict[str, Any]]) -> Optional[RegionEndpoint]:
        """负载均衡路由"""
        try:
            # 获取健康的端点
            healthy_endpoints = [
                endpoint for endpoint in self.endpoints.values()
                if endpoint.status == RegionStatus.HEALTHY
            ]

            if not healthy_endpoints:
                return None

            # 计算权重（基于当前负载）
            weighted_endpoints = []
            for endpoint in healthy_endpoints:
                # 计算可用容量百分比
                load_percentage = (
                    endpoint.current_load["connections"] /
                    endpoint.capacity["max_connections"]
                ) * 100

                # 权重 inversely proportional to load
                if load_percentage < 80:  # 只考虑负载低于80%的端点
                    weight = max(1, 100 - int(load_percentage))
                    weighted_endpoints.append((endpoint, weight))

            if not weighted_endpoints:
                # 如果所有端点都高负载，选择负载最低的
                return min(healthy_endpoints, key=lambda x: x.current_load["connections"])

            # 加权随机选择
            import random
            total_weight = sum(weight for _, weight in weighted_endpoints)
            random_weight = random.uniform(0, total_weight)

            current_weight = 0
            for endpoint, weight in weighted_endpoints:
                current_weight += weight
                if random_weight <= current_weight:
                    return endpoint

            return weighted_endpoints[0][0]

        except Exception as e:
            logger.error(f"Load balanced routing failed: {e}")
            return None

    async def _hybrid_routing(self, actions: List[Dict[str, Any]],
                            geo_info: Dict[str, Any] = None,
                            user_context: Dict[str, Any] = None) -> Optional[RegionEndpoint]:
        """混合路由"""
        try:
            # 组合多种策略
            candidates = []

            # 地理路由候选
            geo_endpoint = await self._geographic_routing(actions, geo_info)
            if geo_endpoint:
                candidates.append(("geographic", geo_endpoint))

            # 性能路由候选
            perf_endpoint = await self._performance_routing(actions, geo_info)
            if perf_endpoint:
                candidates.append(("performance", perf_endpoint))

            # 负载均衡候选
            lb_endpoint = await self._load_balanced_routing(actions)
            if lb_endpoint:
                candidates.append(("load_balanced", lb_endpoint))

            if not candidates:
                return None

            # 计算综合得分
            def calculate_score(strategy_type: str, endpoint: RegionEndpoint) -> float:
                score = 0

                # 地理位置得分
                if geo_info and strategy_type == "geographic":
                    distance = self._calculate_distance(
                        geo_info.get("lat", 0), geo_info.get("lon", 0),
                        endpoint.location["lat"], endpoint.location["lon"]
                    )
                    geo_score = max(0, 100 - distance / 100)  # 距离越近得分越高
                    score += geo_score * 0.4

                # 性能得分
                perf_score = max(0, 100 - endpoint.latency_ms / 10)
                score += perf_score * 0.3

                # 健康得分
                health_score = endpoint.health_score
                score += health_score * 0.2

                # 负载得分
                load_percentage = (
                    endpoint.current_load["connections"] /
                    endpoint.capacity["max_connections"]
                ) * 100
                load_score = max(0, 100 - load_percentage)
                score += load_score * 0.1

                return score

            # 选择最高得分的端点
            best_candidate = max(
                candidates,
                key=lambda x: calculate_score(x[0], x[1])
            )

            return best_candidate[1]

        except Exception as e:
            logger.error(f"Hybrid routing failed: {e}")
            return None

    async def _default_routing(self, geo_info: Dict[str, Any] = None,
                             user_context: Dict[str, Any] = None) -> Optional[RegionEndpoint]:
        """默认路由策略"""
        try:
            strategy = RoutingStrategy(self.config["routing"]["default_strategy"])

            if strategy == RoutingStrategy.GEOGRAPHIC:
                return await self._geographic_routing([], geo_info)
            elif strategy == RoutingStrategy.PERFORMANCE:
                return await self._performance_routing([], geo_info)
            elif strategy == RoutingStrategy.LOAD_BALANCED:
                return await self._load_balanced_routing([])
            elif strategy == RoutingStrategy.HYBRID:
                return await self._hybrid_routing([], geo_info, user_context)
            else:
                # 默认返回第一个健康端点
                for endpoint in self.endpoints.values():
                    if endpoint.status == RegionStatus.HEALTHY:
                        return endpoint

            return None

        except Exception as e:
            logger.error(f"Default routing failed: {e}")
            return None

    def _calculate_distance(self, lat1: float, lon1: float,
                          lat2: float, lon2: float) -> float:
        """计算两点之间的距离（公里）"""
        from math import radians, cos, sin, asin, sqrt

        # 转换为弧度
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        # haversine公式
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # 地球半径（公里）
        return c * r

    async def _update_load(self, region_code: str, action: str):
        """更新负载信息"""
        try:
            if region_code in self.endpoints:
                endpoint = self.endpoints[region_code]
                if action == "increment":
                    endpoint.current_load["connections"] += 1
                elif action == "decrement":
                    endpoint.current_load["connections"] = max(0,
                        endpoint.current_load["connections"] - 1)
        except Exception as e:
            logger.error(f"Failed to update load: {e}")

    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(60)

    async def _perform_health_checks(self):
        """执行健康检查"""
        for region_code, endpoint in self.endpoints.items():
            try:
                start_time = time.time()

                # 执行健康检查请求
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                    health_url = f"{endpoint.endpoint_url}/health"
                    async with session.get(health_url) as response:
                        response_time = (time.time() - start_time) * 1000  # 转换为毫秒

                        if response.status == 200:
                            endpoint.status = RegionStatus.HEALTHY
                            endpoint.health_score = min(100, max(0, 100 - response_time / 10))
                        else:
                            endpoint.status = RegionStatus.DEGRADED
                            endpoint.health_score = 50

                        endpoint.latency_ms = response_time

                        # 记录指标
                        await self._record_metrics(region_code, response_time, 1.0 if response.status == 200 else 0.0)

            except Exception as e:
                logger.warning(f"Health check failed for {region_code}: {e}")
                endpoint.status = RegionStatus.UNHEALTHY
                endpoint.health_score = 0
                endpoint.latency_ms = 9999
                await self._record_metrics(region_code, 9999, 0.0)

    async def _record_metrics(self, region_code: str, response_time_ms: float,
                            success_rate: float):
        """记录路由指标"""
        try:
            if region_code not in self.metrics_history:
                self.metrics_history[region_code] = []

            metric = RoutingMetrics(
                region_code=region_code,
                timestamp=datetime.now(),
                response_time_ms=response_time_ms,
                success_rate=success_rate,
                error_count=0 if success_rate == 1.0 else 1,
                request_count=1,
                bandwidth_mb=0.0
            )

            self.metrics_history[region_code].append(metric)

            # 限制历史记录数量
            max_records = 1000
            if len(self.metrics_history[region_code]) > max_records:
                self.metrics_history[region_code] = self.metrics_history[region_code][-max_records:]

        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")

    async def _metrics_cleanup_loop(self):
        """指标清理循环"""
        while True:
            try:
                retention_days = self.config["routing"]["metrics_retention_days"]
                cutoff_date = datetime.now() - timedelta(days=retention_days)

                for region_code in list(self.metrics_history.keys()):
                    metrics = self.metrics_history[region_code]
                    # 保留最近的指标
                    self.metrics_history[region_code] = [
                        metric for metric in metrics
                        if metric.timestamp > cutoff_date
                    ]

                await asyncio.sleep(3600)  # 每小时清理一次

            except Exception as e:
                logger.error(f"Metrics cleanup error: {e}")
                await asyncio.sleep(3600)

    async def get_routing_stats(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        try:
            stats = {
                "timestamp": datetime.now().isoformat(),
                "endpoints": {},
                "total_requests": 0,
                "overall_success_rate": 0.0
            }

            total_requests = 0
            total_successes = 0

            for region_code, endpoint in self.endpoints.items():
                endpoint_stats = {
                    "status": endpoint.status.value,
                    "health_score": endpoint.health_score,
                    "latency_ms": endpoint.latency_ms,
                    "current_load": endpoint.current_load,
                    "capacity": endpoint.capacity,
                    "cost_per_request": endpoint.cost_per_request
                }

                # 计算最近的统计
                if region_code in self.metrics_history:
                    recent_metrics = self.metrics_history[region_code][-100:]  # 最近100个记录
                    if recent_metrics:
                        avg_response_time = sum(m.response_time_ms for m in recent_metrics) / len(recent_metrics)
                        success_rate = sum(m.success_rate for m in recent_metrics) / len(recent_metrics)
                        requests = sum(m.request_count for m in recent_metrics)

                        endpoint_stats.update({
                            "avg_response_time_ms": avg_response_time,
                            "recent_success_rate": success_rate,
                            "recent_requests": requests
                        })

                        total_requests += requests
                        total_successes += requests * success_rate

                stats["endpoints"][region_code] = endpoint_stats

            stats["total_requests"] = total_requests
            if total_requests > 0:
                stats["overall_success_rate"] = total_successes / total_requests

            return stats

        except Exception as e:
            logger.error(f"Failed to get routing stats: {e}")
            return {}

    async def close(self):
        """关闭路由器"""
        try:
            if self.geoip_reader:
                self.geoip_reader.close()
            logger.info("Smart router closed")
        except Exception as e:
            logger.error(f"Error closing router: {e}")

# 全局智能路由器实例
smart_router = SmartRouter()

async def get_smart_router() -> SmartRouter:
    """获取智能路由器实例"""
    return smart_router