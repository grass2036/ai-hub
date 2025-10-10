"""
Custom exceptions for AI Hub Platform
自定义异常类
"""

from typing import Optional, Any, Dict
from fastapi import HTTPException


class BaseHubException(Exception):
    """Base exception for AI Hub Platform"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class MultiTenantError(BaseHubException):
    """Multi-tenant related errors"""
    pass


class OrganizationNotFoundError(MultiTenantError):
    """Organization not found error"""

    def __init__(self, organization_id: str):
        super().__init__(
            message=f"Organization with ID {organization_id} not found",
            error_code="ORG_NOT_FOUND",
            details={"organization_id": organization_id}
        )


class TeamNotFoundError(MultiTenantError):
    """Team not found error"""

    def __init__(self, team_id: str):
        super().__init__(
            message=f"Team with ID {team_id} not found",
            error_code="TEAM_NOT_FOUND",
            details={"team_id": team_id}
        )


class UserNotFoundError(MultiTenantError):
    """User not found error"""

    def __init__(self, user_id: str):
        super().__init__(
            message=f"User with ID {user_id} not found",
            error_code="USER_NOT_FOUND",
            details={"user_id": user_id}
        )


class PermissionDeniedError(MultiTenantError):
    """Permission denied error"""

    def __init__(self, user_id: str, resource: str, action: str):
        super().__init__(
            message=f"User {user_id} does not have permission to {action} {resource}",
            error_code="PERMISSION_DENIED",
            details={
                "user_id": user_id,
                "resource": resource,
                "action": action
            }
        )


class InsufficientRoleError(MultiTenantError):
    """Insufficient role error"""

    def __init__(self, current_role: str, required_role: str):
        super().__init__(
            message=f"Current role '{current_role}' is insufficient. Required role: '{required_role}'",
            error_code="INSUFFICIENT_ROLE",
            details={
                "current_role": current_role,
                "required_role": required_role
            }
        )


class DataIsolationError(MultiTenantError):
    """Data isolation error"""

    def __init__(self, message: str, user_id: str, organization_id: str):
        super().__init__(
            message=f"Data isolation violation: {message}",
            error_code="DATA_ISOLATION_VIOLATION",
            details={
                "user_id": user_id,
                "organization_id": organization_id
            }
        )


class BudgetError(BaseHubException):
    """Budget related errors"""
    pass


class BudgetExceededError(BudgetError):
    """Budget exceeded error"""

    def __init__(self, organization_id: str, budget_limit: float, current_spend: float):
        super().__init__(
            message=f"Budget exceeded for organization {organization_id}. Limit: ${budget_limit}, Current: ${current_spend}",
            error_code="BUDGET_EXCEEDED",
            details={
                "organization_id": organization_id,
                "budget_limit": budget_limit,
                "current_spend": current_spend
            }
        )


class BudgetNotFoundError(BudgetError):
    """Budget not found error"""

    def __init__(self, organization_id: str):
        super().__init__(
            message=f"Budget not found for organization {organization_id}",
            error_code="BUDGET_NOT_FOUND",
            details={"organization_id": organization_id}
        )


class ApiKeyError(BaseHubException):
    """API Key related errors"""
    pass


class ApiKeyNotFoundError(ApiKeyError):
    """API Key not found error"""

    def __init__(self, key_id: str):
        super().__init__(
            message=f"API Key with ID {key_id} not found",
            error_code="API_KEY_NOT_FOUND",
            details={"key_id": key_id}
        )


class ApiKeyExpiredError(ApiKeyError):
    """API Key expired error"""

    def __init__(self, key_id: str):
        super().__init__(
            message=f"API Key with ID {key_id} has expired",
            error_code="API_KEY_EXPIRED",
            details={"key_id": key_id}
        )


class ApiKeyRevokedError(ApiKeyError):
    """API Key revoked error"""

    def __init__(self, key_id: str):
        super().__init__(
            message=f"API Key with ID {key_id} has been revoked",
            error_code="API_KEY_REVOKED",
            details={"key_id": key_id}
        )


class QuotaExceededError(ApiKeyError):
    """Quota exceeded error"""

    def __init__(self, key_id: str, current_usage: int, monthly_quota: int):
        super().__init__(
            message=f"API Key quota exceeded. Current usage: {current_usage}, Monthly quota: {monthly_quota}",
            error_code="QUOTA_EXCEEDED",
            details={
                "key_id": key_id,
                "current_usage": current_usage,
                "monthly_quota": monthly_quota
            }
        )


class RateLimitExceededError(ApiKeyError):
    """Rate limit exceeded error"""

    def __init__(self, key_id: str, rate_limit: int):
        super().__init__(
            message=f"API Key rate limit exceeded. Limit: {rate_limit} requests per minute",
            error_code="RATE_LIMIT_EXCEEDED",
            details={
                "key_id": key_id,
                "rate_limit": rate_limit
            }
        )


class ValidationError(BaseHubException):
    """Validation error"""

    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Validation failed for field '{field}': {message}",
            error_code="VALIDATION_ERROR",
            details={"field": field, "error": message}
        )


class ConfigurationError(BaseHubException):
    """Configuration error"""

    def __init__(self, message: str, setting: Optional[str] = None):
        details = {"setting": setting} if setting else {}
        super().__init__(
            message=f"Configuration error: {message}",
            error_code="CONFIG_ERROR",
            details=details
        )


class DatabaseError(BaseHubException):
    """Database error"""

    def __init__(self, message: str, operation: Optional[str] = None):
        details = {"operation": operation} if operation else {}
        super().__init__(
            message=f"Database error during {operation}: {message}" if operation else f"Database error: {message}",
            error_code="DATABASE_ERROR",
            details=details
        )


class ExternalServiceError(BaseHubException):
    """External service error"""

    def __init__(self, service: str, message: str, status_code: Optional[int] = None):
        details = {
            "service": service,
            "status_code": status_code
        }
        super().__init__(
            message=f"External service '{service}' error: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details
        )


# HTTP Exception helpers
def create_http_exception(
    status_code: int,
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Create HTTPException with standard format"""

    content = {
        "error": {
            "message": message,
            "error_code": error_code or "UNKNOWN_ERROR",
            "details": details or {}
        }
    }

    return HTTPException(status_code=status_code, detail=content)


