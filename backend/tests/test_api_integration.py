"""
API Integration Tests
API集成测试 - 前后端接口联调
"""

import pytest
import asyncio
import json
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
from backend.core.security import get_password_hash, create_access_token


class TestAPIIntegration:
    """API集成测试类"""

    @pytest.fixture
    async def integration_test_data(self):
        """创建集成测试数据"""
        async for db in get_db():
            # 创建测试用户
            user = User(
                id=uuid4(),
                email="integration@test.com",
                password_hash=get_password_hash("password123"),
                is_active=True,
                created_at=datetime.utcnow()
            )

            db.add(user)
            await db.commit()

            # 创建测试组织
            org = Organization(
                id=uuid4(),
                name="Integration Test Organization",
                slug="integration-test-org",
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
                role="owner",
                created_at=datetime.utcnow()
            )

            db.add(member)
            await db.commit()

            # 创建测试团队
            team = Team(
                id=uuid4(),
                organization_id=org.id,
                name="Integration Test Team",
                description="A team for integration testing",
                created_at=datetime.utcnow()
            )

            db.add(team)
            await db.commit()

            # 创建测试预算
            budget = Budget(
                id=uuid4(),
                organization_id=org.id,
                monthly_limit=1000.0,
                current_spend=0.0,
                currency="USD",
                status="active",
                created_at=datetime.utcnow()
            )

            db.add(budget)
            await db.commit()

            yield {
                'user': user,
                'org': org,
                'team': team,
                'budget': budget
            }

            # 清理测试数据
            await db.execute(text("DELETE FROM budgets"))
            await db.execute(text("DELETE FROM teams"))
            await db.execute(text("DELETE FROM members"))
            await db.execute(text("DELETE FROM organizations"))
            await db.execute(text("DELETE FROM users"))
            await db.commit()

    def get_auth_headers(self, user):
        """获取认证头"""
        token = create_access_token(data={"sub": str(user.id)})
        return {"Authorization": f"Bearer {token}"}

    async def test_organization_management_flow(self, integration_test_data):
        """测试组织管理完整流程"""
        user = integration_test_data['user']
        headers = self.get_auth_headers(user)

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. 获取用户组织列表
            response = await client.get(
                "/api/v1/organizations/",
                headers=headers
            )
            assert response.status_code == 200
            orgs = response.json()
            assert len(orgs) >= 1
            assert orgs[0]['name'] == "Integration Test Organization"

            # 2. 获取组织详情
            org_id = orgs[0]['id']
            response = await client.get(
                f"/api/v1/organizations/{org_id}",
                headers=headers
            )
            assert response.status_code == 200
            org_detail = response.json()
            assert org_detail['name'] == "Integration Test Organization"
            assert org_detail['slug'] == "integration-test-org"

            # 3. 创建新组织
            new_org_data = {
                "name": "New Integration Organization",
                "slug": "new-integration-org",
                "description": "A new organization for testing",
                "plan": "pro"
            }
            response = await client.post(
                "/api/v1/organizations/",
                json=new_org_data,
                headers=headers
            )
            assert response.status_code in [200, 201]

            # 4. 更新组织信息
            update_data = {
                "description": "Updated description for integration test"
            }
            response = await client.put(
                f"/api/v1/organizations/{org_id}",
                json=update_data,
                headers=headers
            )
            assert response.status_code == 200

    async def test_team_management_flow(self, integration_test_data):
        """测试团队管理完整流程"""
        user = integration_test_data['user']
        org = integration_test_data['org']
        headers = self.get_auth_headers(user)

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. 获取组织团队列表
            response = await client.get(
                f"/api/v1/organizations/{org.id}/teams",
                headers=headers
            )
            assert response.status_code == 200
            teams = response.json()
            assert len(teams) >= 1
            assert teams[0]['name'] == "Integration Test Team"

            # 2. 创建新团队
            new_team_data = {
                "name": "New Integration Team",
                "description": "A new team for testing"
            }
            response = await client.post(
                f"/api/v1/organizations/{org.id}/teams",
                json=new_team_data,
                headers=headers
            )
            assert response.status_code in [200, 201]

            # 3. 获取团队详情
            if response.status_code in [200, 201]:
                new_team = response.json()
                team_id = new_team.get('id', teams[0]['id'])
            else:
                team_id = teams[0]['id']

            response = await client.get(
                f"/api/v1/teams/{team_id}",
                headers=headers
            )
            assert response.status_code == 200
            team_detail = response.json()
            assert team_detail['organization_id'] == str(org.id)

            # 4. 更新团队信息
            update_data = {
                "description": "Updated team description"
            }
            response = await client.put(
                f"/api/v1/teams/{team_id}",
                json=update_data,
                headers=headers
            )
            assert response.status_code == 200

    async def test_budget_management_flow(self, integration_test_data):
        """测试预算管理完整流程"""
        user = integration_test_data['user']
        org = integration_test_data['org']
        headers = self.get_auth_headers(user)

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. 获取组织预算列表
            response = await client.get(
                f"/api/v1/organizations/{org.id}/budgets",
                headers=headers
            )
            assert response.status_code == 200
            budgets = response.json()
            assert len(budgets) >= 1
            assert budgets[0]['monthly_limit'] == 1000.0

            # 2. 创建新预算
            new_budget_data = {
                "monthly_limit": 500.0,
                "currency": "USD",
                "alert_threshold": 80.0
            }
            response = await client.post(
                f"/api/v1/organizations/{org.id}/budgets",
                json=new_budget_data,
                headers=headers
            )
            assert response.status_code in [200, 201]

            # 3. 获取预算使用情况
            response = await client.get(
                f"/api/v1/organizations/{org.id}/budgets/usage",
                headers=headers
            )
            assert response.status_code == 200
            usage_data = response.json()
            assert 'total_spend' in usage_data
            assert 'monthly_limit' in usage_data

            # 4. 更新预算设置
            budget_id = budgets[0]['id']
            update_data = {
                "monthly_limit": 1500.0,
                "alert_threshold": 85.0
            }
            response = await client.put(
                f"/api/v1/organizations/{org.id}/budgets/{budget_id}",
                json=update_data,
                headers=headers
            )
            assert response.status_code == 200

    async def test_member_management_flow(self, integration_test_data):
        """测试成员管理完整流程"""
        user = integration_test_data['user']
        org = integration_test_data['org']
        headers = self.get_auth_headers(user)

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. 获取组织成员列表
            response = await client.get(
                f"/api/v1/organizations/{org.id}/members",
                headers=headers
            )
            assert response.status_code == 200
            members = response.json()
            assert len(members) >= 1
            assert members[0]['role'] == 'owner'

            # 2. 邀请新成员 (模拟)
            # 注意：实际实现可能需要发送邮件等
            invite_data = {
                "email": "newmember@test.com",
                "role": "member"
            }
            response = await client.post(
                f"/api/v1/organizations/{org.id}/invite",
                json=invite_data,
                headers=headers
            )
            # 根据实际实现调整期望

            # 3. 获取成员统计
            response = await client.get(
                f"/api/v1/organizations/{org.id}/members/stats",
                headers=headers
            )
            assert response.status_code == 200
            stats = response.json()
            assert 'total_members' in stats
            assert 'role_distribution' in stats

    async def test_api_key_management_flow(self, integration_test_data):
        """测试API密钥管理完整流程"""
        user = integration_test_data['user']
        org = integration_test_data['org']
        headers = self.get_auth_headers(user)

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. 获取组织API密钥列表
            response = await client.get(
                f"/api/v1/organizations/{org.id}/api-keys",
                headers=headers
            )
            assert response.status_code == 200
            api_keys = response.json()
            # 初始可能没有API密钥

            # 2. 创建新API密钥
            new_key_data = {
                "name": "Integration Test API Key",
                "permissions": {
                    "chat": ["read", "write"],
                    "models": ["read"]
                },
                "rate_limit": 100,
                "monthly_quota": 10000
            }
            response = await client.post(
                f"/api/v1/organizations/{org.id}/api-keys",
                json=new_key_data,
                headers=headers
            )
            assert response.status_code in [200, 201]

            # 3. 获取API密钥详情
            if response.status_code in [200, 201]:
                key_data = response.json()
                key_id = key_data.get('id')
                if key_id:
                    response = await client.get(
                        f"/api/v1/api-keys/{key_id}",
                        headers=headers
                    )
                    assert response.status_code == 200

            # 4. 获取API密钥使用统计
            response = await client.get(
                f"/api/v1/organizations/{org.id}/api-keys/usage",
                headers=headers
            )
            assert response.status_code == 200
            usage_stats = response.json()
            assert 'total_keys' in usage_stats
            assert 'total_usage' in usage_stats

    async def test_cross_resource_integration(self, integration_test_data):
        """测试跨资源集成"""
        user = integration_test_data['user']
        org = integration_test_data['org']
        headers = self.get_auth_headers(user)

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. 获取组织概览 (包含所有资源统计)
            response = await client.get(
                f"/api/v1/organizations/{org.id}/overview",
                headers=headers
            )
            assert response.status_code == 200
            overview = response.json()
            assert 'organization' in overview
            assert 'teams_count' in overview
            assert 'members_count' in overview
            assert 'budgets_count' in overview
            assert 'api_keys_count' in overview

            # 2. 获取使用统计
            response = await client.get(
                f"/api/v1/organizations/{org.id}/usage-stats",
                headers=headers
            )
            assert response.status_code == 200
            usage_stats = response.json()
            assert 'chat_usage' in usage_stats
            assert 'api_usage' in usage_stats
            assert 'cost_breakdown' in usage_stats

    async def test_error_handling(self, integration_test_data):
        """测试错误处理"""
        user = integration_test_data['user']
        headers = self.get_auth_headers(user)

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. 访问不存在的组织
            fake_org_id = str(uuid4())
            response = await client.get(
                f"/api/v1/organizations/{fake_org_id}",
                headers=headers
            )
            assert response.status_code == 404

            # 2. 访问不存在的团队
            fake_team_id = str(uuid4())
            response = await client.get(
                f"/api/v1/teams/{fake_team_id}",
                headers=headers
            )
            assert response.status_code == 404

            # 3. 创建重复的组织 (相同slug)
            duplicate_org_data = {
                "name": "Duplicate Organization",
                "slug": "integration-test-org",  # 已存在的slug
                "plan": "pro"
            }
            response = await client.post(
                "/api/v1/organizations/",
                json=duplicate_org_data,
                headers=headers
            )
            assert response.status_code == 400  # 应该返回冲突错误

            # 4. 无效的数据格式
            invalid_data = {
                "name": "",  # 空名称
                "plan": "invalid_plan"
            }
            response = await client.post(
                "/api/v1/organizations/",
                json=invalid_data,
                headers=headers
            )
            assert response.status_code == 422  # 验证错误

    async def test_authentication_flow(self):
        """测试认证流程"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. 无认证访问受保护的端点
            response = await client.get("/api/v1/organizations/")
            assert response.status_code == 401

            # 2. 使用无效token访问
            invalid_headers = {"Authorization": "Bearer invalid_token"}
            response = await client.get(
                "/api/v1/organizations/",
                headers=invalid_headers
            )
            assert response.status_code == 401

            # 3. 登录获取token (如果有登录端点)
            login_data = {
                "email": "integration@test.com",
                "password": "password123"
            }
            # response = await client.post("/api/v1/auth/login", json=login_data)
            # assert response.status_code == 200
            # token_data = response.json()
            # assert "access_token" in token_data

    async def test_data_consistency(self, integration_test_data):
        """测试数据一致性"""
        user = integration_test_data['user']
        org = integration_test_data['org']
        headers = self.get_auth_headers(user)

        async with AsyncClient(app=app, base_url="http://test") as client:
            # 1. 创建团队后验证组织团队数量
            initial_teams_response = await client.get(
                f"/api/v1/organizations/{org.id}/teams",
                headers=headers
            )
            initial_count = len(initial_teams_response.json())

            # 创建新团队
            new_team_data = {
                "name": "Consistency Test Team",
                "description": "Testing data consistency"
            }
            await client.post(
                f"/api/v1/organizations/{org.id}/teams",
                json=new_team_data,
                headers=headers
            )

            # 验证团队数量增加
            updated_teams_response = await client.get(
                f"/api/v1/organizations/{org.id}/teams",
                headers=headers
            )
            updated_count = len(updated_teams_response.json())
            assert updated_count == initial_count + 1

            # 2. 删除团队后验证数据一致性
            if updated_teams_response.json():
                team_to_delete = updated_teams_response.json()[-1]
                delete_response = await client.delete(
                    f"/api/v1/teams/{team_to_delete['id']}",
                    headers=headers
                )
                if delete_response.status_code == 200:
                    final_teams_response = await client.get(
                        f"/api/v1/organizations/{org.id}/teams",
                        headers=headers
                    )
                    final_count = len(final_teams_response.json())
                    assert final_count == initial_count


class TestPerformanceIntegration:
    """性能集成测试"""

    async def test_concurrent_requests(self):
        """测试并发请求"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 并发发送多个请求
            tasks = []
            for i in range(10):
                task = client.get("/api/v1/models")
                tasks.append(task)

            responses = await asyncio.gather(*tasks)

            # 验证所有请求都成功
            for response in responses:
                assert response.status_code == 200

    async def test_response_time(self):
        """测试响应时间"""
        import time
        async with AsyncClient(app=app, base_url="http://test") as client:
            start_time = time.time()
            response = await client.get("/api/v1/models")
            end_time = time.time()

            response_time = end_time - start_time
            assert response_time < 2.0  # 响应时间应小于2秒
            assert response.status_code == 200


if __name__ == "__main__":
    # 运行测试
    asyncio.run(pytest.main([__file__, "-v"]))