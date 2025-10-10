"""
Permissions System - Multi-tenant Role-Based Access Control
"""

import logging
from typing import Dict, List, Set, Optional, Callable, Any
from functools import wraps
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.models.member import OrganizationRole
from backend.models.user import User
from backend.models.organization import Organization
from backend.models.team import Team
from backend.core.database import get_db

logger = logging.getLogger(__name__)


# Organization permission definitions
ORGANIZATION_PERMISSIONS = {
    OrganizationRole.OWNER: [
        "organizations:delete",
        "organizations:edit",
        "organizations:view",
        "members:invite", "members:remove", "members:edit", "members:view",
        "teams:create", "teams:edit", "teams:delete", "teams:view",
        "budgets:edit", "budgets:view",
        "api_keys:create", "api_keys:delete", "api_keys:edit", "api_keys:view",
        "billing:view", "billing:edit"
    ],
    OrganizationRole.ADMIN: [
        "organizations:edit",
        "organizations:view",
        "members:invite", "members:remove", "members:edit", "members:view",
        "teams:create", "teams:edit", "teams:delete", "teams:view",
        "budgets:edit", "budgets:view",
        "api_keys:create", "api_keys:delete", "api_keys:edit", "api_keys:view",
        "billing:view"
    ],
    OrganizationRole.MEMBER: [
        "organizations:view",
        "members:view",
        "teams:view",
        "api_keys:create", "api_keys:view"
    ],
    OrganizationRole.VIEWER: [
        "organizations:view",
        "members:view",
        "teams:view"
    ]
}


# Default permission sets for each role
DEFAULT_PERMISSIONS = {
    OrganizationRole.OWNER: {
        "organizations": ["delete", "edit", "view"],
        "members": ["invite", "remove", "edit", "view"],
        "teams": ["create", "edit", "delete", "view"],
        "budgets": ["edit", "view"],
        "api_keys": ["create", "delete", "edit", "view"],
        "billing": ["view", "edit"]
    },
    OrganizationRole.ADMIN: {
        "organizations": ["edit", "view"],
        "members": ["invite", "remove", "edit", "view"],
        "teams": ["create", "edit", "delete", "view"],
        "budgets": ["edit", "view"],
        "api_keys": ["create", "delete", "edit", "view"],
        "billing": ["view"]
    },
    OrganizationRole.MEMBER: {
        "organizations": ["view"],
        "members": ["view"],
        "teams": ["view"],
        "api_keys": ["create", "view"]
    },
    OrganizationRole.VIEWER: {
        "organizations": ["view"],
        "members": ["view"],
        "teams": ["view"]
    }
}


