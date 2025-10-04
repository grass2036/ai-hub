# Day 1 执行清单 - 数据库模型和API密钥系统

> 从零开始的详细操作步骤 - 保姆级教程

**日期**: Week 1 Day 1
**预计时间**: 8小时
**核心目标**: 完成数据库设计和API密钥认证系统

---

## ⏰ 时间规划

```
09:00-11:00  数据库模型设计和迁移 (2小时)
11:00-11:15  休息
11:15-13:00  API密钥管理器 (1.75小时)
13:00-14:00  午休
14:00-15:45  API密钥管理器续 (1.75小时)
15:45-16:00  休息
16:00-18:00  用户认证API (2小时)
18:00-19:00  晚休
19:00-20:00  单元测试 (1小时)
20:00-20:30  代码审查和提交 (0.5小时)
```

---

## 📋 详细执行步骤

### 阶段1: 环境准备 (09:00-09:30, 30分钟)

#### ✅ 检查开发环境

**1. 检查Python版本**
```bash
python --version  # 应该是 Python 3.11+
```

**2. 检查PostgreSQL**
```bash
psql --version  # 应该是 PostgreSQL 14+

# 测试连接
psql -U postgres -c "SELECT version();"
```

**3. 检查Redis**
```bash
redis-cli ping  # 应该返回 PONG

# 如果Redis未启动
redis-server --daemonize yes
```

**4. 激活虚拟环境**
```bash
cd /Users/chiyingjie/code/git/ai-hub

# 如果虚拟环境不存在，创建它
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
```

**5. 安装依赖**
```bash
# 确保requirements.txt包含以下依赖
pip install -r requirements.txt

# 或者手动安装
pip install fastapi sqlalchemy asyncpg psycopg2-binary \
    pydantic pydantic-settings python-jose passlib bcrypt \
    pytest pytest-asyncio redis
```

#### 📝 检查点 #1
- [ ] Python 3.11+ 已安装
- [ ] PostgreSQL 已启动并可连接
- [ ] Redis 已启动
- [ ] 虚拟环境已激活
- [ ] 所有依赖已安装

---

### 阶段2: 创建项目结构 (09:30-09:45, 15分钟)

#### 创建目录结构

```bash
cd /Users/chiyingjie/code/git/ai-hub

# 创建后端目录
mkdir -p backend/models
mkdir -p backend/core
mkdir -p backend/api/v1/developer
mkdir -p backend/middleware
mkdir -p backend/tests
mkdir -p backend/config

# 创建数据库迁移目录
mkdir -p migrations

# 创建__init__.py文件
touch backend/__init__.py
touch backend/models/__init__.py
touch backend/core/__init__.py
touch backend/api/__init__.py
touch backend/api/v1/__init__.py
touch backend/api/v1/developer/__init__.py
touch backend/middleware/__init__.py
touch backend/tests/__init__.py
touch backend/config/__init__.py
```

#### 验证目录结构

```bash
# 查看创建的目录
tree backend -L 3

# 预期输出：
# backend/
# ├── __init__.py
# ├── api/
# │   ├── __init__.py
# │   └── v1/
# │       ├── __init__.py
# │       └── developer/
# ├── config/
# ├── core/
# ├── middleware/
# ├── models/
# └── tests/
```

#### 📝 检查点 #2
- [ ] backend/models/ 目录已创建
- [ ] backend/core/ 目录已创建
- [ ] backend/api/v1/developer/ 目录已创建
- [ ] backend/tests/ 目录已创建
- [ ] migrations/ 目录已创建
- [ ] 所有__init__.py文件已创建

---

### 阶段3: 数据库配置 (09:45-10:15, 30分钟)

#### 创建数据库

```bash
# 连接到PostgreSQL
psql -U postgres

# 在psql中执行
CREATE DATABASE ai_hub;
CREATE USER ai_hub_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE ai_hub TO ai_hub_user;

# 退出psql
\q
```

#### 创建数据库配置文件

**文件: `backend/config/settings.py`**

```python
"""
应用配置
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置类"""

    # 应用基础配置
    app_name: str = "AI Hub"
    environment: str = "development"
    debug: bool = True

    # 数据库配置
    database_url: str = "postgresql+asyncpg://ai_hub_user:your_secure_password@localhost:5432/ai_hub"

    # Redis配置
    redis_url: str = "redis://localhost:6379/0"

    # JWT配置
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    # API配置
    api_v1_prefix: str = "/api/v1"

    # CORS配置
    cors_origins: list = ["http://localhost:3000", "http://localhost:8000"]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    return Settings()
```

