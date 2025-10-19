/**
 * 高级数据分析仪表板组件
 * Week 5 Day 3: 智能数据分析平台 - 数据可视化
 */

"use client";

import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
  ResponsiveContainer,
  FunnelChart,
  Funnel,
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  Users,
  Activity,
  Eye,
  MousePointer,
  AlertCircle,
  BarChart3,
  LineChart as LineChartIcon,
  PieChart as PieChartIcon,
  Filter,
  Calendar,
  RefreshCw,
  Download,
} from 'lucide-react';

// 类型定义
interface AnalyticsData {
  period_days: number;
  summary: {
    total_events: number;
    total_sessions: number;
    total_page_views: number;
    total_api_calls: number;
    total_errors: number;
    avg_session_duration: number;
    conversion_rate: number;
  };
  behavior_stats: {
    total_events: number;
    unique_users: number;
    unique_sessions: number;
    event_types: Record<string, number>;
    action_types: Record<string, number>;
    top_pages: Record<string, number>;
    error_rate: number;
  };
  top_pages: Array<{ page: string; views: number }>;
  event_types: Array<{ type: string; count: number; percentage: number }>;
  daily_activity: Array<{ date: string; events: number }>;
}

interface RealtimeStats {
  realtime_stats: {
    total_events: number;
    unique_users: number;
    unique_sessions: number;
    event_types: Record<string, number>;
    error_rate: number;
  };
  active_sessions: number;
  user_recent_activity: Array<{
    event_type: string;
    timestamp: string;
    properties: Record<string, any>;
  }>;
  system_health: {
    status: string;
    last_updated: string;
  };
}

