-- Week 3: 订阅和计费系统数据库架构
-- 实现企业级支付、订阅、计费功能

-- 套餐表
CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    billing_cycle VARCHAR(20) NOT NULL, -- monthly, yearly
    features JSONB NOT NULL DEFAULT '{}',
    api_quota INTEGER NOT NULL DEFAULT 1000,
    rate_limit INTEGER NOT NULL DEFAULT 100,
    max_teams INTEGER NOT NULL DEFAULT 1,
    max_users INTEGER NOT NULL DEFAULT 5,
    is_active BOOLEAN DEFAULT true,
    is_popular BOOLEAN DEFAULT false,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 订阅表
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE RESTRICT,
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, canceled, past_due, trialing, incomplete
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,
    trial_start TIMESTAMP,
    trial_end TIMESTAMP,
    canceled_at TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT false,
    payment_method VARCHAR(50) DEFAULT 'mock', -- mock, stripe, paypal
    mock_payment_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_status CHECK (status IN ('active', 'canceled', 'past_due', 'trialing', 'incomplete'))
);

-- 发票表
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft', -- draft, pending, paid, void, overdue
    currency VARCHAR(3) DEFAULT 'USD',
    subtotal DECIMAL(10, 2) NOT NULL,
    tax_amount DECIMAL(10, 2) DEFAULT 0,
    total_amount DECIMAL(10, 2) NOT NULL,
    due_date TIMESTAMP,
    paid_at TIMESTAMP,
    payment_method VARCHAR(50),
    mock_payment_id VARCHAR(255),
    description TEXT,
    line_items JSONB NOT NULL DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    pdf_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_invoice_status CHECK (status IN ('draft', 'pending', 'paid', 'void', 'overdue'))
);

-- 支付记录表
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    payment_id VARCHAR(255) UNIQUE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, succeeded, failed, refunded
    payment_method VARCHAR(50) DEFAULT 'mock',
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_payment_status CHECK (status IN ('pending', 'succeeded', 'failed', 'refunded'))
);

-- 使用量记录表 (扩展现有的usage_records表)
CREATE TABLE billing_usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    api_calls INTEGER NOT NULL DEFAULT 0,
    tokens_used INTEGER NOT NULL DEFAULT 0,
    cost_amount DECIMAL(10, 2) DEFAULT 0,
    cost_currency VARCHAR(3) DEFAULT 'USD',
    breakdown JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_organization_period UNIQUE (organization_id, period_start, period_end)
);

-- 套餐使用限制表
CREATE TABLE plan_usage_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL, -- api_calls, tokens, teams, users
    limit_value INTEGER NOT NULL,
    period_type VARCHAR(20) NOT NULL, -- monthly, yearly, daily
    is_soft_limit BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 订阅变更历史表
CREATE TABLE subscription_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    change_type VARCHAR(50) NOT NULL, -- created, upgraded, downgraded, canceled, renewed
    old_plan_id UUID REFERENCES plans(id),
    new_plan_id UUID REFERENCES plans(id),
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    reason TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_subscriptions_organization_id ON subscriptions(organization_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_current_period_end ON subscriptions(current_period_end);
CREATE INDEX idx_invoices_organization_id ON invoices(organization_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
CREATE INDEX idx_payments_organization_id ON payments(organization_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_billing_usage_records_org_period ON billing_usage_records(organization_id, period_start, period_end);
CREATE INDEX idx_subscription_changes_subscription_id ON subscription_changes(subscription_id);

-- 插入默认套餐数据
INSERT INTO plans (name, slug, description, price, billing_cycle, features, api_quota, rate_limit, max_teams, max_users, is_popular, sort_order) VALUES
('Free', 'free', 'Perfect for individuals and small projects getting started', 0.00, 'monthly',
 '{"api_access": true, "basic_support": true, "community_features": true}',
 1000, 100, 1, 5, false, 1),

('Pro', 'pro', 'Ideal for growing teams and professional use', 29.00, 'monthly',
 '{"api_access": true, "priority_support": true, "advanced_features": true, "custom_models": true}',
 10000, 500, 5, 20, true, 2),

('Enterprise', 'enterprise', 'Complete solution for large organizations', 99.00, 'monthly',
 '{"api_access": true, "dedicated_support": true, "all_features": true, "unlimited_customization": true, "sla_guarantee": true}',
 100000, 2000, 50, 200, false, 3);

-- 插入年度套餐（8折优惠）
INSERT INTO plans (name, slug, description, price, billing_cycle, features, api_quota, rate_limit, max_teams, max_users, is_popular, sort_order) VALUES
('Pro (Yearly)', 'pro-yearly', 'Save 20% with annual billing', 278.40, 'yearly',
 '{"api_access": true, "priority_support": true, "advanced_features": true, "custom_models": true}',
 10000, 500, 5, 20, false, 4),

('Enterprise (Yearly)', 'enterprise-yearly', 'Save 20% with annual billing', 950.40, 'yearly',
 '{"api_access": true, "dedicated_support": true, "all_features": true, "unlimited_customization": true, "sla_guarantee": true}',
 100000, 2000, 50, 200, false, 5);

-- 创建触发器函数用于更新 updated_at 字段
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为相关表创建触发器
CREATE TRIGGER update_plans_updated_at BEFORE UPDATE ON plans FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_invoices_updated_at BEFORE UPDATE ON invoices FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_plan_usage_limits_updated_at BEFORE UPDATE ON plan_usage_limits FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();