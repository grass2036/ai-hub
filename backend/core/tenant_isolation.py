"""
租户隔离机制
实现多租户架构下的数据隔离和权限控制
"""

from typing import Optional, Dict, Any, List, Callable
from functools import wraps
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, Security, status
import threading
from contextvars import ContextVar

from backend.models.tenant import Tenant, TenantUser, Team, TeamMember
from backend.core.database import get_db

# 上下文变量用于存储当前租户信息
current_tenant_id: ContextVar[Optional[str]] = ContextVar('current_tenant_id', default=None)
current_user_id: ContextVar[Optional[str]] = ContextVar('current_user_id', default=None)
current_user_role: ContextVar[Optional[str]] = ContextVar('current_user_role', default=None)

class TenantContext:
    """租户上下文管理器"""

    def __init__(self, tenant_id: str, user_id: str, user_role: str):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.user_role = user_role
        self.token = None

    def __enter__(self):
        self.token = current_tenant_id.set(self.tenant_id)
        current_user_id.set(self.user_id)
        current_user_role.set(self.user_role)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            current_tenant_id.reset(self.token)
            current_user_id.set(None)
            current_user_role.set(None)

@contextmanager
def tenant_context(tenant_id: str, user_id: str, user_role: str):
    """租户上下文管理器"""
    with TenantContext(tenant_id, user_id, user_role):
        yield

def get_current_tenant_id() -> Optional[str]:
    """获取当前租户ID"""
    return current_tenant_id.get()

def get_current_user_id() -> Optional[str]:
    """获取当前用户ID"""
    return current_user_id.get()

def get_current_user_role() -> Optional[str]:
    """获取当前用户角色"""
    return current_user_role.get()

class TenantIsolationMiddleware:
    """租户隔离中间件"""

    def __init__(self):
        self.thread_local = threading.local()

    def set_tenant_context(self, tenant_id: str, user_id: str, user_role: str):
        """设置租户上下文"""
        self.thread_local.tenant_id = tenant_id
        self.thread_local.user_id = user_id
        self.thread_local.user_role = user_role

    def get_tenant_context(self) -> tuple:
        """获取租户上下文"""
        return (
            getattr(self.thread_local, 'tenant_id', None),
            getattr(self.thread_local, 'user_id', None),
            getattr(self.thread_local, 'user_role', None)
        )

    def clear_tenant_context(self):
        """清除租户上下文"""
        self.thread_local.__dict__.clear()

# 全局租户隔离中间件实例
tenant_isolation = TenantIsolationMiddleware()

def require_tenant(func: Callable):
    """装饰器：要求租户上下文"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="租户上下文未设置"
            )
        return func(*args, **kwargs)
    return wrapper

def require_tenant_role(required_roles: List[str]):
    """装饰器：要求特定租户角色"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_role = get_current_user_role()
            tenant_id = get_current_tenant_id()

            if not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="租户上下文未设置"
                )

            if user_role not in required_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"需要以下角色之一: {', '.join(required_roles)}"
                )

            return func(*args, **kwargs)
        return wrapper
    return decorator

class TenantDataFilter:
    """租户数据过滤器"""

    @staticmethod
    def filter_by_tenant(query_model, tenant_id: str = None):
        """为查询添加租户过滤条件"""
        if tenant_id is None:
            tenant_id = get_current_tenant_id()

        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="租户上下文未设置"
            )

        # 根据模型类型添加不同的过滤条件
        if hasattr(query_model, 'tenant_id'):
            return query_model.tenant_id == tenant_id
        elif hasattr(query_model, 'organization_id'):
            return query_model.organization_id == tenant_id
        else:
            # 对于没有直接租户字段的模型，需要特殊处理
            return None

    @staticmethod
    def apply_tenant_filter(query, db: Session, model_class):
        """应用租户过滤到查询"""
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="租户上下文未设置"
            )

        # 检查模型是否有租户字段
        if hasattr(model_class, 'tenant_id'):
            query = query.filter(model_class.tenant_id == tenant_id)
        elif hasattr(model_class, 'organization_id'):
            query = query.filter(model_class.organization_id == tenant_id)

        return query