#### 创建数据库连接文件

**文件: `backend/database.py`**

```python
"""
数据库连接配置
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from backend.config.settings import get_settings

settings = get_settings()

# 创建异步引擎
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True
)

# 创建异步会话工厂
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 创建Base类
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    数据库依赖注入
    用于FastAPI的Depends
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库（创建所有表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
```

#### 创建.env文件

**文件: `.env`**

```bash
# 应用配置
APP_NAME=AI Hub
ENVIRONMENT=development
DEBUG=true

# 数据库配置
DATABASE_URL=postgresql+asyncpg://ai_hub_user:your_secure_password@localhost:5432/ai_hub

# Redis配置
REDIS_URL=redis://localhost:6379/0

# JWT配置
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production-abc123xyz789
JWT_ALGORITHM=HS256
JWT_EXPIRE_DAYS=7

# OpenRouter API配置
OPENROUTER_API_KEY=your_openrouter_key_here

# Gemini API配置
GEMINI_API_KEY=your_gemini_key_here
```

**⚠️ 重要**: 将.env添加到.gitignore

```bash
# 添加到.gitignore
echo ".env" >> .gitignore
echo "venv/" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo ".pytest_cache/" >> .gitignore
```

#### 📝 检查点 #3
- [ ] PostgreSQL数据库 `ai_hub` 已创建
- [ ] 数据库用户 `ai_hub_user` 已创建
- [ ] backend/config/settings.py 已创建
- [ ] backend/database.py 已创建
- [ ] .env 文件已创建并配置
- [ ] .gitignore 已更新

---

### 阶段4: 数据库模型 (10:15-11:00, 45分钟)

#### 创建用户模型

**文件: `backend/models/user.py`**

从Week1详细开发任务清单.md的第76-169行复制完整代码

**关键点**:
- 包含UserPlan枚举（FREE, PRO, ENTERPRISE）
- User类包含所有必要字段
- 实现quota_remaining和quota_percentage属性
- 定义PLAN_QUOTAS和PLAN_PRICES配置

#### 创建API密钥模型

**文件: `backend/models/api_key.py`**

从Week1详细开发任务清单.md的第171-220行复制完整代码

**关键点**:
- APIKey类包含所有必要字段
- 实现is_expired和is_valid属性
- 与User建立关系

#### 创建订阅模型

**文件: `backend/models/subscription.py`**

从Week1详细开发任务清单.md的第222-268行复制完整代码

#### 创建模型索引文件

**文件: `backend/models/__init__.py`**

从Week1详细开发任务清单.md的第270-285行复制完整代码

#### 创建数据库迁移脚本

**文件: `migrations/001_initial_schema.sql`**

从Week1详细开发任务清单.md的第287-330行复制完整SQL代码

#### 执行数据库迁移

```bash
# 执行迁移
psql -U postgres -d ai_hub -f migrations/001_initial_schema.sql

# 验证表是否创建成功
psql -U postgres -d ai_hub -c "\dt"

# 预期输出：
#             List of relations
#  Schema |     Name      | Type  |    Owner
# --------+---------------+-------+--------------
#  public | api_keys      | table | ai_hub_user
#  public | subscriptions | table | ai_hub_user
#  public | users         | table | ai_hub_user
```

#### 📝 检查点 #4
- [ ] backend/models/user.py 已创建
- [ ] backend/models/api_key.py 已创建
- [ ] backend/models/subscription.py 已创建
- [ ] backend/models/__init__.py 已创建
- [ ] migrations/001_initial_schema.sql 已创建
- [ ] 数据库表已成功创建（users, api_keys, subscriptions）

---

### 🎯 中途检查 (11:00-11:15, 15分钟休息)

在继续之前，确认以下内容：

```bash
# 1. 检查Python模块是否可导入
python -c "from backend.models import User, APIKey; print('Models imported successfully!')"

# 2. 检查数据库连接
python -c "from backend.database import get_settings; print(get_settings().database_url)"

# 3. 检查数据库表
psql -U postgres -d ai_hub -c "SELECT tablename FROM pg_tables WHERE schemaname='public';"
```

如果以上任何一个失败，停下来解决问题！

---

### 阶段5: API密钥管理器 (11:15-13:00, 1小时45分钟)

#### 创建API密钥管理器

**文件: `backend/core/api_key_manager.py`**

从Week1详细开发任务清单.md的第335-492行复制完整代码

