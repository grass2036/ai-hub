'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// 类型定义
interface AuditLog {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  user_id?: string;
  old_values: Record<string, any>;
  new_values: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  metadata: Record<string, any>;
  created_at: string;
}

interface Pagination {
  page: number;
  limit: number;
  total: number;
  pages: number;
}

interface AuditLogResponse {
  logs: AuditLog[];
  pagination: Pagination;
}

interface SecurityEvent {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  user_id?: string;
  created_at: string;
  ip_address?: string;
  metadata: Record<string, any>;
}

interface SecurityEventsResponse {
  period: {
    start_date: string | null;
    end_date: string | null;
  };
  total_events: number;
  events_by_severity: Record<string, SecurityEvent[]>;
  all_events: SecurityEvent[];
}

export default function AuditPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'logs' | 'security' | 'stats'>('logs');
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [securityEvents, setSecurityEvents] = useState<SecurityEventsResponse | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState<Pagination | null>(null);
  const [filters, setFilters] = useState({
    page: 1,
    limit: 50,
    action: '',
    resource_type: '',
    user_id: '',
    start_date: '',
    end_date: '',
    severity: ''
  });

  // 模拟数据
  const mockLogs: AuditLog[] = [
    {
      id: '1',
      action: 'user_login',
      resource_type: 'user',
      resource_id: 'user_123',
      user_id: 'user_123',
      old_values: {},
      new_values: { last_login: new Date().toISOString() },
      ip_address: '192.168.1.1',
      user_agent: 'Mozilla/5.0...',
      metadata: {},
      created_at: new Date().toISOString()
    },
    {
      id: '2',
      action: 'api_key_create',
      resource_type: 'api_key',
      resource_id: 'key_456',
      user_id: 'user_123',
      old_values: {},
      new_values: { name: 'Production API Key', permissions: ['read', 'write'] },
      ip_address: '192.168.1.1',
      user_agent: 'Mozilla/5.0...',
      metadata: {},
      created_at: new Date(Date.now() - 3600000).toISOString()
    },
    {
      id: '3',
      action: 'org_update',
      resource_type: 'organization',
      resource_id: 'org_789',
      user_id: 'user_123',
      old_values: { name: 'Old Company Name' },
      new_values: { name: 'New Company Name' },
      ip_address: '192.168.1.1',
      user_agent: 'Mozilla/5.0...',
      metadata: {},
      created_at: new Date(Date.now() - 7200000).toISOString()
    }
  ];

  const mockSecurityEvents: SecurityEventsResponse = {
    period: {
      start_date: new Date(Date.now() - 7 * 24 * 3600000).toISOString(),
      end_date: new Date().toISOString()
    },
    total_events: 5,
    events_by_severity: {
      'low': [
        {
          id: 's1',
          action: 'login_failed',
          resource_type: 'user',
          resource_id: 'user_123',
          user_id: 'user_123',
          created_at: new Date(Date.now() - 3600000).toISOString(),
          ip_address: '192.168.1.100',
          metadata: { reason: 'invalid_password' }
        }
      ],
      'medium': [
        {
          id: 's2',
          action: 'suspicious_activity',
          resource_type: 'user',
          resource_id: 'user_456',
          created_at: new Date(Date.now() - 7200000).toISOString(),
          ip_address: '192.168.1.200',
          metadata: { pattern: 'multiple_failed_logins' }
        }
      ],
      'high': [],
      'critical': []
    },
    all_events: []
  };

  const mockStats = {
    period: {
      days: 30,
      start_date: new Date(Date.now() - 30 * 24 * 3600000).toISOString(),
      end_date: new Date().toISOString()
    },
    activity_summary: {
      total_actions: 1250,
      unique_users: 25,
      action_counts: {
        'user_login': 450,
        'api_key_create': 15,
        'org_update': 8,
        'user_update': 12
      },
      resource_types: {
        'user': 480,
        'api_key': 35,
        'organization': 20,
        'subscription': 8
      }
    },
    security_summary: {
      total_events: 12,
      events_by_severity: {
        'low': 8,
        'medium': 3,
        'high': 1,
        'critical': 0
      }
    }
  };

  useEffect(() => {
    if (activeTab === 'logs') {
      fetchLogs();
    } else if (activeTab === 'security') {
      fetchSecurityEvents();
    } else if (activeTab === 'stats') {
      fetchStats();
    }
  }, [activeTab, filters]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 500));

      const mockPagination: Pagination = {
        page: filters.page,
        limit: filters.limit,
        total: 1250,
        pages: Math.ceil(1250 / filters.limit)
      };

      setLogs(mockLogs);
      setPagination(mockPagination);
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSecurityEvents = async () => {
    setLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 500));
      setSecurityEvents(mockSecurityEvents);
    } catch (error) {
      console.error('Failed to fetch security events:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    setLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 500));
      setStats(mockStats);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      const response = await fetch(`/api/v1/audit/logs/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          format,
          filters,
          start_date: filters.start_date || null,
          end_date: filters.end_date || null
        })
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit_logs.${format}`;
        a.click();
        window.URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  const formatAction = (action: string) => {
    return action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const formatResource = (resource: string) => {
    return resource.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'low': return 'text-green-600 bg-green-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'high': return 'text-red-600 bg-red-100';
      case 'critical': return 'text-red-800 bg-red-200';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">审计日志</h1>
        <p className="text-gray-600">查看和分析系统操作日志及安全事件</p>
      </div>

      {/* 标签页 */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('logs')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'logs'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📋 操作日志
          </button>
          <button
            onClick={() => setActiveTab('security')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'security'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            🔒 安全事件
          </button>
          <button
            onClick={() => setActiveTab('stats')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'stats'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📊 统计分析
          </button>
        </nav>
      </div>

      {/* 筛选器 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">操作类型</label>
            <select
              value={filters.action}
              onChange={(e) => setFilters({ ...filters, action: e.target.value, page: 1 })}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="">全部</option>
              <option value="user_login">用户登录</option>
              <option value="api_key_create">创建API密钥</option>
              <option value="org_update">组织更新</option>
              <option value="subscription_create">订阅创建</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">资源类型</label>
            <select
              value={filters.resource_type}
              onChange={(e) => setFilters({ ...filters, resource_type: e.target.value, page: 1 })}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="">全部</option>
              <option value="user">用户</option>
              <option value="api_key">API密钥</option>
              <option value="organization">组织</option>
              <option value="subscription">订阅</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">开始时间</label>
            <input
              type="datetime-local"
              value={filters.start_date}
              onChange={(e) => setFilters({ ...filters, start_date: e.target.value, page: 1 })}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">结束时间</label>
            <input
              type="datetime-local"
              value={filters.end_date}
              onChange={(e) => setFilters({ ...filters, end_date: e.target.value, page: 1 })}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            />
          </div>
        </div>
        <div className="mt-4 flex justify-between items-center">
          <button
            onClick={() => {
              setFilters({
                page: 1,
                limit: 50,
                action: '',
                resource_type: '',
                user_id: '',
                start_date: '',
                end_date: '',
                severity: ''
              });
            }}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
          >
            重置筛选
          </button>
          <div className="flex space-x-2">
            <button
              onClick={() => handleExport('json')}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
            >
              导出 JSON
            </button>
            <button
              onClick={() => handleExport('csv')}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm"
            >
              导出 CSV
            </button>
          </div>
        </div>
      </div>

      {/* 内容区域 */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <>
          {activeTab === 'logs' && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        时间
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        操作
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        资源
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        用户
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        IP地址
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        操作
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {logs.map((log) => (
                      <tr key={log.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(log.created_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm text-gray-900">
                            {formatAction(log.action)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm text-gray-900">
                            {formatResource(log.resource_type)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {log.user_id || '系统'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {log.ip_address || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <button className="text-blue-600 hover:text-blue-800">
                            查看详情
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {pagination && (
                <div className="px-6 py-3 border-t border-gray-200 flex items-center justify-between">
                  <div className="text-sm text-gray-700">
                    显示 {((pagination.page - 1) * pagination.limit) + 1} 到{' '}
                    {Math.min(pagination.page * pagination.limit, pagination.total)} 条，
                    共 {pagination.total} 条记录
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => setFilters({ ...filters, page: Math.max(1, filters.page - 1) })}
                      disabled={filters.page <= 1}
                      className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                    >
                      上一页
                    </button>
                    <span className="px-3 py-1 text-sm">
                      第 {filters.page} 页，共 {pagination.pages} 页
                    </span>
                    <button
                      onClick={() => setFilters({ ...filters, page: Math.min(pagination.pages, filters.page + 1) })}
                      disabled={filters.page >= pagination.pages}
                      className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                    >
                      下一页
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'security' && securityEvents && (
            <div className="space-y-6">
              {/* 概览统计 */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">总事件数</h3>
                  <p className="text-2xl font-bold text-gray-900">{securityEvents.total_events}</p>
                </div>
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">低风险</h3>
                  <p className="text-2xl font-bold text-green-600">
                    {securityEvents.events_by_severity.low?.length || 0}
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">中风险</h3>
                  <p className="text-2xl font-bold text-yellow-600">
                    {securityEvents.events_by_severity.medium?.length || 0}
                  </p>
                </div>
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">高风险</h3>
                  <p className="text-2xl font-bold text-red-600">
                    {(securityEvents.events_by_severity.high?.length || 0) +
                     (securityEvents.events_by_severity.critical?.length || 0)}
                  </p>
                </div>
              </div>

              {/* 事件列表 */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-medium text-gray-900">安全事件</h3>
                </div>
                <div className="divide-y divide-gray-200">
                  {Object.entries(securityEvents.events_by_severity).map(([severity, events]) => (
                    events.map((event) => (
                      <div key={event.id} className="px-6 py-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-3">
                              <span className={`px-2 py-1 text-xs font-medium rounded-full ${getSeverityColor(severity)}`}>
                                {severity.toUpperCase()}
                              </span>
                              <h4 className="text-sm font-medium text-gray-900">
                                {formatAction(event.action)}
                              </h4>
                              <span className="text-sm text-gray-500">
                                {formatDate(event.created_at)}
                              </span>
                            </div>
                            <div className="mt-2 text-sm text-gray-600">
                              <p>资源: {formatResource(event.resource_type)} ({event.resource_id})</p>
                              {event.ip_address && <p>IP地址: {event.ip_address}</p>}
                              {event.metadata && Object.keys(event.metadata).length > 0 && (
                                <p>详情: {JSON.stringify(event.metadata)}</p>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'stats' && stats && (
            <div className="space-y-6">
              {/* 活动统计 */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">活动统计</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 mb-2">总操作数</h4>
                    <p className="text-3xl font-bold text-gray-900">
                      {stats.activity_summary.total_actions.toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 mb-2">活跃用户</h4>
                    <p className="text-3xl font-bold text-blue-600">
                      {stats.activity_summary.unique_users}
                    </p>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 mb-2">安全事件</h4>
                    <p className="text-3xl font-bold text-red-600">
                      {stats.security_summary.total_events}
                    </p>
                  </div>
                </div>
              </div>

              {/* 操作类型分布 */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">操作类型分布</h3>
                <div className="space-y-3">
                  {Object.entries(stats.activity_summary.action_counts).map(([action, count]) => (
                    <div key={action} className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">{formatAction(action)}</span>
                      <div className="flex items-center space-x-3">
                        <div className="w-32 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{
                              width: `${(count / stats.activity_summary.total_actions) * 100}%`
                            }}
                          ></div>
                        </div>
                        <span className="text-sm font-medium text-gray-900 w-12 text-right">
                          {count}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 资源类型分布 */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">资源类型分布</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(stats.activity_summary.resource_types).map(([resource, count]) => (
                    <div key={resource} className="text-center p-4 bg-gray-50 rounded-lg">
                      <p className="text-2xl font-bold text-gray-900">{count}</p>
                      <p className="text-sm text-gray-600 mt-1">{formatResource(resource)}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}