"""
告警管理API接口
提供告警规则管理、告警事件查询、通知配置等功能
"""
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio

from backend.monitoring.alert_engine import (
    alert_engine, AlertCondition, AlertSeverity, AlertStatus
)
from backend.monitoring.default_alert_rules import (
    DEFAULT_ALERT_RULES, load_default_alert_rules, get_rules_by_category
)
from backend.core.auth import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])

# Pydantic模型
class AlertRuleCreate(BaseModel):
    name: str = Field(..., description="告警规则名称")
    metric_name: str = Field(..., description="监控指标名称")
    operator: str = Field(..., description="操作符 (>, <, >=, <=, =, !=)")
    threshold: Any = Field(..., description="阈值")
    duration_minutes: int = Field(default=5, description="持续时间（分钟）")
    severity: AlertSeverity = Field(default=AlertSeverity.WARNING, description="严重程度")
    description: Optional[str] = Field(None, description="规则描述")
    tags: Optional[Dict[str, str]] = Field(None, description="标签")
    enabled: bool = Field(default=True, description="是否启用")

class AlertRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, description="告警规则名称")
    threshold: Optional[Any] = Field(None, description="阈值")
    duration_minutes: Optional[int] = Field(None, description="持续时间（分钟）")
    severity: Optional[AlertSeverity] = Field(None, description="严重程度")
    description: Optional[str] = Field(None, description="规则描述")
    enabled: Optional[bool] = Field(None, description="是否启用")

class AlertAcknowledge(BaseModel):
    notes: Optional[str] = Field(None, description="确认备注")

class AlertResolve(BaseModel):
    notes: Optional[str] = Field(None, description="解决备注")

class NotificationTest(BaseModel):
    message: str = Field(..., description="测试消息")
    channels: List[str] = Field(default=["email"], description="通知渠道")
    severity: AlertSeverity = Field(default=AlertSeverity.INFO, description="告警级别")

# 告警规则管理
@router.post("/rules")
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    current_user = Depends(get_current_user)
):
    """创建告警规则"""
    try:
        # 生成唯一ID
        rule_id = f"custom_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(alert_engine.rules)}"

        # 创建告警规则
        rule = AlertCondition(
            id=rule_id,
            name=rule_data.name,
            metric_name=rule_data.metric_name,
            operator=rule_data.operator,
            threshold=rule_data.threshold,
            duration_minutes=rule_data.duration_minutes,
            severity=rule_data.severity,
            description=rule_data.description,
            tags=rule_data.tags
        )

        # 添加到告警引擎
        alert_engine.add_rule(rule)

        return {
            "success": True,
            "data": {
                "rule_id": rule_id,
                "name": rule.name,
                "created_at": datetime.utcnow().isoformat()
            },
            "message": f"Alert rule '{rule.name}' created successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create alert rule: {str(e)}")

