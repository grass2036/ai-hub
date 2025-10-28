/**
 * 使用量管理页面
 *
 * 提供详细的使用量统计、配额状态、成本分析等功能。
 */

'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ChartBarIcon,
  ServerIcon,
  CpuChipIcon,
  CurrencyDollarIcon,
  FunnelIcon,
  CalendarIcon,
  DownloadIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

import { BillingLayout, BillingHeader } from '@/components/billing/billing-layout';
import { UsageDashboard } from '@/components/billing/usage-dashboard';
import { useUsageManagement } from '@/store/billing-store';
import { UsageType } from '@/types/billing';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Separator } from '@/components/ui/separator';

export default function UsagePage() {
  const { usageStats, quotaInfo, loading, actions } = useUsageManagement();

  const [timeRange, setTimeRange] = useState('7d');
  const [usageType, setUsageType] = useState<UsageType | undefined>(undefined);
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    // Load initial data
    const endDate = new Date();
    const startDate = new Date();

    switch (timeRange) {
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

    actions.getUsageStats(startDate.toISOString(), endDate.toISOString(), usageType);
    actions.getQuotaStatus();
  }, [actions, timeRange, usageType]);

  const handleDateRangeChange = (startDate: string, endDate: string) => {
    actions.getUsageStats(startDate, endDate, usageType);
  };

  const handleUsageTypeChange = (type: UsageType | undefined) => {
    setUsageType(type);
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 7); // Default to 7 days

    actions.getUsageStats(startDate.toISOString(), endDate.toISOString(), type);
  };

  const handleRefresh = () => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - parseInt(timeRange.replace('d', '')));

    actions.getUsageStats(startDate.toISOString(), endDate.toISOString(), usageType);
    actions.getQuotaStatus();
  };

  // Generate mock detailed usage data
  const generateDetailedUsageData = () => {
    const data = [];
    const days = parseInt(timeRange.replace('d', ''));

    for (let i = days - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);

      // Generate hourly data for the selected day
      const hourlyData = {};
      for (let hour = 0; hour < 24; hour++) {
        hourlyData[hour] = {
          requests: Math.floor(Math.random() * 100) + 10,
          tokens: Math.floor(Math.random() * 10000) + 1000,
          cost: Math.random() * 2 + 0.1,
          model: Math.random() > 0.5 ? 'gpt-3.5-turbo' : 'gpt-4',
          endpoint: '/api/v1/chat/completions',
        };
      }

      data.push({
        date: date.toISOString(),
        requests: Math.floor(Math.random() * 1000) + 500,
        tokens: Math.floor(Math.random() * 50000) + 10000,
        cost: Math.random() * 5 + 0.5,
        modelUsage: {
          'gpt-3.5-turbo': Math.floor(Math.random() * 60) + 20,
          'gpt-4': Math.floor(Math.random() * 30) + 10,
          'claude-instant': Math.floor(Math.random() * 15) + 5,
          'claude-2': Math.floor(Math.random() * 10) + 2,
        },
        endpointUsage: {
          '/api/v1/chat/completions': Math.floor(Math.random() * 70) + 20,
          '/api/v1/embeddings': Math.floor(Math.random() * 20) + 5,
          '/api/v1/models': Math.floor(Math.random() * 10) + 2,
        },
        hourlyData,
      });
    }

    return data;
  };

  const detailedUsageData = generateDetailedUsageData();

  const UsageTable: React.FC<{
    data: any[];
    type: 'requests' | 'tokens' | 'cost';
  }> = ({ data, type }) => {
    const formatValue = (value: number) => {
      switch (type) {
        case 'requests':
          return value.toLocaleString();
        case 'tokens':
          return `${(value / 1000).toFixed(1)}K`;
        case 'cost':
          return `$${value.toFixed(2)}`;
        default:
          return value.toString();
      }
    };

    return (
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Model</TableHead>
              <TableHead>Endpoint</TableHead>
              <TableHead>Requests</TableHead>
              <TableHead>Tokens</TableHead>
              <TableHead>Cost</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((item, index) => (
              <TableRow key={index}>
                <TableCell className="font-medium">
                  {new Date(item.date).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <div className="space-y-1">
                    {Object.entries(item.modelUsage).map(([model, usage]) => (
                      <div key={model} className="flex items-center gap-2 text-sm">
                        <span>{model}</span>
                        <Badge variant="secondary" className="text-xs">
                          {usage}%
                        </Badge>
                      </div>
                    ))}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="space-y-1">
                    {Object.entries(item.endpointUsage).map(([endpoint, usage]) => (
                      <div key={endpoint} className="text-sm">
                        <div className="font-medium">{endpoint}</div>
                        <Badge variant="outline" className="text-xs">
                          {usage}%
                        </Badge>
                      </div>
                    ))}
                  </div>
                </TableCell>
                <TableCell>{formatValue(item.requests)}</TableCell>
                <TableCell>{formatValue(item.tokens)}</TableCell>
                <TableCell className="font-medium">
                  {formatValue(item.cost)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  };

  return (
    <BillingLayout>
      <div className="space-y-6">
        <BillingHeader
          title="Usage Analytics"
          description="Monitor your API usage, track costs, and manage your quotas"
          actions={
            <Button onClick={handleRefresh} variant="outline">
              <ArrowPathIcon className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          }
          breadcrumb={[
            { name: 'Billing', href: '/billing' },
            { name: 'Usage' },
          ]}
        />

        {/* Filters */}
        <Card className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <Select value={timeRange} onValueChange={setTimeRange}>
                <SelectTrigger className="w-full md:w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7d">Last 7 days</SelectItem>
                  <SelectItem value="30d">Last 30 days</SelectItem>
                  <SelectItem value="90d">Last 90 days</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1">
              <Select value={usageType || 'all'} onValueChange={(value) =>
                handleUsageTypeChange(value === 'all' ? undefined : value as UsageType)
              }>
                <SelectTrigger className="w-full md:w-48">
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
        </Card>

        {/* Main Content */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
            <TabsTrigger value="detailed">Detailed Usage</TabsTrigger>
            <TabsTrigger value="quotas">Quota Status</TabsTrigger>
            <TabsTrigger value="export">Export Data</TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            {usageStats && quotaInfo && (
              <UsageDashboard
                usageStats={usageStats}
                quotaInfo={quotaInfo}
                onDateRangeChange={handleDateRangeChange}
                onUsageTypeChange={handleUsageTypeChange}
                loading={loading}
              />
            )}
          </TabsContent>

          <TabsContent value="detailed" className="space-y-6">
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Detailed Usage Breakdown
              </h3>

              <div className="space-y-4">
                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Card className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <ServerIcon className="w-5 h-5 text-blue-600" />
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">Total Requests</div>
                        <div className="text-xl font-bold text-gray-900">
                          {detailedUsageData.reduce((sum, item) => sum + item.requests, 0).toLocaleString()}
                        </div>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                        <CpuChipIcon className="w-5 h-5 text-green-600" />
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">Total Tokens</div>
                        <div className="text-xl font-bold text-gray-900">
                          {(detailedUsageData.reduce((sum, item) => sum + item.tokens, 0) / 1000).toFixed(1)}K
                        </div>
                      </div>
                    </div>
                  </Card>

                  <Card className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
                        <CurrencyDollarIcon className="w-5 h-5 text-yellow-600" />
                      </div>
                      <div>
                        <div className="text-sm text-gray-600">Total Cost</div>
                        <div className="text-xl font-bold text-gray-900">
                          ${detailedUsageData.reduce((sum, item) => sum + item.cost, 0).toFixed(2)}
                        </div>
                      </div>
                    </div>
                  </Card>
                </div>

                <Separator />

                {/* Usage Table */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-medium text-gray-900">Usage Details</h4>
                    <Button variant="outline" size="sm">
                      <DownloadIcon className="w-4 h-4 mr-2" />
                      Export CSV
                    </Button>
                  </div>

                  <UsageTable
                    data={detailedUsageData.slice(0, 10)}
                    type="requests"
                  />
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="quotas" className="space-y-6">
            {quotaInfo ? (
              <>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <Card className="p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      API Call Quota
                    </h3>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Used</span>
                        <span className="font-medium text-gray-900">
                          {quotaInfo.apiCalls.used.toLocaleString()}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Limit</span>
                        <span className="font-medium text-gray-900">
                          {quotaInfo.apiCalls.limit.toLocaleString()}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Remaining</span>
                        <span className={cn(
                          'font-medium',
                          quotaInfo.apiCalls.remaining > 0 ? 'text-green-600' : 'text-red-600'
                        )}>
                          {quotaInfo.apiCalls.remaining.toLocaleString()}
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{
                            width: `${Math.min((quotaInfo.apiCalls.used / quotaInfo.apiCalls.limit) * 100, 100)}%`
                          }}
                        />
                      </div>
                      <div className="text-xs text-gray-500">
                        Resets on {new Date(quotaInfo.apiCalls.resetAt).toLocaleDateString()}
                      </div>
                    </div>
                  </Card>

                  <Card className="p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      Token Quota
                    </h3>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Used</span>
                        <span className="font-medium text-gray-900">
                          {quotaInfo.tokens.used.toLocaleString()}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Limit</span>
                        <span className="font-medium text-gray-900">
                          {quotaInfo.tokens.limit.toLocaleString()}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Remaining</span>
                        <span className={cn(
                          'font-medium',
                          quotaInfo.tokens.remaining > 0 ? 'text-green-600' : 'text-red-600'
                        )}>
                          {quotaInfo.tokens.remaining.toLocaleString()}
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-green-600 h-2 rounded-full transition-all duration-300"
                          style={{
                            width: `${Math.min((quotaInfo.tokens.used / quotaInfo.tokens.limit) * 100, 100)}%`
                          }}
                        />
                      </div>
                      <div className="text-xs text-gray-500">
                        Resets on {new Date(quotaInfo.tokens.resetAt).toLocaleDateString()}
                      </div>
                    </div>
                  </Card>

                  <Card className="p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      Storage Quota
                    </h3>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Used</span>
                        <span className="font-medium text-gray-900">
                          {quotaInfo.storage.used} GB
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Limit</span>
                        <span className="font-medium text-gray-900">
                          {quotaInfo.storage.limit} GB
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Remaining</span>
                        <span className={cn(
                          'font-medium',
                          quotaInfo.storage.remaining > 0 ? 'text-green-600' : 'text-red-600'
                        )}>
                          {quotaInfo.storage.remaining} GB
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                          style={{
                            width: `${Math.min((quotaInfo.storage.used / quotaInfo.storage.limit) * 100, 100)}%`
                          }}
                        />
                      </div>
                    </div>
                  </Card>

                  <Card className="p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                      Rate Limits
                    </h3>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Requests per minute</span>
                        <span className="font-medium text-gray-900">
                          {quotaInfo.rateLimit.requestsPerMinute}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Requests per day</span>
                        <span className="font-medium text-gray-900">
                          {quotaInfo.rateLimit.requestsPerDay.toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </Card>
                </div>

                {/* Quota Warnings */}
                {quotaInfo.warnings && quotaInfo.warnings.length > 0 && (
                  <Card className="p-4 bg-yellow-50 border border-yellow-200">
                    <div className="space-y-2">
                      <h4 className="font-medium text-yellow-800">Quota Warnings</h4>
                      {quotaInfo.warnings.map((warning, index) => (
                        <div key={index} className="flex items-start gap-2 text-sm text-yellow-800">
                          <span>•</span>
                          <span>{warning.message}</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}
              </>
            ) : (
              <Card className="p-12 text-center">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <FunnelIcon className="w-6 h-6 text-gray-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Loading quota information...
                </h3>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="export" className="space-y-6">
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Export Usage Data
              </h3>

              <div className="space-y-4">
                <div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Button variant="outline" className="flex items-center gap-2">
                      <DownloadIcon className="w-4 h-4" />
                      Export as CSV
                    </Button>
                    <Button variant="outline" className="flex items-center gap-2">
                      <DownloadIcon className="w-4 h-4" />
                      Export as JSON
                    </Button>
                    <Button variant="outline" className="flex items-center gap-2">
                      <DownloadIcon className="w-4 h-4" />
                      Export as PDF Report
                    </Button>
                    <Button variant="outline" className="flex items-center gap-2">
                      <DownloadIcon className="w-4 h-4" />
                      Export as Excel
                    </Button>
                  </div>
                </div>

                <Separator />

                <div className="text-sm text-gray-600">
                  <h4 className="font-medium text-gray-900 mb-2">Export Options:</h4>
                  <ul className="space-y-1 list-disc list-inside">
                    <li>Choose your preferred file format</li>
                    <li>Select date range and usage type filters</li>
                    <li>Include detailed breakdowns by model and endpoint</li>
                    <li>Download automatically or receive via email</li>
                  </ul>
                </div>

                <div className="text-sm text-gray-600">
                  <h4 className="font-medium text-gray-900 mb-2">Scheduled Reports:</h4>
                  <p>
                    You can also set up automated reports to be sent to your email address on a daily, weekly, or monthly basis. Configure this in your notification settings.
                  </p>
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </BillingLayout>
  );
}