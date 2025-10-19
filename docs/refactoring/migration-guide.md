# AI Hub 平台代码重构迁移指南

> **版本**: Week 6 Day 3 重构版本
> **适用对象**: 开发团队、运维团队、项目管理
> **更新日期**: 2025年10月17日

---

## 📋 迁移概述

### 🎯 迁移目标
���现有的AI Hub平台代码从旧架构迁移到新的重构架构，实现：
- 提高代码质量和可维护性
- 优化系统架构和性能
- 建立标准化的开发流程
- 保证业务连续性和数据安全

### ⚠️ 重要提示
- **必须先备份数据**：在开始迁移前确保所有数据已完整备份
- **分阶段执行**：严格按照阶段顺序执行，不可跳跃
- **充分测试**：每个阶段完成后必须进行充分测试
- **准备回滚**：确保有完整的回滚方案

---

## 🛠️ 环境准备

### 系统要求
- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Node.js 16+ (前端)

### 依赖更新
```bash
# 安装新的Python依赖
pip install -r requirements-refactor.txt

# 更新数据库连接配置
cp .env.example .env.backup
# 编辑 .env 文件，确保数据库连接正确
```

### 工具安装
```bash
# 代码质量工具
pip install black isort flake8 mypy

# 数据库迁移工具
pip install alembic

# 测试工具
pip install pytest pytest-asyncio pytest-cov
```

---

## 📅 迁移计划

### 阶段1: 环境和数据准备 (第1-2天)

#### 1.1 代码备份
```bash
# 创建备份分支
git checkout -b backup-before-refactor
git push origin backup-before-refactor

# 创建迁移分支
git checkout -b refactor-week6-day3
git push origin refactor-week6-day3

# 代码归档备份
tar -czf backup-code-$(date +%Y%m%d).tar.gz /path/to/backend
```

#### 1.2 数据库备份
```bash
# PostgreSQL备份
pg_dump -h localhost -U username -d ai_hub > backup-db-$(date +%Y%m%d).sql

# Redis备份
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb backup-redis-$(date +%Y%m%d).rdb
```

#### 1.3 配置文件准备
```bash
# 备份现有配置
cp .env .env.backup
cp config/ config.backup/

# 更新配置文件
# 根据新的架构要求更新配置
```

### 阶段2: 核心架构迁移 (第3-4天)

#### 2.1 部署基础抽象层
```bash
# 1. 添加新的核心模块
cp backend/core/base.py backend/core/

# 2. 更新现有模块的导入
# 将旧的导入语句替换为新的抽象层导入

# 示例迁移：
# 旧代码:
# from database import get_db
# from models import User

# 新代码:
# from backend.core.base import BaseService, BaseResponse
# from backend.core.database import get_db
# from backend.models.user import User
```

#### 2.2 数据库架构迁移
```bash
# 1. 创建新的模型文件
cp backend/core/database_schema.py backend/models/

# 2. 生成迁移文件
alembic revision --autogenerate -m "refactor_database_schema"

# 3. 检查迁移文件
cat alembic/versions/xxx_refactor_database_schema.py

# 4. 执行迁移
alembic upgrade head
```

**数据库迁移脚本示例**:
```python
# alembic/versions/xxx_refactor_database_schema.py
def upgrade():
    # 创建新的用户表结构
    op.create_table('users_v2',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        # ... 其他字段
    )

    # 数据迁移
    op.execute("""
        INSERT INTO users_v2 (id, email, password_hash, full_name, created_at)
        SELECT id, email, password_hash, full_name, created_at
        FROM users
    """)

def downgrade():
    op.drop_table('users_v2')
```

#### 2.3 用户服务重构
```python
# 1. 更新用户服务
# backend/services/user_service.py

from backend.core.user_service import UserService
from backend.core.base import PaginationParams

# 2. 更新API端点
# backend/api/v1/users.py

@router.post("/users")
async def create_user(request: CreateUserRequest, db: Session = Depends(get_db)):
    user_service = UserService(db)
    result = await user_service.create_user(request)
    return result

@router.get("/users")
async def get_users(
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    params = PaginationParams(page=page, limit=limit)
    user_service = UserService(db)
    result = await user_service.get_all(params)
    return result
```

### 阶段3: 业务模块迁移 (第5-6天)

