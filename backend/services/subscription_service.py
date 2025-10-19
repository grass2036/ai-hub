"""
订阅管理服务 - Week 3 企业级功能增强
处理订阅创建、管理、计费等业务逻辑
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .mock_payment_service import mock_payment_service
from ..models.subscription import Subscription, Plan, Invoice, Payment
from ..models.organization import Organization

logger = logging.getLogger(__name__)

class SubscriptionService:
    """订阅管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.payment_service = mock_payment_service

    async def create_subscription(
        self,
        organization_id: str,
        plan_id: str,
        payment_method_id: str = None,
        trial_days: int = 0
    ) -> Dict[str, Any]:
        """创建新订阅"""
        try:
            # 验证组织存在
            organization = self.db.query(Organization).filter(
                Organization.id == organization_id
            ).first()

            if not organization:
                raise ValueError("Organization not found")

            # 验证套餐存在
            plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
            if not plan:
                raise ValueError("Plan not found")

            # 检查是否已有活跃订阅
            existing_subscription = self.db.query(Subscription).filter(
                and_(
                    Subscription.organization_id == organization_id,
                    Subscription.status.in_(['active', 'trialing'])
                )
            ).first()

            if existing_subscription:
                # 如果已有活跃订阅，进行升级/降级
                return await self._update_subscription_plan(
                    existing_subscription.id, plan_id
                )

            # 创建模拟订阅
            mock_subscription = await self.payment_service.create_subscription(
                plan_id=plan_id,
                organization_id=organization_id,
                payment_method_id=payment_method_id,
                trial_days=trial_days
            )

            # 计算订阅周期
            now = datetime.utcnow()
            if trial_days > 0:
                trial_start = now
                trial_end = now + timedelta(days=trial_days)
                current_period_start = trial_end
                current_period_end = trial_end + self._get_billing_period_delta(plan.billing_cycle)
            else:
                trial_start = None
                trial_end = None
                current_period_start = now
                current_period_end = now + self._get_billing_period_delta(plan.billing_cycle)

            # 创建订阅记录
            subscription = Subscription(
                organization_id=organization_id,
                plan_id=plan_id,
                status=mock_subscription["status"],
                current_period_start=current_period_start,
                current_period_end=current_period_end,
                trial_start=trial_start,
                trial_end=trial_end,
                payment_method="mock",
                mock_payment_id=mock_subscription["id"],
                metadata={"mock_customer_id": mock_subscription["customer"]}
            )

            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)

            # 创建首张发票
            await self._create_initial_invoice(subscription, plan, trial_days)

            logger.info(f"Created subscription {subscription.id} for organization {organization_id}")

            return {
                "subscription": self._serialize_subscription(subscription),
                "plan": self._serialize_plan(plan),
                "organization": {
                    "id": organization.id,
                    "name": organization.name
                }
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating subscription: {str(e)}")
            raise

    async def update_subscription(
        self,
        subscription_id: str,
        plan_id: str = None,
        cancel_at_period_end: bool = None
    ) -> Dict[str, Any]:
        """更新订阅"""
        try:
            subscription = self.db.query(Subscription).filter(
                Subscription.id == subscription_id
            ).first()

            if not subscription:
                raise ValueError("Subscription not found")

            updated_fields = {}

            if plan_id and plan_id != subscription.plan_id:
                # 升级/降级套餐
                new_plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
                if not new_plan:
                    raise ValueError("New plan not found")

                # 计算按比例退费/收费
                await self._handle_proration(subscription, new_plan)

                subscription.plan_id = plan_id
                updated_fields["plan_changed"] = True

            if cancel_at_period_end is not None:
                subscription.cancel_at_period_end = cancel_at_period_end
                updated_fields["cancel_at_period_end"] = cancel_at_period_end

            if updated_fields:
                subscription.updated_at = datetime.utcnow()
                self.db.commit()
                self.db.refresh(subscription)

                # 记录变更历史
                await self._record_subscription_change(
                    subscription_id,
                    "updated",
                    metadata=updated_fields
                )

            return self._serialize_subscription(subscription)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating subscription: {str(e)}")
            raise

    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True
    ) -> Dict[str, Any]:
        """取消订阅"""
        try:
            subscription = self.db.query(Subscription).filter(
                Subscription.id == subscription_id
            ).first()

            if not subscription:
                raise ValueError("Subscription not found")

            # 调用模拟支付服务取消订阅
            mock_cancellation = await self.payment_service.cancel_subscription(
                subscription_id=subscription.mock_payment_id,
                at_period_end=at_period_end
            )

            if at_period_end:
                subscription.cancel_at_period_end = True
                subscription.canceled_at = datetime.utcnow()
                status = "active"  # 仍然活跃直到计费期结束
            else:
                subscription.status = "canceled"
                subscription.canceled_at = datetime.utcnow()

            subscription.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(subscription)

            # 记录变更历史
            await self._record_subscription_change(
                subscription_id,
                "canceled",
                metadata={"at_period_end": at_period_end}
            )

            logger.info(f"Canceled subscription {subscription_id}, at_period_end: {at_period_end}")

            return self._serialize_subscription(subscription)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error canceling subscription: {str(e)}")
            raise

    async def reactivate_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """重新激活订阅"""
        try:
            subscription = self.db.query(Subscription).filter(
                Subscription.id == subscription_id
            ).first()

            if not subscription:
                raise ValueError("Subscription not found")

            if subscription.status not in ["canceled", "past_due"]:
                raise ValueError("Subscription cannot be reactivated")

            # 检查订阅是否已过期
            if subscription.current_period_end < datetime.utcnow():
                # 需要创建新的订阅周期
                subscription.current_period_start = datetime.utcnow()
                subscription.current_period_end = datetime.utcnow() + self._get_billing_period_delta(
                    subscription.plan.billing_cycle
                )

            subscription.status = "active"
            subscription.cancel_at_period_end = False
            subscription.canceled_at = None
            subscription.updated_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(subscription)

            # 记录变更历史
            await self._record_subscription_change(
                subscription_id,
                "reactivated"
            )

            return self._serialize_subscription(subscription)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error reactivating subscription: {str(e)}")
            raise

    async def get_subscription_details(self, subscription_id: str) -> Dict[str, Any]:
        """获取订阅详情"""
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()

        if not subscription:
            raise ValueError("Subscription not found")

        plan = self.db.query(Plan).filter(Plan.id == subscription.plan_id).first()
        organization = self.db.query(Organization).filter(
            Organization.id == subscription.organization_id
        ).first()

        # 获取最近的发票
        recent_invoices = self.db.query(Invoice).filter(
            Invoice.organization_id == subscription.organization_id
        ).order_by(Invoice.created_at.desc()).limit(5).all()

        return {
            "subscription": self._serialize_subscription(subscription),
            "plan": self._serialize_plan(plan) if plan else None,
            "organization": {
                "id": organization.id,
                "name": organization.name,
                "slug": organization.slug
            } if organization else None,
            "recent_invoices": [self._serialize_invoice(inv) for inv in recent_invoices]
        }

    def get_organization_subscriptions(self, organization_id: str) -> List[Dict[str, Any]]:
        """获取组织的所有订阅"""
        subscriptions = self.db.query(Subscription).filter(
            Subscription.organization_id == organization_id
        ).order_by(Subscription.created_at.desc()).all()

        result = []
        for subscription in subscriptions:
            plan = self.db.query(Plan).filter(Plan.id == subscription.plan_id).first()
            sub_data = self._serialize_subscription(subscription)
            sub_data["plan"] = self._serialize_plan(plan) if plan else None
            result.append(sub_data)

        return result

    async def check_subscription_status(self, organization_id: str) -> Dict[str, Any]:
        """检查组织订阅状态"""
        active_subscription = self.db.query(Subscription).filter(
            and_(
                Subscription.organization_id == organization_id,
                Subscription.status.in_(['active', 'trialing'])
            )
        ).first()

        if not active_subscription:
            return {
                "has_active_subscription": False,
                "status": "none",
                "plan": None,
                "expires_at": None
            }

        plan = self.db.query(Plan).filter(Plan.id == active_subscription.plan_id).first()

        return {
            "has_active_subscription": True,
            "status": active_subscription.status,
            "plan": self._serialize_plan(plan) if plan else None,
            "subscription": self._serialize_subscription(active_subscription),
            "expires_at": active_subscription.current_period_end.isoformat() if active_subscription.current_period_end else None,
            "is_trial": active_subscription.status == "trialing",
            "trial_end": active_subscription.trial_end.isoformat() if active_subscription.trial_end else None
        }

    # 私有方法
    def _get_billing_period_delta(self, billing_cycle: str) -> timedelta:
        """获取计费周期时间差"""
        if billing_cycle == "monthly":
            return timedelta(days=30)
        elif billing_cycle == "yearly":
            return timedelta(days=365)
        else:
            return timedelta(days=30)  # 默认月付

    def _serialize_subscription(self, subscription: Subscription) -> Dict[str, Any]:
        """序列化订阅对象"""
        return {
            "id": subscription.id,
            "organization_id": subscription.organization_id,
            "plan_id": subscription.plan_id,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "trial_start": subscription.trial_start.isoformat() if subscription.trial_start else None,
            "trial_end": subscription.trial_end.isoformat() if subscription.trial_end else None,
            "canceled_at": subscription.canceled_at.isoformat() if subscription.canceled_at else None,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "payment_method": subscription.payment_method,
            "metadata": subscription.metadata or {},
            "created_at": subscription.created_at.isoformat() if subscription.created_at else None,
            "updated_at": subscription.updated_at.isoformat() if subscription.updated_at else None
        }

    def _serialize_plan(self, plan: Plan) -> Dict[str, Any]:
        """序列化套餐对象"""
        return {
            "id": plan.id,
            "name": plan.name,
            "slug": plan.slug,
            "description": plan.description,
            "price": float(plan.price),
            "currency": plan.currency,
            "billing_cycle": plan.billing_cycle,
            "features": plan.features or {},
            "api_quota": plan.api_quota,
            "rate_limit": plan.rate_limit,
            "max_teams": plan.max_teams,
            "max_users": plan.max_users,
            "is_active": plan.is_active,
            "is_popular": plan.is_popular,
            "sort_order": plan.sort_order
        }

    def _serialize_invoice(self, invoice: Invoice) -> Dict[str, Any]:
        """序列化发票对象"""
        return {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "status": invoice.status,
            "currency": invoice.currency,
            "subtotal": float(invoice.subtotal),
            "tax_amount": float(invoice.tax_amount),
            "total_amount": float(invoice.total_amount),
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
            "description": invoice.description,
            "pdf_url": invoice.pdf_url,
            "created_at": invoice.created_at.isoformat() if invoice.created_at else None
        }

    async def _create_initial_invoice(self, subscription: Subscription, plan: Plan, trial_days: int):
        """创建初始发票"""
        if trial_days > 0:
            # 试用期间不创建发票
            return

        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

        invoice = Invoice(
            organization_id=subscription.organization_id,
            subscription_id=subscription.id,
            invoice_number=invoice_number,
            status="pending",
            currency=plan.currency,
            subtotal=plan.price,
            tax_amount=Decimal("0.00"),  # 简化税处理
            total_amount=plan.price,
            due_date=datetime.utcnow() + timedelta(days=30),
            description=f"{plan.name} - {plan.billing_cycle} subscription"
        )

        self.db.add(invoice)
        self.db.commit()

    async def _record_subscription_change(
        self,
        subscription_id: str,
        change_type: str,
        old_plan_id: str = None,
        new_plan_id: str = None,
        metadata: Dict = None
    ):
        """记录订阅变更历史"""
        try:
            # 这里可以创建变更记录表，目前简化处理
            logger.info(f"Subscription {subscription_id} {change_type}: {metadata or {}}")
        except Exception as e:
            logger.error(f"Error recording subscription change: {str(e)}")

    async def _update_subscription_plan(self, subscription_id: str, new_plan_id: str) -> Dict[str, Any]:
        """更新订阅套餐"""
        return await self.update_subscription(subscription_id, plan_id=new_plan_id)

    async def _handle_proration(self, subscription: Subscription, new_plan: Plan):
        """处理按比例退费/收费"""
        # 简化处理，实际场景中需要计算按比例退费
        logger.info(f"Handling proration for subscription {subscription.id} to plan {new_plan.id}")

# 全局订阅服务函数
def get_subscription_service(db: Session) -> SubscriptionService:
    return SubscriptionService(db)