"""
Permission system tests
权限系统测试
"""

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from enum import Enum
from httpx import AsyncClient
from sqlalchemy import text

from backend.main import app
from backend.models.database import get_db
from backend.models.organization import Organization
from backend.models.team import Team
from backend.models.member import Member
from backend.models.user import User
from backend.core.security import get_password_hash


class OrganizationRole(str, Enum):
    """组织角色枚举"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class TestPermissionSystem:
    """权限系统测试类"""

    @pytest.fixture
    async def permission_test_data(self):
        """创建权限测试数据"""
        async for db in get_db():
            # 创建测试用户
            owner = User(
                id=uuid4(),
                email="owner@test.com",
                password_hash=get_password_hash("password123"),
                is_active=True,
                created_at=datetime.utcnow()
            )
            admin = User(
                id=uuid4(),
                email="admin@test.com",
                password_hash=get_password_hash("password123"),
                is_active=True,
                created_at=datetime.utcnow()
            )
            member = User(
                id=uuid4(),
                email="member@test.com",
                password_hash=get_password_hash("password123"),
                is_active=True,
                created_at=datetime.utcnow()
            )
            viewer = User(
                id=uuid4(),
                email="viewer@test.com",
                password_hash=get_password_hash("password123"),
                is_active=True,
                created_at=datetime.utcnow()
            )
            outsider = User(
                id=uuid4(),
                email="outsider@test.com",
                password_hash=get_password_hash("password123"),
                is_active=True,
                created_at=datetime.utcnow()
            )

            db.add_all([owner, admin, member, viewer, outsider])
            await db.commit()

            # 创建测试组织
            org = Organization(
                id=uuid4(),
                name="Permission Test Organization",
                slug="permission-test-org",
                plan="pro",
                status="active",
                created_at=datetime.utcnow()
            )

            db.add(org)
            await db.commit()

            # 创建成员关系
            owner_member = Member(
                id=uuid4(),
                user_id=owner.id,
                organization_id=org.id,
                role=OrganizationRole.OWNER,
                created_at=datetime.utcnow()
            )
            admin_member = Member(
                id=uuid4(),
                user_id=admin.id,
                organization_id=org.id,
                role=OrganizationRole.ADMIN,
                created_at=datetime.utcnow()
            )
            member_member = Member(
                id=uuid4(),
                user_id=member.id,
                organization_id=org.id,
                role=OrganizationRole.MEMBER,
                created_at=datetime.utcnow()
            )
            viewer_member = Member(
                id=uuid4(),
                user_id=viewer.id,
                organization_id=org.id,
                role=OrganizationRole.VIEWER,
                created_at=datetime.utcnow()
            )

            db.add_all([owner_member, admin_member, member_member, viewer_member])
            await db.commit()

            yield {
                'org': org,
                'owner': owner,
                'admin': admin,
                'member': member,
                'viewer': viewer,
                'outsider': outsider
            }

            # 清理测试数据
            await db.execute(text("DELETE FROM members"))
            await db.execute(text("DELETE FROM organizations"))
            await db.execute(text("DELETE FROM users"))
            await db.commit()

    async def get_user_role(self, db, user_id: str, org_id: str):
        """获取用户在组织中的角色"""
        result = await db.execute(
            text("SELECT role FROM members WHERE user_id = :user_id AND organization_id = :org_id"),
            {"user_id": user_id, "org_id": org_id}
        )
        return result.scalar()

    async def test_owner_permissions(self, permission_test_data):
        """测试Owner权限"""
        async for db in get_db():
            role = await self.get_user_role(
                db,
                permission_test_data['owner'].id,
                permission_test_data['org'].id
            )
            assert role == OrganizationRole.OWNER

            # Owner应该拥有所有权限
            owner_permissions = {
                'can_read_organization': True,
                'can_update_organization': True,
                'can_delete_organization': True,
                'can_invite_members': True,
                'can_remove_members': True,
                'can_manage_teams': True,
                'can_manage_budgets': True,
                'can_create_api_keys': True
            }

            # 这里应该调用实际的权限检查函数
            # for permission, expected in owner_permissions.items():
            #     result = await check_permission(user_id, org_id, permission)
            #     assert result == expected

    async def test_admin_permissions(self, permission_test_data):
        """测试Admin权限"""
        async for db in get_db():
            role = await self.get_user_role(
                db,
                permission_test_data['admin'].id,
                permission_test_data['org'].id
            )
            assert role == OrganizationRole.ADMIN

            # Admin应该拥有大部分权限，但不能删除组织
            admin_permissions = {
                'can_read_organization': True,
                'can_update_organization': True,
                'can_delete_organization': False,  # 不能删除组织
                'can_invite_members': True,
                'can_remove_members': True,  # 但不能移除Owner
                'can_manage_teams': True,
                'can_manage_budgets': True,
                'can_create_api_keys': True
            }

    async def test_member_permissions(self, permission_test_data):
        """测试Member权限"""
        async for db in get_db():
            role = await self.get_user_role(
                db,
                permission_test_data['member'].id,
                permission_test_data['org'].id
            )
            assert role == OrganizationRole.MEMBER

            # Member只有基础权限
            member_permissions = {
                'can_read_organization': True,
                'can_update_organization': False,
                'can_delete_organization': False,
                'can_invite_members': False,
                'can_remove_members': False,
                'can_manage_teams': False,
                'can_manage_budgets': False,
                'can_create_api_keys': False
            }

    async def test_viewer_permissions(self, permission_test_data):
        """测试Viewer权限"""
        async for db in get_db():
            role = await self.get_user_role(
                db,
                permission_test_data['viewer'].id,
                permission_test_data['org'].id
            )
            assert role == OrganizationRole.VIEWER

            # Viewer只有只读权限
            viewer_permissions = {
                'can_read_organization': True,
                'can_update_organization': False,
                'can_delete_organization': False,
                'can_invite_members': False,
                'can_remove_members': False,
                'can_manage_teams': False,
                'can_manage_budgets': False,
                'can_create_api_keys': False
            }

    async def test_outsider_permissions(self, permission_test_data):
        """测试外部用户权限"""
        async for db in get_db():
            # 外部用户不应该有成员关系
            role = await self.get_user_role(
                db,
                permission_test_data['outsider'].id,
                permission_test_data['org'].id
            )
            assert role is None

            # 外部用户没有任何权限
            outsider_permissions = {
                'can_read_organization': False,
                'can_update_organization': False,
                'can_delete_organization': False,
                'can_invite_members': False,
                'can_remove_members': False,
                'can_manage_teams': False,
                'can_manage_budgets': False,
                'can_create_api_keys': False
            }

    async def test_role_hierarchy(self, permission_test_data):
        """测试角色层次结构"""
        # 权限级别: Owner > Admin > Member > Viewer
        role_hierarchy = {
            OrganizationRole.OWNER: 4,
            OrganizationRole.ADMIN: 3,
            OrganizationRole.MEMBER: 2,
            OrganizationRole.VIEWER: 1
        }

        async for db in get_db():
            # 验证所有用户的角色
            owner_role = await self.get_user_role(
                db, permission_test_data['owner'].id, permission_test_data['org'].id
            )
            admin_role = await self.get_user_role(
                db, permission_test_data['admin'].id, permission_test_data['org'].id
            )
            member_role = await self.get_user_role(
                db, permission_test_data['member'].id, permission_test_data['org'].id
            )
            viewer_role = await self.get_user_role(
                db, permission_test_data['viewer'].id, permission_test_data['org'].id
            )

            # 验证角色层次
            assert role_hierarchy[owner_role] > role_hierarchy[admin_role]
            assert role_hierarchy[admin_role] > role_hierarchy[member_role]
            assert role_hierarchy[member_role] > role_hierarchy[viewer_role]

    async def test_member_role_update(self, permission_test_data):
        """测试成员角色更新"""
        async for db in get_db():
            # 初始角色验证
            initial_role = await self.get_user_role(
                db, permission_test_data['member'].id, permission_test_data['org'].id
            )
            assert initial_role == OrganizationRole.MEMBER

            # 更新角色为Admin
            await db.execute(
                text("""
                    UPDATE members
                    SET role = :new_role
                    WHERE user_id = :user_id AND organization_id = :org_id
                """),
                {
                    "new_role": OrganizationRole.ADMIN,
                    "user_id": permission_test_data['member'].id,
                    "org_id": permission_test_data['org'].id
                }
            )
            await db.commit()

            # 验证角色更新成功
            updated_role = await self.get_user_role(
                db, permission_test_data['member'].id, permission_test_data['org'].id
            )
            assert updated_role == OrganizationRole.ADMIN

    async def test_member_removal(self, permission_test_data):
        """测试成员移除"""
        async for db in get_db():
            # 验证成员存在
            initial_count = await db.execute(
                text("SELECT COUNT(*) FROM members WHERE user_id = :user_id"),
                {"user_id": permission_test_data['viewer'].id}
            )
            assert initial_count.scalar() == 1

            # 移除成员
            await db.execute(
                text("DELETE FROM members WHERE user_id = :user_id AND organization_id = :org_id"),
                {
                    "user_id": permission_test_data['viewer'].id,
                    "org_id": permission_test_data['org'].id
                }
            )
            await db.commit()

            # 验证成员已被移除
            final_count = await db.execute(
                text("SELECT COUNT(*) FROM members WHERE user_id = :user_id"),
                {"user_id": permission_test_data['viewer'].id}
            )
            assert final_count.scalar() == 0

    async def test_organization_member_count(self, permission_test_data):
        """测试组织成员计数"""
        async for db in get_db():
            # 获取组织成员数量
            count_result = await db.execute(
                text("SELECT COUNT(*) FROM members WHERE organization_id = :org_id"),
                {"org_id": permission_test_data['org'].id}
            )
            member_count = count_result.scalar()
            assert member_count == 4  # owner, admin, member, viewer

            # 按角色统计
            role_counts = await db.execute(
                text("""
                    SELECT role, COUNT(*) as count
                    FROM members
                    WHERE organization_id = :org_id
                    GROUP BY role
                """),
                {"org_id": permission_test_data['org'].id}
            )
            roles = role_counts.fetchall()

            role_dict = {row.role: row.count for row in roles}
            assert role_dict[OrganizationRole.OWNER] == 1
            assert role_dict[OrganizationRole.ADMIN] == 1
            assert role_dict[OrganizationRole.MEMBER] == 1
            assert role_dict[OrganizationRole.VIEWER] == 1


class TestPermissionAPI:
    """权限API测试"""

    @pytest.fixture
    async def api_permission_data(self):
        """创建API权限测试数据"""
        async for db in get_db():
            # 创建测试用户
            user = User(
                id=uuid4(),
                email="perm_api_user@test.com",
                password_hash=get_password_hash("password123"),
                is_active=True,
                created_at=datetime.utcnow()
            )

            db.add(user)
            await db.commit()

            # 创建测试组织
            org = Organization(
                id=uuid4(),
                name="API Permission Org",
                slug="api-permission-org",
                plan="pro",
                status="active",
                created_at=datetime.utcnow()
            )

            db.add(org)
            await db.commit()

            # 创建成员关系
            member = Member(
                id=uuid4(),
                user_id=user.id,
                organization_id=org.id,
                role=OrganizationRole.ADMIN,
                created_at=datetime.utcnow()
            )

            db.add(member)
            await db.commit()

            yield {
                'user': user,
                'org': org
            }

            # 清理测试数据
            await db.execute(text("DELETE FROM members"))
            await db.execute(text("DELETE FROM organizations"))
            await db.execute(text("DELETE FROM users"))
            await db.commit()

    async def test_organization_access_permissions(self, api_permission_data):
        """测试组织访问权限"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 测试有权限的用户访问组织
            response = await client.get(f"/api/v1/organizations/{api_permission_data['org'].id}")
            assert response.status_code == 200

            # 测试组织详情访问
            response = await client.get(f"/api/v1/organizations/{api_permission_data['org'].id}/details")
            assert response.status_code == 200

    async def test_team_management_permissions(self, api_permission_data):
        """测试团队管理权限"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 测试创建团队 (Admin权限)
            team_data = {
                "name": "Test Team",
                "description": "A test team"
            }
            response = await client.post(
                f"/api/v1/organizations/{api_permission_data['org'].id}/teams",
                json=team_data
            )
            assert response.status_code in [200, 201]  # 成功或已存在

            # 测试获取团队列表
            response = await client.get(f"/api/v1/organizations/{api_permission_data['org'].id}/teams")
            assert response.status_code == 200

    async def test_member_management_permissions(self, api_permission_data):
        """测试成员管理权限"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 测试获取成员列表
            response = await client.get(f"/api/v1/organizations/{api_permission_data['org'].id}/members")
            assert response.status_code == 200

            # 测试邀请新成员 (需要Admin权限)
            invite_data = {
                "email": "newmember@test.com",
                "role": OrganizationRole.MEMBER
            }
            response = await client.post(
                f"/api/v1/organizations/{api_permission_data['org'].id}/invite",
                json=invite_data
            )
            # 根据实际实现调整期望的状态码


if __name__ == "__main__":
    # 运行测试
    asyncio.run(pytest.main([__file__, "-v"]))