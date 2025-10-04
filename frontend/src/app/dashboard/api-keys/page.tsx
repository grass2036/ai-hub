'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import type { APIKey } from '@/types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';

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
    loadKeys();
  }, []);

  const loadKeys = async () => {
    try {
      const data: APIKey[] = await apiClient.listAPIKeys();
      setKeys(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response: any = await apiClient.createAPIKey(newKeyData);
      setCreatedKey(response);
      setShowCreateModal(false);
      setNewKeyData({ name: '', description: '', rate_limit: 100 });
      loadKeys(); // 重新加载密钥列表
    } catch (err: any) {
      alert(err.message || 'Failed to create API key');
    }
  };

  const handleRevokeKey = async (keyId: number) => {
    if (!confirm('确定要撤销此API密钥吗？此操作不可撤销。')) {
      return;
    }

    try {
      await apiClient.revokeAPIKey(keyId);
      loadKeys(); // 重新加载密钥列表
    } catch (err: any) {
      alert(err.message || 'Failed to revoke API key');
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center py-8">加载中...</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">API密钥管理</h1>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            创建新密钥
          </button>
        </div>
        <p className="mt-2 text-gray-600">
          管理您的API密钥，用于访问AI Hub的开发者API
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">错误: {error}</p>
        </div>
      )}

      {/* 密钥列表 */}
      {keys.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500">还没有API密钥</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            创建第一个密钥
          </button>
        </div>
      ) : (
        <div className="bg-white shadow overflow-hidden sm:rounded-lg">
          <ul className="divide-y divide-gray-200">
            {keys.map((key) => (
              <li key={key.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center">
                      <p className="text-sm font-medium text-gray-900">
                        {key.name}
                      </p>
                      {!key.is_active && (
                        <span className="ml-2 px-2 py-1 text-xs bg-red-100 text-red-800 rounded">
                          已撤销
                        </span>
                      )}
                      {key.is_expired && (
                        <span className="ml-2 px-2 py-1 text-xs bg-orange-100 text-orange-800 rounded">
                          已过期
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-gray-500">
                      {key.key_prefix}...
                    </p>
                    {key.description && (
                      <p className="mt-1 text-sm text-gray-500">
                        {key.description}
                      </p>
                    )}
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-gray-400">
                      <span>
                        总请求: {key.total_requests}
                      </span>
                      {key.rate_limit && (
                        <span>
                          速率限制: {key.rate_limit}/分钟
                        </span>
                      )}
                      <span>
                        创建于: {new Date(key.created_at).toLocaleDateString('zh-CN')}
                      </span>
                      {key.last_used_at && (
                        <span>
                          最后使用: {new Date(key.last_used_at).toLocaleDateString('zh-CN')}
                        </span>
                      )}
                    </div>
                  </div>
                  {key.is_active && (
                    <button
                      onClick={() => handleRevokeKey(key.id)}
                      className="ml-4 px-3 py-1 text-sm text-red-600 hover:text-red-800"
                    >
                      撤销
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 创建密钥弹窗 */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-lg font-bold mb-4">创建新API密钥</h2>
            <form onSubmit={handleCreateKey}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    密钥名称
                  </label>
                  <input
                    type="text"
                    required
                    value={newKeyData.name}
                    onChange={(e) =>
                      setNewKeyData({ ...newKeyData, name: e.target.value })
                    }
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    描述 (可选)
                  </label>
                  <textarea
                    value={newKeyData.description}
                    onChange={(e) =>
                      setNewKeyData({
                        ...newKeyData,
                        description: e.target.value,
                      })
                    }
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    rows={3}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    速率限制 (请求/分钟, 可选)
                  </label>
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
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
              <div className="mt-6 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  创建
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 密钥创建成功弹窗 */}
      {createdKey && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-lg font-bold mb-4 text-green-600">
              ✓ API密钥创建成功
            </h2>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
              <p className="text-sm text-yellow-800 mb-2">
                ⚠️ 请立即复制此密钥，它只会显示一次！
              </p>
              <div className="bg-white p-3 rounded border border-gray-300 font-mono text-sm break-all">
                {createdKey.key}
              </div>
            </div>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(createdKey.key);
                  alert('已复制到剪贴板');
                }}
                className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
              >
                复制
              </button>
              <button
                onClick={() => setCreatedKey(null)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
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