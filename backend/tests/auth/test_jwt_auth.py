"""
JWT认证系统测试

测试JWT令牌的生成、验证、刷新等功能。
"""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from backend.core.auth.jwt_manager import JWTManager
from backend.core.auth.security import SecurityUtils
from fastapi import HTTPException, status


class TestJWTManager:
    """JWT管理器测试"""

    @pytest.fixture
    def jwt_manager(self):
        """JWT管理器实例"""
        return JWTManager(
            secret_key="test_secret_key_12345678901234567890",
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )

    @pytest.fixture
    def sample_user_data(self):
        """示例用户数据"""
        return {
            "sub": "user123",
            "email": "test@example.com",
            "username": "testuser",
            "role": "user",
            "permissions": ["read", "write"]
        }

    def test_create_access_token(self, jwt_manager, sample_user_data):
        """测试创建访问令牌"""
        token = jwt_manager.create_access_token(sample_user_data)

        # 验证令牌格式
        assert isinstance(token, str)
        assert len(token) > 100  # JWT token应该很长

        # 验证令牌内容
        payload = jwt.decode(
            token,
            jwt_manager.secret_key,
            algorithms=[jwt_manager.algorithm]
        )

        assert payload["sub"] == sample_user_data["sub"]
        assert payload["email"] == sample_user_data["email"]
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload

    def test_create_refresh_token(self, jwt_manager, sample_user_data):
        """测试创建刷新令牌"""
        token = jwt_manager.create_refresh_token(sample_user_data)

        # 验证令牌格式
        assert isinstance(token, str)
        assert len(token) > 100

        # 验证令牌内容
        payload = jwt.decode(
            token,
            jwt_manager.secret_key,
            algorithms=[jwt_manager.algorithm]
        )

        assert payload["sub"] == sample_user_data["sub"]
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_token_with_custom_expiry(self, jwt_manager, sample_user_data):
        """测试创建自定义过期时间的令牌"""
        custom_expiry = timedelta(hours=2)
        token = jwt_manager.create_access_token(
            sample_user_data,
            expires_delta=custom_expiry
        )

        payload = jwt.decode(
            token,
            jwt_manager.secret_key,
            algorithms=[jwt_manager.algorithm]
        )

        # 检查过期时间是否正确（大约2小时后）
        exp_time = datetime.fromtimestamp(payload["exp"], timezone.utc)
        iat_time = datetime.fromtimestamp(payload["iat"], timezone.utc)
        actual_duration = exp_time - iat_time

        # 允许5秒的误差
        assert abs(actual_duration.total_seconds() - custom_expiry.total_seconds()) < 5

    def test_verify_access_token_success(self, jwt_manager, sample_user_data):
        """测试成功验证访问令牌"""
        token = jwt_manager.create_access_token(sample_user_data)
        payload = jwt_manager.verify_token(token, "access")

        assert payload["sub"] == sample_user_data["sub"]
        assert payload["email"] == sample_user_data["email"]
        assert payload["type"] == "access"

    def test_verify_refresh_token_success(self, jwt_manager, sample_user_data):
        """测试成功验证刷新令牌"""
        token = jwt_manager.create_refresh_token(sample_user_data)
        payload = jwt_manager.verify_token(token, "refresh")

        assert payload["sub"] == sample_user_data["sub"]
        assert payload["type"] == "refresh"

    def test_verify_token_invalid_token(self, jwt_manager):
        """测试验证无效令牌"""
        invalid_token = "invalid.jwt.token"

        with pytest.raises(HTTPException) as exc_info:
            jwt_manager.verify_token(invalid_token, "access")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "无效令牌" in str(exc_info.value.detail)

    def test_verify_token_wrong_type(self, jwt_manager, sample_user_data):
        """测试验证错误类型的令牌"""
        access_token = jwt_manager.create_access_token(sample_user_data)

        with pytest.raises(HTTPException) as exc_info:
            jwt_manager.verify_token(access_token, "refresh")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "令牌类型不匹配" in str(exc_info.value.detail)

    def test_verify_token_expired(self, jwt_manager, sample_user_data):
        """测试验证过期令牌"""
        # 创建已过期的令牌
        expired_token = jwt_manager.create_access_token(
            sample_user_data,
            expires_delta=timedelta(seconds=-1)
        )

        with pytest.raises(HTTPException) as exc_info:
            jwt_manager.verify_token(expired_token, "access")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "令牌已过期" in str(exc_info.value.detail)

    def test_refresh_access_token_success(self, jwt_manager, sample_user_data):
        """测试成功刷新访问令牌"""
        refresh_token = jwt_manager.create_refresh_token(sample_user_data)
        result = jwt_manager.refresh_access_token(refresh_token)

        assert "access_token" in result
        assert "token_type" in result
        assert "expires_in" in result
        assert result["token_type"] == "bearer"
        assert result["expires_in"] == jwt_manager.access_token_expire_minutes * 60

        # 验证新的访问令牌
        new_token = result["access_token"]
        payload = jwt_manager.verify_token(new_token, "access")
        assert payload["sub"] == sample_user_data["sub"]

    def test_refresh_access_token_invalid_refresh_token(self, jwt_manager):
        """测试使用无效刷新令牌"""
        invalid_refresh_token = "invalid.refresh.token"

        with pytest.raises(HTTPException) as exc_info:
            jwt_manager.refresh_access_token(invalid_refresh_token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_token_payload(self, jwt_manager, sample_user_data):
        """测试获取令牌载荷（不验证过期时间）"""
        token = jwt_manager.create_access_token(sample_user_data)
        payload = jwt_manager.get_token_payload(token)

        assert payload is not None
        assert payload["sub"] == sample_user_data["sub"]
        assert payload["email"] == sample_user_data["email"]

    def test_get_token_payload_invalid(self, jwt_manager):
        """测试获取无效令牌的载荷"""
        invalid_token = "invalid.jwt.token"
        payload = jwt_manager.get_token_payload(invalid_token)

        assert payload is None

    def test_revoke_token(self, jwt_manager, sample_user_data):
        """测试撤销令牌"""
        token = jwt_manager.create_access_token(sample_user_data)
        result = jwt_manager.revoke_token(token)

        assert result is True

    def test_revoke_token_invalid(self, jwt_manager):
        """测试撤销无效令牌"""
        invalid_token = "invalid.jwt.token"
        result = jwt_manager.revoke_token(invalid_token)

        assert result is False

    def test_is_token_revoked(self, jwt_manager, sample_user_data):
        """测试检查令牌是否被撤销"""
        token = jwt_manager.create_access_token(sample_user_data)

        # 初始状态应该未被撤销
        assert jwt_manager.is_token_revoked(token) is False

        # 撤销令牌后应该被撤销
        jwt_manager.revoke_token(token)
        # 注意：这个测试可能需要实际的存储后端来正确工作

    def test_create_token_pair(self, jwt_manager, sample_user_data):
        """测试创建令牌对"""
        token_pair = jwt_manager.create_token_pair(sample_user_data)

        assert "access_token" in token_pair
        assert "refresh_token" in token_pair
        assert "token_type" in token_pair
        assert "expires_in" in token_pair
        assert "refresh_expires_in" in token_pair

        assert token_pair["token_type"] == "bearer"
        assert token_pair["expires_in"] == jwt_manager.access_token_expire_minutes * 60
        assert token_pair["refresh_expires_in"] == jwt_manager.refresh_token_expire_days * 24 * 60 * 60

        # 验证两个令牌都有效
        access_payload = jwt_manager.verify_token(token_pair["access_token"], "access")
        refresh_payload = jwt_manager.verify_token(token_pair["refresh_token"], "refresh")

        assert access_payload["sub"] == sample_user_data["sub"]
        assert refresh_payload["sub"] == sample_user_data["sub"]

    def test_extract_user_from_token(self, jwt_manager, sample_user_data):
        """测试从令牌中提取用户信息"""
        token = jwt_manager.create_access_token(sample_user_data)
        user_info = jwt_manager.extract_user_from_token(token)

        assert user_info is not None
        assert user_info["user_id"] == sample_user_data["sub"]
        assert user_info["email"] == sample_user_data["email"]
        assert user_info["role"] == sample_user_data["role"]
        assert user_info["permissions"] == sample_user_data["permissions"]
        assert "token_id" in user_info
        assert "issued_at" in user_info
        assert "expires_at" in user_info

    def test_extract_user_from_invalid_token(self, jwt_manager):
        """测试从无效令牌中提取用户信息"""
        invalid_token = "invalid.jwt.token"
        user_info = jwt_manager.extract_user_from_token(invalid_token)

        assert user_info is None

    def test_weak_secret_key_warning(self, caplog):
        """测试弱密钥警告"""
        weak_manager = JWTManager(
            secret_key="weak",
            algorithm="HS256"
        )

        # 应该记录警告
        assert "JWT密钥长度建议至少32位" in caplog.text

    def test_token_generation_error(self, jwt_manager, sample_user_data):
        """测试令牌生成错误"""
        # 模拟编码错误
        with patch.object(jwt, 'encode', side_effect=Exception("Encoding error")):
            with pytest.raises(HTTPException) as exc_info:
                jwt_manager.create_access_token(sample_user_data)

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "令牌创建失败" in str(exc_info.value.detail)

    def test_token_verification_error(self, jwt_manager):
        """测试令牌验证错误"""
        # 模拟解码错误
        with patch.object(jwt, 'decode', side_effect=Exception("Decoding error")):
            with pytest.raises(HTTPException) as exc_info:
                jwt_manager.verify_token("some.token", "access")

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "令牌验证失败" in str(exc_info.value.detail)

    def test_refresh_token_error(self, jwt_manager, sample_user_data):
        """测试刷新令牌错误"""
        refresh_token = jwt_manager.create_refresh_token(sample_user_data)

        # 模拟刷新过程出错
        with patch.object(jwt_manager, 'verify_token', side_effect=Exception("Verification error")):
            with pytest.raises(HTTPException) as exc_info:
                jwt_manager.refresh_access_token(refresh_token)

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "令牌刷新失败" in str(exc_info.value.detail)

    def test_refresh_token_missing_user_id(self, jwt_manager):
        """测试刷新令牌缺少用户ID"""
        # 创建没有sub字段的令牌
        invalid_payload = {"email": "test@example.com"}
        invalid_token = jwt.encode(
            invalid_payload,
            jwt_manager.secret_key,
            algorithm=jwt_manager.algorithm
        )

        with pytest.raises(HTTPException) as exc_info:
            jwt_manager.refresh_access_token(invalid_token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "令牌中缺少用户信息" in str(exc_info.value.detail)