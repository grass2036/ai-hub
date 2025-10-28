"""
价格计划管理器

提供价格计划管理、订阅管理、定价策略等功能。
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


class PlanType(Enum):
    """价格计划类型"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class BillingCycle(Enum):
    """计费周期"""
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class FeatureType(Enum):
    """功能类型"""
    API_CALLS = "api_calls"
    MODELS = "models"
    SUPPORT = "support"
    ANALYTICS = "analytics"
    TEAM = "team"
    CUSTOM = "custom"


@dataclass
class Feature:
    """功能定义"""
    name: str
    type: FeatureType
    included: bool
    limit: Optional[int] = None
    unit: str = ""
    description: str = ""
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.type.value,
            "included": self.included,
            "limit": self.limit,
            "unit": self.unit,
            "description": self.description,
            "metadata": self.metadata or {}
        }


@dataclass
class PricingPlan:
    """价格计划"""
    id: str
    name: str
    type: PlanType
    billing_cycle: BillingCycle
    price: float
    currency: str = "USD"
    features: List[Feature] = None
    description: str = ""
    popular: bool = False
    trial_days: int = 0
    setup_fee: float = 0.0
    is_active: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.features is None:
            self.features = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "billing_cycle": self.billing_cycle.value,
            "price": self.price,
            "currency": self.currency,
            "features": [f.to_dict() for f in self.features],
            "description": self.description,
            "popular": self.popular,
            "trial_days": self.trial_days,
            "setup_fee": self.setup_fee,
            "is_active": self.is_active,
            "metadata": self.metadata
        }

    def get_feature(self, feature_type: FeatureType) -> Optional[Feature]:
        """获取特定功能"""
        for feature in self.features:
            if feature.type == feature_type:
                return feature
        return None

    def has_feature(self, feature_type: FeatureType) -> bool:
        """检查是否包含特定功能"""
        feature = self.get_feature(feature_type)
        return feature is not None and feature.included

    def get_feature_limit(self, feature_type: FeatureType) -> Optional[int]:
        """获取功能限制"""
        feature = self.get_feature(feature_type)
        return feature.limit if feature else None


@dataclass
class Subscription:
    """订阅"""
    id: str
    user_id: str
    plan_id: str
    status: str  # active, cancelled, expired, trial, past_due
    current_period_start: datetime
    current_period_end: datetime
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_at_period_end: bool = False
    created_at: datetime = None
    updated_at: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "plan_id": self.plan_id,
            "status": self.status,
            "current_period_start": self.current_period_start.isoformat(),
            "current_period_end": self.current_period_end.isoformat(),
            "trial_start": self.trial_start.isoformat() if self.trial_start else None,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }

    @property
    def is_active(self) -> bool:
        """检查订阅是否激活"""
        return self.status == "active"

    @property
    def is_trial(self) -> bool:
        """检查是否在试用期内"""
        return (
            self.status == "trial" and
            self.trial_end and
            self.trial_end > datetime.now(timezone.utc)
        )

    @property
    def is_expired(self) -> bool:
        """检查订阅是否过期"""
        return (
            self.current_period_end < datetime.now(timezone.utc) and
            self.status not in ["cancelled"]
        )

    @property
    def days_until_renewal(self) -> int:
        """计算距离续订的天数"""
        delta = self.current_period_end - datetime.now(timezone.utc)
        return max(0, delta.days)

    @property
    def days_in_trial(self) -> int:
        """计算试用剩余天数"""
        if not self.trial_end:
            return 0
        delta = self.trial_end - datetime.now(timezone.utc)
        return max(0, delta.days)