class PermissionChecker:
    """Permission checking utility class"""

    def __init__(self, db: Session):
        self.db = db
        self._permission_cache: Dict[str, Set[str]] = {}

    def has_permission(
        self,
        user_id: str,
        organization_id: str,
        required_permission: str,
        team_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has a specific permission

        Args:
            user_id: User ID
            organization_id: Organization ID
            required_permission: Permission to check (e.g., "organizations:edit")
            team_id: Optional team ID for team-specific permissions

        Returns:
            True if user has permission, False otherwise
        """
        try:
            # Get user's role in the organization
            user_role = self._get_user_role(user_id, organization_id)
            if not user_role:
                return False

            # Get permissions for this role
            permissions = ORGANIZATION_PERMISSIONS.get(user_role, [])

            # Check for exact permission match
            if required_permission in permissions:
                return True

            # Check for wildcard permissions
            resource, action = required_permission.split(":", 1)
            wildcard_permission = f"{resource}:*"
            if wildcard_permission in permissions:
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            return False

    def has_any_permission(
        self,
        user_id: str,
        organization_id: str,
        required_permissions: List[str],
        team_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has any of the required permissions

        Args:
            user_id: User ID
            organization_id: Organization ID
            required_permissions: List of permissions to check
            team_id: Optional team ID

        Returns:
            True if user has any of the permissions
        """
        return any(
            self.has_permission(user_id, organization_id, perm, team_id)
            for perm in required_permissions
        )

    def has_all_permissions(
        self,
        user_id: str,
        organization_id: str,
        required_permissions: List[str],
        team_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has all of the required permissions

        Args:
            user_id: User ID
            organization_id: Organization ID
            required_permissions: List of permissions to check
            team_id: Optional team ID

        Returns:
            True if user has all permissions
        """
        return all(
            self.has_permission(user_id, organization_id, perm, team_id)
            for perm in required_permissions
        )

    def get_user_permissions(
        self,
        user_id: str,
        organization_id: str
    ) -> Set[str]:
        """
        Get all permissions for a user in an organization

        Args:
            user_id: User ID
            organization_id: Organization ID

        Returns:
            Set of permissions
        """
        try:
            user_role = self._get_user_role(user_id, organization_id)
            if not user_role:
                return set()

            # Get base permissions for role
            permissions = set(ORGANIZATION_PERMISSIONS.get(user_role, []))

            # Get custom permissions from member record
            member = self.db.execute(
                select(backend.models.member.Member)
                .where(
                    backend.models.member.Member.user_id == user_id,
                    backend.models.member.Member.organization_id == organization_id
                )
            ).scalar_one_or_none()

            if member and member.permissions:
                # Add custom permissions
                custom_perms = set()
                if isinstance(member.permissions, dict):
                    for resource, actions in member.permissions.items():
                        if isinstance(actions, list):
                            for action in actions:
                                custom_perms.add(f"{resource}:{action}")
                        elif actions is True:
                            custom_perms.add(f"{resource}:*")
                permissions.update(custom_perms)

            return permissions

        except Exception as e:
            logger.error(f"Error getting user permissions: {e}")
            return set()

    def _get_user_role(
        self,
        user_id: str,
        organization_id: str
    ) -> Optional[OrganizationRole]:
        """
        Get user's role in an organization

        Args:
            user_id: User ID
            organization_id: Organization ID

        Returns:
            User's role or None if not a member
        """
        try:
            member = self.db.execute(
                select(backend.models.member.Member)
                .where(
                    backend.models.member.Member.user_id == user_id,
                    backend.models.member.Member.organization_id == organization_id
                )
            ).scalar_one_or_none()

            if member:
                return OrganizationRole(member.role)

            return None

        except Exception as e:
            logger.error(f"Error getting user role: {e}")
            return None


# Decorators for permission checking
def require_permission(permission: str):
    """
    Decorator to require a specific permission

    Args:
        permission: Required permission (e.g., "organizations:edit")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from function arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            # Try to get from kwargs
            if not request:
                request = kwargs.get('request')

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )

            # Get user and organization info from request state
            user_id = getattr(request.state, 'user_id', None)
            organization_id = getattr(request.state, 'organization_id', None)

            if not user_id or not organization_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Check permission
            db = next(get_db())
            checker = PermissionChecker(db)

            if not checker.has_permission(user_id, organization_id, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {permission}"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_role(role: OrganizationRole):
    """
    Decorator to require a specific role

    Args:
        role: Required role
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from function arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            # Try to get from kwargs
            if not request:
                request = kwargs.get('request')

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )

            # Get user and organization info from request state
            user_id = getattr(request.state, 'user_id', None)
            organization_id = getattr(request.state, 'organization_id', None)

            if not user_id or not organization_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Check role
            db = next(get_db())
            checker = PermissionChecker(db)

            user_role = checker._get_user_role(user_id, organization_id)
            if not user_role:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found in organization"
                )

            # Check if user has required role or higher
            role_hierarchy = {
                OrganizationRole.VIEWER: 0,
                OrganizationRole.MEMBER: 1,
                OrganizationRole.ADMIN: 2,
                OrganizationRole.OWNER: 3
            }

            if role_hierarchy.get(user_role, 0) < role_hierarchy.get(role, 0):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient role. Required: {role.value}"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_any_permission(permissions: List[str]):
    """
    Decorator to require any of the specified permissions

    Args:
        permissions: List of required permissions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from function arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            # Try to get from kwargs
            if not request:
                request = kwargs.get('request')

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )

            # Get user and organization info from request state
            user_id = getattr(request.state, 'user_id', None)
            organization_id = getattr(request.state, 'organization_id', None)

            if not user_id or not organization_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Check permissions
            db = next(get_db())
            checker = PermissionChecker(db)

            if not checker.has_any_permission(user_id, organization_id, permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required any of: {', '.join(permissions)}"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


# Permission checking functions for direct use
def has_permission(db: Session, user_id: str, organization_id: str, permission: str) -> bool:
    """
    Check if user has a specific permission

    Args:
        db: Database session
        user_id: User ID
        organization_id: Organization ID
        permission: Permission to check

    Returns:
        True if user has permission
    """
    checker = PermissionChecker(db)
    return checker.has_permission(user_id, organization_id, permission)


def get_user_permissions(db: Session, user_id: str, organization_id: str) -> Set[str]:
    """
    Get all permissions for a user in an organization

    Args:
        db: Database session
        user_id: User ID
        organization_id: Organization ID

    Returns:
        Set of permissions
    """
    checker = PermissionChecker(db)
    return checker.get_user_permissions(user_id, organization_id)


# Resource-specific permission checkers
class OrganizationPermissions:
    """Organization-specific permission checks"""

    @staticmethod
    def can_view(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "organizations:view")

    @staticmethod
    def can_edit(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "organizations:edit")

    @staticmethod
    def can_delete(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "organizations:delete")


class TeamPermissions:
    """Team-specific permission checks"""

    @staticmethod
    def can_view(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "teams:view")

    @staticmethod
    def can_create(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "teams:create")

    @staticmethod
    def can_edit(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "teams:edit")

    @staticmethod
    def can_delete(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "teams:delete")


class MemberPermissions:
    """Member-specific permission checks"""

    @staticmethod
    def can_view(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "members:view")

    @staticmethod
    def can_invite(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "members:invite")

    @staticmethod
    def can_remove(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "members:remove")

    @staticmethod
    def can_edit(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "members:edit")


class BudgetPermissions:
    """Budget-specific permission checks"""

    @staticmethod
    def can_view(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "budgets:view")

    @staticmethod
    def can_edit(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "budgets:edit")


class ApiKeyPermissions:
    """API Key-specific permission checks"""

    @staticmethod
    def can_view(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "api_keys:view")

    @staticmethod
    def can_create(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "api_keys:create")

    @staticmethod
    def can_delete(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "api_keys:delete")

    @staticmethod
    def can_edit(db: Session, user_id: str, organization_id: str) -> bool:
        return has_permission(db, user_id, organization_id, "api_keys:edit")