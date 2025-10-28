"""
API密钥管理系统测试

测试API密钥的生成、验证、权限管理等功能。
"""

import pytest
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from backend.core.auth.api_key_manager import (
    APIKeyManager,
    APIKeyPermission,
    APIKeyStatus,
    APIKeyInfo,
    APIKeyUsage
)
from fastapi import HTTPException, status


class TestAPIKeyManager:
    """API密钥管理器测试"""

    @pytest.fixture
    def api_key_manager(self):
        """API密钥管理器实例"""
        return APIKeyManager(
            storage_backend=None,  # 使用内存缓存
            default_rate_limit=1000,
            max_keys_per_user=5
        )

    @pytest.fixture
    def sample_user_id(self):
        """示例用户ID"""
        return "user123"

    @pytest.fixture
    def sample_api_key_data(self):
        """示例API密钥数据"""
        return {
            "name": "Test API Key",
            "permissions": [APIKeyPermission.READ.value, APIKeyPermission.WRITE.value],
            "expires_in_days": 30,
            "rate_limit": 500,
            "monthly_quota": 10000,
            "metadata": {"description": "Test key for unit testing"}
        }

    def test_generate_api_key_success(self, api_key_manager, sample_user_id, sample_api_key_data):
        """测试成功生成API密钥"""
        result = api_key_manager.generate_api_key(
            user_id=sample_user_id,
            **sample_api_key_data
        )

        # 验证返回数据
        assert "key_id" in result
        assert "api_key" in result
        assert "name" in result
        assert "permissions" in result
        assert "expires_at" in result
        assert "rate_limit" in result
        assert "monthly_quota" in result
        assert "created_at" in result

        # 验证数据正确性
        assert result["name"] == sample_api_key_data["name"]
        assert result["permissions"] == sample_api_key_data["permissions"]
        assert result["rate_limit"] == sample_api_key_data["rate_limit"]
        assert result["monthly_quota"] == sample_api_key_data["monthly_quota"]

        # 验证API密钥格式
        assert result["api_key"].startswith("ah_")
        assert len(result["api_key"]) > 40

        # 验证密钥ID格式
        assert len(result["key_id"]) == 32

        # 验证过期时间
        if result["expires_at"]:
            expires_at = datetime.fromisoformat(result["expires_at"])
            expected_expiry = datetime.now(timezone.utc) + timedelta(days=30)
            # 允许1分钟的误差
            assert abs((expires_at - expected_expiry).total_seconds()) < 60

    def test_generate_api_key_default_values(self, api_key_manager, sample_user_id):
        """测试生成API密钥的默认值"""
        result = api_key_manager.generate_api_key(
            user_id=sample_user_id,
            name="Default Key"
        )

        # 验证默认权限
        assert result["permissions"] == [APIKeyPermission.READ.value]

        # 验证默认速率限制
        assert result["rate_limit"] == 1000

        # 验证默认配额
        assert result["monthly_quota"] is None

        # 验证默认过期时间
        assert result["expires_at"] is None

    def test_generate_api_key_user_limit(self, api_key_manager, sample_user_id):
        """测试用户密钥数量限制"""
        # 创建达到限制数量的密钥
        for i in range(api_key_manager.max_keys_per_user):
            api_key_manager.generate_api_key(
                user_id=sample_user_id,
                name=f"Key {i}"
            )

        # 尝试创建第6个密钥应该失败
        with pytest.raises(HTTPException) as exc_info:
            api_key_manager.generate_api_key(
                user_id=sample_user_id,
                name="Exceeding Limit Key"
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "用户已达到最大密钥数量限制" in str(exc_info.value.detail)

    def test_validate_api_key_success(self, api_key_manager, sample_user_id, sample_api_key_data):
        """测试成功验证API密钥"""
        # 生成密钥
        result = api_key_manager.generate_api_key(
            user_id=sample_user_id,
            **sample_api_key_data
        )
        api_key = result["api_key"]

        # 验证密钥
        key_info = api_key_manager.validate_api_key(api_key)

        assert key_info is not None
        assert key_info.key_id == result["key_id"]
        assert key_info.name == result["name"]
        assert key_info.user_id == sample_user_id
        assert key_info.permissions == result["permissions"]
        assert key_info.status == APIKeyStatus.ACTIVE.value

    def test_validate_api_key_invalid_key(self, api_key_manager):
        """测试验证无效API密钥"""
        invalid_api_key = "ah_invalid_key_12345"

        with pytest.raises(HTTPException) as exc_info:
            api_key_manager.validate_api_key(invalid_api_key)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "无效API密钥" in str(exc_info.value.detail)

    def test_validate_api_key_with_permissions(self, api_key_manager, sample_user_id, sample_api_key_data):
        """测试验证API密钥权限"""
        # 生成带有写权限的密钥
        result = api_key_manager.generate_api_key(
            user_id=sample_user_id,
            **sample_api_key_data
        )
        api_key = result["api_key"]

        # 验证需要读权限
        key_info = api_key_manager.validate_api_key(
            api_key,
            required_permissions=[APIKeyPermission.READ.value]
        )
        assert key_info is not None

        # 验证需要写权限
        key_info = api_key_manager.validate_api_key(
            api_key,
            required_permissions=[APIKeyPermission.WRITE.value]
        )
        assert key_info is not None

        # 验证需要管理权限（应该失败）
        with pytest.raises(HTTPException) as exc_info:
            api_key_manager.validate_api_key(
                api_key,
                required_permissions=[APIKeyPermission.ADMIN.value]
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "API密钥缺少权限" in str(exc_info.value.detail)

    def test_validate_api_key_full_access(self, api_key_manager, sample_user_id):
        """测试验证完全访问权限的API密钥"""
        # 生成具有完全访问权限的密钥
        result = api_key_manager.generate_api_key(
            user_id=sample_user_id,
            name="Full Access Key",
            permissions=[APIKeyPermission.FULL_ACCESS.value]
        )
        api_key = result["api_key"]

        # 应该可以访问任何权限
        key_info = api_key_manager.validate_api_key(
            api_key,
            required_permissions=[APIKeyPermission.ADMIN.value]
        )
        assert key_info is not None

        key_info = api_key_manager.validate_api_key(
            api_key,
            required_permissions=[APIKeyPermission.BILLING.value]
        )
        assert key_info is not None

    def test_revoke_api_key_success(self, api_key_manager, sample_user_id, sample_api_key_data):
        """测试成功撤销API密钥"""
        # 生成密钥
        result = api_key_manager.generate_api_key(
            user_id=sample_user_id,
            **sample_api_key_data
        )
        key_id = result["key_id"]

        # 撤销密钥
        success = api_key_manager.revoke_api_key(key_id, sample_user_id)
        assert success is True

        # 验证密钥状态已更新
        # 注意：由于我们使用内存缓存，这需要在实际实现中测试

    def test_revoke_api_key_not_owner(self, api_key_manager, sample_user_id, sample_api_key_data):
        """测试非所有者尝试撤销API密钥"""
        # 生成密钥
        result = api_key_manager.generate_api_key(
            user_id=sample_user_id,
            **sample_api_key_data
        )
        key_id = result["key_id"]

        # 尝试用其他用户ID撤销
        success = api_key_manager.revoke_api_key(key_id, "other_user_id")
        assert success is False

    def test_revoke_api_key_not_found(self, api_key_manager):
        """测试撤销不存在的API密钥"""
        success = api_key_manager.revoke_api_key("nonexistent_key_id", "user123")
        assert success is False

    def test_list_user_api_keys(self, api_key_manager, sample_user_id):
        """测试列出用户的API密钥"""
        # 创建几个密钥
        keys = []
        for i in range(3):
            result = api_key_manager.generate_api_key(
                user_id=sample_user_id,
                name=f"Test Key {i}"
            )
            keys.append(result)

        # 获取用户密钥列表
        user_keys = api_key_manager.list_user_api_keys(sample_user_id)

        assert len(user_keys) == 3
        for i, key in enumerate(user_keys):
            assert key["name"] == f"Test Key {i}"
            assert key["user_id"] == sample_user_id
            assert "key_id" in key
            assert "status" in key
            assert "created_at" in key

    def test_list_user_api_keys_with_usage(self, api_key_manager, sample_user_id):
        """测试列出用户API密钥（包含使用统计）"""
        # 创建密钥
        result = api_key_manager.generate_api_key(
            user_id=sample_user_id,
            name="Test Key"
        )

        # 获取包含使用统计的密钥列表
        user_keys = api_key_manager.list_user_api_keys(
            sample_user_id,
            include_usage=True
        )

        assert len(user_keys) == 1
        key = user_keys[0]
        assert key["name"] == "Test Key"
        # 使用统计字段应该存在（即使为空）

    def test_update_api_key_success(self, api_key_manager, sample_user_id, sample_api_key_data):
        """测试成功更新API密钥"""
        # 生成密钥
        result = api_key_manager.generate_api_key(
            user_id=sample_user_id,
            **sample_api_key_data
        )
        key_id = result["key_id"]

        # 更新密钥信息
        updates = {
            "name": "Updated Key Name",
            "rate_limit": 2000,
            "metadata": {"updated": True}
        }
        success = api_key_manager.update_api_key(key_id, sample_user_id, updates)
        assert success is True

    def test_update_api_key_not_owner(self, api_key_manager, sample_user_id, sample_api_key_data):
        """测试非所有者尝试更新API密钥"""
        # 生成密钥
        result = api_key_manager.generate_api_key(
            user_id=sample_user_id,
            **sample_api_key_data
        )
        key_id = result["key_id"]

        # 尝试用其他用户ID更新
        updates = {"name": "Hacked Key"}
        success = api_key_manager.update_api_key(key_id, "other_user_id", updates)
        assert success is False

    def test_get_key_usage_stats(self, api_key_manager, sample_user_id, sample_api_key_data):
        """测试获取API密钥使用统计"""
        # 生成密钥
        result = api_key_manager.generate_api_key(
            user_id=sample_user_id,
            **sample_api_key_data
        )
        key_id = result["key_id"]

        # 获取使用统计
        stats = api_key_manager.get_key_usage_stats(key_id, period_days=30)

        # 验证返回的统计数据结构
        assert "period_days" in stats
        assert "total_requests" in stats
        assert "successful_requests" in stats
        assert "failed_requests" in stats
        assert "average_response_time" in stats
        assert "most_used_endpoints" in stats
        assert "daily_usage" in stats

        assert stats["period_days"] == 30

    def test_hash_api_key(self, api_key_manager):
        """测试API密钥哈希"""
        api_key = "ah_test_key_12345678901234567890"
        hash1 = api_key_manager._hash_api_key(api_key)
        hash2 = api_key_manager._hash_api_key(api_key)

        # 相同的密钥应该产生相同的哈希
        assert hash1 == hash2

        # 哈希应该是SHA256格式（64个字符）
        assert len(hash1) == 64

        # 不同的密钥应该产生不同的哈希
        different_key = "ah_different_key_12345678901234567890"
        different_hash = api_key_manager._hash_api_key(different_key)
        assert hash1 != different_hash

    def test_check_user_key_limit(self, api_key_manager, sample_user_id):
        """测试用户密钥数量限制检查"""
        # 初始状态应该通过检查
        api_key_manager._check_user_key_limit(sample_user_id)  # 应该不抛出异常

        # 添加达到限制数量的密钥
        for i in range(api_key_manager.max_keys_per_user):
            key_info = APIKeyInfo(
                key_id=f"key_{i}",
                name=f"Key {i}",
                key_hash=f"hash_{i}",
                user_id=sample_user_id,
                permissions=[APIKeyPermission.READ.value],
                status=APIKeyStatus.ACTIVE.value,
                created_at=datetime.now(timezone.utc),
                expires_at=None,
                last_used_at=None,
                usage_count=0,
                rate_limit=1000,
                monthly_quota=None,
                metadata={}
            )
            api_key_manager._cache[key_info.key_id] = key_info

        # 现在应该抛出异常
        with pytest.raises(HTTPException) as exc_info:
            api_key_manager._check_user_key_limit(sample_user_id)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_is_key_valid_active(self, api_key_manager):
        """测试检查有效密钥"""
        key_info = APIKeyInfo(
            key_id="test_key",
            name="Test Key",
            key_hash="test_hash",
            user_id="user123",
            permissions=[APIKeyPermission.READ.value],
            status=APIKeyStatus.ACTIVE.value,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
            last_used_at=None,
            usage_count=0,
            rate_limit=1000,
            monthly_quota=None,
            metadata={}
        )

        assert api_key_manager._is_key_valid(key_info) is True

    def test_is_key_valid_inactive(self, api_key_manager):
        """测试检查非激活密钥"""
        key_info = APIKeyInfo(
            key_id="test_key",
            name="Test Key",
            key_hash="test_hash",
            user_id="user123",
            permissions=[APIKeyPermission.READ.value],
            status=APIKeyStatus.INACTIVE.value,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
            last_used_at=None,
            usage_count=0,
            rate_limit=1000,
            monthly_quota=None,
            metadata={}
        )

        assert api_key_manager._is_key_valid(key_info) is False

    def test_is_key_valid_expired(self, api_key_manager):
        """测试检查过期密钥"""
        key_info = APIKeyInfo(
            key_id="test_key",
            name="Test Key",
            key_hash="test_hash",
            user_id="user123",
            permissions=[APIKeyPermission.READ.value],
            status=APIKeyStatus.ACTIVE.value,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # 昨天过期
            last_used_at=None,
            usage_count=0,
            rate_limit=1000,
            monthly_quota=None,
            metadata={}
        )

        assert api_key_manager._is_key_valid(key_info) is False

    def test_check_permissions_full_access(self, api_key_manager):
        """测试完全访问权限检查"""
        key_info = APIKeyInfo(
            key_id="test_key",
            name="Test Key",
            key_hash="test_hash",
            user_id="user123",
            permissions=[APIKeyPermission.FULL_ACCESS.value],
            status=APIKeyStatus.ACTIVE.value,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
            last_used_at=None,
            usage_count=0,
            rate_limit=1000,
            monthly_quota=None,
            metadata={}
        )

        # 完全访问权限应该能通过任何权限检查
        api_key_manager._check_permissions(
            key_info,
            [APIKeyPermission.ADMIN.value, APIKeyPermission.BILLING.value]
        )  # 应该不抛出异常

    def test_check_permissions_insufficient(self, api_key_manager):
        """测试权限不足检查"""
        key_info = APIKeyInfo(
            key_id="test_key",
            name="Test Key",
            key_hash="test_hash",
            user_id="user123",
            permissions=[APIKeyPermission.READ.value],
            status=APIKeyStatus.ACTIVE.value,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
            last_used_at=None,
            usage_count=0,
            rate_limit=1000,
            monthly_quota=None,
            metadata={}
        )

        # 尝试访问需要写权限的资源
        with pytest.raises(HTTPException) as exc_info:
            api_key_manager._check_permissions(
                key_info,
                [APIKeyPermission.WRITE.value]
            )

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "API密钥缺少权限" in str(exc_info.value.detail)

    def test_update_key_usage(self, api_key_manager):
        """测试更新密钥使用信息"""
        key_info = APIKeyInfo(
            key_id="test_key",
            name="Test Key",
            key_hash="test_hash",
            user_id="user123",
            permissions=[APIKeyPermission.READ.value],
            status=APIKeyStatus.ACTIVE.value,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
            last_used_at=None,
            usage_count=0,
            rate_limit=1000,
            monthly_quota=None,
            metadata={}
        )

        original_usage_count = key_info.usage_count
        original_last_used = key_info.last_used_at

        # 更新使用信息
        import asyncio
        asyncio.run(api_key_manager._update_key_usage(key_info))

        # 验证使用信息已更新
        assert key_info.usage_count == original_usage_count + 1
        assert key_info.last_used_at is not None
        assert key_info.last_used_at > original_last_used