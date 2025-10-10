"""
Organizations API - Multi-tenant Organization Management
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationWithStats
)
from backend.models.member import OrganizationRole
from backend.services.organization_service import OrganizationService
from backend.schemas.auth import get_current_user  # Assuming auth exists

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


def get_organization_service(db: Session = Depends(get_db)) -> OrganizationService:
    """Dependency to get organization service instance"""
    return OrganizationService(db)


# Simple auth bypass for development - replace with proper auth in production
async def get_current_user_simple() -> str:
    """Temporary simple auth - return a test user ID"""
    # In real implementation, this would extract user from JWT token
    return "550e8400-e29b-41d4-a716-446655440000"  # Test user ID


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    organization_data: OrganizationCreate,
    org_service: OrganizationService = Depends(get_organization_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Create a new organization

    The user will automatically become the owner of the created organization.
    """
    try:
        return await org_service.create_organization(organization_data, current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create organization"
        )


@router.get("/", response_model=List[OrganizationResponse])
async def get_user_organizations(
    limit: int = Query(default=50, le=100, description="Maximum number of organizations to return"),
    offset: int = Query(default=0, ge=0, description="Number of organizations to skip"),
    org_service: OrganizationService = Depends(get_organization_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Get all organizations where the current user is a member

    Returns organizations ordered by creation date (newest first).
    """
    try:
        organizations = await org_service.get_user_organizations(current_user_id)

        # Apply pagination
        return organizations[offset:offset + limit]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting user organizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organizations"
        )


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: str,
    org_service: OrganizationService = Depends(get_organization_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Get organization details by ID

    User must be a member of the organization to access it.
    """
    try:
        return await org_service.get_organization_by_id(organization_id, current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization"
        )


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: str,
    organization_data: OrganizationUpdate,
    org_service: OrganizationService = Depends(get_organization_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Update organization details

    Requires admin or owner role in the organization.
    """
    try:
        return await org_service.update_organization(
            organization_id, organization_data, current_user_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update organization"
        )


@router.delete("/{organization_id}")
async def delete_organization(
    organization_id: str,
    org_service: OrganizationService = Depends(get_organization_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Delete an organization (soft delete)

    Requires owner role. This operation cannot be undone.
    """
    try:
        success = await org_service.delete_organization(organization_id, current_user_id)
        if success:
            return {"message": "Organization deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete organization"
        )


@router.post("/{organization_id}/invite", response_model=Dict[str, Any])
async def invite_member(
    organization_id: str,
    invitation_data: Dict[str, Any],
    org_service: OrganizationService = Depends(get_organization_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Invite a user to join the organization

    Requires admin or owner role.

    Request body should contain:
    - email: Email address of the user to invite
    - role: Role to assign (owner, admin, member, viewer)
    """
    try:
        email = invitation_data.get("email")
        role_str = invitation_data.get("role", "member")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )

        # Validate role
        try:
            role = OrganizationRole(role_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {[r.value for r in OrganizationRole]}"
            )

        return await org_service.invite_member(
            organization_id, email, role, current_user_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error inviting member to organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invite member"
        )


@router.get("/{organization_id}/members", response_model=List[Dict[str, Any]])
async def get_organization_members(
    organization_id: str,
    org_service: OrganizationService = Depends(get_organization_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Get all members of the organization

    User must be a member of the organization to view members.
    """
    try:
        return await org_service.get_organization_members(organization_id, current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting organization members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization members"
        )


@router.delete("/{organization_id}/members/{member_user_id}")
async def remove_member(
    organization_id: str,
    member_user_id: str,
    org_service: OrganizationService = Depends(get_organization_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Remove a member from the organization

    Requires appropriate permissions:
    - Owners can remove any member except themselves
    - Admins can remove members and viewers
    - Users can remove themselves
    """
    try:
        success = await org_service.remove_member(
            organization_id, member_user_id, current_user_id
        )
        if success:
            return {"message": "Member removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error removing member from organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member"
        )


@router.put("/{organization_id}/members/{member_user_id}/role")
async def update_member_role(
    organization_id: str,
    member_user_id: str,
    role_data: Dict[str, str],
    org_service: OrganizationService = Depends(get_organization_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Update a member's role in the organization

    Only owners can change member roles.
    Owners cannot change their own role.

    Request body should contain:
    - role: New role (owner, admin, member, viewer)
    """
    try:
        role_str = role_data.get("role")

        if not role_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role is required"
            )

        # Validate role
        try:
            new_role = OrganizationRole(role_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {[r.value for r in OrganizationRole]}"
            )

        success = await org_service.update_member_role(
            organization_id, member_user_id, new_role, current_user_id
        )

        if success:
            return {"message": f"Member role updated to {new_role.value}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating member role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update member role"
        )


@router.get("/{organization_id}/stats", response_model=Dict[str, Any])
async def get_organization_stats(
    organization_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Get organization statistics

    User must be a member of the organization.
    """
    try:
        # Check if user is a member
        from sqlalchemy import select
        from backend.models.member import Member

        membership = db.execute(
            select(Member)
            .where(
                Member.user_id == current_user_id,
                Member.organization_id == organization_id
            )
        ).scalar_one_or_none()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )

        # Get basic stats
        from backend.models.team import Team
        from backend.models.usage_record import UsageRecord
        from backend.models.budget import Budget

        # Member count
        member_count = db.execute(
            select(Member).where(Member.organization_id == organization_id)
        ).scalar()

        # Team count
        team_count = db.execute(
            select(Team).where(Team.organization_id == organization_id)
        ).scalar()

        # Usage stats (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        usage_records = db.execute(
            select(UsageRecord)
            .where(
                UsageRecord.organization_id == organization_id,
                UsageRecord.timestamp >= thirty_days_ago
            )
        ).scalars().all()

        total_requests = len(usage_records)
        total_tokens = sum(record.total_tokens for record in usage_records)
        total_cost = sum(record.estimated_cost for record in usage_records)

        # Budget info
        budget = db.execute(
            select(Budget).where(Budget.organization_id == organization_id)
        ).scalar_one_or_none()

        budget_info = {}
        if budget:
            budget_info = {
                "monthly_limit": float(budget.monthly_limit),
                "current_spend": float(budget.current_spend),
                "remaining_budget": float(budget.monthly_limit - budget.current_spend),
                "usage_percentage": round(float(budget.current_spend) / float(budget.monthly_limit) * 100, 1) if budget.monthly_limit > 0 else 0,
                "currency": budget.currency
            }

        return {
            "organization_id": organization_id,
            "member_count": member_count,
            "team_count": team_count,
            "usage_stats": {
                "total_requests_30d": total_requests,
                "total_tokens_30d": total_tokens,
                "total_cost_30d": float(total_cost),
                "period_days": 30
            },
            "budget": budget_info,
            "user_role": membership.role
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting organization stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization statistics"
        )