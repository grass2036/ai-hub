"""
计费系统配置

定义计费系统相关的配置项和默认值。
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum


class Currency(str, Enum):
    """支持的货币"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CNY = "CNY"


class Environment(str, Enum):
    """环境类型"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class PaymentProviderConfig(BaseModel):
    """支付提供商配置"""
    enabled: bool = False
    api_key: Optional[str] = None
    webhook_secret: Optional[str] = None
    sandbox: bool = True


class PricingConfig(BaseModel):
    """定价配置"""
    currency: Currency = Currency.USD
    tax_rate: float = Field(default=0.08, ge=0, le=1)  # 税率，0-1之间
    auto_invoice: bool = True
    invoice_due_days: int = Field(default=30, ge=1)  # 发票到期天数
    late_fee_rate: float = Field(default=0.05, ge=0, le=1)  # 滞纳金率
    trial_reminder_days: List[int] = [7, 3, 1]  # 试用提醒天数


class QuotaConfig(BaseModel):
    """配额配置"""
    default_plans: Dict[str, Dict[str, Any]] = Field(default_factory=lambda: {
        "free": {
            "api_calls_monthly": 100,
            "tokens_monthly": 10000,
            "storage_gb": 1,
            "models": ["gpt-3.5-turbo", "claude-instant"],
            "rate_limit_rpm": 10,
            "rate_limit_rpd": 100
        },
        "pro": {
            "api_calls_monthly": 10000,
            "tokens_monthly": 1000000,
            "storage_gb": 100,
            "models": ["gpt-3.5-turbo", "gpt-4", "claude-instant", "claude-2"],
            "rate_limit_rpm": 60,
            "rate_limit_rpd": 10000
        },
        "enterprise": {
            "api_calls_monthly": 1000000,
            "tokens_monthly": 100000000,
            "storage_gb": 1000,
            "models": ["*"],  # 所有模型
            "rate_limit_rpm": 1000,
            "rate_limit_rpd": 1000000,
            "custom_models": True,
            "priority_support": True
        }
    })
    overage_rate_per_token: float = Field(default=0.000002, ge=0)  # 每个超限token的费用
    storage_cost_per_gb: float = Field(default=0.10, ge=0)  # 每GB存储费用
    quota_check_interval: int = Field(default=300, ge=60)  # 配额检查间隔（秒）
    violation_handling: str = Field(default="block", regex="^(block|allow|notify)$")


class UsageTrackingConfig(BaseModel):
    """使用量跟踪配置"""
    tracking_enabled: bool = True
    real_time_tracking: bool = True
    batch_processing: bool = True
    batch_size: int = Field(default=1000, ge=1)
    batch_interval: int = Field(default=60, ge=10)  # 批处理间隔（秒）
    retention_days: int = Field(default=365, ge=30)  # 数据保留天数
    detailed_logging: bool = False
    cost_calculation_enabled: bool = True


class BillingConfig(BaseModel):
    """计费系统主配置"""
    enabled: bool = False
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False

    # 支付提供商配置
    stripe: PaymentProviderConfig = Field(default_factory=PaymentProviderConfig)
    paypal: PaymentProviderConfig = Field(default_factory=PaymentProviderConfig)

    # 定价配置
    pricing: PricingConfig = Field(default_factory=PricingConfig)

    # 配额配置
    quota: QuotaConfig = Field(default_factory=QuotaConfig)

    # 使用量跟踪配置
    usage_tracking: UsageTrackingConfig = Field(default_factory=UsageTrackingConfig)

    # 通知配置
    notifications_enabled: bool = True
    email_notifications: bool = True
    webhook_notifications: bool = True

    # 报表配置
    daily_reports_enabled: bool = False
    weekly_reports_enabled: bool = True
    monthly_reports_enabled: bool = True

    # 安全配置
    webhook_timeout: int = Field(default=30, ge=5, le=300)
    max_retry_attempts: int = Field(default=3, ge=1, le=10)
    encryption_enabled: bool = True

    # 缓存配置
    cache_ttl: int = Field(default=3600, ge=60)  # 缓存TTL（秒）
    quota_cache_ttl: int = Field(default=300, ge=60)  # 配额缓存TTL（秒）
    pricing_cache_ttl: int = Field(default=86400, ge=3600)  # 价格缓存TTL（秒）

    # 数据库配置
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=100)

    # 监控配置
    metrics_enabled: bool = True
    health_check_interval: int = Field(default=60, ge=10)
    performance_monitoring: bool = True

    class Config:
        use_enum_values = True
        env_prefix = "BILLING_"
        case_sensitive = False

    def is_production(self) -> bool:
        """检查是否为生产环境"""
        return self.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        """检查是否为开发环境"""
        return self.environment == Environment.DEVELOPMENT

    def get_currency_symbol(self) -> str:
        """获取货币符号"""
        symbols = {
            Currency.USD: "$",
            Currency.EUR: "€",
            Currency.GBP: "£",
            Currency.JPY: "¥",
            Currency.CNY: "¥"
        }
        return symbols.get(self.pricing.currency, "$")

    def get_plan_limits(self, plan_type: str) -> Dict[str, Any]:
        """获取计划配额限制"""
        return self.quota.default_plans.get(plan_type, self.quota.default_plans["free"])

    def validate_config(self) -> List[str]:
        """验证配置"""
        errors = []

        # 检查支付提供商配置
        if self.enabled:
            if not self.stripe.enabled and not self.paypal.enabled:
                errors.append("至少需要启用一个支付提供商")

            if self.stripe.enabled and not self.stripe.api_key:
                errors.append("Stripe已启用但缺少API密钥")

            if self.paypal.enabled and (not self.paypal.api_key or not self.paypal.client_secret):
                errors.append("PayPal已启用但缺少API凭据")

        # 检查税率配置
        if not (0 <= self.pricing.tax_rate <= 1):
            errors.append("税率必须在0-1之间")

        # 检查配额配置
        if self.quota.overage_rate_per_token < 0:
            errors.append("超限费率不能为负数")

        if self.quota.storage_cost_per_gb < 0:
            errors.append("存储费用不能为负数")

        # 检查使用量跟踪配置
        if self.usage_tracking.batch_size < 1:
            errors.append("批处理大小必须大于0")

        if self.usage_tracking.retention_days < 30:
            errors.append("数据保留天数不能少于30天")

        return errors


# 默认配置实例
def get_default_billing_config() -> BillingConfig:
    """获取默认计费配置"""
    return BillingConfig(
        enabled=False,
        environment=Environment.DEVELOPMENT,
        debug=True,
        stripe=PaymentProviderConfig(
            enabled=False,
            sandbox=True
        ),
        paypal=PaymentProviderConfig(
            enabled=False,
            sandbox=True
        ),
        pricing=PricingConfig(
            currency=Currency.USD,
            tax_rate=0.08,
            auto_invoice=True,
            invoice_due_days=30,
            late_fee_rate=0.05
        ),
        quota=QuotaConfig(
            default_plans={
                "free": {
                    "api_calls_monthly": 100,
                    "tokens_monthly": 10000,
                    "storage_gb": 1,
                    "models": ["gpt-3.5-turbo"],
                    "rate_limit_rpm": 10,
                    "rate_limit_rpd": 100
                },
                "pro": {
                    "api_calls_monthly": 10000,
                    "tokens_monthly": 1000000,
                    "storage_gb": 100,
                    "models": ["gpt-3.5-turbo", "gpt-4"],
                    "rate_limit_rpm": 60,
                    "rate_limit_rpd": 10000
                },
                "enterprise": {
                    "api_calls_monthly": 1000000,
                    "tokens_monthly": 100000000,
                    "storage_gb": 1000,
                    "models": ["*"],
                    "rate_limit_rpm": 1000,
                    "rate_limit_rpd": 1000000,
                    "custom_models": True,
                    "priority_support": True
                }
            }
        ),
        usage_tracking=UsageTrackingConfig(
            tracking_enabled=True,
            real_time_tracking=True,
            batch_processing=True,
            batch_size=1000,
            retention_days=365
        )
    )


# 环境特定配置
def get_billing_config_for_environment(environment: str) -> BillingConfig:
    """根据环境获取计费配置"""
    base_config = get_default_billing_config()

    if environment == "production":
        base_config.environment = Environment.PRODUCTION
        base_config.debug = False
        base_config.stripe.sandbox = False
        base_config.paypal.sandbox = False
        base_config.notifications_enabled = True
        base_config.metrics_enabled = True
        base_config.performance_monitoring = True
        base_config.encryption_enabled = True

    elif environment == "staging":
        base_config.environment = Environment.STAGING
        base_config.debug = True
        base_config.stripe.sandbox = True
        base_config.paypal.sandbox = True
        base_config.notifications_enabled = False
        base_config.metrics_enabled = True

    else:  # development
        base_config.environment = Environment.DEVELOPMENT
        base_config.debug = True
        base_config.stripe.sandbox = True
        base_config.paypal.sandbox = True
        base_config.notifications_enabled = False
        base_config.metrics_enabled = False

    return base_config


# 配置验证函数
def validate_billing_config(config: BillingConfig) -> bool:
    """验证计费配置是否有效"""
    errors = config.validate_config()
    if errors:
        raise ValueError(f"计费配置验证失败: {', '.join(errors)}")
    return True


# 配置导出函数
def export_billing_config(config: BillingConfig, format: str = "dict") -> Dict[str, Any]:
    """导出计费配置"""
    if format == "dict":
        return config.dict()
    elif format == "json":
        return config.json()
    else:
        raise ValueError(f"不支持的导出格式: {format}")


# 配置合并函数
def merge_billing_configs(base_config: BillingConfig, override_config: Dict[str, Any]) -> BillingConfig:
    """合并配置"""
    base_dict = base_config.dict()
    merged_dict = {**base_dict, **override_config}
    return BillingConfig(**merged_dict)