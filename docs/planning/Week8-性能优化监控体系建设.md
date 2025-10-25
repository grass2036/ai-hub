# Week 8 - 性能优化与监控体系建设

## 开���目标
建立完整的性能监控体系，实现系统性能优化，确保AI Hub平台在高并发场景下的稳定性和响应速度。

## Day 1 - 性能监控基础设施

### 上午任务：监控数据采集系统

#### 1. 应用性能监控 (APM)
```typescript
// frontend/src/monitoring/PerformanceMonitor.tsx
interface PerformanceMetrics {
  pageLoad: number;
  apiResponse: number;
  renderTime: number;
  userInteraction: number;
  errorRate: number;
}

export class PerformanceMonitor {
  private metrics: PerformanceMetrics[] = [];

  // 页面性能监控
  monitorPageLoad(): void {
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    const pageLoad = navigation.loadEventEnd - navigation.navigationStart;

    this.recordMetric('pageLoad', pageLoad);
  }

  // API性能监控
  monitorApiCall(endpoint: string, duration: number): void {
    this.recordMetric('apiResponse', duration, { endpoint });
  }

  // 用户交互监控
  monitorUserInteraction(action: string): void {
    const startTime = performance.now();

    return () => {
      const duration = performance.now() - startTime;
      this.recordMetric('userInteraction', duration, { action });
    };
  }
}
```

#### 2. 系统指标监控
```python
# backend/monitoring/system_monitor.py
import psutil
import asyncio
from typing import Dict, List
from datetime import datetime

class SystemMonitor:
    def __init__(self):
        self.metrics_history = []
        self.alerts = []

    async def collect_system_metrics(self) -> Dict:
        """收集系统性能指标"""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'cpu': {
                'usage_percent': psutil.cpu_percent(interval=1),
                'count': psutil.cpu_count(),
                'load_avg': psutil.getloadavg()
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent,
                'used': psutil.virtual_memory().used
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent
            },
            'network': self._get_network_stats()
        }

    def _get_network_stats(self) -> Dict:
        """获取网络统计信息"""
        net_io = psutil.net_io_counters()
        return {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv
        }
```

#### 3. 业务指标监控
```python
# backend/monitoring/business_monitor.py
from dataclasses import dataclass
from typing import Dict, Any
import json

@dataclass
class BusinessMetric:
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = None

class BusinessMonitor:
    def __init__(self):
        self.metrics = []

    def track_api_usage(self, endpoint: str, user_id: str, response_time: float):
        """追踪API使用情况"""
        metric = BusinessMetric(
            name='api_usage',
            value=response_time,
            unit='ms',
            timestamp=datetime.utcnow(),
            tags={
                'endpoint': endpoint,
                'user_id': user_id,
                'status': 'success'
            }
        )
        self.metrics.append(metric)

    def track_ai_model_usage(self, model: str, tokens: int, cost: float):
        """追踪AI模型使用情况"""
        metric = BusinessMetric(
            name='ai_model_usage',
            value=cost,
            unit='USD',
            timestamp=datetime.utcnow(),
            tags={
                'model': model,
                'tokens': str(tokens)
            }
        )
        self.metrics.append(metric)

    def track_user_session(self, user_id: str, session_duration: float):
        """追踪用户会话"""
        metric = BusinessMetric(
            name='user_session_duration',
            value=session_duration,
            unit='seconds',
            timestamp=datetime.utcnow(),
            tags={'user_id': user_id}
        )
        self.metrics.append(metric)
```

### 下午任务：监控数据存储

#### 1. 时序数据库配置
```yaml
# deployment/monitoring/timescale-db.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: timescaledb
spec:
  replicas: 1
  selector:
    matchLabels:
      app: timescaledb
  template:
    metadata:
      labels:
        app: timescaledb
    spec:
      containers:
      - name: timescaledb
        image: timescale/timescaledb:latest-pg14
        env:
        - name: POSTGRES_DB
          value: "monitoring"
        - name: POSTGRES_USER
          value: "monitoring_user"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: timescaledb-password
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: timescaledb-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
      volumes:
      - name: timescaledb-storage
        persistentVolumeClaim:
          claimName: timescaledb-pvc
```

#### 2. 监控数据模型
```sql
-- migrations/005_monitoring_schema.sql

-- 性能指标表
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(20),
    tags JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 创建时序表
SELECT create_hypertable('performance_metrics', 'timestamp', chunk_time_interval => INTERVAL '1 hour');

-- 业务指标表
CREATE TABLE business_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(20),
    user_id UUID,
    organization_id UUID,
    tags JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('business_metrics', 'timestamp', chunk_time_interval => INTERVAL '1 hour');

-- 系统指标表
CREATE TABLE system_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    host_name VARCHAR(255) NOT NULL,
    cpu_usage DOUBLE PRECISION,
    memory_usage DOUBLE PRECISION,
    disk_usage DOUBLE PRECISION,
    network_io JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('system_metrics', 'timestamp', chunk_time_interval => INTERVAL '5 minutes');

-- 告警规则表
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    condition_operator VARCHAR(10) NOT NULL, -- '>', '<', '>=', '<=', '=', '!='
    threshold_value DOUBLE PRECISION NOT NULL,
    duration_minutes INTEGER DEFAULT 5,
    severity VARCHAR(20) NOT NULL, -- 'critical', 'warning', 'info'
    enabled BOOLEAN DEFAULT true,
    notification_channels JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 告警记录表
CREATE TABLE alert_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES alert_rules(id),
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- 'active', 'resolved', 'suppressed'
    trigger_value DOUBLE PRECISION NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 索引优化
CREATE INDEX idx_performance_metrics_name_timestamp ON performance_metrics(metric_name, timestamp DESC);
CREATE INDEX idx_business_metrics_user_timestamp ON business_metrics(user_id, timestamp DESC);
CREATE INDEX idx_business_metrics_org_timestamp ON business_metrics(organization_id, timestamp DESC);
CREATE INDEX idx_system_metrics_host_timestamp ON system_metrics(host_name, timestamp DESC);
CREATE INDEX idx_alert_incidents_rule_status ON alert_incidents(rule_id, status);
```

