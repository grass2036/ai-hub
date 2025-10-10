"""
Multi-tenant data isolation tests
测试多租户数据隔离功能
"""

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy import text

from backend.main import app
from backend.models.database import get_db
from backend.models.organization import Organization
from backend.models.team import Team
from backend.models.member import Member
from backend.models.budget import Budget
from backend.models.user import User
from backend.core.security import get_password_hash


class TestMultiTenantIsolation:
    """多租户数据隔离测试类"""

    @pytest.fixture
    async def test_data(self):
        """创建测试数据"""
        async for db in get_db():
            # 创建测试用户
            user1 = User(
                id=uuid4(),
                email="user1@test.com",
                password_hash=get_password_hash("password123"),
                is_active=True,
                created_at=datetime.utcnow()
            )
            user2 = User(
                id=uuid4(),
                email="user2@test.com",
                password_hash=get_password_hash("password123"),
                is_active=True,
                created_at=datetime.utcnow()
            )

            db.add(user1)
            db.add(user2)
            await db.commit()

            # 创建测试组织
            org1 = Organization(
                id=uuid4(),
                name="Organization 1",
                slug="org1",
                plan="pro",
                status="active",
                created_at=datetime.utcnow()
            )
            org2 = Organization(
                id=uuid4(),
                name="Organization 2",
                slug="org2",
                plan="pro",
                status="active",
                created_at=datetime.utcnow()
            )

            db.add(org1)
            db.add(org2)
            await db.commit()

            # 创建成员关系
            member1 = Member(
                id=uuid4(),
                user_id=user1.id,
                organization_id=org1.id,
                role="owner",
                created_at=datetime.utcnow()
            )
            member2 = Member(
                id=uuid4(),
                user_id=user2.id,
                organization_id=org2.id,
                role="owner",
                created_at=datetime.utcnow()
            )

            db.add(member1)
            db.add(member2)
            await db.commit()

            # 创建团队
            team1 = Team(
                id=uuid4(),
                organization_id=org1.id,
                name="Team 1",
                created_at=datetime.utcnow()
            )
            team2 = Team(
                id=uuid4(),
                organization_id=org2.id,
                name="Team 2",
                created_at=datetime.utcnow()
            )

            db.add(team1)
            db.add(team2)
            await db.commit()

            # 创建预算
            budget1 = Budget(
                id=uuid4(),
                organization_id=org1.id,
                monthly_limit=1000.0,
                current_spend=0.0,
                currency="USD",
                status="active",
                created_at=datetime.utcnow()
            )
            budget2 = Budget(
                id=uuid4(),
                organization_id=org2.id,
                monthly_limit=2000.0,
                current_spend=0.0,
                currency="USD",
                status="active",
                created_at=datetime.utcnow()
            )

            db.add(budget1)
            db.add(budget2)
            await db.commit()

            yield {
                'user1': user1,
                'user2': user2,
                'org1': org1,
                'org2': org2,
                'team1': team1,
                'team2': team2,
                'budget1': budget1,
                'budget2': budget2
            }

            # 清理测试数据
            await db.execute(text("DELETE FROM budgets"))
            await db.execute(text("DELETE FROM teams"))
            await db.execute(text("DELETE FROM members"))
            await db.execute(text("DELETE FROM organizations"))
            await db.execute(text("DELETE FROM users"))
            await db.commit()

    async def test_organization_isolation(self, test_data):
        """测试组织数据隔离"""
        async for db in get_db():
            # 用户1只能看到自己的组织
            org1_query = await db.execute(
                text("SELECT * FROM organizations WHERE id = :org_id"),
                {"org_id": test_data['org1'].id}
            )
            org1_result = org1_query.fetchone()
            assert org1_result is not None
            assert org1_result.name == "Organization 1"

            # 用户2只能看到自己的组织
            org2_query = await db.execute(
                text("SELECT * FROM organizations WHERE id = :org_id"),
                {"org_id": test_data['org2'].id}
            )
            org2_result = org2_query.fetchone()
            assert org2_result is not None
            assert org2_result.name == "Organization 2"

            # 验证数据不会泄漏
            assert org1_result.id != org2_result.id

    async def test_team_isolation(self, test_data):
        """测试团队数据隔离"""
        async for db in get_db():
            # 组织1的团队
            team1_query = await db.execute(
                text("""
                    SELECT t.*, o.name as org_name
                    FROM teams t
                    JOIN organizations o ON t.organization_id = o.id
                    WHERE t.id = :team_id
                """),
                {"team_id": test_data['team1'].id}
            )
            team1_result = team1_query.fetchone()
            assert team1_result is not None
            assert team1_result.org_name == "Organization 1"

            # 组织2的团队
            team2_query = await db.execute(
                text("""
                    SELECT t.*, o.name as org_name
                    FROM teams t
                    JOIN organizations o ON t.organization_id = o.id
                    WHERE t.id = :team_id
                """),
                {"team_id": test_data['team2'].id}
            )
            team2_result = team2_query.fetchone()
            assert team2_result is not None
            assert team2_result.org_name == "Organization 2"

            # 验证团队不会跨组织
            assert team1_result.organization_id != team2_result.organization_id

    async def test_budget_isolation(self, test_data):
        """测试预算数据隔离"""
        async for db in get_db():
            # 组织1的预算
            budget1_query = await db.execute(
                text("""
                    SELECT b.*, o.name as org_name
                    FROM budgets b
                    JOIN organizations o ON b.organization_id = o.id
                    WHERE b.id = :budget_id
                """),
                {"budget_id": test_data['budget1'].id}
            )
            budget1_result = budget1_query.fetchone()
            assert budget1_result is not None
            assert budget1_result.monthly_limit == 1000.0
            assert budget1_result.org_name == "Organization 1"

            # 组织2的预算
            budget2_query = await db.execute(
                text("""
                    SELECT b.*, o.name as org_name
                    FROM budgets b
                    JOIN organizations o ON b.organization_id = o.id
                    WHERE b.id = :budget_id
                """),
                {"budget_id": test_data['budget2'].id}
            )
            budget2_result = budget2_query.fetchone()
            assert budget2_result is not None
            assert budget2_result.monthly_limit == 2000.0
            assert budget2_result.org_name == "Organization 2"

            # 验证预算不会跨组织
            assert budget1_result.organization_id != budget2_result.organization_id

    async def test_member_isolation(self, test_data):
        """测试成员数据隔离"""
        async for db in get_db():
            # 用户1的成员关系
            member1_query = await db.execute(
                text("""
                    SELECT m.*, o.name as org_name, u.email as user_email
                    FROM members m
                    JOIN organizations o ON m.organization_id = o.id
                    JOIN users u ON m.user_id = u.id
                    WHERE m.user_id = :user_id
                """),
                {"user_id": test_data['user1'].id}
            )
            member1_result = member1_query.fetchone()
            assert member1_result is not None
            assert member1_result.org_name == "Organization 1"
            assert member1_result.user_email == "user1@test.com"
            assert member1_result.role == "owner"

            # 用户2的成员关系
            member2_query = await db.execute(
                text("""
                    SELECT m.*, o.name as org_name, u.email as user_email
                    FROM members m
                    JOIN organizations o ON m.organization_id = o.id
                    JOIN users u ON m.user_id = u.id
                    WHERE m.user_id = :user_id
                """),
                {"user_id": test_data['user2'].id}
            )
            member2_result = member2_query.fetchone()
            assert member2_result is not None
            assert member2_result.org_name == "Organization 2"
            assert member2_result.user_email == "user2@test.com"
            assert member2_result.role == "owner"

            # 验证成员关系不会跨组织
            assert member1_result.organization_id != member2_result.organization_id

    async def test_cross_organization_data_leak(self, test_data):
        """测试跨组织数据泄漏"""
        async for db in get_db():
            # 尝试从组织1访问组织2的数据 - 应该失败
            leak_query = await db.execute(
                text("""
                    SELECT t.*, o.name as org_name
                    FROM teams t
                    JOIN organizations o ON t.organization_id = o.id
                    WHERE t.organization_id = :org1_id AND o.id = :org2_id
                """),
                {"org1_id": test_data['org1'].id, "org2_id": test_data['org2'].id}
            )
            leak_result = leak_query.fetchone()
            assert leak_result is None  # 应该没有结果

    async def test_organization_data_count_isolation(self, test_data):
        """测试组织数据统计隔离"""
        async for db in get_db():
            # 组织1的团队数量
            org1_teams_count = await db.execute(
                text("SELECT COUNT(*) FROM teams WHERE organization_id = :org_id"),
                {"org_id": test_data['org1'].id}
            )
            org1_count = org1_teams_count.scalar()
            assert org1_count == 1

            # 组织2的团队数量
            org2_teams_count = await db.execute(
                text("SELECT COUNT(*) FROM teams WHERE organization_id = :org_id"),
                {"org_id": test_data['org2'].id}
            )
            org2_count = org2_teams_count.scalar()
            assert org2_count == 1

            # 验证总数正确
            total_teams_count = await db.execute(text("SELECT COUNT(*) FROM teams"))
            total_count = total_teams_count.scalar()
            assert total_count == 2

    async def test_cascade_delete_isolation(self, test_data):
        """测试级联删除隔离"""
        async for db in get_db():
            # 删除组织1
            await db.execute(
                text("DELETE FROM organizations WHERE id = :org_id"),
                {"org_id": test_data['org1'].id}
            )
            await db.commit()

            # 验证组织1的团队也被删除
            team1_exists = await db.execute(
                text("SELECT COUNT(*) FROM teams WHERE id = :team_id"),
                {"team_id": test_data['team1'].id}
            )
            team1_count = team1_exists.scalar()
            assert team1_count == 0

            # 验证组织2的数据不受影响
            org2_exists = await db.execute(
                text("SELECT COUNT(*) FROM organizations WHERE id = :org_id"),
                {"org_id": test_data['org2'].id}
            )
            org2_count = org2_exists.scalar()
            assert org2_count == 1

            team2_exists = await db.execute(
                text("SELECT COUNT(*) FROM teams WHERE id = :team_id"),
                {"team_id": test_data['team2'].id}
            )
            team2_count = team2_exists.scalar()
            assert team2_count == 1