#### 3.1 组织管理模块迁移
```python
# 重构组织服务
from backend.core.base import BaseService, BaseRepository

class OrganizationService(BaseService):
    def __init__(self, db_session: Session):
        repository = OrganizationRepository(db_session)
        super().__init__(repository)

# 更新API
@router.post("/organizations")
async def create_organization(request: CreateOrganizationRequest, db: Session = Depends(get_db)):
    service = OrganizationService(db)
    return await service.create(request)
```

#### 3.2 API密钥管理迁移
```python
# 更新API密钥服务
from backend.core.base import BaseService

class APIKeyService(BaseService):
    def __init__(self, db_session: Session):
        repository = APIKeyRepository(db_session)
        super().__init__(repository)

# 数据迁移脚本
def migrate_api_keys():
    # 将旧的API密钥数据迁移到新结构
    pass
```

#### 3.3 其他模块迁移
- 分析统计模块
- 订阅计费模块
- 审计日志模块
- 监控告警模块

### 阶段4: 测试和验证 (第7天)

#### 4.1 单元测试
```bash
# 运行新的单元测试
pytest backend/tests/unit/ -v --cov=backend/core

# 检查测试覆盖率
pytest --cov=backend/core --cov-report=html
```

#### 4.2 集成测试
```bash
# 运行集成测试
pytest backend/tests/integration/ -v

# API测试
pytest backend/tests/api/ -v
```

#### 4.3 性能测试
```bash
# 运行性能测试
python backend/tests/performance/test_performance.py

# 压力测试
python backend/tests/performance/test_stress.py
```

#### 4.4 兼容性测试
```bash
# 测试旧API兼容性
curl -X POST http://localhost:8001/api/v1/users/legacy \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# 测试新API功能
curl -X POST http://localhost:8001/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123456","full_name":"Test User"}'
```

---

## 🔧 迁移脚本

### 自动化迁移脚本
```bash
#!/bin/bash
# migrate.sh - 自动化迁移脚本

set -e

echo "🚀 开始AI Hub平台重构迁移..."

# 检查环境
echo "📋 检查环境..."
python --version
psql --version
redis-cli --version

# 备份数据
echo "💾 备份数据..."
python scripts/backup_data.py

# 代码迁移
echo "📝 代码迁移..."
python scripts/migrate_code.py

# 数据库迁移
echo "🗄️ 数据库迁移..."
alembic upgrade head

# 运行测试
echo "🧪 运行测试..."
pytest backend/tests/ -v

echo "✅ 迁移完成！"
```

### 数据迁移脚本
```python
# scripts/migrate_data.py
import asyncio
import logging
from backend.core.database import get_db

logger = logging.getLogger(__name__)

async def migrate_user_data():
    """迁移用户数据"""
    with get_db() as db:
        # 从旧表读取数据
        old_users = db.execute("SELECT * FROM users_old").fetchall()

        for old_user in old_users:
            # 转换为新格式
            new_user_data = {
                'id': old_user['id'],
                'email': old_user['email'],
                'password_hash': old_user['password_hash'],
                'full_name': old_user['full_name'],
                'is_active': old_user.get('is_active', True),
                'preferences': old_user.get('preferences', {}),
                'created_at': old_user['created_at'],
                'updated_at': old_user.get('updated_at', old_user['created_at'])
            }

            # 插入到新表
            db.execute("""
                INSERT INTO users_v2 (id, email, password_hash, full_name, is_active, preferences, created_at, updated_at)
                VALUES (:id, :email, :password_hash, :full_name, :is_active, :preferences, :created_at, :updated_at)
            """, new_user_data)

        db.commit()
        logger.info(f"迁移了 {len(old_users)} 个用户记录")

async def main():
    """主迁移函数"""
    try:
        await migrate_user_data()
        # 添加其他数据迁移函数
        logger.info("数据迁移完成")
    except Exception as e:
        logger.error(f"数据迁移失败: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🚨 回滚方案

### 紧急回滚步骤

#### 1. 代码回滚
```bash
# 切换到备份分支
git checkout backup-before-refactor

# 恢复依赖
pip install -r requirements-old.txt

# 重启服务
systemctl restart ai-hub-backend
```

#### 2. 数据库回滚
```bash
# 恢复数据库
psql -h localhost -U username -d ai_hub < backup-db-YYYYMMDD.sql