**实现的功能**:
1. `generate_key()` - 生成格式为 `ai-hub-xxx` 的密钥
2. `hash_key()` - 使用SHA256哈希密钥
3. `get_key_prefix()` - 获取密钥显示前缀
4. `create_api_key()` - 创建新密钥（返回原始密钥，仅一次）
5. `validate_api_key()` - 验证密钥有效性
6. `revoke_api_key()` - 撤销密钥
7. `list_user_api_keys()` - 列出用户所有密钥

#### 测试API密钥管理器

创建临时测试文件验证功能：

**文件: `test_api_key_temp.py`** (临时文件)

```python
"""
临时测试API密钥管理器
"""
import asyncio
from backend.core.api_key_manager import api_key_manager


async def test_key_generation():
    """测试密钥生成"""
    key = api_key_manager.generate_key()
    print(f"✓ 生成的密钥: {key}")
    assert key.startswith("ai-hub-")

    # 测试哈希
    key_hash = api_key_manager.hash_key(key)
    print(f"✓ 密钥哈希: {key_hash[:20]}...")
    assert len(key_hash) == 64  # SHA256

    # 测试前缀
    prefix = api_key_manager.get_key_prefix(key)
    print(f"✓ 显示前缀: {prefix}")
    assert len(prefix) <= 20


if __name__ == "__main__":
    asyncio.run(test_key_generation())
```

运行测试：
```bash
python test_api_key_temp.py

# 预期输出：
# ✓ 生成的密钥: ai-hub-xxxxxxxxxxx
# ✓ 密钥哈希: abcdef...
# ✓ 显示前缀: ai-hub-xxx...
```

#### 📝 检查点 #5
- [ ] backend/core/api_key_manager.py 已创建
- [ ] generate_key() 函数可生成正确格式的密钥
- [ ] hash_key() 函数可正确哈希密钥
- [ ] 临时测试通过

---

### 🍽️ 午休 (13:00-14:00)

休息充电，下午继续！

---

### 阶段6: 认证工具 (14:00-15:45, 1小时45分钟)

#### 创建认证工具模块

**文件: `backend/core/auth.py`**

从Week1详细开发任务清单.md的第497-591行复制完整代码

**实现的功能**:
1. `hash_password()` - 密码哈希（bcrypt）
2. `verify_password()` - 密码验证
3. `create_access_token()` - 创建JWT令牌
4. `decode_access_token()` - 解码JWT令牌
5. `get_user_by_email()` - 通过邮箱查找用户
6. `authenticate_user()` - 用户认证

#### 测试认证工具

**文件: `test_auth_temp.py`** (临时文件)

```python
"""
临时测试认证工具
"""
from backend.core.auth import hash_password, verify_password, create_access_token, decode_access_token


def test_password():
    """测试密码哈希和验证"""
    password = "test_password_123"

    # 哈希密码
    hashed = hash_password(password)
    print(f"✓ 密码哈希: {hashed[:30]}...")

    # 验证正确密码
    assert verify_password(password, hashed)
    print("✓ 正确密码验证通过")

    # 验证错误密码
    assert not verify_password("wrong_password", hashed)
    print("✓ 错误密码验证失败（符合预期）")


def test_jwt():
    """测试JWT令牌"""
    user_id = 123

    # 创建令牌
    token = create_access_token(user_id)
    print(f"✓ JWT令牌: {token[:30]}...")

    # 解码令牌
    decoded_id = decode_access_token(token)
    assert decoded_id == user_id
    print(f"✓ 解码用户ID: {decoded_id}")

    # 测试无效令牌
    invalid = decode_access_token("invalid_token")
    assert invalid is None
    print("✓ 无效令牌返回None（符合预期）")


if __name__ == "__main__":
    test_password()
    print()
    test_jwt()
```

运行测试：
```bash
python test_auth_temp.py

# 预期输出：
# ✓ 密码哈希: $2b$12$...
# ✓ 正确密码验证通过
# ✓ 错误密码验证失败（符合预期）
#
# ✓ JWT令牌: eyJhbGciOiJIUzI1NiIsInR5cCI6...
# ✓ 解码用户ID: 123
# ✓ 无效令牌返回None（符合预期）
```

#### 📝 检查点 #6
- [ ] backend/core/auth.py 已创建
- [ ] 密码哈希和验证功能正常
- [ ] JWT令牌创建和解码功能正常
- [ ] 临时测试通过

---

### 🎯 下午中途休息 (15:45-16:00)

---

### 阶段7: 用户认证API (16:00-18:00, 2小时)

#### 创建认证API

**文件: `backend/api/v1/auth.py`**

从Week1详细开发任务清单.md的第596-818行复制完整代码

