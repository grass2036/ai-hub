"""
Budget Service - Budget Control and Alert System

This service handles budget management, monitoring, and alerts for organizations.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, desc

from backend.models.budget import (
    Budget, BudgetCreate, BudgetUpdate, BudgetWithStats,
    BudgetAlert, BudgetStatus, calculate_projected_spend,
    get_days_remaining_in_month, should_send_budget_alert
)
from backend.models.organization import Organization
from backend.models.usage_record import UsageRecord
from backend.core.database import get_db

logger = logging.getLogger(__name__)


class BudgetExceededException(Exception):
    """Exception raised when budget limit is exceeded"""
    pass


class BudgetService:
    """Service for budget management and control"""

    def __init__(self, db: Session):
        self.db = db

    async def create_budget(self, budget_data: BudgetCreate) -> Budget:
        """
        Create a new budget for an organization

        Args:
            budget_data: Budget creation data

        Returns:
            Created budget

        Raises:
            ValueError: If organization doesn't exist or budget already exists
        """
        try:
            # Check if organization exists
            organization = self.db.execute(
                select(Organization)
                .where(Organization.id == budget_data.organization_id)
            ).scalar_one_or_none()

            if not organization:
                raise ValueError(f"Organization {budget_data.organization_id} not found")

            # Check if budget already exists for this organization
            existing_budget = self.db.execute(
                select(Budget)
                .where(Budget.organization_id == budget_data.organization_id)
            ).scalar_one_or_none()

            if existing_budget:
                raise ValueError(f"Budget already exists for organization {budget_data.organization_id}")

            # Create new budget
            budget = Budget(
                organization_id=budget_data.organization_id,
                monthly_limit=budget_data.monthly_limit,
                alert_threshold=budget_data.alert_threshold,
                currency=budget_data.currency,
                status=budget_data.status.value
            )

            self.db.add(budget)
            self.db.commit()
            self.db.refresh(budget)

            logger.info(f"Created budget for organization {budget_data.organization_id}")
            return budget

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating budget: {e}")
            raise

    async def get_budget_by_organization(self, organization_id: str) -> Optional[Budget]:
        """
        Get budget by organization ID

        Args:
            organization_id: Organization ID

        Returns:
            Budget or None if not found
        """
        try:
            budget = self.db.execute(
                select(Budget)
                .where(Budget.organization_id == organization_id)
            ).scalar_one_or_none()

            return budget

        except Exception as e:
            logger.error(f"Error getting budget for organization {organization_id}: {e}")
            return None

    async def get_budget_with_stats(self, organization_id: str) -> Optional[BudgetWithStats]:
        """
        Get budget with comprehensive statistics

        Args:
            organization_id: Organization ID

        Returns:
            Budget with statistics or None if not found
        """
        try:
            # Get basic budget
            budget = await self.get_budget_by_organization(organization_id)
            if not budget:
                return None

            # Calculate current month spend
            current_month_start = date.today().replace(day=1)
            current_month_spend = await self._calculate_month_spend(organization_id, current_month_start)

            # Calculate projected monthly spend
            today = date.today()
            days_passed = (today - current_month_start).days + 1
            days_in_month = self._get_days_in_month(today.year, today.month)
            projected_spend = calculate_projected_spend(current_month_spend, days_passed, days_in_month)

            # Build response with stats
            budget_stats = BudgetWithStats(
                id=str(budget.id),
                organization_id=str(budget.organization_id),
                monthly_limit=budget.monthly_limit,
                current_spend=current_month_spend,
                alert_threshold=budget.alert_threshold,
                currency=budget.currency,
                status=BudgetStatus(budget.status),
                created_at=budget.created_at.isoformat() if budget.created_at else "",
                updated_at=budget.updated_at.isoformat() if budget.updated_at else "",
                usage_percentage=budget.usage_percentage,
                remaining_budget=budget.remaining_budget,
                is_alert_threshold_reached=budget.is_alert_threshold_reached,
                is_budget_exceeded=budget.is_budget_exceeded,
                current_month_spend=current_month_spend,
                projected_monthly_spend=projected_spend,
                days_remaining_in_month=get_days_remaining_in_month()
            )

            return budget_stats

        except Exception as e:
            logger.error(f"Error getting budget stats for organization {organization_id}: {e}")
            return None

    async def update_budget(self, organization_id: str, budget_data: BudgetUpdate) -> Optional[Budget]:
        """
        Update budget settings

        Args:
            organization_id: Organization ID
            budget_data: Update data

        Returns:
            Updated budget or None if not found
        """
        try:
            budget = self.db.execute(
                select(Budget)
                .where(Budget.organization_id == organization_id)
            ).scalar_one_or_none()

            if not budget:
                return None

            # Update fields
            update_data = budget_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(budget, field):
                    if field == 'status' and isinstance(value, str):
                        setattr(budget, field, BudgetStatus(value).value)
                    else:
                        setattr(budget, field, value)

            self.db.commit()
            self.db.refresh(budget)

            logger.info(f"Updated budget for organization {organization_id}")
            return budget

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating budget: {e}")
            return None

    async def delete_budget(self, organization_id: str) -> bool:
        """
        Delete budget for organization

        Args:
            organization_id: Organization ID

        Returns:
            True if deleted, False if not found
        """
        try:
            budget = self.db.execute(
                select(Budget)
                .where(Budget.organization_id == organization_id)
            ).scalar_one_or_none()

            if not budget:
                return False

            self.db.delete(budget)
            self.db.commit()

            logger.info(f"Deleted budget for organization {organization_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting budget: {e}")
            return False

    async def check_budget_limit(self, organization_id: str, estimated_cost: Decimal) -> bool:
        """
        Check if a transaction would exceed budget limit

        Args:
            organization_id: Organization ID
            estimated_cost: Estimated cost of transaction

        Returns:
            True if within budget, raises BudgetExceededException if over limit

        Raises:
            BudgetExceededException: If transaction would exceed budget
        """
        try:
            budget = await self.get_budget_by_organization(organization_id)
            if not budget:
                # No budget set, allow transaction
                return True

            if budget.status != BudgetStatus.ACTIVE.value:
                # Inactive budget, allow transaction
                return True

            # Calculate current month spend
            current_month_start = date.today().replace(day=1)
            current_month_spend = await self._calculate_month_spend(organization_id, current_month_start)

            # Check if transaction would exceed limit
            projected_spend = current_month_spend + estimated_cost
            if projected_spend > budget.monthly_limit:
                raise BudgetExceededException(
                    f"Transaction would exceed budget limit. "
                    f"Current: ${current_month_spend:.2f}, "
                    f"Transaction: ${estimated_cost:.2f}, "
                    f"Limit: ${budget.monthly_limit:.2f}"
                )

            return True

        except BudgetExceededException:
            raise
        except Exception as e:
            logger.error(f"Error checking budget limit: {e}")
            # On error, allow transaction to proceed
            return True

    async def record_usage(self, organization_id: str, user_id: str, team_id: Optional[str],
                          service: str, model: str, tokens: int, cost: Decimal) -> bool:
        """
        Record usage and update budget spend

        Args:
            organization_id: Organization ID
            user_id: User ID
            team_id: Team ID (optional)
            service: AI service used
            model: AI model used
            tokens: Number of tokens
            cost: Cost of usage

        Returns:
            True if recorded successfully
        """
        try:
            # Create usage record
            usage_record = UsageRecord(
                organization_id=organization_id,
                user_id=user_id,
                team_id=team_id,
                service=service,
                model=model,
                tokens=tokens,
                cost=cost,
                timestamp=datetime.utcnow()
            )

            self.db.add(usage_record)

            # Update budget current spend
            budget = await self.get_budget_by_organization(organization_id)
            if budget:
                budget.current_spend += cost

                # Check if budget exceeded
                if budget.is_budget_exceeded and budget.status == BudgetStatus.ACTIVE.value:
                    budget.status = BudgetStatus.EXCEEDED.value
                    logger.warning(f"Budget exceeded for organization {organization_id}")

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error recording usage: {e}")
            return False

    async def get_budget_alerts(self, organization_id: Optional[str] = None) -> List[BudgetAlert]:
        """
        Get budget alerts for organizations

        Args:
            organization_id: Optional organization ID to filter by

        Returns:
            List of budget alerts
        """
        try:
            # Build query
            query = select(Budget).where(Budget.status == BudgetStatus.ACTIVE.value)
            if organization_id:
                query = query.where(Budget.organization_id == organization_id)

            budgets = self.db.execute(query).scalars().all()

            alerts = []
            for budget in budgets:
                if should_send_budget_alert(budget):
                    # Get organization details
                    org = self.db.execute(
                        select(Organization)
                        .where(Organization.id == budget.organization_id)
                    ).scalar_one_or_none()

                    if org:
                        # Calculate current month spend
                        current_month_start = date.today().replace(day=1)
                        current_month_spend = await self._calculate_month_spend(
                            str(budget.organization_id), current_month_start
                        )

                        # Calculate projected spend
                        today = date.today()
                        days_passed = (today - current_month_start).days + 1
                        days_in_month = self._get_days_in_month(today.year, today.month)
                        projected_spend = calculate_projected_spend(current_month_spend, days_passed, days_in_month)

                        alert = BudgetAlert(
                            organization_id=str(budget.organization_id),
                            organization_name=org.name,
                            current_spend=current_month_spend,
                            monthly_limit=budget.monthly_limit,
                            usage_percentage=budget.usage_percentage,
                            alert_threshold=budget.alert_threshold,
                            currency=budget.currency,
                            days_remaining_in_month=get_days_remaining_in_month(),
                            projected_monthly_spend=projected_spend
                        )
                        alerts.append(alert)

            return alerts

        except Exception as e:
            logger.error(f"Error getting budget alerts: {e}")
            return []

    async def get_usage_history(self, organization_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get usage history for an organization

        Args:
            organization_id: Organization ID
            days: Number of days to look back

        Returns:
            List of daily usage records
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # Query usage records grouped by day
            usage_by_day = self.db.execute(
                select(
                    func.date(UsageRecord.timestamp).label('date'),
                    func.sum(UsageRecord.tokens).label('tokens'),
                    func.sum(UsageRecord.cost).label('cost'),
                    func.count(UsageRecord.id).label('requests')
                )
                .where(
                    and_(
                        UsageRecord.organization_id == organization_id,
                        UsageRecord.timestamp >= start_date
                    )
                )
                .group_by(func.date(UsageRecord.timestamp))
                .order_by(desc(func.date(UsageRecord.timestamp)))
            ).all()

            # Convert to list of dicts
            history = []
            for record in usage_by_day:
                history.append({
                    'date': record.date.isoformat() if record.date else None,
                    'tokens': int(record.tokens) if record.tokens else 0,
                    'cost': float(record.cost) if record.cost else 0.0,
                    'requests': int(record.requests) if record.requests else 0
                })

            return history

        except Exception as e:
            logger.error(f"Error getting usage history: {e}")
            return []

    # Private helper methods

    async def _calculate_month_spend(self, organization_id: str, month_start: date) -> Decimal:
        """Calculate total spend for a specific month"""
        try:
            month_end = self._get_last_day_of_month(month_start.year, month_start.month)

            total_cost = self.db.execute(
                select(func.sum(UsageRecord.cost))
                .where(
                    and_(
                        UsageRecord.organization_id == organization_id,
                        UsageRecord.timestamp >= month_start,
                        UsageRecord.timestamp <= month_end
                    )
                )
            ).scalar()

            return Decimal(str(total_cost)) if total_cost else Decimal('0.00')

        except Exception as e:
            logger.error(f"Error calculating month spend: {e}")
            return Decimal('0.00')

    def _get_days_in_month(self, year: int, month: int) -> int:
        """Get number of days in a specific month"""
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        return last_day.day

    def _get_last_day_of_month(self, year: int, month: int) -> date:
        """Get the last day of a specific month"""
        if month == 12:
            return date(year + 1, 1, 1) - timedelta(days=1)
        else:
            return date(year, month + 1, 1) - timedelta(days=1)


# Utility functions for working with budgets
def get_budget_service(db: Session = None) -> BudgetService:
    """Get budget service instance"""
    if db is None:
        db = next(get_db())
    return BudgetService(db)


async def check_organization_budget(organization_id: str, estimated_cost: Decimal) -> bool:
    """
    Check if organization has sufficient budget for a transaction

    Args:
        organization_id: Organization ID
        estimated_cost: Estimated cost

    Returns:
        True if within budget limits
    """
    db = next(get_db())
    budget_service = BudgetService(db)
    return await budget_service.check_budget_limit(organization_id, estimated_cost)