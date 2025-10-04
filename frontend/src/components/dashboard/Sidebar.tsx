'use client';

import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiClient } from '@/lib/api';
import type { User } from '@/types';

interface SidebarProps {
  user: User;
}

export default function Sidebar({ user }: SidebarProps) {
  const router = useRouter();
  const pathname = usePathname();

  const navigation = [
    { name: '仪表板', href: '/dashboard', icon: '📊' },
    { name: 'API密钥', href: '/dashboard/api-keys', icon: '🔑' },
    { name: '使用统计', href: '/dashboard/usage', icon: '📈' },
    { name: 'AI聊天', href: '/chat', icon: '💬' },
  ];

  const handleNavigation = (path: string) => {
    console.log('Sidebar navigating to:', path);
    router.push(path);
  };

  const handleLogout = () => {
    apiClient.clearToken();
    router.push('/login');
  };

  return (
    <div className="flex flex-col w-64 bg-white shadow-lg min-h-screen">
      <div className="flex items-center justify-center h-16 px-4 bg-blue-600 text-white">
        <h1 className="text-xl font-bold">AI Hub</h1>
      </div>
      
      <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
        <div className="flex items-center flex-shrink-0 px-4">
          <div className="bg-gray-200 border-2 border-dashed rounded-xl w-16 h-16" />
          <div className="ml-3">
            <p className="text-sm font-medium text-gray-700">
              {user.full_name || user.email}
            </p>
            <p className="text-xs font-medium text-gray-500 capitalize">
              {user.plan} 套餐
            </p>
          </div>
        </div>
        
        <nav className="mt-5 flex-1 px-2 bg-white space-y-1">
          {navigation.map((item) => (
            <Link
              key={item.name}
              href={item.href}
              className={`${
                pathname === item.href
                  ? 'bg-blue-50 text-blue-600'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              } group flex items-center px-2 py-2 text-sm font-medium rounded-md`}
            >
              <span className="mr-3 text-lg">{item.icon}</span>
              {item.name}
            </Link>
          ))}
        </nav>
      </div>
      
      <div className="flex-shrink-0 flex border-t border-gray-200 p-4">
        <button
          onClick={handleLogout}
          className="flex-shrink-0 w-full group block"
        >
          <div className="flex items-center">
            <div>
              <svg className="h-5 w-5 text-gray-400 group-hover:text-gray-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 3a1 1 0 00-1 1v12a1 1 0 102 0V4a1 1 0 00-1-1zm10.293 9.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L14.586 9H7a1 1 0 100 2h7.586l-1.293 1.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-700 group-hover:text-gray-900">
                退出登录
              </p>
            </div>
          </div>
        </button>
      </div>
    </div>
  );
}
