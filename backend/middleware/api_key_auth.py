"""
API Key Authentication Middleware
Week 5 Day 1: API Commercialization Foundation
"""

from typing import Optional
from fastapi import HTTPException, status, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

from datetime import datetime
from backend.database import get_db
from backend.services.developer_api_service import DeveloperAPIService
from backend.models.developer import DeveloperAPIKey

logger = logging.getLogger(__name__)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """API密钥认证中间件"""

    def __init__(self, app, excluded_paths: Optional[list] = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/",
            "/health",
            "/status",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/developer/auth/register",
            "/developer/auth/login",
            "/models",  # 公开的模型列表
            "/chat"  # 公开的聊天接口（用于演示）
        ]

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        path = request.url.path

        # 检查是否为排除路径
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)

        # 检查是否为开发者API路径
        if path.startswith("/developer/"):
            # 开发者API使用JWT认证，跳过API密钥验证
            return await call_next(request)

        # 检查是否为受保护的API路径
        protected_api_paths = [
            "/api/v1/chat/",
            "/api/v1/sessions/",
            "/api/v1/stats/",
        ]

        if any(path.startswith(protected) for protected in protected_api_paths):
            # 验证API密钥
            api_key = self._extract_api_key(request)

            if not api_key:
                logger.warning(f"Missing API key for protected path: {path}")
                return Response(
                    content='{"error": "Missing API key", "message": "Please provide a valid API key in Authorization header or api_key query parameter"}',
                    status_code=401,
                    media_type="application/json"
                )

            # 验证API密钥有效性
            try:
                # 这里需要获取数据库连接来验证API密钥
                # 由于中间件中无法直接使用Depends，我们需要手动处理
                db = next(get_db())
                api_service = DeveloperAPIService(db)

                api_key_obj = await api_service.validate_api_key(api_key)
                if not api_key_obj:
                    logger.warning(f"Invalid API key: {api_key[:8]}... for path: {path}")
                    return Response(
                        content='{"error": "Invalid API key", "message": "The provided API key is invalid or expired"}',
                        status_code=401,
                        media_type="application/json"
                    )

                # 检查API密钥权限
                if not await self._check_api_key_permissions(api_key_obj, path, request.method):
                    logger.warning(f"Insufficient permissions for API key: {api_key[:8]}... for path: {path}")
                    return Response(
                        content='{"error": "Insufficient permissions", "message": "Your API key does not have permission to access this endpoint"}',
                        status_code=403,
                        media_type="application/json"
                    )

                # 检查速率限制
                if not await self._check_rate_limit(api_key_obj):
                    logger.warning(f"Rate limit exceeded for API key: {api_key[:8]}...")
                    return Response(
                        content='{"error": "Rate limit exceeded", "message": "You have exceeded the rate limit for your API key"}',
                        status_code=429,
                        media_type="application/json"
                    )

                # 将API密钥信息添加到请求状态中
                request.state.api_key = api_key_obj
                request.state.developer_id = api_key_obj.developer_id

            except Exception as e:
                logger.error(f"Error validating API key: {str(e)}")
                return Response(
                    content='{"error": "Authentication error", "message": "Failed to validate API key"}',
                    status_code=500,
                    media_type="application/json"
                )
            finally:
                db.close()

        response = await call_next(request)
        return response

    def _extract_api_key(self, request: Request) -> Optional[str]:
        """从请求中提取API密钥"""
        # 1. 从Authorization header提取 (Bearer token)
        authorization = request.headers.get("authorization")
        if authorization:
            try:
                scheme, credentials = authorization.split()
                if scheme.lower() == "bearer":
                    return credentials
            except ValueError:
                pass

        # 2.从X-API-Key header提取
        api_key = request.headers.get("x-api-key")
        if api_key:
            return api_key

        # 3. 从查询参数提取
        api_key = request.query_params.get("api_key")
        if api_key:
            return api_key

        return None

    async def _check_api_key_permissions(self, api_key: DeveloperAPIKey, path: str, method: str) -> bool:
        """检查API密钥权限"""
        # 检查API密钥是否激活
        if not api_key.is_active:
            return False

        # 检查API密钥是否过期
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return False

        # 检查权限列表
        if api_key.permissions:
            # 基础权限映射
            permission_map = {
                "/chat/": "chat.completions",
                "/sessions/": "sessions.manage",
                "/stats/": "usage.view",
                "/models/": "chat.models",
            }

            required_permission = None
            for protected_path, permission in permission_map.items():
                if path.startswith(protected_path):
                    required_permission = permission
                    break

            if required_permission and required_permission not in api_key.permissions:
                return False

        # 检查允许的模型（针对聊天API）
        if path.startswith("/chat/") and api_key.allowed_models:
            # 这里需要从请求体中提取模型信息，暂时跳过
            pass

        return True

    async def _check_rate_limit(self, api_key: DeveloperAPIKey) -> bool:
        """检查速率限制"""
        # 这里应该实现基于Redis的分布式速率限制
        # 暂时使用简单的内存检查（生产环境不推荐）
        if not api_key.rate_limit:
            return True  # 无限制

        # TODO: 实现实际的速率限制逻辑
        # 可以使用Redis存储每个API密钥的请求计数

        return True


# 依赖函数，用于在路由中获取当前API密钥信息
async def get_current_api_key(request: Request) -> Optional[DeveloperAPIKey]:
    """获取当前API密钥信息"""
    return getattr(request.state, "api_key", None)


async def get_current_developer_from_api_key(request: Request) -> Optional[str]:
    """从API密钥获取开发者ID"""
    return getattr(request.state, "developer_id", None)


# 验证API密钥的依赖
async def require_api_key(request: Request) -> DeveloperAPIKey:
    """要求有效的API密钥"""
    api_key = get_current_api_key(request)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key