-- 企业级多租户架构数据库迁移
-- 创建租户、用户、团队等相关表

-- 租户表
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    domain VARCHAR(255) UNIQUE,
    status VARCHAR(20) DEFAULT 'trial' NOT NULL,
    plan VARCHAR(20) DEFAULT 'starter' NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    address TEXT,
    quotas JSONB DEFAULT '{}',
    billing_email VARCHAR(255),
    payment_method JSONB,
    subscription_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    trial_ends_at TIMESTAMP WITH TIME ZONE,
    suspended_at TIMESTAMP WITH TIME ZONE,
    settings JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}'
);

-- 租户用户关联表
CREATE TABLE IF NOT EXISTS tenant_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    role VARCHAR(20) DEFAULT 'member' NOT NULL,
    permissions JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    invited_by UUID,
    invited_at TIMESTAMP WITH TIME ZONE,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    preferences JSONB DEFAULT '{}',
    notifications JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, user_id)
);

-- 团队表
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    slug VARCHAR(100) NOT NULL,
    parent_team_id UUID REFERENCES teams(id),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    quotas JSONB DEFAULT '{}',
    permissions JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, slug)
);

-- 团队成员表
CREATE TABLE IF NOT EXISTS team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    role VARCHAR(20) DEFAULT 'member' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    added_by UUID,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(team_id, user_id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);
CREATE INDEX IF NOT EXISTS idx_tenants_domain ON tenants(domain);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);
CREATE INDEX IF NOT EXISTS idx_tenants_plan ON tenants(plan);
CREATE INDEX IF NOT EXISTS idx_tenants_email ON tenants(email);
CREATE INDEX IF NOT EXISTS idx_tenants_created_at ON tenants(created_at);

CREATE INDEX IF NOT EXISTS idx_tenant_users_tenant_id ON tenant_users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_users_user_id ON tenant_users(user_id);
CREATE INDEX IF NOT EXISTS idx_tenant_users_role ON tenant_users(role);
CREATE INDEX IF NOT EXISTS idx_tenant_users_is_active ON tenant_users(is_active);
CREATE INDEX IF NOT EXISTS idx_tenant_users_joined_at ON tenant_users(joined_at);

CREATE INDEX IF NOT EXISTS idx_teams_tenant_id ON teams(tenant_id);
CREATE INDEX IF NOT EXISTS idx_teams_parent_team_id ON teams(parent_team_id);
CREATE INDEX IF NOT EXISTS idx_teams_slug ON teams(slug);
CREATE INDEX IF NOT EXISTS idx_teams_is_active ON teams(is_active);
CREATE INDEX IF NOT EXISTS idx_teams_created_at ON teams(created_at);

CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user_id ON team_members(user_id);
CREATE INDEX IF NOT EXISTS idx_team_members_role ON team_members(role);
CREATE INDEX IF NOT EXISTS idx_team_members_is_active ON team_members(is_active);
CREATE INDEX IF NOT EXISTS idx_team_members_added_at ON team_members(added_at);

-- 创建更新时间戳的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为表创建更新时间戳触发器
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tenant_users_updated_at BEFORE UPDATE ON tenant_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_team_members_updated_at BEFORE UPDATE ON team_members
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 添加约束
ALTER TABLE tenants ADD CONSTRAINT check_tenant_status
    CHECK (status IN ('active', 'inactive', 'suspended', 'trial', 'pending'));

ALTER TABLE tenants ADD CONSTRAINT check_tenant_plan
    CHECK (plan IN ('starter', 'professional', 'enterprise', 'custom'));

ALTER TABLE tenant_users ADD CONSTRAINT check_tenant_user_role
    CHECK (role IN ('owner', 'admin', 'developer', 'analyst', 'member'));

ALTER TABLE teams ADD CONSTRAINT check_team_slug_format
    CHECK (slug ~ '^[a-zA-Z0-9\-]+$');

ALTER TABLE team_members ADD CONSTRAINT check_team_member_role
    CHECK (role IN ('owner', 'admin', 'developer', 'analyst', 'member'));

-- 添加注释
COMMENT ON TABLE tenants IS '企业租户表，存储多租户架构中的租户信息';
COMMENT ON TABLE tenant_users IS '租户用户关联表，存储用户与租户的关系和权限';
COMMENT ON TABLE teams IS '团队表，存储租户内的团队组织结构';
COMMENT ON TABLE team_members IS '团队成员表，存储团队与成员的关系';

COMMENT ON COLUMN tenants.quotas IS '租户配额配置，存储各种资源的使用限制';
COMMENT ON COLUMN tenants.settings IS '租户设置，存储租户的个性化配置';
COMMENT ON COLUMN tenants.metadata IS '租户元数据，存储额外的租户信息';

COMMENT ON COLUMN tenant_users.permissions IS '用户在租户中的权限列表';
COMMENT ON COLUMN tenant_users.preferences IS '用户在租户中的个人偏好设置';
COMMENT ON COLUMN tenant_users.notifications IS '用户在租户中的通知设置';

COMMENT ON COLUMN teams.quotas IS '团队配额配置';
COMMENT ON COLUMN teams.permissions IS '团队权限配置';

-- 插入默认示例数据（可选）
INSERT INTO tenants (name, slug, email, plan, status, quotas) VALUES
('Demo Company', 'demo-company', 'demo@example.com', 'starter', 'trial',
 '{"max_users": 5, "max_teams": 2, "max_api_keys": 2, "monthly_api_calls": 5000, "storage_gb": 5, "bandwidth_gb": 50}')
ON CONFLICT (slug) DO NOTHING;