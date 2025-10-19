"""
监控配置管理
Week 5 Day 3: 系统监控和运维自动化
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

from backend.config.settings import get_settings

settings = get_settings()


class NotificationConfigType(Enum):
    """通知配置类型"""
    EMAIL = "email"
    SLACK = "slack"
    DINGTALK = "dingtalk"
    WEBHOOK = "webhook"


@dataclass
class MetricsConfig:
    """指标收集配置"""
    collect_system_metrics: bool = True
    collect_api_metrics: bool = True
    collect_database_metrics: bool = True
    collect_redis_metrics: bool = True
    collection_interval: int = 60  # 秒
    metrics_retention_days: int = 7  # 天


@dataclass
class LogConfig:
    """日志收集配置"""
    log_level: str = "INFO"
    log_format: str = "json"
    log_retention_days: int = 7
    batch_size: int = 100
    flush_interval: int = 5  # 秒
    enable_file_logging: bool = True
    enable_redis_logging: bool = True


@dataclass
class HealthCheckConfig:
    """健���检查配置"""
    check_interval: int = 30  # 秒
    database_timeout: int = 5  # 秒
    redis_timeout: int = 3  # 秒
    external_service_timeout: int = 10  # 秒
    enable_detailed_checks: bool = True


@dataclass
class AlertConfig:
    """告警配置"""
    enable_alerts: bool = True
    alert_cooldown: int = 300  # 秒
    max_alerts_per_hour: int = 50
    enable_recovery_notifications: bool = True
    default_severity: str = "warning"


@dataclass
class NotificationChannelConfig:
    """通知渠道配置"""
    email_enabled: bool = False
    slack_enabled: bool = False
    dingtalk_enabled: bool = False
    webhook_enabled: bool = False
    in_app_enabled: bool = True


@dataclass
class MonitoringConfig:
    """监控总配置"""
    metrics: MetricsConfig
    logs: LogConfig
    health_checks: HealthCheckConfig
    alerts: AlertConfig
    notifications: NotificationChannelConfig


def get_monitoring_config() -> MonitoringConfig:
    """获取监控配置"""
    # 从环境变量或设置中读取配置
    metrics_config = MetricsConfig(
        collect_system_metrics=getattr(settings, 'COLLECT_SYSTEM_METRICS', True),
        collect_api_metrics=getattr(settings, 'COLLECT_API_METRICS', True),
        collect_database_metrics=getattr(settings, 'COLLECT_DATABASE_METRICS', True),
        collect_redis_metrics=getattr(settings, 'COLLECT_REDIS_METRICS', True),
        collection_interval=getattr(settings, 'METRICS_COLLECTION_INTERVAL', 60),
        metrics_retention_days=getattr(settings, 'METRICS_RETENTION_DAYS', 7)
    )

    log_config = LogConfig(
        log_level=getattr(settings, 'LOG_LEVEL', 'INFO'),
        log_format=getattr(settings, 'LOG_FORMAT', 'json'),
        log_retention_days=getattr(settings, 'LOG_RETENTION_DAYS', 7),
        batch_size=getattr(settings, 'LOG_BATCH_SIZE', 100),
        flush_interval=getattr(settings, 'LOG_FLUSH_INTERVAL', 5),
        enable_file_logging=getattr(settings, 'ENABLE_FILE_LOGGING', True),
        enable_redis_logging=getattr(settings, 'ENABLE_REDIS_LOGGING', True)
    )

    health_check_config = HealthCheckConfig(
        check_interval=getattr(settings, 'HEALTH_CHECK_INTERVAL', 30),
        database_timeout=getattr(settings, 'DATABASE_HEALTH_TIMEOUT', 5),
        redis_timeout=getattr(settings, 'REDIS_HEALTH_TIMEOUT', 3),
        external_service_timeout=getattr(settings, 'EXTERNAL_SERVICE_HEALTH_TIMEOUT', 10),
        enable_detailed_checks=getattr(settings, 'ENABLE_DETAILED_HEALTH_CHECKS', True)
    )

    alert_config = AlertConfig(
        enable_alerts=getattr(settings, 'ENABLE_ALERTS', True),
        alert_cooldown=getattr(settings, 'ALERT_COOLDOWN', 300),
        max_alerts_per_hour=getattr(settings, 'MAX_ALERTS_PER_HOUR', 50),
        enable_recovery_notifications=getattr(settings, 'ENABLE_RECOVERY_NOTIFICATIONS', True),
        default_severity=getattr(settings, 'DEFAULT_ALERT_SEVERITY', 'warning')
    )

    notification_config = NotificationChannelConfig(
        email_enabled=getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', False),
        slack_enabled=getattr(settings, 'SLACK_NOTIFICATIONS_ENABLED', False),
        dingtalk_enabled=getattr(settings, 'DINGTALK_NOTIFICATIONS_ENABLED', False),
        webhook_enabled=getattr(settings, 'WEBHOOK_NOTIFICATIONS_ENABLED', False),
        in_app_enabled=getattr(settings, 'IN_APP_NOTIFICATIONS_ENABLED', True)
    )

    return MonitoringConfig(
        metrics=metrics_config,
        logs=log_config,
        health_checks=health_check_config,
        alerts=alert_config,
        notifications=notification_config
    )


# 通知渠道配置
NOTIFICATION_CONFIGS = {
    NotificationConfigType.EMAIL: {
        "smtp_server": getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com'),
        "smtp_port": getattr(settings, 'SMTP_PORT', 587),
        "username": getattr(settings, 'SMTP_USERNAME', ''),
        "password": getattr(settings, 'SMTP_PASSWORD', ''),
        "from_email": getattr(settings, 'FROM_EMAIL', ''),
        "to_emails": getattr(settings, 'TO_EMAILS', []).split(',') if getattr(settings, 'TO_EMAILS', '') else []
    },

    NotificationConfigType.SLACK: {
        "webhook_url": getattr(settings, 'SLACK_WEBHOOK_URL', ''),
        "channel": getattr(settings, 'SLACK_CHANNEL', '#alerts'),
        "username": getattr(settings, 'SLACK_USERNAME', 'AI-Hub Bot')
    },

    NotificationConfigType.DINGTALK: {
        "webhook_url": getattr(settings, 'DINGTALK_WEBHOOK_URL', ''),
        "secret": getattr(settings, 'DINGTALK_SECRET', '')
    },

    NotificationConfigType.WEBHOOK: {
        "url": getattr(settings, 'WEBHOOK_URL', ''),
        "method": getattr(settings, 'WEBHOOK_METHOD', 'POST'),
        "headers": getattr(settings, 'WEBHOOK_HEADERS', '{}')
    }
}


# 默认告警规则配置
DEFAULT_ALERT_RULES = [
    {
        "id": "high_cpu_usage",
        "name": "CPU使用率过高",
        "metric_name": "system_cpu_usage",
        "condition": "gt",
        "threshold": 80.0,
        "severity": "warning",
        "duration": 300,
        "enabled": True,
        "labels": {"component": "system"}
    },
    {
        "id": "high_memory_usage",
        "name": "内存使用率过高",
        "metric_name": "system_memory_usage",
        "condition": "gt",
        "threshold": 85.0,
        "severity": "warning",
        "duration": 300,
        "enabled": True,
        "labels": {"component": "system"}
    },
    {
        "id": "api_error_rate",
        "name": "API错误率过高",
        "metric_name": "api_error_rate",
        "condition": "gt",
        "threshold": 5.0,
        "severity": "error",
        "duration": 60,
        "enabled": True,
        "labels": {"component": "api"}
    },
    {
        "id": "slow_response_time",
        "name": "API响应时间过慢",
        "metric_name": "api_response_time_avg",
        "condition": "gt",
        "threshold": 2000.0,
        "severity": "warning",
        "duration": 120,
        "enabled": True,
        "labels": {"component": "api"}
    },
    {
        "id": "disk_space_low",
        "name": "磁盘空间不足",
        "metric_name": "system_disk_usage",
        "condition": "gt",
        "threshold": 90.0,
        "severity": "critical",
        "duration": 180,
        "enabled": True,
        "labels": {"component": "system"}
    },
    {
        "id": "database_connection_fail",
        "name": "数据库连接失败",
        "metric_name": "database_health",
        "condition": "lt",
        "threshold": 1.0,
        "severity": "critical",
        "duration": 30,
        "enabled": True,
        "labels": {"component": "database"}
    },
    {
        "id": "redis_connection_fail",
        "name": "Redis连接失败",
        "metric_name": "redis_health",
        "condition": "lt",
        "threshold": 1.0,
        "severity": "error",
        "duration": 30,
        "enabled": True,
        "labels": {"component": "redis"}
    }
]


# 监控仪表板配置
DASHBOARD_CONFIG = {
    "refresh_interval": 30,  # 秒
    "metrics_display": {
        "system": ["cpu_usage", "memory_usage", "disk_usage", "network_io"],
        "api": ["request_rate", "error_rate", "response_time", "active_keys"],
        "database": ["connection_pool", "query_time", "active_connections"],
        "business": ["daily_active_users", "token_usage", "cost_tracking"]
    },
    "chart_types": {
        "timeseries": ["cpu_usage", "memory_usage", "response_time"],
        "gauge": ["disk_usage", "error_rate"],
        "counter": ["total_requests", "active_users"]
    },
    "alert_summary": {
        "max_displayed": 20,
        "group_by": "severity",
        "auto_refresh": True
    }
}


def is_monitoring_enabled() -> bool:
    """检查监控是否启用"""
    return getattr(settings, 'MONITORING_ENABLED', True)


def get_monitoring_environment() -> str:
    """获取监控环境"""
    return getattr(settings, 'MONITORING_ENVIRONMENT', 'development')