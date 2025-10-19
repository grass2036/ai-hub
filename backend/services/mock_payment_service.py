"""
模拟支付服务 - Week 3 企业级功能增强
提供完整的支付、订阅、计费功能，无需外部支付账户
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class MockPaymentService:
    """模拟支付服务，提供完整的支付功能"""

    def __init__(self):
        self.test_cards = {
            "success": "4242424242424242",
            "failure": "4000000000000002",
            "insufficient": "5000000000000001",
            "expired": "4000000000000069",
            "cvc_check": "4000000000000127"
        }

    async def create_payment_intent(
        self,
        amount: float,
        currency: str = "USD",
        organization_id: str = None,
        description: str = None,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """创建支付意图"""
        payment_id = f"pay_mock_{uuid.uuid4().hex[:12]}"

        return {
            "id": payment_id,
            "object": "payment_intent",
            "amount": int(amount * 100),  # 转换为分
            "currency": currency.lower(),
            "status": "requires_payment_method",
            "client_secret": f"pi_mock_{uuid.uuid4().hex[:24]}",
            "payment_method": None,
            "description": description,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "organization_id": organization_id,
            "mock": True
        }

    async def confirm_payment(
        self,
        payment_intent_id: str,
        payment_method_id: str = None,
        card_number: str = None
    ) -> Dict[str, Any]:
        """确认支付"""
        # 模拟支付处理时间
        import asyncio
        await asyncio.sleep(0.5)

        # 检查是否为失败卡号
        if card_number == self.test_cards["failure"]:
            return {
                "id": payment_intent_id,
                "status": "payment_failed",
                "error": {"message": "Your card was declined."},
                "payment_intent": {"status": "requires_payment_method"}
            }

        elif card_number == self.test_cards["insufficient"]:
            return {
                "id": payment_intent_id,
                "status": "payment_failed",
                "error": {"message": "Insufficient funds."},
                "payment_intent": {"status": "requires_payment_method"}
            }

        elif card_number == self.test_cards["expired"]:
            return {
                "id": payment_intent_id,
                "status": "payment_failed",
                "error": {"message": "Your card has expired."},
                "payment_intent": {"status": "requires_payment_method"}
            }

        # 默认成功支付
        return {
            "id": payment_intent_id,
            "status": "succeeded",
            "payment_intent": {
                "id": payment_intent_id,
                "status": "succeeded",
                "amount_received": int(payment_intent_id.split("_")[2] or "10000")
            },
            "charge": f"ch_mock_{uuid.uuid4().hex[:12]}",
            "paid_at": datetime.utcnow().isoformat()
        }

    async def create_subscription(
        self,
        plan_id: str,
        organization_id: str,
        payment_method_id: str = None,
        trial_days: int = 0
    ) -> Dict[str, Any]:
        """创建订阅"""
        subscription_id = f"sub_mock_{uuid.uuid4().hex[:12]}"
        customer_id = f"cus_mock_{uuid.uuid4().hex[:12]}"

        now = datetime.utcnow()
        trial_end = now + timedelta(days=trial_days) if trial_days > 0 else None
        period_end = now + timedelta(days=30)  # 默认月付

        subscription = {
            "id": subscription_id,
            "object": "subscription",
            "customer": customer_id,
            "status": "trialing" if trial_days > 0 else "active",
            "current_period_start": now.isoformat(),
            "current_period_end": period_end.isoformat(),
            "trial_start": trial_end.isoformat() if trial_end else None,
            "trial_end": trial_end.isoformat() if trial_end else None,
            "plan": {"id": plan_id},
            "items": [{
                "id": f"si_mock_{uuid.uuid4().hex[:12]}",
                "object": "subscription_item",
                "price": {
                    "id": f"price_mock_{uuid.uuid4().hex[:12]}",
                    "currency": "usd",
                    "unit_amount": 2900,  # $29.00
                    "recurring": {"interval": "month"}
                },
                "quantity": 1
            }],
            "created_at": now.isoformat(),
            "organization_id": organization_id,
            "payment_method": payment_method_id,
            "mock": True
        }

        return subscription

    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = False
    ) -> Dict[str, Any]:
        """取消订阅"""
        # 模拟处理时间
        import asyncio
        await asyncio.sleep(0.3)

        now = datetime.utcnow()

        if at_period_end:
            # 在当前计费期结束时取消
            return {
                "id": subscription_id,
                "status": "active",
                "cancel_at_period_end": True,
                "canceled_at": now.isoformat(),
                "ended_at": None
            }
        else:
            # 立即取消
            return {
                "id": subscription_id,
                "status": "canceled",
                "cancel_at_period_end": False,
                "canceled_at": now.isoformat(),
                "ended_at": now.isoformat()
            }

    async def update_subscription(
        self,
        subscription_id: str,
        plan_id: str = None,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """更新订阅"""
        import asyncio
        await asyncio.sleep(0.3)

        now = datetime.utcnow()
        new_period_end = now + timedelta(days=30)

        return {
            "id": subscription_id,
            "status": "active",
            "current_period_start": now.isoformat(),
            "current_period_end": new_period_end.isoformat(),
            "plan": {"id": plan_id} if plan_id else None,
            "metadata": metadata or {},
            "updated_at": now.isoformat()
        }

    async def create_invoice(
        self,
        organization_id: str,
        subscription_id: str = None,
        amount: float = None,
        description: str = None,
        due_days: int = 30
    ) -> Dict[str, Any]:
        """创建发票"""
        invoice_id = f"in_mock_{uuid.uuid4().hex[:12]}"
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

        now = datetime.utcnow()
        due_date = now + timedelta(days=due_days)

        return {
            "id": invoice_id,
            "object": "invoice",
            "number": invoice_number,
            "status": "draft",
            "currency": "usd",
            "amount_due": int((amount or 29.00) * 100),
            "amount_paid": 0,
            "amount_remaining": int((amount or 29.00) * 100),
            "due_date": int(due_date.timestamp()),
            "created_at": int(now.timestamp()),
            "description": description,
            "subscription": subscription_id,
            "organization_id": organization_id,
            "lines": [{
                "id": f"il_mock_{uuid.uuid4().hex[:12]}",
                "object": "line_item",
                "amount": int((amount or 29.00) * 100),
                "currency": "usd",
                "description": description or "Subscription payment",
                "quantity": 1
            }],
            "mock": True
        }

    async def finalize_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """最终确定发票"""
        import asyncio
        await asyncio.sleep(0.2)

        return {
            "id": invoice_id,
            "status": "open",
            "finalized_at": datetime.utcnow().isoformat()
        }

    async def pay_invoice(
        self,
        invoice_id: str,
        payment_method_id: str = None
    ) -> Dict[str, Any]:
        """支付发票"""
        import asyncio
        await asyncio.sleep(0.5)

        payment_id = f"pay_mock_{uuid.uuid4().hex[:12]}"

        return {
            "id": invoice_id,
            "status": "paid",
            "paid_at": datetime.utcnow().isoformat(),
            "charge": f"ch_mock_{uuid.uuid4().hex[:12]}",
            "payment_intent": payment_id
        }

    async def create_refund(
        self,
        payment_id: str,
        amount: float = None,
        reason: str = None
    ) -> Dict[str, Any]:
        """创建退款"""
        import asyncio
        await asyncio.sleep(0.3)

        refund_id = f"re_mock_{uuid.uuid4().hex[:12]}"

        return {
            "id": refund_id,
            "object": "refund",
            "amount": int((amount or 29.00) * 100),
            "currency": "usd",
            "payment_intent": payment_id,
            "reason": reason or "requested_by_customer",
            "status": "succeeded",
            "created_at": int(datetime.utcnow().timestamp()),
            "receipt_number": f"RCPT-{uuid.uuid4().hex[:8].upper()}",
            "mock": True
        }

    async def get_payment_methods(self, customer_id: str) -> List[Dict[str, Any]]:
        """获取支付方式"""
        return [
            {
                "id": "pm_mock_visa",
                "object": "payment_method",
                "type": "card",
                "card": {
                    "brand": "visa",
                    "last4": "4242",
                    "expiry_month": 12,
                    "expiry_year": 2025,
                    "fingerprint": f"fp_mock_{uuid.uuid4().hex[:16]}"
                },
                "billing_details": {
                    "email": "test@example.com",
                    "name": "Test User"
                },
                "created_at": int(datetime.utcnow().timestamp()),
                "customer": customer_id
            }
        ]

    def get_test_cards(self) -> Dict[str, str]:
        """获取测试卡号"""
        return {
            "success": self.test_cards["success"],
            "failure": self.test_cards["failure"],
            "insufficient": self.test_cards["insufficient"],
            "expired": self.test_cards["expired"],
            "cvc_check": self.test_cards["cvc_check"]
        }

    async def calculate_usage_cost(
        self,
        api_calls: int,
        tokens_used: int,
        plan_id: str
    ) -> Dict[str, Any]:
        """计算使用成本"""
        # 模拟不同套餐的计费规则
        plan_costs = {
            "free": {"api_call_cost": 0.001, "token_cost": 0.0001},
            "pro": {"api_call_cost": 0.0005, "token_cost": 0.00005},
            "enterprise": {"api_call_cost": 0.0002, "token_cost": 0.00002}
        }

        plan_config = plan_costs.get(plan_id, plan_costs["free"])

        api_cost = api_calls * plan_config["api_call_cost"]
        token_cost = tokens_used * plan_config["token_cost"]
        total_cost = api_cost + token_cost

        return {
            "api_calls": api_calls,
            "tokens_used": tokens_used,
            "api_cost": round(api_cost, 4),
            "token_cost": round(token_cost, 4),
            "total_cost": round(total_cost, 4),
            "currency": "USD",
            "calculated_at": datetime.utcnow().isoformat()
        }

# 全局支付服务实例
mock_payment_service = MockPaymentService()