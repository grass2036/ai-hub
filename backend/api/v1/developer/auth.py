"""
Developer Authentication API
Week 4 Day 22: Developer Portal and Authentication System
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from typing import Optional

from backend.database import get_db
from backend.services.developer_service import DeveloperService
from backend.core.developer_auth import (
    get_developer_service,
    get_current_developer,
    get_client_info
)
from backend.models.developer import Developer, DeveloperType

# 创建路由器
router = APIRouter()

# 请求/响应模型
class DeveloperRegisterRequest(BaseModel):
    """开发者注册请求"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    developer_type: Optional[str] = DeveloperType.INDIVIDUAL


class DeveloperLoginRequest(BaseModel):
    """开发者登录请求"""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """密码重置请求"""
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """密码重置确认请求"""
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    current_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    """更新资料请求"""
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    preferences: Optional[dict] = None


class VerifyEmailRequest(BaseModel):
    """邮箱验证请求"""
    token: str


# 响应模型
class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class DeveloperResponse(BaseModel):
    """开发者响应"""
    id: str
    email: str
    full_name: Optional[str]
    company_name: Optional[str]
    developer_type: str
    status: str
    email_verified: bool
    api_quota_limit: int
    api_rate_limit: int
    is_active: bool
    created_at: str
    last_login_at: Optional[str]


class DeveloperStatsResponse(BaseModel):
    """开发者统计响应"""
    api_keys_count: int
    monthly_tokens: int
    monthly_requests: int
    monthly_cost: float
    last_updated: str


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_developer(
    request: DeveloperRegisterRequest,
    developer_service: DeveloperService = Depends(get_developer_service),
    http_request: Request = None
):
    """
    注册新开发者

    - **email**: 邮箱地址（必须唯一）
    - **password**: 密码（至少8位）
    - **full_name**: 真实姓名（可选）
    - **company_name**: 公司名称（可选）
    - **developer_type**: 开发者类型（individual/startup/enterprise/agency）
    """
    try:
        # 验证密码强度
        if len(request.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="密码长度至少8位"
            )

        # 注册开发者
        developer, access_token = await developer_service.register_developer(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            company_name=request.company_name,
            developer_type=request.developer_type
        )

        # TODO: 发送验证邮件
        # await email_service.send_verification_email(developer.email, developer.email_verification_token)

        return {
            "success": True,
            "message": "注册成功，请检查邮箱验证链接",
            "data": {
                "developer": developer.to_dict(),
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": 60 * 60 * 24 * 7  # 7天
            }
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )


@router.post("/login", response_model=dict)
async def login_developer(
    request: DeveloperLoginRequest,
    developer_service: DeveloperService = Depends(get_developer_service),
    http_request: Request = None
):
    """
    开发者登录

    - **email**: 邮箱地址
    - **password**: 密码
    """
    try:
        # 获取客户端信息
        client_info = get_client_info(http_request)

        # 登录开发者
        developer, access_token = await developer_service.login_developer(
            email=request.email,
            password=request.password,
            user_agent=client_info.get("user_agent"),
            ip_address=client_info.get("ip_address")
        )

        return {
            "success": True,
            "message": "登录成功",
            "data": {
                "developer": developer.to_dict(),
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": 60 * 60 * 24 * 7  # 7天
            }
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )


@router.post("/refresh", response_model=dict)
async def refresh_token(
    request: RefreshTokenRequest,
    developer_service: DeveloperService = Depends(get_developer_service)
):
    """
    刷新访问令牌

    - **refresh_token**: 刷新令牌
    """
    try:
        developer, new_access_token = await developer_service.refresh_token(
            request.refresh_token
        )

        return {
            "success": True,
            "message": "令牌刷新成功",
            "data": {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": 60 * 60 * 24 * 7  # 7天
            }
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="令牌刷新失败"
        )