### 晚上任务：实时监控仪表板

#### 1. 监控仪表板组件
```typescript
// frontend/src/components/monitoring/MonitoringDashboard.tsx
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface MonitoringData {
  timestamp: string;
  cpu: number;
  memory: number;
  disk: number;
  responseTime: number;
  errorRate: number;
}

export const MonitoringDashboard: React.FC = () => {
  const [data, setData] = useState<MonitoringData[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('1h');

  useEffect(() => {
    const fetchMonitoringData = async () => {
      try {
        const response = await fetch(`/api/v1/monitoring/metrics?range=${timeRange}`);
        const result = await response.json();
        setData(result.data);
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
    return <div className="p-6">加载监控数据中...</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">系统监控</h1>
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          className="border rounded px-3 py-1"
        >
          <option value="5m">最近5分钟</option>
          <option value="1h">最近1小时</option>
          <option value="6h">最近6小时</option>
          <option value="24h">最近24小时</option>
        </select>
      </div>

      {/* 系统资源监控 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard title="CPU使用率" value={data[data.length - 1]?.cpu} unit="%" />
        <MetricCard title="内存使用率" value={data[data.length - 1]?.memory} unit="%" />
        <MetricCard title="磁盘使用率" value={data[data.length - 1]?.disk} unit="%" />
        <MetricCard title="响应时间" value={data[data.length - 1]?.responseTime} unit="ms" />
      </div>

      {/* 性能趋势图 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">系统资源趋势</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="cpu" stroke="#8884d8" name="CPU" />
              <Line type="monotone" dataKey="memory" stroke="#82ca9d" name="内存" />
              <Line type="monotone" dataKey="disk" stroke="#ffc658" name="磁盘" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">响应时间趋势</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="responseTime" stroke="#ff7300" name="响应时间" />
              <Line type="monotone" dataKey="errorRate" stroke="#ff0000" name="错误率" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

const MetricCard: React.FC<{ title: string; value: number; unit: string }> = ({ title, value, unit }) => {
  const getColor = (value: number) => {
    if (value < 50) return 'text-green-600';
    if (value < 80) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h3 className="text-sm font-medium text-gray-500">{title}</h3>
      <p className={`text-2xl font-bold ${getColor(value)}`}>
        {value?.toFixed(1)}{unit}
      </p>
    </div>
  );
};
```

## Day 2 - 智能告警系统

### 上午任务：告警规则引擎

#### 1. 告警规则配置
```python
# backend/monitoring/alert_engine.py
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio

@dataclass
class AlertCondition:
    metric_name: str
    operator: str  # '>', '<', '>=', '<=', '=', '!='
    threshold: float
    duration_minutes: int = 5
    severity: str = 'warning'  # 'critical', 'warning', 'info'

class AlertEngine:
    def __init__(self):
        self.rules: Dict[str, AlertCondition] = {}
        self.active_alerts: Dict[str, datetime] = {}

    def add_rule(self, rule_id: str, condition: AlertCondition):
        """添加告警规则"""
        self.rules[rule_id] = condition

    def remove_rule(self, rule_id: str):
        """移除告警规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
        if rule_id in self.active_alerts:
            del self.active_alerts[rule_id]

    async def evaluate_metric(self, metric_name: str, value: float, timestamp: datetime):
        """评估指标是否触发告警"""
        for rule_id, condition in self.rules.items():
            if condition.metric_name != metric_name:
                continue

            if self._evaluate_condition(value, condition):
                await self._handle_alert_trigger(rule_id, condition, value, timestamp)
            else:
                await self._handle_alert_resolve(rule_id, condition, timestamp)

    def _evaluate_condition(self, value: float, condition: AlertCondition) -> bool:
        """评估条件是否满足"""
        operators = {
            '>': lambda a, b: a > b,
            '<': lambda a, b: a < b,
            '>=': lambda a, b: a >= b,
            '<=': lambda a, b: a <= b,
            '=': lambda a, b: a == b,
            '!=': lambda a, b: a != b,
        }

        return operators.get(condition.operator, lambda a, b: False)(value, condition.threshold)

    async def _handle_alert_trigger(self, rule_id: str, condition: AlertCondition,
                                  value: float, timestamp: datetime):
        """处理告警触发"""
        if rule_id not in self.active_alerts:
            self.active_alerts[rule_id] = timestamp
            return

        # 检查持续时间
        duration = timestamp - self.active_alerts[rule_id]
        if duration >= timedelta(minutes=condition.duration_minutes):
            await self._send_alert(rule_id, condition, value, timestamp)

    async def _handle_alert_resolve(self, rule_id: str, condition: AlertCondition, timestamp: datetime):
        """处理告警解决"""
        if rule_id in self.active_alerts:
            del self.active_alerts[rule_id]
            await self._send_resolution(rule_id, condition, timestamp)

    async def _send_alert(self, rule_id: str, condition: AlertCondition,
                         value: float, timestamp: datetime):
        """发送告警通知"""
        alert_data = {
            'rule_id': rule_id,
            'metric_name': condition.metric_name,
            'severity': condition.severity,
            'value': value,
            'threshold': condition.threshold,
            'timestamp': timestamp.isoformat(),
            'message': f"{condition.metric_name} {condition.operator} {condition.threshold} (当前值: {value})"
        }

        # 发送到不同的通知渠道
        await asyncio.gather(
            self._send_email_alert(alert_data),
            self._send_slack_alert(alert_data),
            self._send_webhook_alert(alert_data)
        )

    async def _send_email_alert(self, alert_data: Dict):
        """发送邮件告警"""
        # 实现邮件发送逻辑
        pass

    async def _send_slack_alert(self, alert_data: Dict):
        """发送Slack告警"""
        # 实现Slack通知逻辑
        pass

    async def _send_webhook_alert(self, alert_data: Dict):
        """发送Webhook告警"""
        # 实现Webhook通知逻辑
        pass
```

