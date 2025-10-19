"""
审计日志服务 - Week 3 扩展功能增强
记录所有用户操作和系统事件，提供完整的审计追踪
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from ..models.audit import AuditLog, AuditAction, AuditResource
from ..models.organization import Organization
from ..models.user import User
from ..core.auth import get_current_user

logger = logging.getLogger(__name__)

class AuditService:
    """审计日志服务"""

    def __init__(self, db: Session):
        self.db = db

    async def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> AuditLog:
        """记录审计日志"""
        try:
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                organization_id=organization_id,
                old_values=old_values or {},
                new_values=new_values or {},
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata or {},
                created_at=datetime.now(timezone.utc)
            )

            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(audit_log)

            logger.info(f"Audit log created: {action} on {resource_type}:{resource_id} by user {user_id}")
            return audit_log

        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")
            self.db.rollback()
            raise

    async def log_user_action(
        self,
        action: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> AuditLog:
        """记录用户操作日志"""
        return await self.log_action(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            organization_id=organization_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent
        )

    async def log_system_action(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict] = None,
        organization_id: Optional[str] = None
    ) -> AuditLog:
        """记录系统操作日志"""
        return await self.log_action(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            organization_id=organization_id,
            metadata=details
        )

    async def log_security_event(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        severity: str = "medium",
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """记录安全事件日志"""
        metadata = {
            "event_type": "security",
            "severity": severity,
            **(details or {})
        }

        return await self.log_action(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            organization_id=organization_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata
        )

    def get_audit_logs(
        self,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 50,
        severity: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取审计日志列表"""
        try:
            query = self.db.query(AuditLog)

            # 构建筛选条件
            if organization_id:
                query = query.filter(AuditLog.organization_id == organization_id)

            if user_id:
                query = query.filter(AuditLog.user_id == user_id)

            if action:
                query = query.filter(AuditLog.action == action)

            if resource_type:
                query = query.filter(AuditLog.resource_type == resource_type)

            if resource_id:
                query = query.filter(AuditLog.resource_id == resource_id)

            if start_date:
                query = query.filter(AuditLog.created_at >= start_date)

            if end_date:
                query = query.filter(AuditLog.created_at <= end_date)

            # 安全事件筛选
            if severity:
                query = query.filter(
                    AuditLog.metadata['event_type'].astext == 'security',
                    AuditLog.metadata['severity'].astext == severity
                )

            # 排序
            query = query.order_by(desc(AuditLog.created_at))

            # 分页
            total = query.count()
            logs = query.offset((page - 1) * limit).limit(limit).all()

            return {
                "logs": [
                    {
                        "id": log.id,
                        "action": log.action,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "user_id": log.user_id,
                        "organization_id": log.organization_id,
                        "old_values": log.old_values,
                        "new_values": log.new_values,
                        "ip_address": log.ip_address,
                        "user_agent": log.user_agent,
                        "metadata": log.metadata or {},
                        "created_at": log.created_at.isoformat() if log.created_at else None
                    }
                    for log in logs
                ],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            }

        except Exception as e:
            logger.error(f"Error getting audit logs: {str(e)}")
            raise

    def get_user_activity_summary(
        self,
        organization_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取用户活动摘要"""
        try:
            query = self.db.query(AuditLog).filter(
                AuditLog.organization_id == organization_id
            )

            if start_date:
                query = query.filter(AuditLog.created_at >= start_date)

            if end_date:
                query = query.filter(AuditLog.created_at <= end_date)

            # 统计各类型操作数量
            action_counts = {}
            for log in query.all():
                action = log.action
                if action not in action_counts:
                    action_counts[action] = 0
                action_counts[action] += 1

            # 统计用户数量
            unique_users = query.with_entities(
                AuditLog.user_id
            ).distinct().count()

            # 统计资源类型
            resource_types = {}
            for log in query.all():
                resource = log.resource_type
                if resource not in resource_types:
                    resource_types[resource] = 0
                resource_types[resource] += 1

            # 获取最近的操作
            recent_logs = query.order_by(desc(AuditLog.created_at)).limit(10).all()

            return {
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                },
                "summary": {
                    "total_actions": len(query.all()),
                    "unique_users": unique_users,
                    "action_counts": action_counts,
                    "resource_types": resource_types
                },
                "recent_activities": [
                    {
                        "id": log.id,
                        "action": log.action,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "user_id": log.user_id,
                        "created_at": log.created_at.isoformat() if log.created_at else None,
                        "ip_address": log.ip_address
                    }
                    for log in recent_logs
                ]
            }

        except Exception as e:
            logger.error(f"Error getting activity summary: {str(e)}")
            raise

    def get_security_events(
        self,
        organization_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        severity: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取安全事件日志"""
        try:
            query = self.db.query(AuditLog).filter(
                and_(
                    AuditLog.organization_id == organization_id,
                    AuditLog.metadata['event_type'].astext == 'security'
                )
            )

            if start_date:
                query = query.filter(AuditLog.created_at >= start_date)

            if end_date:
                query = query.filter(AuditLog.created_at <= end_date)

            if severity:
                query = query.filter(
                    AuditLog.metadata['severity'].astext == severity
                )

            events = query.order_by(desc(AuditLog.created_at)).all()

            # 按严重程度分类
            events_by_severity = {}
            for event in events:
                sev = event.metadata.get('severity', 'medium')
                if sev not in events_by_severity:
                    events_by_severity[sev] = []
                events_by_severity[sev].append({
                    "id": event.id,
                    "action": event.action,
                    "resource_type": event.resource_type,
                    "resource_id": event.resource_id,
                    "user_id": event.user_id,
                    "created_at": event.created_at.isoformat(),
                    "ip_address": event.ip_address,
                    "metadata": event.metadata
                })

            return {
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                },
                "total_events": len(events),
                "events_by_severity": events_by_severity,
                "all_events": [
                    {
                        "id": event.id,
                        "action": event.action,
                        "resource_type": event.resource_type,
                        "resource_id": event.resource_id,
                        "user_id": event.user_id,
                        "created_at": event.created_at.isoformat() if event.created_at else None,
                        "ip_address": event.ip_address,
                        "metadata": event.metadata
                    }
                    for event in events
                ]
            }

        except Exception as e:
            logger.error(f"Error getting security events: {str(e)}")
            raise

    def get_resource_audit_trail(
        self,
        resource_type: str,
        resource_id: str,
        organization_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """获取特定资源的审计轨迹"""
        try:
            logs = self.db.query(AuditLog).filter(
                and_(
                    AuditLog.organization_id == organization_id,
                    AuditLog.resource_type == resource_type,
                    AuditLog.resource_id == resource_id
                )
            ).order_by(desc(AuditLog.created_at)).limit(limit).all()

            return [
                {
                    "id": log.id,
                    "action": log.action,
                    "user_id": log.user_id,
                    "old_values": log.old_values,
                    "new_values": log.new_values,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "metadata": log.metadata or {},
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                for log in logs
            ]

        except Exception as e:
            logger.error(f"Error getting audit trail: {str(e)}")
            raise

    def export_audit_logs(
        self,
        organization_id: str,
        format: str = "json",
        filters: Optional[Dict] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> bytes:
        """导出审计日志"""
        try:
            # 获取符合条件的数据
            logs_data = self.get_audit_logs(
                organization_id=organization_id,
                **(filters or {}),
                start_date=start_date,
                end_date=end_date,
                page=1,
                limit=10000  # 大量导出
            )

            if format.lower() == "csv":
                return self._export_to_csv(logs_data["logs"])
            else:
                return self._export_to_json(logs_data["logs"])

        except Exception as e:
            logger.error(f"Error exporting audit logs: {str(e)}")
            raise

    def _export_to_json(self, logs: List[Dict]) -> bytes:
        """导出为JSON格式"""
        data = {
            "export_date": datetime.now(timezone.utc).isoformat(),
            "total_records": len(logs),
            "logs": logs
        }
        return json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')

    def _export_to_csv(self, logs: List[Dict]) -> bytes:
        """导出为CSV格式"""
        import csv
        from io import StringIO

        output = StringIO()
        if logs:
            writer = csv.DictWriter(output, fieldnames=logs[0].keys())
            writer.writeheader()
            writer.writerows(logs)

        return output.getvalue().encode('utf-8')

# 预定义的审计动作类型
class AuditActions:
    # 用户相关
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"

    # 组织相关
    ORG_CREATE = "org_create"
    ORG_UPDATE = "org_update"
    ORG_DELETE = "org_delete"
    ORG_MEMBER_ADD = "org_member_add"
    ORG_MEMBER_REMOVE = "org_member_remove"
    ORG_MEMBER_UPDATE = "org_member_update"

    # 团队相关
    TEAM_CREATE = "team_create"
    TEAM_UPDATE = "team_update"
    TEAM_DELETE = "team_delete"
    TEAM_MEMBER_ADD = "team_member_add"
    TEAM_MEMBER_REMOVE = "team_member_remove"

    # API密钥相关
    API_KEY_CREATE = "api_key_create"
    API_KEY_UPDATE = "api_key_update"
    API_KEY_DELETE = "api_key_delete"
    API_KEY_ACTIVATE = "api_key_activate"
    API_KEY_DEACTIVATE = "api_key_deactivate"

    # 订阅相关
    SUBSCRIPTION_CREATE = "subscription_create"
    SUBSCRIPTION_UPDATE = "subscription_update"
    SUBSCRIPTION_CANCEL = "subscription_cancel"
    SUBSCRIPTION_UPGRADE = "subscription_upgrade"
    SUBSCRIPTION_DOWNGRADE = "subscription_downgrade"
    SUBSCRIPTION_REACTIVATE = "subscription_reactivate"

    # 支付相关
    PAYMENT_INTENT_CREATE = "payment_intent_create"
    PAYMENT_CONFIRM = "payment_confirm"
    PAYMENT_SUCCEED = "payment_succeed"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_REFUND = "payment_refund"

    # 安全相关
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    PERMISSION_DENIED = "permission_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_EXPORT = "data_export"

    # 系统相关
    SYSTEM_ERROR = "system_error"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"
    MAINTENANCE_MODE = "maintenance_mode"

# 预定义的资源类型
class AuditResources:
    USER = "user"
    ORGANIZATION = "organization"
    TEAM = "team"
    API_KEY = "api_key"
    SUBSCRIPTION = "subscription"
    PAYMENT = "payment"
    INVOICE = "invoice"
    BUDGET = "budget"
    SESSION = "session"
    SYSTEM = "system"

# 全局审计服务实例
def get_audit_service(db: Session) -> AuditService:
    return AuditService(db)