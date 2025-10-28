"""
Authentication API endpoints

提供用户注册、登录、令牌管理、密码重置等认证功能。
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

from backend.config.database import get_db
from backend.models.user import User, UserCreate, UserLogin, UserResponse, TokenResponse, TokenRefresh, PasswordReset, PasswordResetConfirm, PasswordChange
from backend.core.auth.jwt_manager import JWTManager
from backend.core.auth.auth_middleware import AuthMiddleware
from backend.core.auth.security import SecurityUtils

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)

# JWT Manager实例
jwt_manager = None
auth_middleware = None

def get_jwt_manager() -> JWTManager:
    """获取JWT管理器实例"""
    global jwt_manager
    if jwt_manager is None:
        from backend.config.settings import get_settings
        settings = get_settings()
        jwt_manager = JWTManager(
            secret_key=settings.jwt_secret_key,
            access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
            refresh_token_expire_days=settings.jwt_refresh_token_expire_days
        )
    return jwt_manager

def get_auth_middleware() -> AuthMiddleware:
    """获取认证中间件实例"""
    global auth_middleware
    if auth_middleware is None:
        auth_middleware = AuthMiddleware(get_jwt_manager())
    return auth_middleware


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    用户注册

    - **email**: 邮箱地址
    - **username**: 用户名（可选）
    - **password**: 密码
    - **name**: 显示名称（可选）
    """
    try:
        # 检查邮箱是否已存在
        existing_user = db.query(User).filter(User.email == user_data.email.lower()).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )

        # 检查用户名是否已存在
        if user_data.username:
            existing_username = db.query(User).filter(User.username == user_data.username.lower()).first()
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="用户名已被使用"
                )

        # 验证密码强度
        password_validation = SecurityUtils.validate_password_strength(user_data.password)
        if not password_validation["is_strong"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "密码强度不足", "errors": password_validation["errors"]}
            )

        # 创建新用户
        user = User(
            email=user_data.email.lower(),
            username=user_data.username.lower() if user_data.username else None,
            name=user_data.name,
            password_hash=SecurityUtils.hash_password(user_data.password),
            settings=str({}),
            is_active=True,
            is_verified=False  # 需要邮箱验证
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"用户注册成功: {user.email}")

        # TODO: 发送邮箱验证邮件
        # await send_verification_email(user.email)

        return UserResponse.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户注册失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    用户登录

    - **email**: 邮箱地址
    - **password**: 密码
    - **remember_me**: 是否记住登录状态
    """
    try:
        # 查找用户
        user = db.query(User).filter(User.email == login_data.email.lower()).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误"
            )

        # 检查账户状态
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账户已被禁用"
            )

        # 检查账户是否被锁定
        if user.is_locked():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账户已被锁定，请稍后重试"
            )

        # 验证密码
        if not SecurityUtils.verify_password(login_data.password, user.password_hash):
            user.record_failed_login()
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误"
            )

        # 记录登录信息
        client_info = SecurityUtils.extract_client_info(request)
        user.record_login(client_info["ip_address"])
        db.commit()

        # 生成令牌
        token_data = {
            "sub": user.id,
            "email": user.email,
            "username": user.username,
            "role": "user",  # TODO: 从用户角色获取
            "permissions": []  # TODO: 从用户权限获取
        }

        # 如果选择记住登录，延长令牌有效期
        if login_data.remember_me:
            access_token_expires = timedelta(days=7)
            refresh_token_expires = timedelta(days=30)
        else:
            access_token_expires = timedelta(minutes=30)
            refresh_token_expires = timedelta(days=7)

        access_token = get_jwt_manager().create_access_token(token_data, access_token_expires)
        refresh_token = get_jwt_manager().create_refresh_token(token_data, refresh_token_expires)

        logger.info(f"用户登录成功: {user.email}, IP: {client_info['ip_address']}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
            refresh_expires_in=int(refresh_token_expires.total_seconds()),
            user=UserResponse.model_validate(user)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    刷新访问令牌

    - **refresh_token**: 刷新令牌
    """
    try:
        # 验证刷新令牌
        new_tokens = get_jwt_manager().refresh_access_token(token_data.refresh_token)

        # 获取用户信息
        payload = get_jwt_manager().verify_token(new_tokens["access_token"], "access")
        user_id = payload.get("sub")

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被禁用"
            )

        return TokenResponse(
            access_token=new_tokens["access_token"],
            refresh_token=token_data.refresh_token,  # 刷新令牌保持不变
            token_type=new_tokens["token_type"],
            expires_in=new_tokens["expires_in"],
            refresh_expires_in=7 * 24 * 60 * 60,  # 刷新令牌7天有效
            user=UserResponse.model_validate(user)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"令牌刷新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌刷新失败"
        )


