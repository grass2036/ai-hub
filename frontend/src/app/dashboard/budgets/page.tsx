'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';

// 类型定义
interface Budget {
  id: string;
  organization_id: string;
  monthly_limit: number;
  current_spend: number;
  alert_threshold: number;
  currency: string;
  status: string;
  usage_percentage: number;
  remaining_budget: number;
  projected_monthly_spend: number;
  days_remaining_in_month: number;
  organization_name?: string;
}

interface Organization {
  id: string;
  name: string;
  slug: string;
}

interface UsageRecord {
  date: string;
  cost: number;
  tokens: number;
  requests: number;
}

export default function BudgetsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedOrgId = searchParams.get('organization');

  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [usageHistory, setUsageHistory] = useState<{ [key: string]: UsageRecord[] }>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterOrg, setFilterOrg] = useState<string>(selectedOrgId || '');

  useEffect(() => {
    fetchOrganizations();
  }, []);

  useEffect(() => {
    if (organizations.length > 0) {
      fetchBudgets();
    }
  }, [organizations, filterOrg]);

  const fetchOrganizations = async () => {
    try {
      const response = await fetch('/api/v1/organizations/');
      if (response.ok) {
        const data = await response.json();
        setOrganizations(data);
      }
    } catch (error) {
      console.error('Error fetching organizations:', error);
    }
  };

  const fetchBudgets = async () => {
    try {
      setLoading(true);

      let url = '/api/v1/budgets/';
      if (filterOrg) {
        url = `/api/v1/organizations/${filterOrg}/budgets`;
      }

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error('Failed to fetch budgets');
      }

      const data = Array.isArray(response) ? [] : await response.json();

      // Handle both single budget and array responses
      const budgetArray = Array.isArray(data) ? data : (data ? [data] : []);

      // For each budget, get organization name and usage history
      const budgetsWithDetails = await Promise.all(
        budgetArray.map(async (budget: Budget) => {
          try {
            // Get organization name
            const orgResponse = await fetch(`/api/v1/organizations/${budget.organization_id}`);
            const org = orgResponse.ok ? await orgResponse.json() : null;

            // Get usage history
            const usageResponse = await fetch(`/api/v1/organizations/${budget.organization_id}/budgets/usage?days=30`);
            const usageData = usageResponse.ok ? await usageResponse.json() : { usage_history: [] };

            return {
              ...budget,
              organization_name: org?.name || 'Unknown Organization',
              usage_history: usageData.usage_history || []
            };
          } catch (error) {
            console.error(`Error fetching details for budget ${budget.id}:`, error);
            return {
              ...budget,
              organization_name: 'Unknown Organization',
              usage_history: []
            };
          }
        })
      );

      setBudgets(budgetsWithDetails);

      // Collect usage history by organization
      const historyByOrg: { [key: string]: UsageRecord[] } = {};
      budgetsWithDetails.forEach(budget => {
        if (budget.usage_history && budget.usage_history.length > 0) {
          historyByOrg[budget.organization_id] = budget.usage_history;
        }
      });
      setUsageHistory(historyByOrg);

    } catch (error) {
      console.error('Error fetching budgets:', error);
      setError('Failed to load budgets');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      active: 'bg-green-100 text-green-800',
      inactive: 'bg-gray-100 text-gray-800',
      exceeded: 'bg-red-100 text-red-800'
    };

    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status as keyof typeof styles] || styles.active}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const getBudgetHealthColor = (usagePercentage: number) => {
    if (usagePercentage > 90) return 'text-red-600';
    if (usagePercentage > 80) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getBudgetHealthBg = (usagePercentage: number) => {
    if (usagePercentage > 90) return 'bg-red-100';
    if (usagePercentage > 80) return 'bg-yellow-100';
    return 'bg-green-100';
  };

  const calculateTotalBudgets = () => {
    return budgets.reduce((sum, budget) => sum + budget.monthly_limit, 0);
  };

  const calculateTotalSpend = () => {
    return budgets.reduce((sum, budget) => sum + budget.current_spend, 0);
  };

  const calculateAverageUsage = () => {
    if (budgets.length === 0) return 0;
    const totalUsage = budgets.reduce((sum, budget) => sum + budget.usage_percentage, 0);
    return totalUsage / budgets.length;
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <div className="mt-2 text-sm text-red-700">
                {error}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const totalBudgets = calculateTotalBudgets();
  const totalSpend = calculateTotalSpend();
  const averageUsage = calculateAverageUsage();

  return (
    <div className="p-6">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Budget Management</h1>
            <p className="mt-1 text-sm text-gray-600">
              Monitor and manage your organization budgets
            </p>
          </div>
          <Link
            href={`/dashboard/budgets/settings${filterOrg ? `?organization=${filterOrg}` : ''}`}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
            </svg>
            Budget Settings
          </Link>
        </div>
      </div>

      {/* Organization Filter */}
      {organizations.length > 0 && (
        <div className="mb-6">
          <label htmlFor="org-filter" className="block text-sm font-medium text-gray-700 mb-2">
            Filter by Organization
          </label>
          <select
            id="org-filter"
            value={filterOrg}
            onChange={(e) => setFilterOrg(e.target.value)}
            className="block w-full max-w-xs border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
          >
            <option value="">All Organizations</option>
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Summary Cards */}
      {budgets.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Budget</p>
                <p className="text-2xl font-bold text-gray-900">
                  ${totalBudgets.toFixed(2)}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Spend</p>
                <p className="text-2xl font-bold text-gray-900">
                  ${totalSpend.toFixed(2)}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-6 w-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Average Usage</p>
                <p className="text-2xl font-bold text-gray-900">
                  {averageUsage.toFixed(1)}%
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white shadow rounded-lg p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-6 w-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Active Budgets</p>
                <p className="text-2xl font-bold text-gray-900">
                  {budgets.length}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {budgets.length === 0 ? (
        <div className="text-center py-12">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No budgets found</h3>
          <p className="mt-1 text-sm text-gray-500">
            {filterOrg
              ? `No budgets found for the selected organization.`
              : 'Get started by creating your first budget.'
            }
          </p>
          <div className="mt-6">
            <Link
              href={`/dashboard/budgets/settings${filterOrg ? `?organization=${filterOrg}` : ''}`}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
              </svg>
              Create Budget
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {budgets.map((budget) => (
            <div key={budget.id} className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <h3 className="text-lg font-medium text-gray-900">
                      {budget.organization_name} Budget
                    </h3>
                    {getStatusBadge(budget.status)}
                  </div>
                  <div className="flex items-center space-x-2">
                    <Link
                      href={`/dashboard/budgets/settings?organization=${budget.organization_id}`}
                      className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Edit
                    </Link>
                  </div>
                </div>

                {/* Budget Progress */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">Budget Usage</span>
                    <span className={`text-sm font-medium ${getBudgetHealthColor(budget.usage_percentage)}`}>
                      {budget.usage_percentage.toFixed(1)}% used
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full ${
                        budget.usage_percentage > 90
                          ? 'bg-red-600'
                          : budget.usage_percentage > 80
                          ? 'bg-yellow-600'
                          : 'bg-green-600'
                      }`}
                      style={{ width: `${Math.min(budget.usage_percentage, 100)}%` }}
                    ></div>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
                    <span>${budget.current_spend.toFixed(2)} spent</span>
                    <span>${budget.remaining_budget.toFixed(2)} remaining</span>
                  </div>
                </div>

                {/* Budget Details Grid */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                  <div className="text-center p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">Monthly Limit</p>
                    <p className="text-lg font-semibold text-gray-900">
                      ${budget.monthly_limit.toFixed(2)}
                    </p>
                  </div>
                  <div className="text-center p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">Current Spend</p>
                    <p className="text-lg font-semibold text-gray-900">
                      ${budget.current_spend.toFixed(2)}
                    </p>
                  </div>
                  <div className="text-center p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">Projected Spend</p>
                    <p className="text-lg font-semibold text-gray-900">
                      ${budget.projected_monthly_spend.toFixed(2)}
                    </p>
                  </div>
                  <div className="text-center p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">Alert Threshold</p>
                    <p className="text-lg font-semibold text-gray-900">
                      {budget.alert_threshold}%
                    </p>
                  </div>
                </div>

                {/* Mini Usage Chart */}
                {usageHistory[budget.organization_id] && usageHistory[budget.organization_id].length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 mb-3">30-Day Usage Trend</h4>
                    <div className="h-20 flex items-end space-x-1">
                      {usageHistory[budget.organization_id].slice(-14).map((record, index) => {
                        const maxValue = Math.max(...usageHistory[budget.organization_id].slice(-14).map(r => r.cost));
                        const height = maxValue > 0 ? (record.cost / maxValue) * 100 : 0;

                        return (
                          <div
                            key={index}
                            className="flex-1 bg-blue-200 rounded-t"
                            style={{ height: `${height}%` }}
                            title={`${record.date}: $${record.cost.toFixed(2)}`}
                          ></div>
                        );
                      })}
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>14 days ago</span>
                      <span>Today</span>
                    </div>
                  </div>
                )}

                {/* Alert Status */}
                {budget.usage_percentage >= budget.alert_threshold && (
                  <div className={`mt-4 p-3 rounded-md ${getBudgetHealthBg(budget.usage_percentage)}`}>
                    <div className="flex">
                      <div className="flex-shrink-0">
                        <svg className={`h-5 w-5 ${getBudgetHealthColor(budget.usage_percentage)}`} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div className="ml-3">
                        <p className={`text-sm font-medium ${getBudgetHealthColor(budget.usage_percentage)}`}>
                          {budget.usage_percentage > 90 ? 'Critical' : 'Warning'}: Budget Alert
                        </p>
                        <p className="text-sm text-gray-600">
                          {budget.usage_percentage > 90
                            ? `Budget usage (${budget.usage_percentage.toFixed(1)}%) is critically high. Consider reducing usage or increasing the budget limit.`
                            : `Budget usage (${budget.usage_percentage.toFixed(1)}%) has exceeded the alert threshold (${budget.alert_threshold}%).`
                          }
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}