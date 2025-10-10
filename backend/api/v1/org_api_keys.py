"""
Organization API Keys Management API

This module provides API endpoints for enterprise-level API key management,
including creation, updates, revocation, and usage tracking.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.permissions import require_permission, OrganizationRole
from backend.models.org_api_key import (
    OrgApiKeyCreate, OrgApiKeyUpdate, OrgApiKeyWithStats,
    ApiKeyGenerationResponse, ApiKeyStatus
)
from backend.services.org_api_key_service import OrgApiKeyService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.post("/organizations/{organization_id}/api-keys", response_model=ApiKeyGenerationResponse)
@require_permission("api_keys:create")
async def create_api_key(
    organization_id: str,
    key_data: OrgApiKeyCreate,
    request,
    db: Session = Depends(get_db)
):
    """
    Create a new API key for an organization

    Args:
        organization_id: Organization ID
        key_data: API key creation data
        request: FastAPI request object
        db: Database session

    Returns:
        Generated API key and details (key only shown once)
    """
    try:
        # Get current user ID from request state
        user_id = getattr(request.state, 'user_id', None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User authentication required"
            )

        # Ensure organization_id matches the key data
        key_data.organization_id = organization_id

        # Create API key
        key_service = OrgApiKeyService(db)
        result = await key_service.create_api_key(key_data, user_id)

        logger.info(f"API key created for organization {organization_id} by user {user_id}")
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@router.get("/organizations/{organization_id}/api-keys", response_model=List[OrgApiKeyWithStats])
@require_permission("api_keys:view")
async def get_organization_api_keys(
    organization_id: str,
    include_stats: bool = Query(default=True, description="Include usage statistics"),
    status_filter: Optional[str] = Query(None, description="Filter by status (active/suspended/revoked)"),
    db: Session = Depends(get_db)
):
    """
    Get all API keys for an organization

    Args:
        organization_id: Organization ID
        include_stats: Whether to include usage statistics
        status_filter: Optional status filter
        db: Database session

    Returns:
        List of API keys with optional statistics
    """
    try:
        key_service = OrgApiKeyService(db)
        api_keys = await key_service.get_api_keys_by_organization(organization_id, include_stats)

        # Apply status filter if provided
        if status_filter:
            try:
                status_enum = ApiKeyStatus(status_filter.lower())
                api_keys = [key for key in api_keys if key.status == status_enum]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter: {status_filter}"
                )

        return api_keys

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API keys"
        )


@router.get("/api-keys/{key_id}", response_model=OrgApiKeyWithStats)
@require_permission("api_keys:view")
async def get_api_key_details(
    key_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific API key

    Args:
        key_id: API key ID
        db: Database session

    Returns:
        API key details with statistics
    """
    try:
        key_service = OrgApiKeyService(db)
        api_key = await key_service.get_api_key_by_id(key_id)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        # Get organization ID to use existing method
        api_keys = await key_service.get_api_keys_by_organization(
            str(api_key.organization_id),
            include_stats=True
        )

        # Find the specific key
        key_details = next((k for k in api_keys if k.id == key_id), None)
        if not key_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        return key_details

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting API key details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API key details"
        )


@router.put("/api-keys/{key_id}", response_model=dict)
@require_permission("api_keys:edit")
async def update_api_key(
    key_id: str,
    key_data: OrgApiKeyUpdate,
    db: Session = Depends(get_db)
):
    """
    Update API key settings

    Args:
        key_id: API key ID
        key_data: Update data
        db: Database session

    Returns:
        Updated API key information
    """
    try:
        key_service = OrgApiKeyService(db)
        api_key = await key_service.update_api_key(key_id, key_data)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        return {
            "id": str(api_key.id),
            "organization_id": str(api_key.organization_id),
            "name": api_key.name,
            "status": api_key.status,
            "rate_limit": api_key.rate_limit,
            "monthly_quota": api_key.monthly_quota,
            "updated_at": api_key.updated_at.isoformat() if api_key.updated_at else None,
            "message": "API key updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API key"
        )


