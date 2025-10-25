"use client";

import React, { useState, useEffect } from 'react';

// 性能指标接口
interface PerformanceMetrics {
  pageLoad: number;
  apiResponse: number;
  renderTime: number;
  userInteraction: number;
  errorRate: number;
  timestamp: number;
}

// 性能数据点接口
interface PerformanceDataPoint {
  timestamp: string;
  cpu: number;
  memory: number;
  disk: number;
  responseTime: number;
  errorRate: number;
}

interface MetricCardProps {
  title: string;
  value: number;
  unit: string;
  trend?: number;
  status?: 'good' | 'warning' | 'critical';
}

// 指标卡片组件
const MetricCard: React.FC<MetricCardProps> = ({ title, value, unit, trend, status = 'good' }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'critical':
        return 'text-red-600 bg-red-50';
      case 'warning':
        return 'text-yellow-600 bg-yellow-50';
      default:
        return 'text-green-600 bg-green-50';
    }
  };

  const getTrendIcon = (trend?: number) => {
    if (trend === undefined) return null;

    if (trend > 0) {
      return <span className="text-red-500 text-xs">↑ {trend.toFixed(1)}%</span>;
    } else if (trend < 0) {
      return <span className="text-green-500 text-xs">↓ {Math.abs(trend).toFixed(1)}%</span>;
    }
    return <span className="text-gray-500 text-xs">—</span>;
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow border border-gray-200">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-500">{title}</h3>
        {getTrendIcon(trend)}
      </div>
      <p className={`text-2xl font-bold mt-2 px-2 py-1 rounded ${getStatusColor(status)}`}>
        {value?.toFixed(1)}{unit}
      </p>
    </div>
  );
};

// 主要性能监控组件
export class PerformanceMonitor {
  private metrics: PerformanceMetrics[] = [];
  private observers: PerformanceObserver[] = [];
  private apiCallTimes: Map<string, number> = new Map();

  constructor() {
    this.initializeMonitoring();
  }

  // 初始化监控
  private initializeMonitoring() {
    if (typeof window === 'undefined') return;

    // 监控页面加载性能
    this.observePageLoad();

    // 监控API调用
    this.observeApiCalls();

    // 监控用户交互
    this.observeUserInteractions();

    // 监控长任务
    this.observeLongTasks();

    // 监控资源加载
    this.observeResourceLoading();
  }