#### 2. 预定义告警规则
```python
# backend/monitoring/default_alert_rules.py

DEFAULT_ALERT_RULES = {
    'high_cpu_usage': AlertCondition(
        metric_name='cpu_usage',
        operator='>',
        threshold=80.0,
        duration_minutes=5,
        severity='warning'
    ),

    'critical_cpu_usage': AlertCondition(
        metric_name='cpu_usage',
        operator='>',
        threshold=95.0,
        duration_minutes=2,
        severity='critical'
    ),

    'high_memory_usage': AlertCondition(
        metric_name='memory_usage',
        operator='>',
        threshold=85.0,
        duration_minutes=5,
        severity='warning'
    ),

    'critical_memory_usage': AlertCondition(
        metric_name='memory_usage',
        operator='>',
        threshold=95.0,
        duration_minutes=2,
        severity='critical'
    ),

    'high_response_time': AlertCondition(
        metric_name='api_response_time',
        operator='>',
        threshold=2000.0,  # 2秒
        duration_minutes=3,
        severity='warning'
    ),

    'critical_response_time': AlertCondition(
        metric_name='api_response_time',
        operator='>',
        threshold=5000.0,  # 5秒
        duration_minutes=1,
        severity='critical'
    ),

    'high_error_rate': AlertCondition(
        metric_name='error_rate',
        operator='>',
        threshold=5.0,  # 5%
        duration_minutes=2,
        severity='warning'
    ),

    'critical_error_rate': AlertCondition(
        metric_name='error_rate',
        operator='>',
        threshold=10.0,  # 10%
        duration_minutes=1,
        severity='critical'
    ),

    'disk_space_low': AlertCondition(
        metric_name='disk_usage',
        operator='>',
        threshold=90.0,
        duration_minutes=5,
        severity='warning'
    ),

    'disk_space_critical': AlertCondition(
        metric_name='disk_usage',
        operator='>',
        threshold=95.0,
        duration_minutes=1,
        severity='critical'
    )
}
```

### 下午任务：机器学习异常检测

#### 1. 异常检测模型
```python
# backend/monitoring/anomaly_detection.py
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Tuple
import joblib
from datetime import datetime, timedelta

class AnomalyDetector:
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.training_data = {}

    def train_model(self, metric_name: str, historical_data: List[Dict]):
        """训练异常检测模型"""
        if len(historical_data) < 100:  # 至少需要100个数据点
            return False

        # 提取特征
        features = self._extract_features(historical_data)

        # 标准化
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)

        # 训练模型
        model = IsolationForest(
            contamination=0.1,  # 10%的异常率
            random_state=42,
            n_estimators=100
        )
        model.fit(scaled_features)

        # 保存模型和标准化器
        self.models[metric_name] = model
        self.scalers[metric_name] = scaler
        self.training_data[metric_name] = historical_data[-1000:]  # 保留最近1000个数据点

        return True

    def detect_anomaly(self, metric_name: str, current_data: Dict) -> Tuple[bool, float]:
        """检测异常"""
        if metric_name not in self.models:
            return False, 0.0

        model = self.models[metric_name]
        scaler = self.scalers[metric_name]

        # 提取当前特征
        features = self._extract_features([current_data])
        scaled_features = scaler.transform(features)

        # 预测异常分数 (-1表示异常，1表示正常)
        anomaly_score = model.decision_function(scaled_features)[0]
        is_anomaly = model.predict(scaled_features)[0] == -1

        return is_anomaly, anomaly_score

    def _extract_features(self, data: List[Dict]) -> np.ndarray:
        """提取特征"""
        features = []

        for i, point in enumerate(data):
            # 基础指标
            basic_features = [
                point.get('value', 0),
                point.get('rate_of_change', 0),
                point.get('moving_avg_5', 0),
                point.get('moving_avg_15', 0),
                point.get('volatility', 0),
                point.get('hour_of_day', datetime.fromisoformat(point['timestamp']).hour),
                point.get('day_of_week', datetime.fromisoformat(point['timestamp']).weekday())
            ]

            # 添加历史特征
            if i > 0:
                prev_point = data[i-1]
                basic_features.extend([
                    point.get('value', 0) - prev_point.get('value', 0),  # 一阶差分
                    (point.get('value', 0) / max(prev_point.get('value', 1), 1)) - 1,  # 变化率
                ])
            else:
                basic_features.extend([0, 0])

            features.append(basic_features)

        return np.array(features)

    def save_models(self, file_path: str):
        """保存模型"""
        joblib.dump({
            'models': self.models,
            'scalers': self.scalers,
            'training_data': self.training_data
        }, file_path)

    def load_models(self, file_path: str):
        """加载模型"""
        data = joblib.load(file_path)
        self.models = data.get('models', {})
        self.scalers = data.get('scalers', {})
        self.training_data = data.get('training_data', {})
```

