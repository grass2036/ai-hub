"""
Organization Service - Multi-tenant Organization Management
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, select
from fastapi import HTTPException, status

from backend.models.organization import Organization, OrganizationCreate, OrganizationUpdate, OrganizationResponse
from backend.models.member import Member, OrganizationRole, MemberCreate
from backend.models.user import User
from backend.models.budget import Budget, BudgetCreate
from backend.core.database import get_db

logger = logging.getLogger(__name__)


class OrganizationService:
    """Service for managing organizations in multi-tenant environment"""

    def __init__(self, db: Session):
        self.db = db

    async def create_organization(
        self,
        organization_data: OrganizationCreate,
        owner_user_id: str
    ) -> OrganizationResponse:
        """
        Create a new organization and make the user the owner

        Args:
            organization_data: Organization creation data
            owner_user_id: User ID who will become the organization owner

        Returns:
            Created organization response

        Raises:
            HTTPException: If organization slug already exists
        """
        try:
            # Check if slug already exists
            existing_org = self.db.execute(
                select(Organization).where(Organization.slug == organization_data.slug)
            ).scalar_one_or_none()

            if existing_org:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Organization with slug '{organization_data.slug}' already exists"
                )

            # Create organization
            organization = Organization(
                name=organization_data.name,
                slug=organization_data.slug,
                description=organization_data.description,
                logo_url=organization_data.logo_url,
                plan=organization_data.plan.value,
                settings=organization_data.settings
            )

            self.db.add(organization)
            self.db.flush()  # Get the organization ID

            # Create owner membership
            owner_member = Member(
                user_id=owner_user_id,
                organization_id=organization.id,
                role=OrganizationRole.OWNER,
                permissions={"all": True},
                invited_by=owner_user_id
            )

            self.db.add(owner_member)

            # Create default budget for the organization
            default_budget = Budget(
                organization_id=organization.id,
                monthly_limit=100.0,  # Default budget
                alert_threshold=80.0,
                currency="USD"
            )

            self.db.add(default_budget)

            self.db.commit()
            self.db.refresh(organization)

            logger.info(f"Created organization '{organization.name}' with owner {owner_user_id}")

            return OrganizationResponse.from_orm(organization)

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create organization: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create organization"
            )

    async def get_user_organizations(self, user_id: str) -> List[OrganizationResponse]:
        """
        Get all organizations where the user is a member

        Args:
            user_id: User ID

        Returns:
            List of organizations the user belongs to
        """
        try:
            # Get organizations through user's memberships
            result = self.db.execute(
                select(Organization)
                .join(Member)
                .where(
                    and_(
                        Member.user_id == user_id,
                        Organization.status == "active"
                    )
                )
                .order_by(Organization.created_at.desc())
            ).scalars().all()

            return [OrganizationResponse.from_orm(org) for org in result]

        except Exception as e:
            logger.error(f"Failed to get user organizations: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve organizations"
            )

    async def get_organization_by_id(
        self,
        organization_id: str,
        user_id: str
    ) -> OrganizationResponse:
        """
        Get organization details by ID (only if user is a member)

        Args:
            organization_id: Organization ID
            user_id: User ID requesting the organization

        Returns:
            Organization details

        Raises:
            HTTPException: If organization not found or user not a member
        """
        try:
            # Check if user is a member of the organization
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

            # Get organization details
            organization = self.db.execute(
                select(Organization)
                .where(Organization.id == organization_id)
            ).scalar_one_or_none()

            if not organization:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found"
                )

            return OrganizationResponse.from_orm(organization)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get organization {organization_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve organization"
            )

    async def update_organization(
        self,
        organization_id: str,
        organization_data: OrganizationUpdate,
        user_id: str
    ) -> OrganizationResponse:
        """
        Update organization details (requires admin or owner role)

        Args:
            organization_id: Organization ID
            organization_data: Update data
            user_id: User ID making the request

        Returns:
            Updated organization

        Raises:
            HTTPException: If insufficient permissions or organization not found
        """
        try:
            # Check user permissions
            membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == user_id,
                        Member.organization_id == organization_id,
                        Member.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN])
                    )
                )
            ).scalar_one_or_none()

            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to update organization"
                )

            # Get organization
            organization = self.db.execute(
                select(Organization)
                .where(Organization.id == organization_id)
            ).scalar_one_or_none()

            if not organization:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found"
                )

            # Update organization fields
            update_data = organization_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(organization, field):
                    setattr(organization, field, value)

            self.db.commit()
            self.db.refresh(organization)

            logger.info(f"Updated organization '{organization.name}' by user {user_id}")

            return OrganizationResponse.from_orm(organization)

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update organization {organization_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update organization"
            )

    async def delete_organization(
        self,
        organization_id: str,
        user_id: str
    ) -> bool:
        """
        Delete organization (requires owner role)

        Args:
            organization_id: Organization ID
            user_id: User ID making the request

        Returns:
            True if deleted successfully

        Raises:
            HTTPException: If insufficient permissions or organization not found
        """
        try:
            # Check if user is the owner
            membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == user_id,
                        Member.organization_id == organization_id,
                        Member.role == OrganizationRole.OWNER
                    )
                )
            ).scalar_one_or_none()

            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only organization owners can delete organizations"
                )

            # Get organization
            organization = self.db.execute(
                select(Organization)
                .where(Organization.id == organization_id)
            ).scalar_one_or_none()

            if not organization:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found"
                )

            # Soft delete by updating status
            organization.status = "deleted"
            self.db.commit()

            logger.info(f"Deleted organization '{organization.name}' by owner {user_id}")

            return True

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete organization {organization_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete organization"
            )

    async def invite_member(
        self,
        organization_id: str,
        email: str,
        role: OrganizationRole,
        invited_by_user_id: str
    ) -> Dict[str, Any]:
        """
        Invite a user to join an organization

        Args:
            organization_id: Organization ID
            email: Email address to invite
            role: Role to assign to the user
            invited_by_user_id: User ID sending the invitation

        Returns:
            Invitation details

        Raises:
            HTTPException: If insufficient permissions or user already a member
        """
        try:
            # Check inviter permissions (must be admin or owner)
            inviter_membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == invited_by_user_id,
                        Member.organization_id == organization_id,
                        Member.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN])
                    )
                )
            ).scalar_one_or_none()

            if not inviter_membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to invite members"
                )

            # Find user by email
            invited_user = self.db.execute(
                select(User)
                .where(User.email == email.lower())
            ).scalar_one_or_none()

            if not invited_user:
                # For now, create a simple response. In a real implementation,
                # you would send an invitation email
                return {
                    "message": "Invitation sent successfully",
                    "email": email,
                    "organization_id": organization_id,
                    "role": role.value,
                    "note": "User will need to register first"
                }

            # Check if user is already a member
            existing_membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == invited_user.id,
                        Member.organization_id == organization_id
                    )
                )
            ).scalar_one_or_none()

            if existing_membership:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User is already a member of this organization"
                )

            # Create membership
            new_member = Member(
                user_id=invited_user.id,
                organization_id=organization_id,
                role=role,
                permissions={"member": True},
                invited_by=invited_by_user_id
            )

            self.db.add(new_member)
            self.db.commit()

            logger.info(f"Invited user {email} to organization {organization_id} as {role.value}")

            return {
                "message": "User added to organization successfully",
                "user_id": str(invited_user.id),
                "email": email,
                "organization_id": organization_id,
                "role": role.value
            }

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to invite member to organization {organization_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to invite member"
            )

    async def remove_member(
        self,
        organization_id: str,
        member_user_id: str,
        requesting_user_id: str
    ) -> bool:
        """
        Remove a member from an organization

        Args:
            organization_id: Organization ID
            member_user_id: User ID to remove
            requesting_user_id: User ID making the request

        Returns:
            True if removed successfully

        Raises:
            HTTPException: If insufficient permissions or operation not allowed
        """
        try:
            # Check permissions (admin/owner can remove members, owners can remove other owners)
            requester_membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == requesting_user_id,
                        Member.organization_id == organization_id
                    )
                )
            ).scalar_one_or_none()

            if not requester_membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not a member of this organization"
                )

            # Get member to remove
            member_to_remove = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == member_user_id,
                        Member.organization_id == organization_id
                    )
                )
            ).scalar_one_or_none()

            if not member_to_remove:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Member not found"
                )

            # Permission checks
            can_remove = False

            # Owners can remove anyone except themselves (they need to transfer ownership)
            if requester_membership.role == OrganizationRole.OWNER:
                if member_user_id != requesting_user_id:
                    can_remove = True

            # Admins can remove members and viewers, but not owners or other admins
            elif requester_membership.role == OrganizationRole.ADMIN:
                if member_to_remove.role in [OrganizationRole.MEMBER, OrganizationRole.VIEWER]:
                    can_remove = True

            # Users can remove themselves
            elif member_user_id == requesting_user_id:
                can_remove = True

            if not can_remove:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to remove this member"
                )

            # Check if this is the last owner
            if member_to_remove.role == OrganizationRole.OWNER:
                owner_count = self.db.execute(
                    select(Member)
                    .where(
                        and_(
                            Member.organization_id == organization_id,
                            Member.role == OrganizationRole.OWNER
                        )
                    )
                ).scalar()

                if owner_count <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot remove the last owner of an organization"
                    )

            # Remove the member
            self.db.delete(member_to_remove)
            self.db.commit()

            logger.info(f"Removed member {member_user_id} from organization {organization_id} by {requesting_user_id}")

            return True

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to remove member from organization {organization_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove member"
            )

    async def update_member_role(
        self,
        organization_id: str,
        member_user_id: str,
        new_role: OrganizationRole,
        requesting_user_id: str
    ) -> bool:
        """
        Update a member's role in an organization

        Args:
            organization_id: Organization ID
            member_user_id: User ID to update
            new_role: New role to assign
            requesting_user_id: User ID making the request

        Returns:
            True if updated successfully

        Raises:
            HTTPException: If insufficient permissions or invalid operation
        """
        try:
            # Check permissions (only owners can change roles)
            requester_membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == requesting_user_id,
                        Member.organization_id == organization_id,
                        Member.role == OrganizationRole.OWNER
                    )
                )
            ).scalar_one_or_none()

            if not requester_membership:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only organization owners can change member roles"
                )

            # Get member to update
            member_to_update = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == member_user_id,
                        Member.organization_id == organization_id
                    )
                )
            ).scalar_one_or_none()

            if not member_to_update:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Member not found"
                )

            # Prevent owners from changing their own role (to avoid orphaned organizations)
            if member_user_id == requesting_user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot change your own role. Transfer ownership first"
                )

            # If changing away from owner, ensure there will be at least one owner left
            if member_to_update.role == OrganizationRole.OWNER and new_role != OrganizationRole.OWNER:
                owner_count = self.db.execute(
                    select(Member)
                    .where(
                        and_(
                            Member.organization_id == organization_id,
                            Member.role == OrganizationRole.OWNER
                        )
                    )
                ).scalar()

                if owner_count <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot remove the last owner of an organization"
                    )

            # Update the role
            member_to_update.role = new_role

            # Update permissions based on role
            if new_role == OrganizationRole.OWNER:
                member_to_update.permissions = {"all": True}
            elif new_role == OrganizationRole.ADMIN:
                member_to_update.permissions = {
                    "organizations": ["read", "write"],
                    "members": ["read", "write", "invite"],
                    "teams": ["read", "write", "delete"],
                    "budgets": ["read", "write"],
                    "api_keys": ["read", "write", "delete"]
                }
            elif new_role == OrganizationRole.MEMBER:
                member_to_update.permissions = {
                    "organizations": ["read"],
                    "teams": ["read"],
                    "api_keys": ["read", "write"]
                }
            else:  # VIEWER
                member_to_update.permissions = {
                    "organizations": ["read"],
                    "teams": ["read"]
                }

            self.db.commit()

            logger.info(f"Updated member {member_user_id} role to {new_role.value} in organization {organization_id} by {requesting_user_id}")

            return True

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update member role in organization {organization_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update member role"
            )

    async def get_organization_members(
        self,
        organization_id: str,
        requesting_user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all members of an organization

        Args:
            organization_id: Organization ID
            requesting_user_id: User ID making the request

        Returns:
            List of organization members

        Raises:
            HTTPException: If insufficient permissions or organization not found
        """
        try:
            # Check if user is a member
            membership = self.db.execute(
                select(Member)
                .where(
                    and_(
                        Member.user_id == requesting_user_id,
                        Member.organization_id == organization_id
                    )
                )
            ).scalar_one_or_none()

            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found or access denied"
                )

            # Get all members with user details
            result = self.db.execute(
                select(Member, User)
                .join(User)
                .where(Member.organization_id == organization_id)
                .order_by(Member.joined_at.asc())
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
                    "permissions": member.permissions,
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                    "invited_by": str(member.invited_by) if member.invited_by else None
                })

            return members

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get organization members: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve organization members"
            )