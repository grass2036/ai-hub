'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import type { UsageStats } from '@/types';
import { Card } from '@/components/ui/Card';
import UsageChart from '@/components/charts/UsageChart';
import ModelDistribution from '@/components/charts/ModelDistribution';

export default function UsagePage() {
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');
  const [usageData, setUsageData] = useState<any[]>([]);
  const [modelData, setModelData] = useState<any[]>([]);

  useEffect(() => {
    loadUsage();
  }, []);

  const generateMockData = (days: number) => {
    const data = [];
    const now = new Date();

    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);

      // 生成模拟的使用数据
      const baseRequests = Math.floor(Math.random() * 50) + 30;
      const weekendFactor = (date.getDay() === 0 || date.getDay() === 6) ? 0.7 : 1;
      const requests = Math.floor(baseRequests * weekendFactor * (1 + Math.random() * 0.5));
      const cost = requests * 0.001 * (0.8 + Math.random() * 0.4); // $0.001 per request with variation

      data.push({
        date: date.toISOString().split('T')[0],
        requests,
        cost: Number(cost.toFixed(4))
      });
    }

    return data;
  };

  const generateModelData = () => {
    const models = [
      { name: 'GPT-4', requests: 4500 },
      { name: 'Claude-3', requests: 3200 },
      { name: 'GPT-3.5 Turbo', requests: 2800 },
      { name: 'Gemini Pro', requests: 1500 },
      { name: 'Grok-4 Fast', requests: 900 }
    ];

    const total = models.reduce((sum, model) => sum + model.requests, 0);

    return models.map(model => ({
      model: model.name,
      requests: model.requests,
      percentage: (model.requests / total) * 100
    }));
  };

  const loadUsage = async () => {
    try {
      // 使用模拟数据
      const mockUsage: UsageStats = {
        quota_used: 1250,
        quota_total: 50000,
        quota_remaining: 48750,
        quota_percentage: 2.5,
        quota_reset_at: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString(),
        days_until_reset: 15,
        plan: 'Pro',
        requests_today: 45,
        total_cost: 1.25
      };

      setUsage(mockUsage);

      // 生成图表数据
      const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
      setUsageData(generateMockData(days));
      setModelData(generateModelData());

    } catch (err: any) {
      setError(err.message || 'Failed to load usage statistics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsage();
  }, [timeRange]);

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center py-8">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">错误: {error}</p>
        </div>
      </div>
    );
  }

  if (!usage) {
    return (
      <div className="p-6">
        <div className="text-center py-8">暂无使用数据</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 页面头部 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">数据可视化分析</h1>
            <p className="text-gray-600 mt-2">查看您的API使用情况和详细分析报告</p>
          </div>
          <div className="flex items-center space-x-3">
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as '7d' | '30d' | '90d')}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="7d">最近7天</option>
              <option value="30d">最近30天</option>
              <option value="90d">最近90天</option>
            </select>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              导出报告
            </button>
          </div>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-500">本月使用量</h3>
              <div className="p-2 bg-blue-100 rounded-lg">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
            </div>
            <p className="text-2xl font-bold text-gray-900">{usage?.quota_used.toLocaleString() || '0'}</p>
            <p className="text-sm text-gray-600 mt-1">API请求</p>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-green-600 font-medium">+12.5%</span>
                <span className="text-gray-500 ml-2">较上月</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-500">总配额</h3>
              <div className="p-2 bg-green-100 rounded-lg">
                <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
              </div>
            </div>
            <p className="text-2xl font-bold text-gray-900">{usage?.quota_total.toLocaleString() || '0'}</p>
            <p className="text-sm text-gray-600 mt-1">每月限制</p>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-blue-600 font-medium">Pro套餐</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-500">今日请求</h3>
              <div className="p-2 bg-purple-100 rounded-lg">
                <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <p className="text-2xl font-bold text-gray-900">{usage?.requests_today || '0'}</p>
            <p className="text-sm text-gray-600 mt-1">实时计数</p>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-green-600 font-medium">活跃</span>
                <span className="text-gray-500 ml-2">正常使用</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-medium text-gray-500">总成本</h3>
              <div className="p-2 bg-yellow-100 rounded-lg">
                <svg className="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <p className="text-2xl font-bold text-gray-900">${usage?.total_cost.toFixed(2) || '0.00'}</p>
            <p className="text-sm text-gray-600 mt-1">本月花费</p>
            <div className="mt-4">
              <div className="flex items-center text-sm">
                <span className="text-gray-600">$0.001</span>
                <span className="text-gray-500 ml-2">每请求</span>
              </div>
            </div>
          </div>
        </div>

        {/* 图表区域 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-2 bg-white rounded-lg shadow p-6">
            <UsageChart
              data={usageData}
              title={`API使用量趋势 - ${timeRange === '7d' ? '最近7天' : timeRange === '30d' ? '最近30天' : '最近90天'}`}
              type="requests"
              height={350}
            />
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <ModelDistribution
              data={modelData}
              title="模型使用分布"
              size={300}
            />
          </div>
        </div>

        {/* 成本趋势 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <UsageChart
              data={usageData}
              title="成本趋势分析"
              type="cost"
              height={250}
            />
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">配额使用情况</h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">已使用</span>
                  <span className="font-medium">{usage?.quota_percentage.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all duration-300 ${
                      usage?.quota_percentage && usage.quota_percentage > 90
                        ? 'bg-red-500'
                        : usage?.quota_percentage && usage.quota_percentage > 70
                          ? 'bg-yellow-500'
                          : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(usage?.quota_percentage || 0, 100)}%` }}
                  ></div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <p className="text-sm text-gray-600">剩余配额</p>
                  <p className="text-lg font-bold text-gray-900">
                    {usage?.quota_remaining.toLocaleString() || '0'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">重置时间</p>
                  <p className="text-lg font-bold text-gray-900">
                    {usage?.days_until_reset || '0'}天
                  </p>
                </div>
              </div>

              <div className="pt-4 border-t">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-blue-900 mb-2">使用建议</h4>
                  <p className="text-sm text-blue-800">
                    {usage && usage.quota_percentage < 50
                      ? '您的使用量较低，当前配额充足。可以适当增加使用频率。'
                      : usage && usage.quota_percentage < 80
                        ? '使用量正常，请继续关注配额使用情况。'
                        : usage && usage.quota_percentage < 100
                          ? '配额即将用完，建议考虑升级套餐或优化使用策略。'
                          : '配额已用完，请升级套餐以继续使用服务。'
                    }
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 详细数据表格 */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">使用记录详情</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">日期</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">API请求</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">成本</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">主要模型</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {usageData.slice(-7).reverse().map((day, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {new Date(day.date).toLocaleDateString('zh-CN')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {day.requests.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ${day.cost.toFixed(4)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      GPT-4
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}