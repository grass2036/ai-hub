/**
 * 计费概览页面
 *
 * 显示用户的计费摘要、当前订阅状态、使用量统计和重要操作。
 */

'use client';

import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';

// 组件导入
import { BillingLayout, BillingHeader, BillingStatsCard, BillingAlert } from '@/components/billing/billing-layout';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

// 图表导入
import { UsageTrendChart } from '@/components/charts/UsageTrendChart';
import { CostBreakdown } from '@/components/charts/CostBreakdown';

// Hooks导入
import { useBillingData } from '@/store/billing-store';
import { useBillingActions } from '@/store/billing-store';

// 图标导入
import {
  CreditCardIcon,
  ChartBarIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowRightIcon,
  ClockIcon,
  CurrencyDollarIcon,
} from '@heroicons/react/24/outline';

const BillingOverview: React.FC = () => {
  const { currentSubscription, billingSummary, quotaInfo, loading } = useBillingData();
  const { getBillingSummary, getCurrentSubscription, getQuotaStatus } = useBillingActions();

  useEffect(() => {
    const fetchData = async () => {
      try {
        await Promise.all([
          getBillingSummary(),
          getCurrentSubscription(),
          getQuotaStatus(),
        ]);
      } catch (error) {
        console.error('Failed to fetch billing data:', error);
      }
    };

    fetchData();
  }, [getBillingSummary, getCurrentSubscription, getQuotaStatus]);

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
    if (percentage >= 90) return 'text-red-600 bg-red-50';
    if (percentage >= 70) return 'text-yellow-600 bg-yellow-50';
    return 'text-green-600 bg-green-50';
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="h-80 bg-gray-200 rounded"></div>
            <div className="h-80 bg-gray-200 rounded"></div>
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
          title="Billing Overview"
          description="Manage your subscription, track usage, and view billing history"
          actions={
            <div className="flex items-center gap-3">
              <Button variant="outline" asChild>
                <Link href="/billing/invoices">
                  <DocumentTextIcon className="w-4 h-4 mr-2" />
                  View Invoices
                </Link>
              </Button>
              <Button asChild>
                <Link href="/billing/subscription">
                  <CreditCardIcon className="w-4 h-4 mr-2" />
                  Manage Subscription
                </Link>
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
                      <Link href="/billing/usage">View Usage Details</Link>
                    </Button>
                    <Button size="sm" asChild>
                      <Link href="/billing/subscription">Upgrade Plan</Link>
                    </Button>
                  </div>
                }
                dismissible={warning.severity !== 'error'}
              />
            ))}
          </motion.div>
        )}

        {/* Stats Cards */}
        <motion.div
          variants={itemVariants}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
        >
          <BillingStatsCard
            title="Current Plan"
            value={currentSubscription ?
              currentSubscription.plan.type.charAt(0).toUpperCase() + currentSubscription.plan.type.slice(1) :
              'Free'
            }
            description={currentSubscription ? `${formatCurrency(currentSubscription.unitPrice)}/${currentSubscription.billingCycle}` : 'No subscription'}
            icon={CreditCardIcon}
            trend={currentSubscription?.autoRenew ? 'stable' : 'down'}
          />

          <BillingStatsCard
            title="This Month's Usage"
            value={billingSummary ? formatCurrency(billingSummary.usageThisMonth.totalCost) : '$0.00'}
            description={`${billingSummary?.usageThisMonth.totalRequests || 0} API calls`}
            icon={ChartBarIcon}
            change={billingSummary ? 12 : undefined}
            changeType="increase"
          />

          <BillingStatsCard
            title="API Calls Used"
            value={quotaInfo ? `${quotaInfo.apiCalls.used.toLocaleString()}` : '0'}
            description={`${quotaInfo ? quotaInfo.apiCalls.remaining.toLocaleString() : '∞'} remaining`}
            icon={ClockIcon}
          />

          <BillingStatsCard
            title="Next Billing Date"
            value={currentSubscription ?
              new Date(currentSubscription.currentPeriodEnd).toLocaleDateString() :
              'N/A'
            }
            description={currentSubscription ? `${currentSubscription.daysUntilRenewal} days` : 'No active subscription'}
            icon={CurrencyDollarIcon}
          />
        </motion.div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Usage Charts */}
          <motion.div variants={itemVariants} className="lg:col-span-2 space-y-8">
            {/* Usage Trend Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ChartBarIcon className="w-5 h-5" />
                  Usage Trend
                </CardTitle>
                <CardDescription>
                  Your API usage and costs over the past 30 days
                </CardDescription>
              </CardHeader>
              <CardContent>
                <UsageTrendChart
                  data={billingSummary ? [
                    {
                      date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                      requests: Math.floor(billingSummary.usageThisMonth.totalRequests / 30),
                      cost: billingSummary.usageThisMonth.totalCost / 30,
                    },
                    {
                      date: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
                      requests: Math.floor(billingSummary.usageThisMonth.totalRequests / 15),
                      cost: billingSummary.usageThisMonth.totalCost / 15,
                    },
                    {
                      date: new Date().toISOString().split('T')[0],
                      requests: billingSummary.usageThisMonth.totalRequests,
                      cost: billingSummary.usageThisMonth.totalCost,
                    },
                  ] : []}
                  height={300}
                />
              </CardContent>
            </Card>

            {/* Cost Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>Cost Breakdown</CardTitle>
                <CardDescription>
                  Where your spending is allocated this month
                </CardDescription>
              </CardHeader>
              <CardContent>
                <CostBreakdown
                  data={[
                    {
                      category: 'API Calls',
                      amount: billingSummary?.usageThisMonth.totalCost || 0,
                      percentage: 100,
                      color: '#3B82F6',
                    },
                    {
                      category: 'Storage',
                      amount: 0,
                      percentage: 0,
                      color: '#10B981',
                    },
                    {
                      category: 'Data Transfer',
                      amount: 0,
                      percentage: 0,
                      color: '#F59E0B',
                    },
                  ]}
                  height={250}
                />
              </CardContent>
            </Card>
          </motion.div>

          {/* Sidebar */}
          <motion.div variants={itemVariants} className="space-y-6">
            {/* Subscription Status */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CreditCardIcon className="w-5 h-5" />
                  Subscription Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {currentSubscription ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Plan</span>
                      <Badge variant="secondary" className="capitalize">
                        {currentSubscription.plan.type}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Status</span>
                      <Badge
                        variant={currentSubscription.status === 'active' ? 'default' : 'secondary'}
                        className="capitalize"
                      >
                        {currentSubscription.status}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Auto-renew</span>
                      <span className={`text-sm ${currentSubscription.autoRenew ? 'text-green-600' : 'text-red-600'}`}>
                        {currentSubscription.autoRenew ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                    <div className="pt-4 border-t">
                      <Button asChild className="w-full">
                        <Link href="/billing/subscription">
                          Manage Subscription
                          <ArrowRightIcon className="w-4 h-4 ml-2" />
                        </Link>
                      </Button>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="text-sm text-gray-600 mb-4">
                      You're currently on the Free plan. Upgrade to unlock more features and higher limits.
                    </p>
                    <Button asChild className="w-full">
                      <Link href="/billing/subscription">
                        Upgrade Now
                        <ArrowRightIcon className="w-4 h-4 ml-2" />
                      </Link>
                    </Button>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Quota Status */}
            {quotaInfo && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <ClockIcon className="w-5 h-5" />
                    Quota Status
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* API Calls Quota */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">API Calls</span>
                      <span className="text-sm text-gray-600">
                        {quotaInfo.apiCalls.used.toLocaleString()} / {quotaInfo.apiCalls.limit.toLocaleString()}
                      </span>
                    </div>
                    <Progress
                      value={getUsagePercentage(quotaInfo.apiCalls.used, quotaInfo.apiCalls.limit)}
                      className="h-2"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      {quotaInfo.apiCalls.remaining.toLocaleString()} remaining
                    </p>
                  </div>

                  {/* Token Usage */}
                  {quotaInfo.tokens.limit > 0 && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium">Tokens</span>
                        <span className="text-sm text-gray-600">
                          {quotaInfo.tokens.used.toLocaleString()} / {quotaInfo.tokens.limit.toLocaleString()}
                        </span>
                      </div>
                      <Progress
                        value={getUsagePercentage(quotaInfo.tokens.used, quotaInfo.tokens.limit)}
                        className="h-2"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {quotaInfo.tokens.remaining.toLocaleString()} remaining
                      </p>
                    </div>
                  )}

                  {/* Storage Quota */}
                  {quotaInfo.storage.limit > 0 && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium">Storage</span>
                        <span className="text-sm text-gray-600">
                          {(quotaInfo.storage.used / 1024).toFixed(1)}GB / {(quotaInfo.storage.limit / 1024).toFixed(1)}GB
                        </span>
                      </div>
                      <Progress
                        value={getUsagePercentage(quotaInfo.storage.used, quotaInfo.storage.limit)}
                        className="h-2"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        {(quotaInfo.storage.remaining / 1024).toFixed(1)}GB remaining
                      </p>
                    </div>
                  )}

                  <Button variant="outline" size="sm" asChild className="w-full">
                    <Link href="/billing/usage">
                      View Detailed Usage
                      <ArrowRightIcon className="w-4 h-4 ml-2" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button variant="outline" size="sm" asChild className="w-full justify-start">
                  <Link href="/billing/payments/methods">
                    <CreditCardIcon className="w-4 h-4 mr-2" />
                    Manage Payment Methods
                  </Link>
                </Button>
                <Button variant="outline" size="sm" asChild className="w-full justify-start">
                  <Link href="/billing/invoices">
                    <DocumentTextIcon className="w-4 h-4 mr-2" />
                    Download Invoices
                  </Link>
                </Button>
                <Button variant="outline" size="sm" asChild className="w-full justify-start">
                  <Link href="/billing/settings">
                    <CurrencyDollarIcon className="w-4 h-4 mr-2" />
                    Billing Settings
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </motion.div>
    </BillingLayout>
  );
};

export default BillingOverview;