@router.post("/api-keys/{key_id}/revoke")
@require_permission("api_keys:delete")
async def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db)
):
    """
    Revoke an API key

    Args:
        key_id: API key ID
        db: Database session

    Returns:
        Revocation confirmation
    """
    try:
        key_service = OrgApiKeyService(db)
        success = await key_service.revoke_api_key(key_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        logger.info(f"API key {key_id} revoked")
        return {"message": "API key revoked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key"
        )


@router.get("/api-keys/{key_id}/usage")
@require_permission("api_keys:view")
async def get_api_key_usage(
    key_id: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get usage history for an API key

    Args:
        key_id: API key ID
        days: Number of days to look back
        db: Database session

    Returns:
        Usage history data
    """
    try:
        key_service = OrgApiKeyService(db)
        usage_history = await key_service.get_api_key_usage_history(key_id, days)

        # Get API key details for context
        api_key = await key_service.get_api_key_by_id(key_id)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        # Calculate statistics
        total_requests = sum(day['requests'] for day in usage_history)
        total_tokens = sum(day['tokens'] for day in usage_history)
        total_cost = sum(day['cost'] for day in usage_history)

        return {
            "key_id": key_id,
            "key_prefix": api_key.key_prefix,
            "organization_id": str(api_key.organization_id),
            "period_days": days,
            "usage_history": usage_history,
            "statistics": {
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "average_daily_requests": total_requests / max(len(usage_history), 1),
                "average_daily_tokens": total_tokens / max(len(usage_history), 1),
                "average_daily_cost": total_cost / max(len(usage_history), 1)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting API key usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage history"
        )


@router.post("/api-keys/{key_id}/regenerate")
@require_permission("api_keys:create")
async def regenerate_api_key(
    key_id: str,
    request,
    db: Session = Depends(get_db)
):
    """
    Regenerate an API key (create new key, revoke old one)

    Args:
        key_id: API key ID to regenerate
        request: FastAPI request object
        db: Database session

    Returns:
        New API key and details
    """
    try:
        # Get current user ID
        user_id = getattr(request.state, 'user_id', None)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User authentication required"
            )

        key_service = OrgApiKeyService(db)

        # Get current API key
        current_key = await key_service.get_api_key_by_id(key_id)
        if not current_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        # Parse permissions from current key
        import json
        permissions = {}
        try:
            permissions = json.loads(current_key.permissions) if current_key.permissions else {}
        except:
            permissions = {}

        # Create new key with same settings
        new_key_data = OrgApiKeyCreate(
            organization_id=str(current_key.organization_id),
            name=current_key.name + " (Regenerated)",
            permissions=permissions,
            rate_limit=current_key.rate_limit,
            monthly_quota=current_key.monthly_quota,
            expires_at=current_key.expires_at.isoformat() if current_key.expires_at else None
        )

        # Create new key
        new_key_result = await key_service.create_api_key(new_key_data, user_id)

        # Revoke old key
        await key_service.revoke_api_key(key_id)

        logger.info(f"API key {key_id} regenerated by user {user_id}")

        return {
            "message": "API key regenerated successfully",
            "old_key_revoked": True,
            "new_api_key": new_key_result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate API key"
        )


@router.get("/organizations/{organization_id}/api-keys/summary")
@require_permission("api_keys:view")
async def get_organization_api_keys_summary(
    organization_id: str,
    db: Session = Depends(get_db)
):
    """
    Get summary of all API keys for an organization

    Args:
        organization_id: Organization ID
        db: Database session

    Returns:
        Organization API keys summary
    """
    try:
        key_service = OrgApiKeyService(db)
        api_keys = await key_service.get_api_keys_by_organization(organization_id, include_stats=True)

        # Calculate summary statistics
        total_keys = len(api_keys)
        active_keys = len([k for k in api_keys if k.status == ApiKeyStatus.ACTIVE and k.is_active and not k.is_expired])
        suspended_keys = len([k for k in api_keys if k.status == ApiKeyStatus.SUSPENDED])
        revoked_keys = len([k for k in api_keys if k.status == ApiKeyStatus.REVOKED])
        expired_keys = len([k for k in api_keys if k.is_expired])

        # Usage statistics
        total_monthly_usage = sum(k.current_month_usage for k in api_keys)
        total_quota = sum(k.monthly_quota for k in api_keys)
        average_quota_usage = sum(k.quota_usage_percentage for k in api_keys) / max(len(api_keys), 1)

        # Find most used and least used keys
        most_used_key = max(api_keys, key=lambda k: k.current_month_usage) if api_keys else None
        least_used_key = min(api_keys, key=lambda k: k.current_month_usage) if api_keys else None

        return {
            "organization_id": organization_id,
            "summary": {
                "total_keys": total_keys,
                "active_keys": active_keys,
                "suspended_keys": suspended_keys,
                "revoked_keys": revoked_keys,
                "expired_keys": expired_keys
            },
            "usage_statistics": {
                "total_monthly_usage": total_monthly_usage,
                "total_quota": total_quota,
                "quota_utilization_percentage": (total_monthly_usage / max(total_quota, 1)) * 100,
                "average_quota_usage_percentage": average_quota_usage
            },
            "key_highlights": {
                "most_used_key": {
                    "name": most_used_key.name,
                    "usage": most_used_key.current_month_usage,
                    "key_prefix": most_used_key.key_prefix
                } if most_used_key else None,
                "least_used_key": {
                    "name": least_used_key.name,
                    "usage": least_used_key.current_month_usage,
                    "key_prefix": least_used_key.key_prefix
                } if least_used_key else None
            },
            "health_indicators": {
                "keys_needing_attention": len([
                    k for k in api_keys
                    if k.is_expired or k.status in [ApiKeyStatus.SUSPENDED, ApiKeyStatus.REVOKED]
                ]),
                "keys_over_quota": len([k for k in api_keys if k.quota_usage_percentage > 100]),
                "keys_near_quota_limit": len([k for k in api_keys if 80 <= k.quota_usage_percentage <= 100])
            }
        }

    except Exception as e:
        logger.error(f"Error getting API keys summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API keys summary"
        )


@router.post("/organizations/{organization_id}/api-keys/batch-operations")
@require_permission("api_keys:edit")
async def batch_update_api_keys(
    organization_id: str,
    operation: str = Query(..., description="Operation: suspend/activate/revoke"),
    key_ids: List[str] = Query(..., description="List of API key IDs"),
    db: Session = Depends(get_db)
):
    """
    Perform batch operations on multiple API keys

    Args:
        organization_id: Organization ID
        operation: Operation to perform
        key_ids: List of API key IDs
        db: Database session

    Returns:
        Batch operation results
    """
    try:
        key_service = OrgApiKeyService(db)
        results = {
            "operation": operation,
            "total_keys": len(key_ids),
            "successful": [],
            "failed": [],
            "errors": []
        }

        for key_id in key_ids:
            try:
                if operation == "suspend":
                    update_data = {"status": "suspended"}
                    api_key = await key_service.update_api_key(key_id, update_data)
                    if api_key:
                        results["successful"].append(key_id)
                    else:
                        results["failed"].append(key_id)
                        results["errors"].append(f"Key {key_id} not found")

                elif operation == "activate":
                    update_data = {"status": "active"}
                    api_key = await key_service.update_api_key(key_id, update_data)
                    if api_key:
                        results["successful"].append(key_id)
                    else:
                        results["failed"].append(key_id)
                        results["errors"].append(f"Key {key_id} not found")

                elif operation == "revoke":
                    success = await key_service.revoke_api_key(key_id)
                    if success:
                        results["successful"].append(key_id)
                    else:
                        results["failed"].append(key_id)
                        results["errors"].append(f"Key {key_id} not found")

                else:
                    results["failed"].append(key_id)
                    results["errors"].append(f"Invalid operation: {operation}")

            except Exception as e:
                results["failed"].append(key_id)
                results["errors"].append(str(e))

        logger.info(f"Batch {operation} completed for organization {organization_id}: "
                   f"{len(results['successful'])} successful, {len(results['failed'])} failed")

        return results

    except Exception as e:
        logger.error(f"Error in batch operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform batch operation"
        )