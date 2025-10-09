'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// 简化的User类型定义
interface SimpleUser {
  id: number;
  email: string;
  full_name?: string;
  plan: string;
  is_active: boolean;
  created_at: string;
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [user, setUser] = useState<SimpleUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      // 检查是否有token
      const token = localStorage.getItem('access_token');
      if (!token) {
        router.push('/login');
        return;
      }

      try {
        // 模拟用户数据验证
        const mockUser: SimpleUser = {
          id: 1,
          email: 'user@example.com',
          full_name: 'Demo User',
          plan: 'Pro',
          is_active: true,
          created_at: new Date().toISOString()
        };
        setUser(mockUser);
      } catch (error) {
        // Token无效，清除并重定向到登录页面
        localStorage.removeItem('access_token');
        router.push('/login');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  // 如果没有用户数据，不渲染子组件
  if (!user) {
    return null;
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* 简化的侧边栏 */}
      <div className="w-64 bg-white shadow-lg">
        <div className="flex items-center justify-center h-16 px-4 bg-blue-600 text-white">
          <h1 className="text-xl font-bold">AI Hub</h1>
        </div>

        <div className="p-4">
          <div className="flex items-center mb-6">
            <div className="bg-gray-200 rounded-full w-10 h-10"></div>
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-700">
                {user.full_name || user.email}
              </p>
              <p className="text-xs text-gray-500">
                {user.plan} 套餐
              </p>
            </div>
          </div>

          <nav className="space-y-2">
            <a
              href="/dashboard"
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md bg-blue-50 text-blue-600"
            >
              📊 仪表板
            </a>
            <a
              href="/dashboard/api-keys"
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50"
            >
              🔑 API密钥
            </a>
            <a
              href="/dashboard/usage"
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50"
            >
              📈 使用统计
            </a>
            <a
              href="/chat"
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50"
            >
              💬 AI聊天
            </a>
          </nav>
        </div>

        <div className="border-t border-gray-200 p-4">
          <button
            onClick={() => {
              localStorage.removeItem('access_token');
              router.push('/login');
            }}
            className="w-full flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-md"
          >
            <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            退出登录
          </button>
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="flex-1 overflow-hidden">
        <main className="flex-1 relative overflow-y-auto focus:outline-none">
          {children}
        </main>
      </div>
    </div>
  );
}