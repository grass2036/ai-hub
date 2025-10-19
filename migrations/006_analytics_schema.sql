-- 分析系统数据库迁移
-- Week 5 Day 3: 智能数据分析平台 - 数据模型

-- 用户行为记录表
CREATE TABLE IF NOT EXISTS user_behaviors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    action_type VARCHAR(50),
    category VARCHAR(50) NOT NULL,

    -- 事件信息
    url VARCHAR(2048),
    referrer VARCHAR(2048),
    user_agent TEXT,
    ip_address VARCHAR(45),

    -- 事件属性
    properties JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 性能指标
    response_time FLOAT,
    status_code INTEGER
);

-- 用户会话表
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,

    -- 时间信息
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds FLOAT,

    -- 会话统计
    page_views INTEGER DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    total_events INTEGER DEFAULT 0,
    conversion_events INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,

    -- 会话质量指标
    bounce_rate FLOAT,
    engagement_score FLOAT,

    -- 设备和浏览器信息
    device_type VARCHAR(50),
    browser VARCHAR(100),
    os VARCHAR(100),

    -- 地理位置
    country VARCHAR(100),
    city VARCHAR(100),

    -- 会话属性
    properties JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 用户转化漏斗表
CREATE TABLE IF NOT EXISTS user_funnels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    funnel_name VARCHAR(100) NOT NULL,

    -- 漏斗步骤
    step_name VARCHAR(100) NOT NULL,
    step_order INTEGER NOT NULL,

    -- 转化信息
    converted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    conversion_value FLOAT,

    -- 上下文信息
    source VARCHAR(100),
    medium VARCHAR(100),
    campaign VARCHAR(100),

    -- 属性
    properties JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 用户群组表
CREATE TABLE IF NOT EXISTS user_cohorts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cohort_name VARCHAR(100) NOT NULL,
    cohort_type VARCHAR(50) NOT NULL,  -- daily, weekly, monthly

    -- 群组成员
    user_id VARCHAR(255) NOT NULL,

    -- 时间信息
    cohort_date DATE NOT NULL,
    join_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 群组属性
    properties JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 分析指标表
CREATE TABLE IF NOT EXISTS analytics_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,  -- counter, gauge, histogram

    -- 时间信息
    metric_date TIMESTAMP WITH TIME ZONE NOT NULL,
    period VARCHAR(20) NOT NULL,  -- hourly, daily, weekly, monthly

    -- 指标值
    value FLOAT NOT NULL,
    previous_value FLOAT,

    -- 维度信息
    dimensions JSONB DEFAULT '{}',

    -- 统计信息
    sample_count INTEGER DEFAULT 1,
    min_value FLOAT,
    max_value FLOAT,
    avg_value FLOAT,

    -- 元数据
    tags JSONB DEFAULT '{}',
    properties JSONB DEFAULT '{}',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_user_behaviors_user_id ON user_behaviors(user_id);
CREATE INDEX IF NOT EXISTS idx_user_behaviors_session_id ON user_behaviors(session_id);
CREATE INDEX IF NOT EXISTS idx_user_behaviors_event_type ON user_behaviors(event_type);
CREATE INDEX IF NOT EXISTS idx_user_behaviors_created_at ON user_behaviors(created_at);
CREATE INDEX IF NOT EXISTS idx_user_behaviors_category ON user_behaviors(category);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_start_time ON user_sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_user_sessions_end_time ON user_sessions(end_time);

CREATE INDEX IF NOT EXISTS idx_user_funnels_user_id ON user_funnels(user_id);
CREATE INDEX IF NOT EXISTS idx_user_funnels_session_id ON user_funnels(session_id);
CREATE INDEX IF NOT EXISTS idx_user_funnels_funnel_name ON user_funnels(funnel_name);
CREATE INDEX IF NOT EXISTS idx_user_funnels_step_name ON user_funnels(step_name);

