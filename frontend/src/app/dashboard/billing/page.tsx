'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface Plan {
  id: string;
  name: string;
  slug: string;
  description: string;
  price: number;
  currency: string;
  billing_cycle: 'monthly' | 'yearly';
  features: Record<string, any>;
  api_quota: number;
  rate_limit: number;
  max_teams: number;
  max_users: number;
  is_active: boolean;
  is_popular: boolean;
  sort_order: number;
}

interface Subscription {
  id: string;
  organization_id: string;
  plan_id: string;
  status: string;
  current_period_start: string;
  current_period_end: string;
  trial_start?: string;
  trial_end?: string;
  canceled_at?: string;
  cancel_at_period_end: boolean;
  plan?: Plan;
}

export default function BillingPage() {
  const router = useRouter();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [currentSubscription, setCurrentSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [paymentForm, setPaymentForm] = useState({
    cardNumber: '',
    expiryMonth: '',
    expiryYear: '',
    cvc: '',
    cardholderName: '',
    cardType: 'visa'
  });
  const [processingPayment, setProcessingPayment] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchPlans();
    fetchCurrentSubscription();
  }, []);

  useEffect(() => {
    fetchPlans();
  }, [billingCycle]);

  const fetchPlans = async () => {
    try {
      const response = await fetch('/api/v1/payments/plans');
      if (response.ok) {
        const data = await response.json();
        setPlans(data.data.plans.filter((plan: Plan) =>
          plan.billing_cycle === billingCycle && plan.is_active
        ));
      }
    } catch (error) {
      console.error('Error fetching plans:', error);
    }
  };

  const fetchCurrentSubscription = async () => {
    try {
      const response = await fetch('/api/v1/payments/subscription-status');
      if (response.ok) {
        const data = await response.json();
        if (data.data.has_active_subscription && data.data.subscription) {
          setCurrentSubscription(data.data.subscription);
        }
      }
    } catch (error) {
      console.error('Error fetching subscription:', error);
    }
    setLoading(false);
  };

  const handleSelectPlan = (plan: Plan) => {
    if (currentSubscription && currentSubscription.status === 'active') {
      // 已有订阅，显示升级/降级确认
      setSelectedPlan(plan);
      setShowUpgradeModal(true);
    } else {
      // 新订阅，显示支付表单
      setSelectedPlan(plan);
      setShowPaymentModal(true);
    }
  };

  const handlePaymentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setProcessingPayment(true);
    setError('');
    setSuccess('');

    try {
      if (!selectedPlan) {
        throw new Error('No plan selected');
      }

      // 创建支付意图
      const paymentIntentResponse = await fetch('/api/v1/payments/intents', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          amount: selectedPlan.price,
          currency: selectedPlan.currency,
          description: `${selectedPlan.name} - ${selectedPlan.billing_cycle} subscription`
        })
      });

      if (!paymentIntentResponse.ok) {
        throw new Error('Failed to create payment intent');
      }

      const paymentIntentData = await paymentIntentResponse.json();

      // 确认支付
      const confirmResponse = await fetch('/api/v1/payments/confirm', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          payment_intent_id: paymentIntentData.data.id,
          card_number: paymentForm.cardNumber,
          expiry_month: parseInt(paymentForm.expiryMonth),
          expiry_year: parseInt(paymentForm.expiryYear),
          cvc: paymentForm.cvc,
          cardholder_name: paymentForm.cardholderName
        })
      });

      const confirmData = await confirmResponse.json();

      if (confirmData.success) {
        // 创建订阅
        const subscriptionResponse = await fetch('/api/v1/payments/subscriptions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            plan_id: selectedPlan.id,
            trial_days: selectedPlan.price === 0 ? 0 : 14 // 免费套餐无试用，付费套餐14天试用
          })
        });

        if (subscriptionResponse.ok) {
          setSuccess('订阅创建成功！');
          setShowPaymentModal(false);
          setPaymentForm({
            cardNumber: '',
            expiryMonth: '',
            expiryYear: '',
            cvc: '',
            cardholderName: '',
            cardType: 'visa'
          });
          fetchCurrentSubscription();
        } else {
          throw new Error('Failed to create subscription');
        }
      } else {
        throw new Error(confirmData.error?.message || 'Payment failed');
      }

    } catch (err: any) {
      setError(err.message || 'Payment failed');
    } finally {
      setProcessingPayment(false);
    }
  };

  const handleUpgrade = async () => {
    if (!selectedPlan || !currentSubscription) return;

    setProcessingPayment(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`/api/v1/payments/subscriptions/${currentSubscription.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          plan_id: selectedPlan.id
        })
      });

      if (response.ok) {
        setSuccess('套餐升级成功！');
        setShowUpgradeModal(false);
        fetchCurrentSubscription();
        fetchPlans();
      } else {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to update subscription');
      }

    } catch (err: any) {
      setError(err.message || 'Failed to update subscription');
    } finally {
      setProcessingPayment(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!currentSubscription) return;

    if (!confirm('确定要取消订阅吗？取消后将在当前计费期结束时停止服务。')) {
      return;
    }

    setProcessingPayment(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`/api/v1/payments/subscriptions/${currentSubscription.id}/cancel?at_period_end=true`, {
        method: 'POST',
      });

      if (response.ok) {
        setSuccess('订阅已设置在当前计费期结束时取消');
        fetchCurrentSubscription();
      } else {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to cancel subscription');
      }

    } catch (err: any) {
      setError(err.message || 'Failed to cancel subscription');
    } finally {
      setProcessingPayment(false);
    }
  };

  const handleReactivateSubscription = async () => {
    if (!currentSubscription) return;

    setProcessingPayment(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`/api/v1/payments/subscriptions/${currentSubscription.id}/reactivate`, {
        method: 'POST',
      });

      if (response.ok) {
        setSuccess('订阅已重新激活');
        fetchCurrentSubscription();
      } else {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to reactivate subscription');
      }

    } catch (err: any) {
      setError(err.message || 'Failed to reactivate subscription');
    } finally {
      setProcessingPayment(false);
    }
  };

  const detectCardType = (cardNumber: string) => {
    const patterns = {
      visa: /^4/,
      mastercard: /^5[1-5]/,
      amex: /^3[47]/,
      discover: /^6(?:011|5)/,
    };

    for (const [type, pattern] of Object.entries(patterns)) {
      if (pattern.test(cardNumber)) {
        return type;
      }
    }
    return 'visa';
  };

  const formatCardNumber = (value: string) => {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    const matches = v.match(/\d{4,16}/g);
    const match = matches && matches[0] || '';
    const parts = [];

    for (let i = 0, len = match.length; i < len; i += 4) {
      parts.push(match.substring(i, i + 4));
    }

    if (parts.length) {
      return parts.join(' ');
    } else {
      return v;
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-96 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">计费与订阅</h1>
        <p className="mt-2 text-gray-600">管理您的订阅套餐，查看使用情况和账单</p>
      </div>

      {/* 当前订阅状态 */}
      {currentSubscription && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-blue-900">当前订阅</h2>
              <p className="text-blue-700 mt-1">
                {currentSubscription.plan?.name} - {currentSubscription.plan?.billing_cycle}
              </p>
              <p className="text-sm text-blue-600 mt-2">
                状态: <span className="font-medium">
                  {currentSubscription.status === 'active' ? '活跃' :
                   currentSubscription.status === 'trialing' ? '试用中' :
                   currentSubscription.status === 'canceled' ? '已取消' : currentSubscription.status}
                </span>
                {currentSubscription.cancel_at_period_end && (
                  <span className="ml-2">（将在计费期结束时取消）</span>
                )}
              </p>
              {currentSubscription.current_period_end && (
                <p className="text-sm text-blue-600">
                  下次计费: {new Date(currentSubscription.current_period_end).toLocaleDateString()}
                </p>
              )}
            </div>
            <div className="flex items-center space-x-3">
              {currentSubscription.cancel_at_period_end ? (
                <button
                  onClick={handleReactivateSubscription}
                  disabled={processingPayment}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  重新激活
                </button>
              ) : (
                <button
                  onClick={handleCancelSubscription}
                  disabled={processingPayment}
                  className="px-4 py-2 border border-red-300 text-red-700 rounded-md hover:bg-red-50 disabled:opacity-50"
                >
                  取消订阅
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 错误和成功消息 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
          <p className="text-green-800">{success}</p>
        </div>
      )}

      {/* 计费周期切换 */}
      <div className="flex justify-center mb-8">
        <div className="bg-gray-100 rounded-lg p-1 inline-flex">
          <button
            onClick={() => setBillingCycle('monthly')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              billingCycle === 'monthly'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            月付
          </button>
          <button
            onClick={() => setBillingCycle('yearly')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              billingCycle === 'yearly'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            年付 (省20%)
          </button>
        </div>
      </div>

      {/* 套餐选择 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={`relative rounded-lg border-2 p-6 transition-all ${
              plan.is_popular
                ? 'border-blue-500 shadow-lg'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            {plan.is_popular && (
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                <span className="bg-blue-500 text-white px-3 py-1 rounded-full text-sm font-medium">
                  最受欢迎
                </span>
              </div>
            )}

            <div className="text-center mb-6">
              <h3 className="text-xl font-semibold text-gray-900">{plan.name}</h3>
              <div className="mt-4">
                <span className="text-4xl font-bold text-gray-900">
                  ${plan.price}
                </span>
                <span className="text-gray-600">
                  /{plan.billing_cycle === 'monthly' ? '月' : '年'}
                </span>
              </div>
              <p className="text-sm text-gray-600 mt-2">{plan.description}</p>
            </div>

            <div className="space-y-3 mb-6">
              {Object.entries(plan.features).map(([key, value]) => (
                <div key={key} className="flex items-center">
                  <svg
                    className={`w-5 h-5 mr-3 ${
                      value ? 'text-green-500' : 'text-gray-400'
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d={value ? "M5 13l4 4L19 7" : "M6 18L18 6M6 6l12 12"}
                    />
                  </svg>
                  <span className="text-sm text-gray-700">
                    {typeof value === 'boolean'
                      ? (value ? '已包含' : '不包含')
                      : (typeof value === 'string' ? value : JSON.stringify(value))
                    }
                  </span>
                </div>
              ))}
              <div className="flex items-center">
                <span className="text-sm text-gray-700">
                  {plan.api_quota.toLocaleString()} API调用/月
                </span>
              </div>
              <div className="flex items-center">
                <span className="text-sm text-gray-700">
                  {plan.rate_limit} 请求/分钟
                </span>
              </div>
              <div className="flex items-center">
                <span className="text-sm text-gray-700">
                  最多 {plan.max_teams} 个团队
                </span>
              </div>
              <div className="flex items-center">
                <span className="text-sm text-gray-700">
                  最多 {plan.max_users} 个用户
                </span>
              </div>
            </div>

            <button
              onClick={() => handleSelectPlan(plan)}
              className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
                currentSubscription?.plan_id === plan.id
                  ? 'bg-gray-100 text-gray-700 cursor-not-allowed'
                  : plan.is_popular
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-800 text-white hover:bg-gray-900'
              }`}
              disabled={currentSubscription?.plan_id === plan.id}
            >
              {currentSubscription?.plan_id === plan.id
                ? '当前套餐'
                : currentSubscription
                ? (plan.price > (currentSubscription.plan?.price || 0) ? '升级' : '降级')
                : '选择套餐'
              }
            </button>
          </div>
        ))}
      </div>

      {/* 支付模态框 */}
      {showPaymentModal && selectedPlan && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900">
                订阅 {selectedPlan.name}
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                ${selectedPlan.price}/{selectedPlan.billing_cycle === 'monthly' ? '月' : '年'}
              </p>

              <form onSubmit={handlePaymentSubmit} className="mt-4 space-y-4">
                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-md p-3">
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    持卡人姓名
                  </label>
                  <input
                    type="text"
                    value={paymentForm.cardholderName}
                    onChange={(e) => setPaymentForm({...paymentForm, cardholderName: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="John Doe"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    信用卡号
                  </label>
                  <input
                    type="text"
                    value={paymentForm.cardNumber}
                    onChange={(e) => {
                      const formatted = formatCardNumber(e.target.value);
                      setPaymentForm({
                        ...paymentForm,
                        cardNumber: formatted,
                        cardType: detectCardType(formatted.replace(/\s/g, ''))
                      });
                    }}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="4242 4242 4242 4242"
                    maxLength={19}
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      到期月份
                    </label>
                    <input
                      type="text"
                      value={paymentForm.expiryMonth}
                      onChange={(e) => setPaymentForm({...paymentForm, expiryMonth: e.target.value})}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      placeholder="12"
                      maxLength={2}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      到期年份
                    </label>
                    <input
                      type="text"
                      value={paymentForm.expiryYear}
                      onChange={(e) => setPaymentForm({...paymentForm, expiryYear: e.target.value})}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      placeholder="2025"
                      maxLength={4}
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    安全码 (CVC)
                  </label>
                  <input
                    type="text"
                    value={paymentForm.cvc}
                    onChange={(e) => setPaymentForm({...paymentForm, cvc: e.target.value})}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="123"
                    maxLength={4}
                    required
                  />
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
                  <p className="text-sm text-yellow-800">
                    <strong>测试模式:</strong> 这是模拟支付系统，不会产生真实费用。
                    使用卡号 4242424242424242 可以成功支付。
                  </p>
                </div>

                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowPaymentModal(false)}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    disabled={processingPayment}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    {processingPayment ? '处理中...' : `支付 $${selectedPlan.price}`}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* 升级/降级确认模态框 */}
      {showUpgradeModal && selectedPlan && currentSubscription && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900">
                确认套餐变更
              </h3>
              <div className="mt-4">
                <p className="text-sm text-gray-600">
                  当前套餐: <span className="font-medium">{currentSubscription.plan?.name}</span>
                </p>
                <p className="text-sm text-gray-600">
                  新套餐: <span className="font-medium">{selectedPlan.name}</span>
                </p>
                <p className="text-sm text-gray-600">
                  新价格: <span className="font-medium">${selectedPlan.price}/{selectedPlan.billing_cycle === 'monthly' ? '月' : '年'}</span>
                </p>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-md p-3 mt-4">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  onClick={() => setShowUpgradeModal(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  onClick={handleUpgrade}
                  disabled={processingPayment}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {processingPayment ? '处理中...' : '确认变更'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}