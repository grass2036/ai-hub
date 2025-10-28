/**
 * 使用量仪表板组件
 *
 * 显示用户的使用量统计、配额状态、成本分析等信息。
 */

'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ChartBarIcon,
  CpuChipIcon,
  ClockIcon,
  CurrencyDollarIcon,
  ExclamationTriangleIcon,
  FireIcon,
  InformationCircleIcon,
  ServerIcon,
  TrendingUpIcon,
  TrendingDownIcon,
} from '@heroicons/react/24/outline';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

import { UsageStats, QuotaInfo, UsageType } from '@/types/billing';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface UsageDashboardProps {
  usageStats: UsageStats;
  quotaInfo: QuotaInfo;
  onDateRangeChange?: (startDate: string, endDate: string) => void;
  onUsageTypeChange?: (usageType: UsageType | undefined) => void;
  loading?: boolean;
  className?: string;
}

const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

const MetricCard: React.FC<{
  title: string;
  value: string | number;
  change?: number;
  changeType?: 'increase' | 'decrease' | 'neutral';
  icon: React.ComponentType<any>;
  color: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'cyan';
  description?: string;
}> = ({ title, value, change, changeType = 'neutral', icon: Icon, color, description }) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
    cyan: 'bg-cyan-50 text-cyan-600',
  };

  const changeColorClasses = {
    increase: 'text-green-600',
    decrease: 'text-red-600',
    neutral: 'text-gray-600',
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-medium text-gray-600">{title}</h3>
            {change !== undefined && (
              <Badge
                variant="outline"
                className={cn(
                  'text-xs',
                  changeColorClasses[changeType]
                )}
              >
                {changeType === 'increase' && '+'}
                {change}%
              </Badge>
            )}
          </div>
          <div className="flex items-baseline gap-2">
            <div className="text-2xl font-bold text-gray-900">
              {typeof value === 'number' ? value.toLocaleString() : value}
            </div>
            {change !== undefined && (
              changeType === 'increase' ? (
                <TrendingUpIcon className="w-4 h-4 text-green-600" />
              ) : changeType === 'decrease' ? (
                <TrendingDownIcon className="w-4 h-4 text-red-600" />
              ) : null
            )}
          </div>
          {description && (
            <p className="text-xs text-gray-500 mt-1">{description}</p>
          )}
        </div>
        <div className={cn('w-12 h-12 rounded-lg flex items-center justify-center', colorClasses[color])}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </Card>
  );
};

