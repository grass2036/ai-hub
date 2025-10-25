"""
预定义告警规则
包含系统、业务、性能等多个维度的��警规则
"""
from backend.monitoring.alert_engine import AlertCondition, AlertSeverity, alert_engine
from typing import Dict, List

# 系统级告警规则
SYSTEM_ALERT_RULES = [
    AlertCondition(
        id="cpu_usage_warning",
        name="CPU使用率警告",
        metric_name="cpu_usage",
        operator=">",
        threshold=80.0,
        duration_minutes=5,
        severity=AlertSeverity.WARNING,
        description="系统CPU使用率过高，可能影响性能",
        tags={"category": "system", "resource": "cpu"}
    ),

    AlertCondition(
        id="cpu_usage_critical",
        name="CPU使用率严重告警",
        metric_name="cpu_usage",
        operator=">",
        threshold=95.0,
        duration_minutes=2,
        severity=AlertSeverity.CRITICAL,
        description="系统CPU使用率严重过高，需要立即处理",
        tags={"category": "system", "resource": "cpu"}
    ),

    AlertCondition(
        id="memory_usage_warning",
        name="内存使用率警告",
        metric_name="memory_usage",
        operator=">",
        threshold=85.0,
        duration_minutes=5,
        severity=AlertSeverity.WARNING,
        description="系统内存使用率过高，可能影响性能",
        tags={"category": "system", "resource": "memory"}
    ),

    AlertCondition(
        id="memory_usage_critical",
        name="内存使用率严重告警",
        metric_name="memory_usage",
        operator=">",
        threshold=95.0,
        duration_minutes=2,
        severity=AlertSeverity.CRITICAL,
        description="系统��存使用率严重过高，可能导致OOM",
        tags={"category": "system", "resource": "memory"}
    ),

    AlertCondition(
        id="disk_usage_warning",
        name="磁盘空间警告",
        metric_name="disk_usage",
        operator=">",
        threshold=85.0,
        duration_minutes=10,
        severity=AlertSeverity.WARNING,
        description="磁盘空间不足，请及时清理",
        tags={"category": "system", "resource": "disk"}
    ),

    AlertCondition(
        id="disk_usage_critical",
        name="磁盘空间严重告警",
        metric_name="disk_usage",
        operator=">",
        threshold=95.0,
        duration_minutes=5,
        severity=AlertSeverity.CRITICAL,
        description="磁盘空间严重不足，系统可能无法正常运行",
        tags={"category": "system", "resource": "disk"}
    ),

    AlertCondition(
        id="load_average_high",
        name="系统负载过高",
        metric_name="load_average_1m",
        operator=">",
        threshold=2.0,
        duration_minutes=5,
        severity=AlertSeverity.WARNING,
        description="系统1分钟平均负载过高",
        tags={"category": "system", "resource": "load"}
    )
]

# API性能告警规则
API_PERFORMANCE_ALERT_RULES = [
    AlertCondition(
        id="api_response_time_warning",
        name="API响应时间警告",
        metric_name="api_response_time_avg",
        operator=">",
        threshold=2000.0,  # 2秒
        duration_minutes=3,
        severity=AlertSeverity.WARNING,
        description="API平均响应时间过长，用户体验受影响",
        tags={"category": "api", "metric": "response_time"}
    ),

    AlertCondition(
        id="api_response_time_critical",
        name="API响应时间严重告警",
        metric_name="api_response_time_avg",
        operator=">",
        threshold=5000.0,  # 5秒
        duration_minutes=1,
        severity=AlertSeverity.CRITICAL,
        description="API平均响应时间严重过长，系统可能存在问题",
        tags={"category": "api", "metric": "response_time"}
    ),

    AlertCondition(
        id="api_error_rate_warning",
        name="API错误率警告",
        metric_name="api_error_rate",
        operator=">",
        threshold=5.0,  # 5%
        duration_minutes=2,
        severity=AlertSeverity.WARNING,
        description="API错误率过高，需要检查服务状态",
        tags={"category": "api", "metric": "error_rate"}
    ),

    AlertCondition(
        id="api_error_rate_critical",
        name="API错误率严重告警",
        metric_name="api_error_rate",
        operator=">",
        threshold=10.0,  # 10%
        duration_minutes=1,
        severity=AlertSeverity.CRITICAL,
        description="API错误率严重过高，服务可能异常",
        tags={"category": "api", "metric": "error_rate"}
    ),

    AlertCondition(
        id="api_request_rate_spike",
        name="API请求量激增",
        metric_name="api_requests_per_minute",
        operator=">",
        threshold=1000.0,
        duration_minutes=1,
        severity=AlertSeverity.WARNING,
        description="API请求量突然增加，可能需要扩容",
        tags={"category": "api", "metric": "request_rate"}
    ),

    AlertCondition(
        id="api_p99_response_time_high",
        name="API P99响应时间过高",
        metric_name="api_response_time_p99",
        operator=">",
        threshold=10000.0,  # 10秒
        duration_minutes=2,
        severity=AlertSeverity.WARNING,
        description="API P99响应时间过长，部分用户受严重影响",
        tags={"category": "api", "metric": "response_time_p99"}
    )
]

