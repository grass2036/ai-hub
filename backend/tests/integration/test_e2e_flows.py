"""
端到端功能集成测试
Week 6 Day 1: 系统集成测试 - 功能集成验证
验证完整的用户业务流程
"""

import asyncio
import pytest
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.core.database import get_db
from backend.models.user import User, UserRole
from backend.models.organization import Organization
from backend.models.member import OrganizationMember, OrganizationRole
from backend.models.api_key import ApiKey
from backend.models.subscription import Subscription, Plan, SubscriptionStatus

@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)

@pytest.fixture
def db_session():
    """创建数据库会话"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
async def test_user_data():
    """测试用户数据"""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }

@pytest.fixture
async def test_organization_data():
    """测试企业数据"""
    return {
        "name": "Test Corporation",
        "slug": "test-corp",
        "email": "admin@testcorp.com",
        "plan": "professional"
    }

class TestE2EUserFlow:
    """端到端用户流程测试"""

    async def test_complete_user_registration_flow(self, client: TestClient, test_user_data: Dict[str, Any]):
        """测试完整的用户注册流程"""
        print("🔄 测试用户注册流程...")

        # 1. 用户注册
        response = client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 201
        user_data = response.json()
        assert user_data["email"] == test_user_data["email"]

        # 2. 用户登录
        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data

        token = login_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. 获取用户信息
        user_info_response = client.get("/api/v1/users/me", headers=headers)
        assert user_info_response.status_code == 200
        user_info = user_info_response.json()
        assert user_info["email"] == test_user_data["email"]

        print("✅ 用户注册流程测试通过")
        return token, user_info

    async def test_enterprise_onboarding_flow(self, client: TestClient, token: str, test_organization_data: Dict[str, Any]):
        """测试企业入驻流程"""
        print("🔄 测试企业入驻流程...")

        headers = {"Authorization": f"Bearer {token}"}

        # 1. 创建企业
        org_response = client.post("/api/v1/organizations", json=test_organization_data, headers=headers)
        assert org_response.status_code == 201
        org_data = org_response.json()
        assert org_data["name"] == test_organization_data["name"]

        organization_id = org_data["id"]

        # 2. 获取企业详情
        org_detail_response = client.get(f"/api/v1/organizations/{organization_id}", headers=headers)
        assert org_detail_response.status_code == 200
        org_detail = org_detail_response.json()
        assert org_detail["name"] == test_organization_data["name"]

        # 3. 创建API密钥
        api_key_response = client.post("/api/v1/developer/keys", json={
            "name": "Test API Key",
            "description": "Test key for integration testing"
        }, headers=headers)
        assert api_key_response.status_code == 201
        api_key_data = api_key_response.json()
        api_key = api_key_data["api_key"]

        print("✅ 企业入驻流程测试通过")
        return organization_id, api_key

    async def test_api_usage_flow(self, client: TestClient, api_key: str):
        """测试API使用流程"""
        print("🔄 测试API使用流程...")

        headers = {"X-API-Key": api_key}

        # 1. 获取可用模型
        models_response = client.get("/api/v1/models", headers=headers)
        assert models_response.status_code == 200
        models = models_response.json()
        assert len(models) > 0

        # 2. 测试聊天API
        chat_response = client.post("/api/v1/chat/completions", json={
            "model": models[0]["id"],
            "messages": [{"role": "user", "content": "Hello, this is a test message"}],
            "max_tokens": 50
        }, headers=headers)
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        assert "choices" in chat_data
        assert len(chat_data["choices"]) > 0

        # 3. 测试统计API
        stats_response = client.get("/api/v1/stats/overview", headers=headers)
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert "total_requests" in stats

        print("✅ API使用流程测试通过")
        return models[0]["id"]

    async def test_analytics_flow(self, client: TestClient, token: str, model_id: str):
        """测试分析功能流程"""
        print("🔄 测试分析功能流程...")

        headers = {"Authorization": f"Bearer {token}"}

        # 1. 获取分析概览
        analytics_response = client.get("/api/v1/analytics/dashboard/overview?days=7", headers=headers)
        assert analytics_response.status_code == 200
        analytics_data = analytics_response.json()
        assert "summary" in analytics_data
        assert "period_days" in analytics_data

        # 2. 获取用户事件
        events_response = client.get("/api/v1/analytics/events?limit=10", headers=headers)
        assert events_response.status_code == 200
        events = events_response.json()
        assert isinstance(events, list)

        # 3. 获取用户会话
        sessions_response = client.get("/api/v1/analytics/sessions?limit=5", headers=headers)
        assert sessions_response.status_code == 200
        sessions = sessions_response.json()
        assert isinstance(sessions, list)

        print("✅ 分析功能流程测试通过")

class TestAPIVersionIntegration:
    """API版本集成测试"""

    async def test_api_version_compatibility(self, client: TestClient, api_key: str):
        """测试API版本兼容性"""
        print("🔄 测试API版本兼容性...")

        headers_v1 = {"X-API-Key": api_key}

        # 1. 测试v1 API
        v1_response = client.get("/api/v1/models", headers=headers_v1)
        assert v1_response.status_code == 200

        # 2. 测试v2 API
        v2_response = client.get("/api/v2/health/status", headers=headers_v1)
        assert v2_response.status_code == 200
        v2_data = v2_response.json()
        assert "version" in v2_data

        # 3. 测试版本头
        assert "X-API-Version" in v2_response.headers
        assert "X-API-Latest-Version" in v2_response.headers

        print("✅ API版本兼容性测试通过")

class TestDataFlowIntegration:
    """数据流集成测试"""

    async def test_user_behavior_tracking_flow(self, client: TestClient, token: str, api_key: str):
        """测试用户行为跟踪数据流"""
        print("🔄 测试用户行为跟踪数据流...")

        headers_auth = {"Authorization": f"Bearer {token}"}
        headers_api = {"X-API-Key": api_key}

        # 1. 跟踪页面访问事件
        page_event_response = client.post("/api/v1/analytics/events/track", json={
            "session_id": "test-session-123",
            "event_type": "page_view",
            "category": "user_interaction",
            "url": "/dashboard",
            "properties": {
                "page_title": "Dashboard",
                "referrer": "/login"
            }
        }, headers=headers_auth)
        assert page_event_response.status_code == 201

        # 2. 跟踪API调用事件
        api_event_response = client.post("/api/v1/analytics/events/track", json={
            "session_id": "test-session-123",
            "event_type": "api_call",
            "category": "system_event",
            "properties": {
                "endpoint": "/api/v1/models",
                "method": "GET",
                "status_code": 200,
                "response_time": 150.5
            }
        }, headers=headers_auth)
        assert api_event_response.status_code == 201

        # 3. 跟踪用户操作事件
        action_event_response = client.post("/api/v1/analytics/events/track", json={
            "session_id": "test-session-123",
            "event_type": "user_action",
            "action_type": "click",
            "category": "user_interaction",
            "properties": {
                "element": "submit_button",
                "page": "/dashboard"
            }
        }, headers=headers_auth)
        assert action_event_response.status_code == 201

        # 4. 验证事件数据
        events_response = client.get("/api/v1/analytics/events?limit=3", headers=headers_auth)
        assert events_response.status_code == 200
        events = events_response.json()
        assert len(events) >= 3

        # 验证事件类型分布
        event_types = [event["event_type"] for event in events]
        assert "page_view" in event_types
        assert "api_call" in event_types
        assert "user_action" in event_types

        print("✅ 用户行为跟踪数据流测试通过")

    async def test_analytics_real_time_flow(self, client: TestClient, token: str):
        """测试实时分析数据流"""
        print("🔄 测试实时分析数据流...")

        headers = {"Authorization": f"Bearer {token}"}

        # 1. 获取实时统计
        realtime_response = client.get("/api/v1/analytics/realtime/stats", headers=headers)
        assert realtime_response.status_code == 200
        realtime_data = realtime_response.json()
        assert "realtime_stats" in realtime_data
        assert "active_sessions" in realtime_data
        assert "user_recent_activity" in realtime_data

        # 2. 验证实时数据结构
        realtime_stats = realtime_data["realtime_stats"]
        assert "total_events" in realtime_stats
        assert "unique_users" in realtime_stats
        assert "unique_sessions" in realtime_stats

        # 3. 验证用户活动数据
        user_activity = realtime_data["user_recent_activity"]
        assert isinstance(user_activity, list)

        print("✅ 实时分析数据流测试通过")

class TestSecurityIntegration:
    """安全集成测试"""

    async def test_authentication_integration(self, client: TestClient, test_user_data: Dict[str, Any]):
        """测试认证集成"""
        print("🔄 测试认证集成...")

        # 1. 测试无效token
        invalid_headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/v1/users/me", headers=invalid_headers)
        assert response.status_code == 401

        # 2. 测试API密钥认证
        # 首先注册用户并获取API密钥
        register_response = client.post("/api/v1/auth/register", json=test_user_data)
        assert register_response.status_code == 201

        login_response = client.post("/api/v1/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        auth_headers = {"Authorization": f"Bearer {token}"}

        # 创建API密钥
        api_key_response = client.post("/api/v1/developer/keys", json={
            "name": "Test Key",
            "description": "Test key for security testing"
        }, headers=auth_headers)
        assert api_key_response.status_code == 201
        api_key = api_key_response.json()["api_key"]

        # 3. 测试API密钥认证
        api_key_headers = {"X-API-Key": api_key}
        response = client.get("/api/v1/models", headers=api_key_headers)
        assert response.status_code == 200

        # 4. 测试无效API密钥
        invalid_api_headers = {"X-API-Key": "invalid-key"}
        response = client.get("/api/v1/models", headers=invalid_api_headers)
        assert response.status_code == 401

        print("✅ 认证集成测试通过")

# 测试套件运行函数
async def run_integration_tests():
    """运行所有集成测试"""
    print("🚀 开始运行系统集成测试...")
    print("=" * 50)

    client = TestClient(app)
    test_user_data = {
        "email": f"integration-{datetime.now().strftime('%Y%m%d%H%M%S')}@test.com",
        "password": "testpassword123",
        "full_name": "Integration Test User"
    }
    test_organization_data = {
        "name": "Integration Test Corporation",
        "slug": f"integration-test-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "email": "admin@integration-test.com",
        "plan": "professional"
    }

    # 执行测试
    e2e_test = TestE2EUserFlow()
    api_test = TestAPIVersionIntegration()
    dataflow_test = TestDataFlowIntegration()
    security_test = TestSecurityIntegration()

    try:
        # 端到端用户流程测试
        print("\n📋 执行端到端用户流程测试...")
        token, user_info = await e2e_test.test_complete_user_registration_flow(client, test_user_data)
        organization_id, api_key = await e2e_test.test_enterprise_onboarding_flow(client, token, test_organization_data)
        model_id = await e2e_test.test_api_usage_flow(client, api_key)
        await e2e_test.test_analytics_flow(client, token, model_id)

        # API版本集成测试
        print("\n📋 执行API版本集成测试...")
        await api_test.test_api_version_compatibility(client, api_key)

        # 数据流集成测试
        print("\n📋 执行数据流集成测试...")
        await dataflow_test.test_user_behavior_tracking_flow(client, token, api_key)
        await dataflow_test.test_analytics_real_time_flow(client, token)

        # 安全集成测试
        print("\n📋 执行安全集成测试...")
        await security_test.test_authentication_integration(client, test_user_data)

        print("\n" + "=" * 50)
        print("🎉 所有系统集成测试通过！")
        print("✅ 端到端用户流程: 通过")
        print("✅ API版本兼容性: 通过")
        print("✅ 数据流集成: 通过")
        print("✅ 安全认证集成: 通过")

        return {
            "status": "success",
            "tests_passed": 4,
            "test_coverage": "core_functionality",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(run_integration_tests())
    print(f"\n测试结果: {result}")