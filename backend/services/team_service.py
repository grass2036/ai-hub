"""
Team Service - Multi-tenant Team Management
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, select, func
from fastapi import HTTPException, status

from backend.models.team import Team, TeamCreate, TeamUpdate, TeamResponse, TeamWithStats
from backend.models.member import Member, OrganizationRole
from backend.models.user import User
from backend.models.usage_record import UsageRecord
from backend.core.database import get_db

logger = logging.getLogger(__name__)


class TeamService:
    """Service for managing teams in multi-tenant environment"""

    def __init__(self, db: Session):
        self.db = db

    async def create_team(
        self,
        team_data: TeamCreate,
        organization_id: str,
        creator_user_id: str
    ) -> TeamResponse:
        """
        Create a new team within an organization

        Args:
            team_data: Team creation data
            organization_id: Organization ID where team will be created
            creator_user_id: User ID creating the team

        Returns:
            Created team response

        Raises:
            HTTPException: If user lacks permissions or validation fails
        """
        try:
            # Verify user has permission to create teams in the organization
            membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == creator_user_id,
                        Member.organization_id == organization_id,
                        Member.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN])
                    )
                )
            ).scalar_one_or_none()

            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to create teams"
                )

            # Validate parent team if specified
            if team_data.parent_team_id:
                parent_team = self.db.execute(
                    select(Team)
                    .where(
                        and_(
                            Team.id == team_data.parent_team_id,
                            Team.organization_id == organization_id
                        )
                    )
                ).scalar_one_or_none()

                if not parent_team:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid parent team"
                    )

                # Check for circular reference
                if await self._would_create_circular_reference(team_data.parent_team_id, organization_id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot create circular team hierarchy"
                    )

            # Create team
            team = Team(
                organization_id=organization_id,
                name=team_data.name,
                description=team_data.description,
                parent_team_id=team_data.parent_team_id,
                settings=team_data.settings
            )

            self.db.add(team)
            self.db.commit()
            self.db.refresh(team)

            logger.info(f"Created team '{team.name}' in organization {organization_id}")

            return TeamResponse.from_orm(team)

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create team: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create team"
            )

    async def get_organization_teams(
        self,
        organization_id: str,
        user_id: str,
        include_stats: bool = False
    ) -> List[TeamResponse]:
        """
        Get all teams within an organization

        Args:
            organization_id: Organization ID
            user_id: User ID requesting the teams
            include_stats: Whether to include team statistics

        Returns:
            List of teams in the organization

        Raises:
            HTTPException: If user is not a member of the organization
        """
        try:
            # Verify user is a member of the organization
            membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == user_id,
                        Member.organization_id == organization_id
                    )
                )
            ).scalar_one_or_none()

            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found or access denied"
                )

            # Get teams
            result = self.db.execute(
                select(Team)
                .where(Team.organization_id == organization_id)
                .order_by(Team.name.asc())
            ).scalars().all()

            if include_stats:
                teams_with_stats = []
                for team in result:
                    stats = await self._get_team_stats(team.id)
                    team_data = TeamWithStats.from_orm(team)
                    team_data.member_count = stats['member_count']
                    team_data.sub_team_count = stats['sub_team_count']
                    team_data.current_month_spend = stats['current_month_spend']
                    team_data.parent_team_name = stats['parent_team_name']
                    teams_with_stats.append(team_data)
                return teams_with_stats
            else:
                return [TeamResponse.from_orm(team) for team in result]

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get organization teams: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve teams"
            )

    async def get_team_by_id(
        self,
        team_id: str,
        user_id: str
    ) -> TeamResponse:
        """
        Get team details by ID

        Args:
            team_id: Team ID
            user_id: User ID requesting the team

        Returns:
            Team details

        Raises:
            HTTPException: If team not found or user not authorized
        """
        try:
            # Get team with organization info
            team = self.db.execute(
                select(Team)
                .where(Team.id == team_id)
            ).scalar_one_or_none()

            if not team:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Team not found"
                )

            # Verify user is a member of the organization
            membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == user_id,
                        Member.organization_id == team.organization_id
                    )
                )
            ).scalar_one_or_none()

            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Team not found or access denied"
                )

            return TeamResponse.from_orm(team)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get team {team_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve team"
            )

    async def update_team(
        self,
        team_id: str,
        team_data: TeamUpdate,
        user_id: str
    ) -> TeamResponse:
        """
        Update team details

        Args:
            team_id: Team ID
            team_data: Update data
            user_id: User ID making the request

        Returns:
            Updated team

        Raises:
            HTTPException: If insufficient permissions or validation fails
        """
        try:
            # Get team and verify user permissions
            team = self.db.execute(
                select(Team)
                .where(Team.id == team_id)
            ).scalar_one_or_none()

            if not team:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Team not found"
                )

            # Check user permissions (admin or owner of organization)
            membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == user_id,
                        Member.organization_id == team.organization_id,
                        Member.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN])
                    )
                )
            ).scalar_one_or_none()

            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to update team"
                )

            # Update team fields
            update_data = team_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(team, field):
                    setattr(team, field, value)

            self.db.commit()
            self.db.refresh(team)

            logger.info(f"Updated team '{team.name}' by user {user_id}")

            return TeamResponse.from_orm(team)

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update team {team_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update team"
            )

    async def delete_team(
        self,
        team_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a team

        Args:
            team_id: Team ID
            user_id: User ID making the request

        Returns:
            True if deleted successfully

        Raises:
            HTTPException: If insufficient permissions or team not found
        """
        try:
            # Get team and verify user permissions
            team = self.db.execute(
                select(Team)
                .where(Team.id == team_id)
            ).scalar_one_or_none()

            if not team:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Team not found"
                )

            # Check user permissions (admin or owner of organization)
            membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == user_id,
                        Member.organization_id == team.organization_id,
                        Member.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN])
                    )
                )
            ).scalar_one_or_none()

            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to delete team"
                )

            # Check if team has sub-teams
            sub_teams_count = self.db.execute(
                select(func.count(Team.id))
                .where(Team.parent_team_id == team_id)
            ).scalar()

            if sub_teams_count > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete team with sub-teams. Delete sub-teams first"
                )

            # Delete the team
            self.db.delete(team)
            self.db.commit()

            logger.info(f"Deleted team '{team.name}' by user {user_id}")

            return True

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete team {team_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete team"
            )

    async def add_team_member(
        self,
        team_id: str,
        user_id: str,
        requesting_user_id: str
    ) -> bool:
        """
        Add a user to a team

        Args:
            team_id: Team ID
            user_id: User ID to add to team
            requesting_user_id: User ID making the request

        Returns:
            True if added successfully

        Raises:
            HTTPException: If insufficient permissions or validation fails
        """
        try:
            # Get team and verify permissions
            team = self.db.execute(
                select(Team)
                .where(Team.id == team_id)
            ).scalar_one_or_none()

            if not team:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Team not found"
                )

            # Check requesting user permissions (admin or owner of organization)
            membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == requesting_user_id,
                        Member.organization_id == team.organization_id,
                        Member.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN])
                    )
                )
            ).scalar_one_or_none()

            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to add team members"
                )

            # Verify user to add is a member of the organization
            user_membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == user_id,
                        Member.organization_id == team.organization_id
                    )
                )
            ).scalar_one_or_none()

            if not user_membership:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is not a member of this organization"
                )

            # Check if user is already in the team
            existing_member = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == user_id,
                        Member.team_id == team_id
                    )
                )
            ).scalar_one_or_none()

            if existing_member:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User is already a member of this team"
                )

            # Update user's team assignment
            user_membership.team_id = team_id
            self.db.commit()

            logger.info(f"Added user {user_id} to team {team_id}")

            return True

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add user to team {team_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add team member"
            )

    async def remove_team_member(
        self,
        team_id: str,
        user_id: str,
        requesting_user_id: str
    ) -> bool:
        """
        Remove a user from a team

        Args:
            team_id: Team ID
            user_id: User ID to remove from team
            requesting_user_id: User ID making the request

        Returns:
            True if removed successfully

        Raises:
            HTTPException: If insufficient permissions or validation fails
        """
        try:
            # Get team and verify permissions
            team = self.db.execute(
                select(Team)
                .where(Team.id == team_id)
            ).scalar_one_or_none()

            if not team:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Team not found"
            )

            # Check requesting user permissions
            # Admin/owner can remove anyone, users can remove themselves
            membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == requesting_user_id,
                        Member.organization_id == team.organization_id
                    )
                )
            ).scalar_one_or_none()

            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Access denied"
                )

            # Permission check
            can_remove = False
            if membership.role in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
                can_remove = True
            elif user_id == requesting_user_id:
                can_remove = True

            if not can_remove:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to remove team member"
                )

            # Get member to remove
            member_to_remove = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == user_id,
                        Member.organization_id == team.organization_id,
                        Member.team_id == team_id
                    )
                )
            ).scalar_one_or_none()

            if not member_to_remove:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User is not a member of this team"
                )

            # Remove from team (set team_id to None)
            member_to_remove.team_id = None
            self.db.commit()

            logger.info(f"Removed user {user_id} from team {team_id}")

            return True

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to remove user from team {team_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove team member"
            )

    async def get_team_members(
        self,
        team_id: str,
        requesting_user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all members of a team

        Args:
            team_id: Team ID
            requesting_user_id: User ID making the request

        Returns:
            List of team members

        Raises:
            HTTPException: If insufficient permissions or team not found
        """
        try:
            # Get team and verify user permissions
            team = self.db.execute(
                select(Team)
                .where(Team.id == team_id)
            ).scalar_one_or_none()

            if not team:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Team not found"
                )

            # Verify user is a member of the organization
            membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == requesting_user_id,
                        Member.organization_id == team.organization_id
                    )
                )
            ).scalar_one_or_none()

            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Access denied"
                )

            # Get team members with user details
            result = self.db.execute(
                select(Member, User)
                .join(User)
                .where(
                    and_(
                        Member.team_id == team_id,
                        Member.organization_id == team.organization_id
                    )
                ).order_by(Member.joined_at.asc())
            ).all()

            members = []
            for member, user in result:
                members.append({
                    "id": str(member.id),
                    "user_id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "avatar_url": user.avatar_url,
                    "role": member.role,
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None
                })

            return members

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get team members: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve team members"
            )

    async def get_team_hierarchy(
        self,
        organization_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get team hierarchy for an organization

        Args:
            organization_id: Organization ID
            user_id: User ID requesting the hierarchy

        Returns:
            Team hierarchy as a list

        Raises:
            HTTPException: If user is not a member of the organization
        """
        try:
            # Verify user is a member of the organization
            membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == user_id,
                        Member.organization_id == organization_id
                    )
                )
            ).scalar_one_or_none()

            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found or access denied"
                )

            # Get all teams in the organization
            teams = self.db.execute(
                select(Team)
                .where(Team.organization_id == organization_id)
                .order_by(Team.name.asc())
            ).scalars().all()

            # Build hierarchy
            team_dict = {str(team.id): {
                "id": str(team.id),
                "name": team.name,
                "description": team.description,
                "parent_team_id": str(team.parent_team_id) if team.parent_team_id else None,
                "children": []
            } for team in teams}

            # Build tree structure
            root_teams = []
            for team_id, team_data in team_dict.items():
                if team_data["parent_team_id"]:
                    parent = team_dict.get(team_data["parent_team_id"])
                    if parent:
                        parent["children"].append(team_data)
                else:
                    root_teams.append(team_data)

            return root_teams

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get team hierarchy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve team hierarchy"
            )

    async def _would_create_circular_reference(
        self,
        parent_team_id: str,
        organization_id: str
    ) -> bool:
        """
        Check if creating a team with the given parent would create a circular reference

        Args:
            parent_team_id: Potential parent team ID
            organization_id: Organization ID

        Returns:
            True if circular reference would be created
        """
        visited = set()

        def check_circular(team_id: str) -> bool:
            if team_id in visited:
                return True

            visited.add(team_id)

            team = self.db.execute(
                select(Team)
                .where(Team.id == team_id)
            ).scalar_one_or_none()

            if team and team.parent_team_id:
                return check_circular(team.parent_team_id)

            return False

        return check_circular(parent_team_id)

    async def _get_team_stats(self, team_id: str) -> Dict[str, Any]:
        """
        Get statistics for a team

        Args:
            team_id: Team ID

        Returns:
            Team statistics
        """
        try:
            # Member count
            member_count = self.db.execute(
                select(func.count(Member.id))
                .where(Member.team_id == team_id)
            ).scalar()

            # Sub-team count
            sub_team_count = self.db.execute(
                select(func.count(Team.id))
                .where(Team.parent_team_id == team_id)
            ).scalar()

            # Current month spend
            from datetime import datetime, timedelta
            start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            usage_records = self.db.execute(
                select(func.sum(UsageRecord.estimated_cost))
                .where(
                    and_(
                        UsageRecord.team_id == team_id,
                        UsageRecord.timestamp >= start_of_month
                    )
                )
            ).scalar()

            current_month_spend = float(usage_records) if usage_records else 0.0

            # Parent team name
            team = self.db.execute(
                select(Team)
                .where(Team.id == team_id)
            ).scalar_one_or_none()

            parent_team_name = None
            if team and team.parent_team_id:
                parent_team = self.db.execute(
                    select(Team)
                    .where(Team.id == team.parent_team_id)
                ).scalar_one_or_none()
                if parent_team:
                    parent_team_name = parent_team.name

            return {
                "member_count": member_count,
                "sub_team_count": sub_team_count,
                "current_month_spend": current_month_spend,
                "parent_team_name": parent_team_name
            }

        except Exception as e:
            logger.error(f"Failed to get team stats: {e}")
            return {
                "member_count": 0,
                "sub_team_count": 0,
                "current_month_spend": 0.0,
                "parent_team_name": None
            }