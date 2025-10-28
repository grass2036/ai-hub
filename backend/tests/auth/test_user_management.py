"""
用户账户管理测试

测试用户注册、登录、账户管理等功能。
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models.user import User, UserCreate, UserLogin, PasswordChange
from backend.core.auth.security import SecurityUtils
from backend.main import app


class TestUserManagement:
    """用户管理测试"""

    @pytest.fixture
    def client(self):
        """测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def db_session(self):
        """数据库会话"""
        # 创建测试数据库会话
        # 这里应该使用测试数据库配置
        pass

    @pytest.fixture
    def sample_user_data(self):
        """示例用户数据"""
        return {
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPassword123!",
            "name": "Test User"
        }

    @pytest.fixture
    def sample_login_data(self):
        """示例登录数据"""
        return {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "remember_me": False
        }

    @pytest.fixture
    def created_user(self, db_session):
        """创建测试用户"""
        user = User(
            email="existing@example.com",
            username="existinguser",
            password_hash=SecurityUtils.hash_password("ExistingPass123!"),
            name="Existing User"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def test_user_registration_success(self, client, sample_user_data):
        """测试成功用户注册"""
        with patch('backend.api.v1.auth.get_db') as mock_get_db:
            # 模拟数据库会话
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            # 模拟查询结果（邮箱不存在）
            mock_db.query.return_value.filter.return_value.first.return_value = None

            # 模拟用户创建和提交
            mock_user = MagicMock()
            mock_user.id = "user123"
            mock_user.email = sample_user_data["email"]
            mock_user.username = sample_user_data["username"]
            mock_user.name = sample_user_data["name"]
            mock_user.is_active = True
            mock_user.is_verified = False
            mock_user.created_at = "2025-01-01T00:00:00Z"
            mock_user.updated_at = "2025-01-01T00:00:00Z"

            mock_db.add.return_value = None
            mock_db.commit.return_value = None
            mock_db.refresh.return_value = None

            with patch('backend.models.user.User', return_value=mock_user):
                response = client.post("/api/v1/auth/register", json=sample_user_data)

                assert response.status_code == 201
                data = response.json()
                assert data["email"] == sample_user_data["email"]
                assert data["username"] == sample_user_data["username"]
                assert data["name"] == sample_user_data["name"]

    def test_user_registration_email_exists(self, client, sample_user_data, created_user):
        """测试注册时邮箱已存在"""
        with patch('backend.api.v1.auth.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            # 模拟邮箱已存在
            mock_db.query.return_value.filter.return_value.first.return_value = created_user

            response = client.post("/api/v1/auth/register", json=sample_user_data)

            assert response.status_code == 400
            assert "邮箱已被注册" in response.json()["detail"]

    def test_user_registration_username_exists(self, client, sample_user_data, created_user):
        """测试注册时用户名已存在"""
        with patch('backend.api.v1.auth.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            # 模拟邮箱不存在但用户名已存在
            def mock_query_side_effect(*args, **kwargs):
                if "email" in str(args):
                    mock_filter = MagicMock()
                    mock_filter.first.return_value = None  # 邮箱不存在
                    return mock_filter
                elif "username" in str(args):
                    mock_filter = MagicMock()
                    mock_filter.first.return_value = created_user  # 用户名已存在
                    return mock_filter

            mock_db.query.side_effect = mock_query_side_effect

            response = client.post("/api/v1/auth/register", json=sample_user_data)

            assert response.status_code == 400
            assert "用户名已被使用" in response.json()["detail"]

    def test_user_registration_weak_password(self, client, sample_user_data):
        """测试注册时密码强度不足"""
        # 使用弱密码
        weak_password_data = sample_user_data.copy()
        weak_password_data["password"] = "weak"

        with patch('backend.api.v1.auth.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            response = client.post("/api/v1/auth/register", json=weak_password_data)

            assert response.status_code == 400
            response_data = response.json()
            assert "密码强度不足" in response_data["detail"]["message"]
            assert len(response_data["detail"]["errors"]) > 0

    def test_user_login_success(self, client, sample_login_data, created_user):
        """测试成功用户登录"""
        with patch('backend.api.v1.auth.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            # 模拟用户查询
            mock_db.query.return_value.filter.return_value.first.return_value = created_user

            # 模拟数据库提交
            mock_db.commit.return_value = None

            with patch('backend.api.v1.auth.get_jwt_manager') as mock_jwt_manager:
                # 模拟JWT管理器
                mock_jwt_instance = MagicMock()
                mock_jwt_instance.create_access_token.return_value = "access_token_123"
                mock_jwt_instance.create_refresh_token.return_value = "refresh_token_123"
                mock_jwt_manager.return_value = mock_jwt_instance

                with patch('backend.api.v1.auth.SecurityUtils.extract_client_info') as mock_client_info:
                    mock_client_info.return_value = {"ip_address": "127.0.0.1"}

                    response = client.post("/api/v1/auth/login", json=sample_login_data)

                    assert response.status_code == 200
                    data = response.json()
                    assert "access_token" in data
                    assert "refresh_token" in data
                    assert "user" in data
                    assert data["token_type"] == "bearer"

    def test_user_login_invalid_email(self, client, sample_login_data):
        """测试登录时邮箱无效"""
        with patch('backend.api.v1.auth.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None  # 用户不存在

            response = client.post("/api/v1/auth/login", json=sample_login_data)

            assert response.status_code == 401
            assert "邮箱或密码错误" in response.json()["detail"]

    def test_user_login_invalid_password(self, client, sample_login_data, created_user):
        """测试登录时密码错误"""
        with patch('backend.api.v1.auth.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = created_user

            response = client.post("/api/v1/auth/login", json=sample_login_data)

            assert response.status_code == 401
            assert "邮箱或密码错误" in response.json()["detail"]

    def test_user_login_account_locked(self, client, sample_login_data):
        """测试登录时账户被锁定"""
        # 创建被锁定的用户
        locked_user = MagicMock()
        locked_user.email = sample_login_data["email"]
        locked_user.password_hash = SecurityUtils.hash_password("CorrectPassword123!")
        locked_user.is_active = True
        locked_user.is_locked.return_value = True  # 账户被锁定

        with patch('backend.api.v1.auth.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = locked_user

            response = client.post("/api/v1/auth/login", json=sample_login_data)

            assert response.status_code == 401
            assert "账户已被锁定" in response.json()["detail"]

    def test_user_login_account_inactive(self, client, sample_login_data):
        """测试登录时账户未激活"""
        # 创建未激活的用户
        inactive_user = MagicMock()
        inactive_user.email = sample_login_data["email"]
        inactive_user.password_hash = SecurityUtils.hash_password("CorrectPassword123!")
        inactive_user.is_active = False
        inactive_user.is_locked.return_value = False

        with patch('backend.api.v1.auth.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = inactive_user

            response = client.post("/api/v1/auth/login", json=sample_login_data)

            assert response.status_code == 401
            assert "账户已被禁用" in response.json()["detail"]

    def test_refresh_token_success(self, client):
        """测试成功刷新令牌"""
        refresh_data = {"refresh_token": "valid_refresh_token"}

        with patch('backend.api.v1.auth.get_jwt_manager') as mock_jwt_manager:
            mock_jwt_instance = MagicMock()
            mock_jwt_instance.refresh_access_token.return_value = {
                "access_token": "new_access_token",
                "token_type": "bearer",
                "expires_in": 1800
            }
            mock_jwt_manager.return_value = mock_jwt_instance

            # 模拟令牌验证
            mock_jwt_instance.verify_token.return_value = {
                "sub": "user123",
                "email": "test@example.com"
            }

            with patch('backend.api.v1.auth.get_db') as mock_get_db:
                mock_user = MagicMock()
                mock_user.id = "user123"
                mock_user.email = "test@example.com"
                mock_user.is_active = True

                mock_db = MagicMock()
                mock_db.query.return_value.filter.return_value.first.return_value = mock_user
                mock_get_db.return_value = mock_db

                response = client.post("/api/v1/auth/refresh", json=refresh_data)

                assert response.status_code == 200
                data = response.json()
                assert "access_token" in data
                assert data["access_token"] == "new_access_token"

    def test_get_current_user_info(self, client):
        """测试获取当前用户信息"""
        # 模拟认证用户
        with patch('backend.api.v1.users.get_auth_middleware') as mock_auth_middleware:
            mock_middleware = MagicMock()
            mock_auth_middleware.return_value = mock_middleware

            mock_user = {
                "user_id": "user123",
                "email": "test@example.com",
                "name": "Test User"
            }
            mock_middleware.get_current_user_required.return_value = mock_user

            response = client.get("/api/v1/users/me")

            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "test@example.com"
            assert data["name"] == "Test User"

    def test_update_current_user_success(self, client):
        """测试成功更新当前用户信息"""
        update_data = {
            "name": "Updated Name",
            "username": "updateduser",
            "phone": "+1234567890"
        }

        with patch('backend.api.v1.users.get_auth_middleware') as mock_auth_middleware:
            mock_middleware = MagicMock()
            mock_auth_middleware.return_value = mock_middleware

            mock_user_info = {"user_id": "user123"}
            mock_middleware.get_current_user_required.return_value = mock_user_info

            with patch('backend.api.v1.users.get_db') as mock_get_db:
                mock_db = MagicMock()
                mock_get_db.return_value = mock_db

                # 模拟用户查询和更新
                mock_user = MagicMock()
                mock_user.id = "user123"
                mock_user.email = "test@example.com"
                mock_db.query.return_value.filter.return_value.first.return_value = mock_user
                mock_db.commit.return_value = None

                response = client.put("/api/v1/users/me", json=update_data)

                assert response.status_code == 200
                data = response.json()
                # 验证返回了更新后的用户信息

    def test_change_password_success(self, client):
        """测试成功修改密码"""
        password_data = {
            "current_password": "CurrentPassword123!",
            "new_password": "NewPassword456!"
        }

        with patch('backend.api.v1.auth.get_auth_middleware') as mock_auth_middleware:
            mock_middleware = MagicMock()
            mock_auth_middleware.return_value = mock_middleware

            mock_user_info = {"user_id": "user123"}
            mock_middleware.get_current_user_required.return_value = mock_user_info

            with patch('backend.api.v1.auth.get_db') as mock_get_db:
                mock_db = MagicMock()
                mock_get_db.return_value = mock_db

                # 模拟用户查询
                mock_user = MagicMock()
                mock_user.password_hash = SecurityUtils.hash_password("CurrentPassword123!")
                mock_db.query.return_value.filter.return_value.first.return_value = mock_user
                mock_db.commit.return_value = None

                response = client.post("/api/v1/auth/change-password", json=password_data)

                assert response.status_code == 200
                assert "密码修改成功" in response.json()["message"]

    def test_change_password_wrong_current_password(self, client):
        """测试修改密码时当前密码错误"""
        password_data = {
            "current_password": "WrongPassword123!",
            "new_password": "NewPassword456!"
        }

        with patch('backend.api.v1.auth.get_auth_middleware') as mock_auth_middleware:
            mock_middleware = MagicMock()
            mock_auth_middleware.return_value = mock_middleware

            mock_user_info = {"user_id": "user123"}
            mock_middleware.get_current_user_required.return_value = mock_user_info

            with patch('backend.api.v1.auth.get_db') as mock_get_db:
                mock_db = MagicMock()
                mock_get_db.return_value = mock_db

                # 模拟用户查询
                mock_user = MagicMock()
                mock_user.password_hash = SecurityUtils.hash_password("CurrentPassword123!")
                mock_db.query.return_value.filter.return_value.first.return_value = mock_user

                response = client.post("/api/v1/auth/change-password", json=password_data)

                assert response.status_code == 400
                assert "当前密码错误" in response.json()["detail"]

    def test_forgot_password_success(self, client):
        """测试忘记密码"""
        reset_data = {"email": "test@example.com"}

        with patch('backend.api.v1.auth.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            # 模拟用户存在
            mock_user = MagicMock()
            mock_user.email = "test@example.com"
            mock_db.query.return_value.filter.return_value.first.return_value = mock_user

            response = client.post("/api/v1/auth/forgot-password", json=reset_data)

            assert response.status_code == 200
            assert "如果邮箱存在，重置链接已发送" in response.json()["message"]

    def test_forgot_password_user_not_exists(self, client):
        """测试忘记密码时用户不存在"""
        reset_data = {"email": "nonexistent@example.com"}

        with patch('backend.api.v1.auth.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            response = client.post("/api/v1/auth/forgot-password", json=reset_data)

            assert response.status_code == 200
            # 为了安全，即使用户不存在也返回成功消息
            assert "如果邮箱存在，重置链接已发送" in response.json()["message"]

    def test_logout_success(self, client):
        """测试成功登出"""
        with patch('backend.api.v1.auth.get_auth_middleware') as mock_auth_middleware:
            mock_middleware = MagicMock()
            mock_auth_middleware.return_value = mock_middleware

            mock_user_info = {"user_id": "user123"}
            mock_middleware.get_current_user.return_value = mock_user_info

            with patch('backend.api.v1.auth.get_jwt_manager') as mock_jwt_manager:
                mock_jwt_instance = MagicMock()
                mock_jwt_manager.revoke_token.return_value = True
                mock_jwt_manager.return_value = mock_jwt_instance

                response = client.post(
                    "/api/v1/auth/logout",
                    headers={"Authorization": "Bearer test_token"}
                )

                assert response.status_code == 200
                assert "登出成功" in response.json()["message"]

    def test_verify_token_success(self, client):
        """测试验证令牌成功"""
        with patch('backend.api.v1.auth.get_jwt_manager') as mock_jwt_manager:
            mock_jwt_instance = MagicMock()
            mock_jwt_instance.verify_token.return_value = {
                "sub": "user123",
                "email": "test@example.com",
                "exp": 1234567890
            }
            mock_jwt_manager.return_value = mock_jwt_instance

            response = client.get(
                "/api/v1/auth/verify-token",
                headers={"Authorization": "Bearer valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["user_id"] == "user123"
            assert data["email"] == "test@example.com"

    def test_verify_token_invalid(self, client):
        """测试验证无效令牌"""
        response = client.get("/api/v1/auth/verify-token")

        assert response.status_code == 401
        assert "缺少认证信息" in response.json()["detail"]