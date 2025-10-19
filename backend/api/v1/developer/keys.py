"""
Developer API Key Management API
Week 4 Day 23: API Key Management and Permission System
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from backend.database import get_db
from backend.services.developer_api_service import DeveloperAPIService
from backend.core.developer_auth import get_current_developer
from backend.models.developer import Developer

# 创建路由器
router = APIRouter()

# 请求/响应模型
class CreateAPIKeyRequest(BaseModel):
    """创建API密钥请求"""
    name: str = Field(..., min_length=1, max_length=100, description="API密钥名称")
    permissions: Optional[List[str]] = Field(default=None, description="权限列表")
    rate_limit: Optional[int] = Field(default=None, ge=1, le=10000, description="速率限制（请求/分钟）")
    allowed_models: Optional[List[str]] = Field(default=None, description="允许使用的模型列表")
    expires_days: Optional[int] = Field(default=None, ge=1, le=365, description="过期天数")


class UpdateAPIKeyRequest(BaseModel):
    """更新API密钥请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="API密钥名称")
    permissions: Optional[List[str]] = Field(None, description="权限列表")
    rate_limit: Optional[int] = Field(None, ge=1, le=10000, description="速率限制（请求/分钟）")
    allowed_models: Optional[List[str]] = Field(None, description="允许使用的模型列表")
    is_active: Optional[bool] = Field(None, description="是否激活")


class APIKeyResponse(BaseModel):
    """API密钥响应"""
    id: str
    name: str
    key_prefix: str
    permissions: List[str]
    rate_limit: int
    allowed_models: List[str]
    is_active: bool
    expires_at: Optional[str]
    last_used_at: Optional[str]
    usage_count: int
    total_tokens_used: int
    created_at: str
    updated_at: str


class APIKeyWithSecretResponse(BaseModel):
    """包含密钥的API密钥响应（仅在创建时返回）"""
    id: str
    name: str
    api_key: str  # 完整的API密钥，仅在创建时返回一次
    key_prefix: str
    permissions: List[str]
    rate_limit: int
    allowed_models: List[str]
    is_active: bool
    expires_at: Optional[str]
    created_at: str


class APIKeysListResponse(BaseModel):
    """API密钥列表响应"""
    api_keys: List[APIKeyResponse]
    pagination: dict


class APIKeyUsageStatsResponse(BaseModel):
    """API密钥使用统计响应"""
    period_days: int
    total_requests: int
    total_tokens: int
    total_cost: float
    avg_response_time: float
    success_rate: float
    model_usage: dict
    daily_usage: dict


class DeveloperQuotaResponse(BaseModel):
    """开发者配额响应"""
    monthly_quota: int
    monthly_used: int
    monthly_remaining: int
    monthly_usage_percent: float
    monthly_cost: float
    active_api_keys: int
    max_api_keys: int
    reset_date: str


@router.post("/keys", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateAPIKeyRequest,
    developer: Developer = Depends(get_current_developer),
    api_service: DeveloperAPIService = Depends(get_db)
):
    """
    创建新的API密钥

    - **name**: API密钥名称
    - **permissions**: 权限列表（可选）
    - **rate_limit**: 速率限制（可选）
    - **allowed_models**: 允许使用的模型列表（可选）
    - **expires_days**: 过期天数（可选）
    """
    try:
        # 创建API密钥
        api_key, secret_key = await api_service.create_api_key(
            developer_id=str(developer.id),
            name=request.name,
            permissions=request.permissions,
            rate_limit=request.rate_limit,
            allowed_models=request.allowed_models,
            expires_days=request.expires_days
        )

        return {
            "success": True,
            "message": "API密钥创建成功",
            "data": {
                "id": str(api_key.id),
                "name": api_key.name,
                "api_key": secret_key,  # 仅在此处返回完整密钥
                "key_prefix": api_key.key_prefix,
                "permissions": api_key.permissions,
                "rate_limit": api_key.rate_limit,
                "allowed_models": api_key.allowed_models,
                "is_active": api_key.is_active,
                "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
                "created_at": api_key.created_at.isoformat()
            },
            "warning": "请妥善保存您的API密钥，它只会显示一次"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API密钥创建失败"
        )