# Exception handlers for FastAPI
def create_exception_handlers():
    """Create exception handlers for FastAPI app"""

    from fastapi import Request
    from fastapi.responses import JSONResponse

    async def hub_exception_handler(request: Request, exc: BaseHubException):
        """Handle BaseHubException and its subclasses"""
        status_code = 400

        # Map specific error types to HTTP status codes
        if isinstance(exc, (OrganizationNotFoundError, TeamNotFoundError, UserNotFoundError, ApiKeyNotFoundError)):
            status_code = 404
        elif isinstance(exc, (PermissionDeniedError, InsufficientRoleError, DataIsolationError)):
            status_code = 403
        elif isinstance(exc, (BudgetExceededError, QuotaExceededError, RateLimitExceededError)):
            status_code = 429
        elif isinstance(exc, ValidationError):
            status_code = 422
        elif isinstance(exc, ConfigurationError):
            status_code = 500
        elif isinstance(exc, (DatabaseError, ExternalServiceError)):
            status_code = 502

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "message": exc.message,
                    "error_code": exc.error_code or "UNKNOWN_ERROR",
                    "details": exc.details
                }
            }
        )

    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions"""
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Internal server error",
                    "error_code": "INTERNAL_ERROR",
                    "details": {"type": type(exc).__name__}
                }
            }
        )

    return {
        BaseHubException: hub_exception_handler,
        Exception: general_exception_handler
    }


# Utility functions
def handle_database_error(operation: str, original_error: Exception) -> DatabaseError:
    """Convert database errors to DatabaseError"""
    error_message = str(original_error)

    # Add specific handling for common database errors
    if "unique constraint" in error_message.lower():
        error_message = "Duplicate entry found"
    elif "foreign key constraint" in error_message.lower():
        error_message = "Referenced record not found"
    elif "connection" in error_message.lower():
        error_message = "Database connection error"

    return DatabaseError(
        message=error_message,
        operation=operation
    )


def handle_validation_error(field: str, value: Any, constraint: str) -> ValidationError:
    """Create validation error with standard format"""
    return ValidationError(
        field=field,
        message=f"Value '{value}' violates constraint: {constraint}"
    )