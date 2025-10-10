'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

// 类型定义
interface OrgApiKey {
  id: string;
  organization_id: string;
  name: string;
  key_prefix: string;
  status: 'active' | 'suspended' | 'revoked';
  last_used_at?: string;
  created_by?: string;
  created_at: string;
  expires_at?: string;
  current_month_usage: number;
  daily_average_usage: number;
  quota_usage_percentage: number;
  is_active: boolean;
  is_expired: boolean;
  days_until_expiry?: number;
  rate_limit: number;
  monthly_quota: number;
  permissions: Record<string, any>;
  organization_name?: string;
}

interface Organization {
  id: string;
  name: string;
  slug: string;
}

interface ApiKeyFormData {
  name: string;
  organization_id: string;
  permissions: Record<string, any>;
  rate_limit: number;
  monthly_quota: number;
  expires_at?: string;
}

export default function APIKeysPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedOrgId = searchParams.get('organization');

  const [keys, setKeys] = useState<OrgApiKey[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [filterOrg, setFilterOrg] = useState<string>(preselectedOrgId || '');
  const [createdKey, setCreatedKey] = useState<any>(null);
  const [newKeyData, setNewKeyData] = useState<ApiKeyFormData>({
    name: '',
    organization_id: preselectedOrgId || '',
    permissions: {
      chat: ['read', 'write'],
      models: ['read']
    },
    rate_limit: 100,
    monthly_quota: 10000,
    expires_at: ''
  });

  useEffect(() => {
    fetchOrganizations();
  }, []);

  useEffect(() => {
    if (organizations.length > 0) {
      fetchApiKeys();
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

  const fetchApiKeys = async () => {
    try {
      setLoading(true);

      let url = '/api/v1/api-keys';
      if (filterOrg) {
        url = `/api/v1/organizations/${filterOrg}/api-keys`;
      }

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error('Failed to fetch API keys');
      }

      const data = await response.json();

      // For each API key, get organization name
      const keysWithOrgName = await Promise.all(
        data.map(async (key: OrgApiKey) => {
          try {
            const orgResponse = await fetch(`/api/v1/organizations/${key.organization_id}`);
            const org = orgResponse.ok ? await orgResponse.json() : null;

            return {
              ...key,
              organization_name: org?.name || 'Unknown Organization'
            };
          } catch (error) {
            console.error(`Error fetching org name for key ${key.id}:`, error);
            return {
              ...key,
              organization_name: 'Unknown Organization'
            };
          }
        })
      );

      setKeys(keysWithOrgName);
    } catch (error) {
      console.error('Error fetching API keys:', error);
      setError('Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch(`/api/v1/organizations/${newKeyData.organization_id}/api-keys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newKeyData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to create API key');
      }

      const result = await response.json();
      setCreatedKey(result);
      setShowCreateModal(false);
      setSuccess('API key created successfully!');

      // Reset form
      setNewKeyData({
        name: '',
        organization_id: preselectedOrgId || '',
        permissions: {
          chat: ['read', 'write'],
          models: ['read']
        },
        rate_limit: 100,
        monthly_quota: 10000,
        expires_at: ''
      });

      // Refresh keys list
      fetchApiKeys();
    } catch (error) {
      console.error('Error creating API key:', error);
      setError(error instanceof Error ? error.message : 'Failed to create API key');
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    if (!confirm('Are you sure you want to revoke this API key? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/api-keys/${keyId}/revoke`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to revoke API key');
      }

      setSuccess('API key revoked successfully');
      fetchApiKeys();
    } catch (error) {
      console.error('Error revoking API key:', error);
      setError('Failed to revoke API key');
    }
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      active: 'bg-green-100 text-green-800',
      suspended: 'bg-yellow-100 text-yellow-800',
      revoked: 'bg-red-100 text-red-800'
    };

    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status as keyof typeof styles] || styles.active}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const getQuotaHealthColor = (usagePercentage: number) => {
    if (usagePercentage > 90) return 'text-red-600';
    if (usagePercentage > 80) return 'text-yellow-600';
    return 'text-green-600';
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
            <p className="mt-1 text-sm text-gray-600">
              Manage your organization API keys and monitor usage
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Create API Key
          </button>
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

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
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
        <div className="bg-green-50 border border-green-200 rounded-md p-4 mb-6">
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

      {keys.length === 0 ? (
        <div className="text-center py-12">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 012-7.724M17 9h6M7 9h6M5 7a2 2 0 012-2m4 0a6 6 0 012 7.724M9 3H3m6 6v6m6-6v6m0 6h6m-6-0h6" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No API keys</h3>
          <p className="mt-1 text-sm text-gray-500">
            {filterOrg
              ? `No API keys found for the selected organization.`
              : 'Get started by creating your first API key.'
            }
          </p>
          <div className="mt-6">
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Create API Key
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {keys.map((key) => (
            <div key={key.id} className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <h3 className="text-lg font-medium text-gray-900">{key.name}</h3>
                    {getStatusBadge(key.status)}
                  </div>
                  <div className="flex items-center space-x-2">
                    {key.is_active && (
                      <button
                        onClick={() => handleRevokeKey(key.id)}
                        className="inline-flex items-center px-3 py-1.5 border border-red-300 shadow-sm text-xs font-medium rounded text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                      >
                        Revoke
                      </button>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                  <div>
                    <p className="text-sm text-gray-600">API Key</p>
                    <p className="text-sm font-mono text-gray-900 bg-gray-100 px-2 py-1 rounded">
                      {key.key_prefix}...
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Organization</p>
                    <p className="text-sm text-gray-900">{key.organization_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Created</p>
                    <p className="text-sm text-gray-900">
                      {new Date(key.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="text-center p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">Monthly Usage</p>
                    <p className="text-lg font-semibold text-gray-900">
                      {key.current_month_usage.toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-500">requests</p>
                  </div>
                  <div className="text-center p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">Quota Usage</p>
                    <p className={`text-lg font-semibold ${getQuotaHealthColor(key.quota_usage_percentage)}`}>
                      {key.quota_usage_percentage.toFixed(1)}%
                    </p>
                    <p className="text-xs text-gray-500">of {key.monthly_quota.toLocaleString()}</p>
                  </div>
                  <div className="text-center p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">Rate Limit</p>
                    <p className="text-lg font-semibold text-gray-900">
                      {key.rate_limit}
                    </p>
                    <p className="text-xs text-gray-500">requests/min</p>
                  </div>
                  <div className="text-center p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">Daily Average</p>
                    <p className="text-lg font-semibold text-gray-900">
                      {key.daily_average_usage.toFixed(0)}
                    </p>
                    <p className="text-xs text-gray-500">requests/day</p>
                  </div>
                </div>

                {/* Quota Progress Bar */}
                <div className="mt-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">Monthly Quota</span>
                    <span className={`text-sm font-medium ${getQuotaHealthColor(key.quota_usage_percentage)}`}>
                      {key.current_month_usage} / {key.monthly_quota}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        key.quota_usage_percentage > 90
                          ? 'bg-red-600'
                          : key.quota_usage_percentage > 80
                          ? 'bg-yellow-600'
                          : 'bg-green-600'
                      }`}
                      style={{ width: `${Math.min(key.quota_usage_percentage, 100)}%` }}
                    ></div>
                  </div>
                </div>

                {key.expires_at && (
                  <div className="mt-4 text-sm text-gray-500">
                    <span className="font-medium">Expires:</span>{' '}
                    {new Date(key.expires_at).toLocaleDateString()}
                    {key.days_until_expiry !== undefined && key.days_until_expiry <= 30 && (
                      <span className="ml-2 text-yellow-600">
                        ({key.days_until_expiry} days remaining)
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create API Key Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900">Create New API Key</h3>
              <form onSubmit={handleCreateKey} className="mt-4 space-y-4">
                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-md p-3">
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-700">Organization</label>
                  <select
                    name="organization_id"
                    value={newKeyData.organization_id}
                    onChange={(e) => setNewKeyData({ ...newKeyData, organization_id: e.target.value })}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    required
                  >
                    <option value="">Select organization</option>
                    {organizations.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Key Name</label>
                  <input
                    type="text"
                    name="name"
                    value={newKeyData.name}
                    onChange={(e) => setNewKeyData({ ...newKeyData, name: e.target.value })}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="Production API Key"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Rate Limit (requests/min)</label>
                  <input
                    type="number"
                    name="rate_limit"
                    value={newKeyData.rate_limit}
                    onChange={(e) => setNewKeyData({ ...newKeyData, rate_limit: parseInt(e.target.value) || 100 })}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    min="1"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Monthly Quota</label>
                  <input
                    type="number"
                    name="monthly_quota"
                    value={newKeyData.monthly_quota}
                    onChange={(e) => setNewKeyData({ ...newKeyData, monthly_quota: parseInt(e.target.value) || 10000 })}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    min="0"
                  />
                </div>

                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    Create Key
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* API Key Created Modal */}
      {createdKey && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <div className="flex items-center mb-4">
                <div className="flex-shrink-0 w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-lg font-medium text-gray-900">API Key Created</h3>
                </div>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4">
                <p className="text-sm text-yellow-800">
                  <strong>Important:</strong> Save this API key now. It won't be shown again.
                </p>
              </div>

              <div className="bg-gray-100 rounded p-3 mb-4">
                <p className="text-xs text-gray-600 mb-1">API Key:</p>
                <div className="flex items-center justify-between">
                  <code className="text-sm font-mono break-all">
                    {createdKey.api_key}
                  </code>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(createdKey.api_key);
                      alert('API key copied to clipboard!');
                    }}
                    className="ml-2 p-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </button>
                </div>
              </div>

              <div className="flex justify-end">
                <button
                  onClick={() => setCreatedKey(null)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  I've Saved It
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}