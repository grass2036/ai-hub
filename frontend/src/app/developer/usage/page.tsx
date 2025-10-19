'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

// 类型定义
interface UsageOverview {
  period_days: number;
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  unique_models: number;
  avg_response_time: number;
  success_rate: number;
  daily_stats: Record<string, {
    requests: number;
    tokens: number;
    cost: number;
    unique_models: number;
  }>;
  model_breakdown: Record<string, {
    requests: number;
    tokens: number;
    cost: number;
    avg_response_time: number;
    success_rate: number;
  }>;
  error_breakdown: Record<string, number>;
}

interface BillingOverview {
  current_month_cost: number;
  last_month_cost: number;
  total_unpaid: number;
  upcoming_payment: number;
  payment_method: string;
  next_billing_date: string;
  credit_balance: number;
  subscription_status: string;
}

interface PricingInfo {
  models: Record<string, {
    name: string;
    provider: string;
    input_price: number;
    output_price: number;
    currency: string;
    tier: string;
  }>;
}

export default function DeveloperUsage() {
  const router = useRouter();
  const [usageData, setUsageData] = useState<UsageOverview | null>(null);
  const [billingData, setBillingData] = useState<BillingOverview | null>(null);
  const [pricingData, setPricingData] = useState<PricingInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedPeriod, setSelectedPeriod] = useState(30);
  const [activeTab, setActiveTab] = useState<'usage' | 'billing' | 'pricing'>('usage');

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('developer_access_token');

      if (!token) {
        router.push('/developer/login');
        return;
      }

      try {
        // 并行获取所有数据
        const [usageRes, billingRes, pricingRes] = await Promise.all([
          fetch(`/api/v1/developer/usage/overview?days=${selectedPeriod}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch('/api/v1/developer/usage/billing/overview', {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch('/api/v1/developer/usage/billing/pricing', {
            headers: { 'Authorization': `Bearer ${token}` }
          })
        ]);

        if (usageRes.ok) {
          const usageResult = await usageRes.json();
          setUsageData(usageResult.data);
        }

        if (billingRes.ok) {
          const billingResult = await billingRes.json();
          setBillingData(billingResult.data);
        }

        if (pricingRes.ok) {
          const pricingResult = await pricingRes.json();
          setPricingData(pricingResult.data);
        }

      } catch (err) {
        setError('加载数据失败');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [router, selectedPeriod]);

  const handlePeriodChange = (days: number) => {
    setSelectedPeriod(days);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">加载失败</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航栏 */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link href="/developer" className="text-blue-600 hover:text-blue-800">
                ← 返回控制台
              </Link>
              <h1 className="ml-4 text-xl font-bold text-gray-900">
                使用量统计与计费
              </h1>
            </div>
          </div>
        </div>
      </nav>

      {/* 主要内容 */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* 标签页导航 */}
        <div className="bg-white shadow rounded-lg mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8 px-6">
              {[
                { id: 'usage', label: '使用量统计', icon: '📊' },
                { id: 'billing', label: '账单信息', icon: '💳' },
                { id: 'pricing', label: '价格方案', icon: '💰' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* 使用量统计标签页 */}
        {activeTab === 'usage' && usageData && (
          <>
            {/* 时间周期选择 */}
            <div className="bg-white shadow rounded-lg mb-6">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">选择统计周期</h3>
                <div className="flex space-x-2">
                  {[7, 30, 60, 90].map((days) => (
                    <button
                      key={days}
                      onClick={() => handlePeriodChange(days)}
                      className={`px-4 py-2 rounded-lg ${
                        selectedPeriod === days
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {days}天
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* 总体统计 */}
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-6">
              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      </div>
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">总请求数</dt>
                        <dd className="text-lg font-medium text-gray-900">
                          {usageData.total_requests.toLocaleString()}
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                        </svg>
                      </div>
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">总Token数</dt>
                        <dd className="text-lg font-medium text-gray-900">
                          {usageData.total_tokens.toLocaleString()}
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">总费用</dt>
                        <dd className="text-lg font-medium text-gray-900">
                          ${usageData.total_cost.toFixed(4)}
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">成功率</dt>
                        <dd className="text-lg font-medium text-gray-900">
                          {usageData.success_rate.toFixed(1)}%
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 模型使用统计 */}
            <div className="bg-white shadow rounded-lg mb-6">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                  🤖 模型使用统计
                </h3>
                {Object.keys(usageData.model_breakdown).length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            模型
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            请求数
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Token数
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            费用
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            成功率
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {Object.entries(usageData.model_breakdown).map(([model, stats]) => (
                          <tr key={model}>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                              {model}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {stats.requests.toLocaleString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {stats.tokens.toLocaleString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              ${stats.cost.toFixed(4)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                stats.success_rate >= 95 ? 'bg-green-100 text-green-800' :
                                stats.success_rate >= 90 ? 'bg-yellow-100 text-yellow-800' :
                                'bg-red-100 text-red-800'
                              }`}>
                                {stats.success_rate.toFixed(1)}%
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">暂无使用数据</p>
                )}
              </div>
            </div>

            {/* 每日使用趋势 */}
            <div className="bg-white shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                  📈 每日使用趋势
                </h3>
                {Object.keys(usageData.daily_stats).length > 0 ? (
                  <div className="space-y-2">
                    {Object.entries(usageData.daily_stats)
                      .sort(([a], [b]) => a.localeCompare(b))
                      .slice(-10) // 显示最近10天
                      .map(([date, stats]) => {
                        const maxTokens = Math.max(
                          ...Object.values(usageData.daily_stats).map(d => d.tokens)
                        );
                        const percentage = (stats.tokens / maxTokens) * 100;

                        return (
                          <div key={date} className="flex items-center space-x-4">
                            <div className="w-24 text-sm text-gray-600">{date}</div>
                            <div className="flex-1 bg-gray-200 rounded-full h-4">
                              <div
                                className="bg-blue-500 h-4 rounded-full"
                                style={{ width: `${percentage}%` }}
                              ></div>
                            </div>
                            <div className="w-32 text-sm text-gray-900 text-right">
                              {stats.tokens.toLocaleString()} tokens
                            </div>
                            <div className="w-20 text-sm text-gray-600 text-right">
                              ${stats.cost.toFixed(4)}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">暂无使用数据</p>
                )}
              </div>
            </div>
          </>
        )}

        {/* 账单信息标签页 */}
        {activeTab === 'billing' && billingData && (
          <div className="space-y-6">
            {/* 账单概览 */}
            <div className="bg-white shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-6">
                  💳 账单概览
                </h3>
                <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-600">本月费用</p>
                        <p className="text-2xl font-bold text-gray-900">
                          ${billingData.current_month_cost.toFixed(2)}
                        </p>
                      </div>
                      <div className="text-blue-500">
                        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-600">上月费用</p>
                        <p className="text-2xl font-bold text-gray-900">
                          ${billingData.last_month_cost.toFixed(2)}
                        </p>
                      </div>
                      <div className="text-green-500">
                        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-600">待支付金额</p>
                        <p className="text-2xl font-bold text-gray-900">
                          ${billingData.total_unpaid.toFixed(2)}
                        </p>
                      </div>
                      <div className="text-yellow-500">
                        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2">
                  <div className="border-t pt-4">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">下次扣款日期</span>
                      <span className="text-sm font-medium text-gray-900">
                        {billingData.next_billing_date ? new Date(billingData.next_billing_date).toLocaleDateString() : '未设置'}
                      </span>
                    </div>
                  </div>
                  <div className="border-t pt-4">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">订阅状态</span>
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        billingData.subscription_status === 'active' ? 'bg-green-100 text-green-800' :
                        billingData.subscription_status === 'trial' ? 'bg-blue-100 text-blue-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {billingData.subscription_status === 'active' ? '活跃' :
                         billingData.subscription_status === 'trial' ? '试用' :
                         '未激活'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 支付方式 */}
            <div className="bg-white shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg leading-6 font-medium text-gray-900">
                    支付方式
                  </h3>
                  <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm">
                    添加支付方式
                  </button>
                </div>
                <div className="bg-gray-50 rounded-lg p-4 text-center text-gray-500">
                  {billingData.payment_method || '未设置支付方式'}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 价格方案标签页 */}
        {activeTab === 'pricing' && pricingData && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-6">
                💰 模型价格方案
              </h3>
              {pricingData.models && Object.keys(pricingData.models).length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          模型
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          提供商
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          输入价格 (1K tokens)
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          输出价格 (1K tokens)
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          等级
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {Object.entries(pricingData.models).map(([modelId, model]) => (
                        <tr key={modelId}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {model.name}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {model.provider}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            ${model.input_price.toFixed(6)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            ${model.output_price.toFixed(6)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              model.tier === 'free' ? 'bg-green-100 text-green-800' :
                              model.tier === 'basic' ? 'bg-blue-100 text-blue-800' :
                              model.tier === 'premium' ? 'bg-purple-100 text-purple-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {model.tier === 'free' ? '免费' :
                               model.tier === 'basic' ? '基础' :
                               model.tier === 'premium' ? '高级' :
                               model.tier}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">暂无价格信息</p>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}