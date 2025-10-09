"""
配置管理API
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from backend.core.config_manager import config_manager, get_app_config, is_feature_enabled

router = APIRouter()


class AppConfigResponse(BaseModel):
    """应用配置响应"""
    debug_mode: bool = Field(..., description="调试模式")
    enable_rate_limiting: bool = Field(..., description="启用限流")
    enable_request_logging: bool = Field(..., description="启用请求日志")
    enable_response_cache: bool = Field(..., description="启用响应缓存")
    enable_analytics: bool = Field(..., description="启用分析")
    max_requests_per_minute: int = Field(..., description="每分钟最大请求数")
    cache_ttl_seconds: int = Field(..., description="缓存TTL秒数")
    maintenance_mode: bool = Field(..., description="维护模式")
    allowed_origins: List[str] = Field(..., description="允许的来源")


class FeatureFlagResponse(BaseModel):
    """特性开关响应"""
    name: str = Field(..., description="特性名称")
    enabled: bool = Field(..., description="是否启用")
    description: str = Field(..., description="描述")
    rollout_percentage: int = Field(..., description="发布百分比")
    last_updated: Optional[str] = Field(default=None, description="最后更新时间")


class UpdateFeatureFlagRequest(BaseModel):
    """更新特性开关请求"""
    enabled: bool = Field(..., description="是否启用")
    description: Optional[str] = Field(default=None, description="描述")
    rollout_percentage: Optional[int] = Field(default=100, ge=0, le=100, description="发布百分比")


class UpdateConfigRequest(BaseModel):
    """更新配置请求"""
    debug_mode: Optional[bool] = Field(default=None, description="调试模式")
    enable_rate_limiting: Optional[bool] = Field(default=None, description="启用限流")
    enable_request_logging: Optional[bool] = Field(default=None, description="启用请求日志")
    enable_response_cache: Optional[bool] = Field(default=None, description="启用响应缓存")
    enable_analytics: Optional[bool] = Field(default=None, description="启用分析")
    max_requests_per_minute: Optional[int] = Field(default=None, ge=1, le=1000, description="每分钟最大请求数")
    cache_ttl_seconds: Optional[int] = Field(default=None, ge=1, le=3600, description="缓存TTL秒数")
    maintenance_mode: Optional[bool] = Field(default=None, description="维护模式")
    allowed_origins: Optional[List[str]] = Field(default=None, description="允许的来源")


@router.get("/config/app", response_model=AppConfigResponse)
async def get_app_config_endpoint():
    """
    获取应用配置
    """
    try:
        config = await get_app_config()
        return AppConfigResponse(**config.__dict__)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取应用配置失败: {str(e)}"
        )


@router.put("/config/app", response_model=AppConfigResponse)
async def update_app_config_endpoint(request: UpdateConfigRequest):
    """
    更新应用配置
    """
    try:
        current_config = await get_app_config()

        # 更新配置
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(current_config, field):
                setattr(current_config, field, value)

        # 保存配置
        success = await config_manager.save_app_config(current_config)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="保存配置失败"
            )

        return AppConfigResponse(**current_config.__dict__)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新应用配置失败: {str(e)}"
        )


@router.get("/config/feature-flags", response_model=List[FeatureFlagResponse])
async def get_feature_flags():
    """
    获取所有特性开关
    """
    try:
        flags = await config_manager.load_feature_flags()
        return [FeatureFlagResponse(**flag.__dict__) for flag in flags.values()]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取特性开关失败: {str(e)}"
        )


@router.get("/config/feature-flags/{feature_name}", response_model=FeatureFlagResponse)
async def get_feature_flag(feature_name: str):
    """
    获取指定特性开关
    """
    try:
        flags = await config_manager.load_feature_flags()
        if feature_name not in flags:
            raise HTTPException(
                status_code=404,
                detail=f"特性开关 {feature_name} 不存在"
            )

        return FeatureFlagResponse(**flags[feature_name].__dict__)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取特性开关失败: {str(e)}"
        )


@router.put("/config/feature-flags/{feature_name}", response_model=FeatureFlagResponse)
async def update_feature_flag_endpoint(
    feature_name: str,
    request: UpdateFeatureFlagRequest
):
    """
    更新特性开关
    """
    try:
        success = await config_manager.update_feature_flag(
            feature_name=feature_name,
            enabled=request.enabled,
            description=request.description,
            rollout_percentage=request.rollout_percentage
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="更新特性开关失败"
            )

        # 返回更新后的配置
        flags = await config_manager.load_feature_flags()
        return FeatureFlagResponse(**flags[feature_name].__dict__)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新特性开关失败: {str(e)}"
        )


@router.get("/config/feature-flags/{feature_name}/enabled")
async def check_feature_enabled(
    feature_name: str,
    user_id: Optional[str] = Query(default=None, description="用户ID（用于渐进式发布）")
):
    """
    检查特性是否对指定用户启用
    """
    try:
        enabled = await is_feature_enabled(feature_name, user_id)
        return {
            "feature": feature_name,
            "enabled": enabled,
            "user_id": user_id,
            "timestamp": "2025-10-07T00:00:00Z"  # 简化时间戳
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"检查特性开关失败: {str(e)}"
        )


@router.get("/config/all")
async def get_all_configs():
    """
    获取所有配置信息
    """
    try:
        all_configs = await config_manager.get_all_configs()
        return all_configs
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取配置失败: {str(e)}"
        )


@router.post("/config/reset")
async def reset_configs():
    """
    重置所有配置为默认值
    """
    try:
        success = await config_manager.reset_to_defaults()
        if not success:
            raise HTTPException(
                status_code=500,
                detail="重置配置失败"
            )

        return {"message": "配置已重置为默认值"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"重置配置失败: {str(e)}"
        )


@router.get("/config/status")
async def get_config_status():
    """
    获取配置状态信息
    """
    try:
        app_config = await get_app_config()
        flags = await config_manager.load_feature_flags()

        enabled_features = sum(1 for flag in flags.values() if flag.enabled)
        total_features = len(flags)

        return {
            "app_config": {
                "maintenance_mode": app_config.maintenance_mode,
                "debug_mode": app_config.debug_mode,
                "rate_limiting_enabled": app_config.enable_rate_limiting,
                "cache_enabled": app_config.enable_response_cache
            },
            "feature_flags": {
                "total_count": total_features,
                "enabled_count": enabled_features,
                "enabled_percentage": (enabled_features / total_features * 100) if total_features > 0 else 0
            },
            "system_status": {
                "healthy": not app_config.maintenance_mode,
                "production_ready": not app_config.debug_mode and app_config.enable_rate_limiting
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取配置状态失败: {str(e)}"
        )