class TenantPermissionChecker:
    """租户权限检查器"""

    def __init__(self, db: Session):
        self.db = db

    def check_user_tenant_access(self, user_id: str, tenant_id: str) -> bool:
        """检查用户是否有租户访问权限"""
        tenant_user = self.db.query(TenantUser).filter(
            and_(
                TenantUser.user_id == user_id,
                TenantUser.tenant_id == tenant_id,
                TenantUser.is_active == True
            )
        ).first()

        return tenant_user is not None

    def check_user_team_access(self, user_id: str, team_id: str) -> bool:
        """检查用户是否有团队访问权限"""
        team_member = self.db.query(TeamMember).filter(
            and_(
                TeamMember.user_id == user_id,
                TeamMember.team_id == team_id,
                TeamMember.is_active == True
            )
        ).first()

        return team_member is not None

    def get_user_tenants(self, user_id: str) -> List[Tenant]:
        """获取用户可访问的租户列表"""
        tenant_users = self.db.query(TenantUser).filter(
            and_(
                TenantUser.user_id == user_id,
                TenantUser.is_active == True
            )
        ).all()

        tenant_ids = [tu.tenant_id for tu in tenant_users]

        if not tenant_ids:
            return []

        return self.db.query(Tenant).filter(
            and_(
                Tenant.id.in_(tenant_ids),
                Tenant.status.in_(['active', 'trial'])
            )
        ).all()

    def get_user_teams(self, user_id: str, tenant_id: str = None) -> List[Team]:
        """获取用户可访问的团队列表"""
        query = self.db.query(Team).join(TeamMember).filter(
            and_(
                TeamMember.user_id == user_id,
                TeamMember.is_active == True,
                Team.is_active == True
            )
        )

        if tenant_id:
            query = query.filter(Team.tenant_id == tenant_id)

        return query.all()

    def check_permission(self, user_id: str, tenant_id: str, permission: str) -> bool:
        """检查用户在租户中的特定权限"""
        tenant_user = self.db.query(TenantUser).filter(
            and_(
                TenantUser.user_id == user_id,
                TenantUser.tenant_id == tenant_id,
                TenantUser.is_active == True
            )
        ).first()

        if not tenant_user:
            return False

        # 所有者和管理员拥有所有权限
        if tenant_user.role in ['owner', 'admin']:
            return True

        # 检查特定权限
        permissions = tenant_user.permissions or []
        return permission in permissions

class TenantQuotaManager:
    """租户配额管理器"""

    def __init__(self, db: Session):
        self.db = db

    def check_quota(self, tenant_id: str, quota_type: str, additional_amount: int = 0) -> tuple[bool, Dict[str, Any]]:
        """检查租户配额"""
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return False, {"error": "租户不存在"}

        quotas = tenant.quotas or {}
        max_limit = quotas.get(quota_type)

        if max_limit is None:  # 无限制
            return True, {"limit": None, "current": 0, "available": None}

        # 获取当前使用量
        current_usage = self.get_current_usage(tenant_id, quota_type)

        # 检查是否超出配额
        available = max_limit - current_usage
        can_add = available >= additional_amount

        return can_add, {
            "limit": max_limit,
            "current": current_usage,
            "available": available,
            "requested": additional_amount
        }

    def get_current_usage(self, tenant_id: str, quota_type: str) -> int:
        """获取当前配额使用量"""
        if quota_type == "max_users":
            return self.db.query(TenantUser).filter(
                and_(
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.is_active == True
                )
            ).count()

        elif quota_type == "max_teams":
            return self.db.query(Team).filter(
                and_(
                    Team.tenant_id == tenant_id,
                    Team.is_active == True
                )
            ).count()

        elif quota_type == "max_api_keys":
            # 这里需要根据实际的API密钥模型来计算
            # 暂时返回0
            return 0

        elif quota_type == "monthly_api_calls":
            # 这里需要根据使用记录来计算
            # 暂时返回0
            return 0

        # 其他配额类型的处理
        return 0

    def update_quota_usage(self, tenant_id: str, quota_type: str, delta: int):
        """更新配额使用量"""
        # 这里可以实现配额使用的缓存机制
        pass

