# Week 2 Testing Guide
# Week 2 测试指南

## 概述

本文档提供了AI Hub平台Week 2企业多租户架构开发的完整测试指南，包括测试策略、测试用例、执行方法和质量保证标准。

## 测试架构

### 测试金字塔

```
          E2E Tests (端到端测试)
               少量
        Integration Tests (集成测试)
              适量
         Unit Tests (单元测试)
             大量
```

### 测试分类

#### 1. 单元测试 (Unit Tests)
- **目标**: 测试单个函数和类的逻辑
- **覆盖率要求**: > 80%
- **执行频率**: 每次代码提交
- **示例**: 模型验证、工具函数、业务逻辑

#### 2. 集成测试 (Integration Tests)
- **目标**: 测试组件间的交互
- **覆盖率要求**: > 70%
- **执行频率**: 每次构建
- **示例**: API端点、数据库操作、外部服务调用

#### 3. 端到端测试 (E2E Tests)
- **目标**: 测试完整的用户流程
- **覆盖率要求**: 主要用户路径
- **执行频率**: 每日构建
- **示例**: 用户注册、组织创建、API使用

## 测试环境配置

### 环境变量

```bash
# 测试环境配置
TEST_DATABASE_URL=sqlite+aiosqlite:///./test.db
ENVIRONMENT=testing
DEBUG=true
SECRET_KEY=test-secret-key
JWT_SECRET_KEY=test-jwt-secret-key
OPENROUTER_API_KEY=test-key
GEMINI_API_KEY=test-key
```

### 测试数据库

```python
# conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from backend.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture(scope="function")
async def db() -> AsyncSession:
    """提供测试数据库会话"""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)

    # 创建表结构
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 创建会话
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    # 清理
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
```

## 核心测试用例

### 1. 多租户数据隔离测试

#### 测试文件: `test_multi_tenant_isolation.py`

```python
class TestMultiTenantIsolation:
    """多租户数据隔离测试"""

    async def test_organization_isolation(self, test_data):
        """测试组织数据隔离"""
        # 验证用户只能访问自己的组织数据
        # 确保跨组织数据泄漏不会发生

    async def test_team_isolation(self, test_data):
        """测试团队数据隔离"""
        # 验证团队数据按组织隔离

    async def test_budget_isolation(self, test_data):
        """测试预算数据隔离"""
        # 验证预算数据不会跨组织泄漏
```

#### 关键测试点:

1. **数据查询隔离**
   ```python
   # 用户1只能看到自己的组织
   org1_query = await db.execute(
       "SELECT * FROM organizations WHERE id = :org_id",
       {"org_id": user1_org_id}
   )
   ```

2. **跨组织数据泄漏检查**
   ```python
   # 尝试跨组织访问应该失败
   leak_query = await db.execute(
       "SELECT t.* FROM teams t WHERE t.organization_id = :org1_id AND t.id IN (SELECT id FROM teams WHERE organization_id = :org2_id)",
       {"org1_id": org1_id, "org2_id": org2_id}
   )
   assert leak_query.fetchone() is None
   ```

### 2. 权限系统测试

#### 测试文件: `test_permission_system.py`

```python
class TestPermissionSystem:
    """权限系统测试"""

    async def test_owner_permissions(self, test_data):
        """测试Owner权限"""
        # Owner应该拥有所有权限

    async def test_admin_permissions(self, test_data):
        """测试Admin权限"""
        # Admin不能删除组织，但可以管理其他资源

    async def test_member_permissions(self, test_data):
        """测试Member权限"""
        # Member只有基础权限

    async def test_role_hierarchy(self, test_data):
        """测试角色层次结构"""
        # Owner > Admin > Member > Viewer
```

#### 权限矩阵:

| 操作 | Owner | Admin | Member | Viewer |
|------|-------|-------|--------|--------|
| 删除组织 | ✅ | ❌ | ❌ | ❌ |
| 编辑组织 | ✅ | ✅ | ❌ | ❌ |
| 管理成员 | ✅ | ✅ | ❌ | ❌ |
| 管理团队 | ✅ | ✅ | ❌ | ❌ |
| 查看数据 | ✅ | ✅ | ✅ | ✅ |