#### 2. 智能告警策略
```python
# backend/monitoring/smart_alerting.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import statistics

class SmartAlerting:
    def __init__(self, anomaly_detector: AnomalyDetector):
        self.anomaly_detector = anomaly_detector
        self.alert_history = {}
        self.suppression_rules = {}

    def evaluate_smart_alert(self, metric_name: str, current_value: float,
                           timestamp: datetime) -> Optional[Dict]:
        """智能告警评估"""
        # 检查抑制规则
        if self._is_suppressed(metric_name, timestamp):
            return None

        # 获取历史数据
        historical_data = self._get_historical_data(metric_name, lookback_hours=24)

        if len(historical_data) < 10:
            return None

        # 计算统计特征
        stats = self._calculate_statistics(historical_data)

        # 检测异常
        current_data = {
            'timestamp': timestamp.isoformat(),
            'value': current_value,
            'rate_of_change': self._calculate_rate_of_change(historical_data, current_value),
            'moving_avg_5': statistics.mean([p['value'] for p in historical_data[-5:]]),
            'moving_avg_15': statistics.mean([p['value'] for p in historical_data[-15:]]),
            'volatility': statistics.stdev([p['value'] for p in historical_data[-10:]]),
            'hour_of_day': timestamp.hour,
            'day_of_week': timestamp.weekday()
        }

        is_anomaly, anomaly_score = self.anomaly_detector.detect_anomaly(metric_name, current_data)

        if is_anomaly:
            alert = {
                'metric_name': metric_name,
                'current_value': current_value,
                'anomaly_score': anomaly_score,
                'severity': self._calculate_severity(current_value, stats),
                'timestamp': timestamp.isoformat(),
                'context': {
                    'historical_avg': stats['mean'],
                    'historical_std': stats['std'],
                    'percentile': self._calculate_percentile(current_value, historical_data)
                }
            }

            # 记录告警历史
            self._record_alert(metric_name, alert)

            return alert

        return None

    def _calculate_statistics(self, data: List[Dict]) -> Dict:
        """计算统计特征"""
        values = [point['value'] for point in data]
        return {
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'std': statistics.stdev(values) if len(values) > 1 else 0,
            'min': min(values),
            'max': max(values),
            'p95': np.percentile(values, 95),
            'p99': np.percentile(values, 99)
        }

    def _calculate_severity(self, current_value: float, stats: Dict) -> str:
        """计算告警严重程度"""
        # 基于统计分布计算严重程度
        if current_value > stats.get('p99', 0):
            return 'critical'
        elif current_value > stats.get('p95', 0):
            return 'warning'
        else:
            return 'info'

    def _calculate_percentile(self, value: float, data: List[Dict]) -> float:
        """计算当前值在历史数据中的百分位"""
        values = sorted([point['value'] for point in data])
        for i, v in enumerate(values):
            if v >= value:
                return (i / len(values)) * 100
        return 100.0

    def _is_suppressed(self, metric_name: str, timestamp: datetime) -> bool:
        """检查是否被抑制"""
        if metric_name not in self.suppression_rules:
            return False

        rule = self.suppression_rules[metric_name]

        # 检查时间窗口内是否有重复告警
        recent_alerts = self.alert_history.get(metric_name, [])
        for alert in recent_alerts:
            alert_time = datetime.fromisoformat(alert['timestamp'])
            if timestamp - alert_time < timedelta(minutes=rule.get('suppression_minutes', 30)):
                return True

        return False
```

### 晚上任务：告警通知系统

#### 1. 多渠道通知
```python
# backend/monitoring/notifications.py
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List
import json

class NotificationManager:
    def __init__(self, config: Dict):
        self.email_config = config.get('email', {})
        self.slack_config = config.get('slack', {})
        self.webhook_config = config.get('webhooks', {})
        self.sms_config = config.get('sms', {})

    async def send_alert(self, alert_data: Dict, channels: List[str]):
        """发送告警到多个渠道"""
        tasks = []

        if 'email' in channels:
            tasks.append(self._send_email(alert_data))

        if 'slack' in channels:
            tasks.append(self._send_slack(alert_data))

        if 'webhook' in channels:
            tasks.append(self._send_webhook(alert_data))

        if 'sms' in channels and alert_data.get('severity') == 'critical':
            tasks.append(self._send_sms(alert_data))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_email(self, alert_data: Dict):
        """发送邮件通知"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['sender']
            msg['To'] = ', '.join(self.email_config['recipients'])
            msg['Subject'] = f"[{alert_data['severity'].upper()}] AI Hub 告警: {alert_data['metric_name']}"

            body = self._generate_email_body(alert_data)
            msg.attach(MIMEText(body, 'html'))

            server = smtplib.SMTP(self.email_config['smtp_host'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            server.send_message(msg)
            server.quit()

        except Exception as e:
            print(f"Failed to send email alert: {e}")

    async def _send_slack(self, alert_data: Dict):
        """发送Slack通知"""
        try:
            webhook_url = self.slack_config['webhook_url']

            payload = {
                "text": f"🚨 {alert_data['severity'].upper()} Alert",
                "attachments": [
                    {
                        "color": self._get_color_by_severity(alert_data['severity']),
                        "fields": [
                            {"title": "Metric", "value": alert_data['metric_name'], "short": True},
                            {"title": "Current Value", "value": str(alert_data['current_value']), "short": True},
                            {"title": "Severity", "value": alert_data['severity'], "short": True},
                            {"title": "Time", "value": alert_data['timestamp'], "short": True}
                        ],
                        "footer": "AI Hub Monitoring",
                        "ts": int(datetime.fromisoformat(alert_data['timestamp']).timestamp())
                    }
                ]
            }

            requests.post(webhook_url, json=payload, timeout=10)

        except Exception as e:
            print(f"Failed to send Slack alert: {e}")

    async def _send_webhook(self, alert_data: Dict):
        """发送Webhook通知"""
        try:
            for webhook in self.webhook_config.get('urls', []):
                payload = {
                    'alert': alert_data,
                    'timestamp': datetime.utcnow().isoformat(),
                    'service': 'ai-hub-monitoring'
                }

                requests.post(webhook['url'], json=payload,
                            headers=webhook.get('headers', {}),
                            timeout=10)

        except Exception as e:
            print(f"Failed to send webhook alert: {e}")

    async def _send_sms(self, alert_data: Dict):
        """发送短信通知（仅关键告警）"""
        try:
            # 集成短信服务提供商API
            message = f"[CRITICAL] AI Hub: {alert_data['metric_name']} = {alert_data['current_value']}"

            for phone in self.sms_config.get('phone_numbers', []):
                # 调用短信API
                pass

        except Exception as e:
            print(f"Failed to send SMS alert: {e}")

    def _generate_email_body(self, alert_data: Dict) -> str:
        """生成邮件内容"""
        severity_colors = {
            'critical': '#ff4444',
            'warning': '#ffaa00',
            'info': '#00aaff'
        }

        color = severity_colors.get(alert_data['severity'], '#666666')

        return f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: {color}; color: white; padding: 20px; text-align: center;">
                    <h1>AI Hub 系统告警</h1>
                    <p>严重程度: {alert_data['severity'].upper()}</p>
                </div>

                <div style="padding: 20px; background-color: #f9f9f9;">
                    <h2>告警详情</h2>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;"><strong>指标名称</strong></td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{alert_data['metric_name']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;"><strong>当前值</strong></td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{alert_data['current_value']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border: 1px solid #ddd;"><strong>告警时间</strong></td>
                            <td style="padding: 8px; border: 1px solid #ddd;">{alert_data['timestamp']}</td>
                        </tr>
                    </table>

                    <div style="margin-top: 20px; padding: 15px; background-color: #e8f4f8; border-left: 4px solid {color};">
                        <p><strong>建议操作:</strong></p>
                        <ul>
                            <li>登录监控面板查看详细情况</li>
                            <li>检查相关服务状态</li>
                            <li>如需帮助，请联系技术支持团队</li>
                        </ul>
                    </div>
                </div>

                <div style="background-color: #333; color: white; padding: 10px; text-align: center; font-size: 12px;">
                    <p>此邮件由 AI Hub 监控系统自动发送，请勿回复。</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _get_color_by_severity(self, severity: str) -> str:
        """根据严重程度获取颜色"""
        colors = {
            'critical': '#ff4444',
            'warning': '#ffaa00',
            'info': '#00aaff'
        }
        return colors.get(severity, '#666666')
```