class TenantService:
    """租户服务"""

    def __init__(self, db: Session):
        self.db = db
        self.permission_checker = TenantPermissionChecker(db)
        self.quota_manager = TenantQuotaManager(db)

    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """根据slug获取租户"""
        return self.db.query(Tenant).filter(
            and_(
                Tenant.slug == slug,
                Tenant.status.in_(['active', 'trial'])
            )
        ).first()

    def get_tenant_by_domain(self, domain: str) -> Optional[Tenant]:
        """根据域名获取租户"""
        return self.db.query(Tenant).filter(
            and_(
                Tenant.domain == domain,
                Tenant.status.in_(['active', 'trial'])
            )
        ).first()

    def validate_tenant_access(self, user_id: str, tenant_slug: str = None, tenant_domain: str = None) -> Optional[Tenant]:
        """验证用户对租户的访问权限"""
        tenant = None

        if tenant_slug:
            tenant = self.get_tenant_by_slug(tenant_slug)
        elif tenant_domain:
            tenant = self.get_tenant_by_domain(tenant_domain)

        if not tenant:
            return None

        # 检查用户是否有访问权限
        if not self.permission_checker.check_user_tenant_access(user_id, tenant.id):
            return None

        return tenant

    def get_tenant_users(self, tenant_id: str, include_inactive: bool = False) -> List[TenantUser]:
        """获取租户用户列表"""
        query = self.db.query(TenantUser).filter(TenantUser.tenant_id == tenant_id)

        if not include_inactive:
            query = query.filter(TenantUser.is_active == True)

        return query.all()

    def get_tenant_teams(self, tenant_id: str, include_inactive: bool = False) -> List[Team]:
        """获取租户团队列表"""
        query = self.db.query(Team).filter(Team.tenant_id == tenant_id)

        if not include_inactive:
            query = query.filter(Team.is_active == True)

        return query.all()

    def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        """获取租户统计信息"""
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return {}

        return {
            "user_count": self.db.query(TenantUser).filter(
                and_(TenantUser.tenant_id == tenant_id, TenantUser.is_active == True)
            ).count(),
            "team_count": self.db.query(Team).filter(
                and_(Team.tenant_id == tenant_id, Team.is_active == True)
            ).count(),
            "api_key_count": 0,  # 需要根据实际模型实现
            "created_at": tenant.created_at,
            "plan": tenant.plan,
            "status": tenant.status,
            "quotas": tenant.quotas or {}
        }

# 依赖注入函数

def get_tenant_service(db: Session = Depends(get_db)) -> TenantService:
    """获取租户服务实例"""
    return TenantService(db)

def validate_tenant_access(tenant_slug: str = None, tenant_domain: str = None):
    """装饰器：验证租户访问权限"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = get_current_user_id()
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="用户未认证"
                )

            db = next(get_db())
            tenant_service = TenantService(db)

            tenant = tenant_service.validate_tenant_access(
                user_id=user_id,
                tenant_slug=tenant_slug,
                tenant_domain=tenant_domain
            )

            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无租户访问权限"
                )

            # 设置租户上下文
            tenant_user = db.query(TenantUser).filter(
                and_(
                    TenantUser.user_id == user_id,
                    TenantUser.tenant_id == tenant.id,
                    TenantUser.is_active == True
                )
            ).first()

            if tenant_user:
                with tenant_context(tenant.id, user_id, tenant_user.role):
                    return func(*args, **kwargs)
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="用户不在租户中"
                )

        return wrapper
    return decorator

# FastAPI依赖

async def get_current_tenant(
    tenant_slug: str = None,
    tenant_domain: str = None,
    db: Session = Depends(get_db)
) -> Tenant:
    """获取当前租户"""
    user_id = get_current_user_id()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户未认证"
        )

    tenant_service = TenantService(db)
    tenant = tenant_service.validate_tenant_access(
        user_id=user_id,
        tenant_slug=tenant_slug,
        tenant_domain=tenant_domain
    )

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无租户访问权限"
        )

    return tenant

async def get_current_tenant_user(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
) -> TenantUser:
    """获取当前租户用户"""
    user_id = get_current_user_id()

    tenant_user = db.query(TenantUser).filter(
        and_(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant.id,
            TenantUser.is_active == True
        )
    ).first()

    if not tenant_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户不在租户中"
        )

    return tenant_user