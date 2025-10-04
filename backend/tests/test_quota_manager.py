"""
QuotaManager Tests
"""
import pytest
import pytest_asyncio
import fakeredis.aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.quota_manager import QuotaManager
from backend.models.user import User, UserPlan
from backend.models.api_key import APIKey


@pytest_asyncio.fixture
async def quota_manager():
    """Fixture to provide an initialized QuotaManager with a fake Redis client."""
    manager = QuotaManager()
    # Use fakeredis for testing without a real Redis server
    manager.redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield manager
    await manager.close()


@pytest_asyncio.fixture
async def test_user(db: AsyncSession):
    """Fixture for creating a test user with a specific quota."""
    user = User(
        email="quota_user@example.com",
        username="quota_user",
        hashed_password="hashed_password",
        plan=UserPlan.FREE,
        monthly_quota=100,
        quota_used=50
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_api_key(db: AsyncSession, test_user: User):
    """Fixture for creating a test API key."""
    key = APIKey(
        key="test_key_123",
        user_id=test_user.id,
        name="Test Key",
        is_active=True
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key


@pytest.mark.asyncio
async def test_check_quota_no_cache(quota_manager: QuotaManager, db: AsyncSession, test_user: User):
    """Test checking quota when it's not in Redis cache (should fall back to DB)."""
    # Initialize Redis client if not already done
    if quota_manager.redis_client is None:
        quota_manager.redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    
    has_quota, used, total = await quota_manager.check_quota(db, test_user.id)

    assert has_quota is True
    assert used == 50
    assert total == 100

    # Verify that the value was cached in Redis after the first check
    cached_used = await quota_manager.redis_client.get(f"quota:user:{test_user.id}")
    assert int(cached_used) == 50


@pytest.mark.asyncio
async def test_check_quota_with_cache(quota_manager: QuotaManager, db: AsyncSession, test_user: User):
    """Test checking quota when the value is already in Redis cache."""
    # Initialize Redis client if not already done
    if quota_manager.redis_client is None:
        quota_manager.redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    
    quota_key = f"quota:user:{test_user.id}"
    await quota_manager.redis_client.set(quota_key, 70)

    has_quota, used, total = await quota_manager.check_quota(db, test_user.id)

    assert has_quota is True
    assert used == 70  # Should use the cached value
    assert total == 100 # Total is still from DB


@pytest.mark.asyncio
async def test_check_quota_exceeded(quota_manager: QuotaManager, db: AsyncSession, test_user: User):
    """Test checking quota when the used amount exceeds the total."""
    # Initialize Redis client if not already done
    if quota_manager.redis_client is None:
        quota_manager.redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    
    quota_key = f"quota:user:{test_user.id}"
    await quota_manager.redis_client.set(quota_key, 101)

    has_quota, used, total = await quota_manager.check_quota(db, test_user.id)

    assert has_quota is False
    assert used == 101
    assert total == 100


@pytest.mark.asyncio
async def test_consume_quota_success(quota_manager: QuotaManager, db: AsyncSession, test_user: User):
    """Test successfully consuming quota."""
    # Initialize Redis client if not already done
    if quota_manager.redis_client is None:
        quota_manager.redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    
    quota_key = f"quota:user:{test_user.id}"
    await quota_manager.redis_client.set(quota_key, 99)

    success = await quota_manager.consume_quota(db, test_user.id, amount=1)
    assert success is True

    # Verify the Redis cache was incremented
    new_used = await quota_manager.redis_client.get(quota_key)
    assert int(new_used) == 100


@pytest.mark.asyncio
async def test_consume_quota_failure(quota_manager: QuotaManager, db: AsyncSession, test_user: User):
    """Test failing to consume quota when it's already exceeded."""
    # Initialize Redis client if not already done
    if quota_manager.redis_client is None:
        quota_manager.redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    
    quota_key = f"quota:user:{test_user.id}"
    await quota_manager.redis_client.set(quota_key, 100)

    success = await quota_manager.consume_quota(db, test_user.id, amount=1)
    assert success is False

    # Verify the Redis cache was not incremented further
    new_used = await quota_manager.redis_client.get(quota_key)
    assert int(new_used) == 100


@pytest.mark.asyncio
async def test_check_rate_limit_within_limit(quota_manager: QuotaManager, test_api_key: APIKey):
    """Test rate limit check when requests are within the defined limit."""
    # Initialize Redis client if not already done
    if quota_manager.redis_client is None:
        quota_manager.redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    
    # Set a rate limit for the test
    test_api_key.rate_limit = 5
    
    for i in range(test_api_key.rate_limit):
        is_allowed = await quota_manager.check_rate_limit(test_api_key)
        assert is_allowed is True


@pytest.mark.asyncio
async def test_check_rate_limit_exceeded(quota_manager: QuotaManager, test_api_key: APIKey):
    """Test rate limit check when requests exceed the defined limit."""
    # Initialize Redis client if not already done
    if quota_manager.redis_client is None:
        quota_manager.redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    
    # Set a rate limit for the test
    test_api_key.rate_limit = 3
    
    # Use up the limit
    rate_key = f"rate_limit:key:{test_api_key.id}"
    await quota_manager.redis_client.set(rate_key, test_api_key.rate_limit)
    
    # Next request should be denied
    is_allowed = await quota_manager.check_rate_limit(test_api_key)
    assert is_allowed is False


@pytest.mark.asyncio
async def test_reset_monthly_quota(quota_manager: QuotaManager, db: AsyncSession, test_user: User):
    """Test resetting a user's monthly quota."""
    # Initialize Redis client if not already done
    if quota_manager.redis_client is None:
        quota_manager.redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    
    quota_key = f"quota:user:{test_user.id}"
    await quota_manager.redis_client.set(quota_key, 88)

    await quota_manager.reset_monthly_quota(db, test_user.id)

    # Verify the user's quota_used is reset in the database
    await db.refresh(test_user)
    assert test_user.quota_used == 0

    # Verify the Redis cache for that user is deleted
    cached_value = await quota_manager.redis_client.get(quota_key)
    assert cached_value is None