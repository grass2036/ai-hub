"""
支付Webhook处理器

统一处理来自不同支付提供商的webhook事件。
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from enum import Enum

from .stripe_processor import StripeProcessor
from .paypal_processor import PayPalProcessor
from .payment_types import PaymentProvider, PaymentStatus, PaymentType
from ..usage_tracker import UsageTracker
from ..quota_manager import QuotaManager

logger = logging.getLogger(__name__)


class WebhookEventType(str, Enum):
    """Webhook事件类型"""
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_REFUNDED = "payment_refunded"
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    SUBSCRIPTION_PAYMENT_SUCCEEDED = "subscription_payment_succeeded"
    SUBSCRIPTION_PAYMENT_FAILED = "subscription_payment_failed"
    INVOICE_CREATED = "invoice_created"
    INVOICE_PAYMENT_SUCCEEDED = "invoice_payment_succeeded"
    INVOICE_PAYMENT_FAILED = "invoice_payment_failed"


class PaymentWebhookHandler:
    """支付Webhook处理器"""

    def __init__(
        self,
        stripe_processor: Optional[StripeProcessor] = None,
        paypal_processor: Optional[PayPalProcessor] = None,
        usage_tracker: Optional[UsageTracker] = None,
        quota_manager: Optional[QuotaManager] = None
    ):
        """
        初始化Webhook处理器

        Args:
            stripe_processor: Stripe处理器
            paypal_processor: PayPal处理器
            usage_tracker: 使用量跟踪器
            quota_manager: 配额管理器
        """
        self.stripe_processor = stripe_processor
        self.paypal_processor = paypal_processor
        self.usage_tracker = usage_tracker
        self.quota_manager = quota_manager

        # 事件处理器映射
        self.event_handlers = {
            # Stripe事件
            "payment_intent.succeeded": self._handle_stripe_payment_succeeded,
            "payment_intent.payment_failed": self._handle_stripe_payment_failed,
            "payment_intent.canceled": self._handle_stripe_payment_canceled,
            "invoice.payment_succeeded": self._handle_stripe_invoice_payment_succeeded,
            "invoice.payment_failed": self._handle_stripe_invoice_payment_failed,
            "invoice.created": self._handle_stripe_invoice_created,
            "customer.subscription.created": self._handle_stripe_subscription_created,
            "customer.subscription.updated": self._handle_stripe_subscription_updated,
            "customer.subscription.deleted": self._handle_stripe_subscription_cancelled,
            "charge.dispute.created": self._handle_stripe_dispute_created,

            # PayPal事件（简化映射）
            "PAYMENT.SALE.COMPLETED": self._handle_paypal_payment_completed,
            "PAYMENT.SALE.DENIED": self._handle_paypal_payment_denied,
            "PAYMENT.SALE.REFUNDED": self._handle_paypal_payment_refunded,
            "BILLING.SUBSCRIPTION.CREATED": self._handle_paypal_subscription_created,
            "BILLING.SUBSCRIPTION.CANCELLED": self._handle_paypal_subscription_cancelled,
            "BILLING.SUBSCRIPTION.SUSPENDED": self._handle_paypal_subscription_suspended,
        }

    async def handle_webhook(
        self,
        provider: PaymentProvider,
        payload: bytes,
        headers: Dict[str, str],
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理webhook请求

        Args:
            provider: 支付提供商
            payload: 请求载荷
            headers: HTTP头
            signature: 签名（Stripe）

        Returns:
            处理结果
        """
        try:
            # 根据提供商处理webhook
            if provider == PaymentProvider.STRIPE:
                webhook_data = await self._handle_stripe_webhook(payload, signature)
            elif provider == PaymentProvider.PAYPAL:
                webhook_data = await self._handle_paypal_webhook(payload, headers)
            else:
                raise ValueError(f"Unsupported payment provider: {provider}")

            # 获取事件类型和处理器
            event_type = webhook_data.get("type") or webhook_data.get("event_type")
            if not event_type:
                logger.warning("Webhook事件类型为空")
                return {"status": "ignored", "reason": "No event type"}

            # 查找处理器
            handler = self.event_handlers.get(event_type)
            if not handler:
                logger.warning(f"未找到webhook事件处理器: {event_type}")
                return {"status": "ignored", "reason": f"No handler for event: {event_type}"}

            # 执行处理器
            try:
                result = await handler(webhook_data)
                logger.info(f"Webhook事件处理成功: {event_type}")
                return {
                    "status": "processed",
                    "event_type": event_type,
                    "result": result
                }
            except Exception as e:
                logger.error(f"Webhook事件处理失败: {event_type}, 错误: {e}")
                return {
                    "status": "error",
                    "event_type": event_type,
                    "error": str(e)
                }

        except Exception as e:
            logger.error(f"Webhook处理失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def _handle_stripe_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """处理Stripe webhook"""
        if not self.stripe_processor:
            raise ValueError("Stripe processor not configured")

        return await self.stripe_processor.handle_webhook(payload, signature)

    async def _handle_paypal_webhook(
        self,
        payload: bytes,
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """处理PayPal webhook"""
        if not self.paypal_processor:
            raise ValueError("PayPal processor not configured")

        return await self.paypal_processor.handle_webhook(payload, headers)

    # Stripe事件处理器

    async def _handle_stripe_payment_succeeded(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Stripe支付成功事件"""
        intent = event_data.get("data", {}).get("object", {})
        payment_intent_id = intent.get("id")
        amount = intent.get("amount", 0) / 100  # 转换为美元
        currency = intent.get("currency", "usd").upper()
        metadata = intent.get("metadata", {})

        user_id = metadata.get("user_id")
        if not user_id:
            logger.warning(f"支付成功事件缺少用户ID: {payment_intent_id}")
            return {"error": "Missing user_id"}

        # 更新支付状态
        await self._update_payment_status(
            payment_intent_id,
            PaymentStatus.COMPLETED,
            amount=amount,
            currency=currency
        )

        # 如果是订阅支付，更新订阅状态
        subscription_id = metadata.get("subscription_id")
        if subscription_id:
            await self._update_subscription_status(subscription_id, "active")

        # 更新用户配额
        if self.quota_manager:
            await self._update_user_quota_after_payment(user_id, amount, metadata)

        return {
            "payment_intent_id": payment_intent_id,
            "user_id": user_id,
            "amount": amount,
            "currency": currency,
            "subscription_id": subscription_id
        }

    async def _handle_stripe_payment_failed(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Stripe支付失败事件"""
        intent = event_data.get("data", {}).get("object", {})
        payment_intent_id = intent.get("id")
        last_payment_error = intent.get("last_payment_error", {})
        metadata = intent.get("metadata", {})

        user_id = metadata.get("user_id")
        error_message = last_payment_error.get("message", "Payment failed")

        # 更新支付状态
        await self._update_payment_status(
            payment_intent_id,
            PaymentStatus.FAILED,
            failure_reason=error_message
        )

        # 如果是订阅支付失败，更新订阅状态
        subscription_id = metadata.get("subscription_id")
        if subscription_id:
            await self._update_subscription_status(subscription_id, "past_due")

        # 发送支付失败通知
        await self._send_payment_failure_notification(user_id, payment_intent_id, error_message)

        return {
            "payment_intent_id": payment_intent_id,
            "user_id": user_id,
            "error": error_message,
            "subscription_id": subscription_id
        }

    async def _handle_stripe_payment_canceled(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Stripe支付取消事件"""
        intent = event_data.get("data", {}).get("object", {})
        payment_intent_id = intent.get("id")
        metadata = intent.get("metadata", {})

        # 更新支付状态
        await self._update_payment_status(payment_intent_id, PaymentStatus.CANCELLED)

        return {
            "payment_intent_id": payment_intent_id,
            "user_id": metadata.get("user_id")
        }

    async def _handle_stripe_invoice_payment_succeeded(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Stripe发票支付成功事件"""
        invoice = event_data.get("data", {}).get("object", {})
        invoice_id = invoice.get("id")
        subscription_id = invoice.get("subscription")
        amount_paid = invoice.get("amount_paid", 0) / 100
        customer_id = invoice.get("customer")

        # 更新发票状态
        await self._update_invoice_status(invoice_id, "paid", amount_paid)

        # 更新订阅状态
        if subscription_id:
            await self._update_subscription_status(subscription_id, "active")

        # 更新用户配额
        if self.quota_manager and customer_id:
            user_id = await self._get_user_id_from_stripe_customer(customer_id)
            if user_id:
                metadata = {"subscription_id": subscription_id, "invoice_id": invoice_id}
                await self._update_user_quota_after_payment(user_id, amount_paid, metadata)

        return {
            "invoice_id": invoice_id,
            "subscription_id": subscription_id,
            "amount_paid": amount_paid,
            "customer_id": customer_id
        }

    async def _handle_stripe_invoice_payment_failed(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Stripe发票支付失败事件"""
        invoice = event_data.get("data", {}).get("object", {})
        invoice_id = invoice.get("id")
        subscription_id = invoice.get("subscription")
        customer_id = invoice.get("customer")

        # 更新发票状态
        await self._update_invoice_status(invoice_id, "open", 0)

        # 更新订阅状态
        if subscription_id:
            await self._update_subscription_status(subscription_id, "past_due")

        # 发送支付失败通知
        if customer_id:
            user_id = await self._get_user_id_from_stripe_customer(customer_id)
            if user_id:
                await self._send_payment_failure_notification(user_id, invoice_id, "Invoice payment failed")

        return {
            "invoice_id": invoice_id,
            "subscription_id": subscription_id,
            "customer_id": customer_id
        }

    async def _handle_stripe_invoice_created(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Stripe发票创建事件"""
        invoice = event_data.get("data", {}).get("object", {})
        invoice_id = invoice.get("id")
        subscription_id = invoice.get("subscription")
        amount_due = invoice.get("amount_due", 0) / 100

        # 保存发票信息
        await self._save_invoice_data(invoice_id, {
            "subscription_id": subscription_id,
            "amount_due": amount_due,
            "currency": invoice.get("currency", "usd").upper(),
            "status": "draft",
            "created_at": datetime.fromtimestamp(invoice.get("created"), timezone.utc)
        })

        return {
            "invoice_id": invoice_id,
            "subscription_id": subscription_id,
            "amount_due": amount_due
        }

    async def _handle_stripe_subscription_created(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Stripe订阅创建事件"""
        subscription = event_data.get("data", {}).get("object", {})
        subscription_id = subscription.get("id")
        customer_id = subscription.get("customer")
        status = subscription.get("status")

        # 获取用户ID
        user_id = await self._get_user_id_from_stripe_customer(customer_id)

        # 保存订阅信息
        await self._save_subscription_data(subscription_id, {
            "user_id": user_id,
            "stripe_customer_id": customer_id,
            "status": status,
            "current_period_start": datetime.fromtimestamp(
                subscription.get("current_period_start"), timezone.utc
            ),
            "current_period_end": datetime.fromtimestamp(
                subscription.get("current_period_end"), timezone.utc
            ),
            "created_at": datetime.fromtimestamp(subscription.get("created"), timezone.utc)
        })

        return {
            "subscription_id": subscription_id,
            "user_id": user_id,
            "status": status
        }

    async def _handle_stripe_subscription_updated(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Stripe订阅更新事件"""
        subscription = event_data.get("data", {}).get("object", {})
        subscription_id = subscription.get("id")
        status = subscription.get("status")

        # 更新订阅状态
        await self._update_subscription_status(subscription_id, status)

        return {
            "subscription_id": subscription_id,
            "status": status
        }

    async def _handle_stripe_subscription_cancelled(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Stripe订阅取消事件"""
        subscription = event_data.get("data", {}).get("object", {})
        subscription_id = subscription.get("id")

        # 更新订阅状态
        await self._update_subscription_status(subscription_id, "canceled")

        # 更新用户配额（降级到免费计划）
        if self.quota_manager:
            user_id = await self._get_user_id_from_subscription(subscription_id)
            if user_id:
                await self.quota_manager.downgrade_to_free_plan(user_id)

        return {
            "subscription_id": subscription_id,
            "status": "canceled"
        }

    async def _handle_stripe_dispute_created(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理Stripe争议创建事件"""
        dispute = event_data.get("data", {}).get("object", {})
        charge_id = dispute.get("charge")
        amount = dispute.get("amount", 0) / 100
        reason = dispute.get("reason")

        # 记录争议信息
        await self._record_dispute(charge_id, amount, reason)

        # 发送争议通知
        await self._send_dispute_notification(charge_id, amount, reason)

        return {
            "charge_id": charge_id,
            "amount": amount,
            "reason": reason
        }

    # PayPal事件处理器

    async def _handle_paypal_payment_completed(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理PayPal支付完成事件"""
        resource = event_data.get("resource", {})
        sale_id = resource.get("id")
        amount = float(resource.get("amount", {}).get("total", 0))
        currency = resource.get("amount", {}).get("currency", "USD")

        # 更新支付状态
        await self._update_payment_status_by_provider(
            sale_id,
            PaymentProvider.PAYPAL,
            PaymentStatus.COMPLETED,
            amount=amount,
            currency=currency
        )

        return {
            "sale_id": sale_id,
            "amount": amount,
            "currency": currency
        }

    async def _handle_paypal_payment_denied(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理PayPal支付拒绝事件"""
        resource = event_data.get("resource", {})
        sale_id = resource.get("id")

        # 更新支付状态
        await self._update_payment_status_by_provider(
            sale_id,
            PaymentProvider.PAYPAL,
            PaymentStatus.FAILED,
            failure_reason="Payment denied by PayPal"
        )

        return {
            "sale_id": sale_id,
            "status": "denied"
        }

    async def _handle_paypal_payment_refunded(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理PayPal支付退款事件"""
        resource = event_data.get("resource", {})
        sale_id = resource.get("sale_id")
        refund_id = resource.get("id")
        amount = float(resource.get("amount", {}).get("total", 0))

        # 记录退款
        await self._record_refund(refund_id, sale_id, amount, "PayPal refund")

        return {
            "refund_id": refund_id,
            "sale_id": sale_id,
            "amount": amount
        }

    async def _handle_paypal_subscription_created(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理PayPal订阅创建事件"""
        resource = event_data.get("resource", {})
        subscription_id = resource.get("id")
        status = resource.get("status")

        # 保存订阅信息
        await self._save_subscription_data(subscription_id, {
            "provider": PaymentProvider.PAYPAL,
            "status": status,
            "created_at": datetime.now(timezone.utc)
        })

        return {
            "subscription_id": subscription_id,
            "status": status
        }

    async def _handle_paypal_subscription_cancelled(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理PayPal订阅取消事件"""
        resource = event_data.get("resource", {})
        subscription_id = resource.get("id")

        # 更新订阅状态
        await self._update_subscription_status(subscription_id, "CANCELLED")

        return {
            "subscription_id": subscription_id,
            "status": "CANCELLED"
        }

    async def _handle_paypal_subscription_suspended(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理PayPal订阅暂停事件"""
        resource = event_data.get("resource", {})
        subscription_id = resource.get("id")

        # 更新订阅状态
        await self._update_subscription_status(subscription_id, "SUSPENDED")

        return {
            "subscription_id": subscription_id,
            "status": "SUSPENDED"
        }

    # 辅助方法

    async def _update_payment_status(
        self,
        payment_intent_id: str,
        status: PaymentStatus,
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        failure_reason: Optional[str] = None
    ):
        """更新支付状态"""
        # TODO: 实现数据库更新
        logger.info(f"更新支付状态: {payment_intent_id} -> {status.value}")

    async def _update_payment_status_by_provider(
        self,
        transaction_id: str,
        provider: PaymentProvider,
        status: PaymentStatus,
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        failure_reason: Optional[str] = None
    ):
        """根据提供商更新支付状态"""
        # TODO: 实现数据库更新
        logger.info(f"更新支付状态 ({provider}): {transaction_id} -> {status.value}")

    async def _update_invoice_status(
        self,
        invoice_id: str,
        status: str,
        amount_paid: Optional[float] = None
    ):
        """更新发票状态"""
        # TODO: 实现数据库更新
        logger.info(f"更新发票状态: {invoice_id} -> {status}")

    async def _update_subscription_status(self, subscription_id: str, status: str):
        """更新订阅状态"""
        # TODO: 实现数据库更新
        logger.info(f"更新订阅状态: {subscription_id} -> {status}")

    async def _save_invoice_data(self, invoice_id: str, data: Dict[str, Any]):
        """保存发票数据"""
        # TODO: 实现数据库保存
        logger.info(f"保存发票数据: {invoice_id}")

    async def _save_subscription_data(self, subscription_id: str, data: Dict[str, Any]):
        """保存订阅数据"""
        # TODO: 实现数据库保存
        logger.info(f"保存订阅数据: {subscription_id}")

    async def _get_user_id_from_stripe_customer(self, customer_id: str) -> Optional[str]:
        """从Stripe客户ID获取用户ID"""
        # TODO: 实现数据库查询
        return None

    async def _get_user_id_from_subscription(self, subscription_id: str) -> Optional[str]:
        """从订阅ID获取用户ID"""
        # TODO: 实现数据库查询
        return None

    async def _update_user_quota_after_payment(
        self,
        user_id: str,
        amount: float,
        metadata: Dict[str, Any]
    ):
        """支付后更新用户配额"""
        if not self.quota_manager:
            return

        # 根据金额和元数据确定计划类型
        if amount >= 99:  # Enterprise
            plan_type = "enterprise"
        elif amount >= 29:  # Pro
            plan_type = "pro"
        else:
            plan_type = "free"

        await self.quota_manager.upgrade_user_plan(user_id, plan_type)

    async def _send_payment_failure_notification(
        self,
        user_id: Optional[str],
        payment_id: str,
        error_message: str
    ):
        """发送支付失败通知"""
        # TODO: 实现通知发送
        logger.warning(f"支付失败通知 - 用户: {user_id}, 支付: {payment_id}, 错误: {error_message}")

    async def _record_dispute(self, charge_id: str, amount: float, reason: str):
        """记录争议"""
        # TODO: 实现争议记录
        logger.warning(f"记录争议 - 收费: {charge_id}, 金额: {amount}, 原因: {reason}")

    async def _send_dispute_notification(self, charge_id: str, amount: float, reason: str):
        """发送争议通知"""
        # TODO: 实现争议通知
        logger.warning(f"争议通知 - 收费: {charge_id}, 金额: {amount}, 原因: {reason}")

    async def _record_refund(self, refund_id: str, sale_id: str, amount: float, reason: str):
        """记录退款"""
        # TODO: 实现退款记录
        logger.info(f"记录退款 - 退款: {refund_id}, 销售: {sale_id}, 金额: {amount}, 原因: {reason}")