interface FunnelData {
  funnel_name: string;
  steps: Array<{
    step: string;
    step_order: number;
    users: number;
    conversion_rate: number;
    dropoff_rate: number;
  }>;
  total_users: number;
  conversion_rates: number[];
  dropoff_rates: number[];
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export default function AnalyticsDashboard() {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [realtimeStats, setRealtimeStats] = useState<RealtimeStats | null>(null);
  const [funnelData, setFunnelData] = useState<FunnelData | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [timeRange, setTimeRange] = useState('30');
  const [refreshInterval, setRefreshInterval] = useState(30000); // 30秒

  // 获取分析数据
  const fetchAnalyticsData = async () => {
    try {
      const response = await fetch(`/api/v1/analytics/dashboard/overview?days=${timeRange}`);
      if (response.ok) {
        const data = await response.json();
        setAnalyticsData(data);
      }
    } catch (error) {
      console.error('获取分析数据失败:', error);
    }
  };

  // 获取实时统计
  const fetchRealtimeStats = async () => {
    try {
      const response = await fetch('/api/v1/analytics/realtime/stats');
      if (response.ok) {
        const data = await response.json();
        setRealtimeStats(data);
      }
    } catch (error) {
      console.error('获取实时统计失败:', error);
    }
  };

  // 获取漏斗数据
  const fetchFunnelData = async () => {
    try {
      const response = await fetch('/api/v1/analytics/funnel/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          funnel_name: '用户注册流程',
          steps: ['访问首页', '查看产品', '开始注册', '完成注册'],
          start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
          end_date: new Date().toISOString(),
        }),
      });
      if (response.ok) {
        const data = await response.json();
        setFunnelData(data);
      }
    } catch (error) {
      console.error('获取漏斗数据失败:', error);
    }
  };

  // 初始化数据
  useEffect(() => {
    const loadInitialData = async () => {
      setLoading(true);
      await Promise.all([
        fetchAnalyticsData(),
        fetchRealtimeStats(),
        fetchFunnelData(),
      ]);
      setLoading(false);
    };

    loadInitialData();
  }, [timeRange]);

  // 设置定时刷新
  useEffect(() => {
    const interval = setInterval(() => {
      fetchRealtimeStats();
      if (activeTab === 'overview') {
        fetchAnalyticsData();
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval, activeTab, timeRange]);

  // 手动刷新
  const handleRefresh = async () => {
    await fetchAnalyticsData();
    await fetchRealtimeStats();
    await fetchFunnelData();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <RefreshCw className="animate-spin h-8 w-8 mx-auto mb-4 text-blue-600" />
          <p className="text-gray-600">加载分析数据...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">数据分析仪表板</h1>
          <p className="text-gray-600 mt-1">实时监控用户行为和系统性能</p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Label htmlFor="time-range">时间范围:</Label>
            <Select value={timeRange} onValueChange={setTimeRange}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">最近7天</SelectItem>
                <SelectItem value="30">最近30天</SelectItem>
                <SelectItem value="90">最近90天</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button variant="outline" onClick={handleRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* 概览卡片 */}
      {analyticsData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">总事件数</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {analyticsData.summary.total_events.toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground">
                过去{timeRange}天
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">活跃会话</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {analyticsData.summary.total_sessions.toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground">
                平均时长: {Math.round(analyticsData.summary.avg_session_duration)}秒
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">页面浏览量</CardTitle>
              <Eye className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {analyticsData.summary.total_page_views.toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground">
                API调用: {analyticsData.summary.total_api_calls.toLocaleString()}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">转化率</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {analyticsData.summary.conversion_rate}%
              </div>
              <p className="text-xs text-muted-foreground">
                错误率: {analyticsData.behavior_stats.error_rate.toFixed(2)}%
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 主要内容标签页 */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">概览</TabsTrigger>
          <TabsTrigger value="events">事件分析</TabsTrigger>
          <TabsTrigger value="funnel">转化漏斗</TabsTrigger>
          <TabsTrigger value="realtime">实时监控</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* 每日活动趋势 */}
          {analyticsData && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <LineChartIcon className="h-5 w-5" />
                  <span>每日活动趋势</span>
                </CardTitle>
                <CardDescription>
                  过去{timeRange}天的用户活动统计
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={analyticsData.daily_activity}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Area
                      type="monotone"
                      dataKey="events"
                      stroke="#8884d8"
                      fill="#8884d8"
                      fillOpacity={0.3}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          {/* 事件类型分布 */}
          {analyticsData && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <PieChartIcon className="h-5 w-5" />
                    <span>事件类型分布</span>
                  </CardTitle>
                  <CardDescription>
                    各类事件的数量分布
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={analyticsData.event_types}
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="count"
                        label={({ type, percentage }) => `${type}: ${percentage}%`}
                      >
                        {analyticsData.event_types.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <BarChart3 className="h-5 w-5" />
                    <span>热门页面</span>
                  </CardTitle>
                  <CardDescription>
                    访问量最高的页面
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={analyticsData.top_pages.slice(0, 5)}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="page" angle={-45} textAnchor="end" height={60} />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="views" fill="#82ca9d" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="events" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>事件详情分析</CardTitle>
              <CardDescription>
                深入分析用户行为事件
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <MousePointer className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">事件分析功能</h3>
                <p className="text-gray-600 mb-4">详细的事件分析功能正在开发中</p>
                <Badge variant="outline">即将推出</Badge>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="funnel" className="space-y-6">
          {funnelData && (
            <Card>
              <CardHeader>
                <CardTitle>用户转化漏斗</CardTitle>
                <CardDescription>
                  {funnelData.funnel_name} - 总用户数: {funnelData.total_users}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <FunnelChart>
                    <Funnel
                      data={funnelData.steps.map(step => ({
                        name: step.step,
                        value: step.users,
                        fill: COLORS[step.step_order - 1] || '#8884d8'
                      }))}
                      label={({ name, value }) => `${name}: ${value}`}
                    >
                      <Tooltip />
                    </Funnel>
                  </FunnelChart>
                </ResponsiveContainer>

                {/* 转化率统计 */}
                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                  {funnelData.steps.map((step, index) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: COLORS[index] }}
                        />
                        <span className="font-medium">{step.step}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium">{step.users.toLocaleString()} 用户</div>
                        <div className="text-xs text-gray-500">
                          转化率: {step.conversion_rate}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="realtime" className="space-y-6">
          {/* 实时统计卡片 */}
          {realtimeStats && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">实时事件</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {realtimeStats.realtime_stats.total_events}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    最近5分钟
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">活跃用户</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {realtimeStats.realtime_stats.unique_users}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    当前在线
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">活跃会话</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {realtimeStats.active_sessions}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    最近30分钟
                  </p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* 最近活动 */}
          {realtimeStats && (
            <Card>
              <CardHeader>
                <CardTitle>最近用户活动</CardTitle>
                <CardDescription>
                  实时显示用户最近的行为事件
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {realtimeStats.user_recent_activity.slice(0, 10).map((activity, index) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="font-medium">{activity.event_type}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm text-gray-500">
                          {new Date(activity.timestamp).toLocaleTimeString()}
                        </div>
                        {activity.properties && (
                          <div className="text-xs text-gray-400">
                            {Object.keys(activity.properties).join(', ')}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}