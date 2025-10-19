/**
 * 系统监控仪表板
 * Week 5 Day 3: 系统监控和运维自动化
 */

"use client";

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Activity,
  AlertCircle,
  CheckCircle,
  XCircle,
  Cpu,
  HardDrive,
  MemoryStick,
  Wifi,
  Database,
  Server,
  TrendingUp,
  TrendingDown,
  Zap,
  Users,
  Clock,
  RefreshCw
} from 'lucide-react';

// 模拟数据
const mockSystemMetrics = {
  cpu: {
    usage: 45.2,
    cores: 8,
    load_avg: [1.2, 1.5, 1.8]
  },
  memory: {
    used: 6.4,
    total: 16.0,
    usage_percent: 40
  },
  disk: {
    used: 120.5,
    total: 500.0,
    usage_percent: 24.1
  },
  network: {
    bytes_sent: 1024000,
    bytes_recv: 2048000,
    packets_sent: 1500,
    packets_recv: 2800
  }
};

const mockHealthStatus = {
  overall: 'healthy',
  timestamp: new Date().toISOString(),
  checks: {
    database: {
      status: 'healthy',
      message: 'Database connection successful',
      response_time_ms: 15,
      details: {
        active_connections: 12,
        database_size: '2.5GB',
        connection_successful: true
      }
    },
    redis: {
      status: 'healthy',
      message: 'Redis connection successful',
      response_time_ms: 8,
      details: {
        connected: true,
        redis_version: '6.2.6',
        used_memory: '15.2MB',
        connected_clients: 3
      }
    },
    api_service: {
      status: 'healthy',
      message: 'All API endpoints healthy (2/2)',
      response_time_ms: 45,
      details: {
        endpoints: {
          '/health': { success: true, status_code: 200 },
          '/api/v1/status': { success: true, status_code: 200 }
        },
        successful_endpoints: 2,
        total_endpoints: 2
      }
    },
    ai_services: {
      status: 'degraded',
      message: 'Some AI services degraded (1/2)',
      response_time_ms: 120,
      details: {
        services: {
          openrouter: { configured: true, success: true },
          google_gemini: { configured: true, success: false, error: 'timeout' }
        },
        configured_services: 2,
        healthy_services: 1
      }
    }
  }
};

const mockRecentAlerts = [
  {
    id: 1,
    level: 'warning',
    title: 'AI Service Timeout',
    message: 'Google Gemini service response timeout',
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
    status: 'active'
  },
  {
    id: 2,
    level: 'info',
    title: 'High Memory Usage',
    message: 'Memory usage reached 75%',
    timestamp: new Date(Date.now() - 15 * 60 * 1000),
    status: 'resolved'
  },
  {
    id: 3,
    level: 'error',
    title: 'Database Connection Failed',
    message: 'Failed to connect to PostgreSQL',
    timestamp: new Date(Date.now() - 30 * 60 * 1000),
    status: 'resolved'
  }
];

const mockLogStats = {
  total_logs: 15420,
  by_level: {
    DEBUG: 3200,
    INFO: 8500,
    WARNING: 2100,
    ERROR: 1200,
    CRITICAL: 420
  },
  error_rate: 10.5,
  top_errors: [
    { message: 'Database connection timeout', count: 45, level: 'ERROR' },
    { message: 'API rate limit exceeded', count: 32, level: 'WARNING' },
    { message: 'Invalid API key provided', count: 28, level: 'ERROR' }
  ]
};