  // 监控页面加载性能
  private observePageLoad() {
    if (typeof window === 'undefined') return;

    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      entries.forEach((entry) => {
        if (entry.entryType === 'navigation') {
          const navEntry = entry as PerformanceNavigationTiming;
          const pageLoadTime = navEntry.loadEventEnd - navEntry.navigationStart;

          this.recordMetric('pageLoad', pageLoadTime);
        }
      });
    });

    observer.observe({ entryTypes: ['navigation'] });
    this.observers.push(observer);
  }

  // 监控API调用
  private observeApiCalls() {
    if (typeof window === 'undefined') return;

    // 拦截fetch请求
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      const startTime = performance.now();
      const url = args[0] as string;

      try {
        const response = await originalFetch(...args);
        const endTime = performance.now();
        const duration = endTime - startTime;

        this.recordMetric('apiResponse', duration, { url, status: response.status });
        return response;
      } catch (error) {
        const endTime = performance.now();
        const duration = endTime - startTime;

        this.recordMetric('apiResponse', duration, { url, status: 'error' });
        throw error;
      }
    };
  }

  // 监控用户交互
  private observeUserInteractions() {
    if (typeof window === 'undefined') return;

    const events = ['click', 'keydown', 'scroll'];
    let lastInteractionTime = 0;

    events.forEach(eventType => {
      document.addEventListener(eventType, (event) => {
        const currentTime = performance.now();

        // 避免过于频繁的记录
        if (currentTime - lastInteractionTime > 100) {
          this.recordMetric('userInteraction', 0, { type: eventType });
          lastInteractionTime = currentTime;
        }
      }, { passive: true });
    });
  }

  // 监控长任务
  private observeLongTasks() {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry) => {
          if (entry.entryType === 'longtask') {
            this.recordMetric('renderTime', entry.duration, { type: 'longtask' });
          }
        });
      });

      try {
        observer.observe({ entryTypes: ['longtask'] });
        this.observers.push(observer);
      } catch (e) {
        console.warn('Long task observation not supported');
      }
    }
  }

  // 监控资源加载
  private observeResourceLoading() {
    if (typeof window === 'undefined') return;

    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      entries.forEach((entry) => {
        if (entry.entryType === 'resource') {
          const resource = entry as PerformanceResourceTiming;
          const loadTime = resource.responseEnd - resource.startTime;

          // 只记录较慢的资源加载
          if (loadTime > 1000) {
            this.recordMetric('resourceLoad', loadTime, {
              type: resource.initiatorType,
              url: resource.name.split('/').pop()
            });
          }
        }
      });
    });

    observer.observe({ entryTypes: ['resource'] });
    this.observers.push(observer);
  }

  // 记录指标
  private recordMetric(type: string, value: number, metadata?: any) {
    const metric: PerformanceMetrics = {
      pageLoad: 0,
      apiResponse: 0,
      renderTime: 0,
      userInteraction: 0,
      errorRate: 0,
      timestamp: Date.now(),
      [type]: value,
      ...metadata
    } as PerformanceMetrics;

    this.metrics.push(metric);

    // 保持最近1000条记录
    if (this.metrics.length > 1000) {
      this.metrics = this.metrics.slice(-1000);
    }

    // 如果是关键性能指标，发送到后端
    if (['pageLoad', 'apiResponse', 'renderTime'].includes(type) && value > 1000) {
      this.sendMetricToBackend(metric);
    }
  }

  // 发送指标到后端
  private async sendMetricToBackend(metric: PerformanceMetrics) {
    try {
      await fetch('/api/v1/monitoring/frontend-metrics', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(metric)
      });
    } catch (error) {
      console.warn('Failed to send performance metric to backend:', error);
    }
  }

  // 监控API调用（手动调用）
  public monitorApiCall(endpoint: string, duration: number) {
    this.recordMetric('apiResponse', duration, { endpoint });
  }

  // 开始监控用户交互（返回结束函数）
  public monitorUserInteraction(action: string) {
    const startTime = performance.now();

    return () => {
      const duration = performance.now() - startTime;
      this.recordMetric('userInteraction', duration, { action });
    };
  }

  // 获取性能报告
  public getPerformanceReport() {
    if (this.metrics.length === 0) {
      return {
        totalMetrics: 0,
        averagePageLoad: 0,
        averageApiResponse: 0,
        averageRenderTime: 0,
        errorRate: 0
      };
    }

    const pageLoadMetrics = this.metrics.filter(m => m.pageLoad > 0);
    const apiResponseMetrics = this.metrics.filter(m => m.apiResponse > 0);
    const renderTimeMetrics = this.metrics.filter(m => m.renderTime > 0);

    const averagePageLoad = pageLoadMetrics.length > 0
      ? pageLoadMetrics.reduce((sum, m) => sum + m.pageLoad, 0) / pageLoadMetrics.length
      : 0;

    const averageApiResponse = apiResponseMetrics.length > 0
      ? apiResponseMetrics.reduce((sum, m) => sum + m.apiResponse, 0) / apiResponseMetrics.length
      : 0;

    const averageRenderTime = renderTimeMetrics.length > 0
      ? renderTimeMetrics.reduce((sum, m) => sum + m.renderTime, 0) / renderTimeMetrics.length
      : 0;

    return {
      totalMetrics: this.metrics.length,
      averagePageLoad: Math.round(averagePageLoad),
      averageApiResponse: Math.round(averageApiResponse),
      averageRenderTime: Math.round(averageRenderTime),
      errorRate: this.calculateErrorRate()
    };
  }

  // 计算错误率
  private calculateErrorRate(): number {
    const recentMetrics = this.metrics.slice(-100); // 最近100条记录
    const errorCount = recentMetrics.filter(m =>
      m.apiResponse > 5000 || m.renderTime > 3000 // 超时阈值
    ).length;

    return (errorCount / recentMetrics.length) * 100;
  }

  // 清理监控
  public cleanup() {
    this.observers.forEach(observer => observer.disconnect());
    this.observers = [];
    this.metrics = [];
  }
}

