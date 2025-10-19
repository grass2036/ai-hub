"""
监控和告警API - Week 3 P2 扩展功能
提供企业级系统监���、指标管理和告警功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from ..database import get_db
from ..services.monitoring_service import MonitoringService, SystemMetrics
from ..core.auth import get_current_user, get_current_organization
from ..models.user import User
from ..models.organization import Organization

# 创建路由器
router = APIRouter()


# 请求/响应模型
class MetricRequest(BaseModel):
    """指标创建请求"""
    name: str
    display_name: str
    description: str
    metric_type: str
    unit: str
    collection_interval: int = 60
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    metadata: Optional[Dict] = None


class MetricDataRequest(BaseModel):
    """指标数据记录请求"""
    metric_id: str
    value: float
    tags: Optional[Dict] = None
    timestamp: Optional[datetime] = None


class AlertRuleRequest(BaseModel):
    """告警规则创建请求"""
    name: str
    description: str
    metric_id: str
    condition: str
    threshold_value: float
    severity: str
    evaluation_window: int = 300
    consecutive_breaches: int = 1
    notification_channels: Optional[List[str]] = None


class NotificationChannelRequest(BaseModel):
    """通知渠道创建请求"""
    name: str
    channel_type: str
    config: Dict
    is_default: bool = False


class DashboardRequest(BaseModel):
    """仪表板创建请求"""
    name: str
    description: str
    layout: Dict
    widgets: List[Dict]
    is_default: bool = False


class HealthCheckRequest(BaseModel):
    """健康检查记录请求"""
    name: str
    service_name: str
    check_type: str
    status: str
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    endpoint: Optional[str] = None
    metadata: Optional[Dict] = None


@router.get("/metrics")
async def get_metrics(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    metric_type: Optional[str] = Query(None),
    is_enabled: Optional[bool] = Query(None)
):
    """获取指标列表"""
    try:
        monitoring_service = MonitoringService(db)
        metrics = monitoring_service.get_metrics(
            organization_id=str(organization.id),
            metric_type=metric_type,
            is_enabled=is_enabled
        )

        return {
            "success": True,
            "data": [
                {
                    "id": str(metric.id),
                    "name": metric.name,
                    "display_name": metric.display_name,
                    "description": metric.description,
                    "metric_type": metric.metric_type,
                    "unit": metric.unit,
                    "collection_interval": metric.collection_interval,
                    "warning_threshold": metric.warning_threshold,
                    "critical_threshold": metric.critical_threshold,
                    "is_enabled": metric.is_enabled,
                    "created_at": metric.created_at.isoformat()
                }
                for metric in metrics
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metrics")
async def create_metric(
    request: MetricRequest,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """创建监控指标"""
    try:
        monitoring_service = MonitoringService(db)

        metric = await monitoring_service.create_metric(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            metric_type=request.metric_type,
            unit=request.unit,
            collection_interval=request.collection_interval,
            warning_threshold=request.warning_threshold,
            critical_threshold=request.critical_threshold,
            metadata=request.metadata
        )

        return {
            "success": True,
            "data": {
                "id": str(metric.id),
                "name": metric.name,
                "display_name": metric.display_name,
                "created_at": metric.created_at.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metrics/data")
async def record_metric_data(
    request: MetricDataRequest,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """记录指标数据"""
    try:
        monitoring_service = MonitoringService(db)

        metric_data = await monitoring_service.record_metric_data(
            metric_id=request.metric_id,
            value=request.value,
            organization_id=str(organization.id),
            tags=request.tags,
            timestamp=request.timestamp
        )

        return {
            "success": True,
            "data": {
                "id": str(metric_data.id),
                "value": metric_data.value,
                "timestamp": metric_data.timestamp.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/{metric_id}/data")
async def get_metric_data(
    metric_id: str,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    aggregation: str = Query("avg")
):
    """获取指标数据"""
    try:
        # 如果没有指定时间范围，默认为最近24小时
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.utcnow()

        monitoring_service = MonitoringService(db)
        data = monitoring_service.get_metric_data(
            metric_id=metric_id,
            organization_id=str(organization.id),
            start_time=start_time,
            end_time=end_time,
            aggregation=aggregation
        )

        return {
            "success": True,
            "data": [
                {
                    "id": str(d.id),
                    "value": d.value,
                    "avg_value": d.avg_value,
                    "min_value": d.min_value,
                    "max_value": d.max_value,
                    "count": d.count,
                    "timestamp": d.timestamp.isoformat(),
                    "tags": d.tags
                }
                for d in data
            ],
            "period": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200)
):
    """获取告警列表"""
    try:
        from ..models.monitoring import Alert

        query = db.query(Alert).filter(Alert.organization_id == str(organization.id))

        if severity:
            query = query.filter(Alert.severity == severity)
        if status:
            query = query.filter(Alert.status == status)

        total = query.count()
        alerts = query.order_by(desc(Alert.triggered_at)).offset((page - 1) * limit).limit(limit).all()

        return {
            "success": True,
            "data": {
                "alerts": [
                    {
                        "id": str(alert.id),
                        "title": alert.title,
                        "message": alert.message,
                        "severity": alert.severity,
                        "status": alert.status,
                        "trigger_value": alert.trigger_value,
                        "threshold_value": alert.threshold_value,
                        "triggered_at": alert.triggered_at.isoformat(),
                        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                        "metadata": alert.metadata
                    }
                    for alert in alerts
                ],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/active")
async def get_active_alerts(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    severity: Optional[str] = Query(None)
):
    """获取活跃告警"""
    try:
        monitoring_service = MonitoringService(db)
        alerts = monitoring_service.get_active_alerts(
            organization_id=str(organization.id),
            severity=severity
        )

        return {
            "success": True,
            "data": [
                {
                    "id": str(alert.id),
                    "title": alert.title,
                    "message": alert.message,
                    "severity": alert.severity,
                    "trigger_value": alert.trigger_value,
                    "threshold_value": alert.threshold_value,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "metadata": alert.metadata
                }
                for alert in alerts
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alert-rules")
async def create_alert_rule(
    request: AlertRuleRequest,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """创建告警规则"""
    try:
        monitoring_service = MonitoringService(db)

        alert_rule = await monitoring_service.create_alert_rule(
            name=request.name,
            description=request.description,
            organization_id=str(organization.id),
            metric_id=request.metric_id,
            condition=request.condition,
            threshold_value=request.threshold_value,
            severity=request.severity,
            evaluation_window=request.evaluation_window,
            consecutive_breaches=request.consecutive_breaches,
            notification_channels=request.notification_channels
        )

        return {
            "success": True,
            "data": {
                "id": str(alert_rule.id),
                "name": alert_rule.name,
                "severity": alert_rule.severity,
                "created_at": alert_rule.created_at.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notification-channels")
async def create_notification_channel(
    request: NotificationChannelRequest,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """创建通知渠道"""
    try:
        monitoring_service = MonitoringService(db)

        channel = await monitoring_service.create_notification_channel(
            organization_id=str(organization.id),
            name=request.name,
            channel_type=request.channel_type,
            config=request.config,
            is_default=request.is_default
        )

        return {
            "success": True,
            "data": {
                "id": str(channel.id),
                "name": channel.name,
                "type": channel.type,
                "is_default": channel.is_default,
                "created_at": channel.created_at.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dashboards")
async def create_dashboard(
    request: DashboardRequest,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """创建监控仪表板"""
    try:
        monitoring_service = MonitoringService(db)

        dashboard = await monitoring_service.create_dashboard(
            organization_id=str(organization.id),
            name=request.name,
            description=request.description,
            layout=request.layout,
            widgets=request.widgets,
            created_by=str(user.id),
            is_default=request.is_default
        )

        return {
            "success": True,
            "data": {
                "id": str(dashboard.id),
                "name": dashboard.name,
                "description": dashboard.description,
                "created_at": dashboard.created_at.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_system_health(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    service_name: Optional[str] = Query(None)
):
    """获取系统健康状态"""
    try:
        monitoring_service = MonitoringService(db)
        health_data = monitoring_service.get_system_health(service_name=service_name)

        return {
            "success": True,
            "data": health_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health/checks")
async def record_health_check(
    request: HealthCheckRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """记录健康检查结果"""
    try:
        monitoring_service = MonitoringService(db)

        health_check = await monitoring_service.record_health_check(
            name=request.name,
            service_name=request.service_name,
            check_type=request.check_type,
            status=request.status,
            response_time=request.response_time,
            error_message=request.error_message,
            endpoint=request.endpoint,
            metadata=request.metadata
        )

        return {
            "success": True,
            "data": {
                "id": str(health_check.id),
                "status": health_check.status,
                "response_time": health_check.response_time,
                "checked_at": health_check.checked_at.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/alerts")
async def get_alert_statistics(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=90)
):
    """获取告警统计"""
    try:
        monitoring_service = MonitoringService(db)
        stats = monitoring_service.get_alert_statistics(
            organization_id=str(organization.id),
            days=days
        )

        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-metrics")
async def get_system_metrics():
    """获取系统预定义指标列表"""
    return {
        "success": True,
        "data": {
            "metrics": [
                {"key": SystemMetrics.API_REQUEST_RATE, "name": "API请求率", "unit": "req/sec"},
                {"key": SystemMetrics.API_RESPONSE_TIME, "name": "API响应时间", "unit": "ms"},
                {"key": SystemMetrics.API_ERROR_RATE, "name": "API错误率", "unit": "%"},
                {"key": SystemMetrics.CPU_USAGE, "name": "CPU使用率", "unit": "%"},
                {"key": SystemMetrics.MEMORY_USAGE, "name": "内存使用率", "unit": "%"},
                {"key": SystemMetrics.ACTIVE_USERS, "name": "活跃用户数", "unit": "count"},
                {"key": SystemMetrics.API_CALLS, "name": "API调用数", "unit": "count"},
                {"key": SystemMetrics.FAILED_LOGIN_ATTEMPTS, "name": "失败登录尝试", "unit": "count"}
            ]
        }
    }


@router.post("/system-logs")
async def log_system_event(
    background_tasks: BackgroundTasks,
    level: str,
    service: str,
    message: str,
    context: Optional[Dict] = None,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    stack_trace: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """记录系统日志"""
    try:
        # 在后台任务中记录日志，避免影响响应时间
        async def log_task():
            monitoring_service = MonitoringService(db)
            await monitoring_service.log_system_event(
                level=level,
                service=service,
                message=message,
                context=context,
                request_id=request_id,
                user_id=user_id,
                organization_id=organization_id,
                stack_trace=stack_trace
            )

        background_tasks.add_task(log_task)

        return {
            "success": True,
            "message": "System log recorded"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboards")
async def get_dashboards(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """获取仪表板列表"""
    try:
        from ..models.monitoring import Dashboard

        dashboards = db.query(Dashboard).filter(
            Dashboard.organization_id == str(organization.id)
        ).order_by(Dashboard.is_default.desc(), Dashboard.created_at.desc()).all()

        return {
            "success": True,
            "data": [
                {
                    "id": str(dashboard.id),
                    "name": dashboard.name,
                    "description": dashboard.description,
                    "is_default": dashboard.is_default,
                    "is_public": dashboard.is_public,
                    "layout": dashboard.layout,
                    "widgets": dashboard.widgets,
                    "created_at": dashboard.created_at.isoformat()
                }
                for dashboard in dashboards
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboards/{dashboard_id}")
async def get_dashboard(
    dashboard_id: str,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """获取特定仪表板"""
    try:
        from ..models.monitoring import Dashboard

        dashboard = db.query(Dashboard).filter(
            and_(
                Dashboard.id == dashboard_id,
                Dashboard.organization_id == str(organization.id)
            )
        ).first()

        if not dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        return {
            "success": True,
            "data": {
                "id": str(dashboard.id),
                "name": dashboard.name,
                "description": dashboard.description,
                "layout": dashboard.layout,
                "widgets": dashboard.widgets,
                "time_range": dashboard.time_range,
                "refresh_interval": dashboard.refresh_interval,
                "created_at": dashboard.created_at.isoformat(),
                "updated_at": dashboard.updated_at.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))