export default function MonitoringDashboard() {
  const [activeTab, setActiveTab] = useState('overview');
  const [systemMetrics, setSystemMetrics] = useState(mockSystemMetrics);
  const [healthStatus, setHealthStatus] = useState(mockHealthStatus);
  const [recentAlerts, setRecentAlerts] = useState(mockRecentAlerts);
  const [logStats, setLogStats] = useState(mockLogStats);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [isLoading, setIsLoading] = useState(false);

  // 模拟数据刷新
  const refreshData = async () => {
    setIsLoading(true);

    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000));

    // 更新时间戳
    setLastRefresh(new Date());
    setIsLoading(false);
  };

  // 自动刷新
  useEffect(() => {
    const interval = setInterval(() => {
      refreshData();
    }, 30000); // 30秒刷新一次

    return () => clearInterval(interval);
  }, []);

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'degraded':
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      case 'unhealthy':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Activity className="w-5 h-5 text-gray-500" />;
    }
  };

  const getHealthBadgeVariant = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'default';
      case 'degraded':
        return 'secondary';
      case 'unhealthy':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const getAlertIcon = (level: string) => {
    switch (level) {
      case 'critical':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'warning':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      default:
        return <CheckCircle className="w-4 h-4 text-blue-500" />;
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">系统监控仪表板</h1>
          <p className="text-gray-600 mt-2">实时监控AI Hub Platform系统状态和性能指标</p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="text-sm text-gray-500">
            最后更新: {lastRefresh.toLocaleTimeString()}
          </div>
          <Button
            onClick={refreshData}
            disabled={isLoading}
            variant="outline"
            size="sm"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            刷新数据
          </Button>
        </div>
      </div>

      {/* 总体状态卡片 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {getHealthIcon(healthStatus.overall)}
              <div>
                <CardTitle className="text-lg">系统状态</CardTitle>
                <CardDescription>
                  整体系统健康状况
                </CardDescription>
              </div>
            </div>
            <Badge variant={getHealthBadgeVariant(healthStatus.overall)}>
              {healthStatus.overall.toUpperCase()}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {Object.values(healthStatus.checks).filter(c => c.status === 'healthy').length}
              </div>
              <div className="text-sm text-gray-500">健康</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-600">
                {Object.values(healthStatus.checks).filter(c => c.status === 'degraded').length}
              </div>
              <div className="text-sm text-gray-500">降级</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {Object.values(healthStatus.checks).filter(c => c.status === 'unhealthy').length}
              </div>
              <div className="text-sm text-gray-500">故障</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {healthStatus.response_time_ms.toFixed(0)}ms
              </div>
              <div className="text-sm text-gray-500">平均响应时间</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">概览</TabsTrigger>
          <TabsTrigger value="system">系统资源</TabsTrigger>
          <TabsTrigger value="health">健康检查</TabsTrigger>
          <TabsTrigger value="logs">日志统计</TabsTrigger>
          <TabsTrigger value="alerts">告警</TabsTrigger>
        </TabsList>

        {/* 概览标签页 */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* CPU 使用率 */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">CPU 使用率</CardTitle>
                <Cpu className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemMetrics.cpu.usage}%</div>
                <Progress value={systemMetrics.cpu.usage} className="mt-2" />
                <p className="text-xs text-muted-foreground mt-2">
                  负载平均: {systemMetrics.cpu.load_avg.map(v => v.toFixed(2)).join(', ')}
                </p>
              </CardContent>
            </Card>

            {/* 内存使用率 */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">内存使用率</CardTitle>
                <MemoryStick className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemMetrics.memory.usage_percent}%</div>
                <Progress value={systemMetrics.memory.usage_percent} className="mt-2" />
                <p className="text-xs text-muted-foreground mt-2">
                  {systemMetrics.memory.used.toFixed(1)}GB / {systemMetrics.memory.total}GB
                </p>
              </CardContent>
            </Card>

            {/* 磁盘使用率 */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">磁盘使用率</CardTitle>
                <HardDrive className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemMetrics.disk.usage_percent}%</div>
                <Progress value={systemMetrics.disk.usage_percent} className="mt-2" />
                <p className="text-xs text-muted-foreground mt-2">
                  {systemMetrics.disk.used.toFixed(1)}GB / {systemMetrics.disk.total.toFixed(1)}GB
                </p>
              </CardContent>
            </Card>

            {/* 网络流量 */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">网络流量</CardTitle>
                <Wifi className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>上行</span>
                    <span>{(systemMetrics.network.bytes_sent / 1024 / 1024).toFixed(1)} MB</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>下行</span>
                    <span>{(systemMetrics.network.bytes_recv / 1024 / 1024).toFixed(1)} MB</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 最近告警 */}
          <Card>
            <CardHeader>
              <CardTitle>最近告警</CardTitle>
              <CardDescription>系统最近的告警信息</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {recentAlerts.slice(0, 5).map((alert) => (
                  <div key={alert.id} className="flex items-start space-x-3 p-3 border rounded-lg">
                    <div className="mt-1">
                      {getAlertIcon(alert.level)}
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium">{alert.title}</p>
                        <Badge variant={alert.status === 'active' ? 'destructive' : 'secondary'}>
                          {alert.status === 'active' ? '活跃' : '已解决'}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600">{alert.message}</p>
                      <p className="text-xs text-gray-400">
                        {alert.timestamp.toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 系统资源标签页 */}
        <TabsContent value="system" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* CPU 详细信息 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Cpu className="w-5 h-5" />
                  <span>CPU 使用详情</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>当前使用率</span>
                    <span className="font-medium">{systemMetrics.cpu.usage}%</span>
                  </div>
                  <Progress value={systemMetrics.cpu.usage} className="h-2" />
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">CPU 核心数</p>
                    <p className="font-medium">{systemMetrics.cpu.cores}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">1分钟负载</p>
                    <p className="font-medium">{systemMetrics.cpu.load_avg[0]}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">5分钟负载</p>
                    <p className="font-medium">{systemMetrics.cpu.load_avg[1]}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">15分钟负载</p>
                    <p className="font-medium">{systemMetrics.cpu.load_avg[2]}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 内存详细信息 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <MemoryStick className="w-5 h-5" />
                  <span>内存使用详情</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>使用率</span>
                    <span className="font-medium">{systemMetrics.memory.usage_percent}%</span>
                  </div>
                  <Progress value={systemMetrics.memory.usage_percent} className="h-2" />
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">已使用</p>
                    <p className="font-medium">{systemMetrics.memory.used.toFixed(1)} GB</p>
                  </div>
                  <div>
                    <p className="text-gray-500">总内存</p>
                    <p className="font-medium">{systemMetrics.memory.total} GB</p>
                  </div>
                  <div>
                    <p className="text-gray-500">可用内存</p>
                    <p className="font-medium">{(systemMetrics.memory.total - systemMetrics.memory.used).toFixed(1)} GB</p>
                  </div>
                  <div>
                    <p className="text-gray-500">使用率</p>
                    <p className="font-medium">{systemMetrics.memory.usage_percent}%</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 磁盘详细信息 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <HardDrive className="w-5 h-5" />
                  <span>磁盘使用详情</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>使用率</span>
                    <span className="font-medium">{systemMetrics.disk.usage_percent}%</span>
                  </div>
                  <Progress value={systemMetrics.disk.usage_percent} className="h-2" />
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">已使用</p>
                    <p className="font-medium">{systemMetrics.disk.used.toFixed(1)} GB</p>
                  </div>
                  <div>
                    <p className="text-gray-500">总容量</p>
                    <p className="font-medium">{systemMetrics.disk.total.toFixed(1)} GB</p>
                  </div>
                  <div>
                    <p className="text-gray-500">可用空间</p>
                    <p className="font-medium">{(systemMetrics.disk.total - systemMetrics.disk.used).toFixed(1)} GB</p>
                  </div>
                  <div>
                    <p className="text-gray-500">使用率</p>
                    <p className="font-medium">{systemMetrics.disk.usage_percent}%</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 网络详细信息 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Wifi className="w-5 h-5" />
                  <span>网络流量详情</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-gray-500">发送字节数</p>
                    <p className="font-medium">{(systemMetrics.network.bytes_sent / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                  <div>
                    <p className="text-gray-500">接收字节数</p>
                    <p className="font-medium">{(systemMetrics.network.bytes_recv / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                  <div>
                    <p className="text-gray-500">发送包数</p>
                    <p className="font-medium">{systemMetrics.network.packets_sent.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">接收包数</p>
                    <p className="font-medium">{systemMetrics.network.packets_recv.toLocaleString()}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* 健康检查标签页 */}
        <TabsContent value="health" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {Object.entries(healthStatus.checks).map(([component, check]) => (
              <Card key={component}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {getHealthIcon(check.status)}
                      <div>
                        <CardTitle className="text-lg capitalize">{component.replace('_', ' ')}</CardTitle>
                        <CardDescription>
                          {check.message}
                        </CardDescription>
                      </div>
                    </div>
                    <Badge variant={getHealthBadgeVariant(check.status)}>
                      {check.status.toUpperCase()}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">响应时间</span>
                      <span className="font-medium">{check.response_time_ms}ms</span>
                    </div>
                    {check.details && (
                      <div className="border-t pt-2">
                        {Object.entries(check.details).map(([key, value]) => (
                          <div key={key} className="flex justify-between text-sm">
                            <span className="text-gray-500 capitalize">{key.replace('_', ' ')}</span>
                            <span className="font-medium">{String(value)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* 日志统计标签页 */}
        <TabsContent value="logs" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* 日志级别分布 */}
            <Card>
              <CardHeader>
                <CardTitle>日志级别分布</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(logStats.by_level).map(([level, count]) => (
                    <div key={level} className="flex justify-between items-center">
                      <span className="text-sm font-medium capitalize">{level}</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              level === 'ERROR' ? 'bg-red-500' :
                              level === 'WARNING' ? 'bg-yellow-500' :
                              level === 'CRITICAL' ? 'bg-red-600' :
                              'bg-blue-500'
                            }`}
                            style={{ width: `${(count / logStats.total_logs) * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-sm font-medium w-12 text-right">
                          {count}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* 错误统计 */}
            <Card>
              <CardHeader>
                <CardTitle>错误统计</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="text-center">
                    <div className="text-3xl font-bold text-red-600">
                      {logStats.error_rate.toFixed(1)}%
                    </div>
                    <p className="text-sm text-gray-500">错误率</p>
                  </div>
                  <div className="border-t pt-4">
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">总日志数</span>
                        <span className="font-medium">{logStats.total_logs.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">错误日志数</span>
                        <span className="font-medium text-red-600">
                          {(logStats.total_logs * logStats.error_rate / 100).toFixed(0)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 热门错误 */}
            <Card>
              <CardHeader>
                <CardTitle>热门错误</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {logStats.top_errors.map((error, index) => (
                    <div key={index} className="border-b pb-2 last:border-0">
                      <div className="flex justify-between items-start">
                        <div className="flex-1 mr-2">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {error.message}
                          </p>
                          <Badge variant={error.level === 'ERROR' ? 'destructive' : 'secondary'} className="mt-1">
                            {error.level}
                          </Badge>
                        </div>
                        <div className="text-sm font-medium text-gray-500">
                          {error.count}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* 告警标签页 */}
        <TabsContent value="alerts" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>告警列表</CardTitle>
              <CardDescription>系统告警和通知记录</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentAlerts.map((alert) => (
                  <div key={alert.id} className="flex items-start space-x-3 p-4 border rounded-lg">
                    <div className="mt-1">
                      {getAlertIcon(alert.level)}
                    </div>
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-medium">{alert.title}</h4>
                        <div className="flex items-center space-x-2">
                          <Badge variant={alert.status === 'active' ? 'destructive' : 'secondary'}>
                            {alert.status === 'active' ? '活跃' : '已解决'}
                          </Badge>
                          <Badge variant="outline">
                            {alert.level.toUpperCase()}
                          </Badge>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600">{alert.message}</p>
                      <p className="text-xs text-gray-400">
                        {alert.timestamp.toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}