### 3. API集成测试

#### 测试文件: `test_api_integration.py`

```python
class TestAPIIntegration:
    """API集成测试"""

    async def test_organization_management_flow(self, test_data):
        """测试组织管理完整流程"""
        # 创建 -> 读取 -> 更新 -> 删除

    async def test_team_management_flow(self, test_data):
        """测试团队管理完整流程"""

    async def test_budget_management_flow(self, test_data):
        """测试预算管理完整流程"""

    async def test_error_handling(self, test_data):
        """测试错误处理"""
        # 404, 403, 422等错误响应
```

#### API测试要点:

1. **认证和授权**
   ```python
   # 测试无认证访问
   response = await client.get("/api/v1/organizations/")
   assert response.status_code == 401

   # 测试权限验证
   response = await client.delete("/api/v1/organizations/{org_id}", headers=headers)
   assert response.status_code in [200, 403]
   ```

2. **数据验证**
   ```python
   # 测试输入验证
   invalid_data = {"name": "", "slug": "invalid slug with spaces"}
   response = await client.post("/api/v1/organizations/", json=invalid_data)
   assert response.status_code == 422
   ```

### 4. 性能测试

#### 测试文件: `test_performance.py`

```python
class TestDatabasePerformance:
    """数据库性能测试"""

    async def test_organization_query_performance(self, test_data):
        """测试组织查询性能"""
        # 查询时间应小于100ms

    async def test_join_query_performance(self, test_data):
        """测试关联查询性能"""
        # 关联查询时间应小于200ms

    async def test_concurrent_requests(self, test_data):
        """测试并发请求性能"""
        # 20个并发请求应在5秒内完成
```

#### 性能指标:

| 操作类型 | 响应时间要求 | 并发要求 |
|----------|-------------|----------|
| 简单查询 | < 100ms | 100+ 并发 |
| 关联查询 | < 200ms | 50+ 并发 |
| 复杂聚合 | < 300ms | 20+ 并发 |
| API响应 | < 2s | 100+ 并发 |

## 测试执行

### 本地测试

```bash
# 安装测试依赖
cd backend
pip install pytest pytest-asyncio httpx aiosqlite

# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_multi_tenant_isolation.py -v

# 运行特定测试类
pytest tests/test_permission_system.py::TestPermissionSystem -v

# 运行特定测试方法
pytest tests/test_api_integration.py::TestAPIIntegration::test_organization_management_flow -v

# 生成覆盖率报告
pytest tests/ --cov=backend --cov-report=html
```

### CI/CD测试

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov

    - name: Run tests
      run: |
        cd backend
        pytest tests/ --cov=backend --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
```

## 测试数据管理

### 测试夹具 (Fixtures)

```python
@pytest.fixture
async def test_data():
    """创建标准测试数据"""
    async for db in get_db():
        # 创建组织
        org = Organization(name="Test Org", slug="test-org")
        db.add(org)

        # 创建用户
        user = User(email="test@example.com")
        db.add(user)

        # 创建成员关系
        member = Member(user_id=user.id, organization_id=org.id, role="owner")
        db.add(member)

        await db.commit()

        yield {"org": org, "user": user, "member": member}

        # 清理数据
        await db.execute(text("DELETE FROM members"))
        await db.execute(text("DELETE FROM organizations"))
        await db.execute(text("DELETE FROM users"))
        await db.commit()
```

### 数据库清理策略

1. **事务回滚**: 每个测试在独立事务中执行，测试后回滚
2. **表清理**: 测试结束后清理相关数据表
3. **隔离数据库**: 使用内存SQLite数据库进行测试

## 错误处理测试

### 自定义异常测试

```python
def test_custom_exceptions():
    """测试自定义异常"""

    # 测试组织不存在异常
    with pytest.raises(OrganizationNotFoundError):
        raise OrganizationNotFoundError("invalid-org-id")

    # 测试权限拒绝异常
    with pytest.raises(PermissionDeniedError):
        raise PermissionDeniedError("user-123", "organization", "delete")