# AI服务告警规则
AI_SERVICE_ALERT_RULES = [
    AlertCondition(
        id="ai_model_error_rate_high",
        name="AI模型错误率过高",
        metric_name="ai_model_error_rate",
        operator=">",
        threshold=5.0,  # 5%
        duration_minutes=3,
        severity=AlertSeverity.WARNING,
        description="AI模型调用错误率过高，检查模型状态",
        tags={"category": "ai", "metric": "error_rate"}
    ),

    AlertCondition(
        id="ai_model_response_time_high",
        name="AI模型响应时间过长",
        metric_name="ai_model_response_time_avg",
        operator=">",
        threshold=30000.0,  # 30秒
        duration_minutes=2,
        severity=AlertSeverity.WARNING,
        description="AI模型响应时间过长，影响用户体验",
        tags={"category": "ai", "metric": "response_time"}
    ),

    AlertCondition(
        id="ai_daily_cost_limit_warning",
        name="AI日消费成本警告",
        metric_name="ai_daily_cost",
        operator=">",
        threshold=100.0,  # $100
        duration_minutes=1,
        severity=AlertSeverity.WARNING,
        description="AI服务日消费成本接近预算上限",
        tags={"category": "ai", "metric": "cost"}
    ),

    AlertCondition(
        id="ai_token_usage_spike",
        name="AI Token使用量激增",
        metric_name="ai_tokens_per_minute",
        operator=">",
        threshold=10000.0,
        duration_minutes=1,
        severity=AlertSeverity.WARNING,
        description="AI Token使用量突然增加，检查异常调用",
        tags={"category": "ai", "metric": "token_usage"}
    )
]

# 业务指标告警规则
BUSINESS_ALERT_RULES = [
    AlertCondition(
        id="active_users_drop",
        name="活跃用户数下降",
        metric_name="active_users_current",
        operator="<",
        threshold=10.0,
        duration_minutes=10,
        severity=AlertSeverity.WARNING,
        description="当前活跃用户数异常下降",
        tags={"category": "business", "metric": "user_activity"}
    ),

    AlertCondition(
        id="user_session_duration_short",
        name="用户会话时长过短",
        metric_name="user_session_duration_avg",
        operator="<",
        threshold=60.0,  # 1分钟
        duration_minutes=15,
        severity=AlertSeverity.WARNING,
        description="用户平均会话时长过短，可能存在用户体验问题",
        tags={"category": "business", "metric": "user_engagement"}
    ),

    AlertCondition(
        id="new_user_registrations_low",
        name="新用户注册量过低",
        metric_name="new_user_registrations_per_hour",
        operator="<",
        threshold=1.0,
        duration_minutes=60,
        severity=AlertSeverity.INFO,
        description="新用户注册量过低，检查用户获取渠道",
        tags={"category": "business", "metric": "user_acquisition"}
    )
]

# 数据库告警规则
DATABASE_ALERT_RULES = [
    AlertCondition(
        id="db_connection_pool_high",
        name="数据库连接池使用率过高",
        metric_name="db_connection_pool_usage",
        operator=">",
        threshold=80.0,
        duration_minutes=5,
        severity=AlertSeverity.WARNING,
        description="数据库连接池使用率过高，可能影响性能",
        tags={"category": "database", "metric": "connections"}
    ),

    AlertCondition(
        id="db_slow_query_rate_high",
        name="数据库慢查询率过高",
        metric_name="db_slow_query_rate",
        operator=">",
        threshold=5.0,  # 5%
        duration_minutes=3,
        severity=AlertSeverity.WARNING,
        description="数据库慢查询率过高，需要优化查询",
        tags={"category": "database", "metric": "query_performance"}
    ),

    AlertCondition(
        id="db_lock_wait_time_high",
        name="数据库锁等待时间过长",
        metric_name="db_lock_wait_time_avg",
        operator=">",
        threshold=1000.0,  # 1秒
        duration_minutes=2,
        severity=AlertSeverity.WARNING,
        description="数据库锁等待时间过长，存在并发问题",
        tags={"category": "database", "metric": "locks"}
    )
]

