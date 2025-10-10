"""
Organization API Key Service

This service handles enterprise-level API key management,
including generation, permissions, usage tracking, and lifecycle management.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, desc

from backend.models.org_api_key import (
    OrgApiKey, OrgApiKeyCreate, OrgApiKeyUpdate, OrgApiKeyWithStats,
    ApiKeyGenerationResponse, ApiKeyStatus, generate_api_key,
    verify_api_key, generate_default_expiration, calculate_quota_usage_percentage,
    should_send_quota_alert
)
from backend.models.organization import Organization
from backend.models.user import User
from backend.models.usage_record import UsageRecord
from backend.core.database import get_db

logger = logging.getLogger(__name__)


class ApiKeyQuotaExceededException(Exception):
    """Exception raised when API key quota is exceeded"""
    pass


class ApiKeyExpiredException(Exception):
    """Exception raised when API key is expired"""
    pass


class OrgApiKeyService:
    """Service for organization API key management"""

    def __init__(self, db: Session):
        self.db = db

    async def create_api_key(self, key_data: OrgApiKeyCreate, created_by: str) -> ApiKeyGenerationResponse:
        """
        Create a new API key for an organization

        Args:
            key_data: API key creation data
            created_by: User ID creating the key

        Returns:
            Generated API key and details (key only shown once)

        Raises:
            ValueError: If organization doesn't exist or validation fails
        """
        try:
            # Check if organization exists
            organization = self.db.execute(
                select(Organization)
                .where(Organization.id == key_data.organization_id)
            ).scalar_one_or_none()

            if not organization:
                raise ValueError(f"Organization {key_data.organization_id} not found")

            # Validate permissions format
            if not isinstance(key_data.permissions, dict):
                raise ValueError("Permissions must be a dictionary")

            # Generate API key
            api_key, key_hash, key_prefix = generate_api_key()

            # Set default expiration if not provided
            expires_at = None
            if key_data.expires_at:
                expires_at = datetime.fromisoformat(key_data.expires_at.replace('Z', '+00:00'))
            else:
                expires_at = generate_default_expiration(365)  # 1 year default

            # Create API key record
            org_api_key = OrgApiKey(
                organization_id=key_data.organization_id,
                name=key_data.name,
                key_hash=key_hash,
                key_prefix=key_prefix,
                permissions=str(key_data.permissions),  # Store as JSON string
                rate_limit=key_data.rate_limit,
                monthly_quota=key_data.monthly_quota,
                status=ApiKeyStatus.ACTIVE.value,
                created_by=created_by,
                expires_at=expires_at
            )

            self.db.add(org_api_key)
            self.db.commit()
            self.db.refresh(org_api_key)

            # Build response
            key_response = OrgApiKeyWithStats(
                id=str(org_api_key.id),
                organization_id=str(org_api_key.organization_id),
                name=org_api_key.name,
                permissions=key_data.permissions,
                rate_limit=org_api_key.rate_limit,
                monthly_quota=org_api_key.monthly_quota,
                expires_at=org_api_key.expires_at.isoformat() if org_api_key.expires_at else None,
                key_prefix=org_api_key.key_prefix,
                status=ApiKeyStatus(org_api_key.status),
                last_used_at=org_api_key.last_used_at.isoformat() if org_api_key.last_used_at else None,
                created_by=str(org_api_key.created_by) if org_api_key.created_by else None,
                created_at=org_api_key.created_at.isoformat() if org_api_key.created_at else "",
                current_month_usage=0,
                daily_average_usage=0.0,
                quota_usage_percentage=0.0,
                is_active=org_api_key.is_active,
                is_expired=org_api_key.is_expired,
                days_until_expiry=self._calculate_days_until_expiry(org_api_key.expires_at)
            )

            logger.info(f"Created API key {key_prefix} for organization {key_data.organization_id}")

            return ApiKeyGenerationResponse(
                api_key=api_key,  # Only shown once
                key_details=key_response
            )

        except ValueError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating API key: {e}")
            raise

    async def get_api_key_by_id(self, key_id: str) -> Optional[OrgApiKey]:
        """
        Get API key by ID

        Args:
            key_id: API key ID

        Returns:
            API key or None if not found
        """
        try:
            api_key = self.db.execute(
                select(OrgApiKey)
                .where(OrgApiKey.id == key_id)
            ).scalar_one_or_none()

            return api_key

        except Exception as e:
            logger.error(f"Error getting API key {key_id}: {e}")
            return None

    async def get_api_keys_by_organization(self, organization_id: str, include_stats: bool = True) -> List[OrgApiKeyWithStats]:
        """
        Get all API keys for an organization

        Args:
            organization_id: Organization ID
            include_stats: Whether to include usage statistics

        Returns:
            List of API keys with optional statistics
        """
        try:
            api_keys = self.db.execute(
                select(OrgApiKey)
                .where(OrgApiKey.organization_id == organization_id)
                .order_by(desc(OrgApiKey.created_at))
            ).scalars().all()

            result = []
            for api_key in api_keys:
                # Parse permissions from JSON string
                permissions = {}
                try:
                    import json
                    permissions = json.loads(api_key.permissions) if api_key.permissions else {}
                except:
                    permissions = {}

                key_with_stats = OrgApiKeyWithStats(
                    id=str(api_key.id),
                    organization_id=str(api_key.organization_id),
                    name=api_key.name,
                    permissions=permissions,
                    rate_limit=api_key.rate_limit,
                    monthly_quota=api_key.monthly_quota,
                    expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
                    key_prefix=api_key.key_prefix,
                    status=ApiKeyStatus(api_key.status),
                    last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
                    created_by=str(api_key.created_by) if api_key.created_by else None,
                    created_at=api_key.created_at.isoformat() if api_key.created_at else "",
                    current_month_usage=0,
                    daily_average_usage=0.0,
                    quota_usage_percentage=0.0,
                    is_active=api_key.is_active,
                    is_expired=api_key.is_expired,
                    days_until_expiry=self._calculate_days_until_expiry(api_key.expires_at)
                )

                if include_stats:
                    # Add usage statistics
                    stats = await self._get_api_key_stats(str(api_key.id))
                    key_with_stats.current_month_usage = stats['current_month_usage']
                    key_with_stats.daily_average_usage = stats['daily_average_usage']
                    key_with_stats.quota_usage_percentage = stats['quota_usage_percentage']

                result.append(key_with_stats)

            return result

        except Exception as e:
            logger.error(f"Error getting API keys for organization {organization_id}: {e}")
            return []

    async def update_api_key(self, key_id: str, key_data: OrgApiKeyUpdate) -> Optional[OrgApiKey]:
        """
        Update API key settings

        Args:
            key_id: API key ID
            key_data: Update data

        Returns:
            Updated API key or None if not found
        """
        try:
            api_key = self.db.execute(
                select(OrgApiKey)
                .where(OrgApiKey.id == key_id)
            ).scalar_one_or_none()

            if not api_key:
                return None

            # Update fields
            update_data = key_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(api_key, field):
                    if field == 'permissions' and isinstance(value, dict):
                        # Store permissions as JSON string
                        import json
                        setattr(api_key, field, json.dumps(value))
                    elif field == 'status' and isinstance(value, str):
                        setattr(api_key, field, ApiKeyStatus(value).value)
                    elif field == 'expires_at' and isinstance(value, str):
                        setattr(api_key, field, datetime.fromisoformat(value.replace('Z', '+00:00')))
                    else:
                        setattr(api_key, field, value)

            self.db.commit()
            self.db.refresh(api_key)

            logger.info(f"Updated API key {api_key.key_prefix}")
            return api_key

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating API key: {e}")
            return None

    async def revoke_api_key(self, key_id: str) -> bool:
        """
        Revoke an API key

        Args:
            key_id: API key ID

        Returns:
            True if revoked, False if not found
        """
        try:
            api_key = self.db.execute(
                select(OrgApiKey)
                .where(OrgApiKey.id == key_id)
            ).scalar_one_or_none()

            if not api_key:
                return False

            api_key.status = ApiKeyStatus.REVOKED.value
            self.db.commit()

            logger.info(f"Revoked API key {api_key.key_prefix}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error revoking API key: {e}")
            return False

    async def validate_api_key(self, api_key: str) -> Optional[OrgApiKey]:
        """
        Validate an API key and return the key record

        Args:
            api_key: The API key to validate

        Returns:
            API key record if valid, None otherwise

        Raises:
            ApiKeyExpiredException: If key is expired
            ApiKeyQuotaExceededException: If quota exceeded
        """
        try:
            # Find API key by hash
            import hashlib
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()

            key_record = self.db.execute(
                select(OrgApiKey)
                .where(and_(
                    OrgApiKey.key_hash == key_hash,
                    OrgApiKey.status == ApiKeyStatus.ACTIVE.value
                ))
            ).scalar_one_or_none()

            if not key_record:
                return None

            # Check if expired
            if key_record.is_expired:
                raise ApiKeyExpiredException(f"API key {key_record.key_prefix} has expired")

            # Check quota
            await self._check_quota_limit(key_record)

            # Update last used timestamp
            key_record.last_used_at = datetime.utcnow()
            self.db.commit()

            return key_record

        except (ApiKeyExpiredException, ApiKeyQuotaExceededException):
            raise
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return None

    async def record_api_usage(self, api_key_id: str, organization_id: str, user_id: str,
                              team_id: Optional[str], service: str, model: str,
                              tokens: int, cost: Decimal) -> bool:
        """
        Record API usage for an API key

        Args:
            api_key_id: API key ID
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
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error recording API usage: {e}")
            return False

    async def get_api_key_usage_history(self, key_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get usage history for an API key

        Args:
            key_id: API key ID
            days: Number of days to look back

        Returns:
            List of daily usage records
        """
        try:
            # Get API key to find organization
            api_key = await self.get_api_key_by_id(key_id)
            if not api_key:
                return []

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
                        UsageRecord.organization_id == api_key.organization_id,
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
            logger.error(f"Error getting API key usage history: {e}")
            return []

    # Private helper methods

    async def _get_api_key_stats(self, key_id: str) -> Dict[str, Any]:
        """Get usage statistics for an API key"""
        try:
            # Get API key to find organization
            api_key = await self.get_api_key_by_id(key_id)
            if not api_key:
                return {
                    'current_month_usage': 0,
                    'daily_average_usage': 0.0,
                    'quota_usage_percentage': 0.0
                }

            # Calculate current month usage
            current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            monthly_requests = self.db.execute(
                select(func.count(UsageRecord.id))
                .where(
                    and_(
                        UsageRecord.organization_id == api_key.organization_id,
                        UsageRecord.timestamp >= current_month_start
                    )
                )
            ).scalar() or 0

            # Calculate daily average
            days_passed = (datetime.utcnow() - current_month_start).days + 1
            daily_average = monthly_requests / max(days_passed, 1)

            # Calculate quota usage percentage
            quota_usage_percentage = calculate_quota_usage_percentage(
                monthly_requests, api_key.monthly_quota
            )

            return {
                'current_month_usage': monthly_requests,
                'daily_average_usage': daily_average,
                'quota_usage_percentage': quota_usage_percentage
            }

        except Exception as e:
            logger.error(f"Error getting API key stats: {e}")
            return {
                'current_month_usage': 0,
                'daily_average_usage': 0.0,
                'quota_usage_percentage': 0.0
            }

    async def _check_quota_limit(self, api_key: OrgApiKey) -> bool:
        """
        Check if API key is within quota limits

        Args:
            api_key: API key record

        Returns:
            True if within limits

        Raises:
            ApiKeyQuotaExceededException: If quota exceeded
        """
        try:
            # Get current month usage
            current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            monthly_requests = self.db.execute(
                select(func.count(UsageRecord.id))
                .where(
                    and_(
                        UsageRecord.organization_id == api_key.organization_id,
                        UsageRecord.timestamp >= current_month_start
                    )
                )
            ).scalar() or 0

            # Check if quota exceeded
            if monthly_requests >= api_key.monthly_quota:
                raise ApiKeyQuotaExceededException(
                    f"API key {api_key.key_prefix} has exceeded monthly quota of {api_key.monthly_quota} requests"
                )

            return True

        except ApiKeyQuotaExceededException:
            raise
        except Exception as e:
            logger.error(f"Error checking quota limit: {e}")
            return True  # Allow on error

    def _calculate_days_until_expiry(self, expires_at: Optional[datetime]) -> Optional[int]:
        """Calculate days until API key expires"""
        if not expires_at:
            return None

        delta = expires_at - datetime.utcnow()
        return max(0, delta.days)


# Utility functions for working with organization API keys
def get_org_api_key_service(db: Session = None) -> OrgApiKeyService:
    """Get organization API key service instance"""
    if db is None:
        db = next(get_db())
    return OrgApiKeyService(db)


async def validate_organization_api_key(api_key: str) -> Optional[OrgApiKey]:
    """
    Validate an organization API key

    Args:
        api_key: The API key to validate

    Returns:
        API key record if valid
    """
    db = next(get_db())
    key_service = OrgApiKeyService(db)
    return await key_service.validate_api_key(api_key)