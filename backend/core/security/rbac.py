"""
基于角色的访问控制(RBAC)
Week 6 Day 4: 安全加固和权限配置

提供完整的角色权限管理体系
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import redis
import logging
from fastapi import HTTPException, Request

class PermissionType(Enum):
    """权限类型"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"

class ResourceType(Enum):
    """资源类型"""
    USER = "user"
    ORGANIZATION = "organization"
    API_KEY = "api_key"
    BILLING = "billing"
    AUDIT_LOG = "audit_log"
    SYSTEM_CONFIG = "system_config"

@dataclass
class Permission:
    """权限"""
    id: str
    name: str
    description: str
    resource_type: ResourceType
    action: PermissionType
    scope: str = "*"  # 作用域，*表示所有
    conditions: Dict[str, Any] = None  # 权限条件

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "resource_type": self.resource_type.value,
            "action": self.action.value,
            "scope": self.scope,
            "conditions": self.conditions or {}
        }

    def __str__(self) -> str:
        return f"{self.action.value}:{self.resource_type.value}:{self.scope}"

@dataclass
class Role:
    """角色"""
    id: str
    name: str
    description: str
    permissions: List[str]  # 权限ID列表
    is_system_role: bool = False
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions,
            "is_system_role": self.is_system_role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

@dataclass
class RoleAssignment:
    """角色分配"""
    id: str
    user_id: str
    role_id: str
    resource_id: Optional[str] = None  # 特定资源ID，为空表示全局角色
    assigned_by: str
    assigned_at: datetime = None
    expires_at: Optional[datetime] = None
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "resource_id": self.resource_id,
            "assigned_by": self.assigned_by,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active
        }

class PermissionChecker:
    """权限检查器"""

    def __init__(self, rbac_manager: 'RBACManager'):
        self.rbac_manager = rbac_manager

    async def has_permission(
        self,
        user_id: str,
        action: PermissionType,
        resource_type: ResourceType,
        resource_id: Optional[str] = None,
        scope: str = "*",
        context: Dict[str, Any] = None
    ) -> bool:
        """检查用户是否有指定权限"""
        try:
            # 获取用户的所有有效权限
            user_permissions = await self.rbac_manager.get_user_permissions(user_id, resource_id)

            # 检查是否有匹配的权限
            for permission in user_permissions:
                if self._matches_permission(
                    permission, action, resource_type, resource_id, scope, context
                ):
                    return True

            return False

        except Exception as e:
            logging.error(f"Permission check failed: {str(e)}")
            return False

    async def has_role(
        self,
        user_id: str,
        role_name: str,
        resource_id: Optional[str] = None
    ) -> bool:
        """检查用户是否有指定角色"""
        try:
            return await self.rbac_manager.user_has_role(user_id, role_name, resource_id)
        except Exception as e:
            logging.error(f"Role check failed: {str(e)}")
            return False

    async def has_any_permission(
        self,
        user_id: str,
        required_permissions: List[Tuple[PermissionType, ResourceType, str]],
        resource_id: Optional[str] = None,
        context: Dict[str, Any] = None
    ) -> bool:
        """检查用户是否有任意一个所需权限"""
        for action, resource_type, scope in required_permissions:
            if await self.has_permission(
                user_id, action, resource_type, resource_id, scope, context
            ):
                return True
        return False

    async def has_all_permissions(
        self,
        user_id: str,
        required_permissions: List[Tuple[PermissionType, ResourceType, str]],
        resource_id: Optional[str] = None,
        context: Dict[str, Any] = None
    ) -> bool:
        """检查用户是否拥有所有所需权限"""
        for action, resource_type, scope in required_permissions:
            if not await self.has_permission(
                user_id, action, resource_type, resource_id, scope, context
            ):
                return False
        return True

    def _matches_permission(
        self,
        permission: Permission,
        required_action: PermissionType,
        required_resource_type: ResourceType,
        resource_id: Optional[str],
        required_scope: str,
        context: Dict[str, Any] = None
    ) -> bool:
        """检查权限是否匹配"""
        # 检查动作
        if permission.action != required_action and permission.action != PermissionType.ADMIN:
            return False

        # 检查资源类型
        if permission.resource_type != required_resource_type:
            return False

        # 检查作用域
        if not self._matches_scope(permission.scope, required_scope, resource_id):
            return False

        # 检查条件
        if permission.conditions and not self._evaluate_conditions(
            permission.conditions, context, resource_id
        ):
            return False

        return True

    def _matches_scope(self, permission_scope: str, required_scope: str, resource_id: Optional[str]) -> bool:
        """检查作用域是否匹配"""
        # 通配符匹配
        if permission_scope == "*":
            return True

        # 精确匹配
        if permission_scope == required_scope:
            return True

        # 资源ID匹配
        if resource_id and permission_scope == f"resource:{resource_id}":
            return True

        return False

    def _evaluate_conditions(
        self,
        conditions: Dict[str, Any],
        context: Dict[str, Any],
        resource_id: Optional[str]
    ) -> bool:
        """评估权限条件"""
        if not conditions:
            return True

        if not context:
            return False

        # 时间条件
        if "time_range" in conditions:
            time_range = conditions["time_range"]
            current_time = datetime.now().time()
            start_time = datetime.strptime(time_range["start"], "%H:%M").time()
            end_time = datetime.strptime(time_range["end"], "%H:%M").time()

            if not (start_time <= current_time <= end_time):
                return False

        # IP地址条件
        if "allowed_ips" in conditions:
            client_ip = context.get("ip_address")
            if client_ip not in conditions["allowed_ips"]:
                return False

        # 用户属性条件
        if "user_attributes" in conditions:
            user_attrs = conditions["user_attributes"]
            for attr, expected_value in user_attrs.items():
                if context.get(f"user_{attr}") != expected_value:
                    return False

        return True

