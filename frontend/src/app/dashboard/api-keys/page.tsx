'use client';

import { useState, useEffect } from 'react';

interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  status: 'active' | 'inactive';
  created_at: string;
  last_used?: string;
}

export default function APIKeysPage() {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAPIKeys();
  }, []);

  const fetchAPIKeys = async () => {
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000));

      const mockKeys: APIKey[] = [
        {
          id: '1',
          name: 'Production API Key',
          key_prefix: 'ak_live_',
          status: 'active',
          created_at: new Date().toISOString(),
          last_used: new Date(Date.now() - 3600000).toISOString()
        },
        {
          id: '2',
          name: 'Development API Key',
          key_prefix: 'ak_test_',
          status: 'active',
          created_at: new Date(Date.now() - 7 * 24 * 3600000).toISOString(),
          last_used: new Date(Date.now() - 7200000).toISOString()
        }
      ];

      setApiKeys(mockKeys);
    } catch (error) {
      console.error('Failed to fetch API keys:', error);
    } finally {
      setLoading(false);
    }
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
        <h1 className="text-2xl font-bold text-gray-900">API密钥管理</h1>
        <p className="mt-1 text-sm text-gray-600">
          管理您的API密钥并监控使用情况
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
            + 创建新密钥
          </button>
        </div>

        <div className="divide-y divide-gray-200">
          {apiKeys.map((apiKey) => (
            <div key={apiKey.id} className="px-6 py-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-medium text-gray-900">{apiKey.name}</h3>
                  <p className="text-sm text-gray-500">
                    {apiKey.key_prefix}•••••••••••••••••••••••••••••
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    创建于: {new Date(apiKey.created_at).toLocaleDateString('zh-CN')}
                    {apiKey.last_used && ` • 最后使用: ${new Date(apiKey.last_used).toLocaleDateString('zh-CN')}`}
                  </p>
                </div>
                <div className="flex items-center space-x-3">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    apiKey.status === 'active'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {apiKey.status === 'active' ? '活跃' : '停用'}
                  </span>
                  <button className="text-blue-600 hover:text-blue-800 text-sm">
                    编辑
                  </button>
                  <button className="text-red-600 hover:text-red-800 text-sm">
                    删除
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}