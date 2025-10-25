'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SwaggerPage() {
  const router = useRouter();
  const [activeView, setActiveView] = useState<'swagger' | 'redoc' | 'openapi'>('swagger');
  const [loading, setLoading] = useState(true);
  const [apiSpec, setApiSpec] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (!token) {
        router.push('/login');
        return;
      }

      try {
        // 加载OpenAPI规范
        const response = await fetch('/api/openapi.json');
        if (response.ok) {
          const spec = await response.json();
          setApiSpec(spec);
        }
      } catch (err) {
        setError('无法加载API规范');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <span className="ml-4 text-gray-600">加载API文档中...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-red-500 text-xl mb-4">⚠️ 加载失败</div>
          <p className="text-gray-600">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            重新加载
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* 页面标题 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">API 文档中心</h1>
        <p className="text-gray-600">
          AI Hub Platform 完整API文档 - 包含所有端点、参数说明和示例代码
        </p>
      </div>

      {/* API概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-2xl font-bold text-blue-600 mb-2">
            {apiSpec?.paths ? Object.keys(apiSpec.paths).length : 0}
          </div>
          <div className="text-sm text-gray-600">API 端点</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-2xl font-bold text-green-600 mb-2">
            {apiSpec?.components?.schemas ? Object.keys(apiSpec.components.schemas).length : 0}
          </div>
          <div className="text-sm text-gray-600">数据模型</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-2xl font-bold text-purple-600 mb-2">v1.0.0</div>
          <div className="text-sm text-gray-600">API 版本</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-2xl font-bold text-orange-600 mb-2">15+</div>
          <div className="text-sm text-gray-600">核心功能</div>
        </div>
      </div>

      {/* 文档视图切换 */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            <button
              onClick={() => setActiveView('swagger')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'swagger'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              📘 Swagger UI
            </button>
            <button
              onClick={() => setActiveView('redoc')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'redoc'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              📖 ReDoc
            </button>
            <button
              onClick={() => setActiveView('openapi')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'openapi'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              📄 OpenAPI 规范
            </button>
          </nav>
        </div>

        {/* 文档内容区域 */}
        <div className="p-6">
          {activeView === 'swagger' && (
            <div>
              <div className="mb-4 p-4 bg-blue-50 rounded-lg">
                <h3 className="font-semibold text-blue-900 mb-2">Swagger UI 交互式文档</h3>
                <p className="text-blue-700 text-sm">
                  提供完整的API测试界面，可以直接在浏览器中测试所有API端点
                </p>
              </div>
              <div className="border rounded-lg overflow-hidden">
                <iframe
                  src="/api/docs"
                  className="w-full h-screen min-h-[600px] border-0"
                  title="Swagger UI"
                />
              </div>
            </div>
          )}

          {activeView === 'redoc' && (
            <div>
              <div className="mb-4 p-4 bg-green-50 rounded-lg">
                <h3 className="font-semibold text-green-900 mb-2">ReDoc 美化文档</h3>
                <p className="text-green-700 text-sm">
                  三栏式布局的API文档，更适合阅读和分享
                </p>
              </div>
              <div className="border rounded-lg overflow-hidden">
                <iframe
                  src="/api/redoc"
                  className="w-full h-screen min-h-[600px] border-0"
                  title="ReDoc"
                />
              </div>
            </div>
          )}

          {activeView === 'openapi' && (
            <div>
              <div className="mb-4 p-4 bg-purple-50 rounded-lg">
                <h3 className="font-semibold text-purple-900 mb-2">OpenAPI 3.0 规范</h3>
                <p className="text-purple-700 text-sm">
                  原始的API规范文件，可用于代码生成和集成开发
                </p>
              </div>

              {/* 下载按钮 */}
              <div className="mb-6 flex space-x-4">
                <a
                  href="/api/openapi.json"
                  download="ai-hub-api.json"
                  className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  📥 下载 JSON 格式
                </a>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(JSON.stringify(apiSpec, null, 2));
                    alert('已复制到剪贴板');
                  }}
                  className="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                >
                  📋 复制到剪贴板
                </button>
              </div>

              {/* JSON 预览 */}
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
                  <code className="text-sm font-medium text-gray-700">OpenAPI Specification</code>
                </div>
                <div className="max-h-96 overflow-y-auto">
                  <pre className="p-4 text-xs text-gray-800 whitespace-pre-wrap">
                    {JSON.stringify(apiSpec, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 快速链接 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">快速链接</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a
            href="/api/docs"
            target="_blank"
            className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <span className="text-2xl mr-3">🚀</span>
            <div>
              <div className="font-medium text-gray-900">在新标签页打开 Swagger</div>
              <div className="text-sm text-gray-500">完整交互式API文档</div>
            </div>
          </a>
          <a
            href="/api/redoc"
            target="_blank"
            className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <span className="text-2xl mr-3">📚</span>
            <div>
              <div className="font-medium text-gray-900">在新标签页打开 ReDoc</div>
              <div className="text-sm text-gray-500">美化版API文档</div>
            </div>
          </a>
          <a
            href="/dashboard/api-docs"
            className="flex items-center p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <span className="text-2xl mr-3">🧪</span>
            <div>
              <div className="font-medium text-gray-900">API 测试工具</div>
              <div className="text-sm text-gray-500">在线测试API功能</div>
            </div>
          </a>
        </div>
      </div>

      {/* 开发者指南 */}
      <div className="mt-8 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">开发者指南</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-medium text-gray-900 mb-2">🔑 API 认证</h3>
            <p className="text-sm text-gray-600 mb-3">
              所有API请求需要在请求头中包含认证令牌：
            </p>
            <code className="block bg-gray-800 text-green-400 p-3 rounded text-sm">
              Authorization: Bearer YOUR_API_KEY
            </code>
          </div>
          <div>
            <h3 className="font-medium text-gray-900 mb-2">🌐 基础URL</h3>
            <p className="text-sm text-gray-600 mb-3">
              所有API端点的统一基础地址：
            </p>
            <code className="block bg-gray-800 text-green-400 p-3 rounded text-sm">
              https://api.ai-hub.com/api/v1
            </code>
          </div>
        </div>

        <div className="mt-6">
          <h3 className="font-medium text-gray-900 mb-3">📋 主要功能模块</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div className="bg-white rounded-lg p-3">
              <div className="font-medium text-blue-600 mb-1">💬 AI 聊天</div>
              <div className="text-gray-600">对话生成、流式响应</div>
            </div>
            <div className="bg-white rounded-lg p-3">
              <div className="font-medium text-green-600 mb-1">🎨 多模态AI</div>
              <div className="text-gray-600">图像、音频、文档处理</div>
            </div>
            <div className="bg-white rounded-lg p-3">
              <div className="font-medium text-purple-600 mb-1">⚙️ 工作流</div>
              <div className="text-gray-600">流程编排、自动化</div>
            </div>
            <div className="bg-white rounded-lg p-3">
              <div className="font-medium text-orange-600 mb-1">👥 企业管理</div>
              <div className="text-gray-600">组织、团队、权限</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}