"""
计费API端点

提供计费、订阅、使用量查询、支付处理等API接口。
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import logging

from backend.core.auth.jwt_manager import JWTManager, get_current_user
from backend.core.auth.api_key_manager import APIKeyManager, validate_api_key
from backend.core.billing.billing_service import BillingService, BillingConfig
from backend.core.billing.pricing_manager import PlanType, BillingCycle
from backend.core.billing.usage_tracker import UsageType, UsageStats
from backend.core.billing.payments import (
    PaymentProvider, PaymentStatus, PaymentType, Currency,
    PaymentResult, Subscription, PaymentError
)
from backend.core.cache.cache_manager import CacheManager
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

# 全局计费服务实例
billing_service: Optional[BillingService] = None


def get_billing_service() -> BillingService:
    """获取计费服务实例"""
    global billing_service
    if billing_service is None:
        settings = get_settings()

        # 创建计费配置
        config = BillingConfig(
            stripe_enabled=getattr(settings, 'stripe_enabled', False),
            stripe_api_key=getattr(settings, 'stripe_api_key', None),
            stripe_webhook_secret=getattr(settings, 'stripe_webhook_secret', None),
            paypal_enabled=getattr(settings, 'paypal_enabled', False),
            paypal_client_id=getattr(settings, 'paypal_client_id', None),
            paypal_client_secret=getattr(settings, 'paypal_client_secret', None),
            paypal_sandbox=getattr(settings, 'paypal_sandbox', True),
            currency=Currency.USD,
            tax_rate=0.08
        )

        # 创建缓存管理器
        cache_manager = CacheManager()

        # 初始化计费服务
        billing_service = BillingService(config, cache_manager)

    return billing_service


# Pydantic模型

class SubscriptionCreateRequest(BaseModel):
    """订阅创建请求"""
    plan_type: PlanType
    billing_cycle: BillingCycle
    payment_provider: PaymentProvider
    payment_method_id: Optional[str] = None


class SubscriptionCreateResponse(BaseModel):
    """订阅创建响应"""
    subscription_id: str
    user_id: str
    plan_type: str
    billing_cycle: str
    provider: str
    status: str
    current_period_start: str
    current_period_end: str
    external_subscription: Optional[Dict[str, Any]] = None


class SubscriptionCancelRequest(BaseModel):
    """订阅取消请求"""
    at_period_end: bool = True


class SubscriptionUpgradeRequest(BaseModel):
    """订阅升级请求"""
    new_plan_type: PlanType


class PaymentIntentRequest(BaseModel):
    """支付意图请求"""
    amount: float = Field(gt=0)
    payment_provider: PaymentProvider
    payment_method_id: Optional[str] = None
    description: Optional[str] = None


class PaymentIntentResponse(BaseModel):
    """支付意图响应"""
    success: bool
    payment_intent_id: str
    client_secret: Optional[str] = None
    approval_url: Optional[str] = None
    failure_reason: Optional[str] = None


class PaymentConfirmRequest(BaseModel):
    """支付确认请求"""
    payment_intent_id: str
    payment_method_id: Optional[str] = None


class UsageTrackingRequest(BaseModel):
    """使用量跟踪请求"""
    usage_type: UsageType
    model: Optional[str] = None
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    request_size: int = Field(default=0, ge=0)
    response_size: int = Field(default=0, ge=0)
    response_time_ms: int = Field(default=0, ge=0)
    status_code: int = Field(default=200, ge=100, le=599)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UsageStatsResponse(BaseModel):
    """使用量统计响应"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost: float
    average_response_time: float
    success_rate: float
    error_rate: float


class BillingSummaryResponse(BaseModel):
    """计费摘要响应"""
    user_id: str
    current_subscription: Dict[str, Any]
    usage_this_month: Dict[str, Any]
    quota_status: Dict[str, Any]
    billing_period: Dict[str, Any]


class InvoiceGenerateRequest(BaseModel):
    """发票生成请求"""
    invoice_type: str = "monthly"
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


# 订阅管理端点

