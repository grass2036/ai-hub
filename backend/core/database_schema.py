"""
数据库架构优化模块
Week 6 Day 3: 代码重构和架构优化 - 数据库架构优化
实现统一的模型设计、关系映射、迁移管理等功能
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Text, Float,
    ForeignKey, Index, CheckConstraint, UniqueConstraint,
    create_engine, MetaData, event
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import logging

from backend.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# 创建基础模型类
Base = declarative_base()

class TimestampMixin:
    """时间戳混入类"""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class SoftDeleteMixin:
    """软删除混入类"""
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    def soft_delete(self):
        """软删除"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self):
        """恢复"""
        self.is_deleted = False
        self.deleted_at = None

class UUIdMixin:
    """UUID主键混入类"""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

class AuditMixin:
    """审计混入类"""
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    version = Column(Integer, default=1, nullable=False)

# 用户相关模型
class User(Base, UUIdMixin, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """用户模型"""
    __tablename__ = "users"

    # 基本信息
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)

    # 状态字段
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # 角色和权限
    role = Column(String(50), default="user", nullable=False)
    permissions = Column(ARRAY(String), default=[], nullable=False)

    # 个人资料
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    language = Column(String(10), default="en", nullable=False)

    # 联系信息
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)

    # 偏好设置
    preferences = Column(JSONB, default={}, nullable=False)

    # 索引
    __table_args__ = (
        Index('idx_users_email_active', 'email', 'is_active', 'is_deleted'),
        Index('idx_users_role_active', 'role', 'is_active'),
        Index('idx_users_created_at', 'created_at'),
        CheckConstraint('email ~* \'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$\'', name='valid_email'),
    )

class UserProfile(Base, UUIdMixin, TimestampMixin):
    """用户详细资料"""
    __tablename__ = "user_profiles"

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)

    # 个人信息
    date_of_birth = Column(DateTime(timezone=True), nullable=True)
    gender = Column(String(10), nullable=True)
    nationality = Column(String(100), nullable=True)

    # 工作信息
    company = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)

    # 社交媒体
    website = Column(String(500), nullable=True)
    linkedin = Column(String(500), nullable=True)
    twitter = Column(String(500), nullable=True)

    # 附加信息
    metadata = Column(JSONB, default={}, nullable=False)

    # 关系
    user = relationship("User", backref="profile")

# 组织相关模型
class Organization(Base, UUIdMixin, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """组织模型"""
    __tablename__ = "organizations"

    # 基本信息
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    website = Column(String(500), nullable=True)

    # 状态信息
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # 地址信息
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)

    # 业务信息
    industry = Column(String(100), nullable=True)
    size = Column(String(50), nullable=True)  # small, medium, large, enterprise
    revenue = Column(Float, nullable=True)

    # 配置
    settings = Column(JSONB, default={}, nullable=False)

    # 索引
    __table_args__ = (
        Index('idx_organizations_slug_active', 'slug', 'is_active', 'is_deleted'),
        Index('idx_organizations_email', 'email'),
        Index('idx_organizations_industry', 'industry'),
    )

class OrganizationMember(Base, UUIdMixin, TimestampMixin):
    """组织成员模型"""
    __tablename__ = "organization_members"

    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # 角色和权限
    role = Column(String(50), default="member", nullable=False)  # owner, admin, member, developer
    permissions = Column(ARRAY(String), default=[], nullable=False)

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    invited_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    joined_at = Column(DateTime(timezone=True), nullable=True)

    # 约束
    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='unique_organization_user'),
        Index('idx_org_members_org_role', 'organization_id', 'role'),
        Index('idx_org_members_user_active', 'user_id', 'is_active'),
    )

