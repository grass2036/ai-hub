"""
认证中间件

提供JWT令牌验证、用户身份识别、权限检查等中间件功能。
"""

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict, Any, Callable
import logging
from functools import wraps

from .jwt_manager import JWTManager
from .security import SecurityUtils

logger = logging.getLogger(__name__)

# HTTP Bearer认证方案
security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """认证中间件"""

    def __init__(self, jwt_manager: JWTManager):
        """
        初始化认证中间件

        Args:
            jwt_manager: JWT管理器实例
        """
        self.jwt_manager = jwt_manager

    async def get_current_user(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Dict[str, Any]:
        """
        获取当前用户信息

        Args:
            request: FastAPI请求对象
            credentials: HTTP认证凭据

        Returns:
            用户信息字典

        Raises:
            HTTPException: 认证失败
        """
        # 如果没有提供认证信息，返回None（可选认证）
        if credentials is None:
            return None

        try:
            # 提取令牌
            token = credentials.credentials

            # 检查令牌是否被撤销
            if self.jwt_manager.is_token_revoked(token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="令牌已被撤销",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # 验证令牌并提取用户信息
            user_info = self.jwt_manager.extract_user_from_token(token)
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="无效令牌",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # 将用户信息添加到请求状态中
            request.state.user = user_info

            logger.debug(f"用户认证成功: {user_info.get('user_id')}")
            return user_info

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"用户认证失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="认证服务异常"
            )

    async def get_current_user_required(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict[str, Any]:
        """
        获取当前用户信息（必需认证）

        Args:
            request: FastAPI请求对象
            credentials: HTTP认证凭据

        Returns:
            用户信息字典

        Raises:
            HTTPException: 认证失败
        """
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少认证信息",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await self.get_current_user(request, credentials)

    def require_permissions(self, required_permissions: List[str]):
        """
        权限检查装饰器

        Args:
            required_permissions: 需要的权限列表

        Returns:
            装饰器函数
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 获取请求对象（通常是第一个参数或通过依赖注入）
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

                if not request:
                    # 尝试从kwargs中获取
                    request = kwargs.get('request')

                if not request:
                    logger.error("无法获取请求对象进行权限检查")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="权限检查失败"
                    )

                # 检查用户信息
                if not hasattr(request.state, 'user') or not request.state.user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="需要认证"
                    )

                user_permissions = request.state.user.get('permissions', [])
                user_role = request.state.user.get('role', '')

                # 检查权限
                if not self._check_permissions(user_role, user_permissions, required_permissions):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="权限不足"
                    )

                # 执行原函数
                return await func(*args, **kwargs)

            return wrapper
        return decorator

    def _check_permissions(
        self,
        user_role: str,
        user_permissions: List[str],
        required_permissions: List[str]
    ) -> bool:
        """
        检查用户权限

        Args:
            user_role: 用户角色
            user_permissions: 用户权限列表
            required_permissions: 需要的权限列表

        Returns:
            是否有权限
        """
        # 超级管理员拥有所有权限
        if user_role == 'admin' or user_role == 'super_admin':
            return True

        # 检查每个需要的权限
        for permission in required_permissions:
            if permission not in user_permissions:
                return False

        return True

    def require_role(self, required_roles: List[str]):
        """
        角色检查装饰器

        Args:
            required_roles: 需要的角色列表

        Returns:
            装饰器函数
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 获取请求对象
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

                if not request:
                    request = kwargs.get('request')

                if not request:
                    logger.error("无法获取请求对象进行角色检查")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="角色检查失败"
                    )

                # 检查用户信息
                if not hasattr(request.state, 'user') or not request.state.user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="需要认证"
                    )

                user_role = request.state.user.get('role', '')

                # 检查角色
                if user_role not in required_roles:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="角色权限不足"
                    )

                # 执行原函数
                return await func(*args, **kwargs)

            return wrapper
        return decorator

    def extract_token_from_request(self, request: Request) -> Optional[str]:
        """
        从请求中提取令牌

        Args:
            request: FastAPI请求对象

        Returns:
            JWT令牌或None
        """
        # 从Authorization头提取
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            return authorization[7:]

        # 从查询参数提取（用于WebSocket等场景）
        token = request.query_params.get("token")
        if token:
            return token

        # 从Cookie提取
        token = request.cookies.get("access_token")
        if token:
            return token

        return None

    async def authenticate_api_key(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        API密钥认证

        Args:
            request: FastAPI请求对象

        Returns:
            API密钥信息或None
        """
        # 从X-API-Key头提取
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return None

        # 这里应该验证API密钥的有效性
        # 实际实现需要查询数据库或缓存
        # 暂时返回示例数据
        return {
            "api_key": api_key,
            "key_id": "demo_key_id",
            "permissions": ["read", "write"],
            "rate_limit": 1000
        }

    def create_auth_dependency(self, required: bool = True):
        """
        创建认证依赖

        Args:
            required: 是否必需认证

        Returns:
            认证依赖函数
        """
        if required:
            return self.get_current_user_required
        else:
            return self.get_current_user


# 便捷函数
def create_auth_middleware(jwt_manager: JWTManager) -> AuthMiddleware:
    """
    创建认证中间件实例

    Args:
        jwt_manager: JWT管理器

    Returns:
        认证中间件实例
    """
    return AuthMiddleware(jwt_manager)


# 权限检查装饰器
def require_permissions(auth_middleware: AuthMiddleware, permissions: List[str]):
    """
    权限检查装饰器

    Args:
        auth_middleware: 认证中间件
        permissions: 需要的权限列表

    Returns:
        装饰器
    """
    return auth_middleware.require_permissions(permissions)


# 角色检查装饰器
def require_role(auth_middleware: AuthMiddleware, roles: List[str]):
    """
    角色检查装饰器

    Args:
        auth_middleware: 认证中间件
        roles: 需要的角色列表

    Returns:
        装饰器
    """
    return auth_middleware.require_role(roles)