@router.post("/subscriptions", response_model=SubscriptionCreateResponse)
async def create_subscription(
    request: SubscriptionCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    创建订阅
    """
    try:
        billing = get_billing_service()
        result = await billing.create_subscription(
            user_id=current_user["id"],
            plan_type=request.plan_type,
            billing_cycle=request.billing_cycle,
            payment_provider=request.payment_provider,
            payment_method_id=request.payment_method_id
        )

        return SubscriptionCreateResponse(**result)

    except PaymentError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建订阅失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: str,
    request: SubscriptionCancelRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    取消订阅
    """
    try:
        billing = get_billing_service()
        result = await billing.cancel_subscription(
            subscription_id=subscription_id,
            at_period_end=request.at_period_end
        )

        return {"message": "Subscription cancelled successfully", **result}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PaymentError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"取消订阅失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/subscriptions/{subscription_id}/upgrade")
async def upgrade_subscription(
    subscription_id: str,
    request: SubscriptionUpgradeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    升级订阅
    """
    try:
        billing = get_billing_service()
        result = await billing.upgrade_subscription(
            subscription_id=subscription_id,
            new_plan_type=request.new_plan_type
        )

        return {"message": "Subscription upgraded successfully", **result}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PaymentError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"升级订阅失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/subscriptions")
async def get_user_subscriptions(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取用户订阅列表
    """
    try:
        billing = get_billing_service()
        subscriptions = await billing.pricing_manager.get_user_subscriptions(current_user["id"])

        return {
            "subscriptions": [sub.to_dict() for sub in subscriptions],
            "total": len(subscriptions)
        }

    except Exception as e:
        logger.error(f"获取订阅列表失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/subscriptions/{subscription_id}")
async def get_subscription(
    subscription_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取订阅详情
    """
    try:
        billing = get_billing_service()
        subscription = await billing.pricing_manager.get_subscription(subscription_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        if subscription.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        return subscription.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取订阅详情失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# 支付处理端点

@router.post("/payments/intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
    request: PaymentIntentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    创建支付意图
    """
    try:
        billing = get_billing_service()
        result = await billing.create_payment_intent(
            user_id=current_user["id"],
            amount=request.amount,
            payment_provider=request.payment_provider,
            payment_method_id=request.payment_method_id,
            description=request.description
        )

        if not result.success:
            return PaymentIntentResponse(
                success=False,
                payment_intent_id="",
                failure_reason=result.failure_reason
            )

        # 提取客户端相关信息
        client_secret = getattr(result, 'client_secret', None)
        approval_url = result.metadata.get('approval_url') if result.metadata else None

        return PaymentIntentResponse(
            success=True,
            payment_intent_id=result.payment_intent_id,
            client_secret=client_secret,
            approval_url=approval_url
        )

    except Exception as e:
        logger.error(f"创建支付意图失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/payments/confirm")
async def confirm_payment(
    request: PaymentConfirmRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    确认支付
    """
    try:
        billing = get_billing_service()
        result = await billing.confirm_payment(
            payment_intent_id=request.payment_intent_id,
            payment_provider=PaymentProvider.STRIPE,  # 目前只支持Stripe
            payment_method_id=request.payment_method_id
        )

        if not result.success:
            raise HTTPException(status_code=400, detail=result.failure_reason)

        return {
            "message": "Payment confirmed successfully",
            "payment_intent_id": result.payment_intent_id,
            "status": result.status.value
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"确认支付失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/payments")
async def get_payment_history(
    limit: int = 20,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取支付历史
    """
    try:
        # TODO: 实现支付历史查询
        return {
            "payments": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"获取支付历史失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# 使用量管理端点

@router.post("/usage/track")
async def track_usage(
    request: UsageTrackingRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    跟踪使用量
    """
    try:
        billing = get_billing_service()
        result = await billing.track_usage(
            user_id=current_user["id"],
            usage_type=request.usage_type,
            model=request.model,
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens,
            request_size=request.request_size,
            response_size=request.response_size,
            response_time_ms=request.response_time_ms,
            status_code=request.status_code,
            metadata=request.metadata
        )

        return result

    except Exception as e:
        logger.error(f"使用量跟踪失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/usage/stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    start_date: datetime,
    end_date: datetime,
    usage_type: Optional[UsageType] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取使用量统计
    """
    try:
        billing = get_billing_service()
        stats = await billing.get_usage_stats(
            user_id=current_user["id"],
            start_date=start_date,
            end_date=end_date,
            usage_type=usage_type
        )

        return UsageStatsResponse(
            total_requests=stats.total_requests,
            successful_requests=stats.successful_requests,
            failed_requests=stats.failed_requests,
            total_input_tokens=stats.total_input_tokens,
            total_output_tokens=stats.total_output_tokens,
            total_tokens=stats.total_tokens,
            total_cost=stats.total_cost,
            average_response_time=stats.average_response_time,
            success_rate=stats.success_rate,
            error_rate=stats.error_rate
        )

    except Exception as e:
        logger.error(f"获取使用量统计失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/quota")
async def get_quota_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取配额状态
    """
    try:
        billing = get_billing_service()
        quota_status = await billing.get_quota_status(current_user["id"])

        return quota_status

    except Exception as e:
        logger.error(f"获取配额状态失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# 发票管理端点

@router.post("/invoices/generate")
async def generate_invoice(
    request: InvoiceGenerateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    生成发票
    """
    try:
        billing = get_billing_service()
        invoice = await billing.generate_invoice(
            user_id=current_user["id"],
            invoice_type=request.invoice_type,
            period_start=request.period_start,
            period_end=request.period_end
        )

        if not invoice:
            raise HTTPException(status_code=404, detail="No invoice data found")

        return {"message": "Invoice generated successfully", "invoice": invoice}

    except Exception as e:
        logger.error(f"生成发票失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/invoices")
async def get_invoices(
    limit: int = 20,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取发票列表
    """
    try:
        # TODO: 实现发票列表查询
        return {
            "invoices": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"获取发票列表失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取发票详情
    """
    try:
        # TODO: 实现发票详情查询
        return {"invoice_id": invoice_id, "status": "TODO"}

    except Exception as e:
        logger.error(f"获取发票详情失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取发票PDF
    """
    try:
        billing = get_billing_service()
        pdf_content = await billing.get_invoice_pdf(invoice_id)

        if not pdf_content:
            raise HTTPException(status_code=404, detail="Invoice not found")

        return StreamingResponse(
            iter([pdf_content]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=invoice_{invoice_id}.pdf"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取发票PDF失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# 计费摘要端点

@router.get("/summary", response_model=BillingSummaryResponse)
async def get_billing_summary(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取计费摘要
    """
    try:
        billing = get_billing_service()
        summary = await billing.get_billing_summary(current_user["id"])

        if "error" in summary:
            raise HTTPException(status_code=500, detail=summary["error"])

        return BillingSummaryResponse(**summary)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取计费摘要失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Webhook端点

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="stripe-signature")
):
    """
    Stripe webhook端点
    """
    try:
        body = await request.body()
        billing = get_billing_service()

        result = await billing.handle_webhook(
            provider=PaymentProvider.STRIPE,
            payload=body,
            headers=dict(request.headers),
            signature=stripe_signature
        )

        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"Stripe webhook处理失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhooks/paypal")
async def paypal_webhook(request: Request):
    """
    PayPal webhook端点
    """
    try:
        body = await request.body()
        billing = get_billing_service()

        result = await billing.handle_webhook(
            provider=PaymentProvider.PAYPAL,
            payload=body,
            headers=dict(request.headers)
        )

        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"PayPal webhook处理失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# 价格计划端点

@router.get("/plans")
async def get_pricing_plans():
    """
    获取价格计划列表
    """
    try:
        billing = get_billing_service()
        plans = await billing.pricing_manager.get_all_plans()

        return {
            "plans": [plan.to_dict() for plan in plans],
            "total": len(plans)
        }

    except Exception as e:
        logger.error(f"获取价格计划失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/plans/{plan_type}")
async def get_pricing_plan(plan_type: PlanType):
    """
    获取特定类型的价格计划
    """
    try:
        billing = get_billing_service()
        plans = await billing.pricing_manager.get_plans_by_type(plan_type)

        return {
            "plan_type": plan_type.value,
            "plans": [plan.to_dict() for plan in plans],
            "total": len(plans)
        }

    except Exception as e:
        logger.error(f"获取价格计划失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# 管理员端点

@router.get("/admin/revenue")
async def get_revenue_stats(
    start_date: datetime,
    end_date: datetime,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取收入统计（管理员）
    """
    # TODO: 检查管理员权限
    try:
        billing = get_billing_service()
        stats = await billing.get_revenue_stats(start_date, end_date)

        return stats

    except Exception as e:
        logger.error(f"获取收入统计失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/admin/users/{user_id}/billing")
async def get_user_billing_summary(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取用户计费摘要（管理员）
    """
    # TODO: 检查管理员权限
    try:
        billing = get_billing_service()
        summary = await billing.get_billing_summary(user_id)

        if "error" in summary:
            raise HTTPException(status_code=404, detail=summary["error"])

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户计费摘要失败: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")