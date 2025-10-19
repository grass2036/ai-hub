'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';

// 类型定义
interface Metric {
  id: string;
  name: string;
  display_name: string;
  description: string;
  metric_type: string;
  unit: string;
  collection_interval: number;
  warning_threshold?: number;
  critical_threshold?: number;
  is_enabled: boolean;
  created_at: string;
}

interface Alert {
  id: string;
  title: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'active' | 'acknowledged' | 'resolved';
  trigger_value: number;
  threshold_value: number;
  triggered_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
  metadata: Record<string, any>;
}

interface HealthCheck {
  id: string;
  name: string;
  service_name: string;
  status: 'healthy' | 'unhealthy' | 'unknown';
  response_time?: number;
  last_check: string;
  endpoint?: string;
}

interface SystemHealth {
  overall_status: 'healthy' | 'unhealthy' | 'degraded' | 'unknown';
  total_checks: number;
  healthy: number;
  unhealthy: number;
  unknown: number;
  health_percentage: number;
  services: Record<string, {
    status: string;
    response_time?: number;
    last_check: string;
    endpoint?: string;
  }>;
}

export default function MonitoringPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'overview' | 'metrics' | 'alerts' | 'health' | 'dashboards'>('overview');
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [healthChecks, setHealthChecks] = useState<HealthCheck[]>([]);
  const [loading, setLoading] = useState(false);

  // 表单状态
  const [showCreateMetric, setShowCreateMetric] = useState(false);
  const [showCreateAlertRule, setShowCreateAlertRule] = useState(false);

  // 模拟数据
  const mockMetrics: Metric[] = [
    {
      id: '1',
      name: 'api_requests_per_second',
      display_name: 'API请求率',
      description: '每秒API请求数',
      metric_type: 'api',
      unit: 'req/sec',
      collection_interval: 60,
      warning_threshold: 100,
      critical_threshold: 200,
      is_enabled: true,
      created_at: new Date().toISOString()
    },
    {
      id: '2',
      name: 'api_response_time_ms',
      display_name: 'API响应时间',
      description: 'API平均响应时间',
      metric_type: 'performance',
      unit: 'ms',
      collection_interval: 60,
      warning_threshold: 500,
      critical_threshold: 1000,
      is_enabled: true,
      created_at: new Date().toISOString()
    },
    {
      id: '3',
      name: 'cpu_usage_percent',
      display_name: 'CPU使用率',
      description: '服务器CPU使用率',
      metric_type: 'system',
      unit: '%',
      collection_interval: 30,
      warning_threshold: 70,
      critical_threshold: 90,
      is_enabled: true,
      created_at: new Date().toISOString()
    },
    {
      id: '4',
      name: 'memory_usage_percent',
      display_name: '内存使用率',
      description: '服务器内存使用率',
      metric_type: 'system',
      unit: '%',
      collection_interval: 30,
      warning_threshold: 80,
      critical_threshold: 95,
      is_enabled: true,
      created_at: new Date().toISOString()
    }
  ];

  const mockAlerts: Alert[] = [
    {
      id: '1',
      title: 'CPU使用率过高',
      message: '服务器CPU使用率超过阈值',
      severity: 'high',
      status: 'active',
      trigger_value: 92.5,
      threshold_value: 90,
      triggered_at: new Date(Date.now() - 3600000).toISOString(),
      metadata: {
        'rule_name': 'CPU告警',
        'metric_name': 'cpu_usage_percent'
      }
    },
    {
      id: '2',
      title: 'API响应时间延迟',
      message: 'API响应时间超过500ms',
      severity: 'medium',
      status: 'acknowledged',
      trigger_value: 650,
      threshold_value: 500,
      triggered_at: new Date(Date.now() - 7200000).toISOString(),
      acknowledged_at: new Date(Date.now() - 1800000).toISOString(),
      metadata: {
        'rule_name': 'API响应时间告警',
        'metric_name': 'api_response_time_ms'
      }
    },
    {
      id: '3',
      title: '磁盘空间不足',
      message: '磁盘使用率超过85%',
      severity: 'critical',
      status: 'resolved',
      trigger_value: 88.2,
      threshold_value: 85,
      triggered_at: new Date(Date.now() - 10800000).toISOString(),
      resolved_at: new Date(Date.now() - 3600000).toISOString(),
      metadata: {
        'rule_name': '磁盘空间告警',
        'metric_name': 'disk_usage_percent'
      }
    }
  ];

  const mockSystemHealth: SystemHealth = {
    overall_status: 'degraded',
    total_checks: 8,
    healthy: 6,
    unhealthy: 1,
    unknown: 1,
    health_percentage: 75,
    services: {
      'API Gateway': {
        status: 'healthy',
        response_time: 45,
        last_check: new Date().toISOString(),
        endpoint: '/api/health'
      },
      'Database': {
        status: 'healthy',
        response_time: 12,
        last_check: new Date().toISOString(),
        endpoint: 'localhost:5432'
      },
      'Redis Cache': {
        status: 'healthy',
        response_time: 3,
        last_check: new Date().toISOString(),
        endpoint: 'localhost:6379'
      },
      'File Storage': {
        status: 'unhealthy',
        response_time: 250,
        last_check: new Date().toISOString(),
        endpoint: '/storage/health'
      },
      'Payment Service': {
        status: 'healthy',
        response_time: 89,
        last_check: new Date().toISOString(),
        endpoint: '/payments/health'
      },
      'AI Service': {
        status: 'unknown',
        last_check: new Date(Date.now() - 300000).toISOString(),
        endpoint: '/ai/health'
      }
    }
  };

  const mockHealthChecks: HealthCheck[] = [
    {
      id: '1',
      name: 'API Gateway Health Check',
      service_name: 'API Gateway',
      status: 'healthy',
      response_time: 45,
      last_check: new Date().toISOString(),
      endpoint: '/api/health'
    },
    {
      id: '2',
      name: 'Database Connection Check',
      service_name: 'Database',
      status: 'healthy',
      response_time: 12,
      last_check: new Date().toISOString(),
      endpoint: 'localhost:5432'
    },
    {
      id: '3',
      name: 'File Storage Check',
      service_name: 'File Storage',
      status: 'unhealthy',
      response_time: 250,
      last_check: new Date().toISOString(),
      endpoint: '/storage/health'
    }
  ];

  useEffect(() => {
    if (activeTab === 'overview') {
      fetchOverviewData();
    } else if (activeTab === 'metrics') {
      fetchMetrics();
    } else if (activeTab === 'alerts') {
      fetchAlerts();
    } else if (activeTab === 'health') {
      fetchHealthData();
    }
  }, [activeTab]);

  const fetchOverviewData = async () => {
    setLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));
      setSystemHealth(mockSystemHealth);
      setAlerts(mockAlerts);
    } catch (error) {
      console.error('Failed to fetch overview data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 800));
      setMetrics(mockMetrics);
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 800));
      setAlerts(mockAlerts);
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchHealthData = async () => {
    setLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 800));
      setSystemHealth(mockSystemHealth);
      setHealthChecks(mockHealthChecks);
    } catch (error) {
      console.error('Failed to fetch health data:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600 bg-green-100';
      case 'unhealthy': return 'text-red-600 bg-red-100';
      case 'degraded': return 'text-yellow-600 bg-yellow-100';
      case 'unknown': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'low': return 'text-blue-600 bg-blue-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'high': return 'text-orange-600 bg-orange-100';
      case 'critical': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getOverallStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-100 text-green-800';
      case 'unhealthy': return 'bg-red-100 text-red-800';
      case 'degraded': return 'bg-yellow-100 text-yellow-800';
      case 'unknown': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">系统监控</h1>
        <p className="text-gray-600">实时监控系统健康状态、性能指标和告警信息</p>
      </div>

      {/* 标签页 */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'overview'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📊 总览
          </button>
          <button
            onClick={() => setActiveTab('metrics')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'metrics'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📈 指标
          </button>
          <button
            onClick={() => setActiveTab('alerts')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'alerts'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            🚨 告警
          </button>
          <button
            onClick={() => setActiveTab('health')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'health'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            ❤️ 健康检查
          </button>
          <button
            onClick={() => setActiveTab('dashboards')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'dashboards'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📋 仪表板
          </button>
        </nav>
      </div>

      {/* 操作按钮 */}
      <div className="mb-6 flex justify-end space-x-3">
        {activeTab === 'metrics' && (
          <button
            onClick={() => setShowCreateMetric(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            + 创建指标
          </button>
        )}
        {activeTab === 'alerts' && (
          <button
            onClick={() => setShowCreateAlertRule(true)}
            className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700"
          >
            + 创建告警规则
          </button>
        )}
      </div>

      {/* 内容区域 */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <>
          {activeTab === 'overview' && systemHealth && (
            <div className="space-y-6">
              {/* 系统健康状态卡片 */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">系统状态</h3>
                  <div className="flex items-center space-x-2">
                    <div className={`px-3 py-1 rounded-full text-sm font-medium ${getOverallStatusColor(systemHealth.overall_status)}`}>
                      {systemHealth.overall_status.toUpperCase()}
                    </div>
                    <span className="text-2xl font-bold text-gray-900">
                      {systemHealth.health_percentage.toFixed(0)}%
                    </span>
                  </div>
                </div>

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">健康检查</h3>
                  <p className="text-2xl font-bold text-green-600">
                    {systemHealth.healthy}
                  </p>
                  <p className="text-sm text-gray-600">
                    / {systemHealth.total_checks}
                  </p>
                </div>

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">问题服务</h3>
                  <p className="text-2xl font-bold text-red-600">
                    {systemHealth.unhealthy}
                  </p>
                  <p className="text-sm text-gray-600">
                    需要关注
                  </p>
                </div>

                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">活跃告警</h3>
                  <p className="text-2xl font-bold text-orange-600">
                    {alerts.filter(a => a.status === 'active').length}
                  </p>
                  <p className="text-sm text-gray-600">
                    需要处理
                  </p>
                </div>
              </div>

              {/* 服务健康状态 */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">服务健康状态</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {Object.entries(systemHealth.services).map(([serviceName, service]) => (
                    <div key={serviceName} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium text-gray-900">{serviceName}</h4>
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(service.status)}`}>
                          {service.status.toUpperCase()}
                        </span>
                      </div>
                      <div className="space-y-1">
                        {service.response_time && (
                          <p className="text-sm text-gray-600">
                            响应时间: {service.response_time}ms
                          </p>
                        )}
                        <p className="text-sm text-gray-600">
                          最后检查: {formatDate(service.last_check)}
                        </p>
                        {service.endpoint && (
                          <p className="text-xs text-gray-500 truncate">
                            {service.endpoint}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 最近告警 */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-medium text-gray-900">最近告警</h3>
                  <button
                    onClick={() => setActiveTab('alerts')}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    查看全部
                  </button>
                </div>
                <div className="space-y-3">
                  {alerts.slice(0, 5).map((alert) => (
                    <div key={alert.id} className="flex items-center justify-between p-4 border border-gray-100 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getSeverityColor(alert.severity)}`}>
                          {alert.severity.toUpperCase()}
                        </span>
                        <div>
                          <p className="text-sm font-medium text-gray-900">{alert.title}</p>
                          <p className="text-sm text-gray-600">{alert.message}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          alert.status === 'active' ? 'bg-red-100 text-red-800' :
                          alert.status === 'acknowledged' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-green-100 text-green-800'
                        }`}>
                          {alert.status === 'active' ? '活跃' :
                           alert.status === 'acknowledged' ? '已确认' : '已解决'}
                        </span>
                        <p className="text-xs text-gray-500 mt-1">
                          {formatDate(alert.triggered_at)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'metrics' && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        指标名称
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        类型
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        单位
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        收集间隔
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        阈值
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        状态
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        操作
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {metrics.map((metric) => (
                      <tr key={metric.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {metric.display_name}
                            </div>
                            <div className="text-sm text-gray-500">
                              {metric.name}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                            {metric.metric_type}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {metric.unit}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {metric.collection_interval}s
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-600">
                            {metric.warning_threshold && (
                              <div>警告: {metric.warning_threshold}</div>
                            )}
                            {metric.critical_threshold && (
                              <div>严重: {metric.critical_threshold}</div>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                            metric.is_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {metric.is_enabled ? '启用' : '禁用'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <button className="text-blue-600 hover:text-blue-900 mr-3">
                            编辑
                          </button>
                          <button className="text-red-600 hover:text-red-900">
                            删除
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'alerts' && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        告警信息
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        严重程度
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        状态
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        触发值
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        阈值
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        触发时间
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        操作
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {alerts.map((alert) => (
                      <tr key={alert.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {alert.title}
                            </div>
                            <div className="text-sm text-gray-500">
                              {alert.message}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getSeverityColor(alert.severity)}`}>
                            {alert.severity.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                            alert.status === 'active' ? 'bg-red-100 text-red-800' :
                            alert.status === 'acknowledged' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-green-100 text-green-800'
                          }`}>
                            {alert.status === 'active' ? '活跃' :
                             alert.status === 'acknowledged' ? '已确认' : '已解决'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {alert.trigger_value}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {alert.threshold_value}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(alert.triggered_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          {alert.status === 'active' && (
                            <button className="text-yellow-600 hover:text-yellow-800 mr-3">
                              确认
                            </button>
                          )}
                          <button className="text-blue-600 hover:text-blue-800 mr-3">
                            详情
                          </button>
                          {alert.status !== 'resolved' && (
                            <button className="text-green-600 hover:text-green-800">
                              解决
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'health' && (
            <div className="space-y-6">
              {/* 健康检查状态 */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">健康服务</h3>
                  <p className="text-3xl font-bold text-green-600">
                    {systemHealth?.healthy || 0}
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">异常服务</h3>
                  <p className="text-3xl font-bold text-red-600">
                    {systemHealth?.unhealthy || 0}
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">未知状态</h3>
                  <p className="text-3xl font-bold text-gray-600">
                    {systemHealth?.unknown || 0}
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">健康率</h3>
                  <p className="text-3xl font-bold text-blue-600">
                    {systemHealth?.health_percentage.toFixed(0) || 0}%
                  </p>
                </div>
              </div>

              {/* 健康检查详情 */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <h3 className="text-lg font-medium text-gray-900 mb-4 p-6">健康检查详情</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          检查名称
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          服务
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          状态
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          响应时间
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          最后检查
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          端点
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {healthChecks.map((check) => (
                        <tr key={check.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {check.name}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {check.service_name}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(check.status)}`}>
                              {check.status.toUpperCase()}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {check.response_time ? `${check.response_time}ms` : '-'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {formatDate(check.last_check)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {check.endpoint || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'dashboards' && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">监控仪表板</h3>
              <p className="text-gray-600">
                自定义监控仪表板功能正在开发中，将提供拖拽式仪表板配置、实时数据展示等功能。
              </p>
              <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center p-6 bg-blue-50 rounded-lg">
                  <div className="text-3xl mb-3">📊</div>
                  <h4 className="font-medium text-gray-900 mb-2">自定义仪表板</h4>
                  <p className="text-sm text-gray-600">
                    拖拽式配置，实时数据展示
                  </p>
                </div>
                <div className="text-center p-6 bg-green-50 rounded-lg">
                  <div className="text-3xl mb-3">📈</div>
                  <h4 className="font-medium text-gray-900 mb-2">多样化图表</h4>
                  <p className="text-sm text-gray-600">
                    折线图、柱状图、饼图等
                  </p>
                </div>
                <div className="text-center p-6 bg-purple-50 rounded-lg">
                  <div className="text-3xl mb-3">⚡</div>
                  <h4 className="font-medium text-gray-900 mb-2">实时更新</h4>
                  <p className="text-sm text-gray-600">
                    自动刷新，WebSocket支持
                  </p>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* 创建指标模态框 */}
      {showCreateMetric && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">创建监控指标</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">指标名称</label>
                <input
                  type="text"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  placeholder="例如: api_response_time"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">显示名称</label>
                <input
                  type="text"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  placeholder="例如: API响应时间"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">指标类型</label>
                <select className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                  <option value="api">API</option>
                  <option value="system">系统</option>
                  <option value="performance">性能</option>
                  <option value="business">业务</option>
                </select>
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setShowCreateMetric(false)}
                className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900"
              >
                取消
              </button>
              <button
                onClick={() => setShowCreateMetric(false)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 创建告警规则模态框 */}
      {showCreateAlertRule && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">创建告警规则</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">规则名称</label>
                <input
                  type="text"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  placeholder="例如: CPU使用率告警"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">监控指标</label>
                <select className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                  <option value="">请选择指标</option>
                  {metrics.map((metric) => (
                    <option key={metric.id} value={metric.id}>
                      {metric.display_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">触发条件</label>
                <select className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                  <option value=">">请选择条件</option>
                  <option value=">">&gt; 大于</option>
                  <option value="<">&lt; 小于</option>
                  <option value=">="> 大于等于</option>
                  <option value="<=">&lt;= 小于等于</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">阈值</label>
                <input
                  type="number"
                  className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  placeholder="例如: 90"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">严重程度</label>
                <select className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500">
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                  <option value="critical">严重</option>
                </select>
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setShowCreateAlertRule(false)}
                className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900"
              >
                取消
              </button>
              <button
                onClick={() => setShowCreateAlertRule(false)}
                className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}