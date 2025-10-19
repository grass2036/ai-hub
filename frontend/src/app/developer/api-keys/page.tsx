'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

// 类型定义
interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  permissions: string[];
  rate_limit: number;
  allowed_models: string[];
  is_active: boolean;
  expires_at?: string;
  last_used_at?: string;
  usage_count: number;
  total_tokens_used: number;
  created_at: string;
  updated_at: string;
}

interface DeveloperQuota {
  monthly_quota: number;
  monthly_used: number;
  monthly_remaining: number;
  monthly_usage_percent: number;
  monthly_cost: number;
  active_api_keys: number;
  max_api_keys: int;
  reset_date: string;
}

interface NewAPIKeyResponse {
  id: string;
  name: string;
  api_key: string;
  key_prefix: string;
  permissions: string[];
  rate_limit: number;
  allowed_models: string[];
  is_active: boolean;
  expires_at?: string;
  created_at: string;
}

export default function DeveloperAPIKeys() {
  const router = useRouter();
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [quota, setQuota] = useState<DeveloperQuota | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 模态框状态
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showKeySecret, setShowKeySecret] = useState(false);
  const [newKeySecret, setNewKeySecret] = useState<NewAPIKeyResponse | null>(null);

  // 表单状态
  const [formData, setFormData] = useState({
    name: '',
    permissions: ['chat.completions', 'chat.models', 'usage.view'],
    rate_limit: 100,
    allowed_models: [] as string[],
    expires_days: ''
  });

  // 可用权限和模型
  const [availablePermissions, setAvailablePermissions] = useState<any[]>([]);
  const [availableModels, setAvailableModels] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('developer_access_token');
      if (!token) {
        router.push('/developer/login');
        return;
      }

      try {
        // 并行获取数据
        const [keysResponse, quotaResponse, permissionsResponse, modelsResponse] = await Promise.all([
          fetch('/api/v1/developer/keys', {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch('/api/v1/developer/quota', {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch('/api/v1/developer/permissions', {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch('/api/v1/developer/models', {
            headers: { 'Authorization': `Bearer ${token}` }
          })
        ]);

        if (keysResponse.ok) {
          const keysData = await keysResponse.json();
          setApiKeys(keysData.data.api_keys);
        }

        if (quotaResponse.ok) {
          const quotaData = await quotaResponse.json();
          setQuota(quotaData.data);
        }

        if (permissionsResponse.ok) {
          const permissionsData = await permissionsResponse.json();
          setAvailablePermissions(permissionsData.data.permissions);
        }

        if (modelsResponse.ok) {
          const modelsData = await modelsResponse.json();
          setAvailableModels(modelsData.data.models);
        }

      } catch (err) {
        setError('加载数据失败');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [router]);

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem('developer_access_token');

    try {
      const response = await fetch('/api/v1/developer/keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...formData,
          expires_days: formData.expires_days ? parseInt(formData.expires_days) : undefined
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setNewKeySecret(data.data);
        setShowKeySecret(true);
        setShowCreateModal(false);

        // 重置表单
        setFormData({
          name: '',
          permissions: ['chat.completions', 'chat.models', 'usage.view'],
          rate_limit: 100,
          allowed_models: [],
          expires_days: ''
        });

        // 刷新API密钥列表
        await fetchAPIKeys();
      } else {
        setError(data.detail || '创建失败');
      }
    } catch (err) {
      setError('网络错误，请稍后重试');
    }
  };

  const fetchAPIKeys = async () => {
    const token = localStorage.getItem('developer_access_token');
    try {
      const response = await fetch('/api/v1/developer/keys', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setApiKeys(data.data.api_keys);
      }
    } catch (err) {
      console.error('Failed to fetch API keys:', err);
    }
  };

  const handleDeleteKey = async (keyId: string) => {
    if (!confirm('确定要删除这个API密钥吗？此操作不可撤销。')) {
      return;
    }

    const token = localStorage.getItem('developer_access_token');
    try {
      const response = await fetch(`/api/v1/developer/keys/${keyId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        await fetchAPIKeys();
      } else {
        const data = await response.json();
        setError(data.detail || '删除失败');
      }
    } catch (err) {
      setError('网络错误，请稍后重试');
    }
  };

  const handleToggleKey = async (keyId: string, isActive: boolean) => {
    const token = localStorage.getItem('developer_access_token');
    try {
      const response = await fetch(`/api/v1/developer/keys/${keyId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ is_active: !isActive }),
      });

      if (response.ok) {
        await fetchAPIKeys();
      } else {
        const data = await response.json();
        setError(data.detail || '操作失败');
      }
    } catch (err) {
      setError('网络错误，请稍后重试');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // 可以添加一个toast提示
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航栏 */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link href="/developer" className="text-blue-600 hover:text-blue-800">
                ← 返回控制台
              </Link>
              <h1 className="ml-4 text-2xl font-bold text-gray-900">API密钥管理</h1>
            </div>
          </div>
        </div>
      </nav>

      {/* 主要内容 */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="text-sm text-red-600">{error}</div>
          </div>
        )}

        {/* 配额信息卡片 */}
        {quota && (
          <div className="bg-white shadow rounded-lg mb-6">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                📊 API配额信息
              </h3>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <dt className="text-sm font-medium text-gray-500">月度配额</dt>
                  <dd className="mt-1 text-lg font-semibold text-gray-900">
                    {quota.monthly_quota.toLocaleString()} tokens
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">已使用</dt>
                  <dd className="mt-1 text-lg font-semibold text-blue-600">
                    {quota.monthly_used.toLocaleString()} tokens
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">剩余配额</dt>
                  <dd className="mt-1 text-lg font-semibold text-green-600">
                    {quota.monthly_remaining.toLocaleString()} tokens
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">API密钥</dt>
                  <dd className="mt-1 text-lg font-semibold text-purple-600">
                    {quota.active_api_keys}/{quota.max_api_keys}
                  </dd>
                </div>
              </div>

              {/* 使用进度条 */}
              <div className="mt-4">
                <div className="flex justify-between text-sm text-gray-600 mb-1">
                  <span>配额使用率</span>
                  <span>{quota.monthly_usage_percent.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      quota.monthly_usage_percent > 80 ? 'bg-red-500' :
                      quota.monthly_usage_percent > 60 ? 'bg-yellow-500' : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(quota.monthly_usage_percent, 100)}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  配额重置日期: {quota.reset_date}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 操作栏 */}
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold text-gray-900">我的API密钥</h2>
          <button
            onClick={() => setShowCreateModal(true)}
            disabled={quota && quota.active_api_keys >= quota.max_api_keys}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            + 创建新密钥
          </button>
        </div>

        {/* API密钥列表 */}
        <div className="bg-white shadow rounded-lg">
          {apiKeys.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-gray-400 text-6xl mb-4">🔑</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">还没有API密钥</h3>
              <p className="text-gray-600 mb-4">创建您的第一个API密钥开始使用AI Hub服务</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
              >
                创建API密钥
              </button>
            </div>
          ) : (
            <div className="overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      名称
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      密钥前缀
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      状态
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      使用量
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      最后使用
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      创建时间
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {apiKeys.map((apiKey) => (
                    <tr key={apiKey.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{apiKey.name}</div>
                        <div className="text-sm text-gray-500">
                          限制: {apiKey.rate_limit}/分钟
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 font-mono">
                          {apiKey.key_prefix}
                        </div>
                        <button
                          onClick={() => copyToClipboard(apiKey.key_prefix)}
                          className="text-xs text-blue-600 hover:text-blue-800"
                        >
                          复制
                        </button>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          apiKey.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {apiKey.is_active ? '活跃' : '已禁用'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div>{apiKey.usage_count.toLocaleString()} 次请求</div>
                        <div>{apiKey.total_tokens_used.toLocaleString()} tokens</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {apiKey.last_used_at
                          ? new Date(apiKey.last_used_at).toLocaleDateString()
                          : '从未使用'
                        }
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(apiKey.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex justify-end space-x-2">
                          <button
                            onClick={() => handleToggleKey(apiKey.id, apiKey.is_active)}
                            className={`px-3 py-1 rounded text-xs ${
                              apiKey.is_active
                                ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
                                : 'bg-green-100 text-green-800 hover:bg-green-200'
                            }`}
                          >
                            {apiKey.is_active ? '禁用' : '启用'}
                          </button>
                          <button
                            onClick={() => handleDeleteKey(apiKey.id)}
                            className="bg-red-100 text-red-800 px-3 py-1 rounded text-xs hover:bg-red-200"
                          >
                            删除
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* 创建API密钥模态框 */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                创建新的API密钥
              </h3>
              <form onSubmit={handleCreateKey}>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">密钥名称</label>
                    <input
                      type="text"
                      required
                      value={formData.name}
                      onChange={(e) => setFormData({...formData, name: e.target.value})}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      placeholder="例如：生产环境密钥"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">速率限制（请求/分钟）</label>
                    <input
                      type="number"
                      min="1"
                      max="10000"
                      value={formData.rate_limit}
                      onChange={(e) => setFormData({...formData, rate_limit: parseInt(e.target.value)})}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">过期天数（可选）</label>
                    <input
                      type="number"
                      min="1"
                      max="365"
                      value={formData.expires_days}
                      onChange={(e) => setFormData({...formData, expires_days: e.target.value})}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      placeholder="留空表示永不过期"
                    />
                  </div>
                </div>

                <div className="mt-6 flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="bg-gray-100 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-200"
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                  >
                    创建密钥
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* 显示密钥密钥模态框 */}
      {showKeySecret && newKeySecret && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3 text-center">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                <svg className="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                API密钥创建成功！
              </h3>
              <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 mb-4">
                <p className="text-sm text-yellow-800 mb-2">
                  ⚠️ 请立即复制并保存您的API密钥，它只会显示一次！
                </p>
                <div className="bg-white border border-yellow-300 rounded p-2">
                  <code className="text-xs text-gray-900 break-all">
                    {newKeySecret.api_key}
                  </code>
                </div>
                <button
                  onClick={() => copyToClipboard(newKeySecret.api_key)}
                  className="mt-2 w-full bg-yellow-100 text-yellow-800 px-3 py-1 rounded text-sm hover:bg-yellow-200"
                >
                  复制密钥
                </button>
              </div>
              <button
                onClick={() => {
                  setShowKeySecret(false);
                  setNewKeySecret(null);
                }}
                className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
              >
                我已保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}