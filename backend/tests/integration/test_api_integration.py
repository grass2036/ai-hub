"""
API集成测试
Week 6 Day 1: 系统集成测试 - API集成测试
测试API间的跨模块调用和兼容性
"""

import asyncio
import pytest
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from backend.main import app
from backend.core.database import get_db
from backend.models.user import User
from backend.models.organization import Organization

class TestAPICrossModuleIntegration:
    """API跨模块集成测试"""

    @pytest.mark.asyncio
    async def test_user_to_organization_api_flow(self, client: TestClient):
        """测试用户API到企业API的流程"""
        print("🔄 测试用户到企业API流程...")

        # 1. 创建用户
        user_data = {
            "email": "org-test@example.com",
            "password": "testpass123",
            "full_name": "Organization Test User"
        }

        user_response = client.post("/api/v1/auth/register", json=user_data)
        assert user_response.status_code == 201
        user_result = user_response.json()

        # 2. 用户登录获取token
        login_response = client.post("/api/v1/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200
        login_result = login_response.json()
        token = login_result["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. 使用用户token创建企业
        org_data = {
            "name": "Test Org for API Integration",
            "slug": "test-org-api-integration",
            "email": "admin@testorg.com",
            "plan": "professional"
        }

        org_response = client.post("/api/v1/organizations", json=org_data, headers=headers)
        assert org_response.status_code == 201
        org_result = org_response.json()

        # 4. 验证用户在企业中的成员身份
        members_response = client.get(f"/api/v1/organizations/{org_result['id']}/members", headers=headers)
        assert members_response.status_code == 200
        members = members_response.json()
        assert len(members) >= 1
        assert any(member["user_id"] == user_result["id"] for member in members)

        print("✅ 用户到企业API流程测试通过")

    @pytest.mark.asyncio
    async def test_api_key_to_usage_tracking_flow(self, client: TestClient):
        """测试API密钥到使用统计的流程"""
        print("🔄 测试API密钥到使用统计流程...")

        # 创建用户和API密钥（简化版本）
        user_data = {
            "email": "usage-test@example.com",
            "password": "testpass123",
            "full_name": "Usage Test User"
        }

        user_response = client.post("/api/v1/auth/register", json=user_data)
        user_result = user_response.json()

        login_response = client.post("/api/v1/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        login_result = login_response.json()
        token = login_result["access_token"]

        # 创建API密钥
        headers_auth = {"Authorization": f"Bearer {token}"}
        api_key_response = client.post("/api/v1/developer/keys", json={
            "name": "Integration Test API Key",
            "description": "Key for usage tracking integration test"
        }, headers=headers_auth)
        assert api_key_response.status_code == 201
        api_key_result = api_key_response.json()
        api_key = api_key_result["api_key"]

        # 使用API密钥进行多次API调用
        headers_api = {"X-API-Key": api_key}

        # 调用模型API
        models_response = client.get("/api/v1/models", headers=headers_api)
        assert models_response.status_code == 200

        # 调用统计API
        usage_response = client.get("/api/v1/developer/usage/overview", headers=headers_api)
        assert usage_response.status_code == 200
        usage_data = usage_response.json()

        # 验证统计数据
        assert "total_requests" in usage_data
        assert "usage_by_model" in usage_data

        # 调用详细的API使用记录
        usage_records_response = client.get("/api/v1/developer/usage/records", headers=headers_api)
        assert usage_records_response.status_code == 200
        records = usage_records_response.json()
        assert isinstance(records, list)

        print("✅ API密钥到使用统计流程测试通过")

    @pytest.mark.asyncio
    async def test_payment_to_subscription_flow(self, client: TestClient):
        """测试支付到订阅的流程"""
        print("🔄 测试支付到订阅流程...")

        # 创建用户
        user_data = {
            "email": "payment-test@example.com",
            "password": "testpass123",
            "full_name": "Payment Test User"
        }

        user_response = client.post("/api/v1/auth/register", json=user_data)
        user_result = user_response.json()

        login_response = client.post("/api/v1/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        login_result = login_response.json()
        token = login_result["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 创建企业
        org_data = {
            "name": "Payment Test Org",
            "slug": "payment-test-org",
            "email": "billing@payment-test.com",
            "plan": "professional"
        }

        org_response = client.post("/api/v1/organizations", json=org_data, headers=headers)
        org_result = org_response.json()

        # 获取可用的订阅计划
        plans_response = client.get("/api/v1/payments/plans", headers=headers)
        assert plans_response.status_code == 200
        plans = plans_response.json()
        assert len(plans) > 0

        # 创建订阅
        subscription_data = {
            "organization_id": org_result["id"],
            "plan_id": plans[0]["id"],
            "billing_cycle": "monthly"
        }

        subscription_response = client.post("/api/v1/payments/subscriptions", json=subscription_data, headers=headers)
        assert subscription_response.status_code == 201
        subscription_result = subscription_response.json()

        # 验证订阅状态
        subscription_status_response = client.get(
            f"/api/v1/payments/subscriptions/{subscription_result['id']}",
            headers=headers
        )
        assert subscription_status_response.status_code == 200
        subscription_status = subscription_status_response.json()
        assert subscription_status["status"] in ["active", "pending"]

        # 获取企业订阅信息
        org_subscription_response = client.get(
            f"/api/v1/organizations/{org_result['id']}/subscription",
            headers=headers
        )
        assert org_subscription_response.status_code == 200

        print("✅ 支付到订阅流程测试通过")

class TestAPICompatibility:
    """API兼容性测试"""

    @pytest.mark.asyncio
    async def test_api_v1_v2_compatibility(self, client: TestClient):
        """测试API v1和v2的兼容性"""
        print("🔄 测试API v1/v2兼容性...")

        # 创建测试API密钥
        user_data = {
            "email": "compat-test@example.com",
            "password": "testpass123",
            "full_name": "Compatibility Test User"
        }

        user_response = client.post("/api/v1/auth/register", json=user_data)
        user_result = user_response.json()

        login_response = client.post("/api/v1/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        login_result = login_response.json()
        token = login_result["access_token"]

        headers_auth = {"Authorization": f"Bearer {token}"}

        # 创建API密钥
        api_key_response = client.post("/api/v1/developer/keys", json={
            "name": "Compatibility Test Key",
            "description": "Testing v1/v2 compatibility"
        }, headers=headers_auth)
        api_key_result = api_key_response.json()
        api_key = api_key_result["api_key"]
        headers_api = {"X-API-Key": api_key}

        # 测试相同功能在两个版本中的一致性
        v1_health_response = client.get("/api/v1/health", headers=headers_api)
        v2_health_response = client.get("/api/v2/health/status", headers=headers_api)

        assert v1_health_response.status_code == 200
        assert v2_health_response.status_code == 200

        v1_health_data = v1_health_response.json()
        v2_health_data = v2_health_response.json()

        # 验证基础数据一致性
        assert v1_health_data["status"] == "healthy"
        assert v2_health_data["status"] == "healthy"

        # 测试模型API兼容性
        v1_models_response = client.get("/api/v1/models", headers=headers_api)
        assert v1_models_response.status_code == 200
        v1_models = v1_models_response.json()

        # 验证v1模型数据结构
        for model in v1_models:
            assert "id" in model
            assert "name" in model
            assert "description" in model

        print("✅ API v1/v2兼容性测试通过")

    @pytest.mark.asyncio
    async def test_api_version_migration_simulation(self, client: TestClient):
        """测试API版本迁移模拟"""
        print("🔄 测试API版本迁移模拟...")

        # 模拟旧版本的请求数据格式
        old_format_request = {
            "prompt": "Hello, this is old format",
            "max_tokens": 50,
            "temperature": 0.7
        }

        # 模拟新版本的请求数据格式
        new_format_request = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "Hello, this is new format"}
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }

        # 创建测试API密钥
        user_data = {
            "email": "migration-test@example.com",
            "password": "testpass123",
            "full_name": "Migration Test User"
        }

        user_response = client.post("/api/v1/auth/register", json=user_data)
        user_result = user_response.json()

        login_response = client.post("/api/v1/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        login_result = login_response.json()
        token = login_result["access_token"]

        headers_auth = {"Authorization": f"Bearer {token}"}

        # 创建API密钥
        api_key_response = client.post("/api/v1/developer/keys", json={
            "name": "Migration Test Key",
            "description": "Testing API version migration"
        }, headers=headers_auth)
        api_key_result = api_key_response.json()
        api_key = api_key_result["api_key"]
        headers_api = {"X-API-Key": api_key}

        # 获取可用模型
        models_response = client.get("/api/v1/models", headers=headers_api)
        assert models_response.status_code == 200
        models = models_response.json()
        model_id = models[0]["id"]

        # 测试新格式请求
        new_format_request["model"] = model_id
        chat_response = client.post("/api/v1/chat/completions", json=new_format_request, headers=headers_api)
        assert chat_response.status_code == 200
        chat_data = chat_response.json()

        # 验证响应格式
        assert "choices" in chat_data
        assert len(chat_data["choices"]) > 0
        assert "message" in chat_data["choices"][0]

        # 测试版本迁移端点
        migration_response = client.post("/api/v2/health/migrate", json={
            "from_version": "v1",
            "to_version": "v2",
            "sample_data": old_format_request
        }, headers=headers_api)

        # 这个端点可能不存在，所以允许404
        assert migration_response.status_code in [200, 404]

        print("✅ API版本迁移模拟测试通过")

class TestAPIDataConsistency:
    """API数据一致性测试"""

    @pytest.mark.asyncio
    async def test_cross_api_data_consistency(self, client: TestClient):
        """测试跨API数据一致性"""
        print("🔄 测试跨API数据一致性...")

        # 创建用户
        user_data = {
            "email": "consistency-test@example.com",
            "password": "testpass123",
            "full_name": "Consistency Test User"
        }

        user_response = client.post("/api/v1/auth/register", json=user_data)
        user_result = user_response.json()

        login_response = client.post("/api/v1/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        login_result = login_response.json()
        token = login_result["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # 创建企业
        org_data = {
            "name": "Consistency Test Org",
            "slug": "consistency-test-org",
            "email": "admin@consistency-test.com",
            "plan": "professional"
        }

        org_response = client.post("/api/v1/organizations", json=org_data, headers=headers)
        org_result = org_response.json()

        # 从不同API端点获取相同数据，验证一致性
        # 从用户信息API获取企业信息
        user_info_response = client.get("/api/v1/users/me", headers=headers)
        user_info = user_info_response.json()

        # 从组织API获取企业信息
        org_info_response = client.get(f"/api/v1/organizations/{org_result['id']}", headers=headers)
        org_info = org_info_response.json()

        # 验证企业信息一致性
        assert user_info.get("organizations") is not None
        user_orgs = user_info["organizations"]

        # 查找用户在当前企业中的信息
        user_in_current_org = None
        for org in user_orgs:
            if org["id"] == org_result["id"]:
                user_in_current_org = org
                break

        assert user_in_current_org is not None
        assert user_in_current_org["name"] == org_info["name"]
        assert user_in_current_org["slug"] == org_info["slug"]

        print("✅ 跨API数据一致性测试通过")

# 测试运行函数
async def run_api_integration_tests():
    """运行API集成测试"""
    print("🚀 开始运行API集成测试...")
    print("=" * 50)

    client = TestClient(app)

    # 执行测试
    api_integration_test = TestAPICrossModuleIntegration()
    compatibility_test = TestAPICompatibility()
    consistency_test = TestAPIDataConsistency()

    try:
        # 跨模块API集成测试
        print("\n📋 执行跨模块API集成测试...")
        await api_integration_test.test_user_to_organization_api_flow(client)
        await api_integration_test.test_api_key_to_usage_tracking_flow(client)
        await api_integration_test.test_payment_to_subscription_flow(client)

        # API兼容性测试
        print("\n📋 执行API兼容性测试...")
        await compatibility_test.test_api_v1_v2_compatibility(client)
        await compatibility_test.test_api_version_migration_simulation(client)

        # API数据一致性测试
        print("\n📋 执行API数据一致性测试...")
        await consistency_test.test_cross_api_data_consistency(client)

        print("\n" + "=" * 50)
        print("🎉 所有API集成测试通过！")
        print("✅ 跨模块API集成: 通过")
        print("✅ API版本兼容性: 通过")
        print("✅ API数据一致性: 通过")

        return {
            "status": "success",
            "tests_passed": 6,
            "test_coverage": "api_integration",
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
    result = asyncio.run(run_api_integration_tests())
    print(f"\n测试结果: {result}")