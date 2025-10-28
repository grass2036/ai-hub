"""
PayPal支付处理器

提供PayPal支付网关的集成处理。
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import logging
import json
import asyncio
from base64 import b64encode

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from .payment_types import (
    PaymentProvider, PaymentStatus, PaymentType, Currency,
    PaymentMethod, PaymentIntent, PaymentResult, Refund,
    Subscription, PaymentError
)

logger = logging.getLogger(__name__)


class PayPalProcessor:
    """PayPal支付处理器"""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        sandbox: bool = True,
        webhook_url: Optional[str] = None
    ):
        """
        初始化PayPal处理器

        Args:
            client_id: PayPal客户端ID
            client_secret: PayPal客户端密钥
            sandbox: 是否使用沙盒环境
            webhook_url: Webhook URL
        """
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp library not available. Install with: pip install aiohttp")

        self.client_id = client_id
        self.client_secret = client_secret
        self.sandbox = sandbox
        self.webhook_url = webhook_url

        # PayPal API URLs
        if sandbox:
            self.base_url = "https://api-m.sandbox.paypal.com"
        else:
            self.base_url = "https://api-m.paypal.com"

        # 支持的货币
        self.supported_currencies = {
            Currency.USD: "USD",
            Currency.EUR: "EUR",
            Currency.GBP: "GBP",
            Currency.JPY: "JPY",
            Currency.CNY: "CNY"
        }

        # OAuth2 token缓存
        self._access_token = None
        self._token_expires_at = None

    async def _get_access_token(self) -> str:
        """获取访问令牌"""
        # 检查token是否仍然有效
        if (
            self._access_token and
            self._token_expires_at and
            datetime.now(timezone.utc) < self._token_expires_at
        ):
            return self._access_token

        # 获取新token
        try:
            auth_string = b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/oauth2/token",
                    headers={
                        "Authorization": f"Basic {auth_string}",
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    data="grant_type=client_credentials"
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise PaymentError(
                            f"PayPal token获取失败: {error_text}",
                            provider="paypal"
                        )

                    data = await response.json()
                    self._access_token = data["access_token"]
                    # token有效期减少5分钟缓冲
                    expires_in = data.get("expires_in", 3600) - 300
                    self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

                    logger.info("PayPal访问令牌获取成功")
                    return self._access_token

        except Exception as e:
            logger.error(f"PayPal访问令牌获取失败: {e}")
            raise PaymentError(f"PayPal token获取失败: {e}", provider="paypal")

    async def create_payment_intent(
        self,
        amount: float,
        currency: Currency,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> PaymentResult:
        """
        创建支付意图

        Args:
            amount: 金额
            currency: 货币
            return_url: 成功返回URL
            cancel_url: 取消返回URL
            description: 描述
            metadata: 元数据

        Returns:
            支付结果
        """
        try:
            access_token = await self._get_access_token()

            # 构建支付数据
            payment_data = {
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "transactions": [{
                    "amount": {
                        "total": f"{amount:.2f}",
                        "currency": self.supported_currencies[currency]
                    },
                    "description": description or "AI Hub Platform Payment"
                }],
                "redirect_urls": {
                    "return_url": return_url or "https://aihub.com/payment/success",
                    "cancel_url": cancel_url or "https://aihub.com/payment/cancel"
                }
            }

            if metadata:
                payment_data["transactions"][0]["custom"] = json.dumps(metadata)

            # 创建支付
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/payments/payment",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json=payment_data
                ) as response:
                    if response.status not in [200, 201]:
                        error_text = await response.text()
                        raise PaymentError(
                            f"PayPal支付创建失败: {error_text}",
                            provider="paypal"
                        )

                    data = await response.json()

                    # 获取批准URL
                    approval_url = None
                    for link in data.get("links", []):
                        if link.get("rel") == "approval_url":
                            approval_url = link.get("href")
                            break

                    result = PaymentResult(
                        success=True,
                        payment_intent_id=data["id"],
                        provider_transaction_id=data["id"],
                        status=PaymentStatus.PENDING,
                        amount=amount,
                        currency=currency,
                        gateway_response=data,
                        metadata={
                            "approval_url": approval_url,
                            "payment_id": data["id"]
                        }
                    )

                    logger.info(f"PayPal支付创建成功: {data['id']}")
                    return result

        except Exception as e:
            logger.error(f"PayPal支付创建失败: {e}")
            return PaymentResult(
                success=False,
                failure_reason=str(e),
                gateway_response={"error": str(e)}
            )

    async def execute_payment(
        self,
        payment_id: str,
        payer_id: str
    ) -> PaymentResult:
        """
        执行支付

        Args:
            payment_id: 支付ID
            payer_id: 付款人ID

        Returns:
            支付结果
        """
        try:
            access_token = await self._get_access_token()

            execute_data = {
                "payer_id": payer_id
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/payments/payment/{payment_id}/execute",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json=execute_data
                ) as response:
                    if response.status not in [200, 201]:
                        error_text = await response.text()
                        raise PaymentError(
                            f"PayPal支付执行失败: {error_text}",
                            provider="paypal"
                        )

                    data = await response.json()

                    # 获取交易状态
                    transactions = data.get("transactions", [])
                    if transactions and transactions[0].get("related_resources"):
                        sale = transactions[0]["related_resources"][0]["sale"]
                        transaction_id = sale["id"]
                        sale_state = sale["state"]
                    else:
                        transaction_id = None
                        sale_state = "pending"

                    # 转换状态
                    if sale_state == "completed":
                        status = PaymentStatus.COMPLETED
                    elif sale_state == "pending":
                        status = PaymentStatus.PROCESSING
                    elif sale_state in ["denied", "failed"]:
                        status = PaymentStatus.FAILED
                    else:
                        status = PaymentStatus.PENDING

                    result = PaymentResult(
                        success=True,
                        payment_intent_id=payment_id,
                        provider_transaction_id=transaction_id,
                        status=status,
                        gateway_response=data
                    )

                    logger.info(f"PayPal支付执行成功: {payment_id}")
                    return result

        except Exception as e:
            logger.error(f"PayPal支付执行失败: {e}")
            return PaymentResult(
                success=False,
                failure_reason=str(e),
                gateway_response={"error": str(e)}
            )

    async def create_subscription(
        self,
        plan_id: str,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Subscription:
        """
        创建订阅

        Args:
            plan_id: PayPal计划ID
            return_url: 成功返回URL
            cancel_url: 取消返回URL
            metadata: 元数据

        Returns:
            订阅信息
        """
        try:
            access_token = await self._get_access_token()

            # 构建订阅数据
            subscription_data = {
                "plan_id": plan_id,
                "application_context": {
                    "brand_name": "AI Hub Platform",
                    "locale": "en-US",
                    "shipping_preference": "NO_SHIPPING",
                    "user_action": "SUBSCRIBE_NOW",
                    "payment_method": {
                        "payer_selected": "PAYPAL",
                        "payee_preferred": "IMMEDIATE_PAYMENT_REQUIRED"
                    },
                    "return_url": return_url or "https://aihub.com/subscription/success",
                    "cancel_url": cancel_url or "https://aihub.com/subscription/cancel"
                }
            }

            if metadata:
                subscription_data["custom_id"] = json.dumps(metadata)

            # 创建订阅
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/billing/subscriptions",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json=subscription_data
                ) as response:
                    if response.status not in [200, 201]:
                        error_text = await response.text()
                        raise PaymentError(
                            f"PayPal订阅创建失败: {error_text}",
                            provider="paypal"
                        )

                    data = await response.json()

                    # 获取批准URL
                    approval_url = None
                    for link in data.get("links", []):
                        if link.get("rel") == "approve":
                            approval_url = link.get("href")
                            break

                    result = Subscription(
                        id=data["id"],
                        user_id="",  # 需要从数据库映射
                        plan_id=plan_id,
                        price_id=plan_id,
                        provider=PaymentProvider.PAYPAL,
                        provider_subscription_id=data["id"],
                        status=data["status"],
                        current_period_start=datetime.now(timezone.utc),
                        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
                        cancel_at_period_end=False,
                        metadata={
                            "approval_url": approval_url,
                            "subscription_id": data["id"]
                        }
                    )

                    logger.info(f"PayPal订阅创建成功: {data['id']}")
                    return result

        except Exception as e:
            logger.error(f"PayPal订阅创建失败: {e}")
            raise PaymentError(f"PayPal订阅创建失败: {e}", provider="paypal")

    async def cancel_subscription(
        self,
        subscription_id: str,
        reason: str = "Customer requested cancellation"
    ) -> Subscription:
        """
        取消订阅

        Args:
            subscription_id: 订阅ID
            reason: 取消原因

        Returns:
            取消后的订阅信息
        """
        try:
            access_token = await self._get_access_token()

            cancel_data = {
                "reason": reason
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/billing/subscriptions/{subscription_id}/cancel",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json=cancel_data
                ) as response:
                    if response.status != 204:
                        error_text = await response.text()
                        raise PaymentError(
                            f"PayPal订阅取消失败: {error_text}",
                            provider="paypal"
                        )

                    result = Subscription(
                        id=subscription_id,
                        user_id="",  # 需要从数据库查询
                        plan_id="",  # 需要从数据库查询
                        price_id="",
                        provider=PaymentProvider.PAYPAL,
                        provider_subscription_id=subscription_id,
                        status="CANCELLED",
                        current_period_start=datetime.now(timezone.utc),
                        current_period_end=datetime.now(timezone.utc),
                        cancel_at_period_end=True,
                        metadata={"cancellation_reason": reason}
                    )

                    logger.info(f"PayPal订阅取消成功: {subscription_id}")
                    return result

        except Exception as e:
            logger.error(f"PayPal订阅取消失败: {e}")
            raise PaymentError(f"PayPal订阅取消失败: {e}", provider="paypal")

    async def create_refund(
        self,
        sale_id: str,
        amount: Optional[float] = None,
        reason: str = "Requested by customer"
    ) -> Refund:
        """
        创建退款

        Args:
            sale_id: 销售ID
            amount: 退款金额（None表示全额退款）
            reason: 退款原因

        Returns:
            退款信息
        """
        try:
            access_token = await self._get_access_token()

            # 构建退款数据
            refund_data = {}
            if amount:
                refund_data["amount"] = {
                    "total": f"{amount:.2f}",
                    "currency": "USD"  # 默认USD，实际应该从sale中获取
                }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/payments/sale/{sale_id}/refund",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json=refund_data
                ) as response:
                    if response.status not in [200, 201]:
                        error_text = await response.text()
                        raise PaymentError(
                            f"PayPal退款创建失败: {error_text}",
                            provider="paypal"
                        )

                    data = await response.json()

                    # 转换状态
                    state = data.get("state", "pending")
                    if state == "completed":
                        status = PaymentStatus.COMPLETED
                    elif state == "pending":
                        status = PaymentStatus.PROCESSING
                    else:
                        status = PaymentStatus.FAILED

                    result = Refund(
                        id=data["id"],
                        payment_intent_id=sale_id,
                        amount=float(data.get("amount", {}).get("total", 0)),
                        reason=reason,
                        status=status,
                        provider_refund_id=data["id"],
                        metadata=data.get("links", []),
                        created_at=datetime.now(timezone.utc)
                    )

                    logger.info(f"PayPal退款创建成功: {data['id']}")
                    return result

        except Exception as e:
            logger.error(f"PayPal退款创建失败: {e}")
            raise PaymentError(f"PayPal退款创建失败: {e}", provider="paypal")

    async def handle_webhook(self, payload: bytes, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        处理PayPal webhook

        Args:
            payload: Webhook载荷
            headers: HTTP头

        Returns:
            处理结果
        """
        try:
            # 解析webhook数据
            webhook_data = json.loads(payload.decode('utf-8'))

            # 验证webhook签名（生产环境必须）
            if not self.sandbox and self.webhook_url:
                await self._verify_webhook_signature(payload, headers)

            # 处理webhook事件
            result = {
                "event_type": webhook_data.get("event_type"),
                "resource_type": webhook_data.get("resource_type"),
                "summary": webhook_data.get("summary"),
                "resource": webhook_data.get("resource", {}),
                "create_time": webhook_data.get("create_time"),
                "id": webhook_data.get("id")
            }

            logger.info(f"PayPal webhook处理成功: {webhook_data.get('event_type')}")
            return result

        except Exception as e:
            logger.error(f"PayPal webhook处理失败: {e}")
            raise PaymentError(f"Webhook处理失败: {e}", provider="paypal")

    async def _verify_webhook_signature(
        self,
        payload: bytes,
        headers: Dict[str, str]
    ) -> bool:
        """验证webhook签名"""
        try:
            access_token = await self._get_access_token()

            # 获取PayPal签名头
            auth_algo = headers.get("PAYPAL-AUTH-ALGO")
            transmission_id = headers.get("PAYPAL-TRANSMISSION-ID")
            cert_id = headers.get("PAYPAL-CERT-ID")
            transmission_sig = headers.get("PAYPAL-TRANSMISSION-SIG")
            transmission_time = headers.get("PAYPAL-TRANSMISSION-TIME")

            if not all([auth_algo, transmission_id, cert_id, transmission_sig, transmission_time]):
                raise PaymentError("PayPal webhook签名验证失败: 缺少必要的头信息", provider="paypal")

            verification_data = {
                "cert_id": cert_id,
                "transmission_id": transmission_id,
                "transmission_sig": transmission_sig,
                "transmission_time": transmission_time,
                "webhook_id": self.webhook_url,  # 实际应该是webhook ID
                "webhook_event": json.loads(payload.decode('utf-8'))
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/notifications/verify-webhook-signature",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json=verification_data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise PaymentError(
                            f"PayPal webhook签名验证失败: {error_text}",
                            provider="paypal"
                        )

                    data = await response.json()
                    return data.get("verification_status") == "SUCCESS"

        except Exception as e:
            logger.error(f"PayPal webhook签名验证失败: {e}")
            return False

    async def get_payment_details(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        获取支付详情

        Args:
            payment_id: 支付ID

        Returns:
            支付详情或None
        """
        try:
            access_token = await self._get_access_token()

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/v1/payments/payment/{payment_id}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                ) as response:
                    if response.status != 200:
                        return None

                    return await response.json()

        except Exception as e:
            logger.error(f"PayPal支付详情获取失败: {e}")
            return None

    async def get_subscription_details(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """
        获取订阅详情

        Args:
            subscription_id: 订阅ID

        Returns:
            订阅详情或None
        """
        try:
            access_token = await self._get_access_token()

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/v1/billing/subscriptions/{subscription_id}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                ) as response:
                    if response.status != 200:
                        return None

                    return await response.json()

        except Exception as e:
            logger.error(f"PayPal订阅详情获取失败: {e}")
            return None