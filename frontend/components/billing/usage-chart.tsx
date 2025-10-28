/**
 * 使用量图表组件
 *
 * 显示使用量趋势、模型分布等图表。
 */

'use client';

import React from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';

// 类型导入
import { UsageChartProps } from '@/types/billing';

// UI组件导入
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

// 图表配置
const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

const UsageChart: React.FC<UsageChartProps> = ({
  data,
  type,
  height = 300,
}) => {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatNumber = (value: number) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toString();
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const getChartContent = () => {
    switch (type) {
      case 'requests':
        return (
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              className="text-xs"
            />
            <YAxis
              tickFormatter={formatNumber}
              className="text-xs"
            />
            <Tooltip
              formatter={(value: number, name: string) => {
                if (name === 'requests') {
                  return [formatNumber(value), 'API Calls'];
                }
                return [value, name];
              }}
              labelFormatter={(label) => `Date: ${formatDate(label)}`}
              className="bg-white border border-gray-200 rounded-lg shadow-lg"
            />
            <Area
              type="monotone"
              dataKey="requests"
              stroke="#3B82F6"
              fill="#3B82F6"
              fillOpacity={0.3}
              strokeWidth={2}
            />
          </AreaChart>
        );

      case 'tokens':
        return (
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              className="text-xs"
            />
            <YAxis
              tickFormatter={formatNumber}
              className="text-xs"
            />
            <Tooltip
              formatter={(value: number) => [formatNumber(value), 'Tokens']}
              labelFormatter={(label) => `Date: ${formatDate(label)}`}
              className="bg-white border border-gray-200 rounded-lg shadow-lg"
            />
            <Area
              type="monotone"
              dataKey="tokens"
              stroke="#8B5CF6"
              fill="#8B5CF6"
              fillOpacity={0.3}
              strokeWidth={2}
            />
          </AreaChart>
        );

      case 'cost':
        return (
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              className="text-xs"
            />
            <YAxis
              tickFormatter={(value) => `$${value}`}
              className="text-xs"
            />
            <Tooltip
              formatter={(value: number) => [formatCurrency(value), 'Cost']}
              labelFormatter={(label) => `Date: ${formatDate(label)}`}
              className="bg-white border border-gray-200 rounded-lg shadow-lg"
            />
            <Area
              type="monotone"
              dataKey="cost"
              stroke="#10B981"
              fill="#10B981"
              fillOpacity={0.3}
              strokeWidth={2}
            />
          </AreaChart>
        );

      default:
        return (
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              className="text-xs"
            />
            <YAxis
              tickFormatter={formatNumber}
              className="text-xs"
            />
            <Tooltip
              formatter={(value: number, name: string) => [formatNumber(value), name]}
              labelFormatter={(label) => `Date: ${formatDate(label)}`}
              className="bg-white border border-gray-200 rounded-lg shadow-lg"
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="requests"
              stackId="1"
              stroke="#3B82F6"
              fill="#3B82F6"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="tokens"
              stackId="1"
              stroke="#8B5CF6"
              fill="#8B5CF6"
              strokeWidth={2}
            />
          </AreaChart>
        );
    }
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-medium mb-2">{`Date: ${formatDate(label)}`}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name === 'requests' ? 'API Calls: ' :
               entry.name === 'tokens' ? 'Tokens: ' :
               entry.name === 'cost' ? `Cost: ${formatCurrency(entry.value)}` :
               `${entry.name}: ${formatNumber(entry.value)}`}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <div className="text-center">
          <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center mx-auto mb-2">
            <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <p>No usage data available</p>
          <p className="text-sm">Start using the API to see your usage statistics</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        {getChartContent()}
      </ResponsiveContainer>
    </div>
  );
};

// Model Distribution Chart Component
export const ModelDistributionChart: React.FC<{
  data: Array<{
    model: string;
    count: number;
    percentage: number;
    color?: string;
  }>;
  height?: number;
}> = ({ data, height = 250 }) => {
  const formatNumber = (value: number) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toString();
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-medium mb-1">{data.model}</p>
          <p className="text-sm text-gray-600">
            Requests: {formatNumber(data.count)}
          </p>
          <p className="text-sm text-gray-600">
            Percentage: {data.percentage.toFixed(1)}%
          </p>
        </div>
      );
    }
    return null;
  };

  const CustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    if (percent < 0.05) return null; // Don't show label for very small slices

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        className="text-xs font-medium"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <div className="text-center">
          <p>No model usage data available</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={CustomLabel}
            outerRadius={80}
            fill="#8884d8"
            dataKey="count"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color || COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="mt-4 space-y-2">
        {data.map((item, index) => (
          <div key={index} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: item.color || COLORS[index % COLORS.length] }}
              />
              <span className="truncate max-w-[120px]" title={item.model}>
                {item.model}
              </span>
            </div>
            <div className="text-gray-600">
              {formatNumber(item.count)} ({item.percentage.toFixed(1)}%)
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default UsageChart;