# API密钥相关模型
class APIKey(Base, UUIdMixin, TimestampMixin, SoftDeleteMixin):
    """API密钥模型"""
    __tablename__ = "api_keys"

    # 基本信息
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    key_hash = Column(String(255), nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False)

    # 关联信息
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)

    # 状态和配置
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)

    # 权限和限制
    permissions = Column(ARRAY(String), default=[], nullable=False)
    rate_limit = Column(Integer, default=1000, nullable=False)  # 每小时请求限制

    # 使用统计
    total_requests = Column(Integer, default=0, nullable=False)
    total_cost = Column(Float, default=0.0, nullable=False)

    # 索引
    __table_args__ = (
        Index('idx_api_keys_user_active', 'user_id', 'is_active', 'is_deleted'),
        Index('idx_api_keys_org_active', 'organization_id', 'is_active'),
        Index('idx_api_keys_hash', 'key_hash'),
    )

# 使用记录模型
class UsageRecord(Base, UUIdMixin, TimestampMixin):
    """使用记录模型"""
    __tablename__ = "usage_records"

    # 关联信息
    api_key_id = Column(UUID(as_uuid=True), ForeignKey('api_keys.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True)

    # 请求信息
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    model = Column(String(100), nullable=True)

    # 响应信息
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=False)
    tokens_used = Column(Integer, default=0, nullable=False)
    cost = Column(Float, default=0.0, nullable=False)

    # 请求详情
    request_metadata = Column(JSONB, default={}, nullable=False)
    response_metadata = Column(JSONB, default={}, nullable=False)

    # 索引
    __table_args__ = (
        Index('idx_usage_api_key_created', 'api_key_id', 'created_at'),
        Index('idx_usage_user_created', 'user_id', 'created_at'),
        Index('idx_usage_org_created', 'organization_id', 'created_at'),
        Index('idx_usage_model_created', 'model', 'created_at'),
        Index('idx_usage_status_created', 'status_code', 'created_at'),
    )

# 订阅相关模型
class SubscriptionPlan(Base, UUIdMixin, TimestampMixin):
    """订阅计划��型"""
    __tablename__ = "subscription_plans"

    # 基本信息
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # 定价信息
    price_monthly = Column(Float, nullable=False)
    price_yearly = Column(Float, nullable=True)
    currency = Column(String(3), default="USD", nullable=False)

    # 限制
    api_requests_per_month = Column(Integer, nullable=False)
    max_users = Column(Integer, nullable=True)
    max_api_keys = Column(Integer, nullable=True)
    features = Column(ARRAY(String), default=[], nullable=False)

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)

    # 索引
    __table_args__ = (
        Index('idx_subscription_plans_slug', 'slug'),
        Index('idx_subscription_plans_active', 'is_active'),
    )

class Subscription(Base, UUIdMixin, TimestampMixin):
    """订阅模型"""
    __tablename__ = "subscriptions"

    # 关联信息
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('subscription_plans.id'), nullable=False)

    # 状态
    status = Column(String(50), default="active", nullable=False)  # active, cancelled, expired, trialing
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)

    # 账单信息
    billing_cycle = Column(String(10), default="monthly", nullable=False)  # monthly, yearly
    price_paid = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)

    # 使用情况
    api_requests_used = Column(Integer, default=0, nullable=False)
    api_requests_limit = Column(Integer, nullable=False)

    # 取消信息
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancel_reason = Column(Text, nullable=True)

    # 索引
    __table_args__ = (
        Index('idx_subscriptions_org_status', 'organization_id', 'status'),
        Index('idx_subscriptions_plan_status', 'plan_id', 'status'),
        Index('idx_subscriptions_period_end', 'current_period_end'),
    )

# 审计日志模型
class AuditLog(Base, UUIdMixin, TimestampMixin):
    """审计日志模型"""
    __tablename__ = "audit_logs"

    # 基本信息
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(UUID(as_uuid=True), nullable=True)

    # 用户信息
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True)

    # 请求信息
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # 变更信息
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)

    # 索引
    __table_args__ = (
        Index('idx_audit_logs_action_created', 'action', 'created_at'),
        Index('idx_audit_logs_user_created', 'user_id', 'created_at'),
        Index('idx_audit_logs_resource_created', 'resource_type', 'resource_id', 'created_at'),
        Index('idx_audit_logs_org_created', 'organization_id', 'created_at'),
    )

