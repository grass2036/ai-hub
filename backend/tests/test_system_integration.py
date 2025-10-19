"""
System Integration Tests
Week 4 Day 27: System Integration Testing and Documentation
"""

import pytest
import asyncio
import httpx
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.developer import Developer, DeveloperAPIKey
from backend.models.async_task import AsyncTask, BatchJob
from backend.services.developer_service import DeveloperService
from backend.services.batch_service import BatchProcessingService
from backend.core.cache import get_cache_manager
from backend.core.monitoring import get_metrics_collector
from backend.core.security import get_security_validator


class TestSystemIntegration:
    """系统集成测试套件"""

    @pytest.fixture
    def test_client(self):
        """测试客户端"""
        return httpx.AsyncClient(base_url="http://localhost:8001")

    @pytest.fixture
    def test_db(self):
        """测试数据库会话"""
        db = next(get_db())
        try:
            yield db
        finally:
            db.close()

    @pytest.fixture
    async def test_developer_data(self, test_db: Session):
        """测试开发者数据"""
        developer_service = DeveloperService(test_db)

        # 创建测试开发者
        developer_data = await developer_service.register_developer(
            email="test@example.com",
            password="test_password123",
            full_name="Test Developer"
        )

        return developer_data

    @pytest.fixture
    async def test_api_key(self, test_db: Session, test_developer_data):
        """测试API密钥"""
        developer = test_db.query(Developer).filter(Developer.email == "test@example.com").first()

        api_key = DeveloperAPIKey(
            name="Test API Key",
            key_prefix="test_key_123456",
            key_hash="test_hash",
            salt="test_salt",
            is_active=True,
            developer_id=developer.id
        )

        test_db.add(api_key)
        test_db.commit()
        test_db.refresh(api_key)

        return api_key

    @pytest.fixture
    def auth_headers(self, test_developer_data):
        """认证头"""
        return {
            "Authorization": f"Bearer {test_developer_data['access_token']}"
        }

    async def test_health_check(self, test_client):
        """测试健康检查接口"""
        response = await test_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "checks" in data

    async def test_api_status(self, test_client):
        """测试API状态接口"""
        response = await test_client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert "ai_services" in data
        assert "database" in data

    async def test_developer_registration_flow(self, test_client):
        """测试开发者注册流程"""
        # 注册新开发者
        register_data = {
            "email": "integration_test@example.com",
            "password": "test_password123",
            "full_name": "Integration Test Developer"
        }

        response = await test_client.post("/api/v1/developer/auth/register", json=register_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "access_token" in data["data"]
        assert "developer" in data["data"]

        # 验证开发者信息
        access_token = data["data"]["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await test_client.get("/api/v1/developer/auth/me", headers=headers)
        assert response.status_code == 200
        me_data = response.json()
        assert me_data["data"]["email"] == "integration_test@example.com"

    async def test_api_key_management_flow(self, test_client, auth_headers):
        """测试API密钥管理流程"""
        # 创建API密钥
        create_data = {
            "name": "Integration Test Key",
            "permissions": ["chat", "usage"]
        }

        response = await test_client.post("/api/v1/developer/keys", json=create_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "api_key" in data["data"]

        api_key = data["data"]["api_key"]
        api_key_id = data["data"]["id"]

        # 获取API密钥列表
        response = await test_client.get("/api/v1/developer/keys", headers=auth_headers)
        assert response.status_code == 200
        keys_data = response.json()
        assert len(keys_data["data"]) >= 1
        assert any(key["id"] == api_key_id for key in keys_data["data"])

        # 删除API密钥
        response = await test_client.delete(f"/api/v1/developer/keys/{api_key_id}", headers=auth_headers)
        assert response.status_code == 200

    async def test_chat_flow(self, test_client, test_api_key):
        """测试聊天流程"""
        headers = {"X-API-Key": test_api_key.key_prefix}

        # 发送聊天请求
        chat_data = {
            "prompt": "Hello, this is a test message.",
            "model": "gpt-4o-mini"
        }

        response = await test_client.post("/api/v1/chat/completions", json=chat_data, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data["data"]
        assert "model" in data["data"]
        assert "tokens_used" in data["data"]

    async def test_usage_statistics_flow(self, test_client, auth_headers):
        """测试使用统计流程"""
        # 获取使用量概览
        response = await test_client.get("/api/v1/developer/usage/overview", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total_requests" in data["data"]
        assert "total_tokens" in data["data"]

        # 获取使用量分析
        response = await test_client.get("/api/v1/developer/usage/analytics", headers=auth_headers)
        assert response.status_code == 200
        analytics_data = response.json()
        assert "data" in analytics_data

    async def test_batch_processing_flow(self, test_client, auth_headers):
        """测试批量处理流程"""
        # 创建批量生成任务
        batch_data = {
            "name": "Integration Test Batch",
            "model": "gpt-4o-mini",
            "prompts": ["Test prompt 1", "Test prompt 2"],
            "max_concurrent_tasks": 2
        }

        response = await test_client.post("/api/v1/developer/batch/generation", json=batch_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data["data"]

        job_id = data["data"]["job_id"]

        # 获取批量任务状态
        response = await test_client.get(f"/api/v1/developer/batch/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        job_data = response.json()
        assert "data" in job_data
        assert job_data["data"]["job_id"] == job_id

    async def test_monitoring_flow(self, test_client, auth_headers):
        """测试监控流程"""
        # 获取系统统计
        response = await test_client.get("/api/v1/monitoring/metrics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

        # 获取告警信息
        response = await test_client.get("/api/v1/monitoring/alerts", headers=auth_headers)
        assert response.status_code == 200
        alerts_data = response.json()
        assert "data" in alerts_data

    async def test_caching_system(self, test_db: Session):
        """测试缓存系统"""
        cache_manager = await get_cache_manager()

        # 测试缓存设置和获取
        test_key = "test_cache_key"
        test_value = {"test": "data", "timestamp": datetime.utcnow().isoformat()}

        # 设置缓存
        success = await cache_manager.set(test_key, test_value, expire=60)
        assert success == True

        # 获取缓存
        cached_value = await cache_manager.get(test_key)
        assert cached_value is not None
        assert cached_value["test"] == "data"

        # 删除缓存
        success = await cache_manager.delete(test_key)
        assert success == True

        # 验证删除
        cached_value = await cache_manager.get(test_key)
        assert cached_value is None

    async def test_security_validation(self):
        """测试安全验证"""
        security_validator = get_security_validator()

        # 测试正常输入
        valid_input = "This is a normal input"
        result = security_validator.validate_input(valid_input)
        assert result["valid"] == True

        # 测试SQL注入
        sql_injection = "'; DROP TABLE users; --"
        result = security_validator.validate_input(sql_injection)
        assert result["valid"] == False
        assert "sql injection" in " ".join(result["errors"]).lower()

        # 测试XSS
        xss_input = "<script>alert('xss')</script>"
        result = security_validator.validate_input(xss_input)
        assert result["valid"] == False
        assert "xss" in " ".join(result["errors"]).lower()

    async def test_metrics_collection(self):
        """测试指标收集"""
        metrics_collector = await get_metrics_collector()

        # 测试计数器
        metrics_collector.increment_counter("test_counter", 1)
        stats = metrics_collector.get_metric_summary("test_counter")
        assert stats["count"] == 1
        assert stats["sum"] == 1

        # 测试仪表
        metrics_collector.set_gauge("test_gauge", 42)
        stats = metrics_collector.get_metric_summary("test_gauge")
        assert stats["count"] == 1
        assert stats["latest"] == 42

        # 测试直方图
        metrics_collector.record_histogram("test_histogram", 100)
        stats = metrics_collector.get_metric_summary("test_histogram")
        assert stats["count"] == 1
        assert stats["avg"] == 100

    async def test_rate_limiting(self, test_client):
        """测试限流功能"""
        # 模拟大量请求
        responses = []
        for i in range(5):
            response = await test_client.get("/api/v1/health")
            responses.append(response.status_code)

        # 初始请求应该成功
        assert responses[0] == 200

        # 注意：由于这是集成测试，实际的限流行为可能需要调整
        # 在实际环境中，应该测试限流是否按预期工作

    async def test_error_handling(self, test_client):
        """测试错误处理"""
        # 测试不存在的端点
        response = await test_client.get("/api/v1/nonexistent")
        assert response.status_code == 404

        # 测试无效的请求体
        response = await test_client.post(
            "/api/v1/developer/auth/login",
            json={"invalid": "data"}
        )
        assert response.status_code == 422  # 验证错误

        # 测试无权限访问
        response = await test_client.get("/api/v1/developer/auth/me")
        assert response.status_code == 401  # 未授权

    async def test_database_operations(self, test_db: Session):
        """测试数据库操作"""
        # 测试开发者创建
        developer = Developer(
            email="db_test@example.com",
            password_hash="test_hash",
            full_name="DB Test Developer"
        )
        test_db.add(developer)
        test_db.commit()
        test_db.refresh(developer)

        assert developer.id is not None
        assert developer.email == "db_test@example.com"

        # 测试API密钥创建
        api_key = DeveloperAPIKey(
            name="DB Test Key",
            key_prefix="db_test_key",
            key_hash="test_hash",
            salt="test_salt",
            is_active=True,
            developer_id=developer.id
        )
        test_db.add(api_key)
        test_db.commit()
        test_db.refresh(api_key)

        assert api_key.id is not None
        assert api_key.developer_id == developer.id

        # 测试异步任务创建
        async_task = AsyncTask(
            task_id="test_task_id",
            task_type="test_task",
            developer_id=developer.id,
            status="pending"
        )
        test_db.add(async_task)
        test_db.commit()
        test_db.refresh(async_task)

        assert async_task.id is not None
        assert async_task.task_id == "test_task_id"

        # 清理测试数据
        test_db.delete(async_task)
        test_db.delete(api_key)
        test_db.delete(developer)
        test_db.commit()

    async def test_concurrent_operations(self, test_client, auth_headers):
        """测试并发操作"""
        # 并发创建多个API密钥
        async def create_api_key(index):
            data = {
                "name": f"Concurrent Test Key {index}",
                "permissions": ["chat"]
            }
            response = await test_client.post("/api/v1/developer/keys", json=data, headers=auth_headers)
            return response.status_code, response.json() if response.status_code == 200 else None

        # 并发执行
        tasks = [create_api_key(i) for i in range(3)]
        results = await asyncio.gather(*tasks)

        # 验证所有请求都成功
        for status, data in results:
            assert status == 200
            assert data["success"] == True

    async def test_data_consistency(self, test_db: Session):
        """测试数据一致性"""
        # 创建相关数据
        developer = Developer(
            email="consistency_test@example.com",
            password_hash="test_hash",
            full_name="Consistency Test Developer"
        )
        test_db.add(developer)
        test_db.commit()
        test_db.refresh(developer)

        # 创建API密钥
        api_key = DeveloperAPIKey(
            name="Consistency Test Key",
            key_prefix="consistency_key",
            key_hash="test_hash",
            salt="test_salt",
            is_active=True,
            developer_id=developer.id
        )
        test_db.add(api_key)
        test_db.commit()
        test_db.refresh(api_key)

        # 验证外键关系
        retrieved_api_key = test_db.query(DeveloperAPIKey).filter(DeveloperAPIKey.id == api_key.id).first()
        assert retrieved_api_key.developer_id == developer.id

        # 清理
        test_db.delete(retrieved_api_key)
        test_db.delete(developer)
        test_db.commit()


class TestPerformanceIntegration:
    """性能集成测试"""

    async def test_api_response_times(self, test_client):
        """测试API响应时间"""
        endpoints = [
            "/api/v1/health",
            "/api/v1/status",
            "/api/v1/models"
        ]

        for endpoint in endpoints:
            start_time = datetime.utcnow()
            response = await test_client.get(endpoint)
            end_time = datetime.utcnow()

            response_time = (end_time - start_time).total_seconds()

            # API响应时间应该小于2秒
            assert response_time < 2.0
            assert response.status_code == 200

    async def test_batch_request_performance(self, test_client, auth_headers):
        """测试批量请求性能"""
        # 测试批量获取数据
        start_time = datetime.utcnow()

        tasks = [
            test_client.get("/api/v1/developer/keys", headers=auth_headers),
            test_client.get("/api/v1/developer/usage/overview", headers=auth_headers),
            test_client.get("/api/v1/monitoring/metrics", headers=auth_headers)
        ]

        results = await asyncio.gather(*tasks)
        end_time = datetime.utcnow()

        total_time = (end_time - start_time).total_seconds()

        # 并发请求应该更快
        assert total_time < 5.0

        # 所有请求应该成功
        for response in results:
            assert response.status_code == 200

    async def test_memory_usage(self):
        """测试内存使用"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss

        # 执行一些内存密集操作
        test_data = []
        for i in range(1000):
            test_data.append({
                "id": i,
                "name": f"test_item_{i}",
                "data": "x" * 100  # 100字符的数据
            })

        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before

        # 内存增长应该合理（小于100MB）
        assert memory_increase < 100 * 1024 * 1024  # 100MB

        # 清理
        del test_data

    async def test_database_connection_pool(self, test_db: Session):
        """测试数据库连接池"""
        # 执行多个并发查询
        async def concurrent_query():
            return test_db.execute("SELECT 1").scalar()

        tasks = [concurrent_query() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # 所有查询应该成功
        for result in results:
            assert result == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])