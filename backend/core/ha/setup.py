"""
高可用配置和初始化
Week 6 Day 5: 负载均衡和高可用配置

提供完整的HA系统配置管理和统��初始化接口
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import asdict
from pathlib import Path
import redis

from .load_balancer import LoadBalancer, LoadBalancingConfig, MultiRegionLoadBalancer
from .health_check import HealthChecker, HealthCheckConfig, CheckType
from .failover import FailoverManager, FailoverConfig, FailoverStrategy
from .cluster_management import ClusterManager, ClusterConfig

@dataclass
class HighAvailabilityConfig:
    """高可用配置"""
    enabled: bool = True
    load_balancing: Dict[str, Any] = None
    health_check: Dict[str, Any] = None
    failover: Dict[str, Any] = None
    cluster: Dict[str, Any] = None
    monitoring: Dict[str, Any] = None

@dataclass
class LoadBalancingHAConfig:
    """负载均衡HA配置"""
    strategy: str = "least_connections"
    health_check_interval: int = 30
    health_check_timeout: int = 5
    max_retries: int = 3
    retry_delay: float = 1.0
    sticky_sessions: bool = True
    session_affinity_timeout: int = 3600
    connection_timeout: int = 30
    read_timeout: int = 60

@dataclass
class HealthCheckHAConfig:
    """健康检查HA配置"""
    enabled: bool = True
    check_interval: int = 30
    timeout: int = 10
    retries: int = 3
    failure_threshold: int = 3
    success_threshold: int = 2
    checks: List[Dict[str, Any]] = None

@dataclass
class FailoverHAConfig:
    """故障转移HA配置"""
    strategy: str = "active_passive"
    health_check_interval: int = 10
    failure_detection_threshold: int = 3
    failover_timeout: int = 30
    recovery_check_interval: int = 30
    auto_recovery: bool = True
    max_failover_attempts: int = 3
    enable_sticky_sessions: bool = True

@dataclass
class ClusterHAConfig:
    """集群HA配置"""
    enabled: bool = True
    cluster_name: str = "ai-hub-cluster"
    election_timeout: int = 10
    heartbeat_interval: int = 2
    lease_timeout: int = 15
    max_nodes: int = 7
    quorum_size: int = 3
    auto_rejoin: bool = True
    enable_lease: bool = True

@dataclass
class MonitoringHAConfig:
    """监控HA配置"""
    enabled: bool = True
    metrics_collection: bool = True
    alerting: bool = True
    log_all_failures: bool = True
    performance_tracking: bool = True

class HASetup:
    """高可用系统设置"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/high_availability.json"
        self.config = self._load_config()
        self.redis_client: Optional[redis.Redis] = None

        # HA组件
        self.load_balancer: Optional[LoadBalancer] = None
        self.multi_region_lb: Optional[MultiRegionLoadBalancer] = None
        self.health_checker: Optional[HealthChecker] = None
        self.failover_manager: Optional[FailoverManager] = None
        self.cluster_manager: Optional[ClusterManager] = None

        # 后端服务器
        self.backend_servers: List[Dict[str, Any]] = []

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self._get_default_config()
        except Exception as e:
            logging.error(f"Failed to load HA config: {str(e)}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "enabled": True,
            "load_balancing": {
                "strategy": "least_connections",
                "health_check_interval": 30,
                "health_check_timeout": 5,
                "max_retries": 3,
                "retry_delay": 1.0,
                "sticky_sessions": True,
                "session_affinity_timeout": 3600,
                "connection_timeout": 30,
                "read_timeout": 60
            },
            "multi_region": {
                "enabled": False,
                "regions": []
            },
            "health_check": {
                "enabled": True,
                "check_interval": 30,
                "timeout": 10,
                "retries": 3,
                "failure_threshold": 3,
                "success_threshold": 2,
                "checks": [
                    {
                        "name": "Backend API Health",
                        "type": "http_endpoint",
                        "target": "http://localhost:8001/health",
                        "interval": 30,
                        "timeout": 5,
                        "enabled": True,
                        "params": {
                            "method": "GET",
                            "expected_status": 200,
                            "expected_content": "OK"
                        }
                    },
                    {
                        "name": "Database Health",
                        "type": "database",
                        "target": "postgresql://localhost:5432/ai_hub",
                        "interval": 30,
                        "timeout": 10,
                        "enabled": True
                    },
                    {
                        "name": "Redis Health",
                        "type": "redis",
                        "target": "localhost:6379",
                        "interval": 30,
                        "timeout": 5,
                        "enabled": True,
                        "params": {
                            "host": "localhost",
                            "port": 6379
                        }
                    },
                    {
                        "name": "Disk Space",
                        "type": "disk_space",
                        "target": "/",
                        "interval": 60,
                        "timeout": 10,
                        "enabled": True,
                        "params": {
                            "path": "/",
                            "warning_threshold": 80,
                            "critical_threshold": 90
                        }
                    },
                    {
                        "name": "Memory Usage",
                        "type": "memory_usage",
                        "target": "system",
                        "interval": 30,
                        "timeout": 5,
                        "enabled": True,
                        "params": {
                            "warning_threshold": 80,
                            "critical_threshold": 90
                        }
                    },
                    {
                        "name": "CPU Usage",
                        "type": "cpu_usage",
                        "target": "system",
                        "interval": 30,
                        "timeout": 10,
                        "enabled": True,
                        "params": {
                            "warning_threshold": 80,
                            "critical_threshold": 90,
                            "interval": 1
                        }
                    }
                ]
            },
            "failover": {
                "strategy": "active_passive",
                "health_check_interval": 10,
                "failure_detection_threshold": 3,
                "failover_timeout": 30,
                "recovery_check_interval": 30,
                "auto_recovery": True,
                "max_failover_attempts": 3,
                "enable_sticky_sessions": True,
                "session_affinity_timeout": 3600
            },
            "cluster": {
                "enabled": True,
                "cluster_name": "ai-hub-cluster",
                "election_timeout": 10,
                "heartbeat_interval": 2,
                "lease_timeout": 15,
                "max_nodes": 7,
                "quorum_size": 3,
                "auto_rejoin": True,
                "enable_lease": True
            },
            "monitoring": {
                "enabled": True,
                "metrics_collection": True,
                "alerting": True,
                "log_all_failures": True,
                "performance_tracking": True
            },
            "redis": {
                "host": "redis",
                "port": 6379,
                "password": "your_redis_password",
                "db": 2
            },
            "backend_servers": [
                {
                    "id": "backend-1",
                    "host": "localhost",
                    "port": 8001,
                    "weight": 1,
                    "max_connections": 1000,
                    "role": "primary"
                },
                {
                    "id": "backend-2",
                    "host": "localhost",
                    "port": 8002,
                    "weight": 1,
                    "max_connections": 1000,
                    "role": "secondary"
                },
                {
                    "id": "backend-3",
                    "host": "localhost",
                    "port": 8003,
                    "weight": 1,
                    "max_connections": 1000,
                    "role": "secondary"
                }
            ]
        }

    async def initialize(self) -> None:
        """初始化高可用系统"""
        try:
            logging.info("Initializing AI Hub High Availability system...")

            # 初始化Redis连接
            await self._setup_redis()

            # 初始化负载均衡
            await self._setup_load_balancing()

            # 初始化多区域负载均衡
            await self._setup_multi_region()

            # 初始化健康检查
            await self._setup_health_check()

            # 初始化故障转移
            await self._setup_failover()

            # 初始化集群管理
            await self._setup_cluster_management()

            # 设置后端服务器
            await self._setup_backend_servers()

            # 启动所有组件
            await self._start_all_components()

            logging.info("AI Hub High Availability system initialized successfully")

        except Exception as e:
            logging.error(f"Failed to initialize HA system: {str(e)}")
            raise

    async def _setup_redis(self) -> None:
        """设置Redis连接"""
        try:
            redis_config = self.config.get("redis", {})
            if redis_config.get("host"):
                self.redis_client = redis.Redis(
                    host=redis_config["host"],
                    port=redis_config.get("port", 6379),
                    password=redis_config.get("password"),
                    db=redis_config.get("db", 2),
                    decode_responses=True
                )
                # 测试连接
                self.redis_client.ping()
                logging.info("Redis connection established for HA")
            else:
                logging.info("Redis not configured, HA features will be limited")
        except Exception as e:
            logging.warning(f"Failed to setup Redis for HA: {str(e)}")

    async def _setup_load_balancing(self) -> None:
        """设置负载均衡"""
        if not self.config.get("load_balancing", {}).get("enabled", True):
            return

        lb_config_data = self.config["load_balancing"]
        lb_config = LoadBalancingConfig(
            strategy=getattr(LoadBalancingStrategy, lb_config_data["strategy"].upper(), LoadBalancingStrategy.LEAST_CONNECTIONS),
            health_check_interval=lb_config_data.get("health_check_interval", 30),
            health_check_timeout=lb_config_data.get("health_check_timeout", 5),
            max_retries=lb_config_data.get("max_retries", 3),
            retry_delay=lb_config_data.get("retry_delay", 1.0),
            sticky_sessions=lb_config_data.get("sticky_sessions", True),
            session_affinity_timeout=lb_config_data.get("session_affinity_timeout", 3600),
            connection_timeout=lb_config_data.get("connection_timeout", 30),
            read_timeout=lb_config_data.get("read_timeout", 60)
        )

        self.load_balancer = LoadBalancer(lb_config)
        await self.load_balancer.initialize(self.redis_client)

        logging.info("Load balancer initialized")

    async def _setup_multi_region(self) -> None:
        """设置多区域负载均衡"""
        if not self.config.get("multi_region", {}).get("enabled", False):
            return

        regions_config = self.config["multi_region"]["regions"]
        if not regions_config:
            return

        self.multi_region_lb = MultiRegionLoadBalancer(lb_config)

        # 为每个区域创建负载均衡器
        for region_config in regions_config:
            region_lb_config = LoadBalancingConfig(
                strategy=getattr(LoadBalancingStrategy, region_config.get("strategy", "round_robin").upper(), LoadBalancingStrategy.ROUND_ROBIN)
            )
            region_lb = LoadBalancer(region_lb_config)
            await region_lb.initialize(self.redis_client)

            self.multi_region_lb.add_region(
                region_config["name"],
                region_lb,
                region_config.get("weight", 1.0)
            )

        logging.info("Multi-region load balancer initialized")

    async def _setup_health_check(self) -> None:
        """设置健康检查"""
        if not self.config.get("health_check", {}).get("enabled", True):
            return

        self.health_checker = HealthChecker()

        # 添加健康检查
        checks_config = self.config["health_check"].get("checks", [])
        for check_config in checks_config:
            if check_config.get("enabled", True):
                health_check_config = HealthCheckConfig(
                    check_name=check_config["name"],
                    check_type=CheckType(check_config["type"]),
                    target=check_config["target"],
                    interval=check_config.get("interval", 30),
                    timeout=check_config.get("timeout", 10),
                    retries=check_config.get("retries", 3),
                    retry_delay=check_config.get("retry_delay", 1.0),
                    failure_threshold=check_config.get("failure_threshold", 3),
                    success_threshold=check_config.get("success_threshold", 2),
                    enabled=check_config.get("enabled", True),
                    params=check_config.get("params", {})
                )
                self.health_checker.add_check(health_check_config)

        await self.health_checker.start()
        logging.info("Health checker initialized")

    async def _setup_failover(self) -> None:
        """设置故障转移"""
        if not self.config.get("failover", {}).get("enabled", True):
            return

        failover_config_data = self.config["failover"]
        failover_config = FailoverConfig(
            strategy=getattr(FailoverStrategy, failover_config_data["strategy"].upper(), FailoverStrategy.ACTIVE_PASSIVE),
            health_check_interval=failover_config_data.get("health_check_interval", 10),
            failure_detection_threshold=failover_config_data.get("failure_detection_threshold", 3),
            failover_timeout=failover_config_data.get("failover_timeout", 30),
            recovery_check_interval=failover_config_data.get("recovery_check_interval", 30),
            auto_recovery=failover_config_data.get("auto_recovery", True),
            max_failover_attempts=failover_config_data.get("max_failover_attempts", 3),
            enable_sticky_sessions=failover_config_data.get("enable_sticky_sessions", True),
            session_affinity_timeout=failover_config_data.get("session_affinity_timeout", 3600)
        )

        self.failover_manager = FailoverManager(failover_config)
        await self.failover_manager.initialize(self.redis_client)

        # 添加故障转移和恢复回调
        self.failover_manager.add_failover_callback(self._on_failover_event)
        self.failover_manager.add_recovery_callback(self._on_recovery_event)

        logging.info("Failover manager initialized")

    async def _setup_cluster_management(self) -> None:
        """设置集群管理"""
        if not self.config.get("cluster", {}).get("enabled", True):
            return

        cluster_config_data = self.config["cluster"]
        cluster_config = ClusterConfig(
            cluster_name=cluster_config_data["cluster_name"],
            node_id=f"node-{int(time.time())}",  # 生成唯一节点ID
            election_timeout=cluster_config_data.get("election_timeout", 10),
            heartbeat_interval=cluster_config_data.get("heartbeat_interval", 2),
            lease_timeout=cluster_config_data.get("lease_timeout", 15),
            max_nodes=cluster_config_data.get("max_nodes", 7),
            quorum_size=cluster_config_data.get("quorum_size", 3),
            auto_rejoin=cluster_config_data.get("auto_rejoin", True),
            enable_lease=cluster_config_data.get("enable_lease", True)
        )

        self.cluster_manager = ClusterManager(cluster_config)
        await self.cluster_manager.initialize(self.redis_client)

        # 添加集群状态变更回调
        self.cluster_manager.add_state_change_callback(self._on_cluster_state_change)
        self.cluster_manager.add_leadership_callback(self._on_leadership_change)

        logging.info("Cluster manager initialized")

    async def _setup_backend_servers(self) -> None:
        """设置后端服务器"""
        backend_servers_config = self.config.get("backend_servers", [])

        for server_config in backend_servers_config:
            if self.load_balancer:
                backend_server = BackendServer(
                    id=server_config["id"],
                    host=server_config["host"],
                    port=server_config["port"],
                    weight=server_config.get("weight", 1),
                    max_connections=server_config.get("max_connections", 1000),
                    role=server_config.get("role", "secondary")
                )
                self.load_balancer.add_backend(backend_server)
                self.backend_servers.append(server_config)

            if self.failover_manager:
                failover_node = Node(
                    id=server_config["id"],
                    host=server_config["host"],
                    port=server_config["port"],
                    role=server_config.get("role", "secondary"),
                    status=BackendStatus.HEALTHY,
                    last_heartbeat=datetime.utcnow()
                )
                self.failover_manager.add_node(failover_node)

        logging.info(f"Setup {len(self.backend_servers)} backend servers")

    async def _start_all_components(self) -> None:
        """启动所有组件"""
        # 所有组件已经在各自的initialize方法中启动
        pass

    def _on_failover_event(self, event: 'FailoverEvent') -> None:
        """故障转移事件回调"""
        logging.warning(f"Failover event: {event.message}")
        # 这里可以发送告警通知
        self._send_alert(f"Failover: {event.message}")

    def _on_recovery_event(self, event: 'FailoverEvent') -> None:
        """恢复事件回调"""
        logging.info(f"Recovery event: {event.message}")
        # 这里可以发送恢复通知
        self._send_alert(f"Recovery: {event.message}")

    def _on_cluster_state_change(self, state: 'ClusterState') -> None:
        """集群状态变更回调"""
        logging.info(f"Cluster state changed: {state.value}")
        if state.value in ["partitioned", "degraded"]:
            self._send_alert(f"Cluster state: {state.value}")

    def _on_leadership_change(self, leader_id: str, term: int) -> None:
        """领导权变更回调"""
        logging.info(f"Leadership changed: {leader_id} (term: {term})")

    def _send_alert(self, message: str) -> None:
        """发送告警通知"""
        # 这里可以集成各种通知渠道
        # 例如：Slack、邮件、钉钉等
        logging.warning(f"HA Alert: {message}")

    async def get_ha_status(self) -> Dict[str, Any]:
        """获取高可用状态"""
        status = {
            "enabled": self.config["enabled"],
            "components": {
                "load_balancer": {
                    "enabled": self.load_balancer is not None,
                    "type": "single_region" if self.multi_region_lb is None else "multi_region"
                },
                "health_checker": {
                    "enabled": self.health_checker is not None,
                    "checks_count": len(self.health_checker.results) if self.health_checker else 0
                },
                "failover": {
                    "enabled": self.failover_manager is not None,
                    "strategy": self.config["failover"]["strategy"]
                },
                "cluster": {
                    "enabled": self.cluster_manager is not None,
                    "cluster_name": self.config["cluster"]["cluster_name"]
                }
            },
            "redis": {
                "connected": self.redis_client is not None
            }
        }

        # 获取详细统计
        if self.load_balancer:
            status["load_balancer_stats"] = self.load_balancer.get_statistics()

        if self.health_checker:
            status["health_check_stats"] = self.health_checker.get_health_summary()

        if self.failover_manager:
            status["failover_stats"] = self.failover_manager.get_failover_status()

        if self.cluster_manager:
            status["cluster_stats"] = self.cluster_manager.get_cluster_status()

        if self.multi_region_lb:
            status["multi_region_stats"] = self.multi_region_lb.get_region_statistics()

        return status

    async def health_check(self) -> Dict[str, Any]:
        """高可用系统健康检查"""
        overall_status = {
            "status": "healthy",
            "components": {},
            "details": {},
            "timestamp": datetime.utcnow().isoformat()
        }

        all_healthy = True

        # 检查Redis连接
        if self.redis_client:
            try:
                self.redis_client.ping()
                overall_status["components"]["redis"] = {
                    "status": "healthy",
                    "message": "Redis connection OK"
                }
            except Exception as e:
                overall_status["components"]["redis"] = {
                    "status": "unhealthy",
                    "message": f"Redis connection failed: {str(e)}"
                }
                all_healthy = False
        else:
            overall_status["components"]["redis"] = {
                "status": "disabled",
                "message": "Redis not configured"
            }

        # 检查负载均衡器
        if self.load_balancer:
            try:
                lb_stats = self.load_balancer.get_statistics()
                healthy_backends = lb_stats["healthy_backends"]
                total_backends = lb_stats["total_backends"]

                if healthy_backends == 0 and total_backends > 0:
                    overall_status["components"]["load_balancer"] = {
                        "status": "unhealthy",
                        "message": f"No healthy backends available (0/{total_backends})"
                    }
                    all_healthy = False
                else:
                    overall_status["components"]["load_balancer"] = {
                        "status": "healthy",
                        "message": f"Load balancer OK ({healthy_backends}/{total_backends} healthy)"
                    }
            except Exception as e:
                overall_status["components"]["load_balancer"] = {
                    "status": "unhealthy",
                    "message": f"Load balancer error: {str(e)}"
                }
                all_healthy = False

        # 检查健康检查器
        if self.health_checker:
            try:
                health_summary = self.health_checker.get_health_summary()
                if health_summary["overall_status"] in ["unhealthy", "unknown"]:
                    overall_status["components"]["health_checker"] = {
                        "status": "unhealthy",
                        "message": f"Health check status: {health_summary['overall_status']}"
                    }
                    all_healthy = False
                else:
                    overall_status["components"]["health_checker"] = {
                        "status": "healthy",
                        "message": f"Health check OK ({health_summary['healthy_checks']}/{health_summary['total_checks']})"
                    }
            except Exception as e:
                overall_status["components"]["health_checker"] = {
                    "status": "unhealthy",
                    "message": f"Health checker error: {str(e)}"
                }
                all_healthy = False

        # 检查故障转移管理器
        if self.failover_manager:
            try:
                failover_status = self.failover_manager.get_failover_status()
                if failover_status["state"] in ["failed", "partitioned"]:
                    overall_status["components"]["failover"] = {
                        "status": "unhealthy",
                        "message": f"Failover state: {failover_status['state']}"
                    }
                    all_healthy = False
                else:
                    overall_status["components"]["failover"] = {
                        "status": "healthy",
                        "message": f"Failover OK (state: {failover_status['state']})"
                    }
            except Exception as e:
                overall_status["components"]["failover"] = {
                    "status": "unhealthy",
                    "message": f"Failover manager error: {str(e)}"
                }
                all_healthy = False

        # 检查集群管理器
        if self.cluster_manager:
            try:
                cluster_status = self.cluster_manager.get_cluster_status()
                if not cluster_status["has_quorum"]:
                    overall_status["components"]["cluster"] = {
                        "status": "degraded",
                        "message": f"Cluster quorum not met ({cluster_status['healthy_nodes']}/{cluster_status['total_nodes']})"
                    }
                    all_healthy = False
                else:
                    overall_status["components"]["cluster"] = {
                        "status": "healthy",
                        "message": f"Cluster OK (quorum: {cluster_status['healthy_nodes']}/{cluster_status['total_nodes']})"
                    }
            except Exception as e:
                overall_status["components"]["cluster"] = {
                    "status": "unhealthy",
                    "message": f"Cluster manager error: {str(e)}"
                }
                all_healthy = False

        # 设置整体状态
        overall_status["status"] = "healthy" if all_healthy else "unhealthy"

        return overall_status

    def cleanup(self) -> None:
        """清理资源"""
        try:
            if self.cluster_manager:
                await self.cluster_manager.cleanup()
            if self.failover_manager:
                await self.failover_manager.cleanup()
            if self.health_checker:
                await self.health_checker.stop()
            if self.redis_client:
                self.redis_client.close()
            logging.info("HA system cleaned up")
        except Exception as e:
            logging.error(f"Error during HA cleanup: {str(e)}")

    def save_config(self) -> None:
        """保存配置"""
        try:
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            logging.info(f"HA config saved to {self.config_path}")
        except Exception as e:
            logging.error(f"Failed to save HA config: {str(e)}")

# 导入必要的类型
from datetime import timedelta
from .failover import FailoverEvent
from .cluster_management import Node, BackendStatus, ClusterState

# 全局HA设置实例
ha_setup: Optional[HASetup] = None

async def get_ha_config() -> HASetup:
    """获取高可用设置实例"""
    global ha_setup
    if ha_setup is None:
        ha_setup = HASetup()
        await ha_setup.initialize()
    return ha_setup

async def setup_production_ha(config_path: Optional[str] = None) -> HASetup:
    """设置生产环境高可用"""
    setup = HASetup(config_path)
    await setup.initialize()
    return setup