## Day 3 - 性能优化实施

### 上午任务：数据库性能优化

#### 1. 查询优化
```python
# backend/optimization/query_optimizer.py
import asyncio
import time
from typing import List, Dict, Any, Optional
from sqlalchemy import text, Index
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

class QueryOptimizer:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.slow_queries = []
        self.query_cache = {}

    @asynccontextmanager
    async def profile_query(self, query_name: str):
        """查询性能分析"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            if duration > 1.0:  # 超过1秒的慢查询
                self.slow_queries.append({
                    'query_name': query_name,
                    'duration': duration,
                    'timestamp': time.time()
                })

    async def create_optimal_indexes(self):
        """创建优化索引"""
        indexes = [
            # 用户表索引
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_active ON users(email) WHERE is_active = true;",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_org_created ON users(organization_id, created_at);",

            # API密钥表索引
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_keys_user_active ON api_keys(user_id, is_active);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_keys_last_used ON api_keys(last_used_at DESC);",

            # 会话表索引
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_user_created ON sessions(user_id, created_at DESC);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_active ON sessions(is_active) WHERE is_active = true;",

            # 使用记录表索引
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_usage_records_user_date ON usage_records(user_id, created_at);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_usage_records_model_date ON usage_records(model_name, created_at);",

            # 监控数据索引
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_performance_metrics_name_time ON performance_metrics(metric_name, timestamp DESC);",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_business_metrics_user_time ON business_metrics(user_id, timestamp DESC);"
        ]

        for index_sql in indexes:
            try:
                await self.db.execute(text(index_sql))
                await self.db.commit()
                print(f"Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
            except Exception as e:
                print(f"Failed to create index: {e}")
                await self.db.rollback()

    async def analyze_slow_queries(self):
        """分析慢查询"""
        # 获取慢查询统计
        slow_query_sql = """
        SELECT query, mean_time, calls, total_time
        FROM pg_stat_statements
        WHERE mean_time > 1000  -- 超过1秒的查询
        ORDER BY mean_time DESC
        LIMIT 10;
        """

        result = await self.db.execute(text(slow_query_sql))
        slow_queries = result.fetchall()

        analysis = []
        for query in slow_queries:
            analysis.append({
                'query': query.query[:200] + '...' if len(query.query) > 200 else query.query,
                'mean_time': query.mean_time,
                'calls': query.calls,
                'total_time': query.total_time,
                'optimization_suggestions': self._suggest_optimizations(query.query)
            })

        return analysis

    def _suggest_optimizations(self, query: str) -> List[str]:
        """为查询提供优化建议"""
        suggestions = []

        query_lower = query.lower()

        # 检查是否缺少WHERE条件
        if 'where' not in query_lower and 'delete' not in query_lower:
            suggestions.append("考虑添加WHERE条件限制结果集")

        # 检查是否使用SELECT *
        if 'select *' in query_lower:
            suggestions.append("避免使用SELECT *，只查询需要的列")

        # 检查是否有适当的LIMIT
        if 'limit' not in query_lower and 'count(' not in query_lower:
            suggestions.append("考虑添加LIMIT限制返回的行数")

        # 检查JOIN优化
        if 'join' in query_lower and 'hash join' not in query_lower:
            suggestions.append("考虑使用HASH JOIN或优化JOIN条件")

        return suggestions

    async def optimize_table_statistics(self):
        """更新表统计信息"""
        tables = [
            'users', 'organizations', 'api_keys', 'sessions',
            'usage_records', 'performance_metrics', 'business_metrics'
        ]

        for table in tables:
            try:
                await self.db.execute(text(f"ANALYZE {table};"))
                print(f"Updated statistics for table: {table}")
            except Exception as e:
                print(f"Failed to analyze table {table}: {e}")

        await self.db.commit()
```