class TestAPIEndpointIsolation:
    """API端点隔离测试"""

    @pytest.fixture
    async def api_test_data(self):
        """创建API测试数据"""
        async for db in get_db():
            # 创建测试用户
            user1 = User(
                id=uuid4(),
                email="api_user1@test.com",
                password_hash=get_password_hash("password123"),
                is_active=True,
                created_at=datetime.utcnow()
            )
            user2 = User(
                id=uuid4(),
                email="api_user2@test.com",
                password_hash=get_password_hash("password123"),
                is_active=True,
                created_at=datetime.utcnow()
            )

            db.add(user1)
            db.add(user2)
            await db.commit()

            # 创建测试组织
            org1 = Organization(
                id=uuid4(),
                name="API Organization 1",
                slug="api-org1",
                plan="pro",
                status="active",
                created_at=datetime.utcnow()
            )
            org2 = Organization(
                id=uuid4(),
                name="API Organization 2",
                slug="api-org2",
                plan="pro",
                status="active",
                created_at=datetime.utcnow()
            )

            db.add(org1)
            db.add(org2)
            await db.commit()

            # 创建成员关系
            member1 = Member(
                id=uuid4(),
                user_id=user1.id,
                organization_id=org1.id,
                role="owner",
                created_at=datetime.utcnow()
            )
            member2 = Member(
                id=uuid4(),
                user_id=user2.id,
                organization_id=org2.id,
                role="owner",
                created_at=datetime.utcnow()
            )

            db.add(member1)
            db.add(member2)
            await db.commit()

            yield {
                'user1': user1,
                'user2': user2,
                'org1': org1,
                'org2': org2
            }

            # 清理测试数据
            await db.execute(text("DELETE FROM members"))
            await db.execute(text("DELETE FROM organizations"))
            await db.execute(text("DELETE FROM users"))
            await db.commit()

    async def test_organization_api_isolation(self, api_test_data):
        """测试组织API隔离"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 测试获取用户1的组织列表 - 应该只返回org1
            response = await client.get(f"/api/v1/users/{api_test_data['user1'].id}/organizations")
            assert response.status_code == 200
            orgs = response.json()
            assert len(orgs) == 1
            assert orgs[0]['name'] == "API Organization 1"

            # 测试获取用户2的组织列表 - 应该只返回org2
            response = await client.get(f"/api/v1/users/{api_test_data['user2'].id}/organizations")
            assert response.status_code == 200
            orgs = response.json()
            assert len(orgs) == 1
            assert orgs[0]['name'] == "API Organization 2"

    async def test_team_api_isolation(self, api_test_data):
        """测试团队API隔离"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 测试获取组织1的团队列表
            response = await client.get(f"/api/v1/organizations/{api_test_data['org1'].id}/teams")
            assert response.status_code == 200
            teams = response.json()
            # 应该只返回组织1的团队

            # 测试获取组织2的团队列表
            response = await client.get(f"/api/v1/organizations/{api_test_data['org2'].id}/teams")
            assert response.status_code == 200
            teams = response.json()
            # 应该只返回组织2的团队

    async def test_budget_api_isolation(self, api_test_data):
        """测试预算API隔离"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 测试获取组织1的预算
            response = await client.get(f"/api/v1/organizations/{api_test_data['org1'].id}/budgets")
            assert response.status_code == 200
            budgets = response.json()
            # 应该只返回组织1的预算

            # 测试获取组织2的预算
            response = await client.get(f"/api/v1/organizations/{api_test_data['org2'].id}/budgets")
            assert response.status_code == 200
            budgets = response.json()
            # 应该只返回组织2的预算


if __name__ == "__main__":
    # 运行测试
    asyncio.run(pytest.main([__file__, "-v"]))