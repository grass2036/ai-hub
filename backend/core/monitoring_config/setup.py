"""
监控系统配置和初始化
Week 6 Day 4: 系统监控和日志配置

提供监控系统的配置管理和统一初始化接口
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import redis

from .enhanced_monitoring import ProductionMonitor
from .log_config import ProductionLogger, LogLevel
from .alerting import AlertManager, AlertRule, AlertSeverity, NotificationChannel
from .metrics_collector import MetricsCollector, metrics_collector as global_metrics_collector

@dataclass
class MonitoringConfig:
    """监控配置"""
    enabled: bool = True
    service_name: str = "ai-hub"
    environment: str = "production"
    update_interval: int = 30
    buffer_size: int = 10000
    retention_days: int = 30

@dataclass
class LoggingConfig:
    """日志配置"""
    enabled: bool = True
    level: LogLevel = LogLevel.INFO
    service_name: str = "ai-hub"
    console_logging: bool = True
    file_logging: bool = True
    buffer_size: int = 10000
    flush_interval: int = 60
    elasticsearch: Optional[Dict[str, Any]] = None
    s3: Optional[Dict[str, Any]] = None

@dataclass
class AlertingConfig:
    """告警配置"""
    enabled: bool = True
    email_config: Optional[Dict[str, Any]] = None
    slack_config: Optional[Dict[str, Any]] = None
    webhook_config: Optional[Dict[str, Any]] = None
    dingtalk_config: Optional[Dict[str, Any]] = None
    default_rules: bool = True

@dataclass
class MetricsConfig:
    """指标配置"""
    enabled: bool = True
    collect_system_metrics: bool = True
    collect_application_metrics: bool = True
    collect_business_metrics: bool = True
    performance_tracking: bool = True
    error_tracking: bool = True
    usage_tracking: bool = True

class MonitoringSetup:
    """监控系统设置"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/monitoring.json"
        self.config = self._load_config()
        self.production_monitor: Optional[ProductionMonitor] = None
        self.production_logger: Optional[ProductionLogger] = None
        self.alert_manager: Optional[AlertManager] = None
        self.metrics_collector: MetricsCollector = global_metrics_collector
        self.redis_client: Optional[redis.Redis] = None

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 返回默认配置
                return self._get_default_config()
        except Exception as e:
            logging.error(f"Failed to load monitoring config: {str(e)}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "monitoring": {
                "enabled": True,
                "service_name": "ai-hub",
                "environment": "production",
                "update_interval": 30,
                "buffer_size": 10000,
                "retention_days": 30
            },
            "logging": {
                "enabled": True,
                "level": "INFO",
                "service_name": "ai-hub",
                "console_logging": True,
                "file_logging": True,
                "buffer_size": 10000,
                "flush_interval": 60,
                "file_logging": {
                    "path": "logs/application.log",
                    "max_bytes": 104857600,  # 100MB
                    "backup_count": 5
                }
            },
            "alerting": {
                "enabled": True,
                "default_rules": True,
                "email_config": {
                    "enabled": False,
                    "smtp": {
                        "host": "",
                        "port": 587,
                        "use_tls": True,
                        "username": "",
                        "password": "",
                        "from_email": ""
                    },
                    "recipients": []
                },
                "slack_config": {
                    "enabled": False,
                    "webhook_url": "",
                    "channel": "#alerts"
                },
                "webhook_config": {
                    "enabled": False,
                    "url": "",
                    "method": "POST",
                    "headers": {}
                },
                "dingtalk_config": {
                    "enabled": False,
                    "webhook_url": "",
                    "secret": ""
                }
            },
            "metrics": {
                "enabled": True,
                "collect_system_metrics": True,
                "collect_application_metrics": True,
                "collect_business_metrics": True,
                "performance_tracking": True,
                "error_tracking": True,
                "usage_tracking": True
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "password": "",
                "db": 0
            }
        }

    async def initialize(self) -> None:
        """初始化监控系统"""
        try:
            logging.info("Initializing AI Hub monitoring system...")

            # 初始化Redis连接
            await self._setup_redis()

            # 初始化生产监控
            if self.config["monitoring"]["enabled"]:
                await self._setup_production_monitor()

            # 初始化日志系统
            if self.config["logging"]["enabled"]:
                await self._setup_logging()

            # 初始化告警系统
            if self.config["alerting"]["enabled"]:
                await self._setup_alerting()

            # 初始化指标收集
            if self.config["metrics"]["enabled"]:
                await self._setup_metrics()

            logging.info("AI Hub monitoring system initialized successfully")

        except Exception as e:
            logging.error(f"Failed to initialize monitoring system: {str(e)}")
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
                    db=redis_config.get("db", 0),
                    decode_responses=True
                )
                # 测试连接
                self.redis_client.ping()
                logging.info("Redis connection established for monitoring")
            else:
                logging.info("Redis not configured, monitoring will run without caching")
        except Exception as e:
            logging.warning(f"Failed to setup Redis for monitoring: {str(e)}")

    async def _setup_production_monitor(self) -> None:
        """设置生产监控"""
        try:
            monitoring_config = MonitoringConfig(**self.config["monitoring"])
            self.production_monitor = ProductionMonitor(self.redis_client)
            await self.production_monitor.initialize()
            logging.info("Production monitoring initialized")
        except Exception as e:
            logging.error(f"Failed to setup production monitoring: {str(e)}")
            raise

    async def _setup_logging(self) -> None:
        """设置日志系统"""
        try:
            logging_config_dict = self.config["logging"]
            logging_config = LoggingConfig(
                enabled=logging_config_dict["enabled"],
                level=LogLevel(logging_config_dict["level"]),
                service_name=logging_config_dict["service_name"],
                console_logging=logging_config_dict["console_logging"],
                file_logging=logging_config_dict["file_logging"],
                buffer_size=logging_config_dict["buffer_size"],
                flush_interval=logging_config_dict["flush_interval"],
                elasticsearch=logging_config_dict.get("elasticsearch"),
                s3=logging_config_dict.get("s3")
            )

            # 添加文件配置
            if "file_logging" in logging_config_dict and isinstance(logging_config_dict["file_logging"], dict):
                logging_config.file_logging = logging_config_dict["file_logging"]

            self.production_logger = ProductionLogger(asdict(logging_config))
            await self.production_logger.initialize()
            logging.info("Production logging initialized")
        except Exception as e:
            logging.error(f"Failed to setup logging: {str(e)}")
            raise

    async def _setup_alerting(self) -> None:
        """设置告警系统"""
        try:
            self.alert_manager = AlertManager(self.redis_client)

            # 配置通知渠道
            alerting_config = self.config["alerting"]

            # 邮件通知
            if alerting_config.get("email_config", {}).get("enabled", False):
                from .alerting import EmailNotificationProvider
                email_provider = EmailNotificationProvider(alerting_config["email_config"])
                self.alert_manager.register_notification_provider(
                    NotificationChannel.EMAIL, email_provider
                )

            # Slack通知
            if alerting_config.get("slack_config", {}).get("enabled", False):
                from .alerting import SlackNotificationProvider
                slack_provider = SlackNotificationProvider(alerting_config["slack_config"])
                self.alert_manager.register_notification_provider(
                    NotificationChannel.SLACK, slack_provider
                )

            # Webhook通知
            if alerting_config.get("webhook_config", {}).get("enabled", False):
                from .alerting import WebhookNotificationProvider
                webhook_provider = WebhookNotificationProvider(alerting_config["webhook_config"])
                self.alert_manager.register_notification_provider(
                    NotificationChannel.WEBHOOK, webhook_provider
                )

            # 钉钉通知
            if alerting_config.get("dingtalk_config", {}).get("enabled", False):
                from .alerting import DingTalkNotificationProvider
                dingtalk_provider = DingTalkNotificationProvider(alerting_config["dingtalk_config"])
                self.alert_manager.register_notification_provider(
                    NotificationChannel.DINGTALK, dingtalk_provider
                )

            # 添加默认告警规则
            if alerting_config.get("default_rules", True):
                self._add_default_alert_rules()

            # 启动告警评估
            await self.alert_manager.start_evaluation()
            logging.info("Alerting system initialized")
        except Exception as e:
            logging.error(f"Failed to setup alerting: {str(e)}")
            raise

    def _add_default_alert_rules(self) -> None:
        """添加默认告警规则"""
        default_rules = [
            AlertRule(
                id="high_cpu_usage",
                name="高CPU使用率",
                description="CPU使用率超过阈值",
                severity=AlertSeverity.WARNING,
                condition=">",
                threshold=80.0,
                time_window=300,
                evaluation_interval=60,
                notification_channels=[NotificationChannel.EMAIL],
                tags=["system", "performance"]
            ),
            AlertRule(
                id="high_memory_usage",
                name="高内存使用率",
                description="内存使用率超过阈值",
                severity=AlertSeverity.WARNING,
                condition=">",
                threshold=85.0,
                time_window=300,
                evaluation_interval=60,
                notification_channels=[NotificationChannel.EMAIL],
                tags=["system", "performance"]
            ),
            AlertRule(
                id="high_error_rate",
                name="高错误率",
                description="应用错误率超过阈值",
                severity=AlertSeverity.ERROR,
                condition=">",
                threshold=5.0,
                time_window=300,
                evaluation_interval=60,
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
                tags=["application", "availability"]
            ),
            AlertRule(
                id="slow_response_time",
                name="响应时间过慢",
                description="API响应时间超过阈值",
                severity=AlertSeverity.WARNING,
                condition=">",
                threshold=2000.0,
                time_window=300,
                evaluation_interval=60,
                notification_channels=[NotificationChannel.EMAIL],
                tags=["application", "performance"]
            ),
            AlertRule(
                id="critical_cpu_usage",
                name="严重CPU使用率",
                description="CPU使用率达到严重级别",
                severity=AlertSeverity.CRITICAL,
                condition=">",
                threshold=95.0,
                time_window=180,
                evaluation_interval=30,
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
                escalation_policy="urgent",
                tags=["system", "critical"]
            )
        ]

        for rule in default_rules:
            self.alert_manager.add_rule(rule)

    async def _setup_metrics(self) -> None:
        """设置指标收集"""
        try:
            metrics_config = self.config["metrics"]

            if metrics_config.get("collect_system_metrics", True):
                self.metrics_collector.start_collection()

            logging.info("Metrics collection initialized")
        except Exception as e:
            logging.error(f"Failed to setup metrics: {str(e)}")
            raise

    async def get_monitoring_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "monitoring": {
                "enabled": self.config["monitoring"]["enabled"],
                "active": self.production_monitor is not None and self.production_monitor.is_initialized
            },
            "logging": {
                "enabled": self.config["logging"]["enabled"],
                "active": self.production_logger is not None and self.production_logger.is_initialized
            },
            "alerting": {
                "enabled": self.config["alerting"]["enabled"],
                "active": self.alert_manager is not None and self.alert_manager.is_running,
                "rules_count": len(self.alert_manager.rules) if self.alert_manager else 0,
                "active_alerts": len(self.alert_manager.active_alerts) if self.alert_manager else 0
            },
            "metrics": {
                "enabled": self.config["metrics"]["enabled"],
                "collecting": self.metrics_collector.is_collecting
            },
            "redis": {
                "connected": self.redis_client is not None
            }
        }

        # 获取详细状态
        if self.production_monitor:
            status["monitoring"]["dashboard"] = self.production_monitor.get_dashboard_data()

        if self.alert_manager:
            status["alerting"]["statistics"] = self.alert_manager.get_alert_statistics()

        if self.production_logger:
            # 获取日志聚合统计
            if hasattr(self.production_logger, 'aggregator'):
                status["logging"]["aggregator_stats"] = self.production_logger.aggregator.get_stats()

        if self.metrics_collector:
            status["metrics"]["comprehensive"] = self.metrics_collector.get_comprehensive_metrics()

        return status

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health_status = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.now().isoformat()
        }

        all_healthy = True

        # 检查生产监控
        if self.production_monitor:
            try:
                current_metrics = self.production_monitor.get_current_metrics()
                if current_metrics:
                    health_status["checks"]["production_monitor"] = {
                        "status": "healthy",
                        "last_update": current_metrics.timestamp.isoformat()
                    }
                else:
                    health_status["checks"]["production_monitor"] = {
                        "status": "warning",
                        "message": "No metrics available"
                    }
                    all_healthy = False
            except Exception as e:
                health_status["checks"]["production_monitor"] = {
                    "status": "error",
                    "message": str(e)
                }
                all_healthy = False

        # 检查告警系统
        if self.alert_manager:
            try:
                rules_count = len(self.alert_manager.rules)
                active_alerts = len(self.alert_manager.active_alerts)
                critical_alerts = len([a for a in self.alert_manager.active_alerts.values() if a.severity == AlertSeverity.CRITICAL])

                if critical_alerts > 0:
                    health_status["checks"]["alerting"] = {
                        "status": "critical",
                        "message": f"{critical_alerts} critical alerts active",
                        "active_alerts": active_alerts,
                        "critical_alerts": critical_alerts
                    }
                    all_healthy = False
                else:
                    health_status["checks"]["alerting"] = {
                        "status": "healthy",
                        "rules_count": rules_count,
                        "active_alerts": active_alerts
                    }
            except Exception as e:
                health_status["checks"]["alerting"] = {
                    "status": "error",
                    "message": str(e)
                }
                all_healthy = False

        # 检查指标收集
        if self.metrics_collector:
            try:
                collecting = self.metrics_collector.is_collecting
                buffer_size = self.metrics_collector.metrics_buffer.get_size()

                health_status["checks"]["metrics_collection"] = {
                    "status": "healthy" if collecting else "warning",
                    "collecting": collecting,
                    "buffer_size": buffer_size
                }
                if not collecting:
                    all_healthy = False
            except Exception as e:
                health_status["checks"]["metrics_collection"] = {
                    "status": "error",
                    "message": str(e)
                }
                all_healthy = False

        # 检查Redis连接
        if self.redis_client:
            try:
                self.redis_client.ping()
                health_status["checks"]["redis"] = {
                    "status": "healthy"
                }
            except Exception as e:
                health_status["checks"]["redis"] = {
                    "status": "error",
                    "message": str(e)
                }
                all_healthy = False

        if not all_healthy:
            health_status["status"] = "unhealthy"

        return health_status

    async def cleanup(self) -> None:
        """清理资源"""
        try:
            if self.production_monitor:
                await self.production_monitor.cleanup()

            if self.production_logger:
                await self.production_logger.cleanup()

            if self.alert_manager:
                await self.alert_manager.stop_evaluation()

            if self.metrics_collector:
                self.metrics_collector.stop_collection()

            if self.redis_client:
                self.redis_client.close()

            logging.info("Monitoring system cleaned up")
        except Exception as e:
            logging.error(f"Error during monitoring cleanup: {str(e)}")

    def save_config(self) -> None:
        """保存配置"""
        try:
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            logging.info(f"Monitoring config saved to {self.config_path}")
        except Exception as e:
            logging.error(f"Failed to save monitoring config: {str(e)}")

# 全局监控设置实例
monitoring_setup: Optional[MonitoringSetup] = None

async def get_monitoring_config() -> MonitoringSetup:
    """获取监控设置实例"""
    global monitoring_setup
    if monitoring_setup is None:
        monitoring_setup = MonitoringSetup()
        await monitoring_setup.initialize()
    return monitoring_setup

async def setup_production_monitoring(config_path: Optional[str] = None) -> MonitoringSetup:
    """设置生产环境监控"""
    setup = MonitoringSetup(config_path)
    await setup.initialize()
    return setup