// React Hook for Performance Monitoring
export function usePerformanceMonitor() {
  const [monitor] = useState(() => new PerformanceMonitor());
  const [report, setReport] = useState(monitor.getPerformanceReport());

  useEffect(() => {
    const interval = setInterval(() => {
      setReport(monitor.getPerformanceReport());
    }, 5000); // 每5秒更新一次

    return () => {
      clearInterval(interval);
      monitor.cleanup();
    };
  }, [monitor]);

  return {
    monitor,
    report,
    monitorApiCall: monitor.monitorApiCall.bind(monitor),
    monitorUserInteraction: monitor.monitorUserInteraction.bind(monitor)
  };
}

// 性能监控仪表板组件
export const PerformanceDashboard: React.FC = () => {
  const [data, setData] = useState<PerformanceDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('1h');

  useEffect(() => {
    const fetchMonitoringData = async () => {
      try {
        const response = await fetch(`/api/v1/monitoring/metrics?range=${timeRange}`);
        if (response.ok) {
          const result = await response.json();
          setData(result.data || []);
        }
      } catch (error) {
        console.error('Failed to fetch monitoring data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchMonitoringData();
    const interval = setInterval(fetchMonitoringData, 30000); // 30秒更新

    return () => clearInterval(interval);
  }, [timeRange]);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">加载监控数据中...</p>
        </div>
      </div>
    );
  }

  const latestData = data[data.length - 1];

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">系统监控</h1>
        <div className="flex items-center space-x-4">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="5m">最近5分钟</option>
            <option value="1h">最近1小时</option>
            <option value="6h">最近6小时</option>
            <option value="24h">最近24小时</option>
          </select>
        </div>
      </div>

      {/* 系统资源监控 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="CPU使用率"
          value={latestData?.cpu || 0}
          unit="%"
          status={latestData?.cpu > 80 ? (latestData.cpu > 90 ? 'critical' : 'warning') : 'good'}
        />
        <MetricCard
          title="内存使用率"
          value={latestData?.memory || 0}
          unit="%"
          status={latestData?.memory > 85 ? (latestData.memory > 95 ? 'critical' : 'warning') : 'good'}
        />
        <MetricCard
          title="磁盘使用率"
          value={latestData?.disk || 0}
          unit="%"
          status={latestData?.disk > 90 ? 'critical' : (latestData.disk > 80 ? 'warning' : 'good')}
        />
        <MetricCard
          title="响应时间"
          value={latestData?.responseTime || 0}
          unit="ms"
          status={latestData?.responseTime > 2000 ? (latestData.responseTime > 5000 ? 'critical' : 'warning') : 'good'}
        />
      </div>

      {/* 性能趋势图占位符 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <h3 className="text-lg font-semibold mb-4 text-gray-900">系统资源趋势</h3>
          <div className="h-64 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <p>性能趋势图表</p>
              <p className="text-sm">需要集成图表库（如Chart.js或Recharts）</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <h3 className="text-lg font-semibold mb-4 text-gray-900">API响应时间</h3>
          <div className="h-64 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <p>API性能图表</p>
              <p className="text-sm">显示各端点响应时间分布</p>
            </div>
          </div>
        </div>
      </div>

      {/* 系统状态摘要 */}
      <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">系统状态摘要</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <div className="text-2xl font-bold text-green-600">
              {data.filter(d => d.responseTime < 1000).length}
            </div>
            <div className="text-sm text-green-800">正常响应</div>
          </div>
          <div className="text-center p-4 bg-yellow-50 rounded-lg">
            <div className="text-2xl font-bold text-yellow-600">
              {data.filter(d => d.responseTime >= 1000 && d.responseTime < 5000).length}
            </div>
            <div className="text-sm text-yellow-800">缓慢响应</div>
          </div>
          <div className="text-center p-4 bg-red-50 rounded-lg">
            <div className="text-2xl font-bold text-red-600">
              {data.filter(d => d.responseTime >= 5000).length}
            </div>
            <div className="text-sm text-red-800">超时响应</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PerformanceMonitor;