#### 2. 连接池优化
```python
# backend/optimization/connection_pool.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any

class ConnectionPoolManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.session_factory = None
        self.pool_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'idle_connections': 0,
            'overflow_connections': 0
        }

    async def initialize_pool(self, pool_config: Dict[str, Any] = None):
        """初始化连接池"""
        default_config = {
            'pool_size': 20,  # 基础连接数
            'max_overflow': 30,  # 溢出连接数
            'pool_timeout': 30,  # 获取连接超时时间
            'pool_recycle': 3600,  # 连接回收时间（秒）
            'pool_pre_ping': True,  # 连接前ping检查
            'echo': False,  # SQL日志
        }

        if pool_config:
            default_config.update(pool_config)

        self.engine = create_async_engine(
            self.database_url,
            **default_config
        )

        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        print("Database connection pool initialized")
        await self._monitor_pool()

    async def get_session(self) -> AsyncSession:
        """获取数据库会话"""
        if not self.session_factory:
            raise RuntimeError("Connection pool not initialized")

        session = self.session_factory()
        await self._update_pool_stats()
        return session

    async def _update_pool_stats(self):
        """更新连接池统计信息"""
        if self.engine:
            pool = self.engine.pool
            self.pool_stats = {
                'total_connections': pool.size() + pool.overflow(),
                'active_connections': pool.checkedin(),
                'idle_connections': pool.checkedout(),
                'overflow_connections': pool.overflow()
            }

    async def _monitor_pool(self):
        """监控连接池状态"""
        while True:
            await self._update_pool_stats()

            # 检查连接池健康状态
            if self.pool_stats['overflow_connections'] > 0:
                print(f"Warning: {self.pool_stats['overflow_connections']} overflow connections in use")

            if self.pool_stats['active_connections'] > self.pool_stats['total_connections'] * 0.8:
                print("Warning: High connection pool usage detected")

            await asyncio.sleep(60)  # 每分钟检查一次

    async def close_pool(self):
        """关闭连接池"""
        if self.engine:
            await self.engine.dispose()
            print("Database connection pool closed")

    def get_pool_stats(self) -> Dict[str, int]:
        """获取连接池统计信息"""
        return self.pool_stats.copy()
```

### 下午任务：缓存系统优化

#### 1. Redis多级缓存
```python
# backend/optimization/cache_manager.py
import json
import pickle
import hashlib
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from functools import wraps

class CacheManager:
    def __init__(self, redis_url: str):
        self.redis_client = None
        self.redis_url = redis_url
        self.local_cache = {}  # 本地缓存
        self.local_cache_ttl = {}  # 本地缓存过期时间
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'local_hits': 0,
            'redis_hits': 0,
            'sets': 0
        }

    async def initialize(self):
        """初始化Redis连接"""
        self.redis_client = redis.from_url(self.redis_url, decode_responses=False)
        await self.redis_client.ping()
        print("Redis cache initialized")

    def cache_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_hash = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    async def get(self, key: str, use_local_cache: bool = True) -> Optional[Any]:
        """获取缓存值"""
        # 检查本地缓存
        if use_local_cache and key in self.local_cache:
            if key in self.local_cache_ttl and datetime.now() < self.local_cache_ttl[key]:
                self.cache_stats['hits'] += 1
                self.cache_stats['local_hits'] += 1
                return self.local_cache[key]
            else:
                # 本地缓存过期，删除
                del self.local_cache[key]
                if key in self.local_cache_ttl:
                    del self.local_cache_ttl[key]

        # 检查Redis缓存
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    # 反序列化数据
                    data = pickle.loads(cached_data)

                    # 更新本地缓存
                    if use_local_cache:
                        self.local_cache[key] = data
                        self.local_cache_ttl[key] = datetime.now() + timedelta(minutes=5)

                    self.cache_stats['hits'] += 1
                    self.cache_stats['redis_hits'] += 1
                    return data
            except Exception as e:
                print(f"Redis cache get error: {e}")

        self.cache_stats['misses'] += 1
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600,
                  use_local_cache: bool = True, local_ttl_minutes: int = 5):
        """设置缓存值"""
        try:
            # 序列化数据
            serialized_data = pickle.dumps(value)

            # 设置Redis缓存
            if self.redis_client:
                await self.redis_client.setex(key, ttl, serialized_data)

            # 设置本地缓存
            if use_local_cache:
                self.local_cache[key] = value
                self.local_cache_ttl[key] = datetime.now() + timedelta(minutes=local_ttl_minutes)

            self.cache_stats['sets'] += 1

        except Exception as e:
            print(f"Cache set error: {e}")

    async def delete(self, key: str):
        """删除缓存"""
        # 删除本地缓存
        if key in self.local_cache:
            del self.local_cache[key]
        if key in self.local_cache_ttl:
            del self.local_cache_ttl[key]

        # 删除Redis缓存
        if self.redis_client:
            await self.redis_client.delete(key)

    async def clear_pattern(self, pattern: str):
        """清除匹配模式的缓存"""
        # 清除本地缓存
        keys_to_delete = [k for k in self.local_cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.local_cache[key]
            if key in self.local_cache_ttl:
                del self.local_cache_ttl[key]

        # 清除Redis缓存
        if self.redis_client:
            keys = await self.redis_client.keys(f"*{pattern}*")
            if keys:
                await self.redis_client.delete(*keys)

    def cached(self, prefix: str, ttl: int = 3600):
        """缓存装饰器"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = self.cache_key(prefix, *args, **kwargs)

                # 尝试从缓存获取
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # 执行函数
                result = await func(*args, **kwargs)

                # 缓存结果
                await self.set(cache_key, result, ttl)

                return result
            return wrapper
        return decorator

    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        stats = {
            **self.cache_stats,
            'hit_rate_percent': round(hit_rate, 2),
            'local_cache_size': len(self.local_cache),
            'local_cache_hit_rate': (self.cache_stats['local_hits'] / self.cache_stats['hits'] * 100) if self.cache_stats['hits'] > 0 else 0
        }

        # 获取Redis信息
        if self.redis_client:
            try:
                redis_info = await self.redis_client.info()
                stats.update({
                    'redis_used_memory': redis_info.get('used_memory_human'),
                    'redis_connected_clients': redis_info.get('connected_clients'),
                    'redis_keyspace_hits': redis_info.get('keyspace_hits', 0),
                    'redis_keyspace_misses': redis_info.get('keyspace_misses', 0)
                })
            except Exception as e:
                print(f"Failed to get Redis info: {e}")

        return stats

    async def cleanup_expired_local_cache(self):
        """清理过期的本地缓存"""
        current_time = datetime.now()
        expired_keys = [
            key for key, expiry_time in self.local_cache_ttl.items()
            if current_time >= expiry_time
        ]

        for key in expired_keys:
            if key in self.local_cache:
                del self.local_cache[key]
            del self.local_cache_ttl[key]

        if expired_keys:
            print(f"Cleaned up {len(expired_keys)} expired local cache entries")

# 全局缓存管理器实例
cache_manager = CacheManager("redis://localhost:6379/0")
```

