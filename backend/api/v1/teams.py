"""
Teams API - Multi-tenant Team Management
"""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.team import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamWithStats
)
from backend.models.member import OrganizationRole
from backend.services.team_service import TeamService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


def get_team_service(db: Session = Depends(get_db)) -> TeamService:
    """Dependency to get team service instance"""
    return TeamService(db)


# Simple auth bypass for development - replace with proper auth in production
async def get_current_user_simple() -> str:
    """Temporary simple auth - return a test user ID"""
    # In real implementation, this would extract user from JWT token
    return "550e8400-e29b-41d4-a716-446655440000"  # Test user ID


@router.post("/organizations/{organization_id}/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    organization_id: str,
    team_data: TeamCreate,
    team_service: TeamService = Depends(get_team_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Create a new team within an organization

    Requires admin or owner role in the organization.
    Supports hierarchical team structure.
    """
    try:
        return await team_service.create_team(team_data, organization_id, current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating team: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create team"
        )


@router.get("/organizations/{organization_id}/teams", response_model=List[TeamResponse])
async def get_organization_teams(
    organization_id: str,
    include_stats: bool = Query(default=False, description="Include team statistics"),
    limit: int = Query(default=50, le=100, description="Maximum number of teams to return"),
    offset: int = Query(default=0, ge=0, description="Number of teams to skip"),
    team_service: TeamService = Depends(get_team_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Get all teams within an organization

    User must be a member of the organization to access teams.
    Returns teams ordered by name.
    """
    try:
        teams = await team_service.get_organization_teams(
            organization_id, current_user_id, include_stats
        )

        # Apply pagination
        return teams[offset:offset + limit]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting organization teams: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve teams"
        )


@router.get("/organizations/{organization_id}/teams/hierarchy", response_model=List[Dict[str, Any]])
async def get_organization_teams_hierarchy(
    organization_id: str,
    team_service: TeamService = Depends(get_team_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Get team hierarchy for an organization

    Returns a tree structure showing team relationships.
    """
    try:
        return await team_service.get_team_hierarchy(organization_id, current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting team hierarchy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team hierarchy"
        )


@router.get("/teams/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: str,
    team_service: TeamService = Depends(get_team_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Get team details by ID

    User must be a member of the team's organization to access it.
    """
    try:
        return await team_service.get_team_by_id(team_id, current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting team {team_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team"
        )


@router.put("/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    team_data: TeamUpdate,
    team_service: TeamService = Depends(get_team_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Update team details

    Requires admin or owner role in the organization.
    """
    try:
        return await team_service.update_team(team_id, team_data, current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating team {team_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update team"
        )


@router.delete("/teams/{team_id}")
async def delete_team(
    team_id: str,
    team_service: TeamService = Depends(get_team_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Delete a team

    Requires admin or owner role in the organization.
    Cannot delete teams that have sub-teams.
    """
    try:
        success = await team_service.delete_team(team_id, current_user_id)
        if success:
            return {"message": "Team deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting team {team_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete team"
        )


@router.post("/teams/{team_id}/members")
async def add_team_member(
    team_id: str,
    member_data: Dict[str, str],
    team_service: TeamService = Depends(get_team_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Add a user to a team

    Requires admin or owner role in the organization.

    Request body should contain:
    - user_id: User ID to add to the team
    """
    try:
        user_id = member_data.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID is required"
            )

        success = await team_service.add_team_member(team_id, user_id, current_user_id)
        if success:
            return {"message": "User added to team successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error adding team member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add team member"
        )


@router.delete("/teams/{team_id}/members/{user_id}")
async def remove_team_member(
    team_id: str,
    user_id: str,
    team_service: TeamService = Depends(get_team_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Remove a user from a team

    Requires admin or owner role in the organization.
    Users can also remove themselves from teams.
    """
    try:
        success = await team_service.remove_team_member(team_id, user_id, current_user_id)
        if success:
            return {"message": "User removed from team successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error removing team member: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove team member"
        )


@router.get("/teams/{team_id}/members", response_model=List[Dict[str, Any]])
async def get_team_members(
    team_id: str,
    team_service: TeamService = Depends(get_team_service),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Get all members of a team

    User must be a member of the team's organization to view members.
    """
    try:
        return await team_service.get_team_members(team_id, current_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting team members: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team members"
        )


@router.get("/teams/{team_id}/stats", response_model=Dict[str, Any])
async def get_team_stats(
    team_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_simple)
):
    """
    Get team statistics

    User must be a member of the team's organization.
    """
    try:
        # Get team details to verify access
        from sqlalchemy import select
        from backend.models.team import Team
        from backend.models.member import Member

        team = db.execute(
            select(Team)
            .where(Team.id == team_id)
        ).scalar_one_or_none()

        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )

        # Verify user is a member of the organization
        membership = db.execute(
            select(Member)
            .where(
                Member.user_id == current_user_id,
                Member.organization_id == team.organization_id
            )
        ).scalar_one_or_none()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Access denied"
            )

        # Get basic stats
        from backend.models.usage_record import UsageRecord
        from datetime import datetime, timedelta

        # Member count
        member_count = db.execute(
            select(Member).where(Member.team_id == team_id)
        ).scalar()

        # Sub-team count
        sub_team_count = db.execute(
            select(Team).where(Team.parent_team_id == team_id)
        ).scalar()

        # Usage stats (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        usage_records = db.execute(
            select(UsageRecord)
            .where(
                UsageRecord.team_id == team_id,
                UsageRecord.timestamp >= thirty_days_ago
            )
        ).scalars().all()

        total_requests = len(usage_records)
        total_tokens = sum(record.total_tokens for record in usage_records)
        total_cost = sum(record.estimated_cost for record in usage_records)

        # Team hierarchy info
        parent_team_name = None
        if team.parent_team_id:
            parent_team = db.execute(
                select(Team).where(Team.id == team.parent_team_id)
            ).scalar_one_or_none()
            if parent_team:
                parent_team_name = parent_team.name

        return {
            "team_id": team_id,
            "team_name": team.name,
            "organization_id": team.organization_id,
            "member_count": member_count,
            "sub_team_count": sub_team_count,
            "usage_stats": {
                "total_requests_30d": total_requests,
                "total_tokens_30d": total_tokens,
                "total_cost_30d": float(total_cost),
                "period_days": 30
            },
            "parent_team_name": parent_team_name,
            "description": team.description,
            "settings": team.settings,
            "created_at": team.created_at.isoformat(),
            "updated_at": team.updated_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting team stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve team statistics"
        )