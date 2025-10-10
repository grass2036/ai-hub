"""
Budget Control Middleware

This middleware provides real-time budget monitoring and control
for API requests, preventing overspending and providing alerts.
"""

import logging
from typing import Optional, Dict, Any, Callable
from decimal import Decimal
from datetime import datetime

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.services.budget_service import BudgetService, BudgetExceededException
from backend.services.org_api_key_service import OrgApiKeyService, ApiKeyQuotaExceededException, ApiKeyExpiredException
from backend.models.budget import BudgetStatus
from backend.models.org_api_key import ApiKeyStatus

logger = logging.getLogger(__name__)


class BudgetControlMiddleware(BaseHTTPMiddleware):
    """
    Middleware for real-time budget control and API quota management

    This middleware:
    1. Validates API keys and checks quota limits
    2. Checks budget limits before processing requests
    3. Tracks usage and updates budget spend
    4. Provides real-time alerts for budget issues
    """

    def __init__(self, app, enable_hard_limits: bool = True):
        super().__init__(app)
        self.enable_hard_limits = enable_hard_limits
        self._budget_service_cache: Dict[str, BudgetService] = {}
        self._api_key_service_cache: Dict[str, OrgApiKeyService] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip budget control for certain endpoints
        if self._should_skip_budget_control(request):
            return await call_next(request)

        # Extract API key from request
        api_key = self._extract_api_key(request)
        if not api_key:
            # No API key, proceed without budget control
            return await call_next(request)

        try:
            # Validate API key and get context
            api_key_record = await self._validate_api_key(api_key)
            if not api_key_record:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )

            # Inject API key context into request state
            request.state.api_key_id = str(api_key_record.id)
            request.state.organization_id = str(api_key_record.organization_id)
            request.state.api_key_prefix = api_key_record.key_prefix

            # Estimate cost for the request
            estimated_cost = await self._estimate_request_cost(request)
            if estimated_cost > 0:
                # Check budget limits
                await self._check_budget_limits(request.state.organization_id, estimated_cost)

            # Process the request
            response = await call_next(request)

            # Record actual usage if cost estimation available
            if estimated_cost > 0 and response.status_code < 400:
                await self._record_usage(request, estimated_cost)

            return response

        except (BudgetExceededException, ApiKeyQuotaExceededException) as e:
            logger.warning(f"Budget/Quota limit exceeded: {e}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Budget or quota limit exceeded",
                    "message": str(e),
                    "type": "budget_exceeded" if isinstance(e, BudgetExceededException) else "quota_exceeded"
                }
            )

        except ApiKeyExpiredException as e:
            logger.warning(f"API key expired: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "API key expired",
                    "message": str(e),
                    "type": "api_key_expired"
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in budget control middleware: {e}")
            # On error, allow request to proceed
            return await call_next(request)

    def _should_skip_budget_control(self, request: Request) -> bool:
        """Check if budget control should be skipped for this request"""
        # Public endpoints that don't need budget control
        public_paths = [
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/status",
            "/auth/login",
            "/auth/register",
            "/models"
        ]

        # Check if path starts with any public path
        return any(request.url.path.startswith(path) for path in public_paths)

    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request headers"""
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix

        # Check API key header
        api_key_header = request.headers.get("X-API-Key")
        if api_key_header:
            return api_key_header

        return None

    async def _validate_api_key(self, api_key: str):
        """Validate API key and return key record"""
        try:
            db = next(get_db())
            key_service = self._get_api_key_service(db)
            return await key_service.validate_api_key(api_key)
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return None

    async def _estimate_request_cost(self, request: Request) -> Decimal:
        """
        Estimate the cost of the current request

        This is a simplified estimation. In production, you would:
        1. Analyze the request content and model parameters
        2. Use actual pricing from AI service providers
        3. Consider token count, model type, etc.
        """
        try:
            # For chat completions, estimate based on path and content
            if "/chat" in request.url.path:
                # Base cost estimation for chat requests
                # In production, this would analyze the actual prompt and model
                return Decimal("0.001")  # $0.001 per request as baseline

            # For other API calls, minimal cost
            return Decimal("0.0001")

        except Exception as e:
            logger.error(f"Error estimating request cost: {e}")
            return Decimal("0")

    async def _check_budget_limits(self, organization_id: str, estimated_cost: Decimal):
        """Check if the organization has sufficient budget"""
        try:
            db = next(get_db())
            budget_service = self._get_budget_service(db)

            # Check budget limit
            if self.enable_hard_limits:
                await budget_service.check_budget_limit(organization_id, estimated_cost)

        except BudgetExceededException:
            raise
        except Exception as e:
            logger.error(f"Error checking budget limits: {e}")
            # On error, allow request to proceed

    async def _record_usage(self, request: Request, actual_cost: Decimal):
        """Record actual usage after successful request completion"""
        try:
            db = next(get_db())
            budget_service = self._get_budget_service(db)

            # Get request context
            organization_id = getattr(request.state, 'organization_id', None)
            api_key_id = getattr(request.state, 'api_key_id', None)
            user_id = getattr(request.state, 'user_id', 'system')  # Default to system user

            if not organization_id or not api_key_id:
                return

            # Determine service and model from request
            service, model = self._extract_service_info(request)

            # Record usage
            await budget_service.record_usage(
                organization_id=organization_id,
                user_id=user_id,
                team_id=None,  # Can be extracted from request if needed
                service=service,
                model=model,
                tokens=0,  # Would be calculated from actual response
                cost=actual_cost
            )

        except Exception as e:
            logger.error(f"Error recording usage: {e}")
            # Don't fail the request if usage recording fails

    def _extract_service_info(self, request: Request) -> tuple[str, str]:
        """Extract service and model information from request"""
        # Default values - in production, extract from request body/params
        service = "openrouter"  # Default service
        model = "unknown"  # Default model

        # Try to extract from query parameters or path
        if "model" in request.query_params:
            model = request.query_params["model"]

        # Extract from path for chat endpoints
        if "/chat/" in request.url.path:
            path_parts = request.url.path.split('/')
            if len(path_parts) > 3:
                model = path_parts[3]

        return service, model

    def _get_budget_service(self, db: Session) -> BudgetService:
        """Get cached budget service instance"""
        # Simple caching - in production, use more sophisticated caching
        return BudgetService(db)

    def _get_api_key_service(self, db: Session) -> OrgApiKeyService:
        """Get cached API key service instance"""
        # Simple caching - in production, use more sophisticated caching
        return OrgApiKeyService(db)


class BudgetAlertingService:
    """Service for handling budget alerts and notifications"""

    def __init__(self, budget_service: BudgetService):
        self.budget_service = budget_service

    async def check_and_send_alerts(self, organization_id: Optional[str] = None):
        """Check budget status and send alerts if needed"""
        try:
            alerts = await self.budget_service.get_budget_alerts(organization_id)

            for alert in alerts:
                await self._send_alert(alert)

            return len(alerts)

        except Exception as e:
            logger.error(f"Error checking and sending alerts: {e}")
            return 0

    async def _send_alert(self, alert):
        """Send budget alert notification"""
        # In production, this would integrate with email, Slack, etc.
        logger.warning(
            f"Budget Alert for {alert.organization_name}: "
            f"Usage: {alert.usage_percentage:.1f}%, "
            f"Limit: ${alert.monthly_limit:.2f}, "
            f"Spent: ${alert.current_spend:.2f}"
        )

        # For now, just log the alert
        # In production, you would:
        # 1. Send email to organization admins
        # 2. Send Slack notification
        # 3. Create in-app notification
        # 4. Store alert in database


# Utility functions for budget control
def create_budget_control_middleware(enable_hard_limits: bool = True) -> BudgetControlMiddleware:
    """
    Create budget control middleware

    Args:
        enable_hard_limits: Whether to enforce hard budget limits

    Returns:
        BudgetControlMiddleware instance
    """
    return BudgetControlMiddleware(enable_hard_limits=enable_hard_limits)


async def check_request_budget(request: Request, estimated_cost: Decimal) -> bool:
    """
    Check if a request is within budget limits

    Args:
        request: FastAPI request object
        estimated_cost: Estimated cost of the request

    Returns:
        True if within budget limits
    """
    try:
        organization_id = getattr(request.state, 'organization_id', None)
        if not organization_id:
            return True

        db = next(get_db())
        budget_service = BudgetService(db)
        return await budget_service.check_budget_limit(organization_id, estimated_cost)

    except Exception as e:
        logger.error(f"Error checking request budget: {e}")
        return True  # Allow on error


def get_budget_alert_thresholds() -> Dict[str, float]:
    """Get budget alert thresholds configuration"""
    return {
        "warning": 70.0,    # 70% usage
        "critical": 90.0,   # 90% usage
        "emergency": 100.0  # 100% usage
    }


def should_enable_budget_control(request: Request) -> bool:
    """
    Determine if budget control should be enabled for this request

    Args:
        request: FastAPI request object

    Returns:
        True if budget control should be enabled
    """
    # Enable for all authenticated API requests
    return hasattr(request.state, 'organization_id')


# Middleware configuration
class BudgetControlConfig:
    """Configuration for budget control middleware"""

    def __init__(self):
        self.enable_hard_limits = True
        self.enable_usage_tracking = True
        self.enable_alerts = True
        self.alert_thresholds = get_budget_alert_thresholds()
        self.cost_estimation_model = "simple"  # simple, advanced, ml_based

    @classmethod
    def from_environment(cls) -> 'BudgetControlConfig':
        """Create configuration from environment variables"""
        import os
        config = cls()

        config.enable_hard_limits = os.getenv("BUDGET_HARD_LIMITS", "true").lower() == "true"
        config.enable_usage_tracking = os.getenv("BUDGET_TRACKING", "true").lower() == "true"
        config.enable_alerts = os.getenv("BUDGET_ALERTS", "true").lower() == "true"

        return config