class PricingManager:
    """价格管理器"""

    def __init__(self, storage_backend=None):
        """
        初始化价格管理器

        Args:
            storage_backend: 存储后端（数据库/缓存）
        """
        self.storage = storage_backend

        # 预定义价格计划
        self._plans = self._initialize_default_plans()

    def _initialize_default_plans(self) -> Dict[str, PricingPlan]:
        """初始化默认价格计划"""
        plans = {}

        # Free Plan
        free_features = [
            Feature(
                name="API调用",
                type=FeatureType.API_CALLS,
                included=True,
                limit=100,
                unit="次/月",
                description="每月100次API调用"
            ),
            Feature(
                name="基础模型",
                type=FeatureType.MODELS,
                included=True,
                metadata={"models": ["gpt-3.5-turbo", "claude-instant"]},
                description="访问基础AI模型"
            ),
            Feature(
                name="社区支持",
                type=FeatureType.SUPPORT,
                included=True,
                description="社区文档和论坛支持"
            ),
            Feature(
                name="使用报告",
                type=FeatureType.ANALYTICS,
                included=True,
                description="基础使用统计报告"
            )
        ]

        plans["free"] = PricingPlan(
            id="free",
            name="免费版",
            type=PlanType.FREE,
            billing_cycle=BillingCycle.MONTHLY,
            price=0.0,
            features=free_features,
            description="适合个人用户和小型项目",
            trial_days=0
        )

        # Pro Plan
        pro_features = [
            Feature(
                name="API调用",
                type=FeatureType.API_CALLS,
                included=True,
                limit=5000,
                unit="次/月",
                description="每月5,000次API调用"
            ),
            Feature(
                name="高级模型",
                type=FeatureType.MODELS,
                included=True,
                metadata={
                    "models": ["gpt-4", "claude-3-sonnet", "gemini-pro"],
                    "unlimited": False
                },
                description="访问高级AI模型"
            ),
            Feature(
                name="优先支持",
                type=FeatureType.SUPPORT,
                included=True,
                description="24小时内邮件支持"
            ),
            Feature(
                name="实时监控",
                type=FeatureType.ANALYTICS,
                included=True,
                description="实时使用监控和告警"
            ),
            Feature(
                name="团队协作",
                type=FeatureType.TEAM,
                included=True,
                limit=5,
                unit="成员",
                description="最多5个团队成员"
            )
        ]

        plans["pro_monthly"] = PricingPlan(
            id="pro_monthly",
            name="专业版",
            type=PlanType.PRO,
            billing_cycle=BillingCycle.MONTHLY,
            price=29.0,
            features=pro_features,
            description="适合专业开发者和小团队",
            popular=True,
            trial_days=14
        )

        plans["pro_yearly"] = PricingPlan(
            id="pro_yearly",
            name="专业版",
            type=PlanType.PRO,
            billing_cycle=BillingCycle.YEARLY,
            price=290.0,  # 年付优惠
            features=pro_features,
            description="适合专业开发者和小团队，年付享受优惠",
            trial_days=14
        )

        # Enterprise Plan
        enterprise_features = [
            Feature(
                name="API调用",
                type=FeatureType.API_CALLS,
                included=True,
                limit=None,  # 无限制
                unit="次/月",
                description="无限API调用"
            ),
            Feature(
                name="所有模型",
                type=FeatureType.MODELS,
                included=True,
                metadata={
                    "models": "all",
                    "unlimited": True
                },
                description="访问所有AI模型，包括最新模型"
            ),
            Feature(
                name="专属支持",
                type=FeatureType.SUPPORT,
                included=True,
                description="24/7专属技术支持，电话支持"
            ),
            Feature(
                name="高级分析",
                type=FeatureType.ANALYTICS,
                included=True,
                description="高级数据分析和自定义报告"
            ),
            Feature(
                name="团队协作",
                type=FeatureType.TEAM,
                included=True,
                limit=None,  # 无限制
                unit="成员",
                description="无限团队成员"
            ),
            Feature(
                name="SLA保障",
                type=FeatureType.CUSTOM,
                included=True,
                description="99.9%服务可用性保障"
            ),
            Feature(
                name="定制化功能",
                type=FeatureType.CUSTOM,
                included=True,
                description="定制化功能开发"
            )
        ]

        plans["enterprise"] = PricingPlan(
            id="enterprise",
            name="企业版",
            type=PlanType.ENTERPRISE,
            billing_cycle=BillingCycle.MONTHLY,
            price=99.0,
            features=enterprise_features,
            description="适合大型企业和高用量客户",
            trial_days=30
        )

        return plans

    async def get_plan(self, plan_id: str) -> Optional[PricingPlan]:
        """
        获取价格计划

        Args:
            plan_id: 计划ID

        Returns:
            价格计划或None
        """
        # 先从内存缓存查找
        if plan_id in self._plans:
            return self._plans[plan_id]

        # 从存储后端查找
        # TODO: 实现数据库查询
        return None

    async def list_plans(
        self,
        active_only: bool = True,
        plan_types: List[PlanType] = None
    ) -> List[PricingPlan]:
        """
        列出价格计划

        Args:
            active_only: 是否只显示激活的计划
            plan_types: 计划类型过滤

        Returns:
            价格计划列表
        """
        plans = list(self._plans.values())

        # 过滤激活状态
        if active_only:
            plans = [p for p in plans if p.is_active]

        # 过滤计划类型
        if plan_types:
            plans = [p for p in plans if p.type in plan_types]

        # 按价格排序
        plans.sort(key=lambda x: x.price)

        return plans

    async def create_plan(self, plan: PricingPlan) -> bool:
        """
        创建价格计划

        Args:
            plan: 价格计划

        Returns:
            是否成功创建
        """
        try:
            # 验证计划ID唯一性
            if plan.id in self._plans:
                raise ValueError(f"计划ID {plan.id} 已存在")

            # 验证计划数据
            self._validate_plan(plan)

            # 保存到存储后端
            # TODO: 实现数据库保存
            await self._save_plan(plan)

            # 添加到内存缓存
            self._plans[plan.id] = plan

            logger.info(f"创建价格计划成功: {plan.id}")
            return True

        except Exception as e:
            logger.error(f"创建价格计划失败: {e}")
            return False

    async def update_plan(self, plan_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新价格计划

        Args:
            plan_id: 计划ID
            updates: 更新数据

        Returns:
            是否成功更新
        """
        try:
            plan = await self.get_plan(plan_id)
            if not plan:
                return False

            # 更新字段
            for field, value in updates.items():
                if hasattr(plan, field):
                    setattr(plan, field, value)

            # 验证更新后的计划
            self._validate_plan(plan)

            # 保存到存储后端
            # TODO: 实现数据库更新
            await self._save_plan(plan)

            # 更新内存缓存
            self._plans[plan_id] = plan

            logger.info(f"更新价格计划成功: {plan_id}")
            return True

        except Exception as e:
            logger.error(f"更新价格计划失败: {e}")
            return False

    async def delete_plan(self, plan_id: str) -> bool:
        """
        删除价格计划

        Args:
            plan_id: 计划ID

        Returns:
            是否成功删除
        """
        try:
            # 检查是否有活跃订阅
            active_subscriptions = await self._count_active_subscriptions(plan_id)
            if active_subscriptions > 0:
                raise ValueError(f"计划 {plan_id} 还有 {active_subscriptions} 个活跃订阅，无法删除")

            # 从存储后端删除
            # TODO: 实现数据库删除
            await self._delete_plan(plan_id)

            # 从内存缓存删除
            if plan_id in self._plans:
                del self._plans[plan_id]

            logger.info(f"删除价格计划成功: {plan_id}")
            return True

        except Exception as e:
            logger.error(f"删除价格计划失败: {e}")
            return False

    async def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        billing_cycle: BillingCycle = BillingCycle.MONTHLY,
        trial_days: int = 0
    ) -> Optional[Subscription]:
        """
        创建订阅

        Args:
            user_id: 用户ID
            plan_id: 计划ID
            billing_cycle: 计费周期
            trial_days: 试用天数

        Returns:
            订阅或None
        """
        try:
            # 获取价格计划
            plan = await self.get_plan(plan_id)
            if not plan:
                raise ValueError(f"价格计划不存在: {plan_id}")

            # 检查用户是否已有活跃订阅
            existing_subscription = await self._get_active_subscription(user_id)
            if existing_subscription:
                # 升级或降级现有订阅
                return await self._update_subscription_plan(
                    existing_subscription.id,
                    plan_id,
                    billing_cycle
                )

            # 创建新订阅
            now = datetime.now(timezone.utc)
            subscription = Subscription(
                id=self._generate_subscription_id(),
                user_id=user_id,
                plan_id=plan_id,
                status="trial" if trial_days > 0 else "active",
                current_period_start=now,
                current_period_end=self._calculate_period_end(now, billing_cycle),
                trial_start=now if trial_days > 0 else None,
                trial_end=now + timedelta(days=trial_days) if trial_days > 0 else None
            )

            # 保存订阅
            await self._save_subscription(subscription)

            logger.info(f"创建订阅成功: {subscription.id} for user {user_id}")
            return subscription

        except Exception as e:
            logger.error(f"创建订阅失败: {e}")
            return None

    async def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """
        获取订阅

        Args:
            subscription_id: 订阅ID

        Returns:
            订阅或None
        """
        # TODO: 实现数据库查询
        return None

    async def get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """
        获取用户的活跃订阅

        Args:
            user_id: 用户ID

        Returns:
            订阅或None
        """
        return await self._get_active_subscription(user_id)

    async def cancel_subscription(
        self,
        subscription_id: str,
        cancel_at_period_end: bool = True
    ) -> bool:
        """
        取消订阅

        Args:
            subscription_id: 订阅ID
            cancel_at_period_end: 是否在周期结束时取消

        Returns:
            是否成功取消
        """
        try:
            subscription = await self.get_subscription(subscription_id)
            if not subscription:
                return False

            subscription.status = "cancelled"
            subscription.cancelled_at = datetime.now(timezone.utc)
            subscription.cancel_at_period_end = cancel_at_period_end
            subscription.updated_at = datetime.now(timezone.utc)

            await self._save_subscription(subscription)

            logger.info(f"取消订阅成功: {subscription_id}")
            return True

        except Exception as e:
            logger.error(f"取消订阅失败: {e}")
            return False

    async def calculate_subscription_cost(
        self,
        plan_id: str,
        billing_cycle: BillingCycle,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        计算订阅成本

        Args:
            plan_id: 计划ID
            billing_cycle: 计费周期
            quantity: 数量

        Returns:
            成本详情
        """
        plan = await self.get_plan(plan_id)
        if not plan:
            raise ValueError(f"价格计划不存在: {plan_id}")

        base_price = plan.price
        total_price = base_price * quantity

        # 年付折扣
        if billing_cycle == BillingCycle.YEARLY:
            total_price *= 0.8  # 20%折扣

        # 计算税费
        tax_rate = 0.08  # 8%税率
        tax_amount = total_price * tax_rate
        total_with_tax = total_price + tax_amount

        return {
            "plan_id": plan_id,
            "billing_cycle": billing_cycle.value,
            "quantity": quantity,
            "base_price": base_price,
            "total_price": total_price,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "total_with_tax": total_with_tax,
            "currency": plan.currency
        }

    # 私有方法

    def _validate_plan(self, plan: PricingPlan) -> None:
        """验证价格计划"""
        if not plan.name or not plan.id:
            raise ValueError("计划名称和ID不能为空")

        if plan.price < 0:
            raise ValueError("价格不能为负数")

        if not plan.currency:
            raise ValueError("货币不能为空")

        # 验证功能
        for feature in plan.features:
            if not feature.name:
                raise ValueError("功能名称不能为空")

    def _generate_subscription_id(self) -> str:
        """生成订阅ID"""
        import uuid
        return f"sub_{uuid.uuid4().hex[:16]}"

    def _calculate_period_end(
        self,
        start_date: datetime,
        billing_cycle: BillingCycle
    ) -> datetime:
        """计算计费周期结束日期"""
        if billing_cycle == BillingCycle.MONTHLY:
            # 加一个月
            if start_date.month == 12:
                return start_date.replace(year=start_date.year + 1, month=1)
            else:
                return start_date.replace(month=start_date.month + 1)
        elif billing_cycle == BillingCycle.YEARLY:
            # 加一年
            return start_date.replace(year=start_date.year + 1)
        else:
            # 默认加一个月
            return start_date + timedelta(days=30)

    async def _save_plan(self, plan: PricingPlan) -> None:
        """保存价格计划到存储后端"""
        # TODO: 实现数据库保存
        pass

    async def _delete_plan(self, plan_id: str) -> None:
        """从存储后端删除价格计划"""
        # TODO: 实现数据库删除
        pass

    async def _save_subscription(self, subscription: Subscription) -> None:
        """保存订阅到存储后端"""
        # TODO: 实现数据库保存
        pass

    async def _get_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """获取用户的活跃订阅"""
        # TODO: 实现数据库查询
        return None

    async def _count_active_subscriptions(self, plan_id: str) -> int:
        """统计价格计划的活跃订阅数量"""
        # TODO: 实现数据库查询
        return 0

    async def _update_subscription_plan(
        self,
        subscription_id: str,
        new_plan_id: str,
        billing_cycle: BillingCycle
    ) -> Optional[Subscription]:
        """更新订阅计划"""
        # TODO: 实现订阅更新逻辑
        return None