class RBACManager:
    """RBAC管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.permission_checker = PermissionChecker(self)

        # 缓存
        self._permissions_cache: Dict[str, Permission] = {}
        self._roles_cache: Dict[str, Role] = {}
        self._user_permissions_cache: Dict[str, List[Permission]] = {}
        self._cache_ttl = config.get('cache_ttl', 300)  # 5分钟

    async def initialize(self, redis_client: Optional[redis.Redis] = None) -> None:
        """初始化RBAC管理器"""
        self.redis_client = redis_client

        # 初始化系统权限和角色
        await self._initialize_system_permissions()
        await self._initialize_system_roles()

    async def create_permission(
        self,
        name: str,
        description: str,
        resource_type: ResourceType,
        action: PermissionType,
        scope: str = "*",
        conditions: Dict[str, Any] = None
    ) -> Permission:
        """创建权限"""
        permission = Permission(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            resource_type=resource_type,
            action=action,
            scope=scope,
            conditions=conditions
        )

        # 存储到Redis
        if self.redis_client:
            await self._store_permission(permission)

        # 更新缓存
        self._permissions_cache[permission.id] = permission

        return permission

    async def create_role(
        self,
        name: str,
        description: str,
        permissions: List[str],
        is_system_role: bool = False
    ) -> Role:
        """创建角色"""
        role = Role(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            permissions=permissions,
            is_system_role=is_system_role,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # 存储到Redis
        if self.redis_client:
            await self._store_role(role)

        # 更新缓存
        self._roles_cache[role.id] = role

        return role

    async def assign_role(
        self,
        user_id: str,
        role_id: str,
        assigned_by: str,
        resource_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> RoleAssignment:
        """分配角色给用户"""
        assignment = RoleAssignment(
            id=str(uuid.uuid4()),
            user_id=user_id,
            role_id=role_id,
            resource_id=resource_id,
            assigned_by=assigned_by,
            assigned_at=datetime.utcnow(),
            expires_at=expires_at
        )

        # 存储到Redis
        if self.redis_client:
            await self._store_role_assignment(assignment)

        # 清除用户权限缓存
        self._clear_user_permissions_cache(user_id)

        return assignment

    async def revoke_role(self, user_id: str, role_id: str, resource_id: Optional[str] = None) -> bool:
        """撤销用户角色"""
        if not self.redis_client:
            return False

        # 查找角色分配
        assignments = await self._get_user_role_assignments(user_id)
        for assignment in assignments:
            if (assignment.role_id == role_id and
                assignment.resource_id == resource_id and
                assignment.is_active):

                # 标记为非活跃
                assignment.is_active = False
                await self._store_role_assignment(assignment)

                # 清除缓存
                self._clear_user_permissions_cache(user_id)
                return True

        return False

    async def get_user_permissions(
        self,
        user_id: str,
        resource_id: Optional[str] = None
    ) -> List[Permission]:
        """获取用户权限"""
        cache_key = f"{user_id}:{resource_id or 'global'}"

        # 检查缓存
        if cache_key in self._user_permissions_cache:
            cached_time = self._user_permissions_cache[f"{cache_key}_time"]
            if (datetime.now() - cached_time).seconds < self._cache_ttl:
                return self._user_permissions_cache[cache_key]

        permissions = []

        # 获取用户的所有角色分配
        assignments = await self._get_user_role_assignments(user_id)

        for assignment in assignments:
            if not assignment.is_active:
                continue

            # 检查是否过期
            if assignment.expires_at and datetime.utcnow() > assignment.expires_at:
                continue

            # 检查资源匹配
            if resource_id and assignment.resource_id and assignment.resource_id != resource_id:
                continue

            # 获取角色信息
            role = await self._get_role_by_id(assignment.role_id)
            if not role or not role.is_active:
                continue

            # 获取角色的权限
            for permission_id in role.permissions:
                permission = await self._get_permission_by_id(permission_id)
                if permission:
                    permissions.append(permission)

        # 缓存结果
        self._user_permissions_cache[cache_key] = permissions
        self._user_permissions_cache[f"{cache_key}_time"] = datetime.now()

        return permissions

    async def user_has_role(
        self,
        user_id: str,
        role_name: str,
        resource_id: Optional[str] = None
    ) -> bool:
        """检查用户是否拥有指定角色"""
        assignments = await self._get_user_role_assignments(user_id)

        for assignment in assignments:
            if not assignment.is_active:
                continue

            # 检查是否过期
            if assignment.expires_at and datetime.utcnow() > assignment.expires_at:
                continue

            # 检查资源匹配
            if resource_id and assignment.resource_id and assignment.resource_id != resource_id:
                continue

            # 获取角色信息
            role = await self._get_role_by_id(assignment.role_id)
            if role and role.is_active and role.name == role_name:
                return True

        return False

    async def get_all_permissions(self) -> List[Permission]:
        """获取所有权限"""
        if not self.redis_client:
            return list(self._permissions_cache.values())

        # 从Redis获取
        permission_ids = await self.redis_client.smembers("permissions:all")
        permissions = []

        for permission_id in permission_ids:
            permission = await self._get_permission_by_id(permission_id)
            if permission:
                permissions.append(permission)

        return permissions

    async def get_all_roles(self) -> List[Role]:
        """获取所有角色"""
        if not self.redis_client:
            return list(self._roles_cache.values())

        # 从Redis获取
        role_ids = await self.redis_client.smembers("roles:all")
        roles = []

        for role_id in role_ids:
            role = await self._get_role_by_id(role_id)
            if role:
                roles.append(role)

        return roles

    async def get_user_roles(self, user_id: str) -> List[Role]:
        """获取用户角色"""
        assignments = await self._get_user_role_assignments(user_id)
        roles = []

        for assignment in assignments:
            if not assignment.is_active:
                continue

            # 检查是否过期
            if assignment.expires_at and datetime.utcnow() > assignment.expires_at:
                continue

            role = await self._get_role_by_id(assignment.role_id)
            if role and role.is_active:
                roles.append(role)

        return roles

    async def _initialize_system_permissions(self) -> None:
        """初始化系统权限"""
        system_permissions = [
            # 用户权限
            ("read:own_profile", "读取个人资料", ResourceType.USER, PermissionType.READ, "own"),
            ("update:own_profile", "更新个人资料", ResourceType.USER, PermissionType.WRITE, "own"),
            ("read:users", "读取用户列表", ResourceType.USER, PermissionType.READ, "*"),
            ("create:users", "创建用户", ResourceType.USER, PermissionType.WRITE, "*"),
            ("update:users", "更新用户", ResourceType.USER, PermissionType.WRITE, "*"),
            ("delete:users", "删除用户", ResourceType.USER, PermissionType.DELETE, "*"),

            # 组织权限
            ("read:own_organization", "读取自己的组织", ResourceType.ORGANIZATION, PermissionType.READ, "own"),
            ("update:own_organization", "更新自己的组织", ResourceType.ORGANIZATION, PermissionType.WRITE, "own"),
            ("read:organizations", "读取组织列表", ResourceType.ORGANIZATION, PermissionType.READ, "*"),
            ("create:organizations", "创建组织", ResourceType.ORGANIZATION, PermissionType.WRITE, "*"),
            ("update:organizations", "更新组织", ResourceType.ORGANIZATION, PermissionType.WRITE, "*"),
            ("delete:organizations", "删除组织", ResourceType.ORGANIZATION, PermissionType.DELETE, "*"),

            # API密钥权限
            ("read:own_api_keys", "读取自己的API密钥", ResourceType.API_KEY, PermissionType.READ, "own"),
            ("create:own_api_keys", "创建自己的API密钥", ResourceType.API_KEY, PermissionType.WRITE, "own"),
            ("update:own_api_keys", "更新自己的API密钥", ResourceType.API_KEY, PermissionType.WRITE, "own"),
            ("delete:own_api_keys", "删除自己的API密钥", ResourceType.API_KEY, PermissionType.DELETE, "own"),
            ("read:api_keys", "读取所有API密钥", ResourceType.API_KEY, PermissionType.READ, "*"),
            ("manage:api_keys", "管理所有API密钥", ResourceType.API_KEY, PermissionType.ADMIN, "*"),

            # 计费权限
            ("read:own_billing", "读取自己的账单", ResourceType.BILLING, PermissionType.READ, "own"),
            ("read:billing", "读取所有账单", ResourceType.BILLING, PermissionType.READ, "*"),
            ("manage:billing", "管理计费", ResourceType.BILLING, PermissionType.ADMIN, "*"),

            # 审计日志权限
            ("read:audit_logs", "读取审计日志", ResourceType.AUDIT_LOG, PermissionType.READ, "*"),

            # 系统配置权限
            ("read:system_config", "读取系统配置", ResourceType.SYSTEM_CONFIG, PermissionType.READ, "*"),
            ("update:system_config", "更新系统配置", ResourceType.SYSTEM_CONFIG, PermissionType.WRITE, "*"),
            ("admin:system", "系统管理员", ResourceType.SYSTEM_CONFIG, PermissionType.ADMIN, "*"),
        ]

        for name, desc, resource_type, action, scope in system_permissions:
            # 检查权限是否已存在
            if not await self._permission_exists(name):
                await self.create_permission(name, desc, resource_type, action, scope)

    async def _initialize_system_roles(self) -> None:
        """初始化系统角色"""
        # 获取所有权限
        all_permissions = await self.get_all_permissions()
        permission_map = {p.name: p.id for p in all_permissions}

        system_roles = [
            # 普通用户
            ("user", "普通用户", [
                "read:own_profile",
                "update:own_profile",
                "read:own_organization",
                "update:own_organization",
                "read:own_api_keys",
                "create:own_api_keys",
                "update:own_api_keys",
                "delete:own_api_keys",
                "read:own_billing"
            ]),

            # 组织管理员
            ("organization_admin", "组织管理员", [
                "read:own_profile",
                "update:own_profile",
                "read:own_organization",
                "update:own_organization",
                "read:users",
                "create:users",
                "update:users",
                "read:own_api_keys",
                "create:own_api_keys",
                "update:own_api_keys",
                "delete:own_api_keys",
                "read:api_keys",
                "read:own_billing",
                "read:billing"
            ]),

            # 系统管理员
            ("system_admin", "系统管理员", [
                "read:users",
                "create:users",
                "update:users",
                "delete:users",
                "read:organizations",
                "create:organizations",
                "update:organizations",
                "delete:organizations",
                "read:api_keys",
                "manage:api_keys",
                "read:billing",
                "manage:billing",
                "read:audit_logs",
                "read:system_config",
                "update:system_config",
                "admin:system"
            ]),

            # 只读用户
            ("readonly", "只读用户", [
                "read:own_profile",
                "read:own_organization",
                "read:own_api_keys",
                "read:own_billing"
            ])
        ]

        for role_name, description, permission_names in system_roles:
            # 检查角色是否已存在
            if not await self._role_exists(role_name):
                permission_ids = [permission_map.get(name) for name in permission_names if name in permission_map]
                await self.create_role(role_name, description, permission_ids, is_system_role=True)

    async def _store_permission(self, permission: Permission) -> None:
        """存储权限到Redis"""
        if not self.redis_client:
            return

        key = f"permission:{permission.id}"
        await self.redis_client.hset(key, mapping={
            "id": permission.id,
            "name": permission.name,
            "description": permission.description,
            "resource_type": permission.resource_type.value,
            "action": permission.action.value,
            "scope": permission.scope,
            "conditions": json.dumps(permission.conditions or {})
        })
        await self.redis_client.sadd("permissions:all", permission.id)

    async def _store_role(self, role: Role) -> None:
        """存储角色到Redis"""
        if not self.redis_client:
            return

        key = f"role:{role.id}"
        await self.redis_client.hset(key, mapping={
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "permissions": ",".join(role.permissions),
            "is_system_role": str(role.is_system_role),
            "is_active": str(role.is_active),
            "created_at": role.created_at.isoformat() if role.created_at else "",
            "updated_at": role.updated_at.isoformat() if role.updated_at else ""
        })
        await self.redis_client.sadd("roles:all", role.id)

    async def _store_role_assignment(self, assignment: RoleAssignment) -> None:
        """存储角色分配到Redis"""
        if not self.redis_client:
            return

        key = f"role_assignment:{assignment.id}"
        await self.redis_client.hset(key, mapping={
            "id": assignment.id,
            "user_id": assignment.user_id,
            "role_id": assignment.role_id,
            "resource_id": assignment.resource_id or "",
            "assigned_by": assignment.assigned_by,
            "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else "",
            "expires_at": assignment.expires_at.isoformat() if assignment.expires_at else "",
            "is_active": str(assignment.is_active)
        })
        await self.redis_client.sadd(f"user_role_assignments:{assignment.user_id}", assignment.id)

    async def _get_permission_by_id(self, permission_id: str) -> Optional[Permission]:
        """根据ID获取权限"""
        # 检查缓存
        if permission_id in self._permissions_cache:
            return self._permissions_cache[permission_id]

        if not self.redis_client:
            return None

        data = await self.redis_client.hgetall(f"permission:{permission_id}")
        if not data:
            return None

        permission = Permission(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            resource_type=ResourceType(data["resource_type"]),
            action=PermissionType(data["action"]),
            scope=data["scope"],
            conditions=json.loads(data.get("conditions", "{}"))
        )

        # 更新缓存
        self._permissions_cache[permission_id] = permission
        return permission

    async def _get_role_by_id(self, role_id: str) -> Optional[Role]:
        """根据ID获取角色"""
        # 检查缓存
        if role_id in self._roles_cache:
            return self._roles_cache[role_id]

        if not self.redis_client:
            return None

        data = await self.redis_client.hgetall(f"role:{role_id}")
        if not data:
            return None

        role = Role(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            permissions=data.get("permissions", "").split(",") if data.get("permissions") else [],
            is_system_role=data.get("is_system_role") == "True",
            is_active=data.get("is_active") == "True",
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
        )

        # 更新缓存
        self._roles_cache[role_id] = role
        return role

    async def _get_user_role_assignments(self, user_id: str) -> List[RoleAssignment]:
        """获取用户的角色分配"""
        if not self.redis_client:
            return []

        assignment_ids = await self.redis_client.smembers(f"user_role_assignments:{user_id}")
        assignments = []

        for assignment_id in assignment_ids:
            data = await self.redis_client.hgetall(f"role_assignment:{assignment_id}")
            if data:
                assignment = RoleAssignment(
                    id=data["id"],
                    user_id=data["user_id"],
                    role_id=data["role_id"],
                    resource_id=data.get("resource_id") or None,
                    assigned_by=data["assigned_by"],
                    assigned_at=datetime.fromisoformat(data["assigned_at"]) if data.get("assigned_at") else None,
                    expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
                    is_active=data.get("is_active") == "True"
                )
                assignments.append(assignment)

        return assignments

    async def _permission_exists(self, name: str) -> bool:
        """检查权限是否存在"""
        if not self.redis_client:
            return any(p.name == name for p in self._permissions_cache.values())

        # 在Redis中查找
        for permission_id in await self.redis_client.smembers("permissions:all"):
            permission = await self._get_permission_by_id(permission_id)
            if permission and permission.name == name:
                return True
        return False

    async def _role_exists(self, name: str) -> bool:
        """检查角色是否存在"""
        if not self.redis_client:
            return any(r.name == name for r in self._roles_cache.values())

        # 在Redis中查找
        for role_id in await self.redis_client.smembers("roles:all"):
            role = await self._get_role_by_id(role_id)
            if role and role.name == name:
                return True
        return False

    def _clear_user_permissions_cache(self, user_id: str) -> None:
        """清除用户权限缓存"""
        keys_to_remove = [key for key in self._user_permissions_cache.keys() if key.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            del self._user_permissions_cache[key]

# 导入uuid
import uuid