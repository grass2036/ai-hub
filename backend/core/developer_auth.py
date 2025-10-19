"""
Developer Authentication Core
Week 4 Day 22: Developer Portal and Authentication System
"""

from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.developer_service import DeveloperService
from backend.models.developer import Developer

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)


async def get_developer_service(db: Session = Depends(get_db)) -> DeveloperService:
    """获取开发者服务实例"""
    return DeveloperService(db)


async def get_current_developer_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    developer_service: DeveloperService = Depends(get_developer_service)
) -> Optional[Developer]:
    """获取当前开发���（可选，不抛出异常）"""

    if not credentials:
        return None

    try:
        return await developer_service.get_current_developer(credentials.credentials)
    except Exception:
        return None


async def get_current_developer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    developer_service: DeveloperService = Depends(get_developer_service)
) -> Developer:
    """获取当前开发者（必需，会抛出异常）"""

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    developer = await developer_service.get_current_developer(credentials.credentials)

    if not developer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return developer


async def get_current_verified_developer(
    developer: Developer = Depends(get_current_developer)
) -> Developer:
    """获取当前已验证邮箱的开发者"""

    if not developer.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请先验证邮箱地址"
        )

    return developer


async def get_current_active_developer(
    developer: Developer = Depends(get_current_developer)
) -> Developer:
    """获取当前活跃开发者"""

    if not developer.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )

    return developer


def get_client_info(request: Request) -> dict:
    """获取客户端信息"""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "origin": request.headers.get("origin"),
        "referer": request.headers.get("referer")
    }


class DeveloperPermissions:
    """开发者权限检查"""

    # 基础权限
    READ_PROFILE = "read_profile"
    UPDATE_PROFILE = "update_profile"
    MANAGE_API_KEYS = "manage_api_keys"
    VIEW_USAGE = "view_usage"

    # 高级权限
    MANAGE_WEBHOOKS = "manage_webhooks"
    MANAGE_BILLING = "manage_billing"
    ACCESS_ANALYTICS = "access_analytics"
    BATCH_PROCESSING = "batch_processing"

    # 管理权限
    MANAGE_SUBSCRIPTION = "manage_subscription"
    EXPORT_DATA = "export_data"
    DELETE_ACCOUNT = "delete_account"


class DeveloperPermissionChecker:
    """开发者权限检查器"""

    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions

    def __call__(
        self,
        developer: Developer = Depends(get_current_verified_developer),
        developer_service: DeveloperService = Depends(get_developer_service)
    ) -> Developer:
        """检查开发者权限"""

        # TODO: 实现基于API密钥的权限检查
        # 目前暂时通过开发者类型和状态来判断基础权限

        # 检查邮箱验证状态
        if not developer.email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="请先验证邮箱地址"
            )

        # 检查账户状态
        if not developer.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账户已被禁用"
            )

        # TODO: 添加具体权限检查逻辑
        # 这里可以根据开发者类型、订阅等级等来检查具体权限

        return developer


def require_permissions(*permissions: str):
    """权限装饰器工厂"""
    return DeveloperPermissionChecker(list(permissions))


# 预定义的权限依赖
require_profile_read = require_permissions(DeveloperPermissions.READ_PROFILE)
require_profile_update = require_permissions(DeveloperPermissions.UPDATE_PROFILE)
require_api_keys_manage = require_permissions(DeveloperPermissions.MANAGE_API_KEYS)
require_usage_view = require_permissions(DeveloperPermissions.VIEW_USAGE)
require_webhooks_manage = require_permissions(DeveloperPermissions.MANAGE_WEBHOOKS)
require_billing_manage = require_permissions(DeveloperPermissions.MANAGE_BILLING)
require_analytics_access = require_permissions(DeveloperPermissions.ACCESS_ANALYTICS)
require_batch_processing = require_permissions(DeveloperPermissions.BATCH_PROCESSING)