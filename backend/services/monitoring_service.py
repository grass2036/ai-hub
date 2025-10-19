"""
监控和告警服务 - Week 3 P2 扩展功能
提供企业级系统监控、指标收集和告警管理
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func

from ..models.monitoring import (
    Metric, MetricData, AlertRule, Alert, NotificationChannel,
    Dashboard, HealthCheck, SystemLog, MetricType, AlertSeverity, AlertStatus
)
from ..models.organization import Organization
from ..core.auth import get_current_user

logger = logging.getLogger(__name__)


class MonitoringService:
    """监控服务"""

    def __init__(self, db: Session):
        self.db = db

    async def create_metric(
        self,
        name: str,
        display_name: str,
        description: str,
        metric_type: str,
        unit: str,
        collection_interval: int = 60,
        warning_threshold: Optional[float] = None,
        critical_threshold: Optional[float] = None,
        metadata: Optional[Dict] = None
    ) -> Metric:
        """创建监控指标"""
        try:
            metric = Metric(
                id=str(uuid.uuid4()),
                name=name,
                display_name=display_name,
                description=description,
                metric_type=metric_type,
                unit=unit,
                collection_interval=collection_interval,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
                metadata=metadata or {},
                created_at=datetime.now(timezone.utc)
            )

            self.db.add(metric)
            self.db.commit()
            self.db.refresh(metric)

            logger.info(f"Metric created: {name}")
            return metric

        except Exception as e:
            logger.error(f"Error creating metric: {str(e)}")
            self.db.rollback()
            raise

    async def record_metric_data(
        self,
        metric_id: str,
        value: float,
        organization_id: str,
        tags: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ) -> MetricData:
        """记录指标数据"""
        try:
            now = timestamp or datetime.now(timezone.utc)
            period_start = now.replace(second=0, microsecond=0)
            period_end = period_start + timedelta(minutes=1)

            # 检查是否已有该时间段的数据
            existing_data = self.db.query(MetricData).filter(
                and_(
                    MetricData.metric_id == metric_id,
                    MetricData.organization_id == organization_id,
                    MetricData.period_start == period_start
                )
            ).first()

            if existing_data:
                # 更新现有数据
                existing_data.count += 1
                existing_data.sum_value += value
                existing_data.avg_value = existing_data.sum_value / existing_data.count
                existing_data.min_value = min(existing_data.min_value or float('inf'), value)
                existing_data.max_value = max(existing_data.max_value or 0, value)
                metric_data = existing_data
            else:
                # 创建新数据
                metric_data = MetricData(
                    id=str(uuid.uuid4()),
                    metric_id=metric_id,
                    organization_id=organization_id,
                    value=value,
                    min_value=value,
                    max_value=value,
                    avg_value=value,
                    sum_value=value,
                    count=1,
                    timestamp=now,
                    period_start=period_start,
                    period_end=period_end,
                    tags=tags or {}
                )
                self.db.add(metric_data)

            self.db.commit()
            self.db.refresh(metric_data)

            # 检查是否需要触发告警
            await self._check_alert_rules(metric_id, organization_id, value)

            return metric_data

        except Exception as e:
            logger.error(f"Error recording metric data: {str(e)}")
            self.db.rollback()
            raise

    async def create_alert_rule(
        self,
        name: str,
        description: str,
        organization_id: str,
        metric_id: str,
        condition: str,
        threshold_value: float,
        severity: str,
        evaluation_window: int = 300,
        consecutive_breaches: int = 1,
        notification_channels: Optional[List[str]] = None
    ) -> AlertRule:
        """创建告警规则"""
        try:
            alert_rule = AlertRule(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                organization_id=organization_id,
                metric_id=metric_id,
                condition=condition,
                threshold_value=threshold_value,
                severity=severity,
                evaluation_window=evaluation_window,
                consecutive_breaches=consecutive_breaches,
                notification_channels=notification_channels or [],
                created_at=datetime.now(timezone.utc)
            )

            self.db.add(alert_rule)
            self.db.commit()
            self.db.refresh(alert_rule)

            logger.info(f"Alert rule created: {name}")
            return alert_rule

        except Exception as e:
            logger.error(f"Error creating alert rule: {str(e)}")
            self.db.rollback()
            raise

    async def _check_alert_rules(
        self,
        metric_id: str,
        organization_id: str,
        current_value: float
    ):
        """检查告警规则"""
        try:
            # 获取相关的告警规则
            rules = self.db.query(AlertRule).filter(
                and_(
                    AlertRule.metric_id == metric_id,
                    AlertRule.organization_id == organization_id,
                    AlertRule.is_enabled == True
                )
            ).all()

            for rule in rules:
                await self._evaluate_alert_rule(rule, current_value)

        except Exception as e:
            logger.error(f"Error checking alert rules: {str(e)}")

    async def _evaluate_alert_rule(
        self,
        rule: AlertRule,
        current_value: float
    ):
        """评估告警规则"""
        try:
            # 检查条件
            triggered = self._evaluate_condition(
                current_value,
                rule.condition,
                rule.threshold_value
            )

            if not triggered:
                return

            # 检查是否已有活跃告警
            existing_alert = self.db.query(Alert).filter(
                and_(
                    Alert.alert_rule_id == rule.id,
                    Alert.status == "active"
                )
            ).first()

            if existing_alert:
                # 更新现有告警
                existing_alert.trigger_value = current_value
                existing_alert.metadata = existing_alert.metadata or {}
                existing_alert.metadata["last_evaluation"] = datetime.now(timezone.utc).isoformat()
                existing_alert.triggered_at = datetime.now(timezone.utc)
            else:
                # 创建新告警
                alert = Alert(
                    id=str(uuid.uuid4()),
                    alert_rule_id=rule.id,
                    organization_id=rule.organization_id,
                    title=f"告警: {rule.name}",
                    message=f"指标 {rule.metric.name} 的值 {current_value} {rule.condition} {rule.threshold_value}",
                    severity=rule.severity,
                    status="active",
                    trigger_value=current_value,
                    threshold_value=rule.threshold_value,
                    triggered_at=datetime.now(timezone.utc),
                    metadata={
                        "rule_name": rule.name,
                        "metric_name": rule.metric.name,
                        "condition": f"{current_value} {rule.condition} {rule.threshold_value}"
                    }
                )

                self.db.add(alert)

            self.db.commit()

            # 发送通知
            await self._send_alert_notifications(rule, current_value)

        except Exception as e:
            logger.error(f"Error evaluating alert rule: {str(e)}")

    def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool:
        """评估条件"""
        if condition == ">":
            return value > threshold
        elif condition == "<":
            return value < threshold
        elif condition == ">=":
            return value >= threshold
        elif condition == "<=":
            return value <= threshold
        elif condition == "==":
            return value == threshold
        elif condition == "!=":
            return value != threshold
        return False

    async def _send_alert_notifications(
        self,
        rule: AlertRule,
        current_value: float
    ):
        """发送告警通知"""
        try:
            # 这里可以实现邮件、Slack、Webhook等通知
            # 目前只记录日志
            logger.warning(
                f"Alert triggered: {rule.name} - "
                f"Value: {current_value} {rule.condition} {rule.threshold_value} - "
                f"Channels: {rule.notification_channels}"
            )

            # TODO: 实现实际的通知发送逻辑
            # - 邮件通知
            # - Slack通知
            # - Webhook通知
            # - 短信通知

        except Exception as e:
            logger.error(f"Error sending alert notifications: {str(e)}")

    async def create_notification_channel(
        self,
        organization_id: str,
        name: str,
        channel_type: str,
        config: Dict,
        is_default: bool = False
    ) -> NotificationChannel:
        """创建通知渠道"""
        try:
            channel = NotificationChannel(
                id=str(uuid.uuid4()),
                organization_id=organization_id,
                name=name,
                type=channel_type,
                config=config,
                is_default=is_default,
                created_at=datetime.now(timezone.utc)
            )

            self.db.add(channel)
            self.db.commit()
            self.db.refresh(channel)

            logger.info(f"Notification channel created: {name}")
            return channel

        except Exception as e:
            logger.error(f"Error creating notification channel: {str(e)}")
            self.db.rollback()
            raise

    async def create_dashboard(
        self,
        organization_id: str,
        name: str,
        description: str,
        layout: Dict,
        widgets: List[Dict],
        created_by: str,
        is_default: bool = False
    ) -> Dashboard:
        """创建监控仪表板"""
        try:
            dashboard = Dashboard(
                id=str(uuid.uuid4()),
                organization_id=organization_id,
                name=name,
                description=description,
                layout=layout,
                widgets=widgets,
                created_by=created_by,
                is_default=is_default,
                created_at=datetime.now(timezone.utc)
            )

            self.db.add(dashboard)
            self.db.commit()
            self.db.refresh(dashboard)

            logger.info(f"Dashboard created: {name}")
            return dashboard

        except Exception as e:
            logger.error(f"Error creating dashboard: {str(e)}")
            self.db.rollback()
            raise

    async def record_health_check(
        self,
        name: str,
        service_name: str,
        check_type: str,
        status: str,
        response_time: Optional[float] = None,
        error_message: Optional[str] = None,
        endpoint: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> HealthCheck:
        """记录健康检查结果"""
        try:
            health_check = HealthCheck(
                id=str(uuid.uuid4()),
                name=name,
                service_name=service_name,
                check_type=check_type,
                endpoint=endpoint,
                status=status,
                response_time=response_time,
                error_message=error_message,
                metadata=metadata or {},
                checked_at=datetime.now(timezone.utc)
            )

            if status == "healthy":
                health_check.last_healthy_at = datetime.now(timezone.utc)

            self.db.add(health_check)
            self.db.commit()
            self.db.refresh(health_check)

            return health_check

        except Exception as e:
            logger.error(f"Error recording health check: {str(e)}")
            self.db.rollback()
            raise

    async def log_system_event(
        self,
        level: str,
        service: str,
        message: str,
        context: Optional[Dict] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        stack_trace: Optional[str] = None
    ) -> SystemLog:
        """记录系统日志"""
        try:
            system_log = SystemLog(
                id=str(uuid.uuid4()),
                level=level,
                service=service,
                message=message,
                context=context or {},
                request_id=request_id,
                user_id=user_id,
                organization_id=organization_id,
                stack_trace=stack_trace,
                timestamp=datetime.now(timezone.utc)
            )

            self.db.add(system_log)
            self.db.commit()
            self.db.refresh(system_log)

            return system_log

        except Exception as e:
            logger.error(f"Error logging system event: {str(e)}")
            self.db.rollback()
            raise

    def get_metrics(
        self,
        organization_id: str,
        metric_type: Optional[str] = None,
        is_enabled: Optional[bool] = None
    ) -> List[Metric]:
        """获取指标列表"""
        try:
            query = self.db.query(Metric)

            if metric_type:
                query = query.filter(Metric.metric_type == metric_type)
            if is_enabled is not None:
                query = query.filter(Metric.is_enabled == is_enabled)

            return query.all()

        except Exception as e:
            logger.error(f"Error getting metrics: {str(e)}")
            raise

    def get_metric_data(
        self,
        metric_id: str,
        organization_id: str,
        start_time: datetime,
        end_time: datetime,
        aggregation: str = "avg"
    ) -> List[MetricData]:
        """获取指标数据"""
        try:
            query = self.db.query(MetricData).filter(
                and_(
                    MetricData.metric_id == metric_id,
                    MetricData.organization_id == organization_id,
                    MetricData.timestamp >= start_time,
                    MetricData.timestamp <= end_time
                )
            ).order_by(MetricData.timestamp.asc())

            return query.all()

        except Exception as e:
            logger.error(f"Error getting metric data: {str(e)}")
            raise

    def get_active_alerts(
        self,
        organization_id: str,
        severity: Optional[str] = None
    ) -> List[Alert]:
        """获取活跃告警"""
        try:
            query = self.db.query(Alert).filter(
                and_(
                    Alert.organization_id == organization_id,
                    Alert.status == "active"
                )
            )

            if severity:
                query = query.filter(Alert.severity == severity)

            return query.order_by(desc(Alert.triggered_at)).all()

        except Exception as e:
            logger.error(f"Error getting active alerts: {str(e)}")
            raise

    def get_system_health(
        self,
        service_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取系统健康状态"""
        try:
            query = self.db.query(HealthCheck)

            if service_name:
                query = query.filter(HealthCheck.service_name == service_name)

            recent_checks = query.filter(
                HealthCheck.checked_at >= datetime.now(timezone.utc) - timedelta(minutes=5)
            ).all()

            # 统计健康状态
            health_summary = {
                "total_checks": len(recent_checks),
                "healthy": 0,
                "unhealthy": 0,
                "unknown": 0,
                "services": {}
            }

            for check in recent_checks:
                health_summary["services"][check.service_name] = {
                    "status": check.status,
                    "response_time": check.response_time,
                    "last_check": check.checked_at.isoformat(),
                    "endpoint": check.endpoint
                }

                if check.status == "healthy":
                    health_summary["healthy"] += 1
                elif check.status == "unhealthy":
                    health_summary["unhealthy"] += 1
                else:
                    health_summary["unknown"] += 1

            # 计算整体健康状态
            total = health_summary["total_checks"]
            if total == 0:
                overall_status = "unknown"
            elif health_summary["healthy"] == total:
                overall_status = "healthy"
            elif health_summary["unhealthy"] > 0:
                overall_status = "unhealthy"
            else:
                overall_status = "degraded"

            health_summary["overall_status"] = overall_status
            health_summary["health_percentage"] = (
                (health_summary["healthy"] / total * 100) if total > 0 else 0
            )

            return health_summary

        except Exception as e:
            logger.error(f"Error getting system health: {str(e)}")
            raise

    def get_alert_statistics(
        self,
        organization_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """获取告警统计"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            # 总告警数
            total_alerts = self.db.query(Alert).filter(
                and_(
                    Alert.organization_id == organization_id,
                    Alert.triggered_at >= start_date
                )
            ).count()

            # 按严重程度分组
            alerts_by_severity = self.db.query(
                Alert.severity,
                func.count(Alert.id).label("count")
            ).filter(
                and_(
                    Alert.organization_id == organization_id,
                    Alert.triggered_at >= start_date
                )
            ).group_by(Alert.severity).all()

            # 按状态分组
            alerts_by_status = self.db.query(
                Alert.status,
                func.count(Alert.id).label("count")
            ).filter(
                and_(
                    Alert.organization_id == organization_id,
                    Alert.triggered_at >= start_date
                )
            ).group_by(Alert.status).all()

            return {
                "period": {"days": days, "start_date": start_date.isoformat()},
                "total_alerts": total_alerts,
                "alerts_by_severity": {severity: count for severity, count in alerts_by_severity},
                "alerts_by_status": {status: count for status, count in alerts_by_status}
            }

        except Exception as e:
            logger.error(f"Error getting alert statistics: {str(e)}")
            raise


# 预定义指标常量
class SystemMetrics:
    """系统预定义指标"""

    # API指标
    API_REQUEST_RATE = "api_requests_per_second"
    API_RESPONSE_TIME = "api_response_time_ms"
    API_ERROR_RATE = "api_error_rate"
    API_SUCCESS_RATE = "api_success_rate"

    # 系统指标
    CPU_USAGE = "cpu_usage_percent"
    MEMORY_USAGE = "memory_usage_percent"
    DISK_USAGE = "disk_usage_percent"
    NETWORK_IN = "network_in_bytes_per_sec"
    NETWORK_OUT = "network_out_bytes_per_sec"

    # 数据库指标
    DB_CONNECTIONS = "database_connections"
    DB_QUERY_TIME = "database_query_time_ms"
    DB_ERROR_RATE = "database_error_rate"

    # 业务指标
    ACTIVE_USERS = "active_users"
    NEW_SIGNUPS = "new_signups_per_hour"
    API_CALLS = "api_calls_per_hour"
    REVENUE = "revenue_per_hour"

    # 安全指标
    FAILED_LOGIN_ATTEMPTS = "failed_login_attempts"
    SECURITY_ALERTS = "security_alerts_count"
    SUSPICIOUS_ACTIVITIES = "suspicious_activities_count"


# 全局监控服务实例
def get_monitoring_service(db: Session) -> MonitoringService:
    return MonitoringService(db)