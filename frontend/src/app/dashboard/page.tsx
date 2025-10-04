'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import type { User } from '@/types';
import { Card } from '@/components/ui/Card';

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const userData: User = await apiClient.getCurrentUser();
        setUser(userData);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch user data');
        // 如果认证失败，重定向到登录页面
        if (err.message && (err.message.includes('Unauthorized') || err.message.includes('认证'))) {
          router.push('/login');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [router]);
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">AI Hub 仪表板</h1>
        <p className="mt-2 text-gray-600">
          欢迎回来, {user?.full_name || user?.email}
        </p>
      </div>

      {/* 配额信息卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card title="当前套餐">
          <p className="text-2xl font-bold text-blue-600">{user?.plan.toUpperCase()}</p>
        </Card>
        
        <Card title="已使用配额">
          <p className="text-2xl font-bold text-gray-900">{user?.quota_used}</p>
        </Card>
        
        <Card title="剩余配额">
          <p className="text-2xl font-bold text-green-600">{user?.quota_remaining}</p>
        </Card>
      </div>

      {/* 快速导航 */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">快速导航</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link 
            href="/dashboard/api-keys" 
            className="block p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <h3 className="font-medium text-gray-900">API密钥管理</h3>
            <p className="text-sm text-gray-500 mt-1">创建和管理您的API密钥</p>
          </Link>
          
          <Link 
            href="/dashboard/usage" 
            className="block p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <h3 className="font-medium text-gray-900">使用统计</h3>
            <p className="text-sm text-gray-500 mt-1">查看您的API使用情况</p>
          </Link>
          
          <Link 
            href="/chat" 
            className="block p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <h3 className="font-medium text-gray-900">AI聊天</h3>
            <p className="text-sm text-gray-500 mt-1">开始与AI对话</p>
          </Link>
        </div>
      </div>
    </div>
  );
}
