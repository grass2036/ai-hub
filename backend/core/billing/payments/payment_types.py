"""
支付类型定义

定义支付相关的数据结构和枚举。
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass


class PaymentProvider(str, Enum):
    """支付提供商"""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"


class PaymentStatus(str, Enum):
    """支付状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentType(str, Enum):
    """支付类型"""
    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"
    INSTALLMENT = "installment"
    REFUND = "refund"


class Currency(str, Enum):
    """货币类型"""
    USD = "usd"
    EUR = "eur"
    GBP = "gbp"
    JPY = "jpy"
    CNY = "cny"


@dataclass
class PaymentMethod:
    """支付方式"""
    id: str
    user_id: str
    provider: PaymentProvider
    type: str
    last4: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    brand: Optional[str] = None
    country: Optional[str] = None
    is_default: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider.value,
            "type": self.type,
            "last4": self.last4,
            "expiry_month": self.expiry_month,
            "expiry_year": self.expiry_year,
            "brand": self.brand,
            "country": self.country,
            "is_default": self.is_default,
            "metadata": self.metadata
        }


@dataclass
class PaymentItem:
    """支付项目"""
    name: str
    description: str
    amount: float
    quantity: int
    currency: Currency
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "amount": self.amount,
            "quantity": self.quantity,
            "currency": self.currency.value,
            "metadata": self.metadata
        }


@dataclass
class PaymentIntent:
    """支付意图"""
    id: str
    user_id: str
    amount: float
    currency: Currency
    payment_type: PaymentType
    items: List[PaymentItem]
    provider: PaymentProvider
    provider_intent_id: str
    status: PaymentStatus = PaymentStatus.PENDING
    client_secret: Optional[str] = None
    confirmation_method: str = "automatic"
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount,
            "currency": self.currency.value,
            "payment_type": self.payment_type.value,
            "items": [item.to_dict() for item in self.items],
            "provider": self.provider.value,
            "provider_intent_id": self.provider_intent_id,
            "status": self.status.value,
            "client_secret": self.client_secret,
            "confirmation_method": self.confirmation_method,
            "return_url": self.return_url,
            "cancel_url": self.cancel_url,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class PaymentResult:
    """支付结果"""
    success: bool
    payment_intent_id: str
    provider_transaction_id: Optional[str] = None
    status: PaymentStatus
    amount: Optional[float] = None
    currency: Optional[Currency] = None
    fee_amount: Optional[float] = None
    net_amount: Optional[float] = None
    failure_reason: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "payment_intent_id": self.payment_intent_id,
            "provider_transaction_id": self.provider_transaction_id,
            "status": self.status.value,
            "amount": self.amount,
            "currency": self.currency.value if self.currency else None,
            "fee_amount": self.fee_amount,
            "net_amount": self.net_amount,
            "failure_reason": self.failure_reason,
            "gateway_response": self.gateway_response,
            "metadata": self.metadata
        }


@dataclass
class Refund:
    """退款"""
    id: str
    payment_intent_id: str
    amount: float
    reason: str
    status: PaymentStatus = PaymentStatus.PENDING
    provider_refund_id: Optional[str] = None
    fee_amount: Optional[float] = None
    net_amount: Optional[float] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    processed_at: Optional[datetime] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "payment_intent_id": self.payment_intent_id,
            "amount": self.amount,
            "reason": self.reason,
            "status": self.status.value,
            "provider_refund_id": self.provider_refund_id,
            "fee_amount": self.fee_amount,
            "net_amount": self.net_amount,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None
        }


@dataclass
class Subscription:
    """订阅"""
    id: str
    user_id: str
    plan_id: str
    price_id: str
    provider: PaymentProvider
    provider_subscription_id: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "plan_id": self.plan_id,
            "price_id": self.price_id,
            "provider": self.provider.value,
            "provider_subscription_id": self.provider_subscription_id,
            "status": self.status,
            "current_period_start": self.current_period_start.isoformat(),
            "current_period_end": self.current_period_end.isoformat(),
            "trial_start": self.trial_start.isoformat() if self.trial_start else None,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class PaymentError(Exception):
    """支付错误"""
    def __init__(self, message: str, error_code: str = None, provider: str = None):
        self.message = message
        self.error_code = error_code
        self.provider = provider
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error": self.message,
            "error_code": self.error_code,
            "provider": self.provider
        }