const QuotaIndicator: React.FC<{
  quota: QuotaInfo['api_calls'] | QuotaInfo['tokens'] | QuotaInfo['storage'];
  type: 'api_calls' | 'tokens' | 'storage';
  title: string;
  unit: string;
}> = ({ quota, type, title, unit }) => {
  const percentageUsed = (quota.used / quota.limit) * 100;
  const isNearLimit = percentageUsed >= 80;
  const isOverLimit = percentageUsed >= 100;

  const getStatusColor = () => {
    if (isOverLimit) return 'text-red-600';
    if (isNearLimit) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getProgressColor = () => {
    if (isOverLimit) return 'bg-red-500';
    if (isNearLimit) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const formatResetTime = (resetAt: string) => {
    const resetDate = new Date(resetAt);
    const now = new Date();
    const diffTime = resetDate.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays <= 0) return 'Resets today';
    if (diffDays === 1) return 'Resets tomorrow';
    return `Resets in ${diffDays} days`;
  };

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-gray-900">{title}</h4>
        <Badge
          variant="outline"
          className={cn(
            'text-xs',
            getStatusColor(),
            isOverLimit && 'border-red-500',
            isNearLimit && 'border-yellow-500'
          )}
        >
          {isOverLimit ? 'Over Limit' : isNearLimit ? 'Near Limit' : 'Healthy'}
        </Badge>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">
            {quota.used.toLocaleString()} / {quota.limit.toLocaleString()} {unit}
          </span>
          <span className={cn('font-medium', getStatusColor())}>
            {percentageUsed.toFixed(1)}%
          </span>
        </div>

        <Progress
          value={Math.min(percentageUsed, 100)}
          className={cn('h-2', getProgressColor())}
        />

        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>
            {quota.remaining.toLocaleString()} {unit} remaining
          </span>
          <span>{formatResetTime(quota.resetAt)}</span>
        </div>
      </div>

      {/* Warnings */}
      {quota.warnings && quota.warnings.length > 0 && (
        <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex items-start gap-2">
            <ExclamationTriangleIcon className="w-4 h-4 text-yellow-600 mt-0.5" />
            <div className="flex-1">
              <p className="text-xs text-yellow-800">
                {quota.warnings[0].message}
              </p>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};

const UsageChart: React.FC<{
  data: Array<{
    date: string;
    requests: number;
    tokens: number;
    cost: number;
  }>;
  type: 'requests' | 'tokens' | 'cost';
  height?: number;
}> = ({ data, type, height = 300 }) => {
  const formatData = () => {
    return data.map(item => ({
      ...item,
      date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    }));
  };

  const getChartConfig = () => {
    switch (type) {
      case 'requests':
        return {
          dataKey: 'requests',
          stroke: '#3b82f6',
          fill: '#3b82f6',
          label: 'Requests',
          format: (value: number) => value.toLocaleString(),
        };
      case 'tokens':
        return {
          dataKey: 'tokens',
          stroke: '#22c55e',
          fill: '#22c55e',
          label: 'Tokens',
          format: (value: number) => `${(value / 1000).toFixed(1)}K`,
        };
      case 'cost':
        return {
          dataKey: 'cost',
          stroke: '#f59e0b',
          fill: '#f59e0b',
          label: 'Cost ($)',
          format: (value: number) => `$${value.toFixed(2)}`,
        };
      default:
        return {
          dataKey: 'requests',
          stroke: '#3b82f6',
          fill: '#3b82f6',
          label: 'Requests',
          format: (value: number) => value.toLocaleString(),
        };
    }
  };

  const config = getChartConfig();

  return (
    <div className="h-64 md:h-80">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={formatData()}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: '#e5e7eb' }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: '#e5e7eb' }}
            tickFormatter={config.format}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#111827', fontWeight: 600 }}
          />
          <Area
            type="monotone"
            dataKey={config.dataKey}
            stroke={config.stroke}
            fill={config.fill}
            fillOpacity={0.2}
            strokeWidth={2}
            name={config.label}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

const ModelUsageChart: React.FC<{
  data: Record<string, number>;
}> = ({ data }) => {
  const chartData = Object.entries(data).map(([model, usage]) => ({
    name: model,
    value: usage,
  }));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export const UsageDashboard: React.FC<UsageDashboardProps> = ({
  usageStats,
  quotaInfo,
  onDateRangeChange,
  onUsageTypeChange,
  loading = false,
  className,
}) => {
  const [timeRange, setTimeRange] = useState('7d');
  const [usageType, setUsageType] = useState<UsageType | undefined>(undefined);

  // Generate mock chart data (in real app, this would come from API)
  const generateChartData = () => {
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
    const data = [];

    for (let i = days - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);

      data.push({
        date: date.toISOString(),
        requests: Math.floor(Math.random() * 1000) + 500,
        tokens: Math.floor(Math.random() * 50000) + 10000,
        cost: Math.random() * 5 + 0.5,
      });
    }

    return data;
  };

  const chartData = generateChartData();

  const handleTimeRangeChange = (value: string) => {
    setTimeRange(value);
    // Trigger date range change callback
    const endDate = new Date();
    const startDate = new Date();

    switch (value) {
      case '7d':
        startDate.setDate(startDate.getDate() - 7);
        break;
      case '30d':
        startDate.setDate(startDate.getDate() - 30);
        break;
      case '90d':
        startDate.setDate(startDate.getDate() - 90);
        break;
    }

    if (onDateRangeChange) {
      onDateRangeChange(startDate.toISOString(), endDate.toISOString());
    }
  };

  const handleUsageTypeChange = (value: string) => {
    const type = value === 'all' ? undefined : value as UsageType;
    setUsageType(type);
    if (onUsageTypeChange) {
      onUsageTypeChange(type);
    }
  };

  if (loading) {
    return (
      <div className={cn('space-y-6', className)}>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="p-6">
              <div className="animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-8 bg-gray-200 rounded w-1/2 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-full"></div>
              </div>
            </Card>
          ))}
        </div>
        <Card className="p-6">
          <div className="animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Usage Dashboard</h2>
          <p className="text-gray-600">Monitor your API usage and quota status</p>
        </div>

        <div className="flex items-center gap-3">
          <Select value={timeRange} onValueChange={handleTimeRangeChange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
            </SelectContent>
          </Select>

          <Select value={usageType || 'all'} onValueChange={handleUsageTypeChange}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Usage</SelectItem>
              <SelectItem value="api_call">API Calls</SelectItem>
              <SelectItem value="token_usage">Token Usage</SelectItem>
              <SelectItem value="storage">Storage</SelectItem>
              <SelectItem value="bandwidth">Bandwidth</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Requests"
          value={usageStats.totalRequests}
          change={12.5}
          changeType="increase"
          icon={ServerIcon}
          color="blue"
          description="API calls this period"
        />

        <MetricCard
          title="Total Tokens"
          value={(usageStats.totalTokens / 1000).toFixed(1) + 'K'}
          change={8.2}
          changeType="increase"
          icon={CpuChipIcon}
          color="green"
          description="Input + output tokens"
        />

        <MetricCard
          title="Total Cost"
          value={`$${usageStats.totalCost.toFixed(2)}`}
          change={-3.1}
          changeType="decrease"
          icon={CurrencyDollarIcon}
          color="yellow"
          description="Current period cost"
        />

        <MetricCard
          title="Avg Response Time"
          value={`${usageStats.averageResponseTime.toFixed(0)}ms`}
          change={-15.3}
          changeType="decrease"
          icon={ClockIcon}
          color="purple"
          description="Average response time"
        />
      </div>

      {/* Charts and Quotas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Usage Charts */}
        <div className="lg:col-span-2 space-y-6">
          <Tabs defaultValue="requests" className="space-y-4">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="requests">Requests</TabsTrigger>
              <TabsTrigger value="tokens">Tokens</TabsTrigger>
              <TabsTrigger value="cost">Cost</TabsTrigger>
            </TabsList>

            <TabsContent value="requests">
              <Card className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">API Requests Over Time</h3>
                <UsageChart data={chartData} type="requests" />
              </Card>
            </TabsContent>

            <TabsContent value="tokens">
              <Card className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Token Usage Over Time</h3>
                <UsageChart data={chartData} type="tokens" />
              </Card>
            </TabsContent>

            <TabsContent value="cost">
              <Card className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost Over Time</h3>
                <UsageChart data={chartData} type="cost" />
              </Card>
            </TabsContent>
          </Tabs>

          {/* Model Usage Distribution */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Usage by Model</h3>
            <ModelUsageChart data={usageStats.modelUsage} />
          </Card>
        </div>

        {/* Quota Status */}
        <div className="space-y-4">
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Quota Status</h3>
            <div className="space-y-4">
              <QuotaIndicator
                quota={quotaInfo.apiCalls}
                type="api_calls"
                title="API Calls"
                unit="calls"
              />

              <QuotaIndicator
                quota={quotaInfo.tokens}
                type="tokens"
                title="Tokens"
                unit="tokens"
              />

              <QuotaIndicator
                quota={quotaInfo.storage}
                type="storage"
                title="Storage"
                unit="GB"
              />
            </div>
          </Card>

          {/* Plan Features */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Available Features</h3>
            <div className="space-y-2">
              {quotaInfo.features.map((feature, index) => (
                <div key={index} className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm text-gray-700">{feature}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* Performance Metrics */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {usageStats.successRate.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-600">Success Rate</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {usageStats.errorRate.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-600">Error Rate</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {usageStats.p95ResponseTime.toFixed(0)}ms
            </div>
            <div className="text-sm text-gray-600">95th Percentile</div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default UsageDashboard;