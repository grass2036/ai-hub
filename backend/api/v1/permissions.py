"""
权限管理API - Week 3 扩展功能增强
提供完整的权限管理、角色管理和访问控制功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from ..database import get_db
from ..services.permission_service import PermissionService, SystemPermissions, SystemRoles
from ..core.auth import get_current_user, get_current_organization
from ..models.user import User
from ..models.organization import Organization

# 创建路由器
router = APIRouter()


# 请求/响应模型
class PermissionRequest(BaseModel):
    """权限创建请求"""
    name: str
    display_name: str
    description: str
    scope: str
    action: str
    resource_type: Optional[str] = None
    conditions: Optional[Dict] = None
    metadata: Optional[Dict] = None


class RoleRequest(BaseModel):
    """角色创建请求"""
    name: str
    display_name: str
    description: str
    scope: str
    level: int = 0
    parent_role_id: Optional[str] = None
    permission_ids: Optional[List[str]] = None
    metadata: Optional[Dict] = None


class RoleAssignmentRequest(BaseModel):
    """角色分配请求"""
    user_id: str
    role_id: str
    organization_id: Optional[str] = None
    team_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    restrictions: Optional[Dict] = None


class ResourcePermissionRequest(BaseModel):
    """资源权限请求"""
    resource_type: str
    resource_id: str
    user_id: str
    permission_action: str
    expires_at: Optional[datetime] = None
    conditions: Optional[Dict] = None


class PermissionCheckRequest(BaseModel):
    """权限检查请求"""
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    organization_id: Optional[str] = None
    context: Optional[Dict] = None


@router.get("/permissions")
async def get_permissions(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    scope: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200)
):
    """获取权限列表"""
    try:
        from ..models.permissions import Permission

        query = db.query(Permission).filter(Permission.is_active == True)

        if scope:
            query = query.filter(Permission.scope == scope)
        if action:
            query = query.filter(Permission.action == action)
        if resource_type:
            query = query.filter(Permission.resource_type == resource_type)

        total = query.count()
        permissions = query.offset((page - 1) * limit).limit(limit).all()

        return {
            "success": True,
            "data": {
                "permissions": [
                    {
                        "id": str(perm.id),
                        "name": perm.name,
                        "display_name": perm.display_name,
                        "description": perm.description,
                        "scope": perm.scope,
                        "action": perm.action,
                        "resource_type": perm.resource_type,
                        "conditions": perm.conditions,
                        "metadata": perm.metadata,
                        "created_at": perm.created_at.isoformat()
                    }
                    for perm in permissions
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


@router.post("/permissions")
async def create_permission(
    request: PermissionRequest,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """创建权限"""
    try:
        # 检查用户是否有创建权限的权限
        permission_service = PermissionService(db)

        perm_check = await permission_service.check_permission(
            user_id=str(user.id),
            action="create",
            resource_type="permission",
            organization_id=str(organization.id)
        )

        if not perm_check["granted"]:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions to create permissions"
            )

        permission = await permission_service.create_permission(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            scope=request.scope,
            action=request.action,
            resource_type=request.resource_type,
            conditions=request.conditions,
            metadata=request.metadata
        )

        return {
            "success": True,
            "data": {
                "id": str(permission.id),
                "name": permission.name,
                "display_name": permission.display_name,
                "scope": permission.scope,
                "action": permission.action,
                "created_at": permission.created_at.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles")
async def get_roles(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    scope: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200)
):
    """获取角色列表"""
    try:
        from ..models.permissions import Role

        query = db.query(Role).filter(Role.is_active == True)

        if scope:
            query = query.filter(Role.scope == scope)

        total = query.count()
        roles = query.offset((page - 1) * limit).limit(limit).all()

        return {
            "success": True,
            "data": {
                "roles": [
                    {
                        "id": str(role.id),
                        "name": role.name,
                        "display_name": role.display_name,
                        "description": role.description,
                        "scope": role.scope,
                        "level": role.level,
                        "parent_role_id": str(role.parent_role_id) if role.parent_role_id else None,
                        "is_system_role": role.is_system_role,
                        "is_default": role.is_default,
                        "permission_count": len(role.permissions),
                        "created_at": role.created_at.isoformat()
                    }
                    for role in roles
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


@router.post("/roles")
async def create_role(
    request: RoleRequest,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """创建角色"""
    try:
        permission_service = PermissionService(db)

        # 检查权限
        perm_check = await permission_service.check_permission(
            user_id=str(user.id),
            action="create",
            resource_type="role",
            organization_id=str(organization.id)
        )

        if not perm_check["granted"]:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions to create roles"
            )

        role = await permission_service.create_role(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            scope=request.scope,
            level=request.level,
            parent_role_id=request.parent_role_id,
            permission_ids=request.permission_ids,
            metadata=request.metadata
        )

        return {
            "success": True,
            "data": {
                "id": str(role.id),
                "name": role.name,
                "display_name": role.display_name,
                "scope": role.scope,
                "level": role.level,
                "created_at": role.created_at.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/roles/assign")
async def assign_role_to_user(
    request: RoleAssignmentRequest,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """为用户分配角色"""
    try:
        permission_service = PermissionService(db)

        # 检查权限
        perm_check = await permission_service.check_permission(
            user_id=str(user.id),
            action="update",
            resource_type="user_role",
            organization_id=str(organization.id)
        )

        if not perm_check["granted"]:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions to assign roles"
            )

        user_role = await permission_service.assign_role_to_user(
            user_id=request.user_id,
            role_id=request.role_id,
            organization_id=request.organization_id or str(organization.id),
            team_id=request.team_id,
            assigned_by=str(user.id),
            expires_at=request.expires_at,
            restrictions=request.restrictions
        )

        return {
            "success": True,
            "data": {
                "id": str(user_role.id),
                "user_id": user_role.user_id,
                "role_id": user_role.role_id,
                "assigned_at": user_role.assigned_at.isoformat(),
                "expires_at": user_role.expires_at.isoformat() if user_role.expires_at else None
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/permissions/grant")
async def grant_resource_permission(
    request: ResourcePermissionRequest,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """授予资源权限"""
    try:
        permission_service = PermissionService(db)

        # 检查权限
        perm_check = await permission_service.check_permission(
            user_id=str(user.id),
            action="grant",
            resource_type=request.resource_type,
            organization_id=str(organization.id)
        )

        if not perm_check["granted"]:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions to grant resource permissions"
            )

        resource_permission = await permission_service.grant_resource_permission(
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            user_id=request.user_id,
            permission_action=request.permission_action,
            granted_by=str(user.id),
            organization_id=str(organization.id),
            expires_at=request.expires_at,
            conditions=request.conditions
        )

        return {
            "success": True,
            "data": {
                "id": str(resource_permission.id),
                "resource_type": resource_permission.resource_type,
                "resource_id": resource_permission.resource_id,
                "user_id": resource_permission.user_id,
                "permission_action": resource_permission.permission_action,
                "granted_at": resource_permission.granted_at.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check")
async def check_permission(
    request: PermissionCheckRequest,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """检查权限"""
    try:
        permission_service = PermissionService(db)

        result = await permission_service.check_permission(
            user_id=request.user_id,
            action=request.action,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            organization_id=request.organization_id or str(organization.id),
            context=request.context
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    include_inherited: bool = Query(True)
):
    """获取用户权限列表"""
    try:
        permission_service = PermissionService(db)

        permissions = permission_service.get_user_permissions(
            user_id=user_id,
            organization_id=str(organization.id),
            include_inherited=include_inherited
        )

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "permissions": permissions,
                "total_count": len(permissions)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles/{role_id}/users")
async def get_role_users(
    role_id: str,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    active_only: bool = Query(True)
):
    """获取角色用户列表"""
    try:
        permission_service = PermissionService(db)

        users = permission_service.get_role_users(
            role_id=role_id,
            organization_id=str(organization.id),
            active_only=active_only
        )

        return {
            "success": True,
            "data": {
                "role_id": role_id,
                "users": users,
                "total_count": len(users)
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/permissions/{permission_id}")
async def revoke_permission(
    permission_id: str,
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """撤销权限"""
    try:
        permission_service = PermissionService(db)

        # 检查权限
        perm_check = await permission_service.check_permission(
            user_id=str(user.id),
            action="delete",
            resource_type="permission",
            organization_id=str(organization.id)
        )

        if not perm_check["granted"]:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions to revoke permissions"
            )

        success = await permission_service.revoke_permission(
            permission_id=permission_id,
            revoked_by=str(user.id)
        )

        if success:
            return {"success": True, "message": "Permission revoked successfully"}
        else:
            raise HTTPException(status_code=404, detail="Permission not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/roles/{role_id}/users/{user_id}")
async def remove_user_role(
    role_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """移除用户角色"""
    try:
        permission_service = PermissionService(db)

        # 检查权限
        perm_check = await permission_service.check_permission(
            user_id=str(current_user.id),
            action="delete",
            resource_type="user_role",
            organization_id=str(organization.id)
        )

        if not perm_check["granted"]:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions to remove user roles"
            )

        success = await permission_service.remove_user_role(
            user_id=user_id,
            role_id=role_id,
            organization_id=str(organization.id)
        )

        if success:
            return {"success": True, "message": "User role removed successfully"}
        else:
            raise HTTPException(status_code=404, detail="User role assignment not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/permissions")
async def get_system_permissions():
    """获取系统预定义权限列表"""
    return {
        "success": True,
        "data": {
            "permissions": [
                {"name": perm, "display_name": perm.replace(".", " ").title()}
                for perm in SystemPermissions.__dict__.values()
                if not perm.startswith("_")
            ]
        }
    }


@router.get("/system/roles")
async def get_system_roles():
    """获取系统预定义角色列表"""
    return {
        "success": True,
        "data": {
            "roles": [
                {"name": role, "display_name": role.replace("_", " ").title()}
                for role in SystemRoles.__dict__.values()
                if not role.startswith("_")
            ]
        }
    }


@router.get("/access-logs")
async def get_access_logs(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    permission_result: Optional[str] = Query(None)
):
    """获取访问日志"""
    try:
        from ..models.permissions import AccessLog

        query = db.query(AccessLog).filter(
            AccessLog.organization_id == str(organization.id)
        )

        if user_id:
            query = query.filter(AccessLog.user_id == user_id)
        if resource_type:
            query = query.filter(AccessLog.resource_type == resource_type)
        if action:
            query = query.filter(AccessLog.action == action)
        if permission_result:
            query = query.filter(AccessLog.permission_result == permission_result)

        total = query.count()
        logs = query.order_by(desc(AccessLog.created_at)).offset((page - 1) * limit).limit(limit).all()

        return {
            "success": True,
            "data": {
                "logs": [
                    {
                        "id": str(log.id),
                        "user_id": log.user_id,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "action": log.action,
                        "permission_result": log.permission_result,
                        "permission_source": log.permission_source,
                        "ip_address": log.ip_address,
                        "request_path": log.request_path,
                        "request_method": log.request_method,
                        "created_at": log.created_at.isoformat()
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
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))