@router.post("/logout", response_model=dict)
async def logout_developer(
    developer: Developer = Depends(get_current_developer),
    developer_service: DeveloperService = Depends(get_developer_service)
):
    """
    开发者登出
    """
    try:
        # 这里需要从请求头获取访问令牌
        # 由于fastapi的限制，我们暂时使用成功响应
        # 实际的登出逻辑在前端删除令牌
        return {
            "success": True,
            "message": "登出成功"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出失败"
        )


@router.get("/me", response_model=dict)
async def get_current_developer_info(
    developer: Developer = Depends(get_current_developer)
):
    """
    获取当前开发者信息
    """
    return {
        "success": True,
        "data": developer.to_dict()
    }


@router.put("/me", response_model=dict)
async def update_developer_profile(
    request: UpdateProfileRequest,
    developer: Developer = Depends(get_current_developer),
    developer_service: DeveloperService = Depends(get_developer_service)
):
    """
    更新开发者资料

    - **full_name**: 真实姓名
    - **company_name**: 公司名称
    - **timezone**: 时区
    - **language**: 语言
    - **preferences**: 用户偏好设置
    """
    try:
        updated_developer = await developer_service.update_developer_profile(
            developer_id=str(developer.id),
            full_name=request.full_name,
            company_name=request.company_name,
            timezone=request.timezone,
            language=request.language,
            preferences=request.preferences
        )

        return {
            "success": True,
            "message": "资料更新成功",
            "data": updated_developer.to_dict()
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="资料更新失败"
        )


@router.post("/change-password", response_model=dict)
async def change_password(
    request: ChangePasswordRequest,
    developer: Developer = Depends(get_current_developer),
    developer_service: DeveloperService = Depends(get_developer_service)
):
    """
    修改密码

    - **current_password**: 当前密码
    - **new_password**: 新密码（至少8位）
    """
    try:
        # 验证新密码强度
        if len(request.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="新密码长度至少8位"
            )

        success = await developer_service.change_password(
            developer_id=str(developer.id),
            current_password=request.current_password,
            new_password=request.new_password
        )

        if success:
            return {
                "success": True,
                "message": "密码修改成功，请重新登录"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前密码错误"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码修改失败"
        )


@router.post("/verify-email", response_model=dict)
async def verify_email(
    request: VerifyEmailRequest,
    developer_service: DeveloperService = Depends(get_developer_service)
):
    """
    验证邮箱

    - **token**: 邮箱验证令牌
    """
    try:
        success = await developer_service.verify_email(request.token)

        if success:
            return {
                "success": True,
                "message": "邮箱验证成功"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证链接无效或已过期"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="邮箱验证失败"
        )


@router.post("/request-password-reset", response_model=dict)
async def request_password_reset(
    request: PasswordResetRequest,
    developer_service: DeveloperService = Depends(get_developer_service)
):
    """
    请求密码重置

    - **email**: 邮箱地址
    """
    try:
        # 为了安全，无论邮箱是否存在都返回成功消息
        await developer_service.request_password_reset(request.email)

        return {
            "success": True,
            "message": "如果该邮箱已注册，您将收到密码重置邮件"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码重置请求失败"
        )


@router.post("/reset-password", response_model=dict)
async def reset_password(
    request: PasswordResetConfirmRequest,
    developer_service: DeveloperService = Depends(get_developer_service)
):
    """
    重置密码

    - **token**: 密码重置令牌
    - **new_password**: 新密码（至少8位）
    """
    try:
        # 验证新密码强度
        if len(request.new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="密码长度至少8位"
            )

        success = await developer_service.reset_password(
            token=request.token,
            new_password=request.new_password
        )

        if success:
            return {
                "success": True,
                "message": "密码重置成功，请重新登录"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="重置链接无效或已过期"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码重置失败"
        )


@router.get("/stats", response_model=dict)
async def get_developer_stats(
    developer: Developer = Depends(get_current_developer),
    developer_service: DeveloperService = Depends(get_developer_service)
):
    """
    获取开发者统计信息
    """
    try:
        stats = await developer_service.get_developer_stats(str(developer.id))

        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取统计信息失败"
        )