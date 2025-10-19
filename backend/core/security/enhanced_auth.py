"""
增强的JWT认证机制
Week 6 Day 4: 安全加固和权限配置

提供安全的JWT令牌管理、认证中间件和安全上下文
"""

import asyncio
import jwt
import time
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
import redis
import bcrypt
import logging
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

class TokenType(Enum):
    """令牌类型"""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"
    EMAIL_VERIFICATION = "email_verification"
    API_KEY = "api_key"

class SecurityContext:
    """安全上下文"""

    def __init__(self):
        self.user_id: Optional[str] = None
        self.username: Optional[str] = None
        self.email: Optional[str] = None
        self.roles: List[str] = []
        self.permissions: List[str] = []
        self.session_id: Optional[str] = None
        self.ip_address: Optional[str] = None
        self.user_agent: Optional[str] = None
        self.auth_method: Optional[str] = None
        self.token_jti: Optional[str] = None
        self.token_issued_at: Optional[datetime] = None
        self.token_expires_at: Optional[datetime] = None
        self.is_authenticated: bool = False
        self.is_active: bool = False
        self.is_verified: bool = False

    @classmethod
    def from_token(cls, token_data: Dict[str, Any]) -> 'SecurityContext':
        """从令牌数据创建安全上下文"""
        context = cls()
        context.user_id = token_data.get('sub')
        context.username = token_data.get('username')
        context.email = token_data.get('email')
        context.roles = token_data.get('roles', [])
        context.permissions = token_data.get('permissions', [])
        context.session_id = token_data.get('session_id')
        context.token_jti = token_data.get('jti')
        context.is_authenticated = True
        context.is_active = token_data.get('is_active', False)
        context.is_verified = token_data.get('is_verified', False)
        return context

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "permissions": self.permissions,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "auth_method": self.auth_method,
            "token_jti": self.token_jti,
            "is_authenticated": self.is_authenticated,
            "is_active": self.is_active,
            "is_verified": self.is_verified
        }

class AuthenticationError(Exception):
    """认证错误"""
    pass

class AuthorizationError(Exception):
    """授权错误"""
    pass

