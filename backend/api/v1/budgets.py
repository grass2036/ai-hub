"""
Budget Management API

This module provides API endpoints for budget management,
monitoring, and alerts for organizations.
"""

import logging
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.permissions import require_permission, OrganizationRole
from backend.models.budget import (
    BudgetCreate, BudgetUpdate, BudgetWithStats, BudgetAlert,
    calculate_projected_spend, get_days_remaining_in_month
)
from backend.services.budget_service import BudgetService, BudgetExceededException

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.post("/organizations/{organization_id}/budgets", response_model=dict)
@require_permission("budgets:edit")
async def create_budget(
    organization_id: str,
    budget_data: BudgetCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new budget for an organization

    Args:
        organization_id: Organization ID
        budget_data: Budget creation data
        db: Database session

    Returns:
        Created budget information
    """
    try:
        # Ensure organization_id matches the budget data
        budget_data.organization_id = organization_id

        # Create budget
        budget_service = BudgetService(db)
        budget = await budget_service.create_budget(budget_data)

        return {
            "id": str(budget.id),
            "organization_id": str(budget.organization_id),
            "monthly_limit": float(budget.monthly_limit),
            "current_spend": float(budget.current_spend),
            "alert_threshold": float(budget.alert_threshold),
            "currency": budget.currency,
            "status": budget.status,
            "created_at": budget.created_at.isoformat() if budget.created_at else None,
            "message": "Budget created successfully"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create budget"
        )


@router.get("/organizations/{organization_id}/budgets", response_model=BudgetWithStats)
@require_permission("budgets:view")
async def get_budget(
    organization_id: str,
    db: Session = Depends(get_db)
):
    """
    Get budget information with statistics for an organization

    Args:
        organization_id: Organization ID
        db: Database session

    Returns:
        Budget with comprehensive statistics
    """
    try:
        budget_service = BudgetService(db)
        budget_stats = await budget_service.get_budget_with_stats(organization_id)

        if not budget_stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found for this organization"
            )

        return budget_stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve budget information"
        )


@router.put("/organizations/{organization_id}/budgets", response_model=dict)
@require_permission("budgets:edit")
async def update_budget(
    organization_id: str,
    budget_data: BudgetUpdate,
    db: Session = Depends(get_db)
):
    """
    Update budget settings for an organization

    Args:
        organization_id: Organization ID
        budget_data: Budget update data
        db: Database session

    Returns:
        Updated budget information
    """
    try:
        budget_service = BudgetService(db)
        budget = await budget_service.update_budget(organization_id, budget_data)

        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found for this organization"
            )

        return {
            "id": str(budget.id),
            "organization_id": str(budget.organization_id),
            "monthly_limit": float(budget.monthly_limit),
            "current_spend": float(budget.current_spend),
            "alert_threshold": float(budget.alert_threshold),
            "currency": budget.currency,
            "status": budget.status,
            "updated_at": budget.updated_at.isoformat() if budget.updated_at else None,
            "message": "Budget updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update budget"
        )


@router.delete("/organizations/{organization_id}/budgets")
@require_permission("budgets:edit")
async def delete_budget(
    organization_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete budget for an organization

    Args:
        organization_id: Organization ID
        db: Database session

    Returns:
        Deletion confirmation
    """
    try:
        budget_service = BudgetService(db)
        success = await budget_service.delete_budget(organization_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found for this organization"
            )

        return {"message": "Budget deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete budget"
        )


@router.get("/organizations/{organization_id}/budgets/usage")
@require_permission("budgets:view")
async def get_budget_usage(
    organization_id: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get budget usage history for an organization

    Args:
        organization_id: Organization ID
        days: Number of days to look back
        db: Database session

    Returns:
        Usage history data
    """
    try:
        budget_service = BudgetService(db)
        usage_history = await budget_service.get_usage_history(organization_id, days)

        return {
            "organization_id": organization_id,
            "period_days": days,
            "usage_history": usage_history,
            "total_records": len(usage_history)
        }

    except Exception as e:
        logger.error(f"Error getting budget usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage history"
        )


@router.post("/organizations/{organization_id}/budgets/alerts")
@require_permission("budgets:edit")
async def configure_budget_alerts(
    organization_id: str,
    alert_threshold: float = Query(..., ge=0, le=100, description="Alert threshold percentage"),
    db: Session = Depends(get_db)
):
    """
    Configure budget alert settings for an organization

    Args:
        organization_id: Organization ID
        alert_threshold: Alert threshold percentage
        db: Database session

    Returns:
        Updated alert configuration
    """
    try:
        # Update budget alert threshold
        budget_update = BudgetUpdate(alert_threshold=Decimal(str(alert_threshold)))
        budget_service = BudgetService(db)
        budget = await budget_service.update_budget(organization_id, budget_update)

        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found for this organization"
            )

        return {
            "organization_id": organization_id,
            "alert_threshold": float(budget.alert_threshold),
            "message": "Budget alerts configured successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error configuring budget alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure budget alerts"
        )


@router.get("/organizations/{organization_id}/budgets/alerts/test")
@require_permission("budgets:view")
async def test_budget_alerts(
    organization_id: str,
    db: Session = Depends(get_db)
):
    """
    Test budget alert configuration for an organization

    Args:
        organization_id: Organization ID
        db: Database session

    Returns:
        Alert test results
    """
    try:
        budget_service = BudgetService(db)
        alerts = await budget_service.get_budget_alerts(organization_id)

        # Get current budget status
        budget_stats = await budget_service.get_budget_with_stats(organization_id)

        if not budget_stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found for this organization"
            )

        return {
            "organization_id": organization_id,
            "current_status": {
                "usage_percentage": budget_stats.usage_percentage,
                "is_alert_threshold_reached": budget_stats.is_alert_threshold_reached,
                "is_budget_exceeded": budget_stats.is_budget_exceeded,
                "remaining_budget": float(budget_stats.remaining_budget),
                "days_remaining_in_month": budget_stats.days_remaining_in_month
            },
            "alerts": alerts,
            "alert_count": len(alerts),
            "would_send_alert": len(alerts) > 0
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing budget alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test budget alerts"
        )


@router.get("/budgets/alerts", response_model=List[BudgetAlert])
@require_permission("budgets:view")
async def get_all_budget_alerts(
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    db: Session = Depends(get_db)
):
    """
    Get all budget alerts (for admin monitoring)

    Args:
        organization_id: Optional organization ID filter
        db: Database session

    Returns:
        List of budget alerts
    """
    try:
        budget_service = BudgetService(db)
        alerts = await budget_service.get_budget_alerts(organization_id)

        return alerts

    except Exception as e:
        logger.error(f"Error getting budget alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve budget alerts"
        )


@router.post("/organizations/{organization_id}/budgets/check")
@require_permission("budgets:view")
async def check_budget_limit(
    organization_id: str,
    estimated_cost: float = Query(..., ge=0, description="Estimated cost to check"),
    db: Session = Depends(get_db)
):
    """
    Check if a transaction would exceed budget limits

    Args:
        organization_id: Organization ID
        estimated_cost: Estimated cost of transaction
        db: Database session

    Returns:
        Budget check result
    """
    try:
        budget_service = BudgetService(db)

        try:
            within_budget = await budget_service.check_budget_limit(
                organization_id,
                Decimal(str(estimated_cost))
            )

            return {
                "organization_id": organization_id,
                "estimated_cost": estimated_cost,
                "within_budget": within_budget,
                "message": "Transaction within budget limits" if within_budget else "Transaction would exceed budget"
            }

        except BudgetExceededException as e:
            return {
                "organization_id": organization_id,
                "estimated_cost": estimated_cost,
                "within_budget": False,
                "message": str(e),
                "budget_exceeded": True
            }

    except Exception as e:
        logger.error(f"Error checking budget limit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check budget limit"
        )


@router.get("/organizations/{organization_id}/budgets/summary")
@require_permission("budgets:view")
async def get_budget_summary(
    organization_id: str,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive budget summary for an organization

    Args:
        organization_id: Organization ID
        db: Database session

    Returns:
        Budget summary with projections and recommendations
    """
    try:
        budget_service = BudgetService(db)
        budget_stats = await budget_service.get_budget_with_stats(organization_id)

        if not budget_stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found for this organization"
            )

        # Get recent usage for trend analysis
        recent_usage = await budget_service.get_usage_history(organization_id, 7)

        # Calculate recommendations
        recommendations = _generate_budget_recommendations(budget_stats, recent_usage)

        return {
            "organization_id": organization_id,
            "budget_status": budget_stats.dict(),
            "recent_trend": {
                "last_7_days_usage": recent_usage,
                "average_daily_spend": sum(day['cost'] for day in recent_usage) / max(len(recent_usage), 1)
            },
            "projections": {
                "projected_monthly_spend": float(budget_stats.projected_monthly_spend),
                "days_remaining": budget_stats.days_remaining_in_month,
                "recommended_budget_adjustment": _calculate_recommended_adjustment(budget_stats)
            },
            "recommendations": recommendations,
            "health_status": _assess_budget_health(budget_stats)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting budget summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve budget summary"
        )


# Helper functions

def _generate_budget_recommendations(budget_stats: BudgetWithStats, recent_usage: List[dict]) -> List[str]:
    """Generate budget recommendations based on current status"""
    recommendations = []

    if budget_stats.is_budget_exceeded:
        recommendations.append("Budget exceeded! Consider increasing the budget limit or reducing usage.")

    if budget_stats.is_alert_threshold_reached:
        recommendations.append(f"Alert threshold ({budget_stats.alert_threshold}%) reached. Monitor usage closely.")

    if budget_stats.usage_percentage > 90:
        recommendations.append("Usage is very high. Consider upgrading to a higher tier plan.")

    if budget_stats.projected_monthly_spend > budget_stats.monthly_limit:
        recommendations.append("Projected spend will exceed budget. Adjust usage or budget limits.")

    if budget_stats.days_remaining_in_month < 7 and budget_stats.usage_percentage > 80:
        recommendations.append("Less than a week remaining with high usage. Plan for next month's budget.")

    if not recommendations:
        recommendations.append("Budget usage is within healthy limits.")

    return recommendations


def _calculate_recommended_adjustment(budget_stats: BudgetWithStats) -> Optional[float]:
    """Calculate recommended budget adjustment"""
    if budget_stats.projected_monthly_spend > budget_stats.monthly_limit:
        # Recommend 20% buffer above projected spend
        return float(budget_stats.projected_monthly_spend * Decimal('1.2'))
    return None


def _assess_budget_health(budget_stats: BudgetWithStats) -> str:
    """Assess overall budget health"""
    if budget_stats.is_budget_exceeded:
        return "critical"
    elif budget_stats.is_alert_threshold_reached:
        return "warning"
    elif budget_stats.usage_percentage > 80:
        return "caution"
    else:
        return "healthy"