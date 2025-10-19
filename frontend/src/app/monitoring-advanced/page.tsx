"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Cpu,
  Database,
  HardDrive,
  MemoryStick,
  RefreshCw,
  Server,
  TrendingUp,
  TrendingDown,
  Zap,
  Globe,
  Shield,
  AlertCircle
} from 'lucide-react';

interface MetricData {
  timestamp: string;
  value: number;
  label?: string;
}

interface HealthCheck {
  check_id: string;
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'critical' | 'unknown';
  last_check: string;
  uptime_percentage: number;
  avg_response_time: number;
  error_rate: number;
}

interface LogAnomaly {
  anomaly_id: string;
  anomaly_type: string;
  description: string;
  detected_at: string;
  severity: string;
  resolved: boolean;
}

interface AutomationRule {
  rule_id: string;
  name: string;
  enabled: boolean;
  total_executions: number;
  success_rate: number;
  last_executed?: string;
}

interface TraceData {
  trace_id: string;
  span_count: number;
  duration_ms: number;
  status: string;
  services: string[];
}

export default function AdvancedMonitoringPage() {
  const [systemMetrics, setSystemMetrics] = useState({
    cpu: [] as MetricData[],
    memory: [] as MetricData[],
    disk: [] as MetricData[],
    network: [] as MetricData[]
  });

  const [healthChecks, setHealthChecks] = useState<HealthCheck[]>([]);
  const [logAnomalies, setLogAnomalies] = useState<LogAnomaly[]>([]);
  const [automationRules, setAutomationRules] = useState<AutomationRule[]>([]);
  const [traces, setTraces] = useState<TraceData[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  // 模拟数据获取
  const fetchMonitoringData = async () => {
    setIsLoading(true);
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000));

      // 生成模拟的系统指标数据
      const now = new Date();
      const generateMetricData = (baseValue: number, variance: number) => {
        return Array.from({ length: 60 }, (_, i) => ({
          timestamp: new Date(now.getTime() - (59 - i) * 60000).toISOString(),
          value: Math.max(0, baseValue + (Math.random() - 0.5) * variance)
        }));
      };

      setSystemMetrics({
        cpu: generateMetricData(45, 30),
        memory: generateMetricData(65, 25),
        disk: generateMetricData(75, 15),
        network: generateMetricData(25, 40)
      });

      // 生成模拟的健康检查数据
      const healthData: HealthCheck[] = [
        {
          check_id: 'database_connection',
          name: 'Database Connection',
          status: 'healthy',
          last_check: new Date().toISOString(),
          uptime_percentage: 99.8,
          avg_response_time: 45,
          error_rate: 0.2
        },
        {
          check_id: 'redis_connection',
          name: 'Redis Cache',
          status: 'healthy',
          last_check: new Date().toISOString(),
          uptime_percentage: 99.9,
          avg_response_time: 12,
          error_rate: 0.1
        },
        {
          check_id: 'disk_space',
          name: 'Disk Space',
          status: 'degraded',
          last_check: new Date().toISOString(),
          uptime_percentage: 100,
          avg_response_time: 8,
          error_rate: 0
        },
        {
          check_id: 'cpu_usage',
          name: 'CPU Usage',
          status: 'healthy',
          last_check: new Date().toISOString(),
          uptime_percentage: 98.5,
          avg_response_time: 5,
          error_rate: 1.5
        },
        {
          check_id: 'external_apis',
          name: 'External APIs',
          status: 'unhealthy',
          last_check: new Date().toISOString(),
          uptime_percentage: 85.2,
          avg_response_time: 2500,
          error_rate: 14.8
        }
      ];

      setHealthChecks(healthData);

      // 生成模拟的日志异常数据
      const anomalyData: LogAnomaly[] = [
        {
          anomaly_id: '1',
          anomaly_type: 'error_burst',
          description: 'Error burst detected: 25 errors in 5 minutes',
          detected_at: new Date(Date.now() - 300000).toISOString(),
          severity: 'error',
          resolved: false
        },
        {
          anomaly_id: '2',
          anomaly_type: 'spike',
          description: 'API request spike detected',
          detected_at: new Date(Date.now() - 600000).toISOString(),
          severity: 'warn',
          resolved: true
        },
        {
          anomaly_id: '3',
          anomaly_type: 'silence',
          description: 'Silence detected: 15 minutes without logs',
          detected_at: new Date(Date.now() - 900000).toISOString(),
          severity: 'warn',
          resolved: true
        }
      ];

      setLogAnomalies(anomalyData);

      // 生成模拟的自动化规则数据
      const ruleData: AutomationRule[] = [
        {
          rule_id: 'auto_restart_failed_service',
          name: 'Auto Restart Failed Service',
          enabled: true,
          total_executions: 5,
          success_rate: 80,
          last_executed: new Date(Date.now() - 3600000).toISOString()
        },
        {
          rule_id: 'auto_cleanup_logs',
          name: 'Auto Cleanup Logs',
          enabled: true,
          total_executions: 30,
          success_rate: 100,
          last_executed: new Date(Date.now() - 86400000).toISOString()
        },
        {
          rule_id: 'error_burst_alert',
          name: 'Error Burst Alert',
          enabled: true,
          total_executions: 2,
          success_rate: 100,
          last_executed: new Date(Date.now() - 1800000).toISOString()
        }
      ];

      setAutomationRules(ruleData);

      // 生成模拟的追踪数据
      const traceData: TraceData[] = [
        {
          trace_id: 'trace_001',
          span_count: 8,
          duration_ms: 1250,
          status: 'ok',
          services: ['api', 'database', 'cache']
        },
        {
          trace_id: 'trace_002',
          span_count: 5,
          duration_ms: 890,
          status: 'ok',
          services: ['api', 'ai_service']
        },
        {
          trace_id: 'trace_003',
          span_count: 12,
          duration_ms: 2300,
          status: 'error',
          services: ['api', 'database', 'cache', 'external_api']
        }
      ];

      setTraces(traceData);

      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch monitoring data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMonitoringData();
    const interval = setInterval(fetchMonitoringData, 30000); // 每30秒刷新
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'ok':
        return 'text-green-600';
      case 'degraded':
        return 'text-yellow-600';
      case 'unhealthy':
        return 'text-orange-600';
      case 'critical':
      case 'error':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'ok':
        return <CheckCircle className="h-4 w-4" />;
      case 'degraded':
        return <AlertTriangle className="h-4 w-4" />;
      case 'unhealthy':
        return <AlertCircle className="h-4 w-4" />;
      case 'critical':
      case 'error':
        return <XCircle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const currentCpuUsage = systemMetrics.cpu.length > 0
    ? systemMetrics.cpu[systemMetrics.cpu.length - 1].value
    : 0;

  const currentMemoryUsage = systemMetrics.memory.length > 0
    ? systemMetrics.memory[systemMetrics.memory.length - 1].value
    : 0;

  const currentDiskUsage = systemMetrics.disk.length > 0
    ? systemMetrics.disk[systemMetrics.disk.length - 1].value
    : 0;

  const overallHealth = healthChecks.length > 0
    ? healthChecks.filter(check => check.status === 'healthy').length / healthChecks.length * 100
    : 0;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <RefreshCw className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading monitoring data...</span>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Advanced System Monitoring</h1>
          <p className="text-gray-600">Real-time system health and performance monitoring</p>
        </div>
        <div className="flex items-center space-x-4">
          <Badge variant="outline" className="text-xs">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </Badge>
          <Button onClick={fetchMonitoringData} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overall Health</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overallHealth.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              {healthChecks.filter(c => c.status === 'healthy').length} of {healthChecks.length} services healthy
            </p>
            <Progress value={overallHealth} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{currentCpuUsage.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              {currentCpuUsage > 80 ? 'High usage' : 'Normal usage'}
            </p>
            <Progress value={currentCpuUsage} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Memory Usage</CardTitle>
            <MemoryStick className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{currentMemoryUsage.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">
              {currentMemoryUsage > 85 ? 'High usage' : 'Normal usage'}
            </p>
            <Progress value={currentMemoryUsage} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Issues</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {logAnomalies.filter(a => !a.resolved).length}
            </div>
            <p className="text-xs text-muted-foreground">
              unresolved anomalies
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="health">Health</TabsTrigger>
          <TabsTrigger value="traces">Traces</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="automation">Automation</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>System Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={systemMetrics.cpu}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                    />
                    <YAxis />
                    <Tooltip
                      labelFormatter={(value) => `${value}%`}
                      formatter={(value) => [`${value}%`, 'CPU Usage']}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#8884d8"
                      strokeWidth={2}
                      name="CPU Usage"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Resource Utilization</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={systemMetrics.memory}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                    />
                    <YAxis />
                    <Tooltip
                      labelFormatter={(value) => `${value}%`}
                      formatter={(value) => [`${value}%`, 'Memory Usage']}
                    />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#82ca9d"
                      fill="#82ca9d"
                      fillOpacity={0.6}
                      name="Memory Usage"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Recent Anomalies</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {logAnomalies.slice(0, 5).map((anomaly) => (
                  <div key={anomaly.anomaly_id} className="flex items-center justify-between p-2 border rounded">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(anomaly.severity)}
                      <div>
                        <p className="text-sm font-medium">{anomaly.description}</p>
                        <p className="text-xs text-gray-500">
                          {new Date(anomaly.detected_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {anomaly.resolved ? (
                        <Badge variant="default" className="text-xs">Resolved</Badge>
                      ) : (
                        <Badge variant="destructive" className="text-xs">Active</Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Metrics Tab */}
        <TabsContent value="metrics" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>CPU & Memory Trends</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={systemMetrics.cpu}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                    />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#8884d8"
                      name="CPU %"
                      data={systemMetrics.cpu}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#82ca9d"
                      name="Memory %"
                      data={systemMetrics.memory}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Storage & Network</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={systemMetrics.disk}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={(value) => new Date(value).toLocaleTimeString()}
                    />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#ffc658"
                      name="Disk %"
                      data={systemMetrics.disk}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#ff7c7c"
                      name="Network"
                      data={systemMetrics.network}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Health Tab */}
        <TabsContent value="health" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Component Health Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {healthChecks.map((check) => (
                  <div key={check.check_id} className="flex items-center justify-between p-3 border rounded">
                    <div className="flex items-center space-x-3">
                      <div className={getStatusColor(check.status)}>
                        {getStatusIcon(check.status)}
                      </div>
                      <div>
                        <p className="font-medium">{check.name}</p>
                        <p className="text-sm text-gray-500">
                          Last check: {new Date(check.last_check).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center space-x-2 mb-1">
                        <span className="text-sm font-medium">
                          {check.uptime_percentage.toFixed(1)}%
                        </span>
                        {getStatusIcon(check.status)}
                      </div>
                      <div className="flex items-center space-x-4 text-xs text-gray-500">
                        <span>Response: {check.avg_response_time}ms</span>
                        <span>Error Rate: {check.error_rate}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Traces Tab */}
        <TabsContent value="traces" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Distributed Traces</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {traces.map((trace) => (
                  <div key={trace.trace_id} className="flex items-center justify-between p-3 border rounded">
                    <div className="flex items-center space-x-3">
                      <div className={getStatusColor(trace.status)}>
                        {getStatusIcon(trace.status)}
                      </div>
                      <div>
                        <p className="font-medium">{trace.trace_id}</p>
                        <p className="text-sm text-gray-500">
                          {trace.span_count} spans • {trace.services.join(' → ')}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium">
                        {trace.duration_ms}ms
                      </p>
                      <p className="text-xs text-gray-500">
                        {new Date().toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Logs Tab */}
        <TabsContent value="logs" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Log Anomalies</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {logAnomalies.map((anomaly) => (
                  <Alert key={anomaly.anomaly_id}>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{anomaly.description}</p>
                          <p className="text-sm text-gray-500">
                            Type: {anomaly.anomaly_type} •
                            Detected: {new Date(anomaly.detected_at).toLocaleString()}
                          </p>
                        </div>
                        <Badge
                          variant={anomaly.resolved ? "default" : "destructive"}
                        >
                          {anomaly.resolved ? 'Resolved' : 'Active'}
                        </Badge>
                      </div>
                    </AlertDescription>
                  </Alert>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Automation Tab */}
        <TabsContent value="automation" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Automation Rules</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {automationRules.map((rule) => (
                  <div key={rule.rule_id} className="flex items-center justify-between p-3 border rounded">
                    <div className="flex items-center space-x-3">
                      <Zap className="h-4 w-4 text-blue-500" />
                      <div>
                        <p className="font-medium">{rule.name}</p>
                        <p className="text-sm text-gray-500">
                          {rule.total_executions} executions •
                          {rule.success_rate.toFixed(1)}% success rate
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center space-x-2 mb-1">
                        <span className={`text-xs px-2 py-1 rounded ${
                          rule.enabled
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {rule.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {rule.success_rate}% success
                        </Badge>
                      </div>
                      {rule.last_executed && (
                        <p className="text-xs text-gray-500">
                          Last: {new Date(rule.last_executed).toLocaleString()}
                        </p>
                      )}
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