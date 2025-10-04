"""
API Key Management Endpoints
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.api_key_manager import APIKeyManager
from backend.core.quota_manager import quota_manager
from backend.models.user import User
from backend.schemas.api_key import (
    APIKeyCreateRequest,
    APIKeyResponse,
    APIKeyListItem,
    QuotaResponse
)
from backend.api.v1.auth.auth import get_current_active_user

router = APIRouter(prefix="/developer", tags=["Developer"])


@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: APIKeyCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新的API密钥

    - **name**: 密钥名称（必填）
    - **description**: 密钥描述（可选）
    - **expires_days**: 过期天数（可选，1-365天）
    """
    # Check if user has reached API key limit (e.g., 10 keys per user)
    existing_keys = await APIKeyManager.get_user_api_keys(db, current_user.id)
    if len(existing_keys) >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of API keys reached (10)"
        )

    # Create API key
    api_key = await APIKeyManager.create_api_key(
        db=db,
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        expires_days=request.expires_days
    )

    return api_key


@router.get("/api-keys", response_model=List[APIKeyListItem])
async def list_api_keys(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的所有API密钥

    - **include_inactive**: 是否包含已停用的密钥
    """
    api_keys = await APIKeyManager.get_user_api_keys(
        db=db,
        user_id=current_user.id,
        include_inactive=include_inactive
    )

    # Convert to list items with masked keys
    return [
        APIKeyListItem(
            id=key.id,
            name=key.name,
            description=key.description,
            key_preview=f"{key.key[:12]}****{key.key[-4:]}" if len(key.key) > 16 else "****",
            is_active=key.is_active,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at
        )
        for key in api_keys
    ]


@router.get("/api-keys/{api_key_id}", response_model=APIKeyListItem)
async def get_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取指定API密钥详情"""
    api_key = await APIKeyManager.get_api_key_by_id(
        db=db,
        api_key_id=api_key_id,
        user_id=current_user.id
    )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    return APIKeyListItem(
        id=api_key.id,
        name=api_key.name,
        description=api_key.description,
        key_preview=f"{api_key.key[:12]}****{api_key.key[-4:]}",
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at
    )


@router.delete("/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """删除API密钥"""
    success = await APIKeyManager.delete_api_key(
        db=db,
        api_key_id=api_key_id,
        user_id=current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    return None


@router.post("/api-keys/{api_key_id}/revoke", status_code=status.HTTP_200_OK)
async def revoke_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """撤销API密钥（停用但不删除）"""
    success = await APIKeyManager.revoke_api_key(
        db=db,
        api_key_id=api_key_id,
        user_id=current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    return {"message": "API key revoked successfully"}


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的配额信息

    包括：
    - 配额限制（每日/每月请求数和token数）
    - 当前使用量
    - 重置时间
    """
    await quota_manager.initialize()
    quota_info = await quota_manager.get_quota_limits(db, current_user.id)
    return QuotaResponse(**quota_info)
