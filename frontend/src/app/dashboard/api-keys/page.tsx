'use client';

import { useState, useEffect } from 'react';

interface APIKey {
  id: number;
  key_prefix: string;
  name: string;
  description?: string;
  is_active: boolean;
  rate_limit?: number;
  total_requests: number;
  last_used_at?: string;
  created_at: string;
  expires_at?: string;
  is_expired: boolean;
}

export default function APIKeysPage() {
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyData, setNewKeyData] = useState({
    name: '',
    description: '',
    rate_limit: 100,
  });
  const [createdKey, setCreatedKey] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const mockKeys: APIKey[] = [
      {
        id: 1,
        key_prefix: 'sk-live',
        name: 'Production API Key',
        description: '生产环境主要API密钥',
        is_active: true,
        rate_limit: 1000,
        total_requests: 15420,
        last_used_at: new Date().toISOString(),
        created_at: '2024-01-15T10:30:00Z',
        expires_at: '2025-01-15T10:30:00Z',
        is_expired: false
      },
      {
        id: 2,
        key_prefix: 'sk-dev',
        name: 'Development Key',
        description: '开发和测试环境使用',
        is_active: true,
        rate_limit: 100,
        total_requests: 856,
        last_used_at: new Date(Date.now() - 86400000).toISOString(),
        created_at: '2024-02-01T15:45:00Z',
        is_expired: false
      }
    ];
    setKeys(mockKeys);
    setLoading(false);
  }, []);

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const mockResponse = {
        key: 'sk-live' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
      };
      setCreatedKey(mockResponse);
      setShowCreateModal(false);
      setNewKeyData({ name: '', description: '', rate_limit: 100 });
    } catch (err: any) {
      alert(err.message || 'Failed to create API key');
    }
  };

  const handleRevokeKey = async (keyId: number) => {
    if (!confirm('确定要撤销此API密钥吗？此操作不可撤销。')) {
      return;
    }

    try {
      setKeys(keys.map(key =>
        key.id === keyId ? { ...key, is_active: false } : key
      ));
    } catch (err: any) {
      alert(err.message || 'Failed to revoke API key');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">API 密钥管理</h1>
            <p className="text-gray-600 mt-2">管理您的API密钥，监控使用情况，设置权限和限制</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            创建新密钥
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800">错误: {error}</p>
          </div>
        )}

        {keys.length === 0 ? (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="text-center py-12">
              <div className="text-gray-400 text-6xl mb-4">🔑</div>
              <p className="text-gray-500">还没有API密钥</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                创建第一个密钥
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">名称</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">密钥</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {keys.map((key) => (
                    <tr key={key.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{key.name}</div>
                        {key.description && (
                          <div className="text-sm text-gray-500">{key.description}</div>
                        )}
                        <div className="text-xs text-gray-400 mt-1">
                          创建于: {new Date(key.created_at).toLocaleDateString()}
                        </div>
                        {key.last_used_at && (
                          <div className="text-xs text-gray-400">
                            最后使用: {new Date(key.last_used_at).toLocaleDateString()}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                            {key.key_prefix}...
                          </code>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          key.is_active && !key.is_expired
                            ? 'bg-green-100 text-green-800'
                            : key.is_expired
                              ? 'bg-red-100 text-red-800'
                              : 'bg-gray-100 text-gray-800'
                        }`}>
                          {key.is_active && !key.is_expired ? '活跃' : key.is_expired ? '已过期' : '未激活'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <div className="flex items-center space-x-2">
                          <button
                            className="text-blue-600 hover:text-blue-900"
                            title="编辑"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          {key.is_active && (
                            <button
                              onClick={() => handleRevokeKey(key.id)}
                              className="text-red-600 hover:text-red-900"
                              title="撤销"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-md w-full">
              <div className="p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">创建新API密钥</h2>
                <form onSubmit={handleCreateKey}>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">密钥名称</label>
                      <input
                        type="text"
                        required
                        value={newKeyData.name}
                        onChange={(e) =>
                          setNewKeyData({ ...newKeyData, name: e.target.value })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="例如：Production API Key"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">描述 (可选)</label>
                      <textarea
                        value={newKeyData.description}
                        onChange={(e) =>
                          setNewKeyData({
                            ...newKeyData,
                            description: e.target.value,
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        rows={3}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">速率限制 (请求/分钟, 可选)</label>
                      <input
                        type="number"
                        min="1"
                        value={newKeyData.rate_limit}
                        onChange={(e) =>
                          setNewKeyData({
                            ...newKeyData,
                            rate_limit: parseInt(e.target.value) || 100,
                          })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                  <div className="mt-6 flex justify-end space-x-3">
                    <button
                      type="button"
                      onClick={() => setShowCreateModal(false)}
                      className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                    >
                      取消
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      创建
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        )}

        {createdKey && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-lg w-full">
              <div className="p-6">
                <div className="flex items-center mb-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <div className="ml-4">
                    <h2 className="text-xl font-bold text-gray-900">API密钥创建成功</h2>
                    <p className="text-sm text-gray-600">您的API密钥已生成</p>
                  </div>
                </div>

                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
                  <div className="flex items-start">
                    <svg className="w-5 h-5 text-amber-600 mt-0.5 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    <div>
                      <p className="text-sm font-medium text-amber-800">安全提醒</p>
                      <p className="text-xs text-amber-700 mt-1">
                        此API密钥只会显示一次。请立即复制并安全保存，关闭此窗口后将无法再次查看完整密钥。
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4 mb-6">
                  <label className="block text-sm font-medium text-gray-700 mb-2">API密钥</label>
                  <div className="flex items-center justify-between">
                    <code className="text-sm bg-white border border-gray-300 rounded px-3 py-2 font-mono flex-1 mr-2 break-all">
                      {createdKey.key}
                    </code>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(createdKey.key);
                        alert('已复制到剪贴板');
                      }}
                      className="p-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                      title="复制密钥"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2h-2z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l-8 8-8-8" />
                      </svg>
                    </button>
                  </div>
                </div>

                <div className="flex space-x-3">
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(createdKey.key);
                      alert('API密钥已复制到剪贴板！');
                    }}
                    className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center justify-center"
                  >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2h-2z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l-8 8-8-8" />
                    </svg>
                    复制密钥
                  </button>
                  <button
                    onClick={() => setCreatedKey(null)}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    我已保存
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}