@router.get("/rules")
async def list_alert_rules(
    category: Optional[str] = Query(None, description="按分类筛选"),
    severity: Optional[AlertSeverity] = Query(None, description="按严重程度筛选"),
    enabled: Optional[bool] = Query(None, description="按启用状态筛选"),
    current_user = Depends(get_current_user)
):
    """获取告警规则列表"""
    try:
        rules = list(alert_engine.rules.values())

        # 应用筛选条件
        if category:
            rules = [rule for rule in rules if rule.tags and rule.tags.get('category') == category]
        if severity:
            rules = [rule for rule in rules if rule.severity == severity]
        if enabled is not None:
            rules = [rule for rule in rules if rule.enabled == enabled]

        # 获取规则状态
        rules_status = alert_engine.get_rules_status()

        # 构建响应数据
        result = []
        for rule in rules:
            status = rules_status.get(rule.id, {})
            result.append({
                "id": rule.id,
                "name": rule.name,
                "metric_name": rule.metric_name,
                "operator": rule.operator,
                "threshold": rule.threshold,
                "duration_minutes": rule.duration_minutes,
                "severity": rule.severity.value,
                "description": rule.description,
                "tags": rule.tags,
                "enabled": rule.enabled,
                "current_status": status.get("current_status", "normal"),
                "active_since": status.get("active_since"),
                "created_at": rule.id.split("_")[1] if "_" in rule.id else None
            })

        # 按名称排序
        result.sort(key=lambda x: x["name"])

        return {
            "success": True,
            "data": {
                "rules": result,
                "total_count": len(result),
                "filters": {
                    "category": category,
                    "severity": severity.value if severity else None,
                    "enabled": enabled
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list alert rules: {str(e)}")

@router.get("/rules/{rule_id}")
async def get_alert_rule(
    rule_id: str,
    current_user = Depends(get_current_user)
):
    """获取单个告警规则详情"""
    try:
        rule = alert_engine.rules.get(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        # 获取规则状态
        rules_status = alert_engine.get_rules_status()
        status = rules_status.get(rule_id, {})

        return {
            "success": True,
            "data": {
                "id": rule.id,
                "name": rule.name,
                "metric_name": rule.metric_name,
                "operator": rule.operator,
                "threshold": rule.threshold,
                "duration_minutes": rule.duration_minutes,
                "severity": rule.severity.value,
                "description": rule.description,
                "tags": rule.tags,
                "enabled": rule.enabled,
                "current_status": status.get("current_status", "normal"),
                "active_since": status.get("active_since")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert rule: {str(e)}")

@router.put("/rules/{rule_id}")
async def update_alert_rule(
    rule_id: str,
    rule_update: AlertRuleUpdate,
    current_user = Depends(get_current_user)
):
    """更新告警规则"""
    try:
        rule = alert_engine.rules.get(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        # 更新规则属性
        if rule_update.name is not None:
            rule.name = rule_update.name
        if rule_update.threshold is not None:
            rule.threshold = rule_update.threshold
        if rule_update.duration_minutes is not None:
            rule.duration_minutes = rule_update.duration_minutes
        if rule_update.severity is not None:
            rule.severity = rule_update.severity
        if rule_update.description is not None:
            rule.description = rule_update.description
        if rule_update.enabled is not None:
            rule.enabled = rule_update.enabled

        return {
            "success": True,
            "message": f"Alert rule '{rule.name}' updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update alert rule: {str(e)}")

@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: str,
    current_user = Depends(get_current_user)
):
    """删除告警规则"""
    try:
        rule = alert_engine.rules.get(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        rule_name = rule.name
        alert_engine.remove_rule(rule_id)

        return {
            "success": True,
            "message": f"Alert rule '{rule_name}' deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete alert rule: {str(e)}")

@router.post("/rules/{rule_id}/enable")
async def enable_alert_rule(
    rule_id: str,
    current_user = Depends(get_current_user)
):
    """启用告警规则"""
    try:
        if rule_id not in alert_engine.rules:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        alert_engine.enable_rule(rule_id)
        rule = alert_engine.rules[rule_id]

        return {
            "success": True,
            "message": f"Alert rule '{rule.name}' enabled successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable alert rule: {str(e)}")

@router.post("/rules/{rule_id}/disable")
async def disable_alert_rule(
    rule_id: str,
    current_user = Depends(get_current_user)
):
    """禁用告警规则"""
    try:
        if rule_id not in alert_engine.rules:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        alert_engine.disable_rule(rule_id)
        rule = alert_engine.rules[rule_id]

        return {
            "success": True,
            "message": f"Alert rule '{rule.name}' disabled successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable alert rule: {str(e)}")

# 告警事件管理
@router.get("/incidents")
async def list_alert_incidents(
    severity: Optional[AlertSeverity] = Query(None, description="按严重程度筛选"),
    status: Optional[AlertStatus] = Query(None, description="按状态筛选"),
    hours: int = Query(default=24, ge=1, le=168, description="时间范围（小时）"),
    current_user = Depends(get_current_user)
):
    """获取告警事件列表"""
    try:
        incidents = alert_engine.get_alert_history(hours)

        # 应用筛选条件
        if severity:
            incidents = [inc for inc in incidents if inc.severity == severity]
        if status:
            incidents = [inc for inc in incidents if inc.status == status]

        # 构建响应数据
        result = []
        for incident in incidents:
            result.append({
                "id": incident.id,
                "rule_id": incident.rule_id,
                "rule_name": alert_engine.rules.get(incident.rule_id, {}).name if incident.rule_id in alert_engine.rules else "Unknown",
                "status": incident.status.value,
                "severity": incident.severity.value,
                "message": incident.message,
                "trigger_value": incident.trigger_value,
                "triggered_at": incident.triggered_at.isoformat(),
                "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                "acknowledged_at": incident.acknowledged_at.isoformat() if incident.acknowledged_at else None,
                "acknowledged_by": incident.acknowledged_by,
                "notes": incident.notes,
                "context": incident.context
            })

        # 按触发时间倒序排序
        result.sort(key=lambda x: x["triggered_at"], reverse=True)

        return {
            "success": True,
            "data": {
                "incidents": result,
                "total_count": len(result),
                "period_hours": hours,
                "filters": {
                    "severity": severity.value if severity else None,
                    "status": status.value if status else None
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list alert incidents: {str(e)}")

@router.get("/incidents/active")
async def get_active_alerts(
    severity: Optional[AlertSeverity] = Query(None, description="按严重程度筛选"),
    current_user = Depends(get_current_user)
):
    """获取活跃告警"""
    try:
        incidents = alert_engine.get_active_alerts(severity)

        result = []
        for incident in incidents:
            result.append({
                "id": incident.id,
                "rule_id": incident.rule_id,
                "rule_name": alert_engine.rules.get(incident.rule_id, {}).name if incident.rule_id in alert_engine.rules else "Unknown",
                "severity": incident.severity.value,
                "message": incident.message,
                "trigger_value": incident.trigger_value,
                "triggered_at": incident.triggered_at.isoformat(),
                "duration_minutes": int((datetime.utcnow() - incident.triggered_at).total_seconds() / 60),
                "acknowledged": incident.acknowledged_at is not None,
                "acknowledged_by": incident.acknowledged_by,
                "context": incident.context
            })

        # 按严重程度和触发时间排序
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        result.sort(key=lambda x: (
            severity_order.get(x["severity"], 3),
            x["triggered_at"]
        ), reverse=True)

        return {
            "success": True,
            "data": {
                "active_alerts": result,
                "total_count": len(result),
                "severity_counts": {
                    "critical": len([a for a in result if a["severity"] == "critical"]),
                    "warning": len([a for a in result if a["severity"] == "warning"]),
                    "info": len([a for a in result if a["severity"] == "info"])
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active alerts: {str(e)}")

@router.post("/incidents/{incident_id}/acknowledge")
async def acknowledge_alert(
    incident_id: str,
    ack_data: AlertAcknowledge,
    current_user = Depends(get_current_user)
):
    """确认告警"""
    try:
        success = await alert_engine.acknowledge_alert(
            incident_id,
            current_user.get("id", "unknown"),
            ack_data.notes
        )

        if not success:
            raise HTTPException(status_code=404, detail="Alert incident not found or not active")

        return {
            "success": True,
            "message": f"Alert incident '{incident_id}' acknowledged successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")

@router.post("/incidents/{incident_id}/resolve")
async def resolve_alert(
    incident_id: str,
    resolve_data: AlertResolve,
    current_user = Depends(get_current_user)
):
    """解决告警"""
    try:
        success = await alert_engine.resolve_alert(
            incident_id,
            current_user.get("id", "unknown"),
            resolve_data.notes
        )

        if not success:
            raise HTTPException(status_code=404, detail="Alert incident not found or not active")

        return {
            "success": True,
            "message": f"Alert incident '{incident_id}' resolved successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve alert: {str(e)}")

# 统计和分析
@router.get("/stats")
async def get_alert_statistics(
    hours: int = Query(default=24, ge=1, le=168, description="统计时间范围（小时）"),
    current_user = Depends(get_current_user)
):
    """获取告警统计数据"""
    try:
        # 基础统计
        evaluation_stats = alert_engine.get_evaluation_stats(hours)
        incidents = alert_engine.get_alert_history(hours)
        active_alerts = alert_engine.get_active_alerts()

        # 按严重程度统计
        severity_counts = {"critical": 0, "warning": 0, "info": 0}
        for incident in incidents:
            severity_counts[incident.severity.value] += 1

        # 按规则统计
        rule_counts = {}
        for incident in incidents:
            rule_name = alert_engine.rules.get(incident.rule_id, {}).name if incident.rule_id in alert_engine.rules else "Unknown"
            rule_counts[rule_name] = rule_counts.get(rule_name, 0) + 1

        # 按时间分布统计
        hourly_distribution = {}
        for incident in incidents:
            hour = incident.triggered_at.hour
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1

        # 解决时间统计
        resolved_incidents = [inc for inc in incidents if inc.resolved_at]
        avg_resolution_time = 0
        if resolved_incidents:
            total_resolution_time = sum(
                (inc.resolved_at - inc.triggered_at).total_seconds()
                for inc in resolved_incidents
            )
            avg_resolution_time = total_resolution_time / len(resolved_incidents)

        return {
            "success": True,
            "data": {
                "period_hours": hours,
                "evaluation_stats": evaluation_stats,
                "incident_stats": {
                    "total_incidents": len(incidents),
                    "active_incidents": len(active_alerts),
                    "resolved_incidents": len(resolved_incidents),
                    "severity_distribution": severity_counts,
                    "top_rules": sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:10],
                    "hourly_distribution": hourly_distribution,
                    "avg_resolution_time_minutes": avg_resolution_time / 60 if avg_resolution_time > 0 else 0
                },
                "rule_stats": {
                    "total_rules": len(alert_engine.rules),
                    "enabled_rules": len([r for r in alert_engine.rules.values() if r.enabled]),
                    "disabled_rules": len([r for r in alert_engine.rules.values() if not r.enabled])
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert statistics: {str(e)}")

# 系统管理
@router.post("/load-default-rules")
async def load_default_rules(
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """加载默认告警规则"""
    try:
        # 在后台任务中加载规则
        background_tasks.add_task(load_default_alert_rules)

        return {
            "success": True,
            "message": "Default alert rules are being loaded in background"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load default rules: {str(e)}")

@router.get("/categories")
async def get_alert_categories(
    current_user = Depends(get_current_user)
):
    """获取告警分类列表"""
    try:
        categories = {}
        for rule in DEFAULT_ALERT_RULES:
            if rule.tags and "category" in rule.tags:
                category = rule.tags["category"]
                if category not in categories:
                    categories[category] = {
                        "name": category,
                        "rules_count": 0,
                        "enabled_count": 0,
                        "severity_distribution": {"critical": 0, "warning": 0, "info": 0}
                    }

                categories[category]["rules_count"] += 1
                if rule.enabled:
                    categories[category]["enabled_count"] += 1
                categories[category]["severity_distribution"][rule.severity.value] += 1

        return {
            "success": True,
            "data": {
                "categories": list(categories.values()),
                "total_categories": len(categories)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert categories: {str(e)}")

@router.post("/test-notification")
async def test_notification(
    test_data: NotificationTest,
    current_user = Depends(get_current_user)
):
    """测试告警通知"""
    try:
        # 创建测试告警数据
        notification_data = {
            "incident_id": f"test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "rule_id": "test_rule",
            "severity": test_data.severity.value,
            "message": f"[TEST] {test_data.message}",
            "trigger_value": "N/A",
            "triggered_at": datetime.utcnow().isoformat(),
            "context": {
                "test": True,
                "user": current_user.get("id", "unknown"),
                "channels": test_data.channels
            }
        }

        # 发送测试通知
        from backend.monitoring.notifications import notification_manager
        await notification_manager.send_alert(notification_data, test_data.channels)

        return {
            "success": True,
            "message": f"Test notification sent to channels: {', '.join(test_data.channels)}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test notification: {str(e)}")