#### 2. 应用层缓存策略
```python
# backend/optimization/api_cache.py
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import hashlib
import json

class APICacheMiddleware:
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        # 可缓存的端点配置
        self.cacheable_endpoints = {
            '/api/v1/models': {'ttl': 300, 'vary_by_user': False},
            '/api/v1/stats': {'ttl': 60, 'vary_by_user': True},
            '/api/v1/config': {'ttl': 600, 'vary_by_user': True},
            '/api/v1/health': {'ttl': 30, 'vary_by_user': False},
        }

    async def __call__(self, request: Request, call_next):
        # 检查是否为可缓存端点
        if request.method != 'GET' or request.url.path not in self.cacheable_endpoints:
            return await call_next(request)

        cache_config = self.cacheable_endpoints[request.url.path]

        # 生成缓存键
        cache_key = await self._generate_cache_key(request, cache_config)

        # 尝试从缓存获取
        cached_response = await self.cache_manager.get(cache_key)
        if cached_response:
            return JSONResponse(
                content=cached_response['content'],
                status_code=cached_response['status_code'],
                headers=cached_response['headers']
            )

        # 执行请求
        response = await call_next(request)

        # 缓存响应
        if response.status_code == 200:
            response_body = b''
            async for chunk in response.body_iterator:
                response_body += chunk

            try:
                content = json.loads(response_body.decode())
                await self.cache_manager.set(
                    cache_key,
                    {
                        'content': content,
                        'status_code': response.status_code,
                        'headers': dict(response.headers)
                    },
                    ttl=cache_config['ttl']
                )
            except json.JSONDecodeError:
                pass  # 不缓存非JSON响应

        return response

    async def _generate_cache_key(self, request: Request, cache_config: Dict) -> str:
        """生成API缓存键"""
        key_parts = [
            f"api_cache:{request.url.path}",
            f"method:{request.method}"
        ]

        # 如果需要根据用户变化
        if cache_config.get('vary_by_user', False):
            user_id = getattr(request.state, 'user_id', 'anonymous')
            key_parts.append(f"user:{user_id}")

        # 添加查询参数
        if request.query_params:
            sorted_params = sorted(request.query_params.items())
            key_parts.append(f"params:{json.dumps(sorted_params)}")

        return ":".join(key_parts)

# 智能缓存预热
class CacheWarmup:
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager

    async def warmup_cache(self):
        """预热缓存"""
        warmup_tasks = [
            self._warmup_models_cache(),
            self._warmup_config_cache(),
            self._warmup_stats_cache()
        ]

        await asyncio.gather(*warmup_tasks, return_exceptions=True)
        print("Cache warmup completed")

    async def _warmup_models_cache(self):
        """预热模型缓存"""
        try:
            # 这里需要调用实际的模型API
            models_data = await self._fetch_models_data()
            await self.cache_manager.set('api_cache:/api/v1/models:method:GET', models_data, ttl=300)
        except Exception as e:
            print(f"Failed to warmup models cache: {e}")

    async def _warmup_config_cache(self):
        """预热配置缓存"""
        try:
            config_data = await self._fetch_config_data()
            await self.cache_manager.set('api_cache:/api/v1/config:method:GET', config_data, ttl=600)
        except Exception as e:
            print(f"Failed to warmup config cache: {e}")

    async def _warmup_stats_cache(self):
        """预热统计数据缓存"""
        try:
            stats_data = await self._fetch_stats_data()
            await self.cache_manager.set('api_cache:/api/v1/stats:method:GET', stats_data, ttl=60)
        except Exception as e:
            print(f"Failed to warmup stats cache: {e}")

    async def _fetch_models_data(self):
        """获取模型数据（模拟）"""
        # 实际实现中调用模型服务
        return {"models": []}

    async def _fetch_config_data(self):
        """获取配置数据（模拟）"""
        # 实际实现中调用配置服务
        return {"config": {}}

    async def _fetch_stats_data(self):
        """获取统计数据（模拟）"""
        # 实际实现中调用统计服务
        return {"stats": {}}
```

### 晚上任务：API性能优化