# 恢复Redis
redis-cli FLUSHALL
redis-cli RESTORE dump.rdb 0 "$(cat backup-redis-YYYYMMDD.rdb)"
```

#### 3. 配置回滚
```bash
# 恢复配置文件
cp .env.backup .env
cp -r config.backup/* config/

# 重启服务
systemctl restart ai-hub-backend
```

### 部分回滚方案

#### 仅回滚特定模块
```bash
# 回滚用户服务
git checkout backup-before-refactor -- backend/services/user_service.py
git checkout backup-before-refactor -- backend/api/v1/users.py

# 回滚数据库表
alembic downgrade -1  # 回滚一个版本
```

---

## 📊 迁移验证清单

### ✅ 代码验证
- [ ] 所有Python文件语法正确
- [ ] 导入语句更新完成
- [ ] 类型注解添加完成
- [ ] 代码格式化检查通过
- [ ] 静态分析检查通过

### ✅ 数据库验证
- [ ] 所有表创建成功
- [ ] 数据迁移完整
- [ ] 外键约束正确
- [ ] 索引创建成功
- [ ] 数据一致性验证通过

### ✅ API验证
- [ ] 所有API端点响应正常
- [ ] 请求/响应格式正确
- [ ] 错误处理正常
- [ ] 认证授权正常
- [ ] 兼容性API正常工作

### ✅ 功能验证
- [ ] 用户注册登录正常
- [ ] 组织管理功能正常
- [ ] API密钥管理正常
- [ ] 统计分析功能正常
- [ ] 监控告警功能正常

### ✅ 性能验证
- [ ] API响应时间 < 500ms
- [ ] 数据库查询时间 < 200ms
- [ ] 内存使用正常
- [ ] 并发处理正常
- [ ] 错误率 < 1%

---

## 🆘 故障排除

### 常见问题及解决方案

#### 1. 数据库迁移失败
**问题**: `alembic upgrade head` 失败
**解决方案**:
```bash
# 检查迁移文件语法
alembic check

# 手动执行SQL
psql -d ai_hub -f migration.sql

# 标记迁移为完成
alembic stamp head
```

#### 2. 导入错误
**问题**: `ImportError: cannot import name 'BaseService'`
**解决方案**:
```bash
# 检查PYTHONPATH
export PYTHONPATH=$PYTHONPATH:/path/to/backend

# 检查模块路径
python -c "from backend.core.base import BaseService; print('Import successful')"
```

#### 3. API响应格式错误
**问题**: 新API返回格式与前端不兼容
**解决方案**:
```python
# 添加兼容性适配器
def adapt_response(old_response):
    return {
        "success": old_response.status == 200,
        "data": old_response.data,
        "message": old_response.message
    }
```

#### 4. 性能下降
**问题**: 迁移后性能下降
**解决方案**:
```bash
# 检查数据库索引
psql -d ai_hub -c "\d users"

# 分析慢查询
psql -d ai_hub -c "SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# 优化缓存配置
redis-cli CONFIG GET maxmemory
```

---

## 📞 支持和联系

### 技术支持
- **文档**: 查看项目文档和API文档
- **日志**: 检查应用日志和错误日志
- **监控**: 查看性能监控和系统监控

### 紧急联系
- **开发团队**: [联系方式]
- **运维团队**: [联系方式]
- **项目经理**: [联系方式]

### 反馈渠道
- **GitHub Issues**: [项目地址]
- **技术讨论群**: [群组地址]
- **邮件**: [邮箱地址]

---

## 📝 迁移记录

### 迁移日志模板
```markdown
## 迁移记录 - [日期]

### 执行人
- 姓名: [姓名]
- 角色: [角色]

### 迁移阶段
- [ ] 阶段1: 环境和数据准备
- [ ] 阶段2: 核心架构迁移
- [ ] 阶段3: 业务模块迁移
- [ ] 阶段4: 测试和验证

### 遇到的问题
1. [问题描述]
   - 解决方案: [解决方案]
   - 耗时: [时间]

### 验证结果
- 测试通过率: [百分比]
- 性能指标: [指标]
- 发现的问题: [问题列表]

### 后续行动
- [待办事项1]
- [待办事项2]
```

---

**最后更新**: 2025年10月17日
**文档版本**: 1.0
**审核人**: AI Hub开发团队
**下次更新**: 根据迁移进展及时更新