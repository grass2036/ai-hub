import Link from 'next/link'

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-zinc-200 pb-6 pt-8 backdrop-blur-2xl dark:from-inherit lg:static lg:w-auto lg:rounded-xl lg:border lg:bg-gray-200 lg:p-4 lg:dark:bg-zinc-800/30">
      <div className="container mx-auto px-4">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-8">
            Welcome to AI Hub
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-8">
            开发者AI API服务平台 - 统一接入多个AI模型
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">
            类似OpenRouter,提供API密钥、配额管理、企业级控制
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Link href="/chat" className="block transform hover:scale-105 transition-transform">
              <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg hover:shadow-xl">
                <div className="text-3xl mb-4">🤖</div>
                <h2 className="text-xl font-semibold mb-4">AI Chat Demo</h2>
                <p className="text-gray-600 dark:text-gray-300">
                  体验多模型AI聊天能力
                </p>
              </div>
            </Link>
            <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg opacity-50">
              <div className="text-3xl mb-4">🔑</div>
              <h2 className="text-xl font-semibold mb-4">API Keys</h2>
              <p className="text-gray-600 dark:text-gray-300">
                API密钥管理（开发中）
              </p>
            </div>
            <Link href="/dashboard" className="block transform hover:scale-105 transition-transform">
              <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg hover:shadow-xl">
                <div className="text-3xl mb-4">📊</div>
                <h2 className="text-xl font-semibold mb-4">Dashboard</h2>
                <p className="text-gray-600 dark:text-gray-300">
                  用量统计和管理
                </p>
              </div>
            </Link>
          </div>
        </div>
      </div>
    </main>
  )
}