#### 1. 异步优化
```python
# backend/optimization/async_optimizer.py
import asyncio
import time
from typing import List, Dict, Any, Callable, Awaitable
from concurrent.futures import ThreadPoolExecutor
import functools

class AsyncOptimizer:
    def __init__(self):
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        self.performance_stats = {}

    def batch_async_requests(self, coroutines: List[Awaitable],
                           max_concurrency: int = 10) -> List[Any]:
        """批量执行异步请求"""
        semaphore = asyncio.Semaphore(max_concurrency)

        async def bounded_coroutine(coro):
            async with semaphore:
                return await coro

        bounded_coroutines = [bounded_coroutine(coro) for coro in coroutines]
        return asyncio.run(bounded_coroutines)

    def run_in_thread(self, func: Callable, *args, **kwargs):
        """在线程池中运行同步函数"""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(self.thread_pool, functools.partial(func, *args, **kwargs))

    def async_timed(self, operation_name: str):
        """异步计时装饰器"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time

                    # 记录性能统计
                    if operation_name not in self.performance_stats:
                        self.performance_stats[operation_name] = []
                    self.performance_stats[operation_name].append({
                        'duration': duration,
                        'timestamp': time.time(),
                        'success': True
                    })

                    return result
                except Exception as e:
                    duration = time.time() - start_time

                    if operation_name not in self.performance_stats:
                        self.performance_stats[operation_name] = []
                    self.performance_stats[operation_name].append({
                        'duration': duration,
                        'timestamp': time.time(),
                        'success': False,
                        'error': str(e)
                    })

                    raise
            return wrapper
        return decorator

    async def parallel_api_calls(self, api_calls: List[Dict[str, Any]]) -> List[Any]:
        """并行执行多个API调用"""
        async def execute_api_call(call_config):
            api_func = call_config['function']
            args = call_config.get('args', [])
            kwargs = call_config.get('kwargs', {})

            try:
                result = await api_func(*args, **kwargs)
                return {
                    'success': True,
                    'result': result,
                    'call_id': call_config.get('id')
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'call_id': call_config.get('id')
                }

        tasks = [execute_api_call(call) for call in api_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return results

    def get_performance_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        report = {}

        for operation, stats in self.performance_stats.items():
            if not stats:
                continue

            successful_calls = [s for s in stats if s['success']]
            failed_calls = [s for s in stats if not s['success']]

            if successful_calls:
                durations = [s['duration'] for s in successful_calls]
                report[operation] = {
                    'total_calls': len(stats),
                    'successful_calls': len(successful_calls),
                    'failed_calls': len(failed_calls),
                    'success_rate': len(successful_calls) / len(stats) * 100,
                    'avg_duration': sum(durations) / len(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'p95_duration': sorted(durations)[int(len(durations) * 0.95)],
                    'recent_errors': [call['error'] for call in failed_calls[-5:]]
                }

        return report

# 使用示例
async_optimizer = AsyncOptimizer()

@async_optimizer.async_timed('ai_model_call')
async def optimized_ai_call(prompt: str, model: str):
    """优化的AI模型调用"""
    # 实现优化的AI调用逻辑
    pass
```

#### 2. 响应压缩
```python
# backend/optimization/compression.py
import gzip
import json
from fastapi import Response, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict

class ResponseCompressor:
    def __init__(self, min_size: int = 1024):  # 1KB以上压缩
        self.min_size = min_size

    def compress_response(self, response_data: Any, accept_encoding: str) -> Response:
        """压缩响应数据"""
        # 序列化数据
        if isinstance(response_data, dict):
            content = json.dumps(response_data).encode('utf-8')
        else:
            content = str(response_data).encode('utf-8')

        # 检查是否需要压缩
        if len(content) < self.min_size or 'gzip' not in accept_encoding.lower():
            return JSONResponse(content=response_data)

        # 压缩数据
        compressed_content = gzip.compress(content)

        # 计算压缩率
        compression_ratio = (1 - len(compressed_content) / len(content)) * 100

        headers = {
            'Content-Encoding': 'gzip',
            'Content-Type': 'application/json',
            'X-Compression-Ratio': f"{compression_ratio:.2f}%"
        }

        return Response(
            content=compressed_content,
            headers=headers,
            media_type="application/json"
        )

class StreamingOptimizer:
    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size

    async def stream_with_backpressure(self, generator, max_queue_size: int = 100):
        """带背压控制的流式响应"""
        queue = asyncio.Queue(maxsize=max_queue_size)

        async def producer():
            try:
                async for item in generator:
                    await queue.put(item)
                await queue.put(None)  # 结束标记
            except Exception as e:
                await queue.put({'error': str(e)})

        async def consumer():
            producer_task = asyncio.create_task(producer())

            try:
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    if isinstance(item, dict) and 'error' in item:
                        raise Exception(item['error'])
                    yield item
                    queue.task_done()
            finally:
                producer_task.cancel()
                try:
                    await producer_task
                except asyncio.CancelledError:
                    pass

        return consumer()

# 响应优化中间件
class OptimizationMiddleware:
    def __init__(self):
        self.compressor = ResponseCompressor()
        self.streaming_optimizer = StreamingOptimizer()

    async def __call__(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        # 添加性能头
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        # 压缩响应（如果适用）
        if (request.headers.get("accept-encoding", "").lower().find("gzip") != -1 and
            isinstance(response, JSONResponse) and
            len(str(response.body)) > self.compressor.min_size):

            # 重新构建压缩响应
            return self.compressor.compress_response(
                response.body,
                request.headers.get("accept-encoding", "")
            )

        return response
```

## 总结

Week 8将建立完整的性能监控和优化体系：

### 核心功能
1. **实时监控仪表板** - 系统指标、业务指标可视化
2. **智能告警系统** - 基于机器学习的异常检测
3. **多级缓存优化** - Redis + 本地缓存策略
4. **数据库性能优化** - 查询优化、连接池管理
5. **API性能优化** - 异步处理、响应压缩

### 预期成果
- **系统响应时间** < 100ms (P95)
- **监控覆盖率** 100%
- **告警准确率** > 95%
- **缓存命中率** > 80%
- **系统可用性** > 99.9%

这些功能将确保AI Hub平台在高并发场景下的稳定性和高性能表现。