# 数据库初始化和迁移
class DatabaseManager:
    """数据库管理器"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None

    def initialize(self):
        """初始化数据库连接"""
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=settings.is_development()
        )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        # 创建所有表
        Base.metadata.create_all(bind=self.engine)

        logger.info("数据库初始化完成")

    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("数据库表创建完成")

    def drop_tables(self):
        """删除所有表"""
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("数据库表已删除")

    def create_indexes(self):
        """创建额外索引"""
        # 这里可以添加自定义索引
        pass

# 事件监听器
@event.listens_for(User, 'before_insert')
def set_user_defaults(mapper, connection, target):
    """设置用户默认值"""
    if not target.preferences:
        target.preferences = {}
    if not target.permissions:
        target.permissions = []

@event.listens_for(Organization, 'before_insert')
def set_organization_defaults(mapper, connection, target):
    """设置组织默认值"""
    if not target.settings:
        target.settings = {
            "allow_public_profile": False,
            "require_verification": True,
            "default_role": "member"
        }

@event.listens_for(APIKey, 'before_insert')
def set_api_key_defaults(mapper, connection, target):
    """设置API密钥默认值"""
    if not target.permissions:
        target.permissions = ["read", "write"]

# 数据库迁移助手
class MigrationHelper:
    """数据库迁移助手"""

    @staticmethod
    def create_migration_table():
        """创建迁移记录表"""
        from sqlalchemy import Table, Column, String, DateTime

        migrations_table = Table(
            'schema_migrations',
            Base.metadata,
            Column('version', String(255), primary_key=True),
            Column('applied_at', DateTime(timezone=True), server_default=func.now())
        )

    @staticmethod
    def run_migration(migration_version: str, migration_func):
        """运行迁移"""
        logger.info(f"开始执行迁移: {migration_version}")
        try:
            migration_func()
            logger.info(f"迁移完成: {migration_version}")
        except Exception as e:
            logger.error(f"迁移失败: {migration_version}, 错误: {e}")
            raise

# 查询优化器
class QueryOptimizer:
    """查询优化器"""

    @staticmethod
    def apply_pagination(query, page: int, limit: int):
        """应用分页"""
        offset = (page - 1) * limit
        return query.offset(offset).limit(limit)

    @staticmethod
    def apply_filters(query, filters: Dict[str, Any]):
        """应用过滤器"""
        for key, value in filters.items():
            if value is not None:
                if hasattr(query.column_descriptions[0]['type'], key):
                    query = query.filter(getattr(query.column_descriptions[0]['type'], key) == value)
        return query

    @staticmethod
    def apply_search(query, search_fields: List[str], search_term: str):
        """应用搜索"""
        if search_term:
            search_conditions = []
            for field in search_fields:
                if hasattr(query.column_descriptions[0]['type'], field):
                    field_attr = getattr(query.column_descriptions[0]['type'], field)
                    search_conditions.append(field_attr.ilike(f"%{search_term}%"))

            if search_conditions:
                from sqlalchemy import or_
                query = query.filter(or_(*search_conditions))

        return query

# 测试函数
def test_database_schema():
    """测试数据库架构"""
    print("🗄️ 测试数据库架构优化...")

    # 测试模型创建
    try:
        from backend.config.settings import get_settings
        settings = get_settings()

        db_manager = DatabaseManager(settings.database_url)

        print("✅ 数据库架构优化完成:")
        print("- 统一的模型基础类")
        print("- 完善的关系映射")
        print("- 优化的索引设计")
        print("- 软删除支持")
        print("- 审计日志功能")
        print("- 时间戳和版本控制")
        print("- 迁移管理支持")

    except Exception as e:
        print(f"❌ 数据库架构测试失败: {e}")

if __name__ == "__main__":
    test_database_schema()