```

### HTTP异常测试

```python
async def test_http_exception_handling():
    """测试HTTP异常处理"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 测试404错误
        response = await client.get("/api/v1/organizations/nonexistent")
        assert response.status_code == 404
        assert "error" in response.json()

        # 测试401错误
        response = await client.get("/api/v1/organizations/")
        assert response.status_code == 401
```

## 测试报告

### 覆盖率报告

```bash
# 生成HTML覆盖率报告
pytest --cov=backend --cov-report=html

# 查看报告
open htmlcov/index.html
```

### 测试结果示例

```
============================= test session starts ==============================
collected 45 items

tests/test_multi_tenant_isolation.py::TestMultiTenantIsolation::test_organization_isolation PASSED [  2%]
tests/test_multi_tenant_isolation.py::TestMultiTenantIsolation::test_team_isolation PASSED [  4%]
tests/test_permission_system.py::TestPermissionSystem::test_owner_permissions PASSED [  6%]
tests/test_api_integration.py::TestAPIIntegration::test_organization_management_flow PASSED [  8%]
...

================= 45 passed, 2 warnings in 12.34s ==================```

## 最佳实践

### 1. 测试命名规范

```python
def test_{feature}_{scenario}_{expected_result}():
    """测试_{功能}_{场景}_{期望结果}"""

# 示例
def test_organization_creation_with_valid_data_should_succeed():
    pass

def test_organization_creation_with_duplicate_slug_should_fail():
    pass
```

### 2. 测试结构 (AAA模式)

```python
def test_user_can_create_organization():
    # Arrange (准备)
    user_data = {"email": "test@example.com", "name": "Test User"}
    org_data = {"name": "Test Org", "slug": "test-org"}

    # Act (执行)
    response = client.post("/api/v1/organizations/", json=org_data, headers=headers)

    # Assert (断言)
    assert response.status_code == 201
    assert response.json()["name"] == "Test Org"
```

### 3. 测试隔离

- 每个测试应该独立运行
- 不依赖测试执行顺序
- 使用独立的测试数据
- 在测试后清理状态

### 4. Mock和Stub

```python
from unittest.mock import patch, AsyncMock

@patch('backend.services.external_api.call_external_service')
async def test_external_service_integration(mock_service):
    """测试外部服务集成"""
    mock_service.return_value = {"status": "success"}

    # 执行测试
    result = await some_function()

    # 验证外部服务被正确调用
    mock_service.assert_called_once()
```

## 持续集成

### 预提交钩子

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest tests/
        language: system
        pass_filenames: false
        always_run: true
```

### 质量门禁

- **测试覆盖率**: ≥ 80%
- **测试通过率**: 100%
- **性能回归**: 响应时间不超过基准20%
- **安全扫描**: 无高危漏洞

## 故障排查

### 常见问题

1. **数据库连接错误**
   ```bash
   # 检查测试数据库配置
   echo $TEST_DATABASE_URL
   ```

2. **异步测试问题**
   ```python
   # 确保测试函数是异步的
   async def test_something():
       await some_async_function()
   ```

3. **导入错误**
   ```python
   # 检查Python路径和模块结构
   import sys
   print(sys.path)
   ```

### 调试技巧

```python
# 使用pytest的调试功能
pytest -s -v tests/test_specific.py::test_function

# 在测试中添加断点
import pdb; pdb.set_trace()

# 使用pytest的日志功能
pytest --log-cli-level=DEBUG tests/
```

## 总结

Week 2的测试体系确保了多租户架构的可靠性和安全性。通过全面的单元测试、集成测试和性能测试，我们可以：

1. **保证数据隔离**: 确保租户间数据不会泄漏
2. **验证权限系统**: 确保用户只能访问授权资源
3. **监控性能**: 确保系统响应时间符合要求
4. **提升代码质量**: 通过高覆盖率测试发现潜在问题

测试是Week 2成功的关键，为后续的功能开发和生产部署提供了坚实的基础。