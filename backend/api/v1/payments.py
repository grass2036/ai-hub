"""
支付系统API - Week 3 企业级功能增强
提供支付、订阅、发票等完整的RESTful API接口
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import logging

from ..core.auth import get_current_user, get_current_organization
from ..core.permissions import require_permission
from ..services.mock_payment_service import mock_payment_service
from ..services.subscription_service import get_subscription_service
from ..models.subscription import Subscription, Plan, Invoice, Payment
from ..models.organization import Organization
from ..database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])

# Pydantic模型
class PaymentIntentRequest(BaseModel):
    amount: float = Field(..., gt=0, description="支付金额")
    currency: str = Field(default="USD", description="货币类型")
    description: Optional[str] = Field(None, description="支付描述")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class PaymentConfirmRequest(BaseModel):
    payment_intent_id: str = Field(..., description="支付意图ID")
    card_number: str = Field(..., description="信用卡号")
    expiry_month: int = Field(..., ge=1, le=12, description="到期月份")
    expiry_year: int = Field(..., ge=2024, le=2050, description="到期年份")
    cvc: str = Field(..., description="安全码")
    cardholder_name: str = Field(..., description="持卡人姓名")

class SubscriptionCreateRequest(BaseModel):
    plan_id: str = Field(..., description="套餐ID")
    payment_method_id: Optional[str] = Field(None, description="支付方式ID")
    trial_days: int = Field(default=0, ge=0, le=90, description="试用天数")

class SubscriptionUpdateRequest(BaseModel):
    plan_id: Optional[str] = Field(None, description="新套餐ID")
    cancel_at_period_end: Optional[bool] = Field(None, description="在计费期结束时取消")

class PaymentMethod(BaseModel):
    card_number: str = Field(..., description="信用卡号")
    expiry_month: int = Field(..., ge=1, le=12, description="到期月份")
    expiry_year: int = Field(..., ge=2024, le=2050, description="到期年份")
    cvc: str = Field(..., description="安全码")
    cardholder_name: str = Field(..., description="持卡人姓名")

# 支付相关API
@router.post("/intents", summary="创建支付意图")
async def create_payment_intent(
    request: PaymentIntentRequest,
    current_user: dict = Depends(get_current_user),
    current_org: dict = Depends(get_current_organization),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("billing:edit"))
):
    """创建支付意图"""
    try:
        payment_intent = await mock_payment_service.create_payment_intent(
            amount=request.amount,
            currency=request.currency,
            organization_id=current_org["id"],
            description=request.description,
            metadata=request.metadata
        )

        return {
            "success": True,
            "data": payment_intent
        }

    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment intent: {str(e)}"
        )

@router.post("/confirm", summary="确认支付")
async def confirm_payment(
    request: PaymentConfirmRequest,
    current_user: dict = Depends(get_current_user),
    current_org: dict = Depends(get_current_organization),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("billing:edit"))
):
    """确认支付"""
    try:
        # 验证信用卡号格式
        if len(request.card_number) not in [16, 15]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid card number"
            )

        # 确认支付
        payment_result = await mock_payment_service.confirm_payment(
            payment_intent_id=request.payment_intent_id,
            card_number=request.card_number
        )

        if payment_result["status"] == "succeeded":
            # 创建支付记录
            payment = Payment(
                organization_id=current_org["id"],
                payment_id=payment_result["charge"],
                amount=Decimal(request.amount),
                currency=request.currency,
                status="succeeded",
                payment_method="mock",
                description=request.description,
                metadata={"card_last4": request.card_number[-4:]}
            )

            db.add(payment)
            db.commit()

        return {
            "success": True,
            "data": payment_result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming payment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm payment: {str(e)}"
        )

@router.get("/test-cards", summary="获取测试卡号")
async def get_test_cards(
    _: None = Depends(get_current_user)
):
    """获取可用的测试卡号列表"""
    try:
        test_cards = mock_payment_service.get_test_cards()
        return {
            "success": True,
            "data": {
                "cards": test_cards,
                "description": "Use these card numbers to test different payment scenarios",
                "note": "For expiry date, use any future date. For CVC, use any 3 digits."
            }
        }
    except Exception as e:
        logger.error(f"Error getting test cards: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get test cards: {str(e)}"
        )

# 订阅相关API
@router.get("/plans", summary="获取可用套餐")
async def get_plans(
    active_only: bool = Query(True, description="仅获取激活的套餐"),
    _: None = Depends(get_current_user)
):
    """获取所有可用的订阅套餐"""
    try:
        plans = mock_payment_service.get_plans()

        if active_only:
            plans = [plan for plan in plans if plan.get("is_active", True)]

        return {
            "success": True,
            "data": {
                "plans": plans,
                "count": len(plans)
            }
        }
    except Exception as e:
        logger.error(f"Error getting plans: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get plans: {str(e)}"
        )

@router.post("/subscriptions", summary="创建订阅")
async def create_subscription(
    request: SubscriptionCreateRequest,
    current_user: dict = Depends(get_current_user),
    current_org: dict = Depends(get_current_organization),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("billing:edit"))
):
    """创建新订阅"""
    try:
        subscription_service = get_subscription_service(db)

        result = await subscription_service.create_subscription(
            organization_id=current_org["id"],
            plan_id=request.plan_id,
            payment_method_id=request.payment_method_id,
            trial_days=request.trial_days
        )

        return {
            "success": True,
            "message": "Subscription created successfully",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription: {str(e)}"
        )

@router.get("/subscriptions", summary="获取订阅列表")
async def get_subscriptions(
    current_user: dict = Depends(get_current_user),
    current_org: dict = Depends(get_current_organization),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("billing:view"))
):
    """获取组织的订阅列表"""
    try:
        subscription_service = get_subscription_service(db)
        subscriptions = subscription_service.get_organization_subscriptions(current_org["id"])

        return {
            "success": True,
            "data": {
                "subscriptions": subscriptions,
                "count": len(subscriptions)
            }
        }

    except Exception as e:
        logger.error(f"Error getting subscriptions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscriptions: {str(e)}"
        )

@router.get("/subscriptions/{subscription_id}", summary="获取订阅详情")
async def get_subscription_details(
    subscription_id: str,
    current_user: dict = Depends(get_current_user),
    current_org: dict = Depends(get_current_organization),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("billing:view"))
):
    """获取订阅详情"""
    try:
        subscription_service = get_subscription_service(db)

        # 验证订阅属于当前组织
        subscription = db.query(Subscription).filter(
            Subscription.id == subscription_id,
            Subscription.organization_id == current_org["id"]
        ).first()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        details = await subscription_service.get_subscription_details(subscription_id)

        return {
            "success": True,
            "data": details
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscription details: {str(e)}"
        )

@router.put("/subscriptions/{subscription_id}", summary="更新订阅")
async def update_subscription(
    subscription_id: str,
    request: SubscriptionUpdateRequest,
    current_user: dict = Depends(get_current_user),
    current_org: dict = Depends(get_current_organization),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("billing:edit"))
):
    """更新订阅（升级/降级套餐、取消设置等）"""
    try:
        # 验证订阅属于当前组织
        subscription = db.query(Subscription).filter(
            Subscription.id == subscription_id,
            Subscription.organization_id == current_org["id"]
        ).first()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        subscription_service = get_subscription_service(db)

        result = await subscription_service.update_subscription(
            subscription_id=subscription_id,
            plan_id=request.plan_id,
            cancel_at_period_end=request.cancel_at_period_end
        )

        return {
            "success": True,
            "message": "Subscription updated successfully",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update subscription: {str(e)}"
        )

@router.post("/subscriptions/{subscription_id}/cancel", summary="取消订阅")
async def cancel_subscription(
    subscription_id: str,
    at_period_end: bool = Query(True, description="在计费期结束时取消"),
    current_user: dict = Depends(get_current_user),
    current_org: dict = Depends(get_current_organization),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("billing:edit"))
):
    """取消订阅"""
    try:
        # 验证订阅属于当前组织
        subscription = db.query(Subscription).filter(
            Subscription.id == subscription_id,
            Subscription.organization_id == current_org["id"]
        ).first()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        subscription_service = get_subscription_service(db)

        result = await subscription_service.cancel_subscription(
            subscription_id=subscription_id,
            at_period_end=at_period_end
        )

        return {
            "success": True,
            "message": "Subscription canceled successfully",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel subscription: {str(e)}"
        )

@router.post("/subscriptions/{subscription_id}/reactivate", summary="重新激活订阅")
async def reactivate_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user),
    current_org: dict = Depends(get_current_organization),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("billing:edit"))
):
    """重新激活订阅"""
    try:
        # 验证订阅属于当前组织
        subscription = db.query(Subscription).filter(
            Subscription.id == subscription_id,
            Subscription.organization_id == current_org["id"]
        ).first()

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )

        subscription_service = get_subscription_service(db)

        result = await subscription_service.reactivate_subscription(subscription_id)

        return {
            "success": True,
            "message": "Subscription reactivated successfully",
            "data": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reactivating subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reactivate subscription: {str(e)}"
        )

@router.get("/subscription-status", summary="检查订阅状态")
async def check_subscription_status(
    current_user: dict = Depends(get_current_user),
    current_org: dict = Depends(get_current_organization),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("billing:view"))
):
    """检查组织的订阅状态"""
    try:
        subscription_service = get_subscription_service(db)
        status = await subscription_service.check_subscription_status(current_org["id"])

        return {
            "success": True,
            "data": status
        }

    except Exception as e:
        logger.error(f"Error checking subscription status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check subscription status: {str(e)}"
        )

# 发票相关API
@router.get("/invoices", summary="获取发票列表")
async def get_invoices(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="发票状态筛选"),
    current_user: dict = Depends(get_current_user),
    current_org: dict = Depends(get_current_organization),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("billing:view"))
):
    """获取组织发票列表"""
    try:
        query = db.query(Invoice).filter(Invoice.organization_id == current_org["id"])

        if status:
            query = query.filter(Invoice.status == status)

        # 分页
        total = query.count()
        invoices = query.order_by(Invoice.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

        return {
            "success": True,
            "data": {
                "invoices": [
                    {
                        "id": inv.id,
                        "invoice_number": inv.invoice_number,
                        "status": inv.status,
                        "total_amount": float(inv.total_amount),
                        "currency": inv.currency,
                        "due_date": inv.due_date.isoformat() if inv.due_date else None,
                        "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                        "created_at": inv.created_at.isoformat() if inv.created_at else None
                    }
                    for inv in invoices
                ],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            }
        }

    except Exception as e:
        logger.error(f"Error getting invoices: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get invoices: {str(e)}"
        )