class TokenManager:
    """令牌管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.secret_key = config['secret_key']
        self.algorithm = config.get('algorithm', 'HS256')
        self.access_token_expire_minutes = config.get('access_token_expire_minutes', 30)
        self.refresh_token_expire_days = config.get('refresh_token_expire_days', 7)
        self.reset_password_token_expire_minutes = config.get('reset_password_token_expire_minutes', 15)
        self.verification_token_expire_hours = config.get('verification_token_expire_hours', 24)
        self.redis_client: Optional[redis.Redis] = None

    async def initialize(self, redis_client: Optional[redis.Redis] = None) -> None:
        """初始化令牌管理器"""
        self.redis_client = redis_client

    def _create_token(
        self,
        token_type: TokenType,
        payload: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建令牌"""
        now = datetime.utcnow()

        if expires_delta:
            expire = now + expires_delta
        else:
            if token_type == TokenType.ACCESS:
                expire = now + timedelta(minutes=self.access_token_expire_minutes)
            elif token_type == TokenType.REFRESH:
                expire = now + timedelta(days=self.refresh_token_expire_days)
            elif token_type == TokenType.RESET_PASSWORD:
                expire = now + timedelta(minutes=self.reset_password_token_expire_minutes)
            elif token_type == TokenType.EMAIL_VERIFICATION:
                expire = now + timedelta(hours=self.verification_token_expire_hours)
            else:
                expire = now + timedelta(hours=1)

        payload.update({
            'exp': expire,
            'iat': now,
            'jti': str(uuid.uuid4()),
            'type': token_type.value
        })

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    async def create_access_token(
        self,
        user_id: str,
        username: str,
        email: str,
        roles: List[str],
        permissions: List[str],
        session_id: Optional[str] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """创建访问令牌"""
        payload = {
            'sub': user_id,
            'username': username,
            'email': email,
            'roles': roles,
            'permissions': permissions,
            'is_active': True,
            'is_verified': True
        }

        if session_id:
            payload['session_id'] = session_id

        if additional_claims:
            payload.update(additional_claims)

        token = self._create_token(TokenType.ACCESS, payload)

        # 将令牌存储到Redis以便撤销
        if self.redis_client:
            await self._store_token(token, TokenType.ACCESS, payload)

        return token

    async def create_refresh_token(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> str:
        """创建刷新令牌"""
        payload = {
            'sub': user_id,
            'session_id': session_id
        }

        token = self._create_token(TokenType.REFRESH, payload)

        # 存储刷新令牌
        if self.redis_client:
            await self._store_token(token, TokenType.REFRESH, payload)

        return token

    def create_reset_password_token(self, user_id: str, email: str) -> str:
        """创建重置密码令牌"""
        payload = {
            'sub': user_id,
            'email': email,
            'purpose': 'password_reset'
        }

        return self._create_token(TokenType.RESET_PASSWORD, payload)

    def create_email_verification_token(self, user_id: str, email: str) -> str:
        """创建邮箱验证令牌"""
        payload = {
            'sub': user_id,
            'email': email,
            'purpose': 'email_verification'
        }

        return self._create_token(TokenType.EMAIL_VERIFICATION, payload)

    async def verify_token(self, token: str, expected_type: Optional[TokenType] = None) -> Dict[str, Any]:
        """验证令牌"""
        try:
            # 检查令牌是否在黑名单中
            if self.redis_client:
                is_blacklisted = await self._is_token_blacklisted(token)
                if is_blacklisted:
                    raise AuthenticationError("Token has been revoked")

            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # 检查令牌类型
            if expected_type and payload.get('type') != expected_type.value:
                raise AuthenticationError(f"Invalid token type. Expected {expected_type.value}")

            # 检查过期时间
            if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
                raise AuthenticationError("Token has expired")

            return payload

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")

    async def revoke_token(self, token: str) -> bool:
        """撤销令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            jti = payload.get('jti')
            exp = payload.get('exp')

            if self.redis_client and jti and exp:
                # 将令牌加入黑名单，直到其自然过期
                ttl = exp - int(time.time())
                if ttl > 0:
                    await self.redis_client.setex(f"blacklist:{jti}", ttl, "revoked")
                    return True

            return False

        except jwt.InvalidTokenError:
            return False

    async def revoke_user_tokens(self, user_id: str) -> int:
        """撤销用户的所有令牌"""
        if not self.redis_client:
            return 0

        # 获取用户的所有活跃令牌
        pattern = f"token:*:{user_id}:*"
        keys = await self.redis_client.keys(pattern)

        revoked_count = 0
        for key in keys:
            # 获取令牌JTI并加入黑名单
            token_data = await self.redis_client.hgetall(key)
            jti = token_data.get('jti')
            if jti:
                await self.redis_client.setex(f"blacklist:{jti}", 86400, "revoked")  # 24小时
                await self.redis_client.delete(key)
                revoked_count += 1

        return revoked_count

    async def _store_token(self, token: str, token_type: TokenType, payload: Dict[str, Any]) -> None:
        """存储令牌到Redis"""
        if not self.redis_client:
            return

        jti = payload.get('jti')
        user_id = payload.get('sub')
        session_id = payload.get('session_id')
        exp = payload.get('exp')

        if not all([jti, user_id, exp]):
            return

        ttl = exp - int(time.time())
        if ttl <= 0:
            return

        key = f"token:{token_type.value}:{user_id}:{session_id or 'no_session'}:{jti}"
        await self.redis_client.hset(key, mapping={
            'token': token,
            'jti': jti,
            'user_id': user_id,
            'session_id': session_id or '',
            'issued_at': payload.get('iat'),
            'expires_at': exp
        })
        await self.redis_client.expire(key, ttl)

    async def _is_token_blacklisted(self, token: str) -> bool:
        """检查令牌是否在黑名单中"""
        if not self.redis_client:
            return False

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            jti = payload.get('jti')
            return bool(await self.redis_client.exists(f"blacklist:{jti}"))
        except jwt.InvalidTokenError:
            return True

class EnhancedJWTAuth:
    """增强的JWT认证器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.token_manager = TokenManager(config)
        self.redis_client: Optional[redis.Redis] = None
        self.security_context = SecurityContext()
        self.bearer = HTTPBearer()

    async def initialize(self, redis_client: Optional[redis.Redis] = None) -> None:
        """初始化认证器"""
        self.redis_client = redis_client
        await self.token_manager.initialize(redis_client)

    async def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """认证用户"""
        # 这里应该从数据库获取用户信息
        # 示例实现，实际应该查询用户表
        user_data = await self._get_user_by_username(username)
        if not user_data:
            raise AuthenticationError("Invalid credentials")

        # 验证密码
        if not self._verify_password(password, user_data['password_hash']):
            raise AuthenticationError("Invalid credentials")

        # 检查用户状态
        if not user_data.get('is_active', False):
            raise AuthenticationError("Account is disabled")

        if not user_data.get('is_verified', False):
            raise AuthenticationError("Account is not verified")

        # 检查账户锁定状态
        if user_data.get('is_locked', False):
            raise AuthenticationError("Account is locked")

        # 生成会话ID
        session_id = str(uuid.uuid4())

        # 获取用户角色和权限
        roles = user_data.get('roles', [])
        permissions = await self._get_user_permissions(user_data['id'])

        # 创建访问令牌
        access_token = await self.token_manager.create_access_token(
            user_id=user_data['id'],
            username=user_data['username'],
            email=user_data['email'],
            roles=roles,
            permissions=permissions,
            session_id=session_id
        )

        # 创建刷新令牌
        refresh_token = await self.token_manager.create_refresh_token(
            user_id=user_data['id'],
            session_id=session_id
        )

        # 记录登录事件
        await self._record_login_event(
            user_data['id'],
            session_id,
            ip_address,
            user_agent,
            "success"
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.token_manager.access_token_expire_minutes * 60,
            "session_id": session_id,
            "user": {
                "id": user_data['id'],
                "username": user_data['username'],
                "email": user_data['email'],
                "roles": roles,
                "permissions": permissions
            }
        }

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """刷新访问令牌"""
        try:
            # 验证刷新令牌
            payload = await self.token_manager.verify_token(refresh_token, TokenType.REFRESH)
            user_id = payload.get('sub')
            session_id = payload.get('session_id')

            if not user_id:
                raise AuthenticationError("Invalid refresh token")

            # 获取用户信息
            user_data = await self._get_user_by_id(user_id)
            if not user_data:
                raise AuthenticationError("User not found")

            # 检查用户状态
            if not user_data.get('is_active', False):
                raise AuthenticationError("Account is disabled")

            # 获取用户角色和权限
            roles = user_data.get('roles', [])
            permissions = await self._get_user_permissions(user_id)

            # 创建新的访问令牌
            access_token = await self.token_manager.create_access_token(
                user_id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                roles=roles,
                permissions=permissions,
                session_id=session_id
            )

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": self.token_manager.access_token_expire_minutes * 60
            }

        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Token refresh failed: {str(e)}")

    async def logout(self, token: str) -> bool:
        """用户登出"""
        try:
            # 撤销访问令牌
            await self.token_manager.revoke_token(token)

            # 记录登出事件
            payload = await self.token_manager.verify_token(token, TokenType.ACCESS)
            user_id = payload.get('sub')
            session_id = payload.get('session_id')

            if user_id and session_id:
                await self._record_logout_event(user_id, session_id, "success")

            return True

        except Exception as e:
            logging.error(f"Logout failed: {str(e)}")
            return False

    async def logout_all_sessions(self, user_id: str) -> int:
        """登出所有会话"""
        revoked_count = await self.token_manager.revoke_user_tokens(user_id)

        # 记录批量登出事件
        await self._record_logout_all_sessions_event(user_id, revoked_count)

        return revoked_count

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False

    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    async def _get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户信息"""
        # 这里应该查询数据库
        # 示例实现
        return {
            "id": "user123",
            "username": username,
            "email": f"{username}@example.com",
            "password_hash": "$2b$12$hashed_password",  # 实际应该是数据库中的哈希
            "is_active": True,
            "is_verified": True,
            "is_locked": False,
            "roles": ["user"]
        }

    async def _get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取用户信息"""
        # 这里应该查询数据库
        return {
            "id": user_id,
            "username": "testuser",
            "email": "test@example.com",
            "is_active": True,
            "is_verified": True,
            "is_locked": False,
            "roles": ["user"]
        }

    async def _get_user_permissions(self, user_id: str) -> List[str]:
        """获取用户权限"""
        # 这里应该查询权限表
        return ["read:profile", "update:profile"]

    async def _record_login_event(
        self,
        user_id: str,
        session_id: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
        status: str
    ) -> None:
        """记录登录事件"""
        if self.redis_client:
            event_data = {
                "user_id": user_id,
                "session_id": session_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.redis_client.lpush(
                f"auth_events:login:{user_id}",
                json.dumps(event_data)
            )
            # 只保留最近100次登录事件
            await self.redis_client.ltrim(f"auth_events:login:{user_id}", 0, 99)

    async def _record_logout_event(self, user_id: str, session_id: str, status: str) -> None:
        """记录登出事件"""
        if self.redis_client:
            event_data = {
                "user_id": user_id,
                "session_id": session_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.redis_client.lpush(
                f"auth_events:logout:{user_id}",
                json.dumps(event_data)
            )
            await self.redis_client.ltrim(f"auth_events:logout:{user_id}", 0, 99)

    async def _record_logout_all_sessions_event(self, user_id: str, revoked_count: int) -> None:
        """记录批量登出事件"""
        if self.redis_client:
            event_data = {
                "user_id": user_id,
                "revoked_count": revoked_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.redis_client.lpush(
                f"auth_events:logout_all:{user_id}",
                json.dumps(event_data)
            )

class AuthMiddleware:
    """认证中间件"""

    def __init__(self, auth: EnhancedJWTAuth):
        self.auth = auth

    async def __call__(
        self,
        request: Request,
        call_next: Callable
    ) -> Any:
        """中间件处理"""
        try:
            # 提取认证头
            authorization = request.headers.get("Authorization")
            if not authorization:
                # 跳过认证的路径
                if self._should_skip_auth(request.url.path):
                    return await call_next(request)
                else:
                    raise HTTPException(
                        status_code=401,
                        detail="Not authenticated",
                        headers={"WWW-Authenticate": "Bearer"}
                    )

            # 解析Bearer令牌
            if not authorization.startswith("Bearer "):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authorization header format"
                )

            token = authorization.split(" ")[1]

            # 验证令牌
            payload = await self.auth.token_manager.verify_token(token, TokenType.ACCESS)

            # 创建安全上下文
            security_context = SecurityContext.from_token(payload)
            security_context.ip_address = request.client.host if request.client else None
            security_context.user_agent = request.headers.get("User-Agent")
            security_context.auth_method = "jwt"

            # 将安全上下文添加到请求状态
            request.state.security_context = security_context

            return await call_next(request)

        except AuthenticationError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            logging.error(f"Authentication middleware error: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication failed")

    def _should_skip_auth(self, path: str) -> bool:
        """检查是否应该跳过认证"""
        skip_paths = [
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/verify-email",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
            "/docs",
            "/openapi.json"
        ]
        return any(path.startswith(skip_path) for skip_path in skip_paths)

# 权限检查装饰器
def require_permissions(required_permissions: Union[str, List[str]]):
    """权限检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从请求中获取安全上下文
            request = None
            for arg in args:
                if hasattr(arg, 'state') and hasattr(arg.state, 'security_context'):
                    request = arg
                    break

            if not request:
                raise HTTPException(
                    status_code=500,
                    detail="Security context not available"
                )

            security_context = request.state.security_context

            if not security_context.is_authenticated:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )

            # 检查权限
            if isinstance(required_permissions, str):
                required_permissions = [required_permissions]

            if not all(perm in security_context.permissions for perm in required_permissions):
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions. Required: {', '.join(required_permissions)}"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator

def require_roles(required_roles: Union[str, List[str]]):
    """角色检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从请求中获取安全上下文
            request = None
            for arg in args:
                if hasattr(arg, 'state') and hasattr(arg.state, 'security_context'):
                    request = arg
                    break

            if not request:
                raise HTTPException(
                    status_code=500,
                    detail="Security context not available"
                )

            security_context = request.state.security_context

            if not security_context.is_authenticated:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required"
                )

            # 检查角色
            if isinstance(required_roles, str):
                required_roles = [required_roles]

            if not any(role in security_context.roles for role in required_roles):
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient roles. Required one of: {', '.join(required_roles)}"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator

# FastAPI依赖项
async def get_current_user(request: Request) -> SecurityContext:
    """获取当前用户"""
    if not hasattr(request.state, 'security_context'):
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    return request.state.security_context

async def get_current_active_user(current_user: SecurityContext = Depends(get_current_user)) -> SecurityContext:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Inactive user"
        )
    return current_user

async def get_current_verified_user(current_user: SecurityContext = Depends(get_current_active_user)) -> SecurityContext:
    """获取当前已验证用户"""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="Email not verified"
        )
    return current_user