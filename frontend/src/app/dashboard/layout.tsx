'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import PageLoading from '@/components/ui/LoadingSpinner';
import { useTheme } from '@/contexts/ThemeContext';
import { I18nProvider, useI18n } from '@/contexts/I18nContext';
import ThemeSettings from '@/components/ui/ThemeSettings';

// 简化的User类型定义
interface SimpleUser {
  id: number;
  email: string;
  full_name?: string;
  plan: string;
  is_active: boolean;
  created_at: string;
}

// Dashboard Layout with i18n support
function DashboardContent({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { preferences } = useTheme();
  const { t, language, setLanguage, availableLanguages } = useI18n();
  const [user, setUser] = useState<SimpleUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

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

  // 移动端检测和响应式处理
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth >= 768) {
        setSidebarOpen(false); // 桌面端关闭移动端菜单
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // 处理菜单切换
  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  // 处理导航点击（移动端关闭菜单）
  const handleNavClick = () => {
    if (isMobile) {
      setSidebarOpen(false);
    }
  };

  if (loading) {
    return <PageLoading message={t('common.loading')} />;
  }

  // 如果没有用户数据，不渲染子组件
  if (!user) {
    return null;
  }

  return (
    <div className={`flex min-h-screen ${preferences.theme === 'dark' ? 'dark' : ''}`}>
      {/* 主题设置组件 */}
      <ThemeSettings />

      {/* 移动端遮罩层 */}
      {isMobile && sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* 响应式侧边栏 */}
      <div className={`
        ${isMobile
          ? `fixed inset-y-0 left-0 z-50 w-64 transform transition-transform duration-300 ease-in-out ${
              sidebarOpen ? 'translate-x-0' : '-translate-x-full'
            }`
          : 'w-64 relative'
        } bg-white shadow-lg`}
      >
        {/* 侧边栏头部 */}
        <div className="flex items-center justify-between h-16 px-4 bg-blue-600 text-white">
          <h1 className="text-xl font-bold">AI Hub</h1>
          <div className="flex items-center space-x-2">
            {/* 语言选择器 */}
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value as any)}
              className="bg-blue-700 text-white text-sm px-2 py-1 rounded border border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-400"
            >
              {Object.entries(availableLanguages).map(([code, config]) => (
                <option key={code} value={code}>
                  {config.flag} {config.nativeName}
                </option>
              ))}
            </select>
            {isMobile && (
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-2 rounded-md hover:bg-blue-700 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>

        <div className="p-4">
          <div className="flex items-center mb-6">
            <div className="bg-gray-200 rounded-full w-10 h-10"></div>
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-700">
                {user.full_name || user.email}
              </p>
              <p className="text-xs text-gray-500">
                {user.plan} {t('billing.subscription')}
              </p>
            </div>
          </div>

          <nav className="space-y-2">
            <a
              href="/dashboard"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors"
            >
              📊 {t('dashboard.title')}
            </a>
            <a
              href="/dashboard/organizations"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              🏢 组织管理
            </a>
            <a
              href="/dashboard/teams"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              👥 团队管理
            </a>
            <a
              href="/dashboard/budgets"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              💰 预算管理
            </a>
            <a
              href="/dashboard/billing"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              💳 {t('billing.title')}
            </a>
            <a
              href="/dashboard/api-keys"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              🔑 {t('api.keys')}
            </a>
            <a
              href="/dashboard/usage"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              📈 {t('api.usage')}
            </a>
            <a
              href="/dashboard/reports"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              📊 {t('analytics.reports')}
            </a>
            <a
              href="/dashboard/audit"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              📋 审计日志
            </a>
            <a
              href="/dashboard/permissions"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              🔐 {t('settings.security')}
            </a>
          <a
              href="/dashboard/monitoring"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              📊 系统监控
            </a>
            <a
              href="/dashboard/multimodal"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              🎨 多模态AI
            </a>
            <a
              href="/dashboard/workflow"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              ⚙️ 工作流引擎
            </a>
            <a
              href="/dashboard/api-docs"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              📚 {t('api.test')}
            </a>
            <a
              href="/dashboard/swagger"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              📖 {t('api.documentation')}
            </a>
            <a
              href="/developer-portal"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              👨 {t('developer.portal')}
            </a>
          <a
              href="/chat"
              onClick={handleNavClick}
              className="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
            >
              💬 {t('chat.title')}
            </a>
          </nav>
        </div>

        <div className="border-t border-gray-200 dark:border-gray-600 p-4 space-y-2">
          {/* 主题切换按钮 */}
          <button
            onClick={() => {
              const newTheme = preferences.theme === 'dark' ? 'light' : 'dark';
              // 这里可以通过全局状态更新主题
            }}
            className="w-full flex items-center px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors"
          >
            <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {preferences.theme === 'dark' ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              )}
            </svg>
            {preferences.theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </button>

          {/* 退出登录 */}
          <button
            onClick={() => {
              localStorage.removeItem('access_token');
              router.push('/login');
            }}
            className="w-full flex items-center px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors"
          >
            <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            {t('navigation.logout')}
          </button>
        </div>
      </div>

      {/* 主内容区域 */}
      <div className="flex-1 overflow-hidden">
        {/* 顶部工具栏 (移动端) */}
        <header className="bg-white shadow-sm border-b border-gray-200 lg:hidden">
          <div className="flex items-center justify-between h-16 px-4">
            <button
              onClick={toggleSidebar}
              className="p-2 rounded-md text-gray-600 hover:bg-gray-100 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="flex items-center space-x-3">
              <span className="text-sm font-medium text-gray-700">{user.full_name || user.email}</span>
              <div className="bg-gray-200 rounded-full w-8 h-8"></div>
            </div>
          </div>
        </header>

        <main className="flex-1 relative overflow-y-auto focus:outline-none">
          {children}
        </main>
      </div>
    </div>
  );
}

// Main export with I18n Provider wrapper
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <I18nProvider defaultLanguage="zh-CN">
      <DashboardContent>
        {children}
      </DashboardContent>
    </I18nProvider>
  );
}