@router.post("/logout")
async def logout(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    current_user: dict = Depends(get_auth_middleware().get_current_user)
):
    """
    用户登出
    """
    try:
        if credentials:
            # 撤销访问令牌
            get_jwt_manager().revoke_token(credentials.credentials)
            logger.info(f"用户登出成功: {current_user.get('user_id') if current_user else 'unknown'}")

        return {"message": "登出成功"}

    except Exception as e:
        logger.error(f"用户登出失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出失败"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_auth_middleware().get_current_user_required)
):
    """
    获取当前用户信息
    """
    try:
        # TODO: 从数据库获取最新的用户信息
        return current_user

    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    修改密码

    - **current_password**: 当前密码
    - **new_password**: 新密码
    """
    try:
        # 获取用户信息
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        # 验证当前密码
        if not SecurityUtils.verify_password(password_data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前密码错误"
            )

        # 验证新密码强度
        password_validation = SecurityUtils.validate_password_strength(password_data.new_password)
        if not password_validation["is_strong"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "新密码强度不足", "errors": password_validation["errors"]}
            )

        # 更新密码
        user.password_hash = SecurityUtils.hash_password(password_data.new_password)
        user.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"用户修改密码成功: {user.email}")

        return {"message": "密码修改成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="修改密码失败，请稍后重试"
        )


@router.post("/forgot-password")
async def forgot_password(
    reset_data: PasswordReset,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    忘记密码

    - **email**: 邮箱地址
    """
    try:
        # 查找用户
        user = db.query(User).filter(User.email == reset_data.email.lower()).first()
        if not user:
            # 为了安全，即使用户不存在也返回成功消息
            return {"message": "如果邮箱存在，重置链接已发送"}

        # TODO: 生成重置令牌并发送邮件
        # reset_token = generate_password_reset_token(user.id)
        # await send_password_reset_email(user.email, reset_token)

        logger.info(f"密码重置请求: {user.email}")

        return {"message": "如果邮箱存在，重置链接已发送"}

    except Exception as e:
        logger.error(f"忘记密码处理失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="处理请求失败，请稍后重试"
        )


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    重置密码

    - **token**: 重置令牌
    - **new_password**: 新密码
    """
    try:
        # TODO: 验证重置令牌
        # user_id = verify_password_reset_token(reset_data.token)
        # if not user_id:
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="重置令牌无效或已过期"
        #     )

        # 暂时返回成功消息
        return {"message": "密码重置成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"密码重置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码重置失败，请稍后重试"
        )


@router.get("/verify-token")
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    验证令牌有效性
    """
    try:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少认证信息"
            )

        # 验证令牌
        payload = get_jwt_manager().verify_token(credentials.credentials, "access")

        return {
            "valid": True,
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "expires_at": payload.get("exp")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"令牌验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="令牌验证失败"
        )


@router.post("/2fa/setup")
async def setup_2fa(
    current_user: dict = Depends(get_auth_middleware().get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    设置双因素认证
    """
    try:
        # TODO: 实现双因素认证设置
        return {
            "message": "双因素认证设置功能开发中",
            "status": "development"
        }

    except Exception as e:
        logger.error(f"双因素认证设置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="双因素认证设置失败"
        )


@router.post("/2fa/verify")
async def verify_2fa(
    # verification_data: TwoFactorVerify,
    current_user: dict = Depends(get_auth_middleware().get_current_user_required)
):
    """
    验证双因素认证代码
    """
    try:
        # TODO: 实现双因素认证验证
        return {
            "message": "双因素认证验证功能开发中",
            "status": "development"
        }

    except Exception as e:
        logger.error(f"双因素认证验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="双因素认证验证失败"
        )