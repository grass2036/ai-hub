export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm text-gray-500 mb-2">当前套餐</h3>
          <p className="text-2xl font-bold text-gray-900">Free</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm text-gray-500 mb-2">本月请求</h3>
          <p className="text-2xl font-bold text-green-600">1,250</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm text-gray-500 mb-2">今日请求</h3>
          <p className="text-2xl font-bold text-yellow-600">45</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-sm text-gray-500 mb-2">总成本</h3>
          <p className="text-2xl font-bold text-purple-600">$0.13</p>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold text-gray-900 mb-4">配额使用情况</h2>
        <div className="w-full bg-gray-200 rounded-full h-4 mb-4">
          <div className="bg-green-500 h-4 rounded-full" style={{width: '2.5%'}}></div>
        </div>
        <p className="text-sm text-gray-600">已使用: 1,250 / 50,000 (2.5%)</p>
      </div>
    </div>
  );
}