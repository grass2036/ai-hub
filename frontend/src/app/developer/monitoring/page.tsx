'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { performanceMonitor } from '@/lib/performance';

// 类型定义
interface SystemMetric {
  name: string;
  value: number;
  unit: string;
  status: 'good' | 'warning' | 'critical';
  timestamp: string;
}

interface Alert {
  id: string;
  type: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  timestamp: string;
  resolved: boolean;
}

export default function DeveloperMonitoring() {
  const router = useRouter();
  const [systemMetrics, setSystemMetrics] = useState<SystemMetric[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [frontendMetrics, setFrontendMetrics] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'overview' | 'metrics' | 'alerts' | 'performance'>('overview');

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('developer_access_token');

      if (!token) {
        router.push('/developer/login');
        return;
      }

      try {
        // 并行获取所有监控数据
        const [metricsRes, alertsRes] = await Promise.all([
          fetch('/api/v1/monitoring/metrics', {
            headers: { 'Authorization': `Bearer ${token}` }
          }),
          fetch('/api/v1/monitoring/alerts', {
            headers: { 'Authorization': `Bearer ${token}` }
          })
        ]);

        if (metricsRes.ok) {
          const metricsData = await metricsRes.json();
          setSystemMetrics(metricsData.data.metrics || []);
        }

        if (alertsRes.ok) {
          const alertsData = await alertsRes.json();
          setAlerts(alertsData.data.alerts || []);
        }

        // 获取前端性能指标
        setFrontendMetrics(performanceMonitor.getAllMetrics());

      } catch (err) {
        setError('加载监控数据失败');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    // 定期刷新数据
    const interval = setInterval(fetchData, 30000); // 30秒刷新一次
    return () => clearInterval(interval);
  }, [router]);

  const getMetricStatus = (name: string, value: number): 'good' | 'warning' | 'critical' => {
    if (name.includes('cpu')) {
      if (value > 80) return 'critical';
      if (value > 60) return 'warning';
      return 'good';
    }
    if (name.includes('memory')) {
      if (value > 85) return 'critical';
      if (value > 70) return 'warning';
      return 'good';
    }
    if (name.includes('disk')) {
      if (value > 90) return 'critical';
      if (value > 75) return 'warning';
      return 'good';
    }
    return 'good';
  };

  const getStatusColor = (status: 'good' | 'warning' | 'critical') => {
    switch (status) {
      case 'good':
        return 'text-green-600 bg-green-100';
      case 'warning':
        return 'text-yellow-600 bg-yellow-100';
      case 'critical':
        return 'text-red-600 bg-red-100';
    }
  };

  const getAlertSeverityColor = (severity: string) => {
    switch (severity) {
      case 'info':
        return 'text-blue-600 bg-blue-100';
      case 'warning':
        return 'text-yellow-600 bg-yellow-100';
      case 'error':
        return 'text-red-600 bg-red-100';
      case 'critical':
        return 'text-red-800 bg-red-200';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">加载失败</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航栏 */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link href="/developer" className="text-blue-600 hover:text-blue-800">
                ← 返回控制台
              </Link>
              <h1 className="ml-4 text-xl font-bold text-gray-900">
                系统监控
              </h1>
            </div>
          </div>
        </div>
      </nav>

      {/* 主要内容 */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* 标签页导航 */}
        <div className="bg-white shadow rounded-lg mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8 px-6">
              {[
                { id: 'overview', label: '概览', icon: '📊' },
                { id: 'metrics', label: '系统指标', icon: '📈' },
                { id: 'alerts', label: '告警管理', icon: '🚨' },
                { id: 'performance', label: '性能分析', icon: '⚡' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* 概览标签页 */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* 系统状态概览 */}
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {systemMetrics.slice(0, 8).map((metric) => {
                const status = getMetricStatus(metric.name, metric.value);
                return (
                  <div key={metric.name} className="bg-white overflow-hidden shadow rounded-lg">
                    <div className="p-5">
                      <div className="flex items-center">
                        <div className="flex-shrink-0">
                          <div className={`w-8 h-8 rounded-md flex items-center justify-center ${
                            status === 'good' ? 'bg-green-500' :
                            status === 'warning' ? 'bg-yellow-500' :
                            'bg-red-500'
                          }`}>
                            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                          </div>
                        </div>
                        <div className="ml-5 w-0 flex-1">
                          <dl>
                            <dt className="text-sm font-medium text-gray-500 truncate">
                              {metric.name.replace(/_/g, ' ').toUpperCase()}
                            </dt>
                            <dd className="text-lg font-medium text-gray-900">
                              {metric.value.toFixed(1)}{metric.unit}
                            </dd>
                          </dl>
                        </div>
                      </div>
                      <div className="mt-2">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(status)}`}>
                          {status}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 活跃告警 */}
            <div className="bg-white shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                  活跃告警
                </h3>
                {alerts.filter(alert => !alert.resolved).length > 0 ? (
                  <div className="space-y-3">
                    {alerts.filter(alert => !alert.resolved).slice(0, 5).map((alert) => (
                      <div key={alert.id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center space-x-3">
                          <div className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getAlertSeverityColor(alert.severity)}`}>
                            {alert.severity.toUpperCase()}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">{alert.message}</p>
                            <p className="text-xs text-gray-500">
                              {new Date(alert.timestamp).toLocaleString()}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">暂无活跃告警</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 系统指标标签页 */}
        {activeTab === 'metrics' && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-6">
                系统指标详情
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        指标名称
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        当前值
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        单位
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        状态
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        更新时间
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {systemMetrics.map((metric) => {
                      const status = getMetricStatus(metric.name, metric.value);
                      return (
                        <tr key={metric.name}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {metric.name.replace(/_/g, ' ').toUpperCase()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {metric.value.toFixed(2)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {metric.unit}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(status)}`}>
                              {status}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {new Date(metric.timestamp).toLocaleString()}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* 告警管理标签页 */}
        {activeTab === 'alerts' && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-6">
                告警历史
              </h3>
              {alerts.length > 0 ? (
                <div className="space-y-3">
                  {alerts.map((alert) => (
                    <div key={alert.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getAlertSeverityColor(alert.severity)}`}>
                          {alert.severity.toUpperCase()}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{alert.message}</p>
                          <p className="text-xs text-gray-500">
                            {new Date(alert.timestamp).toLocaleString()}
                            {alert.resolved && (
                              <span className="ml-2 text-green-600">
                                (已解决 - {new Date(alert.resolved as any).toLocaleString()})
                              </span>
                            )}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {alert.resolved ? (
                          <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                            已解决
                          </span>
                        ) : (
                          <button className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700">
                            处理
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-4">暂无告警记录</p>
              )}
            </div>
          </div>
        )}

        {/* 性能分析标签页 */}
        {activeTab === 'performance' && (
          <div className="space-y-6">
            {/* 前端性能指标 */}
            <div className="bg-white shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-6">
                  前端性能指标
                </h3>
                {Object.keys(frontendMetrics).length > 0 ? (
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {Object.entries(frontendMetrics).map(([name, stats]) => (
                      <div key={name} className="border rounded-lg p-4">
                        <h4 className="text-sm font-medium text-gray-900 mb-2">
                          {name.replace(/_/g, ' ').toUpperCase()}
                        </h4>
                        {stats && typeof stats === 'object' && 'avg' in stats ? (
                          <div className="space-y-1 text-sm">
                            <div className="flex justify-between">
                              <span className="text-gray-600">平均值:</span>
                              <span className="font-medium">{stats.avg.toFixed(2)}ms</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">P95:</span>
                              <span className="font-medium">{stats.p95.toFixed(2)}ms</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">P99:</span>
                              <span className="font-medium">{stats.p99.toFixed(2)}ms</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-600">采样数:</span>
                              <span className="font-medium">{stats.count}</span>
                            </div>
                          </div>
                        ) : (
                          <p className="text-sm text-gray-500">暂无数据</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-4">暂无前端性能数据</p>
                )}
              </div>
            </div>

            {/* 性能优化建议 */}
            <div className="bg-white shadow rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <h3 className="text-lg leading-6 font-medium text-gray-900 mb-6">
                  性能优化建议
                </h3>
                <div className="space-y-4">
                  <div className="p-4 border-l-4 border-blue-500 bg-blue-50">
                    <div className="flex">
                      <div className="ml-3">
                        <p className="text-sm text-blue-700">
                          <strong>图片优化:</strong> 使用现代图片格式（WebP、AVIF）和响应式图片可以显著减少页面加载时间。
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 border-l-4 border-green-500 bg-green-50">
                    <div className="flex">
                      <div className="ml-3">
                        <p className="text-sm text-green-700">
                          <strong>代码分割:</strong> 使用动态导入和代码分割可以减少初始JavaScript包大小。
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 border-l-4 border-yellow-500 bg-yellow-50">
                    <div className="flex">
                      <div className="ml-3">
                        <p className="text-sm text-yellow-700">
                          <strong>缓存策略:</strong> 实施适当的缓存策略可以减少重复请求，提高用户体验。
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}