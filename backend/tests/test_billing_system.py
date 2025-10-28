"""
计费系统测试

测试计费系统的所有组件，包��定价管理、使用量跟踪、配额管理、
发票生成、支付处理和API端点。
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal

from backend.core.billing.pricing_manager import PricingManager, PlanType, BillingCycle
from backend.core.billing.usage_tracker import UsageTracker, UsageType, UsageStats
from backend.core.billing.quota_manager import QuotaManager, QuotaViolation, QuotaType
from backend.core.billing.invoice_generator import InvoiceGenerator
from backend.core.billing.billing_service import BillingService, BillingConfig
from backend.core.billing.payments import (
    StripeProcessor, PayPalProcessor, PaymentWebhookHandler,
    PaymentProvider, PaymentStatus, PaymentType, Currency,
    PaymentResult, PaymentError
)
from backend.core.cache.cache_manager import CacheManager


class TestPricingManager:
    """定价管理器测试"""

    @pytest.fixture
    def pricing_manager(self):
        """创建定价管理器实例"""
        return PricingManager()

    @pytest.mark.asyncio
    async def test_create_plan(self, pricing_manager):
        """测试创建价格计划"""
        plan = await pricing_manager.create_plan(
            name="Test Pro Plan",
            type=PlanType.PRO,
            billing_cycle=BillingCycle.MONTHLY,
            price=29.99,
            currency="USD",
            description="Test professional plan",
            features=["API Access", "Basic Support"],
            trial_days=14
        )

        assert plan.id is not None
        assert plan.name == "Test Pro Plan"
        assert plan.type == PlanType.PRO
        assert plan.billing_cycle == BillingCycle.MONTHLY
        assert plan.price == 29.99
        assert plan.currency == "USD"
        assert plan.trial_days == 14
        assert len(plan.features) == 2

    @pytest.mark.asyncio
    async def test_get_plan(self, pricing_manager):
        """测试获取价格计划"""
        # 创建计划
        created_plan = await pricing_manager.create_plan(
            name="Test Plan",
            type=PlanType.ENTERPRISE,
            billing_cycle=BillingCycle.YEARLY,
            price=999.99
        )

        # 获取计划
        retrieved_plan = await pricing_manager.get_plan(created_plan.id)

        assert retrieved_plan is not None
        assert retrieved_plan.id == created_plan.id
        assert retrieved_plan.name == "Test Plan"
        assert retrieved_plan.type == PlanType.ENTERPRISE

    @pytest.mark.asyncio
    async def test_get_plans_by_type(self, pricing_manager):
        """测试按类型获取价格计划"""
        # 创建多个计划
        await pricing_manager.create_plan(
            name="Pro Monthly",
            type=PlanType.PRO,
            billing_cycle=BillingCycle.MONTHLY,
            price=29.99
        )
        await pricing_manager.create_plan(
            name="Pro Yearly",
            type=PlanType.PRO,
            billing_cycle=BillingCycle.YEARLY,
            price=299.99
        )
        await pricing_manager.create_plan(
            name="Free Plan",
            type=PlanType.FREE,
            billing_cycle=BillingCycle.MONTHLY,
            price=0.0
        )

        # 获取PRO类型计划
        pro_plans = await pricing_manager.get_plans_by_type(PlanType.PRO)

        assert len(pro_plans) == 2
        assert all(plan.type == PlanType.PRO for plan in pro_plans)

    @pytest.mark.asyncio
    async def test_calculate_subscription_cost(self, pricing_manager):
        """测试计算订阅费用"""
        # 创建计划
        plan = await pricing_manager.create_plan(
            name="Test Plan",
            type=PlanType.PRO,
            billing_cycle=BillingCycle.MONTHLY,
            price=100.0
        )

        # 计算月度费用
        monthly_cost = await pricing_manager.calculate_subscription_cost(
            plan_id=plan.id,
            billing_cycle=BillingCycle.MONTHLY,
            quantity=1
        )
        assert monthly_cost == 100.0

        # 计算年度费用
        yearly_cost = await pricing_manager.calculate_subscription_cost(
            plan_id=plan.id,
            billing_cycle=BillingCycle.YEARLY,
            quantity=1
        )
        assert yearly_cost == 100.0 * 12 * 0.8  # 假设8折优惠

    @pytest.mark.asyncio
    async def test_create_subscription(self, pricing_manager):
        """测试创建订阅"""
        # 创建计划
        plan = await pricing_manager.create_plan(
            name="Test Plan",
            type=PlanType.PRO,
            billing_cycle=BillingCycle.MONTHLY,
            price=29.99
        )

        # 创建订阅
        subscription = await pricing_manager.create_subscription(
            user_id="test_user_123",
            plan_id=plan.id,
            billing_cycle=BillingCycle.MONTHLY
        )

        assert subscription.id is not None
        assert subscription.user_id == "test_user_123"
        assert subscription.plan_id == plan.id
        assert subscription.status.value == "active"
        assert subscription.is_active is True

    @pytest.mark.asyncio
    async def test_cancel_subscription(self, pricing_manager):
        """测试取消订阅"""
        # 创建计划和订阅
        plan = await pricing_manager.create_plan(
            name="Test Plan",
            type=PlanType.PRO,
            billing_cycle=BillingCycle.MONTHLY,
            price=29.99
        )
        subscription = await pricing_manager.create_subscription(
            user_id="test_user_123",
            plan_id=plan.id,
            billing_cycle=BillingCycle.MONTHLY
        )

        # 取消订阅（立即生效）
        cancelled_subscription = await pricing_manager.cancel_subscription(
            subscription_id=subscription.id,
            at_period_end=False
        )

        assert cancelled_subscription.status.value == "cancelled"
        assert cancelled_subscription.cancel_at_period_end is False

    @pytest.mark.asyncio
    async def test_change_subscription_plan(self, pricing_manager):
        """测试更改订阅计划"""
        # 创建两个计划
        pro_plan = await pricing_manager.create_plan(
            name="Pro Plan",
            type=PlanType.PRO,
            billing_cycle=BillingCycle.MONTHLY,
            price=29.99
        )
        enterprise_plan = await pricing_manager.create_plan(
            name="Enterprise Plan",
            type=PlanType.ENTERPRISE,
            billing_cycle=BillingCycle.MONTHLY,
            price=99.99
        )

        # 创建订阅
        subscription = await pricing_manager.create_subscription(
            user_id="test_user_123",
            plan_id=pro_plan.id,
            billing_cycle=BillingCycle.MONTHLY
        )

        # 升级计划
        updated_subscription = await pricing_manager.change_subscription_plan(
            subscription_id=subscription.id,
            new_plan_id=enterprise_plan.id
        )

        assert updated_subscription.plan_id == enterprise_plan.id
        assert updated_subscription.user_id == "test_user_123"


class TestUsageTracker:
    """使用量跟踪器测试"""

    @pytest.fixture
    def usage_tracker(self):
        """创建使用量跟踪器实例"""
        cache_manager = Mock(spec=CacheManager)
        cache_manager.get = AsyncMock(return_value=None)
        cache_manager.set = AsyncMock()
        return UsageTracker(cache_manager)

    @pytest.mark.asyncio
    async def test_track_api_usage(self, usage_tracker):
        """测试跟踪API使用量"""
        usage_record = await usage_tracker.track_usage(
            user_id="test_user_123",
            usage_type=UsageType.API_CALL,
            model="gpt-3.5-turbo",
            input_tokens=100,
            output_tokens=50,
            request_size=1024,
            response_size=2048,
            response_time_ms=1500,
            status_code=200
        )

        assert usage_record.id is not None
        assert usage_record.user_id == "test_user_123"
        assert usage_record.usage_type == UsageType.API_CALL
        assert usage_record.model == "gpt-3.5-turbo"
        assert usage_record.input_tokens == 100
        assert usage_record.output_tokens == 50
        assert usage_record.total_tokens == 150
        assert usage_record.is_successful is True

    @pytest.mark.asyncio
    async def test_track_usage_with_error(self, usage_tracker):
        """测试跟踪错误使用量"""
        usage_record = await usage_tracker.track_usage(
            user_id="test_user_123",
            usage_type=UsageType.API_CALL,
            model="gpt-3.5-turbo",
            input_tokens=100,
            output_tokens=0,
            status_code=429,
            error_message="Rate limit exceeded"
        )

        assert usage_record.status_code == 429
        assert usage_record.is_successful is False
        assert usage_record.error_message == "Rate limit exceeded"

    @pytest.mark.asyncio
    async def test_calculate_cost(self, usage_tracker):
        """测试计算费用"""
        cost = usage_tracker._calculate_cost(
            model="gpt-3.5-turbo",
            input_tokens=1000,
            output_tokens=500
        )

        assert isinstance(cost, float)
        assert cost > 0
        # GPT-3.5-turbo大约 $0.0015/1K input tokens, $0.002/1K output tokens
        expected_cost = (1000 * 0.0015 / 1000) + (500 * 0.002 / 1000)
        assert abs(cost - expected_cost) < 0.001

    @pytest.mark.asyncio
    async def test_get_usage_stats(self, usage_tracker):
        """测试获取使用量统计"""
        # 模拟一些使用记录
        user_id = "test_user_123"
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        end_date = datetime.now(timezone.utc)

        # Mock数据库查询结果
        mock_records = [
            Mock(
                total_tokens=100,
                cost=0.01,
                is_successful=True,
                response_time_ms=500,
                status_code=200
            ),
            Mock(
                total_tokens=200,
                cost=0.02,
                is_successful=True,
                response_time_ms=800,
                status_code=200
            ),
            Mock(
                total_tokens=50,
                cost=0.005,
                is_successful=False,
                response_time_ms=300,
                status_code=429
            )
        ]

        with patch.object(usage_tracker, '_query_usage_records', return_value=mock_records):
            stats = await usage_tracker.get_usage_stats(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )

        assert stats.total_requests == 3
        assert stats.successful_requests == 2
        assert stats.failed_requests == 1
        assert stats.total_tokens == 350
        assert stats.total_cost == 0.035
        assert stats.success_rate == 66.67
        assert stats.error_rate == 33.33


class TestQuotaManager:
    """配额管理器测试"""

    @pytest.fixture
    def quota_manager(self):
        """创建配额管理器实例"""
        cache_manager = Mock(spec=CacheManager)
        cache_manager.get = AsyncMock(return_value=None)
        cache_manager.set = AsyncMock()
        return QuotaManager(cache_manager)

    @pytest.mark.asyncio
    async def test_get_user_quota(self, quota_manager):
        """测试获取用户配额"""
        user_id = "test_user_123"

        # Mock配额数据
        mock_quota = {
            "plan_type": "pro",
            "api_calls_monthly": 10000,
            "tokens_monthly": 1000000,
            "storage_gb": 100,
            "api_calls_used": 5000,
            "tokens_used": 500000,
            "storage_used": 50
        }

        with patch.object(quota_manager, '_get_quota_from_db', return_value=mock_quota):
            quota_status = await quota_manager.get_quota_status(user_id)

        assert quota_status["plan_type"] == "pro"
        assert quota_status["api_calls"]["limit"] == 10000
        assert quota_status["api_calls"]["used"] == 5000
        assert quota_status["api_calls"]["remaining"] == 5000
        assert quota_status["tokens"]["limit"] == 1000000
        assert quota_status["tokens"]["used"] == 500000
        assert quota_status["tokens"]["remaining"] == 500000

    @pytest.mark.asyncio
    async def test_check_quota_violation_no_violation(self, quota_manager):
        """测试配额检查 - 无违规"""
        user_id = "test_user_123"
        quota_type = QuotaType.API_CALLS
        amount = 100

        with patch.object(quota_manager, '_get_current_usage', return_value=5000):
            with patch.object(quota_manager, '_get_quota_limit', return_value=10000):
                violation = await quota_manager.check_quota_violation(
                    user_id=user_id,
                    quota_type=quota_type,
                    amount=amount
                )

        assert violation is None

    @pytest.mark.asyncio
    async def test_check_quota_violation_with_violation(self, quota_manager):
        """测试配额检查 - 有违规"""
        user_id = "test_user_123"
        quota_type = QuotaType.API_CALLS
        amount = 100

        with patch.object(quota_manager, '_get_current_usage', return_value=9950):
            with patch.object(quota_manager, '_get_quota_limit', return_value=10000):
                violation = await quota_manager.check_quota_violation(
                    user_id=user_id,
                    quota_type=quota_type,
                    amount=amount
                )

        assert violation is not None
        assert violation.user_id == user_id
        assert violation.quota_type == quota_type
        assert violation.current_usage == 9950
        assert violation.limit == 10000
        assert violation.requested_amount == 100
        assert violation.would_exceed_by == 50

    @pytest.mark.asyncio
    async def test_upgrade_user_plan(self, quota_manager):
        """测试升级用户计划"""
        user_id = "test_user_123"
        new_plan_type = "enterprise"

        with patch.object(quota_manager, '_update_user_plan_in_db') as mock_update:
            await quota_manager.upgrade_user_plan(user_id, new_plan_type)
            mock_update.assert_called_once_with(user_id, new_plan_type)

    @pytest.mark.asyncio
    async def test_record_quota_violation(self, quota_manager):
        """测试记录配额违规"""
        violation = QuotaViolation(
            user_id="test_user_123",
            quota_type=QuotaType.API_CALLS,
            current_usage=9950,
            limit=10000,
            requested_amount=100,
            would_exceed_by=50
        )

        with patch.object(quota_manager, '_save_violation_to_db') as mock_save:
            await quota_manager.record_quota_violation(violation)
            mock_save.assert_called_once_with(violation)


class TestInvoiceGenerator:
    """发票生成器测试"""

    @pytest.fixture
    def invoice_generator(self):
        """创建发票生成器实例"""
        return InvoiceGenerator()

    @pytest.mark.asyncio
    async def test_generate_monthly_invoice(self, invoice_generator):
        """测试生成月度发票"""
        user_id = "test_user_123"
        subscription_id = "sub_123"
        period_start = datetime.now(timezone.utc).replace(day=1)
        period_end = period_start + timedelta(days=32)
        period_end = period_end.replace(day=1) - timedelta(days=1)

        # Mock依赖方法
        with patch.object(invoice_generator, '_get_user') as mock_get_user:
            with patch.object(invoice_generator, '_get_subscription') as mock_get_sub:
                with patch.object(invoice_generator, '_get_pricing_plan') as mock_get_plan:
                    with patch.object(invoice_generator, '_save_invoice') as mock_save:

                        # Mock返回数据
                        mock_get_user.return_value = {
                            "id": user_id,
                            "name": "Test User",
                            "email": "test@example.com",
                            "address": "123 Test St",
                            "phone": "+1-555-0123"
                        }

                        mock_get_sub.return_value = {
                            "id": subscription_id,
                            "plan_id": "pro_monthly",
                            "status": "active",
                            "billing_cycle": "monthly"
                        }

                        mock_get_plan.return_value = {
                            "id": "pro_monthly",
                            "name": "Professional Plan",
                            "type": "pro",
                            "price": 29.0,
                            "billing_cycle": "monthly"
                        }

                        mock_save.return_value = {
                            "id": "inv_123",
                            "status": "draft"
                        }

                        invoice = await invoice_generator.generate_monthly_invoice(
                            user_id=user_id,
                            subscription_id=subscription_id,
                            period_start=period_start,
                            period_end=period_end
                        )

        assert invoice is not None
        assert invoice["user_id"] == user_id
        assert invoice["subscription_id"] == subscription_id
        assert invoice["amounts"]["subtotal"] == 29.0
        assert invoice["amounts"]["tax_amount"] == 2.32  # 8% tax
        assert invoice["amounts"]["total_amount"] == 31.32
        assert invoice["status"] == "draft"

    @pytest.mark.asyncio
    async def test_generate_usage_invoice(self, invoice_generator):
        """测试生成使用量发票"""
        user_id = "test_user_123"
        usage_data = {
            "api_calls": 15000,
            "api_call_rate": 0.001,
            "api_calls_cost": 15.0,
            "tokens": 500000,
            "token_rate": 0.000002,
            "tokens_cost": 1.0,
            "storage_gb": 150,
            "storage_rate": 0.1,
            "storage_cost": 15.0
        }

        with patch.object(invoice_generator, '_get_user') as mock_get_user:
            with patch.object(invoice_generator, '_save_invoice') as mock_save:

                mock_get_user.return_value = {
                    "id": user_id,
                    "name": "Test User",
                    "email": "test@example.com"
                }

                mock_save.return_value = {
                    "id": "inv_usage_123",
                    "status": "draft"
                }

                invoice = await invoice_generator.generate_usage_invoice(
                    user_id=user_id,
                    usage_data=usage_data,
                    description="Overage Usage Charges"
                )

        assert invoice is not None
        assert invoice["user_id"] == user_id
        assert invoice["description"] == "Overage Usage Charges"
        assert len(invoice["line_items"]) == 3  # API calls, tokens, storage
        assert invoice["amounts"]["subtotal"] == 31.0  # 15 + 1 + 15
        assert invoice["amounts"]["total_amount"] == 33.48  # 31 + 8% tax

    @pytest.mark.asyncio
    async def test_generate_credit_invoice(self, invoice_generator):
        """测试生成信用发票"""
        user_id = "test_user_123"
        amount = -10.0
        reason = "Service credit for downtime"

        with patch.object(invoice_generator, '_get_user') as mock_get_user:
            with patch.object(invoice_generator, '_save_invoice') as mock_save:

                mock_get_user.return_value = {
                    "id": user_id,
                    "name": "Test User",
                    "email": "test@example.com"
                }

                mock_save.return_value = {
                    "id": "inv_credit_123",
                    "status": "draft"
                }

                invoice = await invoice_generator.generate_credit_invoice(
                    user_id=user_id,
                    amount=amount,
                    reason=reason,
                    related_invoice_id="inv_123"
                )

        assert invoice is not None
        assert invoice["user_id"] == user_id
        assert invoice["description"] == reason
        assert invoice["amounts"]["total_amount"] == -10.0
        assert invoice["amounts"]["tax_amount"] == 0.0  # 退款不计税
        assert invoice["related_invoice_id"] == "inv_123"


class TestStripeProcessor:
    """Stripe处理器测试"""

    @pytest.fixture
    def stripe_processor(self):
        """创建Stripe处理器实例"""
        with patch('backend.core.billing.payments.stripe_processor.stripe'):
            return StripeProcessor(
                api_key="sk_test_123",
                webhook_secret="whsec_123"
            )

    @pytest.mark.asyncio
    async def test_create_payment_intent(self, stripe_processor):
        """测试创建支付意图"""
        with patch('backend.core.billing.payments.stripe_processor.stripe.PaymentIntent.create') as mock_create:
            # Mock Stripe响应
            mock_create.return_value = {
                "id": "pi_123",
                "status": "requires_payment_method",
                "amount": 2999,
                "currency": "usd",
                "client_secret": "pi_123_secret_123"
            }

            result = await stripe_processor.create_payment_intent(
                amount=29.99,
                currency=Currency.USD,
                payment_method_id="pm_123"
            )

        assert result.success is True
        assert result.payment_intent_id == "pi_123"
        assert result.provider_transaction_id == "pi_123"
        assert result.status == PaymentStatus.PENDING
        assert result.amount == 29.99
        assert result.currency == Currency.USD
        assert result.client_secret == "pi_123_secret_123"

    @pytest.mark.asyncio
    async def test_confirm_payment_intent(self, stripe_processor):
        """测试确认支付意图"""
        with patch('backend.core.billing.payments.stripe_processor.stripe.PaymentIntent.retrieve') as mock_retrieve:
            with patch('backend.core.billing.payments.stripe_processor.stripe.PaymentIntent.confirm') as mock_confirm:

                # Mock Stripe响应
                mock_retrieve.return_value = {
                    "id": "pi_123",
                    "status": "requires_confirmation",
                    "amount": 2999,
                    "currency": "usd"
                }

                mock_confirm.return_value = {
                    "id": "pi_123",
                    "status": "succeeded",
                    "charges": {
                        "data": [{
                            "id": "ch_123",
                            "balance_transaction": {
                                "fee": 87,
                                "net": 2912
                            }
                        }]
                    }
                }

                result = await stripe_processor.confirm_payment_intent(
                    payment_intent_id="pi_123",
                    payment_method_id="pm_123"
                )

        assert result.success is True
        assert result.payment_intent_id == "pi_123"
        assert result.status == PaymentStatus.COMPLETED
        assert result.amount == 29.99
        assert result.fee_amount == 0.87
        assert result.net_amount == 29.12

    @pytest.mark.asyncio
    async def test_create_subscription(self, stripe_processor):
        """测试创建订阅"""
        with patch('backend.core.billing.payments.stripe_processor.stripe.Subscription.create') as mock_create:

            # Mock Stripe响应
            mock_create.return_value = {
                "id": "sub_123",
                "status": "trialing",
                "current_period_start": 1640995200,  # 2022-01-01
                "current_period_end": 1643587200,    # 2022-01-31
                "trial_start": 1640995200,
                "trial_end": 1641600000,             # 2022-01-08
                "created": 1640995200,
                "start_date": 1640995200,
                "metadata": {}
            }

            subscription = await stripe_processor.create_subscription(
                customer_id="cus_123",
                price_id="price_123",
                trial_period_days=7
            )

        assert subscription.id == "sub_123"
        assert subscription.provider_subscription_id == "sub_123"
        assert subscription.provider == PaymentProvider.STRIPE
        assert subscription.status == "trialing"
        assert subscription.cancel_at_period_end is False

    @pytest.mark.asyncio
    async def test_handle_webhook(self, stripe_processor):
        """测试处理webhook"""
        payload = b'{"id": "evt_123", "type": "payment_intent.succeeded", "data": {"object": {"id": "pi_123"}}}'
        signature = "v1=12345"

        with patch('backend.core.billing.payments.stripe_processor.stripe.Webhook.construct_event') as mock_construct:

            # Mock Stripe webhook验证
            mock_event = Mock()
            mock_event.id = "evt_123"
            mock_event.type = "payment_intent.succeeded"
            mock_event.created = 1640995200
            mock_event.data.to_dict.return_value = {"id": "pi_123"}
            mock_construct.return_value = mock_event

            result = await stripe_processor.handle_webhook(payload, signature)

        assert result["event_id"] == "evt_123"
        assert result["type"] == "payment_intent.succeeded"
        assert "data" in result
        assert "created" in result


class TestBillingService:
    """计费服务测试"""

    @pytest.fixture
    def billing_service(self):
        """创建计费服务实例"""
        config = BillingConfig(
            stripe_enabled=True,
            stripe_api_key="sk_test_123",
            paypal_enabled=False
        )
        with patch('backend.core.billing.billing_service.StripeProcessor'):
            with patch('backend.core.billing.billing_service.CacheManager'):
                return BillingService(config)

    @pytest.mark.asyncio
    async def test_create_subscription(self, billing_service):
        """测试创建订阅"""
        user_id = "test_user_123"
        plan_type = PlanType.PRO
        billing_cycle = BillingCycle.MONTHLY
        payment_provider = PaymentProvider.STRIPE

        # Mock依赖方法
        with patch.object(billing_service.pricing_manager, 'get_plan') as mock_get_plan:
            with patch.object(billing_service.pricing_manager, 'create_subscription') as mock_create_sub:
                with patch.object(billing_service, '_get_or_create_stripe_customer') as mock_customer:
                    with patch.object(billing_service.stripe_processor, 'create_price') as mock_price:
                        with patch.object(billing_service.stripe_processor, 'create_subscription') as mock_stripe_sub:
                            with patch.object(billing_service.quota_manager, 'upgrade_user_plan') as mock_upgrade:

                                # Mock返回数据
                                mock_plan = Mock()
                                mock_plan.id = "plan_123"
                                mock_plan.name = "Pro Plan"
                                mock_plan.description = "Professional plan"
                                mock_plan.trial_days = 14
                                mock_plan.price = 29.99
                                mock_get_plan.return_value = mock_plan

                                mock_subscription = Mock()
                                mock_subscription.id = "sub_123"
                                mock_subscription.status.value = "active"
                                mock_subscription.current_period_start = datetime.now(timezone.utc)
                                mock_subscription.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
                                mock_create_sub.return_value = mock_subscription

                                mock_customer.return_value = "cus_123"

                                mock_stripe_subscription = Mock()
                                mock_stripe_subscription.to_dict.return_value = {"id": "sub_stripe_123"}
                                mock_stripe_sub.return_value = mock_stripe_subscription

                                result = await billing_service.create_subscription(
                                    user_id=user_id,
                                    plan_type=plan_type,
                                    billing_cycle=billing_cycle,
                                    payment_provider=payment_provider
                                )

        assert result["subscription_id"] == "sub_123"
        assert result["user_id"] == user_id
        assert result["plan_type"] == plan_type.value
        assert result["billing_cycle"] == billing_cycle.value
        assert result["provider"] == payment_provider.value
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_track_usage(self, billing_service):
        """测试跟踪使用量"""
        user_id = "test_user_123"
        usage_type = UsageType.API_CALL

        with patch.object(billing_service.usage_tracker, 'track_usage') as mock_track:
            with patch.object(billing_service.quota_manager, 'check_quota_violation') as mock_check:
                with patch.object(billing_service.quota_manager, 'record_quota_violation') as mock_record:

                    # Mock使用记录
                    mock_usage_record = Mock()
                    mock_usage_record.id = "usage_123"
                    mock_usage_record.cost = 0.01
                    mock_usage_record.is_successful = True
                    mock_track.return_value = mock_usage_record

                    # Mock配额检查
                    mock_check.return_value = None

                    result = await billing_service.track_usage(
                        user_id=user_id,
                        usage_type=usage_type,
                        model="gpt-3.5-turbo",
                        input_tokens=100,
                        output_tokens=50
                    )

        assert result["usage_record_id"] == "usage_123"
        assert result["cost"] == 0.01
        assert result["successful"] is True
        assert result["quota_violation"] is None
        assert result["message"] == "Usage tracked successfully"

    @pytest.mark.asyncio
    async def test_get_billing_summary(self, billing_service):
        """测试获取计费摘要"""
        user_id = "test_user_123"

        with patch.object(billing_service.pricing_manager, 'get_user_subscriptions') as mock_subscriptions:
            with patch.object(billing_service, 'get_usage_stats') as mock_usage:
                with patch.object(billing_service, 'get_quota_status') as mock_quota:

                    # Mock订阅数据
                    mock_subscription = Mock()
                    mock_subscription.plan.type.value = "pro"
                    mock_subscription.status.value = "active"
                    mock_subscription.current_period_end = datetime.now(timezone.utc) + timedelta(days=15)
                    mock_subscription.days_until_renewal = 15
                    mock_subscriptions.return_value = [mock_subscription]

                    # Mock使用量统计
                    mock_stats = Mock()
                    mock_stats.total_requests = 1000
                    mock_stats.total_tokens = 50000
                    mock_stats.total_cost = 10.0
                    mock_stats.successful_requests = 950
                    mock_stats.failed_requests = 50
                    mock_usage.return_value = mock_stats

                    # Mock配额状态
                    mock_quota.return_value = {
                        "plan_type": "pro",
                        "api_calls": {"used": 1000, "limit": 10000, "remaining": 9000}
                    }

                    result = await billing_service.get_billing_summary(user_id)

        assert result["user_id"] == user_id
        assert result["current_subscription"]["plan_type"] == "pro"
        assert result["current_subscription"]["status"] == "active"
        assert result["usage_this_month"]["total_requests"] == 1000
        assert result["usage_this_month"]["total_cost"] == 10.0
        assert result["quota_status"]["plan_type"] == "pro"


# API端点测试

class TestBillingAPI:
    """计费API测试"""

    @pytest.mark.asyncio
    async def test_create_subscription_api(self, client, mock_current_user):
        """测试创建订阅API"""
        request_data = {
            "plan_type": "pro",
            "billing_cycle": "monthly",
            "payment_provider": "stripe",
            "payment_method_id": "pm_123"
        }

        with patch('backend.api.v1.billing.get_billing_service') as mock_get_service:
            with patch.object(mock_get_service.return_value, 'create_subscription') as mock_create:

                mock_create.return_value = {
                    "subscription_id": "sub_123",
                    "user_id": "test_user",
                    "plan_type": "pro",
                    "billing_cycle": "monthly",
                    "provider": "stripe",
                    "status": "active",
                    "current_period_start": "2024-01-01T00:00:00Z",
                    "current_period_end": "2024-02-01T00:00:00Z"
                }

                response = await client.post(
                    "/api/v1/billing/subscriptions",
                    json=request_data,
                    headers={"Authorization": "Bearer test_token"}
                )

        assert response.status_code == 200
        data = response.json()
        assert data["subscription_id"] == "sub_123"
        assert data["plan_type"] == "pro"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_track_usage_api(self, client, mock_current_user):
        """测试使用量跟踪API"""
        request_data = {
            "usage_type": "api_call",
            "model": "gpt-3.5-turbo",
            "input_tokens": 100,
            "output_tokens": 50,
            "status_code": 200
        }

        with patch('backend.api.v1.billing.get_billing_service') as mock_get_service:
            with patch.object(mock_get_service.return_value, 'track_usage') as mock_track:

                mock_track.return_value = {
                    "usage_record_id": "usage_123",
                    "cost": 0.01,
                    "successful": True,
                    "quota_violation": None,
                    "message": "Usage tracked successfully"
                }

                response = await client.post(
                    "/api/v1/billing/usage/track",
                    json=request_data,
                    headers={"Authorization": "Bearer test_token"}
                )

        assert response.status_code == 200
        data = response.json()
        assert data["usage_record_id"] == "usage_123"
        assert data["successful"] is True
        assert data["cost"] == 0.01

    @pytest.mark.asyncio
    async def test_get_billing_summary_api(self, client, mock_current_user):
        """测试获取计费摘要API"""
        with patch('backend.api.v1.billing.get_billing_service') as mock_get_service:
            with patch.object(mock_get_service.return_value, 'get_billing_summary') as mock_summary:

                mock_summary.return_value = {
                    "user_id": "test_user",
                    "current_subscription": {
                        "plan_type": "pro",
                        "status": "active",
                        "days_until_renewal": 15
                    },
                    "usage_this_month": {
                        "total_requests": 1000,
                        "total_cost": 10.0
                    },
                    "quota_status": {
                        "plan_type": "pro"
                    },
                    "billing_period": {
                        "start": "2024-01-01T00:00:00Z",
                        "end": "2024-01-31T23:59:59Z"
                    }
                }

                response = await client.get(
                    "/api/v1/billing/summary",
                    headers={"Authorization": "Bearer test_token"}
                )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test_user"
        assert data["current_subscription"]["plan_type"] == "pro"
        assert data["usage_this_month"]["total_requests"] == 1000
        assert data["usage_this_month"]["total_cost"] == 10.0

    @pytest.mark.asyncio
    async def test_get_pricing_plans_api(self, client):
        """测试获取价格计划API"""
        with patch('backend.api.v1.billing.get_billing_service') as mock_get_service:
            with patch.object(mock_get_service.return_value.pricing_manager, 'get_all_plans') as mock_plans:

                mock_plans.return_value = [
                    Mock(
                        to_dict=lambda: {
                            "id": "plan_free",
                            "name": "Free Plan",
                            "type": "free",
                            "price": 0.0,
                            "currency": "USD"
                        }
                    ),
                    Mock(
                        to_dict=lambda: {
                            "id": "plan_pro",
                            "name": "Pro Plan",
                            "type": "pro",
                            "price": 29.99,
                            "currency": "USD"
                        }
                    )
                ]

                response = await client.get("/api/v1/billing/plans")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["plans"]) == 2
        assert data["plans"][0]["type"] == "free"
        assert data["plans"][1]["type"] == "pro"

    @pytest.mark.asyncio
    async def test_webhook_stripe_api(self, client):
        """测试Stripe webhook API"""
        payload = b'{"id": "evt_123", "type": "payment_intent.succeeded"}'
        headers = {"stripe-signature": "v1=12345"}

        with patch('backend.api.v1.billing.get_billing_service') as mock_get_service:
            with patch.object(mock_get_service.return_value, 'handle_webhook') as mock_webhook:

                mock_webhook.return_value = {
                    "status": "success",
                    "result": {"event_id": "evt_123"}
                }

                response = await client.post(
                    "/api/v1/billing/webhooks/stripe",
                    data=payload,
                    headers=headers
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["result"]["event_id"] == "evt_123"


# 集成测试

class TestBillingIntegration:
    """计费系统集成测试"""

    @pytest.mark.asyncio
    async def test_complete_subscription_flow(self):
        """测试完整的订阅流程"""
        # 创建计费服务
        config = BillingConfig(stripe_enabled=False, paypal_enabled=False)
        billing_service = BillingService(config)

        user_id = "test_user_123"

        # 1. 创建价格计划
        plan = await billing_service.pricing_manager.create_plan(
            name="Test Pro Plan",
            type=PlanType.PRO,
            billing_cycle=BillingCycle.MONTHLY,
            price=29.99
        )

        # 2. 创建订阅
        subscription = await billing_service.pricing_manager.create_subscription(
            user_id=user_id,
            plan_id=plan.id,
            billing_cycle=BillingCycle.MONTHLY
        )

        assert subscription.user_id == user_id
        assert subscription.plan_id == plan.id
        assert subscription.is_active is True

        # 3. 跟踪使用量
        for i in range(10):
            await billing_service.track_usage(
                user_id=user_id,
                usage_type=UsageType.API_CALL,
                model="gpt-3.5-turbo",
                input_tokens=100,
                output_tokens=50,
                status_code=200
            )

        # 4. 获取使用量统计
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        stats = await billing_service.get_usage_stats(
            user_id=user_id,
            start_date=month_start,
            end_date=now
        )

        assert stats.total_requests == 10
        assert stats.successful_requests == 10
        assert stats.failed_requests == 0
        assert stats.total_cost > 0

        # 5. 获取计费摘要
        summary = await billing_service.get_billing_summary(user_id)

        assert summary["user_id"] == user_id
        assert summary["current_subscription"]["plan_type"] == "pro"
        assert summary["usage_this_month"]["total_requests"] == 10

        # 6. 生成发票
        invoice = await billing_service.generate_invoice(
            user_id=user_id,
            invoice_type="monthly"
        )

        assert invoice is not None
        assert invoice["user_id"] == user_id

        # 7. 取消订阅
        await billing_service.pricing_manager.cancel_subscription(
            subscription_id=subscription.id,
            at_period_end=False
        )

        cancelled_subscription = await billing_service.pricing_manager.get_subscription(subscription.id)
        assert cancelled_subscription.status.value == "cancelled"

    @pytest.mark.asyncio
    async def test_quota_enforcement_flow(self):
        """测试配额执行流程"""
        # 创建配额管理器
        cache_manager = Mock(spec=CacheManager)
        quota_manager = QuotaManager(cache_manager)

        user_id = "test_user_123"

        # 设置配额限制
        quota_limit = 100

        # 模拟接近配额限制的使用
        current_usage = 95
        requested_amount = 10

        with patch.object(quota_manager, '_get_current_usage', return_value=current_usage):
            with patch.object(quota_manager, '_get_quota_limit', return_value=quota_limit):
                with patch.object(quota_manager, '_save_violation_to_db') as mock_save:

                    # 检查配额违规
                    violation = await quota_manager.check_quota_violation(
                        user_id=user_id,
                        quota_type=QuotaType.API_CALLS,
                        amount=requested_amount
                    )

                    assert violation is not None
                    assert violation.user_id == user_id
                    assert violation.current_usage == current_usage
                    assert violation.limit == quota_limit
                    assert violation.requested_amount == requested_amount
                    assert violation.would_exceed_by == 5

                    # 记录违规
                    await quota_manager.record_quota_violation(violation)
                    mock_save.assert_called_once_with(violation)

    @pytest.mark.asyncio
    async def test_payment_webhook_processing(self):
        """测试支付webhook处理"""
        # 创建webhook处理器
        webhook_handler = PaymentWebhookHandler()

        # 模拟Stripe支付成功事件
        stripe_payload = {
            "id": "evt_123",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_123",
                    "amount": 2999,
                    "currency": "usd",
                    "metadata": {
                        "user_id": "test_user_123",
                        "subscription_id": "sub_123"
                    }
                }
            }
        }

        # Mock Stripe处理器
        stripe_processor = Mock(spec=StripeProcessor)
        stripe_processor.handle_webhook = AsyncMock(return_value=stripe_payload)

        webhook_handler.stripe_processor = stripe_processor

        # 处理webhook
        result = await webhook_handler.handle_webhook(
            provider=PaymentProvider.STRIPE,
            payload=json.dumps(stripe_payload).encode(),
            headers={},
            signature="mock_signature"
        )

        assert result["status"] == "processed"
        assert result["event_type"] == "payment_intent.succeeded"
        assert "result" in result


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])