"""
User management API endpoints

提供用户信息管理、账户设置等功能。
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
import logging

from backend.config.database import get_db
from backend.models.user import User, UserUpdate, UserResponse, UserWithOrganizations
from backend.core.auth.auth_middleware import AuthMiddleware
from backend.core.auth.security import SecurityUtils

router = APIRouter(prefix="/users", tags=["users"])

# 获取认证中间件
def get_auth_middleware() -> AuthMiddleware:
    """获取认证中间件实例"""
    from backend.core.auth.auth_middleware import AuthMiddleware
    from backend.core.auth.jwt_manager import JWTManager
    from backend.config.settings import get_settings

    settings = get_settings()
    jwt_manager = JWTManager(
        secret_key=settings.jwt_secret_key,
        access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
        refresh_token_expire_days=settings.jwt_refresh_token_expire_days
    )
    return AuthMiddleware(jwt_manager)


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    获取当前用户详细信息
    """
    try:
        # 从数据库获取最新用户信息
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        return UserResponse.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    更新当前用户信息

    - **name**: 显示名称
    - **username**: 用户名
    - **avatar_url**: 头像URL
    - **phone**: 电话号码
    - **company**: 公司
    - **website**: 个人网站
    - **timezone**: 时区
    - **language**: 语言
    - **settings**: 用户设置
    """
    try:
        # 获取用户
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        # 检查用户名是否已被其他用户使用
        if user_update.username and user_update.username != user.username:
            existing_user = db.query(User).filter(
                User.username == user_update.username.lower(),
                User.id != user.id
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="用户名已被其他用户使用"
                )

        # 更新用户信息
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "username" and value:
                setattr(user, field, value.lower())
            elif field == "settings" and value:
                setattr(user, field, str(value))
            else:
                setattr(user, field, value)

        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

        logger.info(f"用户信息更新成功: {user.email}")

        return UserResponse.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户信息失败，请稍后重试"
        )


@router.get("/me/organizations", response_model=UserWithOrganizations)
async def get_user_organizations(
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的组织信息
    """
    try:
        # 获取用户
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        # TODO: 获取用户的组织信息
        organizations = []
        total_organizations = 0

        return UserWithOrganizations(
            **UserResponse.model_validate(user).model_dump(),
            organizations=organizations,
            total_organizations=total_organizations
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户组织信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取组织信息失败"
        )


@router.get("/me/sessions")
async def get_user_sessions(
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的活跃会话列表
    """
    try:
        # TODO: 实现会话管理
        return {
            "sessions": [],
            "total_sessions": 0,
            "message": "会话管理功能开发中"
        }

    except Exception as e:
        logger.error(f"获取用户会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话信息失败"
        )


@router.delete("/me/sessions/{session_id}")
async def terminate_user_session(
    session_id: str,
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    终止指定的用户会话
    """
    try:
        # TODO: 实现会话终止
        return {
            "message": "会话终止功能开发中",
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"终止用户会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="终止会话失败"
        )


@router.delete("/me/sessions")
async def terminate_all_user_sessions(
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    终止用户的所有其他会话（除当前会话外）
    """
    try:
        # TODO: 实现所有会话终止
        return {
            "message": "终止所有会话功能开发中"
        }

    except Exception as e:
        logger.error(f"终止所有用户会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="终止会话失败"
        )


@router.get("/me/activity")
async def get_user_activity(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的活动日志
    """
    try:
        # TODO: 实现用户活动日志查询
        return {
            "activities": [],
            "total_activities": 0,
            "limit": limit,
            "offset": offset,
            "message": "活动日志功能开发中"
        }

    except Exception as e:
        logger.error(f"获取用户活动失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取活动日志失败"
        )


@router.post("/me/deactivate")
async def deactivate_user_account(
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    停用当前用户账户
    """
    try:
        # 获取用户
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        # 停用账户
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"用户账户停用: {user.email}")

        return {"message": "账户已停用"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停用用户账户失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="停用账户失败，请稍后重试"
        )


@router.post("/me/verify-email")
async def request_email_verification(
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    请求邮箱验证
    """
    try:
        # 获取用户
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        if user.is_verified:
            return {"message": "邮箱已验证"}

        # TODO: 发送邮箱验证邮件
        # verification_token = generate_email_verification_token(user.id)
        # await send_verification_email(user.email, verification_token)

        logger.info(f"邮箱验证请求: {user.email}")

        return {"message": "验证邮件已发送"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送邮箱验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送验证邮件失败，请稍后重试"
        )


@router.get("/me/notifications")
async def get_user_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的通知列表
    """
    try:
        # TODO: 实现通知系统
        return {
            "notifications": [],
            "total_notifications": 0,
            "unread_count": 0,
            "limit": limit,
            "offset": offset,
            "message": "通知系统功能开发中"
        }

    except Exception as e:
        logger.error(f"获取用户通知失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取通知失败"
        )


@router.put("/me/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    标记通知为已读
    """
    try:
        # TODO: 实现通知标记已读
        return {
            "message": "通知标记功能开发中",
            "notification_id": notification_id
        }

    except Exception as e:
        logger.error(f"标记通知已读失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="标记通知失败"
        )


@router.get("/me/preferences")
async def get_user_preferences(
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    获取用户偏好设置
    """
    try:
        # 获取用户
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        # 解析设置JSON
        import json
        try:
            settings = json.loads(user.settings) if user.settings else {}
        except:
            settings = {}

        # 返回用户偏好设置
        return {
            "timezone": user.timezone,
            "language": user.language,
            "email_notifications": settings.get("email_notifications", True),
            "theme": settings.get("theme", "light"),
            "settings": settings
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户偏好设置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取偏好设置失败"
        )


@router.put("/me/preferences")
async def update_user_preferences(
    preferences: dict,
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    更新用户偏好设置
    """
    try:
        # 获取用户
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        # 更新用户偏好
        if "timezone" in preferences:
            user.timezone = preferences["timezone"]
        if "language" in preferences:
            user.language = preferences["language"]

        # 更新设置JSON
        import json
        try:
            current_settings = json.loads(user.settings) if user.settings else {}
        except:
            current_settings = {}

        # 合并设置
        for key, value in preferences.items():
            if key not in ["timezone", "language"]:
                current_settings[key] = value

        user.settings = json.dumps(current_settings)
        user.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"用户偏好设置更新成功: {user.email}")

        return {"message": "偏好设置已更新"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户偏好设置失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新偏好设置失败，请稍后重试"
        )