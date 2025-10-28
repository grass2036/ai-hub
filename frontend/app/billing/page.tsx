/**
 * 计费首页 - 计费摘要仪表板
 *
 * 显示用户的计费摘要、当前订阅状态、使用量概览等信息。
 */

'use client';

import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  CreditCardIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  DocumentTextIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  ExclamationTriangleIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';

import { BillingLayout, BillingHeader, BillingStatsCard, BillingAlert } from '@/components/billing/billing-layout';
import { SubscriptionCard, SubscriptionSummary } from '@/components/billing/subscription-card';
import { UsageDashboard } from '@/components/billing/usage-dashboard';
import { useBillingData, useBillingActions } from '@/store/billing-store';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function BillingPage() {
  const {
    currentSubscription,
    billingSummary,
    quotaInfo,
    loading,
  } = useBillingData();

  const actions = useBillingActions();

  useEffect(() => {
    // Load initial data
    actions.getBillingSummary();
    actions.getCurrentSubscription();
    actions.getQuotaStatus();
  }, [actions]);

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const handleUpgradeSubscription = () => {
    // Navigate to upgrade page or open upgrade modal
    window.location.href = '/billing/subscription/upgrade';
  };

  const handleManageSubscription = () => {
    window.location.href = '/billing/subscription';
  };

  if (loading) {
    return (
      <BillingLayout>
        <div className="space-y-6">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-64 mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-96"></div>
          </div>

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
      </BillingLayout>
    );
  }

  return (
    <BillingLayout>
      <div className="space-y-6">
        {/* Header */}
        <BillingHeader
          title="Billing Overview"
          description="Manage your subscription, track usage, and view your billing history"
          actions={
            billingSummary && (
              <div className="flex items-center gap-3">
                <Button variant="outline" onClick={() => window.location.href = '/billing/invoices'}>
                  <DocumentTextIcon className="w-4 h-4 mr-2" />
                  View Invoices
                </Button>
                {currentSubscription && currentSubscription.plan.type !== 'enterprise' && (
                  <Button onClick={handleUpgradeSubscription}>
                    <ArrowUpIcon className="w-4 h-4 mr-2" />
                    Upgrade Plan
                  </Button>
                )}
              </div>
            )
          }
        />

        {/* Alerts */}
        {billingSummary && (
          <div className="space-y-4">
            {/* Trial Alert */}
            {currentSubscription?.isTrial && currentSubscription.trialEnd && (
              <BillingAlert
                type="info"
                title="Free Trial Active"
                message={`You have ${currentSubscription.daysInTrial} days left in your trial. Upgrade now to continue using our premium features.`}
                actions={
                  <Button onClick={handleUpgradeSubscription}>
                    <SparklesIcon className="w-4 h-4 mr-2" />
                    Upgrade Now
                  </Button>
                }
              />
            )}

            {/* Overdue Alert */}
            {currentSubscription?.status === 'past_due' && (
              <BillingAlert
                type="error"
                title="Payment Overdue"
                message="Your subscription payment is overdue. Please update your payment method to avoid service interruption."
                actions={
                  <Button onClick={handleManageSubscription}>
                    <CreditCardIcon className="w-4 h-4 mr-2" />
                    Update Payment
                  </Button>
                }
              />
            )}

            {/* Usage Warning */}
            {quotaInfo && (
              quotaInfo.apiCalls.percentageUsed >= 80 && (
                <BillingAlert
                  type="warning"
                  title="High Usage Alert"
                  message={`You've used ${quotaInfo.apiCalls.percentageUsed.toFixed(1)}% of your API calls quota this month. Consider upgrading your plan to avoid service interruption.`}
                  actions={
                    <Button onClick={handleUpgradeSubscription}>
                      <ArrowUpIcon className="w-4 h-4 mr-2" />
                      Upgrade Plan
                    </Button>
                  }
                />
              )
            )}
          </div>
        )}

        {/* Key Metrics */}
        {billingSummary && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <BillingStatsCard
              title="Current Plan"
              value={billingSummary.currentSubscription.planType.charAt(0).toUpperCase() +
                    billingSummary.currentSubscription.planType.slice(1)}
              icon={CreditCardIcon}
              description="Monthly subscription"
              trend="stable"
            />

            <BillingStatsCard
              title="This Month's Usage"
              value={billingSummary.usageThisMonth.totalRequests.toLocaleString()}
              change={12.5}
              changeType="increase"
              icon={ChartBarIcon}
              description="API requests"
              trend="up"
            />

            <BillingStatsCard
              title="Total Cost"
              value={formatCurrency(billingSummary.usageThisMonth.totalCost)}
              change={-5.2}
              changeType="decrease"
              icon={CurrencyDollarIcon}
              description="Current month charges"
              trend="down"
            />

            <BillingStatsCard
              title="Tokens Used"
              value={(billingSummary.usageThisMonth.totalTokens / 1000).toFixed(1) + 'K'}
              icon={ChartBarIcon}
              description="Input + output tokens"
              trend="stable"
            />
          </div>
        )}

        {/* Main Content Tabs */}
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="usage">Usage Details</TabsTrigger>
            <TabsTrigger value="subscription">Subscription</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            {/* Quick Stats */}
            {billingSummary && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Usage Overview */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Usage Overview</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Total Requests</span>
                      <span className="font-medium text-gray-900">
                        {billingSummary.usageThisMonth.totalRequests.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Successful</span>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-green-600">
                          {billingSummary.usageThisMonth.successfulRequests.toLocaleString()}
                        </span>
                        <Badge variant="secondary" className="text-xs">
                          {((billingSummary.usageThisMonth.successfulRequests / billingSummary.usageThisMonth.totalRequests) * 100).toFixed(1)}%
                        </Badge>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Failed</span>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-red-600">
                          {billingSummary.usageThisMonth.failedRequests.toLocaleString()}
                        </span>
                        <Badge variant="secondary" className="text-xs">
                          {((billingSummary.usageThisMonth.failedRequests / billingSummary.usageThisMonth.totalRequests) * 100).toFixed(1)}%
                        </Badge>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Total Tokens</span>
                      <span className="font-medium text-gray-900">
                        {(billingSummary.usageThisMonth.totalTokens / 1000).toFixed(1)}K
                      </span>
                    </div>
                  </div>
                </Card>

                {/* Cost Breakdown */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost Breakdown</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Base Subscription</span>
                      <span className="font-medium text-gray-900">
                        {formatCurrency(29.99)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Usage Charges</span>
                      <span className="font-medium text-gray-900">
                        {formatCurrency(billingSummary.usageThisMonth.totalCost - 29.99)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">Total This Month</span>
                      <span className="font-semibold text-lg text-blue-600">
                        {formatCurrency(billingSummary.usageThisMonth.totalCost)}
                      </span>
                    </div>
                    <div className="pt-3 border-t border-gray-200">
                      <div className="text-sm text-gray-600 mb-2">Projected Monthly Total</div>
                      <div className="text-lg font-semibold text-gray-900">
                        {formatCurrency(billingSummary.usageThisMonth.totalCost * 1.2)}
                      </div>
                      <div className="text-xs text-gray-500">Based on current usage trend</div>
                    </div>
                  </div>
                </Card>
              </div>
            )}

            {/* Recent Activity */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
              <div className="space-y-4">
                <div className="flex items-center gap-3 text-sm">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-gray-600">Payment processed successfully</span>
                  <span className="text-gray-500 ml-auto">2 hours ago</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <span className="text-gray-600">Subscription upgraded to Pro plan</span>
                  <span className="text-gray-500 ml-auto">3 days ago</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                  <span className="text-gray-600">Invoice generated</span>
                  <span className="text-gray-500 ml-auto">7 days ago</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                  <span className="text-gray-600">Free trial started</span>
                  <span className="text-gray-500 ml-auto">14 days ago</span>
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="usage">
            {quotaInfo && billingSummary && (
              <UsageDashboard
                usageStats={{
                  totalRequests: billingSummary.usageThisMonth.totalRequests,
                  successfulRequests: billingSummary.usageThisMonth.successfulRequests,
                  failedRequests: billingSummary.usageThisMonth.failedRequests,
                  totalInputTokens: Math.floor(billingSummary.usageThisMonth.totalTokens * 0.6),
                  totalOutputTokens: Math.floor(billingSummary.usageThisMonth.totalTokens * 0.4),
                  totalTokens: billingSummary.usageThisMonth.totalTokens,
                  totalCost: billingSummary.usageThisMonth.totalCost,
                  currency: 'USD',
                  averageResponseTime: 450,
                  p95ResponseTime: 1200,
                  successRate: (billingSummary.usageThisMonth.successfulRequests / billingSummary.usageThisMonth.totalRequests) * 100,
                  errorRate: (billingSummary.usageThisMonth.failedRequests / billingSummary.usageThisMonth.totalRequests) * 100,
                  modelUsage: {
                    'gpt-3.5-turbo': 45,
                    'gpt-4': 30,
                    'claude-instant': 20,
                    'claude-2': 5,
                  },
                  endpointUsage: {
                    '/api/v1/chat/completions': 70,
                    '/api/v1/embeddings': 20,
                    '/api/v1/models': 10,
                  },
                  hourlyUsage: {},
                }}
                quotaInfo={quotaInfo}
              />
            )}
          </TabsContent>

          <TabsContent value="subscription">
            {currentSubscription && (
              <div className="space-y-6">
                <SubscriptionCard
                  subscription={currentSubscription}
                  onUpgrade={handleUpgradeSubscription}
                  onManage={handleManageSubscription}
                />

                {/* Subscription Benefits */}
                <Card className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Plan Benefits</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-3">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="text-sm text-gray-700">API access to all models</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="text-sm text-gray-700">Priority support</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="text-sm text-gray-700">Advanced analytics</span>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="text-sm text-gray-700">Custom model training</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="text-sm text-gray-700">Team collaboration tools</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="text-sm text-gray-700">Enterprise-grade security</span>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </BillingLayout>
  );
}