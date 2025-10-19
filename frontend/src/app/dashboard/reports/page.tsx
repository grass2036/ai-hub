'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';

// 类型定义
interface UsageReport {
  period: {
    start_date: string;
    end_date: string;
    days: number;
  };
  summary: {
    total_requests: number;
    total_cost: number;
    total_tokens: number;
    unique_users: number;
    avg_daily_requests: number;
  };
  daily_usage: Array<{
    date: string;
    requests: number;
    cost: number;
    tokens: number;
    users: number;
  }>;
  model_usage: Array<{
    model_name: string;
    requests: number;
    cost: number;
    tokens: number;
    percentage: number;
  }>;
  user_usage: Array<{
    user_id: string;
    user_name: string;
    requests: number;
    cost: number;
    tokens: number;
  }>;
  cost_breakdown: {
    api_calls: number;
    tokens: number;
    storage: number;
    other: number;
  };
}

interface CostAnalysis {
  current_month: {
    total_cost: number;
    requests: number;
    tokens: number;
    forecast: number;
  };
  previous_month: {
    total_cost: number;
    requests: number;
    tokens: number;
  };
  trend: {
    direction: 'up' | 'down' | 'stable';
    percentage: number;
  };
  projections: Array<{
    month: string;
    projected_cost: number;
    projected_requests: number;
  }>;
}

interface EfficiencyMetrics {
  avg_cost_per_request: number;
  avg_tokens_per_request: number;
  cost_efficiency_score: number;
  usage_distribution: {
    peak_hours: Array<{ hour: number; requests: number }>;
    week_days: Array<{ day: string; requests: number }>;
  };
  error_rates: {
    total_errors: number;
    error_rate: number;
    common_errors: Array<{ error_type: string; count: number; percentage: number }>;
  };
}