CREATE INDEX IF NOT EXISTS idx_user_cohorts_user_id ON user_cohorts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_cohorts_cohort_name ON user_cohorts(cohort_name);
CREATE INDEX IF NOT EXISTS idx_user_cohorts_cohort_date ON user_cohorts(cohort_date);

CREATE INDEX IF NOT EXISTS idx_analytics_metrics_name ON analytics_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_analytics_metrics_date ON analytics_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_analytics_metrics_period ON analytics_metrics(period);

-- 创建更新时间戳的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为用户会话表创建更新时间戳触发器
CREATE TRIGGER update_user_sessions_updated_at
    BEFORE UPDATE ON user_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 添加约束
ALTER TABLE user_behaviors ADD CONSTRAINT check_event_type
    CHECK (event_type IN ('page_view', 'api_call', 'user_action', 'error_occurred', 'performance_metric', 'business_event', 'system_event'));

ALTER TABLE user_sessions ADD CONSTRAINT check_device_type
    CHECK (device_type IN ('desktop', 'mobile', 'tablet', 'other'));

ALTER TABLE user_cohorts ADD CONSTRAINT check_cohort_type
    CHECK (cohort_type IN ('daily', 'weekly', 'monthly', 'quarterly'));

ALTER TABLE analytics_metrics ADD CONSTRAINT check_metric_type
    CHECK (metric_type IN ('counter', 'gauge', 'histogram', 'timer'));

ALTER TABLE analytics_metrics ADD CONSTRAINT check_period
    CHECK (period IN ('hourly', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly'));

-- 添加注释
COMMENT ON TABLE user_behaviors IS '用户行为记录表，存储所有用户交互事件';
COMMENT ON TABLE user_sessions IS '用户会话表，记录用户访问会话的详细信息';
COMMENT ON TABLE user_funnels IS '用户转化漏斗表，跟踪用户转化路径';
COMMENT ON TABLE user_cohorts IS '用户群组表，用于用户分组分析';
COMMENT ON TABLE analytics_metrics IS '分析指标表，存储各种聚合指标';

-- 创建分区表（可选，用于大数据量场景）
-- 可以根据实际需要为user_behaviors表创建按月分区

-- 创建聚合视图（用于快速查询）
CREATE OR REPLACE VIEW daily_user_activity AS
SELECT
    DATE(created_at) as activity_date,
    user_id,
    COUNT(*) as total_events,
    COUNT(DISTINCT session_id) as unique_sessions,
    COUNT(DISTINCT CASE WHEN event_type = 'page_view' THEN session_id END) as page_view_sessions,
    COUNT(DISTINCT CASE WHEN event_type = 'api_call' THEN session_id END) as api_call_sessions,
    COUNT(DISTINCT CASE WHEN event_type = 'error_occurred' THEN session_id END) as error_sessions
FROM user_behaviors
GROUP BY DATE(created_at), user_id;

-- 创建用户行为聚合表（用于快速统计）
CREATE TABLE IF NOT EXISTS user_behavior_daily_aggregates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    activity_date DATE NOT NULL,

    -- 聚合统计
    total_events INTEGER DEFAULT 0,
    unique_sessions INTEGER DEFAULT 0,
    page_views INTEGER DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    avg_session_duration FLOAT,

    -- 最活跃时间段
    peak_hour INTEGER,

    -- 设备信息
    primary_device_type VARCHAR(50),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_behavior_daily_aggregates_unique
    ON user_behavior_daily_aggregates(user_id, activity_date);

-- 添加聚合触发器（可选）
-- 可以创建定时任务来更新聚合表

-- 插入示例数据（可选）
INSERT INTO user_cohorts (cohort_name, cohort_type, cohort_date, user_id) VALUES
('2024年1月新用户', 'monthly', '2024-01-01', 'user_1'),
('2024年1月新用户', 'monthly', '2024-01-01', 'user_2')
ON CONFLICT DO NOTHING;

COMMENT ON TABLE user_behavior_daily_aggregates IS '用户行为每日聚合表，用于快速查询用户活动统计';