**实现的端点**:
1. `POST /api/v1/auth/register` - 用户注册
2. `POST /api/v1/auth/login` - 用户登录
3. `GET /api/v1/auth/me` - 获取当前用户信息
4. `POST /api/v1/auth/logout` - 用户登出

#### 创建API密钥管理API

**文件: `backend/api/v1/developer/api_keys.py`**

从Week1详细开发任务清单.md的第823-995行复制完整代码

**实现的端点**:
1. `POST /api/v1/developer/api-keys` - 创建API密钥
2. `GET /api/v1/developer/api-keys` - 列出API密钥
3. `DELETE /api/v1/developer/api-keys/{key_id}` - 撤销API密钥

#### 创建主应用文件（如果不存在）

**文件: `backend/main.py`**

```python
"""
FastAPI主应用
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config.settings import get_settings
from backend.database import init_db, close_db
from backend.api.v1 import auth
from backend.api.v1.developer import api_keys

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await init_db()
    yield
    # 关闭时清理资源
    await close_db()


# 创建应用实例
app = FastAPI(
    title=settings.app_name,
    description="企业级多模型AI聚合平台",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix=settings.api_v1_prefix, tags=["Authentication"])
app.include_router(api_keys.router, prefix=f"{settings.api_v1_prefix}/developer", tags=["API Keys"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to AI Hub API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
```

#### 启动应用测试

```bash
# 启动FastAPI应用
python backend/main.py

# 应该看到：
# INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
# INFO:     Started reloader process
# INFO:     Started server process
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
```

#### 测试API端点（使用curl）

```bash
# 1. 测试健康检查
curl http://localhost:8001/health

# 2. 测试用户注册
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123456",
    "full_name": "Test User"
  }'

# 3. 测试用户登录
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123456"
  }'

# 4. 访问API文档
# 打开浏览器访问: http://localhost:8001/docs
```

#### 📝 检查点 #7
- [ ] backend/api/v1/auth.py 已创建
- [ ] backend/api/v1/developer/api_keys.py 已创建
- [ ] backend/main.py 已创建或更新
- [ ] FastAPI应用可以启动
- [ ] /health 端点返回正常
- [ ] /docs 页面可以访问
- [ ] 用户注册API工作正常
- [ ] 用户登录API工作正常

---

### 🍽️ 晚休 (18:00-19:00)

---

### 阶段8: 单元测试 (19:00-20:00, 1小时)

#### 创建测试配置

**文件: `backend/tests/conftest.py`**

从Week1详细开发任务清单.md的第1000-1028行复制完整代码

#### 创建API密钥管理器测试

**文件: `backend/tests/test_api_key_manager.py`**

从Week1详细开发任务清单.md的第1030-1133行复制完整代码

#### 创建认证测试

**文件: `backend/tests/test_auth.py`**

```python
"""
认证功能测试
"""
import pytest
from backend.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)


def test_hash_password():
    """测试密码哈希"""
    password = "test_password_123"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2b$")


def test_verify_password():
    """测试密码验证"""
    password = "test_password_123"
    hashed = hash_password(password)

    # 正确密码
    assert verify_password(password, hashed) is True

    # 错误密码
    assert verify_password("wrong_password", hashed) is False


def test_create_access_token():
    """测试JWT令牌创建"""
    user_id = 123
    token = create_access_token(user_id)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 20


def test_decode_access_token():
    """测试JWT令牌解码"""
    user_id = 456
    token = create_access_token(user_id)

    # 解码有效令牌
    decoded_id = decode_access_token(token)
    assert decoded_id == user_id

    # 解码无效令牌
    invalid_id = decode_access_token("invalid_token_xyz")
    assert invalid_id is None
```

#### 运行测试

```bash
# 运行所有测试
pytest backend/tests/ -v

# 运行特定测试
pytest backend/tests/test_auth.py -v

# 运行测试并显示覆盖率
pytest backend/tests/ --cov=backend --cov-report=html

# 预期输出：
# ======================== test session starts =========================
# collected 8 items
#
# backend/tests/test_api_key_manager.py::test_generate_key PASSED
# backend/tests/test_api_key_manager.py::test_hash_key PASSED
# backend/tests/test_api_key_manager.py::test_create_api_key PASSED
# backend/tests/test_api_key_manager.py::test_validate_api_key PASSED
# backend/tests/test_auth.py::test_hash_password PASSED
# backend/tests/test_auth.py::test_verify_password PASSED
# backend/tests/test_auth.py::test_create_access_token PASSED
# backend/tests/test_auth.py::test_decode_access_token PASSED
#
# ========================= 8 passed in 2.34s ==========================
```