export default function ReportsPage() {
  const router = useRouter();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const costCanvasRef = useRef<HTMLCanvasElement>(null);
  const efficiencyCanvasRef = useRef<HTMLCanvasElement>(null);

  const [activeTab, setActiveTab] = useState<'usage' | 'costs' | 'efficiency' | 'predictions'>('usage');
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | '1y'>('30d');
  const [loading, setLoading] = useState(false);

  const [usageReport, setUsageReport] = useState<UsageReport | null>(null);
  const [costAnalysis, setCostAnalysis] = useState<CostAnalysis | null>(null);
  const [efficiencyMetrics, setEfficiencyMetrics] = useState<EfficiencyMetrics | null>(null);

  // 模拟数据
  const mockUsageReport: UsageReport = {
    period: {
      start_date: new Date(Date.now() - 30 * 24 * 3600000).toISOString(),
      end_date: new Date().toISOString(),
      days: 30
    },
    summary: {
      total_requests: 15420,
      total_cost: 127.45,
      total_tokens: 2450000,
      unique_users: 12,
      avg_daily_requests: 514
    },
    daily_usage: Array.from({ length: 30 }, (_, i) => ({
      date: new Date(Date.now() - (29 - i) * 24 * 3600000).toISOString().split('T')[0],
      requests: Math.floor(Math.random() * 800) + 200,
      cost: Math.random() * 8 + 2,
      tokens: Math.floor(Math.random() * 100000) + 50000,
      users: Math.floor(Math.random() * 8) + 4
    })),
    model_usage: [
      { model_name: 'gpt-4', requests: 5420, cost: 65.04, tokens: 850000, percentage: 35.1 },
      { model_name: 'claude-3-sonnet', requests: 4120, cost: 41.20, tokens: 720000, percentage: 26.7 },
      { model_name: 'gemini-pro', requests: 3850, cost: 15.40, tokens: 680000, percentage: 25.0 },
      { model_name: 'deepseek-chat', requests: 2030, cost: 5.81, tokens: 200000, percentage: 13.2 }
    ],
    user_usage: [
      { user_id: '1', user_name: '张三', requests: 3420, cost: 28.90, tokens: 520000 },
      { user_id: '2', user_name: '李四', requests: 2850, cost: 23.15, tokens: 450000 },
      { user_id: '3', user_name: '王五', requests: 2240, cost: 18.70, tokens: 380000 },
      { user_id: '4', user_name: '赵六', requests: 1890, cost: 15.20, tokens: 320000 }
    ],
    cost_breakdown: {
      api_calls: 89.50,
      tokens: 32.30,
      storage: 4.20,
      other: 1.45
    }
  };

  const mockCostAnalysis: CostAnalysis = {
    current_month: {
      total_cost: 127.45,
      requests: 15420,
      tokens: 2450000,
      forecast: 145.60
    },
    previous_month: {
      total_cost: 108.30,
      requests: 13200,
      tokens: 2100000
    },
    trend: {
      direction: 'up',
      percentage: 17.7
    },
    projections: [
      { month: '2024-01', projected_cost: 135.20, projected_requests: 16500 },
      { month: '2024-02', projected_cost: 142.80, projected_requests: 17200 },
      { month: '2024-03', projected_cost: 151.40, projected_requests: 18100 }
    ]
  };

  const mockEfficiencyMetrics: EfficiencyMetrics = {
    avg_cost_per_request: 0.0083,
    avg_tokens_per_request: 158.9,
    cost_efficiency_score: 85.2,
    usage_distribution: {
      peak_hours: Array.from({ length: 24 }, (_, i) => ({
        hour: i,
        requests: Math.floor(Math.random() * 100) + 10
      })),
      week_days: [
        { day: '周一', requests: 520 },
        { day: '周二', requests: 680 },
        { day: '周三', requests: 720 },
        { day: '周四', requests: 650 },
        { day: '周五', requests: 580 },
        { day: '周六', requests: 320 },
        { day: '周日', requests: 280 }
      ]
    },
    error_rates: {
      total_errors: 142,
      error_rate: 0.92,
      common_errors: [
        { error_type: 'Rate Limit', count: 68, percentage: 47.9 },
        { error_type: 'Token Limit', count: 42, percentage: 29.6 },
        { error_type: 'Timeout', count: 20, percentage: 14.1 },
        { error_type: 'Other', count: 12, percentage: 8.5 }
      ]
    }
  };

  useEffect(() => {
    fetchReportData();
  }, [timeRange, activeTab]);

  useEffect(() => {
    if (usageReport && activeTab === 'usage' && canvasRef.current) {
      drawUsageChart();
    }
    if (costAnalysis && activeTab === 'costs' && costCanvasRef.current) {
      drawCostChart();
    }
    if (efficiencyMetrics && activeTab === 'efficiency' && efficiencyCanvasRef.current) {
      drawEfficiencyChart();
    }
  }, [usageReport, costAnalysis, efficiencyMetrics, activeTab]);

  const fetchReportData = async () => {
    setLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));

      setUsageReport(mockUsageReport);
      setCostAnalysis(mockCostAnalysis);
      setEfficiencyMetrics(mockEfficiencyMetrics);

    } catch (error) {
      console.error('Failed to fetch report data:', error);
    } finally {
      setLoading(false);
    }
  };

  const drawUsageChart = () => {
    const canvas = canvasRef.current;
    if (!canvas || !usageReport) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    ctx.clearRect(0, 0, width, height);

    const maxRequests = Math.max(...usageReport.daily_usage.map(d => d.requests));

    // 绘制网格
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;

    for (let i = 0; i <= 5; i++) {
      const y = padding + (chartHeight / 5) * i;
      ctx.beginPath();
      ctx.moveTo(padding, y);
      ctx.lineTo(width - padding, y);
      ctx.stroke();
    }

    // 绘制数据线
    ctx.strokeStyle = '#3b82f6';
    ctx.fillStyle = '#3b82f6';
    ctx.lineWidth = 2;

    ctx.beginPath();
    usageReport.daily_usage.forEach((data, index) => {
      const x = padding + (chartWidth / (usageReport.daily_usage.length - 1)) * index;
      const y = padding + chartHeight - (data.requests / maxRequests) * chartHeight;

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();

    // 绘制数据点
    usageReport.daily_usage.forEach((data, index) => {
      const x = padding + (chartWidth / (usageReport.daily_usage.length - 1)) * index;
      const y = padding + chartHeight - (data.requests / maxRequests) * chartHeight;

      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
    });

    // 绘制标签
    ctx.fillStyle = '#6b7280';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';

    const step = Math.ceil(usageReport.daily_usage.length / 7);
    usageReport.daily_usage.forEach((data, index) => {
      if (index % step === 0 || index === usageReport.daily_usage.length - 1) {
        const x = padding + (chartWidth / (usageReport.daily_usage.length - 1)) * index;
        const date = new Date(data.date);
        const label = `${date.getMonth() + 1}/${date.getDate()}`;
        ctx.fillText(label, x, height - 10);
      }
    });
  };

  const drawCostChart = () => {
    const canvas = costCanvasRef.current;
    if (!canvas || !costAnalysis) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;

    ctx.clearRect(0, 0, width, height);

    // 绘制成本对比柱状图
    const barWidth = 60;
    const barSpacing = 40;
    const maxHeight = height - padding * 2;
    const maxCost = Math.max(costAnalysis.current_month.total_cost, costAnalysis.previous_month.total_cost);

    // 上个月成本
    const prevHeight = (costAnalysis.previous_month.total_cost / maxCost) * maxHeight;
    ctx.fillStyle = '#9ca3af';
    ctx.fillRect(
      width / 2 - barWidth - barSpacing / 2,
      height - padding - prevHeight,
      barWidth,
      prevHeight
    );

    // 当前月成本
    const currentHeight = (costAnalysis.current_month.total_cost / maxCost) * maxHeight;
    ctx.fillStyle = '#3b82f6';
    ctx.fillRect(
      width / 2 + barSpacing / 2,
      height - padding - currentHeight,
      barWidth,
      currentHeight
    );

    // 标签
    ctx.fillStyle = '#374151';
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('上月', width / 2 - barWidth / 2 - barSpacing / 2, height - 20);
    ctx.fillText('本月', width / 2 + barWidth / 2 + barSpacing / 2, height - 20);

    // 数值
    ctx.fillStyle = '#111827';
    ctx.font = '12px sans-serif';
    ctx.fillText(
      `$${costAnalysis.previous_month.total_cost.toFixed(2)}`,
      width / 2 - barWidth / 2 - barSpacing / 2,
      height - padding - prevHeight - 10
    );
    ctx.fillText(
      `$${costAnalysis.current_month.total_cost.toFixed(2)}`,
      width / 2 + barWidth / 2 + barSpacing / 2,
      height - padding - currentHeight - 10
    );
  };

  const drawEfficiencyChart = () => {
    const canvas = efficiencyCanvasRef.current;
    if (!canvas || !efficiencyMetrics) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;

    ctx.clearRect(0, 0, width, height);

    // 绘制错误率饼图
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 3;

    const errors = efficiencyMetrics.error_rates.common_errors;
    const total = errors.reduce((sum, error) => sum + error.count, 0);
    let currentAngle = -Math.PI / 2;

    const colors = ['#ef4444', '#f59e0b', '#10b981', '#6b7280'];

    errors.forEach((error, index) => {
      const sliceAngle = (error.count / total) * 2 * Math.PI;

      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
      ctx.closePath();
      ctx.fillStyle = colors[index % colors.length];
      ctx.fill();

      // 绘制标签
      const labelAngle = currentAngle + sliceAngle / 2;
      const labelX = centerX + Math.cos(labelAngle) * (radius + 20);
      const labelY = centerY + Math.sin(labelAngle) * (radius + 20);

      ctx.fillStyle = '#374151';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`${error.error_type}`, labelX, labelY);
      ctx.fillText(`${error.percentage}%`, labelX, labelY + 15);

      currentAngle += sliceAngle;
    });
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN');
  };

  const exportReport = async (format: 'pdf' | 'excel') => {
    try {
      // 模拟导出功能
      await new Promise(resolve => setTimeout(resolve, 1000));
      alert(`报告已导出为 ${format.toUpperCase()} 格式`);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">使用报告与分析</h1>
          <p className="text-gray-600 mt-1">深入分析AI服务使用情况和成本效益</p>
        </div>
        <div className="flex space-x-3">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as '7d' | '30d' | '90d' | '1y')}
            className="px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="7d">最近7天</option>
            <option value="30d">最近30天</option>
            <option value="90d">最近90天</option>
            <option value="1y">最近1年</option>
          </select>
          <button
            onClick={() => exportReport('pdf')}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
          >
            导出PDF
          </button>
          <button
            onClick={() => exportReport('excel')}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
          >
            导出Excel
          </button>
        </div>
      </div>

      {/* 标签页 */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('usage')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'usage'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📊 使用统计
          </button>
          <button
            onClick={() => setActiveTab('costs')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'costs'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            💰 成本分析
          </button>
          <button
            onClick={() => setActiveTab('efficiency')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'efficiency'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            ⚡ 效率指标
          </button>
          <button
            onClick={() => setActiveTab('predictions')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'predictions'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            🔮 预测分析
          </button>
        </nav>
      </div>

      {/* 使用统计 */}
      {activeTab === 'usage' && usageReport && (
        <div className="space-y-6">
          {/* 概览卡片 */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">总请求数</h3>
              <p className="text-2xl font-bold text-gray-900">
                {formatNumber(usageReport.summary.total_requests)}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                日均: {formatNumber(usageReport.summary.avg_daily_requests)}
              </p>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">总成本</h3>
              <p className="text-2xl font-bold text-purple-600">
                {formatCurrency(usageReport.summary.total_cost)}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                期间: {usageReport.period.days} 天
              </p>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Token使用量</h3>
              <p className="text-2xl font-bold text-blue-600">
                {formatNumber(usageReport.summary.total_tokens)}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                平均: {formatNumber(Math.round(usageReport.summary.total_tokens / usageReport.summary.total_requests))} / 请求
              </p>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">活跃用户</h3>
              <p className="text-2xl font-bold text-green-600">
                {usageReport.summary.unique_users}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                用户: {formatNumber(Math.round(usageReport.summary.total_requests / usageReport.summary.unique_users))} / 天
              </p>
            </div>
          </div>

          {/* 使用趋势图 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">使用趋势</h3>
            <canvas
              ref={canvasRef}
              width={800}
              height={300}
              className="w-full"
            ></canvas>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 模型使用分布 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">模型使用分布</h3>
              <div className="space-y-3">
                {usageReport.model_usage.map((model) => (
                  <div key={model.model_name} className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-900">
                          {model.model_name}
                        </span>
                        <span className="text-sm text-gray-600">
                          {model.percentage.toFixed(1)}%
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
                        {formatNumber(model.requests)} 次
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatCurrency(model.cost)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 用户使用排行 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">用户使用排行</h3>
              <div className="space-y-3">
                {usageReport.user_usage.map((user, index) => (
                  <div key={user.user_id} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-sm font-medium text-blue-600">{index + 1}</span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{user.user_name}</p>
                        <p className="text-xs text-gray-500">
                          {formatNumber(user.requests)} 次请求
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-900">
                        {formatCurrency(user.cost)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatNumber(user.tokens)} tokens
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 成本分解 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">成本分解</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <p className="text-2xl font-bold text-blue-600">
                  {formatCurrency(usageReport.cost_breakdown.api_calls)}
                </p>
                <p className="text-sm text-gray-600 mt-1">API调用</p>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <p className="text-2xl font-bold text-green-600">
                  {formatCurrency(usageReport.cost_breakdown.tokens)}
                </p>
                <p className="text-sm text-gray-600 mt-1">Token费用</p>
              </div>
              <div className="text-center p-4 bg-yellow-50 rounded-lg">
                <p className="text-2xl font-bold text-yellow-600">
                  {formatCurrency(usageReport.cost_breakdown.storage)}
                </p>
                <p className="text-sm text-gray-600 mt-1">存储费用</p>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <p className="text-2xl font-bold text-purple-600">
                  {formatCurrency(usageReport.cost_breakdown.other)}
                </p>
                <p className="text-sm text-gray-600 mt-1">其他费用</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 成本分析 */}
      {activeTab === 'costs' && costAnalysis && (
        <div className="space-y-6">
          {/* 成本对比 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">本月成本</h3>
              <p className="text-2xl font-bold text-gray-900">
                {formatCurrency(costAnalysis.current_month.total_cost)}
              </p>
              <div className="flex items-center mt-2">
                {costAnalysis.trend.direction === 'up' ? (
                  <span className="text-red-600 text-sm">↑ {costAnalysis.trend.percentage}%</span>
                ) : (
                  <span className="text-green-600 text-sm">↓ {costAnalysis.trend.percentage}%</span>
                )}
                <span className="text-sm text-gray-500 ml-1">vs 上月</span>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">本月预测</h3>
              <p className="text-2xl font-bold text-blue-600">
                {formatCurrency(costAnalysis.current_month.forecast)}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                基于当前使用率
              </p>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">平均成本/请求</h3>
              <p className="text-2xl font-bold text-purple-600">
                ${(costAnalysis.current_month.total_cost / costAnalysis.current_month.requests).toFixed(4)}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                {formatNumber(costAnalysis.current_month.requests)} 次请求
              </p>
            </div>
          </div>

          {/* 成本对比图 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">月度成本对比</h3>
            <canvas
              ref={costCanvasRef}
              width={400}
              height={300}
              className="w-full max-w-md mx-auto"
            ></canvas>
          </div>

          {/* 未来预测 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">成本预测</h3>
            <div className="space-y-3">
              {costAnalysis.projections.map((projection) => (
                <div key={projection.month} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900">{projection.month}</p>
                    <p className="text-sm text-gray-600">
                      预计 {formatNumber(projection.projected_requests)} 次请求
                    </p>
                  </div>
                  <p className="text-lg font-bold text-blue-600">
                    {formatCurrency(projection.projected_cost)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 效率指标 */}
      {activeTab === 'efficiency' && efficiencyMetrics && (
        <div className="space-y-6">
          {/* 效率概览 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">平均成本/请求</h3>
              <p className="text-2xl font-bold text-gray-900">
                ${efficiencyMetrics.avg_cost_per_request.toFixed(4)}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                成本效率评分: {efficiencyMetrics.cost_efficiency_score}/100
              </p>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">平均Token/请求</h3>
              <p className="text-2xl font-bold text-blue-600">
                {efficiencyMetrics.avg_tokens_per_request.toFixed(1)}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                每请求平均使用量
              </p>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">错误率</h3>
              <p className="text-2xl font-bold text-red-600">
                {efficiencyMetrics.error_rates.error_rate.toFixed(2)}%
              </p>
              <p className="text-sm text-gray-600 mt-1">
                {efficiencyMetrics.error_rates.total_errors} 个错误
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 使用时间分布 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">24小时使用分布</h3>
              <div className="grid grid-cols-12 gap-1">
                {efficiencyMetrics.usage_distribution.peak_hours.map((hour) => (
                  <div key={hour.hour} className="text-center">
                    <div
                      className="bg-blue-500 rounded-sm"
                      style={{
                        height: `${(hour.requests / Math.max(...efficiencyMetrics.usage_distribution.peak_hours.map(h => h.requests))) * 100}px`
                      }}
                    ></div>
                    <p className="text-xs text-gray-500 mt-1">{hour.hour}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* 错误分析 */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">错误类型分布</h3>
              <canvas
                ref={efficiencyCanvasRef}
                width={300}
                height={300}
                className="w-full max-w-sm mx-auto"
              ></canvas>
            </div>
          </div>

          {/* 星期使用分布 */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">星期使用分布</h3>
            <div className="grid grid-cols-7 gap-4">
              {efficiencyMetrics.usage_distribution.week_days.map((day) => (
                <div key={day.day} className="text-center">
                  <div className="bg-blue-100 rounded-lg p-4">
                    <p className="text-lg font-bold text-blue-600">{day.requests}</p>
                    <p className="text-sm text-gray-600">{day.day}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 预测分析 */}
      {activeTab === 'predictions' && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">智能预测分析</h3>
          <p className="text-gray-600">
            预测分析功能正在开发中，将基于历史数据提供智能预测和建议。
          </p>
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center p-6 bg-blue-50 rounded-lg">
              <div className="text-3xl mb-3">🤖</div>
              <h4 className="font-medium text-gray-900 mb-2">AI预测</h4>
              <p className="text-sm text-gray-600">
                基于机器学习的使用量预测
              </p>
            </div>
            <div className="text-center p-6 bg-green-50 rounded-lg">
              <div className="text-3xl mb-3">💡</div>
              <h4 className="font-medium text-gray-900 mb-2">优化建议</h4>
              <p className="text-sm text-gray-600">
                成本优化和使用效率建议
              </p>
            </div>
            <div className="text-center p-6 bg-purple-50 rounded-lg">
              <div className="text-3xl mb-3">📈</div>
              <h4 className="font-medium text-gray-900 mb-2">趋势分析</h4>
              <p className="text-sm text-gray-600">
                长期趋势和季节性分析
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}