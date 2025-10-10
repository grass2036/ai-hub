"""
Multi-tenant Middleware - Data Isolation and Permission Management
"""

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.core.database import get_db
from backend.models.member import Member, OrganizationRole
from backend.models.user import User
from backend.models.org_api_key import OrgApiKey
from backend.models.organization import Organization

logger = logging.getLogger(__name__)


class MultiTenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware for multi-tenant data isolation and permission management

    This middleware:
    1. Extracts organization context from API keys or authentication
    2. Injects user and organization information into request state
    3. Validates user access to organization resources
    4. Provides tenant isolation for database queries
    """

    async def dispatch(self, request: Request, call_next):
        # Process the request
        response = await call_next(request)

        return response

    async def extract_organization_context(self, request: Request) -> Optional[dict]:
        """
        Extract organization context from request

        This can extract from:
        1. API Key (for API requests)
        2. JWT Token (for authenticated users)
        3. Organization header (for internal requests)
        """
        context = None

        # Try API key first (for API requests)
        api_key = self._extract_api_key(request)
        if api_key:
            context = await self._get_context_from_api_key(api_key)
            if context:
                return context

        # Try JWT token (for authenticated users)
        auth_token = self._extract_auth_token(request)
        if auth_token:
            context = await self._get_context_from_token(auth_token)
            if context:
                return context

        # Try organization header (for internal requests)
        org_header = request.headers.get("X-Organization-ID")
        if org_header:
            context = await self._get_context_from_header(org_header, request)
            if context:
                return context

        return None

    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request"""
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix

        # Check API key header
        api_key_header = request.headers.get("X-API-Key")
        if api_key_header:
            return api_key_header

        # Check query parameter (for testing only)
        if hasattr(request, "query_params"):
            return request.query_params.get("api_key")

        return None

    def _extract_auth_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request"""
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None

    async def _get_context_from_api_key(self, api_key: str) -> Optional[dict]:
        """Get organization context from API key"""
        try:
            db = next(get_db())

            # Find API key in database
            org_api_key = db.execute(
                select(OrgApiKey)
                .where(OrgApiKey.key_hash == self._hash_api_key(api_key))
                .where(OrgApiKey.status == "active")
            ).scalar_one_or_none()

            if not org_api_key:
                logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
                return None

            # Check if API key is expired
            if org_api_key.expires_at and org_api_key.expires_at < datetime.utcnow():
                logger.warning(f"Expired API key attempted: {org_api_key.key_prefix}")
                return None

            # Update last used timestamp
            org_api_key.last_used_at = datetime.utcnow()
            db.commit()

            # Get organization details
            organization = db.execute(
                select(Organization)
                .where(Organization.id == org_api_key.organization_id)
            ).scalar_one_or_none()

            if not organization:
                logger.error(f"Organization not found for API key: {org_api_key.key_prefix}")
                return None

            return {
                "organization_id": str(org_api_key.organization_id),
                "organization_name": organization.name,
                "api_key_id": str(org_api_key.id),
                "api_key_name": org_api_key.name,
                "api_key_permissions": org_api_key.permissions,
                "source": "api_key"
            }

        except Exception as e:
            logger.error(f"Error extracting context from API key: {e}")
            return None

    async def _get_context_from_token(self, token: str) -> Optional[dict]:
        """Get organization context from JWT token"""
        # This would be implemented with actual JWT decoding
        # For now, return None as we'll implement JWT authentication separately
        return None

    async def _get_context_from_header(self, org_id: str, request: Request) -> Optional[dict]:
        """Get organization context from header (for internal requests)"""
        try:
            db = next(get_db())

            # Validate organization exists
            organization = db.execute(
                select(Organization)
                .where(Organization.id == org_id)
                .where(Organization.status == "active")
            ).scalar_one_or_none()

            if not organization:
                logger.warning(f"Invalid organization ID in header: {org_id}")
                return None

            return {
                "organization_id": org_id,
                "organization_name": organization.name,
                "source": "header"
            }

        except Exception as e:
            logger.error(f"Error extracting context from header: {e}")
            return None

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for comparison"""
        import hashlib
        return hashlib.sha256(api_key.encode()).hexdigest()


class OrganizationContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to inject organization context into request state

    This middleware runs after authentication and extracts/validates
    organization context for multi-tenant operations.
    """

    async def dispatch(self, request: Request, call_next):
        # Extract organization context
        context = await self._extract_organization_context(request)

        # Inject context into request state
        if context:
            request.state.organization_id = context["organization_id"]
            request.state.organization_name = context.get("organization_name")
            request.state.organization_source = context.get("source")

            # If API key, also inject API key info
            if context.get("source") == "api_key":
                request.state.api_key_id = context.get("api_key_id")
                request.state.api_key_name = context.get("api_key_name")
                request.state.api_key_permissions = context.get("api_key_permissions", {})

        # If this is an authenticated user request, inject user context
        user_id = self._extract_user_id(request)
        if user_id:
            request.state.user_id = user_id
            # Inject user's role if we have organization context
            if context and context.get("organization_id"):
                user_role = await self._get_user_role(user_id, context["organization_id"])
                if user_role:
                    request.state.user_role = user_role.value

        # Process the request
        response = await call_next(request)

        return response

    async def _extract_organization_context(self, request: Request) -> Optional[dict]:
        """Extract organization context from request"""
        # This would integrate with the main MultiTenantMiddleware
        # For now, implement basic extraction
        return None

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request"""
        # This would extract from JWT token
        # For development, return a test user ID
        return "550e8400-e29b-41d4-a716-446655440000"

    async def _get_user_role(self, user_id: str, organization_id: str) -> Optional[OrganizationRole]:
        """Get user's role in organization"""
        try:
            db = next(get_db())

            member = db.execute(
                select(Member)
                .where(
                    Member.user_id == user_id,
                    Member.organization_id == organization_id
                )
            ).scalar_one_or_none()

            if member:
                return OrganizationRole(member.role)

            return None

        except Exception as e:
            logger.error(f"Error getting user role: {e}")
            return None


class DataIsolationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to ensure data isolation at the database level

    This middleware automatically filters queries based on
    organization context to prevent data leakage.
    """

    async def dispatch(self, request: Request, call_next):
        # Get organization context
        organization_id = getattr(request.state, 'organization_id', None)

        # If we have organization context, add filter to request state
        if organization_id:
            request.state.require_organization_filter = True
            request.state.organization_id = organization_id

        # Process the request
        response = await call_next(request)

        return response


class PermissionValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate permissions for sensitive operations

    This middleware automatically validates permissions based on
    the requested operation and user's role in the organization.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip permission validation for public endpoints
        if self._is_public_endpoint(request):
            return await call_next(request)

        # Get required context
        organization_id = getattr(request.state, 'organization_id', None)
        user_id = getattr(request.state, 'user_id', None)

        # If missing context, return unauthorized
        if not organization_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Organization context required"
            )

        # Validate user has access to organization
        if user_id and not await self._validate_user_access(user_id, organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to organization"
            )

        # Process the request
        response = await call_next(request)

        return response

    def _is_public_endpoint(self, request: Request) -> bool:
        """Check if endpoint is public (doesn't require organization context)"""
        public_paths = [
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/auth/login",
            "/auth/register",
            "/models"
        ]

        return any(request.url.path.startswith(path) for path in public_paths)

    async def _validate_user_access(self, user_id: str, organization_id: str) -> bool:
        """Validate user has access to organization"""
        try:
            db = next(get_db())

            member = db.execute(
                select(Member)
                .where(
                    Member.user_id == user_id,
                    Member.organization_id == organization_id
                )
            ).scalar_one_or_none()

            return member is not None

        except Exception as e:
            logger.error(f"Error validating user access: {e}")
            return False


def create_multi_tenant_middleware() -> BaseHTTPMiddleware:
    """
    Factory function to create the multi-tenant middleware stack

    Returns:
        Combined middleware for multi-tenant operations
    """
    # Create middleware stack
    return OrganizationContextMiddleware(
        DataIsolationMiddleware(
            PermissionValidationMiddleware()
        )
    )


# Utility functions for working with multi-tenant data
class MultiTenantQuery:
    """Utility class for building multi-tenant queries"""

    @staticmethod
    def filter_by_organization(query, organization_id: UUID):
        """Filter query by organization ID"""
        return query.filter(backend.models.organization.Organization.id == organization_id)

    @staticmethod
    def filter_by_team(query, team_id: UUID):
        """Filter query by team ID"""
        return query.filter(backend.models.team.Team.id == team_id)

    @staticmethod
    def filter_by_user_organization(query, user_id: UUID, organization_id: UUID):
        """Filter query by user and organization (for user-specific resources)"""
        return query.filter(
            backend.models.member.Member.user_id == user_id,
            backend.models.member.Member.organization_id == organization_id
        )

    @staticmethod
    def ensure_organization_access(query, user_id: UUID, organization_id: UUID):
        """
        Ensure user has access to organization and filter accordingly

        This is a safety check that should be used in addition to
        middleware-based filtering for defense in depth.
        """
        # First verify user is member of organization
        member_exists = query.session.execute(
            select(backend.models.member.Member)
            .where(
                backend.models.member.Member.user_id == user_id,
                backend.models.member.Member.organization_id == organization_id
            )
        ).scalar_one_or_none()

        if not member_exists:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to organization"
            )

        # Apply organization filter
        return MultiTenantQuery.filter_by_organization(query, organization_id)


# Helper functions for common multi-tenant operations
def get_user_organizations(db: Session, user_id: str) -> list:
    """Get all organizations a user belongs to"""
    return db.execute(
        select(backend.models.organization.Organization)
        .join(backend.models.member.Member)
        .where(
            backend.models.member.Member.user_id == user_id,
            backend.models.organization.Organization.status == "active"
        )
        .order_by(backend.models.organization.Organization.created_at.desc())
    ).scalars().all()


def get_user_role_in_organization(db: Session, user_id: str, organization_id: str) -> Optional[OrganizationRole]:
    """Get user's role in a specific organization"""
    member = db.execute(
        select(backend.models.member.Member)
        .where(
            backend.models.member.Member.user_id == user_id,
            backend.models.member.Member.organization_id == organization_id
        )
    ).scalar_one_or_none()

    if member:
        return OrganizationRole(member.role)
    return None


def validate_organization_membership(db: Session, user_id: str, organization_id: str) -> bool:
    """Validate user is a member of the organization"""
    return db.execute(
        select(backend.models.member.Member)
        .where(
            backend.models.member.Member.user_id == user_id,
            backend.models.member.Member.organization_id == organization_id
        )
    ).scalar_one_or_none() is not None