# 缓存告警规则
CACHE_ALERT_RULES = [
    AlertCondition(
        id="cache_hit_rate_low",
        name="缓存命中率过低",
        metric_name="cache_hit_rate",
        operator="<",
        threshold=70.0,  # 70%
        duration_minutes=10,
        severity=AlertSeverity.WARNING,
        description="缓存命中率过低，检查缓存策略",
        tags={"category": "cache", "metric": "hit_rate"}
    ),

    AlertCondition(
        id="cache_memory_usage_high",
        name="缓存内存使用率过高",
        metric_name="cache_memory_usage",
        operator=">",
        threshold=90.0,
        duration_minutes=5,
        severity=AlertSeverity.WARNING,
        description="缓存内存使用率过高，可能需要清理或扩容",
        tags={"category": "cache", "metric": "memory"}
    ),

    AlertCondition(
        id="cache_eviction_rate_high",
        name="缓存驱逐率过高",
        metric_name="cache_eviction_rate",
        operator=">",
        threshold=10.0,  # 10%
        duration_minutes=5,
        severity=AlertSeverity.WARNING,
        description="缓存驱逐率过高，检查缓存容量配置",
        tags={"category": "cache", "metric": "evictions"}
    )
]

# 所有预定义规则的集合
DEFAULT_ALERT_RULES = (
    SYSTEM_ALERT_RULES +
    API_PERFORMANCE_ALERT_RULES +
    AI_SERVICE_ALERT_RULES +
    BUSINESS_ALERT_RULES +
    DATABASE_ALERT_RULES +
    CACHE_ALERT_RULES
)

def load_default_alert_rules():
    """加载默认告警规则到告警引擎"""
    loaded_count = 0

    for rule in DEFAULT_ALERT_RULES:
        try:
            alert_engine.add_rule(rule)
            loaded_count += 1
        except Exception as e:
            print(f"Failed to load alert rule {rule.id}: {e}")

    print(f"Successfully loaded {loaded_count} default alert rules")
    return loaded_count

def get_rules_by_category(category: str) -> List[AlertCondition]:
    """根据分类获取告警规则"""
    return [rule for rule in DEFAULT_ALERT_RULES
            if rule.tags and rule.tags.get('category') == category]

def get_rules_by_severity(severity: AlertSeverity) -> List[AlertCondition]:
    """根据严重程度获取告警规则"""
    return [rule for rule in DEFAULT_ALERT_RULES if rule.severity == severity]

def enable_rules_by_category(category: str, enabled: bool = True):
    """根据分类启用/禁用告警规则"""
    rules = get_rules_by_category(category)
    for rule in rules:
        if enabled:
            alert_engine.enable_rule(rule.id)
        else:
            alert_engine.disable_rule(rule.id)

def configure_suppression_rules():
    """配置告警抑制规则"""
    # 工作时间外抑制非关键告警
    work_hours_suppression = {
        'suppress_hours': [22, 23, 0, 1, 2, 3, 4, 5, 6],  # 晚10点到早7点
        'time_window_minutes': 30
    }

    # 周末抑制信息类告警
    weekend_suppression = {
        'suppress_weekends': True,
        'time_window_minutes': 60
    }

    # 应用抑制规则到特定规则
    info_rules = get_rules_by_severity(AlertSeverity.INFO)
    for rule in info_rules:
        alert_engine.add_suppression_rule(rule.id, weekend_suppression)

    warning_rules = get_rules_by_severity(AlertSeverity.WARNING)
    for rule in warning_rules:
        if rule.tags.get('category') in ['business']:
            alert_engine.add_suppression_rule(rule.id, work_hours_suppression)

# 初始化函数
def initialize_alert_system():
    """初始化告警系统"""
    print("Initializing alert system...")

    # 加载默认规则
    load_default_alert_rules()

    # 配置抑制规则
    configure_suppression_rules()

    print("Alert system initialized successfully")

# 如果直接运行此文件，执行初始化
if __name__ == "__main__":
    initialize_alert_system()