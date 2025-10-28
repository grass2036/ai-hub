"""
Stripe支付处理器

提供Stripe支付网关的集成处理。
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import logging
import json
import asyncio

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    logger.warning("Stripe library not available. Install with: pip install stripe")

from .payment_types import (
    PaymentProvider, PaymentStatus, PaymentType, Currency,
    PaymentMethod, PaymentIntent, PaymentResult, Refund,
    Subscription, PaymentError
)

logger = logging.getLogger(__name__)


class StripeProcessor:
    """Stripe支付处理器"""

    def __init__(self, api_key: str, webhook_secret: str = None):
        """
        初始化Stripe处理器

        Args:
            api_key: Stripe API密钥
            webhook_secret: Webhook密钥
        """
        if not STRIPE_AVAILABLE:
            raise ImportError("Stripe library not available. Install with: pip install stripe")

        stripe.api_key = api_key
        self.api_key = api_key
        self.webhook_secret = webhook_secret

        # 支持的货币
        self.supported_currencies = {
            Currency.USD: "usd",
            Currency.EUR: "eur",
            Currency.GBP: "gbp",
            Currency.JPY: "jpy",
            Currency.CNY: "cny"
        }

    async def create_payment_intent(
        self,
        amount: float,
        currency: Currency,
        payment_method_id: Optional[str] = None,
        confirmation_method: str = "automatic",
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> PaymentResult:
        """
        创建支付意图

        Args:
            amount: 金额（以最小货币单位表示，例如美元用cent）
            currency: 货币
            payment_method_id: 支付方式ID
            confirmation_method: 确认方式
            return_url: 成功返回URL
            cancel_url: 取消返回URL
            metadata: 元数据

        Returns:
            支付结果
        """
        try:
            # 转换金额为cents（美元）
            if currency == Currency.USD:
                amount_cents = int(amount * 100)
            else:
                # 其他货币根据Stripe的规则转换
                amount_cents = int(amount)

            # 构建支付意图参数
            intent_params = {
                "amount": amount_cents,
                "currency": self.supported_currencies[currency],
                "confirmation_method": confirmation_method,
                "metadata": metadata or {}
            }

            if payment_method_id:
                intent_params["payment_method"] = payment_method_id
            else:
                intent_params["automatic_payment_methods"] = {"enabled": True}

            if return_url:
                intent_params["return_url"] = return_url
            if cancel_url:
                intent_params["cancel_url"] = cancel_url

            # 创建支付意图
            intent = stripe.PaymentIntent.create(**intent_params)

            # 构建返回结果
            result = PaymentResult(
                success=True,
                payment_intent_id=intent.id,
                provider_transaction_id=intent.id,
                status=self._convert_stripe_status(intent.status),
                amount=float(intent.amount) / 100,  # 转换回美元
                currency=currency,
                gateway_response=intent.to_dict()
            )

            # 如果需要确认，包含client_secret
            if intent.status in ["requires_action", "requires_payment_method"]:
                result.client_secret = intent.client_secret

            logger.info(f"Stripe支付意图创建成功: {intent.id}")
            return result

        except stripe.error.StripeError as e:
            logger.error(f"Stripe支付意图创建失败: {e}")
            return PaymentResult(
                success=False,
                failure_reason=str(e),
                gateway_response={"error": str(e)}
            )
        except Exception as e:
            logger.error(f"Stripe支付意图创建异常: {e}")
            return PaymentResult(
                success=False,
                failure_reason="Internal server error",
                gateway_response={"error": str(e)}
            )

    async def confirm_payment_intent(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None
    ) -> PaymentResult:
        """
        确认支付意图

        Args:
            payment_intent_id: 支付意图ID
            payment_method_id: 支付方式ID

        Returns:
            支付结果
        """
        try:
            # 获取支付意图
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            # 如果需要，设置支付方式
            if payment_method_id and intent.status == "requires_payment_method":
                intent = stripe.PaymentIntent.modify(
                    payment_intent_id,
                    payment_method=payment_method_id
                )

            # 确认支付
            if intent.status in ["requires_confirmation", "requires_action"]:
                intent = stripe.PaymentIntent.confirm(payment_intent_id)

            # 构建返回结果
            result = PaymentResult(
                success=True,
                payment_intent_id=intent.id,
                provider_transaction_id=intent.charges.data[0].id if intent.charges.data else None,
                status=self._convert_stripe_status(intent.status),
                amount=float(intent.amount) / 100,
                currency=Currency(self._reverse_currency_lookup(intent.currency)),
                fee_amount=float(intent.charges.data[0].balance_transaction.fee / 100) if intent.charges.data else 0,
                net_amount=float(intent.charges.data[0].balance_transaction.net / 100) if intent.charges.data else 0,
                gateway_response=intent.to_dict()
            )

            logger.info(f"Stripe支付确认成功: {payment_intent_id}")
            return result

        except stripe.error.StripeError as e:
            logger.error(f"Stripe支付确认失败: {e}")
            return PaymentResult(
                success=False,
                failure_reason=str(e),
                gateway_response={"error": str(e)}
            )
        except Exception as e:
            logger.error(f"Stripe支付确认异常: {e}")
            return PaymentResult(
                success=False,
                failure_reason="Internal server error",
                gateway_response={"error": str(e)}
            )

    async def create_payment_method(
        self,
        payment_method_type: str,
        card_data: Optional[Dict[str, Any]] = None,
        billing_details: Optional[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        创建支付方式

        Args:
            payment_method_type: 支付方式类型
            card_data: 卡片数据
            billing_details: 账单详情
            metadata: 元数据

        Returns:
            支付方式ID
        """
        try:
            method_params = {
                "type": payment_method_type,
                "metadata": metadata or {}
            }

            if payment_method_type == "card":
                if not card_data:
                    raise ValueError("Card data is required for card payment method")

                method_params.update({
                    "card": card_data,
                    "billing_details": billing_details
                })

            # 创建支付方式
            payment_method = stripe.PaymentMethod.create(**method_params)

            logger.info(f"Stripe支付方式创建成功: {payment_method.id}")
            return payment_method.id

        except stripe.error.StripeError as e:
            logger.error(f"Stripe支付方式创建失败: {e}")
            raise PaymentError(str(e), provider="stripe")
        except Exception as e:
            logger.error(f"Stripe支付方式创建异常: {e}")
            raise PaymentError("Internal server error", provider="stripe")

    async def retrieve_payment_method(self, payment_method_id: str) -> Optional[Dict[str, Any]]:
        """
        获取支付方式信息

        Args:
            payment_method_id: 支付方式ID

        Returns:
            支付方式信息或None
        """
        try:
            payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
            return payment_method.to_dict()

        except stripe.error.StripeError as e:
            logger.error(f"Stripe支付方式获取失败: {e}")
            return None
        except Exception as e:
            logger.error(f"Stripe支付方式获取异常: {e}")
            return None

    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        payment_method_id: Optional[str] = None,
        trial_period_days: Optional[int] = None,
        metadata: Dict[str, Any] = None
    ) -> Subscription:
        """
        创建订阅

        Args:
            customer_id: 客户ID
            price_id: 价格ID
            payment_method_id: 支付方式ID
            trial_period_days: 试用天数
            metadata: 元数据

        Returns:
            订阅信息
        """
        try:
            # 构建订阅参数
            subscription_params = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "metadata": metadata or {}
            }

            # 设置支付方式
            if payment_method_id:
                subscription_params["default_payment_method"] = payment_method_id

            # 设置试用期
            if trial_period_days:
                subscription_params["trial_period_days"] = trial_period_days

            # 创建订阅
            subscription = stripe.Subscription.create(**subscription_params)

            # 构建返回对象
            result = Subscription(
                id=subscription.id,
                user_id=customer_id,  # 这里应该是用户ID，需要从customer_id映射
                plan_id=price_id,
                price_id=price_id,
                provider=PaymentProvider.STRIPE,
                provider_subscription_id=subscription.id,
                status=subscription.status,
                current_period_start=datetime.fromtimestamp(
                    subscription.current_period_start, timezone.utc
                ),
                current_period_end=datetime.fromtimestamp(
                    subscription.current_period_end, timezone.utc
                ),
                trial_start=datetime.fromtimestamp(
                    subscription.trial_start, timezone.utc
                ) if subscription.trial_start else None,
                trial_end=datetime.fromtimestamp(
                    subscription.trial_end, timezone.utc
                ) if subscription.trial_end else None,
                cancel_at_period_end=subscription.cancel_at_period_end,
                metadata=subscription.metadata or {},
                created_at=datetime.fromtimestamp(
                    subscription.created, timezone.utc
                ),
                updated_at=datetime.fromtimestamp(
                    subscription.start_date, timezone.utc
                )
            )

            logger.info(f"Stripe订阅创建成功: {subscription.id}")
            return result

        except stripe.error.StripeError as e:
            logger.error(f"Stripe订阅创建失败: {e}")
            raise PaymentError(str(e), provider="stripe")
        except Exception as e:
            logger.error(f"Stripe订阅创建异常: {e}")
            raise PaymentError("Internal server error", provider="stripe")

    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = False
    ) -> Subscription:
        """
        取消订阅

        Args:
            subscription_id: 订阅ID
            at_period_end: 是否在周期结束时取消

        Returns:
            取消后的订阅信息
        """
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=at_period_end
            )

            result = Subscription(
                id=subscription.id,
                user_id="",  # 需要从数据库查询
                plan_id="",  # 需要从数据库查询
                price_id="",
                provider=PaymentProvider.STRIPE,
                provider_subscription_id=subscription.id,
                status=subscription.status,
                current_period_start=datetime.fromtimestamp(
                    subscription.current_period_start, timezone.utc
                ),
                current_period_end=datetime.fromtimestamp(
                    subscription.current_period_end, timezone.utc
                ),
                trial_start=datetime.fromtimestamp(
                    subscription.trial_start, timezone.utc
                ) if subscription.trial_start else None,
                trial_end=datetime.fromtimestamp(
                    subscription.trial_end, timezone.utc
                ) if subscription.trial_end else None,
                cancel_at_period_end=subscription.cancel_at_period_end,
                metadata=subscription.metadata or {},
                created_at=datetime.fromtimestamp(
                    subscription.created, timezone.utc
                ),
                updated_at=datetime.fromtimestamp(
                    subscription.start_date, timezone.utc
                )
            )

            logger.info(f"Stripe订阅取消成功: {subscription_id}")
            return result

        except stripe.error.StripeError as e:
            logger.error(f"Stripe订阅取消失败: {e}")
            raise PaymentError(str(e), provider="stripe")
        except Exception as e:
            logger.error(f"Stripe订阅取消异常: {e}")
            raise PaymentError("Internal server error", provider="stripe")

    async def create_refund(
        self,
        charge_id: str,
        amount: Optional[float] = None,
        reason: str = "Requested by customer"
    ) -> Refund:
        """
        创建退款

        Args:
            charge_id: 支付charge ID
            amount: 退款金额（None表示全额退款）
            reason: 退款原因

        Returns:
            退款信息
        """
        try:
            # 构建退款参数
            refund_params = {
                "charge": charge_id,
                "reason": reason,
                "metadata": {"created_by": "stripe_processor"}
            }

            if amount:
                # 转换为cents
                refund_params["amount"] = int(amount * 100)

            # 创建退款
            refund = stripe.Refund.create(**refund_params)

            result = Refund(
                id=refund.id,
                payment_intent_id=refund.charge,
                amount=float(refund.amount) / 100,
                reason=reason,
                status=self._convert_stripe_status(refund.status),
                provider_refund_id=refund.id,
                fee_amount=float(refund.fee / 100) if refund.fee else 0,
                net_amount=float(refund.net / 100) if refund.net else 0,
                metadata=refund.metadata or {},
                created_at=datetime.fromtimestamp(refund.created, timezone.utc)
            )

            logger.info(f"Stripe退款创建成功: {refund.id}")
            return result

        except stripe.error.StripeError as e:
            logger.error(f"Stripe退款创建失败: {e}")
            raise PaymentError(str(e), provider="stripe")
        except Exception as e:
            logger.error(f"Stripe退款创建异常: {e}")
            raise PaymentError("Internal server error", provider="stripe")

    async def handle_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        处理Stripe webhook

        Args:
            payload: Webhook载荷
            signature: 签名

        Returns:
            处理结果
        """
        try:
            if not self.webhook_secret:
                raise PaymentError("Webhook secret not configured", provider="stripe")

            # 验证webhook签名
            try:
                event = stripe.Webhook.construct_event(
                    payload, signature, self.webhook_secret
                )
            except ValueError as e:
                raise PaymentError(f"Webhook signature verification failed: {e}", provider="stripe")

            # 处理webhook事件
            result = {
                "event_id": event.id,
                "type": event.type,
                "data": event.data.to_dict(),
                "created": datetime.fromtimestamp(event.created, timezone.utc).isoformat()
            }

            logger.info(f"Stripe webhook处理成功: {event.type}")
            return result

        except Exception as e:
            logger.error(f"Stripe webhook处理失败: {e}")
            raise PaymentError(f"Webhook processing failed: {e}", provider="stripe")

    def _convert_stripe_status(self, stripe_status: str) -> PaymentStatus:
        """转换Stripe状态"""
        status_mapping = {
            "requires_payment_method": PaymentStatus.PENDING,
            "requires_confirmation": PaymentStatus.PENDING,
            "requires_action": PaymentStatus.PENDING,
            "processing": PaymentStatus.PROCESSING,
            "succeeded": PaymentStatus.COMPLETED,
            "canceled": PaymentStatus.CANCELLED,
            "failed": PaymentStatus.FAILED
        }

        return status_mapping.get(stripe_status, PaymentStatus.PENDING)

    def _reverse_currency_lookup(self, stripe_currency: str) -> Currency:
        """反向查找货币类型"""
        currency_mapping = {v: k for k, v in self.supported_currencies.items()}
        return currency_mapping.get(stripe_currency, Currency.USD)

    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        创建Stripe客户

        Args:
            email: 邮箱
            name: 姓名
            metadata: 元数据

        Returns:
            客户ID
        """
        try:
            customer_params = {
                "email": email,
                "metadata": metadata or {}
            }

            if name:
                customer_params["name"] = name

            customer = stripe.Customer.create(**customer_params)
            return customer.id

        except stripe.error.StripeError as e:
            logger.error(f"Stripe客户创建失败: {e}")
            raise PaymentError(str(e), provider="stripe")
        except Exception as e:
            logger.error(f"Stripe客户创建异常: {e}")
            raise PaymentError("Internal server error", provider="stripe")

    async def create_price(
        self,
        unit_amount: float,
        currency: Currency,
        product_name: str,
        product_description: str,
        recurring: Optional[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        创建价格

        Args:
            unit_amount: 单位金额
            currency: 货币
            product_name: 产品名称
            product_description: 产品描述
            recurring: 循环配置
            metadata: 元数据

        Returns:
            价格ID
        """
        try:
            # 转换金额为cents
            if currency == Currency.USD:
                amount_cents = int(unit_amount * 100)
            else:
                amount_cents = int(unit_amount)

            # 创建产品
            product = stripe.Product.create(
                name=product_name,
                description=product_description,
                metadata=metadata or {}
            )

            # 构建价格参数
            price_params = {
                "product": product.id,
                "unit_amount": amount_cents,
                "currency": self.supported_currencies[currency],
                "metadata": metadata or {}
            }

            # 添加循环配置
            if recurring:
                price_params["recurring"] = recurring

            # 创建价格
            price = stripe.Price.create(**price_params)
            return price.id

        except stripe.error.StripeError as e:
            logger.error(f"Stripe价格创建失败: {e}")
            raise PaymentError(str(e), provider="stripe")
        except Exception as e:
            logger.error(f"Stripe价格创建异常: {e}")
            raise PaymentError("Internal server error", provider="stripe")