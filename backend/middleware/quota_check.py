"""
配额检查中间件
"""
from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.api_key_manager import APIKeyManager
from backend.core.quota_manager import quota_manager


async def check_api_key_and_quota(request: Request) -> dict:
    """
    检查API密钥和配额

    Returns:
        包含user_id和api_key的字典
    """
    # 获取API密钥
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key"
        )

    api_key_string = auth_header.replace("Bearer ", "")

    # 验证API密钥
    db: AsyncSession = request.state.db
    result = await APIKeyManager.validate_api_key(db, api_key_string)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key"
        )
    
    api_key, user = result

    # 检查速率限制
    if not await quota_manager.check_rate_limit(api_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {api_key.rate_limit} requests per minute."
        )

    # 检查配额
    has_quota, used, total = await quota_manager.check_quota(db, user.id)

    if not has_quota:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Quota exceeded. Used {used}/{total} requests this month."
        )

    return {
        "user_id": user.id,
        "api_key": api_key
    }