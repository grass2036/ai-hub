'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

// 类型定义
interface UsageStats {
  period_days: number;
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  avg_response_time: number;
  success_rate: number;
  model_usage: Record<string, {
    requests: number;
    tokens: number;
    cost: number;
    avg_response_time: number;
    success_rate: number;
  }>;
  daily_usage: Record<string, {
    requests: number;
    tokens: number;
    cost: number;
  }>;
}

interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  created_at: string;
}

export default function APIKeyUsage() {
  const router = useRouter();
  const [apiKey, setApiKey] = useState<APIKey | null>(null);
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedPeriod, setSelectedPeriod] = useState(30);

  useEffect(() => {
    const fetchData = async () => {
      const keyId = router.query.id as string;
      const token = localStorage.getItem('developer_access_token');

      if (!token || !keyId) {
        router.push('/developer/login');
        return;
      }

      try {
        // 获取API密钥基本信息
        const keyResponse = await fetch(`/api/v1/developer/keys/${keyId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (keyResponse.ok) {
          const keyData = await keyResponse.json();
          setApiKey(keyData.data);
        }

        // 获取使用统计
        const usageResponse = await fetch(`/api/v1/developer/keys/${keyId}/usage?days=${selectedPeriod}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (usageResponse.ok) {
          const usageData = await usageResponse.json();
          setUsageStats(usageData.data);
        }

      } catch (err) {
        setError('加载数据失败');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    if (router.query.id) {
      fetchData();
    }
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

  if (error || !apiKey) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">加载失败</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <Link href="/developer/api-keys" className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700">
            返回API密钥列表
          </Link>
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
              <Link href="/developer/api-keys" className="text-blue-600 hover:text-blue-800">
                ← 返回API密钥
              </Link>
              <h1 className="ml-4 text-xl font-bold text-gray-900">
                {apiKey.name} - 使用统计
              </h1>
            </div>
          </div>
        </div>
      </nav>

      {/* 主要内容 */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
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

        {usageStats && (
          <>
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
                          {usageStats.total_requests.toLocaleString()}
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
                          {usageStats.total_tokens.toLocaleString()}
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
                          ${usageStats.total_cost.toFixed(4)}
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
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                        </svg>
                      </div>
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">成功率</dt>
                        <dd className="text-lg font-medium text-gray-900">
                          {usageStats.success_rate.toFixed(1)}%
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
                {Object.keys(usageStats.model_usage).length > 0 ? (
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
                        {Object.entries(usageStats.model_usage).map(([model, stats]) => (
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
                {Object.keys(usageStats.daily_usage).length > 0 ? (
                  <div className="space-y-2">
                    {Object.entries(usageStats.daily_usage)
                      .sort(([a], [b]) => a.localeCompare(b))
                      .slice(-10) // 显示最近10天
                      .map(([date, stats]) => {
                        const maxTokens = Math.max(
                          ...Object.values(usageStats.daily_usage).map(d => d.tokens)
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
      </main>
    </div>
  );
}