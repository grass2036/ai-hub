'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import type { UsageStats } from '@/types';
import { Card } from '@/components/ui/Card';

export default function UsagePage() {
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadUsage();
  }, []);

  const loadUsage = async () => {
    try {
      const data: UsageStats = await apiClient.getCurrentUsage();
      setUsage(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load usage statistics');
    } finally {
      setLoading(false);
    }
  };

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
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">使用统计</h1>
        <p className="mt-2 text-gray-600">
          查看您的API使用情况和配额信息
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card title="已使用配额">
          <p className="mt-2 text-3xl font-bold text-blue-600">
            {usage.quota_used.toLocaleString()}
          </p>
          <p className="mt-1 text-sm text-gray-500">
            请求次数
          </p>
        </Card>

        <Card title="总配额">
          <p className="mt-2 text-3xl font-bold text-green-600">
            {usage.quota_total.toLocaleString()}
          </p>
          <p className="mt-1 text-sm text-gray-500">
            每月请求次数
          </p>
        </Card>

        <Card title="剩余配额">
          <p className="mt-2 text-3xl font-bold text-yellow-600">
            {usage.quota_remaining.toLocaleString()}
          </p>
          <p className="mt-1 text-sm text-gray-500">
            还可使用
          </p>
        </Card>
      </div>

      <Card title="配额使用情况">
        <div className="w-full bg-gray-200 rounded-full h-4">
          <div 
            className="bg-blue-600 h-4 rounded-full" 
            style={{ width: `${Math.min(usage.quota_percentage, 100)}%` }}
          ></div>
        </div>
        <div className="mt-2 flex justify-between text-sm text-gray-600">
          <span>0%</span>
          <span className="font-medium">{usage.quota_percentage.toFixed(1)}%</span>
          <span>100%</span>
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="套餐信息">
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">当前套餐</span>
              <span className="font-medium capitalize">{usage.plan}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">重置日期</span>
              <span className="font-medium">
                {new Date(usage.quota_reset_at).toLocaleDateString('zh-CN')}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">剩余天数</span>
              <span className="font-medium">{usage.days_until_reset} 天</span>
            </div>
          </div>
        </Card>

        <Card title="使用建议">
          <div className="space-y-3">
            {usage.quota_percentage < 50 ? (
              <p className="text-green-600">
                您的使用量较低，当前配额充足。
              </p>
            ) : usage.quota_percentage < 80 ? (
              <p className="text-yellow-600">
                您的使用量中等，请注意配额使用情况。
              </p>
            ) : usage.quota_percentage < 100 ? (
              <p className="text-orange-600">
                您的配额即将用完，考虑升级套餐。
              </p>
            ) : (
              <p className="text-red-600">
                您已超出配额限制，请升级套餐以继续使用。
              </p>
            )}
            <button className="w-full mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
              查看套餐选项
            </button>
          </div>
        </Card>
      </div>
    </div>
  );
}