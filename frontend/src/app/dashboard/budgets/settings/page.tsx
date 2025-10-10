'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';

// 类型定义
interface BudgetFormData {
  monthly_limit: number;
  alert_threshold: number;
  currency: string;
  organization_id: string;
}

interface Organization {
  id: string;
  name: string;
  slug: string;
}

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
}

export default function BudgetSettingsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedOrgId = searchParams.get('organization');

  const [loading, setLoading] = useState(false);
  const [fetchLoading, setFetchLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [existingBudget, setExistingBudget] = useState<Budget | null>(null);
  const [formData, setFormData] = useState<BudgetFormData>({
    monthly_limit: 1000,
    alert_threshold: 80,
    currency: 'USD',
    organization_id: preselectedOrgId || ''
  });

  useEffect(() => {
    fetchOrganizations();
  }, []);

  useEffect(() => {
    if (organizations.length > 0 && formData.organization_id) {
      checkExistingBudget();
    }
  }, [organizations, formData.organization_id]);

  const fetchOrganizations = async () => {
    try {
      const response = await fetch('/api/v1/organizations/');
      if (response.ok) {
        const data = await response.json();
        setOrganizations(data);
      }
    } catch (error) {
      console.error('Error fetching organizations:', error);
    } finally {
      setFetchLoading(false);
    }
  };

  const checkExistingBudget = async () => {
    if (!formData.organization_id) return;

    try {
      const response = await fetch(`/api/v1/organizations/${formData.organization_id}/budgets`);
      if (response.ok) {
        const budget = await response.json();
        setExistingBudget(budget);
        // Pre-fill form with existing budget data
        setFormData(prev => ({
          ...prev,
          monthly_limit: budget.monthly_limit,
          alert_threshold: budget.alert_threshold,
          currency: budget.currency
        }));
      } else {
        setExistingBudget(null);
      }
    } catch (error) {
      console.error('Error checking existing budget:', error);
      setExistingBudget(null);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'monthly_limit' || name === 'alert_threshold' ? parseFloat(value) || 0 : value
    }));
  };

  const validateForm = () => {
    if (!formData.organization_id) {
      setError('Organization is required');
      return false;
    }
    if (formData.monthly_limit <= 0) {
      setError('Monthly limit must be greater than 0');
      return false;
    }
    if (formData.alert_threshold < 0 || formData.alert_threshold > 100) {
      setError('Alert threshold must be between 0 and 100');
      return false;
    }
    if (!formData.currency || formData.currency.length !== 3) {
      setError('Currency must be a valid 3-letter code');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      const method = existingBudget ? 'PUT' : 'POST';
      const url = existingBudget
        ? `/api/v1/organizations/${formData.organization_id}/budgets`
        : `/api/v1/organizations/${formData.organization_id}/budgets`;

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to save budget');
      }

      const savedBudget = await response.json();
      setExistingBudget(savedBudget);
      setSuccess(existingBudget ? 'Budget updated successfully!' : 'Budget created successfully!');

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000);

    } catch (error) {
      console.error('Error saving budget:', error);
      setError(error instanceof Error ? error.message : 'Failed to save budget');
    } finally {
      setLoading(false);
    }
  };

  if (fetchLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (organizations.length === 0) {
    return (
      <div className="p-6">
        <div className="text-center py-12">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No organizations available</h3>
          <p className="mt-1 text-sm text-gray-500">
            You need to create an organization first before you can set up budgets.
          </p>
          <div className="mt-6">
            <Link
              href="/dashboard/organizations/create"
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Create Organization
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <div className="flex items-center space-x-3">
          <Link
            href="/dashboard/budgets"
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Budget Settings</h1>
        </div>
        <p className="mt-1 text-sm text-gray-600">
          {existingBudget ? 'Update your budget settings and alert preferences' : 'Set up budget monitoring and alert settings'}
        </p>
      </div>

      <div className="max-w-2xl">
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
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
          )}

          {success && (
            <div className="bg-green-50 border border-green-200 rounded-md p-4">
              <div className="flex">
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-green-800">Success</h3>
                  <div className="mt-2 text-sm text-green-700">
                    {success}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
            <div className="space-y-6">
              <div>
                <label htmlFor="organization_id" className="block text-sm font-medium text-gray-700">
                  Organization *
                </label>
                <div className="mt-1">
                  <select
                    name="organization_id"
                    id="organization_id"
                    required
                    value={formData.organization_id}
                    onChange={handleInputChange}
                    className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  >
                    <option value="">Select an organization</option>
                    {organizations.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.name}
                      </option>
                    ))}
                  </select>
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  The organization this budget will apply to
                </p>
              </div>

              <div>
                <label htmlFor="monthly_limit" className="block text-sm font-medium text-gray-700">
                  Monthly Budget Limit *
                </label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <span className="text-gray-500 sm:text-sm">$</span>
                  </div>
                  <input
                    type="number"
                    name="monthly_limit"
                    id="monthly_limit"
                    required
                    min="0.01"
                    step="0.01"
                    value={formData.monthly_limit}
                    onChange={handleInputChange}
                    className="block w-full pl-7 pr-12 border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="1000.00"
                  />
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                    <span className="text-gray-500 sm:text-sm">USD</span>
                  </div>
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  The maximum amount your organization can spend per month
                </p>
              </div>

              <div>
                <label htmlFor="alert_threshold" className="block text-sm font-medium text-gray-700">
                  Alert Threshold *
                </label>
                <div className="mt-1 relative rounded-md shadow-sm">
                  <input
                    type="number"
                    name="alert_threshold"
                    id="alert_threshold"
                    required
                    min="0"
                    max="100"
                    step="1"
                    value={formData.alert_threshold}
                    onChange={handleInputChange}
                    className="block w-full pr-12 border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="80"
                  />
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                    <span className="text-gray-500 sm:text-sm">%</span>
                  </div>
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  Send alerts when usage reaches this percentage of the budget limit
                </p>
              </div>

              <div>
                <label htmlFor="currency" className="block text-sm font-medium text-gray-700">
                  Currency *
                </label>
                <div className="mt-1">
                  <select
                    name="currency"
                    id="currency"
                    required
                    value={formData.currency}
                    onChange={handleInputChange}
                    className="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  >
                    <option value="USD">USD - US Dollar</option>
                    <option value="EUR">EUR - Euro</option>
                    <option value="GBP">GBP - British Pound</option>
                    <option value="JPY">JPY - Japanese Yen</option>
                    <option value="CAD">CAD - Canadian Dollar</option>
                    <option value="AUD">AUD - Australian Dollar</option>
                  </select>
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  The currency used for budget tracking and reporting
                </p>
              </div>
            </div>
          </div>

          {/* Budget Recommendations */}
          {formData.monthly_limit > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
              <div className="flex">
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800">Budget Recommendations</h3>
                  <div className="mt-2 text-sm text-blue-700">
                    <ul className="list-disc list-inside space-y-1">
                      <li>Start with a conservative budget and monitor usage for the first month</li>
                      <li>Set alerts at 70-80% to avoid unexpected overages</li>
                      <li>Review spending patterns monthly and adjust as needed</li>
                      <li>Consider seasonal usage patterns when setting limits</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Current Budget Status */}
          {existingBudget && (
            <div className="bg-gray-50 rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Current Budget Status</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">Current Usage</span>
                  <span className="text-sm text-gray-900">
                    ${existingBudget.current_spend.toFixed(2)} / ${existingBudget.monthly_limit.toFixed(2)}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      existingBudget.usage_percentage > 90
                        ? 'bg-red-600'
                        : existingBudget.usage_percentage > 80
                        ? 'bg-yellow-600'
                        : 'bg-green-600'
                    }`}
                    style={{ width: `${Math.min(existingBudget.usage_percentage, 100)}%` }}
                  ></div>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Usage Percentage:</span>
                    <span className="ml-2 font-medium">{existingBudget.usage_percentage.toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Remaining:</span>
                    <span className="ml-2 font-medium">${existingBudget.remaining_budget.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              type="submit"
              disabled={loading}
              className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  {existingBudget ? 'Updating...' : 'Creating...'}
                </>
              ) : (
                existingBudget ? 'Update Budget' : 'Create Budget'
              )}
            </button>
            <Link
              href="/dashboard/budgets"
              className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
            >
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}