#### 📝 检查点 #8
- [ ] backend/tests/conftest.py 已创建
- [ ] backend/tests/test_api_key_manager.py 已创建
- [ ] backend/tests/test_auth.py 已创建
- [ ] 所有单元测试通过
- [ ] 测试覆盖率 >70%

---

### 阶段9: 代码审查和提交 (20:00-20:30, 30分钟)

#### 代码质量检查

```bash
# 1. 检查代码格式（如果安装了black）
black backend/ --check

# 2. 检查导入顺序（如果安装了isort）
isort backend/ --check

# 3. 类型检查（如果安装了mypy）
mypy backend/ --ignore-missing-imports

# 4. 代码风格检查（如果安装了flake8）
flake8 backend/ --max-line-length=100
```

#### Git提交

```bash
# 查看修改
git status

# 添加文件
git add backend/
git add migrations/
git add .env.example  # 不要添加.env本身！
git add .gitignore

# 提交代码
git commit -m "feat(day1): 完成数据库模型和API密钥认证系统

- 添加User, APIKey, Subscription数据库模型
- 实现API密钥生成、验证、撤销功能
- 实现JWT认证和密码哈希
- 添加用户注册、登录API
- 添加API密钥管理API
- 完成单元测试，覆盖率>70%

Day 1完成 ✅"

# 查看提交
git log -1
```

#### 创建Day 1完成报告

**文件: `docs/progress/day1-completion.md`**

```markdown
# Day 1 完成报告

**日期**: 2025-10-01
**用时**: 8小时
**状态**: ✅ 已完成

## 完成的工作

### 数据库设计
- [x] User模型（用户、套餐、配额）
- [x] APIKey模型（密钥管理）
- [x] Subscription模型（订阅记录）
- [x] 数据库迁移脚本
- [x] 表创建和索引

### 核心功能
- [x] API密钥管理器（生成、验证、撤销）
- [x] 认证工具（JWT、密码哈希）
- [x] 用户注册API
- [x] 用户登录API
- [x] API密钥创建API
- [x] API密钥列表API
- [x] API密钥撤销API

### 测试
- [x] API密钥管理器测试（6个测试用例）
- [x] 认证工具测试（4个测试用例）
- [x] 测试覆盖率达到75%

## 代码统计

```
文件数: 12个
代码行数: ~1200行
测试用例: 10个
通过率: 100%
```

## 遇到的问题和解决

1. **问题**: PostgreSQL连接失败
   - **解决**: 检查PostgreSQL服务是否启动，确认database_url配置正确

2. **问题**: JWT解码失败
   - **解决**: 确保jwt_secret_key配置正确，密钥长度足够

## 明天计划 (Day 2)

- [ ] 实现配额管理器（Redis集成）
- [ ] 实现速率限制
- [ ] 创建使用统计API
- [ ] 实现配额检查中间件
- [ ] 开发者聊天API（带配额）

## 笔记

- 数据库模型设计遵循企业级标准
- 所有密码使用bcrypt加密
- JWT令牌默认有效期7天
- API密钥格式: ai-hub-{random_string}
- 密钥只在创建时显示一次

---

**Day 1总结**: 成功完成所有计划任务，为Week 1打下坚实基础！🎉
```

#### 📝 最终检查点
- [ ] 代码格式检查通过
- [ ] 所有测试通过
- [ ] Git提交完成
- [ ] Day 1完成报告已创建
- [ ] 清理临时文件（test_*_temp.py）

---

## 🎉 Day 1 完成！

### 成果总结

**创建的文件** (12个):
```
✅ backend/config/settings.py
✅ backend/database.py
✅ backend/models/user.py
✅ backend/models/api_key.py
✅ backend/models/subscription.py
✅ backend/models/__init__.py
✅ backend/core/api_key_manager.py
✅ backend/core/auth.py
✅ backend/api/v1/auth.py
✅ backend/api/v1/developer/api_keys.py
✅ backend/tests/conftest.py
✅ backend/tests/test_api_key_manager.py
✅ backend/tests/test_auth.py
✅ migrations/001_initial_schema.sql
```

**功能完成度**: 100%
**测试覆盖率**: >70%
**代码质量**: 优秀

### 明天预告

Day 2将继续实现：
- 配额管理器（Redis）
- 速率限制
- 使用统计API
- 开发者API（带配额检查）

**预计难度**: 中等
**预计用时**: 8小时

---

**恭喜你完成了Day 1！休息一下，明天继续加油！** 💪

*记得push代码到GitHub，保持进度同步！*
