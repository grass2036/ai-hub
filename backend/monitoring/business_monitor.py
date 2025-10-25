"""
业务监控模块
追踪API使用、AI模型调用、用户会话等业务指标
"""
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import uuid
import logging

logger = logging.getLogger(__name__)

@dataclass
class BusinessMetric:
    """业务指标数据结构"""
    id: str
    name: str
    value: float
    unit: str
    timestamp: datetime
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class APICallMetric:
    """API调用指标"""
    endpoint: str
    method: str
    user_id: str
    response_time: float
    status_code: int
    request_size: int
    response_size: int
    timestamp: datetime
    user_agent: str
    ip_address: str

@dataclass
class AIModelMetric:
    """AI模型使用指标"""
    model_name: str
    provider: str
    user_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    response_time: float
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class BusinessMonitor:
    """业务监控器"""

    def __init__(self):
        self.metrics: List[BusinessMetric] = []
        self.api_calls: List[APICallMetric] = []
        self.ai_model_calls: List[AIModelMetric] = []
        self.active_sessions: Dict[str, datetime] = {}
        self.daily_stats: Dict[str, Dict] = defaultdict(lambda: defaultdict(int))
        self.real_time_stats = {
            'current_active_users': 0,
            'requests_per_minute': deque(maxlen=60),  # 最近60分钟的请求
            'errors_per_minute': deque(maxlen=60),    # 最近60分钟的错误
            'response_times': deque(maxlen=1000),     # 最近1000个响应时间
        }
        self.max_metrics_size = 10000

    def track_api_call(self, endpoint: str, method: str, user_id: str,
                      response_time: float, status_code: int,
                      request_size: int = 0, response_size: int = 0,
                      user_agent: str = '', ip_address: str = ''):
        """追踪API调用"""
        metric = APICallMetric(
            endpoint=endpoint,
            method=method,
            user_id=user_id,
            response_time=response_time,
            status_code=status_code,
            request_size=request_size,
            response_size=response_size,
            timestamp=datetime.utcnow(),
            user_agent=user_agent,
            ip_address=ip_address
        )

        self.api_calls.append(metric)
        self._update_real_time_stats(metric)
        self._update_daily_stats(metric)

        # 保持列表大小在合理范围内
        if len(self.api_calls) > self.max_metrics_size:
            self.api_calls = self.api_calls[-self.max_metrics_size:]

    def track_ai_model_usage(self, model_name: str, provider: str, user_id: str,
                           prompt_tokens: int, completion_tokens: int,
                           cost: float, response_time: float,
                           success: bool = True, error_message: str = None):
        """追踪AI模型使用情况"""
        metric = AIModelMetric(
            model_name=model_name,
            provider=provider,
            user_id=user_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost,
            response_time=response_time,
            success=success,
            error_message=error_message
        )

        self.ai_model_calls.append(metric)
        self._update_ai_stats(metric)

        # 保持列表大小在合理范围内
        if len(self.ai_model_calls) > self.max_metrics_size:
            self.ai_model_calls = self.ai_model_calls[-self.max_metrics_size:]

    def track_user_session(self, user_id: str, session_id: str, action: str = 'start'):
        """追踪用户会话"""
        session_key = f"{user_id}:{session_id}"

        if action == 'start':
            self.active_sessions[session_key] = datetime.utcnow()
            self.real_time_stats['current_active_users'] = len(set(
                key.split(':')[0] for key in self.active_sessions.keys()
            ))
        elif action == 'end' and session_key in self.active_sessions:
            session_duration = datetime.utcnow() - self.active_sessions[session_key]
            del self.active_sessions[session_key]

            # 记录会话时长指标
            self.add_metric(BusinessMetric(
                id=str(uuid.uuid4()),
                name='user_session_duration',
                value=session_duration.total_seconds(),
                unit='seconds',
                timestamp=datetime.utcnow(),
                user_id=user_id,
                tags={'action': 'session_end'}
            ))

            self.real_time_stats['current_active_users'] = len(set(
                key.split(':')[0] for key in self.active_sessions.keys()
            ))

    def add_metric(self, metric: BusinessMetric):
        """添加自定义业务指标"""
        self.metrics.append(metric)

        # 保持列表大小在合理范围内
        if len(self.metrics) > self.max_metrics_size:
            self.metrics = self.metrics[-self.max_metrics_size:]

    def _update_real_time_stats(self, metric: APICallMetric):
        """更新实时统计"""
        current_minute = datetime.utcnow().minute

        # 更新请求计数
        self.real_time_stats['requests_per_minute'].append({
            'minute': current_minute,
            'count': 1,
            'timestamp': datetime.utcnow()
        })

        # 更新错误计数
        if metric.status_code >= 400:
            self.real_time_stats['errors_per_minute'].append({
                'minute': current_minute,
                'count': 1,
                'timestamp': datetime.utcnow()
            })

        # 更新响应时间
        self.real_time_stats['response_times'].append({
            'time': metric.response_time,
            'timestamp': datetime.utcnow()
        })

    def _update_daily_stats(self, metric: APICallMetric):
        """更新每日统计"""
        date_key = metric.timestamp.strftime('%Y-%m-%d')

        self.daily_stats[date_key]['total_requests'] += 1
        self.daily_stats[date_key][f'requests_{metric.method}'] += 1
        self.daily_stats[date_key][f'endpoint_{metric.endpoint.replace("/", "_")}'] += 1

        if metric.status_code >= 400:
            self.daily_stats[date_key]['total_errors'] += 1

    def _update_ai_stats(self, metric: AIModelMetric):
        """更新AI模型统计"""
        date_key = metric.timestamp.strftime('%Y-%m-%d')

        self.daily_stats[date_key]['ai_calls_total'] += 1
        self.daily_stats[date_key]['ai_tokens_total'] += metric.total_tokens
        self.daily_stats[date_key]['ai_cost_total'] += metric.cost
        self.daily_stats[date_key][f'ai_calls_{metric.model_name.replace(":", "_")}'] += 1

        if not metric.success:
            self.daily_stats[date_key]['ai_errors_total'] += 1

    def get_api_stats(self, hours: int = 24) -> Dict:
        """获取API统计数据"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_calls = [call for call in self.api_calls if call.timestamp >= cutoff_time]

        if not recent_calls:
            return {'period_hours': hours, 'total_requests': 0}

        # 基础统计
        total_requests = len(recent_calls)
        successful_requests = len([c for c in recent_calls if c.status_code < 400])
        error_rate = (total_requests - successful_requests) / total_requests * 100

        # 响应时间统计
        response_times = [c.response_time for c in recent_calls]
        avg_response_time = sum(response_times) / len(response_times)
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
        p99_response_time = sorted(response_times)[int(len(response_times) * 0.99)]

        # 端点统计
        endpoint_stats = defaultdict(lambda: {'count': 0, 'total_time': 0, 'errors': 0})
        for call in recent_calls:
            endpoint_stats[call.endpoint]['count'] += 1
            endpoint_stats[call.endpoint]['total_time'] += call.response_time
            if call.status_code >= 400:
                endpoint_stats[call.endpoint]['errors'] += 1

        # 用户统计
        unique_users = len(set(call.user_id for call in recent_calls))

        return {
            'period_hours': hours,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'error_rate_percent': round(error_rate, 2),
            'unique_users': unique_users,
            'avg_response_time_ms': round(avg_response_time * 1000, 2),
            'p95_response_time_ms': round(p95_response_time * 1000, 2),
            'p99_response_time_ms': round(p99_response_time * 1000, 2),
            'top_endpoints': [
                {
                    'endpoint': endpoint,
                    'count': stats['count'],
                    'avg_time_ms': round(stats['total_time'] / stats['count'] * 1000, 2),
                    'error_count': stats['errors']
                }
                for endpoint, stats in sorted(endpoint_stats.items(),
                                            key=lambda x: x[1]['count'], reverse=True)[:10]
            ]
        }

    def get_ai_model_stats(self, hours: int = 24) -> Dict:
        """获取AI模型使用统计"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_calls = [call for call in self.ai_model_calls if call.timestamp >= cutoff_time]

        if not recent_calls:
            return {'period_hours': hours, 'total_calls': 0}

        # 基础统计
        total_calls = len(recent_calls)
        successful_calls = len([c for c in recent_calls if c.success])
        success_rate = successful_calls / total_calls * 100

        # Token和成本统计
        total_tokens = sum(c.total_tokens for c in recent_calls)
        total_cost = sum(c.cost for c in recent_calls)

        # 响应时间统计
        response_times = [c.response_time for c in recent_calls if c.success]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        # 模型统计
        model_stats = defaultdict(lambda: {
            'count': 0, 'tokens': 0, 'cost': 0, 'errors': 0, 'total_time': 0
        })
        for call in recent_calls:
            model_stats[call.model_name]['count'] += 1
            model_stats[call.model_name]['tokens'] += call.total_tokens
            model_stats[call.model_name]['cost'] += call.cost
            model_stats[call.model_name]['total_time'] += call.response_time
            if not call.success:
                model_stats[call.model_name]['errors'] += 1

        return {
            'period_hours': hours,
            'total_calls': total_calls,
            'successful_calls': successful_calls,
            'success_rate_percent': round(success_rate, 2),
            'total_tokens': total_tokens,
            'total_cost_usd': round(total_cost, 4),
            'avg_response_time_s': round(avg_response_time, 2),
            'top_models': [
                {
                    'model_name': model,
                    'calls': stats['count'],
                    'tokens': stats['tokens'],
                    'cost_usd': round(stats['cost'], 4),
                    'avg_time_s': round(stats['total_time'] / stats['count'], 2) if stats['count'] > 0 else 0,
                    'error_count': stats['errors']
                }
                for model, stats in sorted(model_stats.items(),
                                         key=lambda x: x[1]['count'], reverse=True)[:10]
            ]
        }

    def get_user_activity_stats(self, hours: int = 24) -> Dict:
        """获取用户活动统计"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # API活动用户
        active_api_users = set(
            call.user_id for call in self.api_calls
            if call.timestamp >= cutoff_time
        )

        # AI使用用户
        active_ai_users = set(
            call.user_id for call in self.ai_model_calls
            if call.timestamp >= cutoff_time
        )

        # 当前活跃会话
        current_active_users = len(set(
            key.split(':')[0] for key in self.active_sessions.keys()
        ))

        return {
            'period_hours': hours,
            'active_api_users': len(active_api_users),
            'active_ai_users': len(active_ai_users),
            'current_active_sessions': len(self.active_sessions),
            'current_active_users': current_active_users,
            'unique_users_today': len(active_api_users | active_ai_users)
        }

    def get_real_time_stats(self) -> Dict:
        """获取实时统计数据"""
        now = datetime.utcnow()
        current_minute = now.minute

        # 请求率（每分钟）
        recent_requests = [
            req for req in self.real_time_stats['requests_per_minute']
            if (now - req['timestamp']).total_seconds() < 300  # 最近5分钟
        ]
        requests_per_minute = len(recent_requests) / 5 if recent_requests else 0

        # 错误率（每分钟）
        recent_errors = [
            err for err in self.real_time_stats['errors_per_minute']
            if (now - err['timestamp']).total_seconds() < 300  # 最近5分钟
        ]
        errors_per_minute = len(recent_errors) / 5 if recent_errors else 0
        error_rate = (errors_per_minute / requests_per_minute * 100) if requests_per_minute > 0 else 0

        # 当前响应时间（最近5分钟的平均值）
        recent_response_times = [
            rt['time'] for rt in self.real_time_stats['response_times']
            if (now - rt['timestamp']).total_seconds() < 300
        ]
        current_response_time = sum(recent_response_times) / len(recent_response_times) if recent_response_times else 0

        return {
            'timestamp': now.isoformat(),
            'current_active_users': self.real_time_stats['current_active_users'],
            'requests_per_minute': round(requests_per_minute, 2),
            'errors_per_minute': round(errors_per_minute, 2),
            'error_rate_percent': round(error_rate, 2),
            'current_response_time_ms': round(current_response_time * 1000, 2),
            'active_sessions': len(self.active_sessions)
        }

    def get_daily_summary(self, date: str = None) -> Dict:
        """获取每日汇总数据"""
        if date is None:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        stats = self.daily_stats.get(date, {})

        return {
            'date': date,
            'total_requests': stats.get('total_requests', 0),
            'total_errors': stats.get('total_errors', 0),
            'ai_calls_total': stats.get('ai_calls_total', 0),
            'ai_tokens_total': stats.get('ai_tokens_total', 0),
            'ai_cost_total': round(stats.get('ai_cost_total', 0), 4),
            'ai_errors_total': stats.get('ai_errors_total', 0)
        }

    def export_metrics(self, filename: str, metric_type: str = 'all', hours: int = 24):
        """导出指标到文件"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        data = {}

        if metric_type in ('all', 'api'):
            api_data = [asdict(call) for call in self.api_calls if call.timestamp >= cutoff_time]
            for item in api_data:
                item['timestamp'] = item['timestamp'].isoformat()
            data['api_calls'] = api_data

        if metric_type in ('all', 'ai'):
            ai_data = [asdict(call) for call in self.ai_model_calls if call.timestamp >= cutoff_time]
            for item in ai_data:
                item['timestamp'] = item['timestamp'].isoformat()
            data['ai_model_calls'] = ai_data

        if metric_type in ('all', 'business'):
            business_data = [asdict(metric) for metric in self.metrics if metric.timestamp >= cutoff_time]
            for item in business_data:
                item['timestamp'] = item['timestamp'].isoformat()
            data['business_metrics'] = business_data

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported metrics to {filename}")

# 全局业务监控器实例
business_monitor = BusinessMonitor()