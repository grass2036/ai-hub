"""
计费服务

统一管理计费相关的所有功能，包括定价、使用量跟踪、配额管理、发票生成和支付处理。
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

from .pricing_manager import PricingManager, PlanType, BillingCycle
from .usage_tracker import UsageTracker, UsageType, UsageStats
from .quota_manager import QuotaManager, QuotaViolation
from .invoice_generator import InvoiceGenerator
from .payments import (
    StripeProcessor, PayPalProcessor, PaymentWebhookHandler,
    PaymentProvider, PaymentStatus, PaymentType, Currency,
    PaymentResult, Subscription, PaymentError
)
from ..cache.cache_manager import CacheManager

logger = logging.getLogger(__name__)


@dataclass
class BillingConfig:
    """计费配置"""
    stripe_enabled: bool = False
    stripe_api_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    paypal_enabled: bool = False
    paypal_client_id: Optional[str] = None
    paypal_client_secret: Optional[str] = None
    paypal_sandbox: bool = True
    currency: Currency = Currency.USD
    tax_rate: float = 0.08  # 8% 税率
    auto_invoice: bool = True
    webhook_endpoints: Dict[str, str] = None


class BillingService:
    """计费服务主类"""

    def __init__(self, config: BillingConfig, cache_manager: Optional[CacheManager] = None):
        """
        初始化计费服务

        Args:
            config: 计费配置
            cache_manager: 缓存管理器
        """
        self.config = config
        self.cache = cache_manager

        # 初始化核心组件
        self.pricing_manager = PricingManager()
        self.usage_tracker = UsageTracker(cache_manager)
        self.quota_manager = QuotaManager(cache_manager)
        self.invoice_generator = InvoiceGenerator()

        # 初始化支付处理器
        self.stripe_processor: Optional[StripeProcessor] = None
        self.paypal_processor: Optional[PayPalProcessor] = None
        self.webhook_handler: Optional[PaymentWebhookHandler] = None

        # 初始化支付处理器
        self._initialize_payment_processors()

    def _initialize_payment_processors(self):
        """初始化支付处理器"""
        try:
            # Stripe处理器
            if self.config.stripe_enabled and self.config.stripe_api_key:
                self.stripe_processor = StripeProcessor(
                    api_key=self.config.stripe_api_key,
                    webhook_secret=self.config.stripe_webhook_secret
                )
                logger.info("Stripe支付处理器初始化成功")

            # PayPal处理器
            if self.config.paypal_enabled and self.config.paypal_client_id:
                self.paypal_processor = PayPalProcessor(
                    client_id=self.config.paypal_client_id,
                    client_secret=self.config.paypal_client_secret,
                    sandbox=self.config.paypal_sandbox
                )
                logger.info("PayPal支付处理器初始化成功")

            # Webhook处理器
            if self.stripe_processor or self.paypal_processor:
                self.webhook_handler = PaymentWebhookHandler(
                    stripe_processor=self.stripe_processor,
                    paypal_processor=self.paypal_processor,
                    usage_tracker=self.usage_tracker,
                    quota_manager=self.quota_manager
                )
                logger.info("Webhook处理器初始化成功")

        except Exception as e:
            logger.error(f"支付处理器初始化失败: {e}")

    # 订阅管理

    async def create_subscription(
        self,
        user_id: str,
        plan_type: PlanType,
        billing_cycle: BillingCycle,
        payment_provider: PaymentProvider,
        payment_method_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建订阅

        Args:
            user_id: 用户ID
            plan_type: 计划类型
            billing_cycle: 计费周期
            payment_provider: 支付提供商
            payment_method_id: 支付方式ID

        Returns:
            订阅创建结果
        """
        try:
            # 获取价格计划
            plan = await self.pricing_manager.get_plan(plan_type, billing_cycle)
            if not plan:
                raise ValueError(f"价格计划不存在: {plan_type} - {billing_cycle}")

            # 创建内部订阅记录
            subscription = await self.pricing_manager.create_subscription(
                user_id=user_id,
                plan_id=plan.id,
                billing_cycle=billing_cycle
            )

            # 创建外部支付订阅
            external_subscription = None
            if payment_provider == PaymentProvider.STRIPE and self.stripe_processor:
                # 创建Stripe客户
                customer_id = await self._get_or_create_stripe_customer(user_id)

                # 创建Stripe价格
                price_id = await self.stripe_processor.create_price(
                    unit_amount=plan.price,
                    currency=self.config.currency,
                    product_name=plan.name,
                    product_description=plan.description,
                    recurring={
                        "interval": billing_cycle.value,
                        "interval_count": 1
                    }
                )

                # 创建Stripe订阅
                external_subscription = await self.stripe_processor.create_subscription(
                    customer_id=customer_id,
                    price_id=price_id,
                    payment_method_id=payment_method_id,
                    trial_period_days=plan.trial_days
                )

            elif payment_provider == PaymentProvider.PAYPAL and self.paypal_processor:
                # PayPal订阅创建（需要前端重定向）
                external_subscription = await self.paypal_processor.create_subscription(
                    plan_id=plan.paypal_plan_id,  # 需要预先在PayPal创建
                    return_url=self.config.webhook_endpoints.get("return_url"),
                    cancel_url=self.config.webhook_endpoints.get("cancel_url")
                )

            # 更新订阅记录
            if external_subscription:
                await self._update_subscription_with_provider(
                    subscription.id,
                    payment_provider,
                    external_subscription
                )

            # 更新用户配额
            await self.quota_manager.upgrade_user_plan(user_id, plan_type.value)

            return {
                "subscription_id": subscription.id,
                "user_id": user_id,
                "plan_type": plan_type.value,
                "billing_cycle": billing_cycle.value,
                "provider": payment_provider.value,
                "status": subscription.status.value,
                "current_period_start": subscription.current_period_start.isoformat(),
                "current_period_end": subscription.current_period_end.isoformat(),
                "external_subscription": external_subscription.to_dict() if external_subscription else None
            }

        except Exception as e:
            logger.error(f"创建订阅失败: {e}")
            raise PaymentError(f"创建订阅失败: {e}")

    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True
    ) -> Dict[str, Any]:
        """
        取消订阅

        Args:
            subscription_id: 订阅ID
            at_period_end: 是否在周期结束时取消

        Returns:
            取消结果
        """
        try:
            # 获取订阅信息
            subscription = await self.pricing_manager.get_subscription(subscription_id)
            if not subscription:
                raise ValueError("订阅不存在")

            # 取消外部订阅
            if subscription.provider == PaymentProvider.STRIPE and self.stripe_processor:
                await self.stripe_processor.cancel_subscription(
                    subscription.provider_subscription_id,
                    at_period_end
                )
            elif subscription.provider == PaymentProvider.PAYPAL and self.paypal_processor:
                await self.paypal_processor.cancel_subscription(
                    subscription.provider_subscription_id
                )

            # 更新内部订阅状态
            await self.pricing_manager.cancel_subscription(subscription_id, at_period_end)

            # 如果立即取消，降级用户配额
            if not at_period_end:
                await self.quota_manager.downgrade_to_free_plan(subscription.user_id)

            return {
                "subscription_id": subscription_id,
                "status": "cancelled" if not at_period_end else "active_until_period_end",
                "cancelled_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"取消订阅失败: {e}")
            raise PaymentError(f"取消订阅失败: {e}")

    async def upgrade_subscription(
        self,
        subscription_id: str,
        new_plan_type: PlanType
    ) -> Dict[str, Any]:
        """
        升级订阅

        Args:
            subscription_id: 订阅ID
            new_plan_type: 新计划类型

        Returns:
            升级结果
        """
        try:
            # 获取当前订阅
            subscription = await self.pricing_manager.get_subscription(subscription_id)
            if not subscription:
                raise ValueError("订阅不存在")

            # 获取新计划
            new_plan = await self.pricing_manager.get_plan(new_plan_type, subscription.billing_cycle)
            if not new_plan:
                raise ValueError(f"新计划不存在: {new_plan_type}")

            # 升级外部订阅
            if subscription.provider == PaymentProvider.STRIPE and self.stripe_processor:
                # Stripe订阅升级逻辑
                price_id = await self.stripe_processor.create_price(
                    unit_amount=new_plan.price,
                    currency=self.config.currency,
                    product_name=new_plan.name,
                    product_description=new_plan.description,
                    recurring={
                        "interval": subscription.billing_cycle.value,
                        "interval_count": 1
                    }
                )
                # TODO: 实现Stripe订阅升级

            # 更新内部订阅
            await self.pricing_manager.change_subscription_plan(subscription_id, new_plan.id)

            # 更新用户配额
            await self.quota_manager.upgrade_user_plan(subscription.user_id, new_plan_type.value)

            return {
                "subscription_id": subscription_id,
                "old_plan": subscription.plan_id,
                "new_plan": new_plan.id,
                "new_plan_type": new_plan_type.value,
                "upgraded_at": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"升级订阅失败: {e}")
            raise PaymentError(f"升级订阅失败: {e}")

    # 支付处理

    async def create_payment_intent(
        self,
        user_id: str,
        amount: float,
        payment_provider: PaymentProvider,
        payment_method_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> PaymentResult:
        """
        创建支付意图

        Args:
            user_id: 用户ID
            amount: 金额
            payment_provider: 支付提供商
            payment_method_id: 支付方式ID
            description: 描述

        Returns:
            支付结果
        """
        try:
            if payment_provider == PaymentProvider.STRIPE and self.stripe_processor:
                result = await self.stripe_processor.create_payment_intent(
                    amount=amount,
                    currency=self.config.currency,
                    payment_method_id=payment_method_id,
                    metadata={"user_id": user_id}
                )

            elif payment_provider == PaymentProvider.PAYPAL and self.paypal_processor:
                result = await self.paypal_processor.create_payment_intent(
                    amount=amount,
                    currency=self.config.currency,
                    description=description,
                    metadata={"user_id": user_id}
                )

            else:
                raise ValueError(f"不支持的支付提供商: {payment_provider}")

            # 保存支付记录
            if result.success:
                await self._save_payment_record(
                    user_id=user_id,
                    payment_intent_id=result.payment_intent_id,
                    provider=payment_provider,
                    amount=amount,
                    currency=self.config.currency,
                    status=result.status
                )

            return result

        except Exception as e:
            logger.error(f"创建支付意图失败: {e}")
            return PaymentResult(
                success=False,
                failure_reason=str(e)
            )

    async def confirm_payment(
        self,
        payment_intent_id: str,
        payment_provider: PaymentProvider,
        payment_method_id: Optional[str] = None
    ) -> PaymentResult:
        """
        确认支付

        Args:
            payment_intent_id: 支付意图ID
            payment_provider: 支付提供商
            payment_method_id: 支付方式ID

        Returns:
            支付结果
        """
        try:
            if payment_provider == PaymentProvider.STRIPE and self.stripe_processor:
                result = await self.stripe_processor.confirm_payment_intent(
                    payment_intent_id=payment_intent_id,
                    payment_method_id=payment_method_id
                )

            else:
                raise ValueError(f"支付确认不支持提供商: {payment_provider}")

            # 更新支付状态
            if result.success:
                await self._update_payment_status(
                    payment_intent_id,
                    result.status
                )

            return result

        except Exception as e:
            logger.error(f"确认支付失败: {e}")
            return PaymentResult(
                success=False,
                failure_reason=str(e)
            )

    # 使用量和配额管理

    async def track_usage(
        self,
        user_id: str,
        usage_type: UsageType,
        model: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        request_size: int = 0,
        response_size: int = 0,
        response_time_ms: int = 0,
        status_code: int = 200,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        跟踪使用量

        Args:
            user_id: 用户ID
            usage_type: 使用类型
            model: 模型名称
            input_tokens: 输入tokens
            output_tokens: 输出tokens
            request_size: 请求大小
            response_size: 响应大小
            response_time_ms: 响应时间
            status_code: 状态码
            metadata: 元数据

        Returns:
            使用量跟踪结果
        """
        try:
            # 记录使用量
            usage_record = await self.usage_tracker.track_usage(
                user_id=user_id,
                usage_type=usage_type,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                request_size=request_size,
                response_size=response_size,
                response_time_ms=response_time_ms,
                status_code=status_code,
                metadata=metadata or {}
            )

            # 检查配额
            quota_violation = None
            if not usage_record.is_successful:
                quota_violation = await self.quota_manager.check_quota_violation(
                    user_id=user_id,
                    usage_type=usage_type,
                    amount=input_tokens + output_tokens
                )

                if quota_violation:
                    # 记录配额违规
                    await self.quota_manager.record_quota_violation(quota_violation)

            return {
                "usage_record_id": usage_record.id,
                "cost": usage_record.cost,
                "successful": usage_record.is_successful,
                "quota_violation": quota_violation.to_dict() if quota_violation else None,
                "message": "Usage tracked successfully" if usage_record.is_successful else "Usage limit exceeded"
            }

        except Exception as e:
            logger.error(f"使用量跟踪失败: {e}")
            return {
                "error": str(e),
                "successful": False
            }

    async def get_usage_stats(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        usage_type: Optional[UsageType] = None
    ) -> UsageStats:
        """
        获取使用量统计

        Args:
            user_id: 用户ID
            start_date: 开始日期
            end_date: 结束日期
            usage_type: 使用类型

        Returns:
            使用量统计
        """
        return await self.usage_tracker.get_usage_stats(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            usage_type=usage_type
        )

    async def get_quota_status(self, user_id: str) -> Dict[str, Any]:
        """
        获取配额状态

        Args:
            user_id: 用户ID

        Returns:
            配额状态
        """
        return await self.quota_manager.get_quota_status(user_id)

    # 发票管理

    async def generate_invoice(
        self,
        user_id: str,
        invoice_type: str = "monthly",
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        生成发票

        Args:
            user_id: 用户ID
            invoice_type: 发票类型
            period_start: 开始周期
            period_end: 结束周期

        Returns:
            发票数据或None
        """
        try:
            if invoice_type == "monthly":
                if not period_start:
                    period_start = datetime.now(timezone.utc).replace(day=1)
                if not period_end:
                    period_end = period_start + timedelta(days=32)
                    period_end = period_end.replace(day=1) - timedelta(days=1)

                # 获取用户订阅
                subscriptions = await self.pricing_manager.get_user_subscriptions(user_id)
                if not subscriptions:
                    return None

                subscription = subscriptions[0]  # 假设只有一个活跃订阅
                return await self.invoice_generator.generate_monthly_invoice(
                    user_id=user_id,
                    subscription_id=subscription.id,
                    period_start=period_start,
                    period_end=period_end
                )

            else:
                raise ValueError(f"不支持的发票类型: {invoice_type}")

        except Exception as e:
            logger.error(f"生成发票失败: {e}")
            return None

    async def get_invoice_pdf(self, invoice_id: str) -> Optional[bytes]:
        """
        获取发票PDF

        Args:
            invoice_id: 发票ID

        Returns:
            PDF内容或None
        """
        return await self.invoice_generator.get_invoice_pdf(invoice_id)

    # Webhook处理

    async def handle_webhook(
        self,
        provider: PaymentProvider,
        payload: bytes,
        headers: Dict[str, str],
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理webhook

        Args:
            provider: 支付提供商
            payload: 载荷
            headers: 头信息
            signature: 签名

        Returns:
            处理结果
        """
        if not self.webhook_handler:
            raise ValueError("Webhook处理器未初始化")

        return await self.webhook_handler.handle_webhook(
            provider=provider,
            payload=payload,
            headers=headers,
            signature=signature
        )

    # 辅助方法

    async def _get_or_create_stripe_customer(self, user_id: str) -> str:
        """获取或创建Stripe客户"""
        # TODO: 实现Stripe客户管理
        return f"cus_{user_id}"

    async def _update_subscription_with_provider(
        self,
        subscription_id: str,
        provider: PaymentProvider,
        external_subscription: Subscription
    ):
        """更新订阅的外部提供商信息"""
        # TODO: 实现订阅更新
        logger.info(f"更新订阅提供商信息: {subscription_id} -> {provider.value}")

    async def _save_payment_record(
        self,
        user_id: str,
        payment_intent_id: str,
        provider: PaymentProvider,
        amount: float,
        currency: Currency,
        status: PaymentStatus
    ):
        """保存支付记录"""
        # TODO: 实现支付记录保存
        logger.info(f"保存支付记录: {user_id} - {payment_intent_id}")

    async def _update_payment_status(
        self,
        payment_intent_id: str,
        status: PaymentStatus
    ):
        """更新支付状态"""
        # TODO: 实现支付状态更新
        logger.info(f"更新支付状态: {payment_intent_id} -> {status.value}")

    # 统计和报告

    async def get_billing_summary(self, user_id: str) -> Dict[str, Any]:
        """
        获取计费摘要

        Args:
            user_id: 用户ID

        Returns:
            计费摘要
        """
        try:
            # 获取当前订阅
            subscriptions = await self.pricing_manager.get_user_subscriptions(user_id)
            current_subscription = subscriptions[0] if subscriptions else None

            # 获取本月使用量
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            usage_stats = await self.get_usage_stats(user_id, month_start, now)

            # 获取配额状态
            quota_status = await self.get_quota_status(user_id)

            # 获取最近发票
            # TODO: 实现发票查询

            return {
                "user_id": user_id,
                "current_subscription": {
                    "plan_type": current_subscription.plan.type.value if current_subscription else "free",
                    "status": current_subscription.status.value if current_subscription else "none",
                    "current_period_end": current_subscription.current_period_end.isoformat() if current_subscription else None,
                    "days_until_renewal": current_subscription.days_until_renewal if current_subscription else None
                },
                "usage_this_month": {
                    "total_requests": usage_stats.total_requests,
                    "total_tokens": usage_stats.total_tokens,
                    "total_cost": usage_stats.total_cost,
                    "successful_requests": usage_stats.successful_requests,
                    "failed_requests": usage_stats.failed_requests
                },
                "quota_status": quota_status,
                "billing_period": {
                    "start": month_start.isoformat(),
                    "end": now.isoformat()
                }
            }

        except Exception as e:
            logger.error(f"获取计费摘要失败: {e}")
            return {"error": str(e)}

    async def get_revenue_stats(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        获取收入统计

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            收入统计
        """
        try:
            # TODO: 实现收入统计
            return {
                "total_revenue": 0.0,
                "total_subscriptions": 0,
                "new_subscriptions": 0,
                "churned_subscriptions": 0,
                "mrr": 0.0,  # Monthly Recurring Revenue
                "arr": 0.0,  # Annual Recurring Revenue
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }

        except Exception as e:
            logger.error(f"获取收入统计失败: {e}")
            return {"error": str(e)}