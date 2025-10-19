"""
审计日志API - Week 3 扩展功能增强
提供完整的审计日志查询、导出和管理功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from ..database import get_db
from ..services.audit_service import AuditService, AuditActions, AuditResources
from ..models.audit import AuditSeverity
from ..core.auth import get_current_user, get_current_organization
from ..models.user import User
from ..models.organization import Organization

# 创建路由器
router = APIRouter()


# 请求/响应模型
class AuditLogRequest(BaseModel):
    """审计日志创建请求"""
    action: str
    resource_type: str
    resource_id: str
    old_values: Optional[Dict] = None
    new_values: Optional[Dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[Dict] = None


class SecurityEventRequest(BaseModel):
    """安全事件记录请求"""
    action: str
    resource_type: str
    resource_id: str
    user_id: Optional[str] = None
    severity: Optional[str] = "medium"
    details: Optional[Dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ExportRequest(BaseModel):
    """审计日志导出请求"""
    format: str = "json"  # json, csv
    filters: Optional[Dict] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@router.get("/logs")
async def get_audit_logs(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    severity: Optional[str] = Query(None)
):
    """获取审计日志列表"""
    try:
        audit_service = AuditService(db)

        # 验证严重程度参数
        if severity and severity not in [s.value for s in AuditSeverity]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity. Must be one of: {[s.value for s in AuditSeverity]}"
            )

        result = audit_service.get_audit_logs(
            organization_id=str(organization.id),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            start_date=start_date,
            end_date=end_date,
            page=page,
            limit=limit,
            severity=severity
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/summary")
async def get_activity_summary(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """获取用户活动摘要"""
    try:
        audit_service = AuditService(db)

        # 如果没有指定时间范围，默认为最近30天
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        summary = audit_service.get_user_activity_summary(
            organization_id=str(organization.id),
            start_date=start_date,
            end_date=end_date
        )

        return {
            "success": True,
            "data": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/security")
async def get_security_events(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    severity: Optional[str] = Query(None)
):
    """获取安全事件日志"""
    try:
        audit_service = AuditService(db)

        # 验证严重程度参数
        if severity and severity not in [s.value for s in AuditSeverity]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity. Must be one of: {[s.value for s in AuditSeverity]}"
            )

        events = audit_service.get_security_events(
            organization_id=str(organization.id),
            start_date=start_date,
            end_date=end_date,
            severity=severity
        )

        return {
            "success": True,
            "data": events
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/trail/{resource_type}/{resource_id}")
async def get_resource_audit_trail(
    resource_type: str,
    resource_id: str,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200)
):
    """获取特定资源的审计轨迹"""
    try:
        audit_service = AuditService(db)

        # 验证资源类型
        valid_resources = [r.value for r in AuditResources]
        if resource_type not in valid_resources:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid resource_type. Must be one of: {valid_resources}"
            )

        trail = audit_service.get_resource_audit_trail(
            resource_type=resource_type,
            resource_id=resource_id,
            organization_id=str(organization.id),
            limit=limit
        )

        return {
            "success": True,
            "data": trail
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logs")
async def create_audit_log(
    request: AuditLogRequest,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """创建审计日志"""
    try:
        audit_service = AuditService(db)

        # 验证动作和资源类型
        valid_actions = [a.value for a in AuditActions]
        if request.action not in valid_actions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action. Must be one of: {valid_actions[:10]}..."  # 只显示前10个
            )

        valid_resources = [r.value for r in AuditResources]
        if request.resource_type not in valid_resources:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid resource_type. Must be one of: {valid_resources}"
            )

        log = await audit_service.log_user_action(
            action=request.action,
            user_id=str(user.id),
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            old_values=request.old_values,
            new_values=request.new_values,
            ip_address=request.ip_address,
            user_agent=request.user_agent,
            organization_id=str(organization.id)
        )

        return {
            "success": True,
            "data": {
                "id": str(log.id),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "created_at": log.created_at.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logs/security")
async def create_security_event(
    request: SecurityEventRequest,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """记录安全事件"""
    try:
        audit_service = AuditService(db)

        # 验证严重程度
        if request.severity not in [s.value for s in AuditSeverity]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity. Must be one of: {[s.value for s in AuditSeverity]}"
            )

        log = await audit_service.log_security_event(
            action=request.action,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            user_id=request.user_id,
            organization_id=str(organization.id),
            severity=request.severity,
            details=request.details,
            ip_address=request.ip_address,
            user_agent=request.user_agent
        )

        return {
            "success": True,
            "data": {
                "id": str(log.id),
                "action": log.action,
                "severity": request.severity,
                "created_at": log.created_at.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logs/export")
async def export_audit_logs(
    request: ExportRequest,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """导出审计日志"""
    try:
        audit_service = AuditService(db)

        # 验证导出格式
        if request.format not in ["json", "csv"]:
            raise HTTPException(
                status_code=400,
                detail="Format must be 'json' or 'csv'"
            )

        # 如果没有指定时间范围，默认为最近30天
        if not request.start_date:
            request.start_date = datetime.utcnow() - timedelta(days=30)
        if not request.end_date:
            request.end_date = datetime.utcnow()

        # 验证时间范围不超过90天
        if (request.end_date - request.start_date).days > 90:
            raise HTTPException(
                status_code=400,
                detail="Date range cannot exceed 90 days"
            )

        data = audit_service.export_audit_logs(
            organization_id=str(organization.id),
            format=request.format,
            filters=request.filters,
            start_date=request.start_date,
            end_date=request.end_date
        )

        # 设置下载文件名
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"audit_logs_{organization.name}_{timestamp}.{request.format}"

        # 返回文件下载响应
        content_type = "application/json" if request.format == "json" else "text/csv"

        return Response(
            content=data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(data))
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions")
async def get_audit_actions():
    """获取可用的审计动作列表"""
    return {
        "success": True,
        "data": {
            "actions": [{"value": a.value, "label": a.value.replace("_", " ").title()}
                       for a in AuditActions],
            "total": len(AuditActions)
        }
    }


@router.get("/resources")
async def get_audit_resources():
    """获取可用的资源类型列表"""
    return {
        "success": True,
        "data": {
            "resources": [{"value": r.value, "label": r.value.replace("_", " ").title()}
                         for r in AuditResources],
            "total": len(AuditResources)
        }
    }


@router.get("/severities")
async def get_audit_severities():
    """获取可用的事件严重程度列表"""
    return {
        "success": True,
        "data": {
            "severities": [{"value": s.value, "label": s.value.title()}
                          for s in AuditSeverity],
            "total": len(AuditSeverity)
        }
    }


@router.get("/stats")
async def get_audit_statistics(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365)
):
    """获取审计统计信息"""
    try:
        audit_service = AuditService(db)

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 获取活动摘要
        summary = audit_service.get_user_activity_summary(
            organization_id=str(organization.id),
            start_date=start_date,
            end_date=end_date
        )

        # 获取安全事件
        security_events = audit_service.get_security_events(
            organization_id=str(organization.id),
            start_date=start_date,
            end_date=end_date
        )

        return {
            "success": True,
            "data": {
                "period": {
                    "days": days,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "activity_summary": summary["summary"],
                "security_summary": {
                    "total_events": security_events["total_events"],
                    "events_by_severity": security_events["events_by_severity"]
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))