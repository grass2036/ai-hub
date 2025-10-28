/**
 * 使用量管理页面
 *
 * 显示详细的使用量统计、配额状态和趋势图表。
 */

'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

// 组件导入
import { BillingLayout, BillingHeader, BillingAlert } from '@/components/billing/billing-layout';
import { QuotaIndicator } from '@/components/billing/quota-indicator';
import { UsageChart } from '@/components/billing/usage-chart';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

// 图表导入
import { UsageTrendChart } from '@/components/charts/UsageTrendChart';
import { ModelDistribution } from '@/components/charts/ModelDistribution';

// Hooks导入
import { useUsageManagement } from '@/store/billing-store';

// 图标导入
import {
  ChartBarIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  FunnelIcon,
  CalendarIcon,
  BoltIcon,
  ServerIcon,
  DocumentTextIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

const UsageDashboard: React.FC = () => {
  const { usageStats, quotaInfo, loading, error, actions } = useUsageManagement();
  const [dateRange, setDateRange] = useState('30'); // days
  const [usageType, setUsageType] = useState<'api_call' | 'token_usage' | 'storage' | 'all'>('all');

  useEffect(() => {
    const fetchUsageData = async () => {
      try {
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - parseInt(dateRange));

        await Promise.all([
          actions.getUsageStats(
            startDate.toISOString().split('T')[0],
            endDate.toISOString().split('T')[0],
            usageType === 'all' ? undefined : usageType
          ),
          actions.getQuotaStatus(),
        ]);
      } catch (error) {
        console.error('Failed to fetch usage data:', error);
      }
    };

    fetchUsageData();
  }, [actions, dateRange, usageType]);

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const getUsagePercentage = (used: number, limit: number) => {
    if (limit === 0) return 0;
    return Math.min((used / limit) * 100, 100);
  };

  const getQuotaStatusColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getTrendIcon = (value: number) => {
    if (value > 0) return <ArrowTrendingUpIcon className="w-4 h-4 text-green-600" />;
    if (value < 0) return <ArrowTrendingDownIcon className="w-4 h-4 text-red-600" />;
    return <div className="w-4 h-4 bg-gray-300 rounded-full" />;
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        type: 'spring',
        damping: 20,
        stiffness: 100,
      },
    },
  };

  if (loading) {
    return (
      <BillingLayout>
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 h-96 bg-gray-200 rounded"></div>
            <div className="h-96 bg-gray-200 rounded"></div>
          </div>
        </div>
      </BillingLayout>
    );
  }

  return (
    <BillingLayout>
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Page Header */}
        <BillingHeader
          title="Usage Dashboard"
          description="Monitor your API usage, quotas, and spending trends"
          actions={
            <div className="flex items-center gap-3">
              <Select value={dateRange} onValueChange={setDateRange}>
                <SelectTrigger className="w-32">
                  <CalendarIcon className="w-4 h-4 mr-2" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7">Last 7 days</SelectItem>
                  <SelectItem value="30">Last 30 days</SelectItem>
                  <SelectItem value="90">Last 90 days</SelectItem>
                  <SelectItem value="365">Last year</SelectItem>
                </SelectContent>
              </Select>

              <Button variant="outline" onClick={() => window.location.reload()}>
                <ArrowPathIcon className="w-4 h-4 mr-2" />
                Refresh
              </Button>

              <Button asChild>
                <a href="/billing/subscription">
                  Upgrade Plan
                </a>
              </Button>
            </div>
          }
        />

        {/* Alerts */}
        {quotaInfo?.warnings && quotaInfo.warnings.length > 0 && (
          <motion.div variants={itemVariants} className="mb-6">
            {quotaInfo.warnings.map((warning, index) => (
              <BillingAlert
                key={index}
                type={warning.severity === 'error' ? 'error' : warning.severity === 'warning' ? 'warning' : 'info'}
                title={`${warning.type.replace('_', ' ').toUpperCase()} Limit Warning`}
                message={warning.message}
                actions={
                  <div className="flex items-center gap-3">
                    <Button size="sm" variant="outline" asChild>
                      <a href="/billing/subscription">Manage Plan</a>
                    </Button>
                    <Button size="sm" asChild>
                      <a href="/billing/payments/methods">Add Credits</a>
                    </Button>
                  </div>
                }
                dismissible={warning.severity !== 'error'}
              />
            ))}
          </motion.div>
        )}

        {/* Usage Stats Cards */}
        <motion.div
          variants={itemVariants}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
        >
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">API Calls</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {usageStats ? formatNumber(usageStats.totalRequests) : '0'}
                  </p>
                  <div className="flex items-center gap-1 mt-2">
                    {getTrendIcon(12)} {/* Mock trend data */}
                    <span className="text-sm text-green-600">+12%</span>
                    <span className="text-sm text-gray-500">vs last period</span>
                  </div>
                </div>
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <BoltIcon className="w-6 h-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Tokens Used</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {usageStats ? formatNumber(usageStats.totalTokens) : '0'}
                  </p>
                  <div className="flex items-center gap-1 mt-2">
                    {getTrendIcon(8)}
                    <span className="text-sm text-green-600">+8%</span>
                    <span className="text-sm text-gray-500">vs last period</span>
                  </div>
                </div>
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                  <DocumentTextIcon className="w-6 h-6 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Cost</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {usageStats ? formatCurrency(usageStats.totalCost) : '$0.00'}
                  </p>
                  <div className="flex items-center gap-1 mt-2">
                    {getTrendIcon(15)}
                    <span className="text-sm text-green-600">+15%</span>
                    <span className="text-sm text-gray-500">vs last period</span>
                  </div>
                </div>
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <ChartBarIcon className="w-6 h-6 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Success Rate</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {usageStats ? `${Math.round(usageStats.successRate * 100)}%` : '0%'}
                  </p>
                  <div className="flex items-center gap-1 mt-2">
                    {getTrendIcon(2)}
                    <span className="text-sm text-green-600">+2%</span>
                    <span className="text-sm text-gray-500">vs last period</span>
                  </div>
                </div>
                <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                  <CheckCircleIcon className="w-6 h-6 text-yellow-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Quota Status */}
        {quotaInfo && (
          <motion.div variants={itemVariants} className="mb-8">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ClockIcon className="w-5 h-5" />
                  Quota Status
                </CardTitle>
                <CardDescription>
                  Current usage against your plan limits
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {/* API Calls Quota */}
                  <QuotaIndicator
                    quota={{
                      type: 'API_CALLS' as any,
                      currentUsage: quotaInfo.apiCalls.used,
                      limit: quotaInfo.apiCalls.limit,
                      percentageUsed: getUsagePercentage(quotaInfo.apiCalls.used, quotaInfo.apiCalls.limit),
                      message: `${quotaInfo.apiCalls.used.toLocaleString()} / ${quotaInfo.apiCalls.limit.toLocaleString()} API calls`,
                      severity: getUsagePercentage(quotaInfo.apiCalls.used, quotaInfo.apiCalls.limit) >= 90 ? 'error' :
                                getUsagePercentage(quotaInfo.apiCalls.used, quotaInfo.apiCalls.limit) >= 70 ? 'warning' : 'info',
                    }}
                    showDetails={true}
                  />

                  {/* Tokens Quota */}
                  {quotaInfo.tokens.limit > 0 && (
                    <QuotaIndicator
                      quota={{
                        type: 'TOKENS' as any,
                        currentUsage: quotaInfo.tokens.used,
                        limit: quotaInfo.tokens.limit,
                        percentageUsed: getUsagePercentage(quotaInfo.tokens.used, quotaInfo.tokens.limit),
                        message: `${quotaInfo.tokens.used.toLocaleString()} / ${quotaInfo.tokens.limit.toLocaleString()} tokens`,
                        severity: getUsagePercentage(quotaInfo.tokens.used, quotaInfo.tokens.limit) >= 90 ? 'error' :
                                  getUsagePercentage(quotaInfo.tokens.used, quotaInfo.tokens.limit) >= 70 ? 'warning' : 'info',
                      }}
                      showDetails={true}
                    />
                  )}

                  {/* Storage Quota */}
                  {quotaInfo.storage.limit > 0 && (
                    <QuotaIndicator
                      quota={{
                        type: 'STORAGE' as any,
                        currentUsage: quotaInfo.storage.used,
                        limit: quotaInfo.storage.limit,
                        percentageUsed: getUsagePercentage(quotaInfo.storage.used, quotaInfo.storage.limit),
                        message: `${(quotaInfo.storage.used / 1024).toFixed(1)}GB / ${(quotaInfo.storage.limit / 1024).toFixed(1)}GB`,
                        severity: getUsagePercentage(quotaInfo.storage.used, quotaInfo.storage.limit) >= 90 ? 'error' :
                                  getUsagePercentage(quotaInfo.storage.used, quotaInfo.storage.limit) >= 70 ? 'warning' : 'info',
                      }}
                      showDetails={true}
                    />
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Usage Charts */}
        <motion.div
          variants={itemVariants}
          className="grid grid-cols-1 lg:grid-cols-3 gap-8"
        >
          {/* Usage Trend Chart */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>Usage Trend</CardTitle>
                <CardDescription>
                  Your API usage over the selected time period
                </CardDescription>
              </CardHeader>
              <CardContent>
                <UsageTrendChart
                  data={usageStats ? [
                    {
                      date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                      requests: Math.floor(usageStats.totalRequests * 0.7),
                      cost: usageStats.totalCost * 0.6,
                    },
                    {
                      date: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                      requests: Math.floor(usageStats.totalRequests * 0.85),
                      cost: usageStats.totalCost * 0.8,
                    },
                    {
                      date: new Date().toISOString().split('T')[0],
                      requests: usageStats.totalRequests,
                      cost: usageStats.totalCost,
                    },
                  ] : []}
                  height={350}
                />
              </CardContent>
            </Card>
          </div>

          {/* Model Distribution */}
          <div>
            <Card>
              <CardHeader>
                <CardTitle>Model Usage</CardTitle>
                <CardDescription>
                  Distribution across different AI models
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ModelDistribution
                  data={usageStats ? Object.entries(usageStats.modelUsage).map(([model, count]) => ({
                    model,
                    count,
                    percentage: (count / usageStats.totalRequests) * 100,
                    color: '#3B82F6', // Mock color
                  })) : []}
                  height={250}
                />
              </CardContent>
            </Card>
          </div>
        </motion.div>

        {/* Detailed Usage Table */}
        <motion.div variants={itemVariants} className="mt-8">
          <Card>
            <CardHeader>
              <CardTitle>Detailed Usage</CardTitle>
              <CardDescription>
                Hourly usage breakdown for the selected period
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="daily" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="daily">Daily</TabsTrigger>
                  <TabsTrigger value="weekly">Weekly</TabsTrigger>
                  <TabsTrigger value="hourly">Hourly</TabsTrigger>
                </TabsList>

                <TabsContent value="daily" className="mt-4">
                  <UsageChart
                    data={usageStats ? Object.entries(usageStats.hourlyUsage).map(([hour, requests]) => ({
                      date: hour,
                      requests,
                      cost: requests * 0.001, // Mock cost calculation
                      tokens: requests * 1000, // Mock token calculation
                    })) : []}
                    type="requests"
                    height={300}
                  />
                </TabsContent>

                <TabsContent value="weekly" className="mt-4">
                  <div className="text-center py-8 text-gray-500">
                    Weekly view coming soon
                  </div>
                </TabsContent>

                <TabsContent value="hourly" className="mt-4">
                  <div className="text-center py-8 text-gray-500">
                    Hourly detailed view coming soon
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </motion.div>

        {/* Quick Actions */}
        <motion.div variants={itemVariants} className="mt-8">
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
              <CardDescription>
                Common tasks to manage your usage and billing
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Button variant="outline" className="justify-start h-auto p-4" asChild>
                  <a href="/billing/subscription">
                    <ServerIcon className="w-5 h-5 mr-3" />
                    <div className="text-left">
                      <div className="font-medium">Upgrade Plan</div>
                      <div className="text-sm text-gray-600">Increase your limits</div>
                    </div>
                  </a>
                </Button>

                <Button variant="outline" className="justify-start h-auto p-4" asChild>
                  <a href="/billing/invoices">
                    <DocumentTextIcon className="w-5 h-5 mr-3" />
                    <div className="text-left">
                      <div className="font-medium">View Invoices</div>
                      <div className="text-sm text-gray-600">Download billing records</div>
                    </div>
                  </a>
                </Button>

                <Button variant="outline" className="justify-start h-auto p-4" asChild>
                  <a href="/billing/settings">
                    <FunnelIcon className="w-5 h-5 mr-3" />
                    <div className="text-left">
                      <div className="font-medium">Usage Alerts</div>
                      <div className="text-sm text-gray-600">Configure notifications</div>
                    </div>
                  </a>
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>
    </BillingLayout>
  );
};

export default UsageDashboard;