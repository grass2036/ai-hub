"""
权限管理服务 - Week 3 扩展功能增强
实现基于角色的访问控制(RBAC)和细粒度权限管理
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from ..models.permissions import (
    Permission, Role, UserRole, ResourcePermission,
    PermissionTemplate, AccessLog, PermissionScope, PermissionAction
)
from ..models.user import User
from ..models.organization import Organization
from ..core.auth import get_current_user

logger = logging.getLogger(__name__)


class PermissionService:
    """权限管理服务"""

    def __init__(self, db: Session):
        self.db = db

    async def create_permission(
        self,
        name: str,
        display_name: str,
        description: str,
        scope: str,
        action: str,
        resource_type: Optional[str] = None,
        conditions: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> Permission:
        """创建权限"""
        try:
            permission = Permission(
                id=str(uuid.uuid4()),
                name=name,
                display_name=display_name,
                description=description,
                scope=scope,
                action=action,
                resource_type=resource_type,
                conditions=conditions or {},
                metadata=metadata or {},
                created_at=datetime.now(timezone.utc)
            )

            self.db.add(permission)
            self.db.commit()
            self.db.refresh(permission)

            logger.info(f"Permission created: {name}")
            return permission

        except Exception as e:
            logger.error(f"Error creating permission: {str(e)}")
            self.db.rollback()
            raise

    async def create_role(
        self,
        name: str,
        display_name: str,
        description: str,
        scope: str,
        level: int = 0,
        parent_role_id: Optional[str] = None,
        permission_ids: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Role:
        """创建角色"""
        try:
            role = Role(
                id=str(uuid.uuid4()),
                name=name,
                display_name=display_name,
                description=description,
                scope=scope,
                level=level,
                parent_role_id=parent_role_id,
                metadata=metadata or {},
                created_at=datetime.now(timezone.utc)
            )

            self.db.add(role)
            self.db.flush()  # 获取角色ID

            # 添加权限到角色
            if permission_ids:
                permissions = self.db.query(Permission).filter(
                    Permission.id.in_(permission_ids)
                ).all()
                role.permissions.extend(permissions)

            self.db.commit()
            self.db.refresh(role)

            logger.info(f"Role created: {name}")
            return role

        except Exception as e:
            logger.error(f"Error creating role: {str(e)}")
            self.db.rollback()
            raise

    async def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        organization_id: Optional[str] = None,
        team_id: Optional[str] = None,
        assigned_by: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        restrictions: Optional[Dict] = None
    ) -> UserRole:
        """为用户分配角色"""
        try:
            user_role = UserRole(
                id=str(uuid.uuid4()),
                user_id=user_id,
                role_id=role_id,
                organization_id=organization_id,
                team_id=team_id,
                assigned_by=assigned_by,
                expires_at=expires_at,
                restrictions=restrictions or {},
                assigned_at=datetime.now(timezone.utc)
            )

            self.db.add(user_role)
            self.db.commit()
            self.db.refresh(user_role)

            logger.info(f"Role assigned to user: user_id={user_id}, role_id={role_id}")
            return user_role

        except Exception as e:
            logger.error(f"Error assigning role to user: {str(e)}")
            self.db.rollback()
            raise

    async def grant_resource_permission(
        self,
        resource_type: str,
        resource_id: str,
        user_id: str,
        permission_action: str,
        granted_by: str,
        organization_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        conditions: Optional[Dict] = None
    ) -> ResourcePermission:
        """授予资源权限"""
        try:
            resource_permission = ResourcePermission(
                id=str(uuid.uuid4()),
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                permission_action=permission_action,
                granted_by=granted_by,
                organization_id=organization_id,
                expires_at=expires_at,
                conditions=conditions or {},
                granted_at=datetime.now(timezone.utc)
            )

            self.db.add(resource_permission)
            self.db.commit()
            self.db.refresh(resource_permission)

            logger.info(f"Resource permission granted: {resource_type}:{resource_id} to user {user_id}")
            return resource_permission

        except Exception as e:
            logger.error(f"Error granting resource permission: {str(e)}")
            self.db.rollback()
            raise

    async def check_permission(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """检查用户权限"""
        try:
            result = {
                "granted": False,
                "source": None,
                "reason": None,
                "conditions": {}
            }

            # 1. 检查直接资源权限
            if resource_id:
                direct_permission = self._check_direct_resource_permission(
                    user_id, action, resource_type, resource_id, organization_id
                )
                if direct_permission["granted"]:
                    return direct_permission

            # 2. 检查角色权限
            role_permission = await self._check_role_permission(
                user_id, action, resource_type, resource_id, organization_id, context
            )
            if role_permission["granted"]:
                return role_permission

            # 3. 检查组织级权限
            if organization_id:
                org_permission = await self._check_organization_permission(
                    user_id, action, resource_type, organization_id, context
                )
                if org_permission["granted"]:
                    return org_permission

            result["reason"] = "No matching permissions found"
            return result

        except Exception as e:
            logger.error(f"Error checking permission: {str(e)}")
            return {
                "granted": False,
                "source": "error",
                "reason": str(e),
                "conditions": {}
            }

    def _check_direct_resource_permission(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        organization_id: Optional[str]
    ) -> Dict[str, Any]:
        """检查直接资源权限"""
        permission = self.db.query(ResourcePermission).filter(
            and_(
                ResourcePermission.user_id == user_id,
                ResourcePermission.resource_type == resource_type,
                ResourcePermission.resource_id == resource_id,
                ResourcePermission.permission_action == action,
                ResourcePermission.is_active == True,
                ResourcePermission.is_denied == False,
                or_(
                    ResourcePermission.expires_at.is_(None),
                    ResourcePermission.expires_at > datetime.now(timezone.utc)
                )
            )
        ).first()

        if permission:
            return {
                "granted": True,
                "source": "direct_resource",
                "reason": f"Direct permission granted on {resource_type}:{resource_id}",
                "conditions": permission.conditions
            }

        return {"granted": False, "source": None, "reason": None, "conditions": {}}

    async def _check_role_permission(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        organization_id: Optional[str],
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """检查角色权限"""
        # 获取用户的有效角色
        user_roles = self.db.query(UserRole).filter(
            and_(
                UserRole.user_id == user_id,
                UserRole.is_active == True,
                or_(
                    UserRole.expires_at.is_(None),
                    UserRole.expires_at > datetime.now(timezone.utc)
                )
            )
        ).all()

        for user_role in user_roles:
            # 获取角色权限
            role = self.db.query(Role).filter(
                Role.id == user_role.role_id,
                Role.is_active == True
            ).first()

            if not role:
                continue

            # 检查角色权限
            for permission in role.permissions:
                if (permission.action == action and
                    permission.resource_type == resource_type and
                    permission.is_active):

                    # 检查权限条件
                    if self._evaluate_conditions(permission.conditions, context):
                        return {
                            "granted": True,
                            "source": "role",
                            "reason": f"Permission granted via role {role.name}",
                            "conditions": permission.conditions
                        }

        return {"granted": False, "source": None, "reason": None, "conditions": {}}

    async def _check_organization_permission(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        organization_id: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """检查组织级权限"""
        # 获取用户在组织中的角色
        user_roles = self.db.query(UserRole).filter(
            and_(
                UserRole.user_id == user_id,
                UserRole.organization_id == organization_id,
                UserRole.is_active == True,
                or_(
                    UserRole.expires_at.is_(None),
                    UserRole.expires_at > datetime.now(timezone.utc)
                )
            )
        ).all()

        for user_role in user_roles:
            role = self.db.query(Role).filter(
                and_(
                    Role.id == user_role.role_id,
                    Role.scope == "organization",
                    Role.is_active == True
                )
            ).first()

            if not role:
                continue

            # 检查组织级权限
            for permission in role.permissions:
                if (permission.action == action and
                    permission.scope == "organization" and
                    permission.is_active):

                    if self._evaluate_conditions(permission.conditions, context):
                        return {
                            "granted": True,
                            "source": "organization_role",
                            "reason": f"Organization permission granted via role {role.name}",
                            "conditions": permission.conditions
                        }

        return {"granted": False, "source": None, "reason": None, "conditions": {}}

    def _evaluate_conditions(self, conditions: Dict, context: Optional[Dict]) -> bool:
        """评估权限条件"""
        if not conditions or not context:
            return True

        # 这里可以实现复杂的条件评估逻辑
        # 例如：时间限制、IP限制、资源限制等

        if "time_range" in conditions:
            # 检查时间范围
            current_time = datetime.now(timezone.utc)
            start_time = conditions["time_range"].get("start")
            end_time = conditions["time_range"].get("end")

            if start_time and current_time < datetime.fromisoformat(start_time):
                return False
            if end_time and current_time > datetime.fromisoformat(end_time):
                return False

        if "ip_ranges" in conditions:
            # 检查IP范围
            user_ip = context.get("ip_address")
            if user_ip and not self._check_ip_in_ranges(user_ip, conditions["ip_ranges"]):
                return False

        return True

    def _check_ip_in_ranges(self, ip: str, ranges: List[str]) -> bool:
        """检查IP是否在允许范围内"""
        # 简化的IP检查逻辑
        for ip_range in ranges:
            if ip.startswith(ip_range):
                return True
        return False

    async def log_access(
        self,
        user_id: Optional[str],
        organization_id: Optional[str],
        resource_type: str,
        resource_id: str,
        action: str,
        permission_result: str,
        permission_source: Optional[str] = None,
        required_permissions: Optional[List[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_path: Optional[str] = None,
        request_method: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> AccessLog:
        """记录访问日志"""
        try:
            access_log = AccessLog(
                id=str(uuid.uuid4()),
                user_id=user_id,
                organization_id=organization_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                permission_result=permission_result,
                permission_source=permission_source,
                required_permissions=required_permissions or [],
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request_path,
                request_method=request_method,
                metadata=metadata or {},
                created_at=datetime.now(timezone.utc)
            )

            self.db.add(access_log)
            self.db.commit()
            self.db.refresh(access_log)

            return access_log

        except Exception as e:
            logger.error(f"Error logging access: {str(e)}")
            self.db.rollback()
            raise

    def get_user_permissions(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        include_inherited: bool = True
    ) -> List[Dict[str, Any]]:
        """获取用户权限列表"""
        try:
            permissions = []

            # 1. 获取直接资源权限
            direct_permissions = self.db.query(ResourcePermission).filter(
                and_(
                    ResourcePermission.user_id == user_id,
                    ResourcePermission.is_active == True,
                    ResourcePermission.is_denied == False,
                    or_(
                        ResourcePermission.expires_at.is_(None),
                        ResourcePermission.expires_at > datetime.now(timezone.utc)
                    )
                )
            ).all()

            for perm in direct_permissions:
                permissions.append({
                    "id": str(perm.id),
                    "type": "direct",
                    "resource_type": perm.resource_type,
                    "resource_id": perm.resource_id,
                    "action": perm.permission_action,
                    "source": "direct",
                    "conditions": perm.conditions,
                    "expires_at": perm.expires_at.isoformat() if perm.expires_at else None
                })

            # 2. 获取角色权限
            user_roles = self.db.query(UserRole).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.is_active == True,
                    or_(
                        UserRole.expires_at.is_(None),
                        UserRole.expires_at > datetime.now(timezone.utc)
                    )
                )
            ).all()

            for user_role in user_roles:
                role = self.db.query(Role).filter(Role.id == user_role.role_id).first()
                if role:
                    for perm in role.permissions:
                        if perm.is_active:
                            permissions.append({
                                "id": str(perm.id),
                                "type": "role",
                                "resource_type": perm.resource_type,
                                "action": perm.action,
                                "scope": perm.scope,
                                "source": f"role:{role.name}",
                                "conditions": perm.conditions,
                                "role_id": str(role.id),
                                "role_name": role.name
                            })

            return permissions

        except Exception as e:
            logger.error(f"Error getting user permissions: {str(e)}")
            raise

    def get_role_users(
        self,
        role_id: str,
        organization_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """获取角色用户列表"""
        try:
            query = self.db.query(UserRole).filter(UserRole.role_id == role_id)

            if organization_id:
                query = query.filter(UserRole.organization_id == organization_id)

            if active_only:
                query = query.filter(
                    and_(
                        UserRole.is_active == True,
                        or_(
                            UserRole.expires_at.is_(None),
                            UserRole.expires_at > datetime.now(timezone.utc)
                        )
                    )
                )

            user_roles = query.all()

            result = []
            for user_role in user_roles:
                user = self.db.query(User).filter(User.id == user_role.user_id).first()
                if user:
                    result.append({
                        "user_id": str(user.id),
                        "user_email": user.email,
                        "user_name": user.full_name or user.email,
                        "assigned_at": user_role.assigned_at.isoformat(),
                        "expires_at": user_role.expires_at.isoformat() if user_role.expires_at else None,
                        "is_active": user_role.is_active
                    })

            return result

        except Exception as e:
            logger.error(f"Error getting role users: {str(e)}")
            raise

    async def revoke_permission(
        self,
        permission_id: str,
        revoked_by: str
    ) -> bool:
        """撤销权限"""
        try:
            permission = self.db.query(ResourcePermission).filter(
                ResourcePermission.id == permission_id
            ).first()

            if permission:
                self.db.delete(permission)
                self.db.commit()
                logger.info(f"Permission revoked: {permission_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error revoking permission: {str(e)}")
            self.db.rollback()
            raise

    async def remove_user_role(
        self,
        user_id: str,
        role_id: str,
        organization_id: Optional[str] = None
    ) -> bool:
        """移除用户角色"""
        try:
            query = self.db.query(UserRole).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role_id
                )
            )

            if organization_id:
                query = query.filter(UserRole.organization_id == organization_id)

            user_role = query.first()

            if user_role:
                self.db.delete(user_role)
                self.db.commit()
                logger.info(f"User role removed: user_id={user_id}, role_id={role_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error removing user role: {str(e)}")
            self.db.rollback()
            raise


# 预定义权限常量
class SystemPermissions:
    """系统预定义权限"""

    # 用户管理权限
    USER_CREATE = "user.create"
    USER_READ = "user.read"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_ADMIN = "user.admin"

    # 组织管理权限
    ORG_CREATE = "organization.create"
    ORG_READ = "organization.read"
    ORG_UPDATE = "organization.update"
    ORG_DELETE = "organization.delete"
    ORG_ADMIN = "organization.admin"

    # 团队管理权限
    TEAM_CREATE = "team.create"
    TEAM_READ = "team.read"
    TEAM_UPDATE = "team.update"
    TEAM_DELETE = "team.delete"
    TEAM_ADMIN = "team.admin"

    # API密钥权限
    API_KEY_CREATE = "api_key.create"
    API_KEY_READ = "api_key.read"
    API_KEY_UPDATE = "api_key.update"
    API_KEY_DELETE = "api_key.delete"
    API_KEY_EXECUTE = "api_key.execute"

    # 财务权限
    BILLING_READ = "billing.read"
    BILLING_UPDATE = "billing.update"
    INVOICE_READ = "invoice.read"
    PAYMENT_PROCESS = "payment.process"

    # 审计权限
    AUDIT_READ = "audit.read"
    AUDIT_EXPORT = "audit.export"

    # 系统权限
    SYSTEM_ADMIN = "system.admin"
    SYSTEM_CONFIG = "system.config"


# 预定义角色常量
class SystemRoles:
    """系统预定义角色"""

    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    TEAM_ADMIN = "team_admin"
    DEVELOPER = "developer"
    USER = "user"
    VIEWER = "viewer"


# 全局权限服务实例
def get_permission_service(db: Session) -> PermissionService:
    return PermissionService(db)