'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';

// 类型定义
interface DashboardStats {
  total_requests: number;
  today_requests: number;
  monthly_quota: number;
  cost_this_month: number;
  active_users: number;
  total_teams: number;
  active_api_keys: number;
  security_alerts: number;
}

interface UsageTrend {
  date: string;
  requests: number;
  cost: number;
}

interface TopModel {
  model_name: string;
  requests: number;
  cost: number;
  percentage: number;
}

interface RecentActivity {
  id: string;
  action: string;
  resource_type: string;
  user_name: string;
  timestamp: string;
  status: 'success' | 'warning' | 'error';
}

export default function DashboardPage() {
  const router = useRouter();
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [stats, setStats] = useState<DashboardStats>({
    total_requests: 1250,
    today_requests: 45,
    monthly_quota: 50000,
    cost_this_month: 0.13,
    active_users: 8,
    total_teams: 3,
    active_api_keys: 5,
    security_alerts: 2
  });

  const [usageTrend, setUsageTrend] = useState<UsageTrend[]>([]);
  const [topModels, setTopModels] = useState<TopModel[]>([]);
  const [recentActivities, setRecentActivities] = useState<RecentActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');

  // 模拟数据
  const mockUsageTrend: UsageTrend[] = Array.from({ length: 30 }, (_, i) => ({
    date: new Date(Date.now() - (29 - i) * 24 * 3600000).toISOString().split('T')[0],
    requests: Math.floor(Math.random() * 100) + 20,
    cost: Math.random() * 0.01 + 0.001
  }));

  const mockTopModels: TopModel[] = [
    { model_name: 'gpt-4', requests: 450, cost: 0.08, percentage: 36 },
    { model_name: 'claude-3-sonnet', requests: 320, cost: 0.04, percentage: 26 },
    { model_name: 'gemini-pro', requests: 280, cost: 0.02, percentage: 22 },
    { model_name: 'deepseek-chat', requests: 200, cost: 0.01, percentage: 16 }
  ];

  const mockRecentActivities: RecentActivity[] = [
    {
      id: '1',
      action: 'API密钥创建',
      resource_type: 'api_key',
      user_name: '张三',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      status: 'success'
    },
    {
      id: '2',
      action: '用户登录失败',
      resource_type: 'user',
      user_name: '未知用户',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      status: 'warning'
    },
    {
      id: '3',
      action: '订阅升级',
      resource_type: 'subscription',
      user_name: '李四',
      timestamp: new Date(Date.now() - 10800000).toISOString(),
      status: 'success'
    },
    {
      id: '4',
      action: '权限不足',
      resource_type: 'team',
      user_name: '王五',
      timestamp: new Date(Date.now() - 14400000).toISOString(),
      status: 'error'
    }
  ];

  useEffect(() => {
    fetchDashboardData();
  }, [timeRange]);

  useEffect(() => {
    if (usageTrend.length > 0 && canvasRef.current) {
      drawUsageChart();
    }
  }, [usageTrend]);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000));

      setUsageTrend(mockUsageTrend);
      setTopModels(mockTopModels);
      setRecentActivities(mockRecentActivities);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const drawUsageChart = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    // 清除画布
    ctx.clearRect(0, 0, width, height);

    // 找出最大值
    const maxRequests = Math.max(...usageTrend.map(d => d.requests));

    // 绘制网格线
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;

    // 水平网格线
    for (let i = 0; i <= 5; i++) {
      const y = padding + (chartHeight / 5) * i;
      ctx.beginPath();
      ctx.moveTo(padding, y);
      ctx.lineTo(width - padding, y);
      ctx.stroke();
    }

    // 绘制数据点和连线
    ctx.strokeStyle = '#3b82f6';
    ctx.fillStyle = '#3b82f6';
    ctx.lineWidth = 2;

    ctx.beginPath();
    usageTrend.forEach((data, index) => {
      const x = padding + (chartWidth / (usageTrend.length - 1)) * index;
      const y = padding + chartHeight - (data.requests / maxRequests) * chartHeight;

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();

    // 绘制数据点
    usageTrend.forEach((data, index) => {
      const x = padding + (chartWidth / (usageTrend.length - 1)) * index;
      const y = padding + chartHeight - (data.requests / maxRequests) * chartHeight;

      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
    });

    // 绘制标签
    ctx.fillStyle = '#6b7280';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';

    // X轴标签（显示部分日期）
    const step = Math.ceil(usageTrend.length / 7);
    usageTrend.forEach((data, index) => {
      if (index % step === 0 || index === usageTrend.length - 1) {
        const x = padding + (chartWidth / (usageTrend.length - 1)) * index;
        const date = new Date(data.date);
        const label = `${date.getMonth() + 1}/${date.getDate()}`;
        ctx.fillText(label, x, height - 10);
      }
    });

    // Y轴标签
    ctx.textAlign = 'right';
    for (let i = 0; i <= 5; i++) {
      const y = padding + (chartHeight / 5) * i;
      const value = Math.round(maxRequests * (1 - i / 5));
      ctx.fillText(value.toString(), padding - 10, y + 4);
    }
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('zh-CN').format(num);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));

    if (diffInMinutes < 60) {
      return `${diffInMinutes}分钟前`;
    } else if (diffInMinutes < 1440) {
      return `${Math.floor(diffInMinutes / 60)}小时前`;
    } else {
      return `${Math.floor(diffInMinutes / 1440)}天前`;
    }
  };

  const getStatusColor = (status: 'success' | 'warning' | 'error') => {
    switch (status) {
      case 'success': return 'text-green-600 bg-green-100';
      case 'warning': return 'text-yellow-600 bg-yellow-100';
      case 'error': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: 'success' | 'warning' | 'error') => {
    switch (status) {
      case 'success': return '✅';
      case 'warning': return '⚠️';
      case 'error': return '❌';
      default: return '📄';
    }
  };

  const quotaPercentage = (stats.total_requests / stats.monthly_quota) * 100;
  const quotaColor = quotaPercentage > 80 ? 'red' : quotaPercentage > 60 ? 'yellow' : 'green';

  return (
    <div className="p-6">
      {/* 页面标题 */}
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">企业仪表板</h1>
          <p className="text-gray-600 mt-1">监控您的AI服务使用情况和业务指标</p>
        </div>
        <div className="flex space-x-3">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as '7d' | '30d' | '90d')}
            className="px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="7d">最近7天</option>
            <option value="30d">最近30天</option>
            <option value="90d">最近90天</option>
          </select>
          <button
            onClick={() => fetchDashboardData()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            刷新数据
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* 关键指标卡片 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">本月请求数</h3>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {formatNumber(stats.total_requests)}
                  </p>
                  <p className="text-sm text-gray-600 mt-1">
                    今日: {formatNumber(stats.today_requests)}
                  </p>
                </div>
                <div className="text-3xl">📊</div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">本月成本</h3>
                  <p className="text-2xl font-bold text-purple-600 mt-1">
                    {formatCurrency(stats.cost_this_month)}
                  </p>
                  <p className="text-sm text-green-600 mt-1">
                    ↓ 12% vs 上月
                  </p>
                </div>
                <div className="text-3xl">💰</div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">活跃用户</h3>
                  <p className="text-2xl font-bold text-blue-600 mt-1">
                    {stats.active_users}
                  </p>
                  <p className="text-sm text-gray-600 mt-1">
                    共 {stats.total_teams} 个团队
                  </p>
                </div>
                <div className="text-3xl">👥</div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">安全警报</h3>
                  <p className="text-2xl font-bold text-red-600 mt-1">
                    {stats.security_alerts}
                  </p>
                  <p className="text-sm text-gray-600 mt-1">
                    {stats.active_api_keys} 个活跃密钥
                  </p>
                </div>
                <div className="text-3xl">🔒</div>
              </div>
            </div>
          </div>

          {/* 配额使用情况 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">配额使用情况</h3>
              <span className={`text-sm font-medium ${
                quotaPercentage > 80 ? 'text-red-600' :
                quotaPercentage > 60 ? 'text-yellow-600' : 'text-green-600'
              }`}>
                {quotaPercentage.toFixed(1)}%
              </span>
            </div>
            <div className="space-y-3">
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className={`h-3 rounded-full transition-all duration-300 ${
                    quotaPercentage > 80 ? 'bg-red-500' :
                    quotaPercentage > 60 ? 'bg-yellow-500' : 'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(quotaPercentage, 100)}%` }}
                ></div>
              </div>
              <div className="flex justify-between text-sm text-gray-600">
                <span>已使用: {formatNumber(stats.total_requests)}</span>
                <span>总计: {formatNumber(stats.monthly_quota)}</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 使用趋势图 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">使用趋势</h3>
              <canvas
                ref={canvasRef}
                width={500}
                height={300}
                className="w-full"
              ></canvas>
            </div>

            {/* 热门模型 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">热门模型</h3>
              <div className="space-y-4">
                {topModels.map((model, index) => (
                  <div key={model.model_name} className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-900">
                          {model.model_name}
                        </span>
                        <span className="text-sm text-gray-600">
                          {formatNumber(model.requests)} 次
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${model.percentage}%` }}
                        ></div>
                      </div>
                    </div>
                    <div className="ml-4 text-right">
                      <p className="text-sm text-gray-600">
                        {formatCurrency(model.cost)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 最近活动 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">最近活动</h3>
              <button
                onClick={() => router.push('/dashboard/audit')}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                查看全部
              </button>
            </div>
            <div className="space-y-3">
              {recentActivities.map((activity) => (
                <div key={activity.id} className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
                  <div className="flex items-center space-x-3">
                    <span className="text-lg">{getStatusIcon(activity.status)}</span>
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {activity.action}
                      </p>
                      <p className="text-sm text-gray-600">
                        {activity.user_name} · {activity.resource_type}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(activity.status)}`}>
                      {activity.status === 'success' ? '成功' :
                       activity.status === 'warning' ? '警告' : '错误'}
                    </span>
                    <p className="text-xs text-gray-500 mt-1">
                      {formatTime(activity.timestamp)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 快捷操作 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <button
              onClick={() => router.push('/dashboard/api-keys')}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="text-center">
                <div className="text-3xl mb-3">🔑</div>
                <h4 className="font-medium text-gray-900">管理API密钥</h4>
                <p className="text-sm text-gray-600 mt-1">创建和管理API访问密钥</p>
              </div>
            </button>

            <button
              onClick={() => router.push('/dashboard/billing')}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="text-center">
                <div className="text-3xl mb-3">💳</div>
                <h4 className="font-medium text-gray-900">账单与订阅</h4>
                <p className="text-sm text-gray-600 mt-1">查看账单和管理订阅</p>
              </div>
            </button>

            <button
              onClick={() => router.push('/dashboard/audit')}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="text-center">
                <div className="text-3xl mb-3">📋</div>
                <h4 className="font-medium text-gray-900">审计日志</h4>
                <p className="text-sm text-gray-600 mt-1">查看系统操作记录</p>
              </div>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}