@router.get("/keys", response_model=dict)
async def get_api_keys(
    developer: Developer = Depends(get_current_developer),
    api_service: DeveloperAPIService = Depends(get_db),
    include_inactive: bool = Query(False, description="是否包含已禁用的密钥"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取开发者的API密钥列表

    - **include_inactive**: 是否包含已禁用的密钥
    - **page**: 页码
    - **limit**: 每页数量
    """
    try:
        result = await api_service.get_api_keys(
            developer_id=str(developer.id),
            include_inactive=include_inactive,
            page=page,
            limit=limit
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取API密钥列表失败"
        )


@router.get("/keys/{api_key_id}", response_model=dict)
async def get_api_key(
    api_key_id: str,
    developer: Developer = Depends(get_current_developer),
    api_service: DeveloperAPIService = Depends(get_db)
):
    """
    获取特定API密钥详情

    - **api_key_id**: API密钥ID
    """
    try:
        api_key = await api_service.get_api_key(api_key_id, str(developer.id))

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API密钥不存在"
            )

        return {
            "success": True,
            "data": api_key.to_dict(include_usage=True)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取API密钥详情失败"
        )


@router.put("/keys/{api_key_id}", response_model=dict)
async def update_api_key(
    api_key_id: str,
    request: UpdateAPIKeyRequest,
    developer: Developer = Depends(get_current_developer),
    api_service: DeveloperAPIService = Depends(get_db)
):
    """
    更新API密钥信息

    - **api_key_id**: API密钥ID
    - **name**: API密钥名称（可选）
    - **permissions**: 权限列表（可选）
    - **rate_limit**: 速率限制（可选）
    - **allowed_models**: 允许使用的模型列表（可选）
    - **is_active**: 是否激活（可选）
    """
    try:
        api_key = await api_service.update_api_key(
            api_key_id=api_key_id,
            developer_id=str(developer.id),
            name=request.name,
            permissions=request.permissions,
            rate_limit=request.rate_limit,
            allowed_models=request.allowed_models,
            is_active=request.is_active
        )

        return {
            "success": True,
            "message": "API密钥更新成功",
            "data": api_key.to_dict()
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API密钥更新失败"
        )


@router.post("/keys/{api_key_id}/regenerate", response_model=dict)
async def regenerate_api_key(
    api_key_id: str,
    developer: Developer = Depends(get_current_developer),
    api_service: DeveloperAPIService = Depends(get_db)
):
    """
    重新生成API密钥

    - **api_key_id**: API密钥ID
    """
    try:
        api_key, new_secret_key = await api_service.regenerate_api_key(
            api_key_id=api_key_id,
            developer_id=str(developer.id)
        )

        return {
            "success": True,
            "message": "API密钥重新生成成功",
            "data": {
                "id": str(api_key.id),
                "name": api_key.name,
                "api_key": new_secret_key,  # 新的完整密钥
                "key_prefix": api_key.key_prefix,
                "created_at": api_key.created_at.isoformat()
            },
            "warning": "请妥善保存您的新API密钥，它只会显示一次"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API密钥重新生成失败"
        )


@router.delete("/keys/{api_key_id}", response_model=dict)
async def delete_api_key(
    api_key_id: str,
    developer: Developer = Depends(get_current_developer),
    api_service: DeveloperAPIService = Depends(get_db)
):
    """
    删除API密钥（软删除）

    - **api_key_id**: API密钥ID
    """
    try:
        success = await api_service.delete_api_key(
            api_key_id=api_key_id,
            developer_id=str(developer.id)
        )

        if success:
            return {
                "success": True,
                "message": "API密钥删除成功"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API密钥不存在"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API密钥删除失败"
        )


@router.get("/keys/{api_key_id}/usage", response_model=dict)
async def get_api_key_usage_stats(
    api_key_id: str,
    developer: Developer = Depends(get_current_developer),
    api_service: DeveloperAPIService = Depends(get_db),
    days: int = Query(30, ge=1, le=90, description="统计天数")
):
    """
    获取API密钥使用统计

    - **api_key_id**: API密钥ID
    - **days**: 统计天数（1-90天）
    """
    try:
        stats = await api_service.get_api_key_usage_stats(
            api_key_id=api_key_id,
            developer_id=str(developer.id),
            days=days
        )

        return {
            "success": True,
            "data": stats
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取使用统计失败"
        )


@router.get("/quota", response_model=dict)
async def get_developer_quota(
    developer: Developer = Depends(get_current_developer),
    api_service: DeveloperAPIService = Depends(get_db)
):
    """
    获取开发者配额信息
    """
    try:
        quota_info = await api_service.get_developer_api_quota(str(developer.id))

        return {
            "success": True,
            "data": quota_info
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取配额信息失败"
        )


@router.get("/permissions", response_model=dict)
async def get_available_permissions(
    developer: Developer = Depends(get_current_developer)
):
    """
    获取可用权限列表
    """
    try:
        # 基础权限
        basic_permissions = [
            {
                "name": "chat.completions",
                "description": "对话完成API",
                "category": "基础功能"
            },
            {
                "name": "chat.models",
                "description": "获取可用模型列表",
                "category": "基础功能"
            },
            {
                "name": "usage.view",
                "description": "查看使用统计",
                "category": "基础功能"
            }
        ]

        # 高级权限（根据开发者类型决定）
        advanced_permissions = [
            {
                "name": "batch.processing",
                "description": "批量处理功能",
                "category": "高级功能"
            },
            {
                "name": "webhooks.manage",
                "description": "管理Webhook",
                "category": "高级功能"
            },
            {
                "name": "analytics.access",
                "description": "访问高级分析",
                "category": "高级功能"
            }
        ]

        # 管理权限（企业用户）
        admin_permissions = [
            {
                "name": "billing.manage",
                "description": "管理账单和订阅",
                "category": "管理功能"
            },
            {
                "name": "subscription.manage",
                "description": "管理订阅",
                "category": "管理功能"
            }
        ]

        all_permissions = basic_permissions

        # 根据开发者类型添加权限
        if developer.developer_type in ['startup', 'enterprise', 'agency']:
            all_permissions.extend(advanced_permissions)

        if developer.developer_type == 'enterprise':
            all_permissions.extend(admin_permissions)

        return {
            "success": True,
            "data": {
                "permissions": all_permissions,
                "categories": ["基础功能", "高级功能", "管理功能"]
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取权限列表失败"
        )


@router.get("/models", response_model=dict)
async def get_available_models(
    developer: Developer = Depends(get_current_developer)
):
    """
    获取可用模型列表
    """
    try:
        # 基础模型（所有开发者可用）
        basic_models = [
            {
                "id": "gpt-4o-mini",
                "name": "GPT-4o Mini",
                "description": "轻量级GPT-4o模型，适合日常任务",
                "category": "基础模型",
                "pricing": "$0.00015/1K tokens"
            },
            {
                "id": "llama-3.1-70b",
                "name": "Llama 3.1 70B",
                "description": "Meta开源的高性能模型",
                "category": "基础模型",
                "pricing": "$0.001/1K tokens"
            }
        ]

        # 高级模型（付费用户可用）
        advanced_models = [
            {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "description": "OpenAI最新旗舰模型",
                "category": "高级模型",
                "pricing": "$0.015/1K tokens"
            },
            {
                "id": "claude-3.5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "description": "Anthropic高性能模型",
                "category": "高级模型",
                "pricing": "$0.003/1K tokens"
            },
            {
                "id": "gemini-1.5-pro",
                "name": "Gemini 1.5 Pro",
                "description": "Google多模态大模型",
                "category": "高级模型",
                "pricing": "$0.0025/1K tokens"
            }
        ]

        all_models = basic_models

        # 根据开发者类型决定可用模型
        if developer.developer_type in ['startup', 'enterprise', 'agency']:
            all_models.extend(advanced_models)

        return {
            "success": True,
            "data": {
                "models": all_models,
                "categories": ["基础模型", "高级模型"]
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取模型列表失败"
        )