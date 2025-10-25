"""
智能告警策略
结合传统规则和机器学习的智能告警系统
"""
import asyncio
import statistics
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, deque
import logging

from backend.monitoring.alert_engine import alert_engine, AlertCondition, AlertSeverity
from backend.monitoring.anomaly_detection import anomaly_detector, AnomalyResult
from backend.monitoring.business_monitor import business_monitor
from backend.monitoring.system_monitor import system_monitor

logger = logging.getLogger(__name__)

@dataclass
class SmartAlertContext:
    """智能告警上下文"""
    metric_name: str
    current_value: float
    timestamp: datetime
    historical_data: List[Dict]
    anomaly_result: Optional[AnomalyResult] = None
    rule_based_result: Optional[Dict] = None
    business_context: Optional[Dict] = None
    system_context: Optional[Dict] = None

@dataclass
class SmartAlert:
    """智能告警结果"""
    metric_name: str
    alert_type: str  # 'rule_based', 'anomaly_based', 'hybrid'
    severity: AlertSeverity
    confidence: float
    message: str
    context: Dict[str, Any]
    recommendations: List[str]
    triggered_at: datetime
    contributing_factors: List[str]

class SmartAlerting:
    """智能告警引擎"""

    def __init__(self, anomaly_detector_instance=None):
        self.anomaly_detector = anomaly_detector_instance or anomaly_detector
        self.alert_history = defaultdict(deque)  # metric_name -> alert_history
        self.suppression_rules = {}
        self.correlation_rules = {}
        self.trend_analyzers = {}
        self.seasonal_patterns = {}
        self.baseline_calculators = {}
        self.max_history_size = 100

        # 配置参数
        self.min_confidence_threshold = 0.6
        self.alert_cooldown_minutes = 5
        self.correlation_window_minutes = 10

    async def evaluate_smart_alert(self, metric_name: str, current_value: float,
                                  timestamp: datetime = None, context: Dict = None) -> Optional[SmartAlert]:
        """智能告警评估"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        # 获取历史数据
        historical_data = self._get_historical_data(metric_name, lookback_hours=48)
        if len(historical_data) < 10:
            return None

        # 创建告警上下文
        alert_context = SmartAlertContext(
            metric_name=metric_name,
            current_value=current_value,
            timestamp=timestamp,
            historical_data=historical_data,
            business_context=self._get_business_context(metric_name),
            system_context=self._get_system_context()
        )

        # 1. 规则基础告警
        rule_result = await self._evaluate_rule_based_alerts(alert_context)

        # 2. 异常检测告警
        anomaly_result = await self._evaluate_anomaly_based_alerts(alert_context)

        # 3. 趋势分析告警
        trend_result = await self._evaluate_trend_based_alerts(alert_context)

        # 4. 季节性告警
        seasonal_result = await self._evaluate_seasonal_alerts(alert_context)

        # 5. 关联分析
        correlation_result = await self._evaluate_correlation_alerts(alert_context)

        # 综合评估结果
        smart_alert = self._combine_alert_results(
            alert_context, rule_result, anomaly_result, trend_result, seasonal_result, correlation_result
        )

        if smart_alert:
            # 记录告警历史
            self._record_alert_history(metric_name, smart_alert)

            # 生成建议
            smart_alert.recommendations = self._generate_recommendations(smart_alert, alert_context)

        return smart_alert

    async def _evaluate_rule_based_alerts(self, context: SmartAlertContext) -> Optional[Dict]:
        """评估基于规则的告警"""
        try:
            # 获取相关的告警规则
            relevant_rules = [
                rule for rule in alert_engine.rules.values()
                if rule.metric_name == context.metric_name and rule.enabled
            ]

            triggered_rules = []
            for rule in relevant_rules:
                if alert_engine._evaluate_condition(context.current_value, rule):
                    triggered_rules.append(rule)

            if triggered_rules:
                # 选择最高严重程度的规则
                highest_severity_rule = max(
                    triggered_rules,
                    key=lambda r: {'critical': 3, 'warning': 2, 'info': 1}[r.severity.value]
                )

                return {
                    'type': 'rule_based',
                    'severity': highest_severity_rule.severity,
                    'rule_id': highest_severity_rule.id,
                    'rule_name': highest_severity_rule.name,
                    'threshold': highest_severity_rule.threshold,
                    'operator': highest_severity_rule.operator,
                    'confidence': 0.9,  # 规则告警置信度较高
                    'message': alert_engine._generate_alert_message(
                        highest_severity_rule, context.current_value, context.business_context
                    )
                }

        except Exception as e:
            logger.error(f"Error in rule-based evaluation for {context.metric_name}: {e}")

        return None

    async def _evaluate_anomaly_based_alerts(self, context: SmartAlertContext) -> Optional[Dict]:
        """评估基于异常检测的告警"""
        try:
            # 确保有足够的训练数据
            if len(context.historical_data) < 100:
                return None

            # 执行异常检测
            current_data = {
                'value': context.current_value,
                'timestamp': context.timestamp.isoformat()
            }

            anomaly_result = self.anomaly_detector.detect_anomaly(
                context.metric_name, current_data, context.historical_data
            )

            if anomaly_result and anomaly_result.is_anomaly:
                # 根据异常分数确定严重程度
                severity = self._determine_severity_from_anomaly_score(anomaly_result.anomaly_score)

                return {
                    'type': 'anomaly_based',
                    'severity': severity,
                    'anomaly_score': anomaly_result.anomaly_score,
                    'confidence': anomaly_result.confidence,
                    'feature_contributions': anomaly_result.feature_contributions,
                    'message': f"异常检测: {context.metric_name} 出现异常模式 (分数: {anomaly_result.anomaly_score:.3f})"
                }

        except Exception as e:
            logger.error(f"Error in anomaly-based evaluation for {context.metric_name}: {e}")

        return None

    async def _evaluate_trend_based_alerts(self, context: SmartAlertContext) -> Optional[Dict]:
        """评估基于趋势的告警"""
        try:
            if len(context.historical_data) < 20:
                return None

            # 计算趋势
            trend_analysis = self._analyze_trend(context.historical_data)

            # 检测异常趋势
            if trend_analysis['slope'] > 0.5:  # 上升趋势
                if trend_analysis['r_squared'] > 0.7:  # 强趋势
                    severity = AlertSeverity.WARNING if trend_analysis['slope'] < 2.0 else AlertSeverity.CRITICAL

                    return {
                        'type': 'trend_based',
                        'severity': severity,
                        'trend_direction': 'increasing',
                        'slope': trend_analysis['slope'],
                        'r_squared': trend_analysis['r_squared'],
                        'confidence': trend_analysis['r_squared'],
                        'message': f"趋势告警: {context.metric_name} 呈现上升趋势 (斜率: {trend_analysis['slope']:.3f})"
                    }

            elif trend_analysis['slope'] < -0.5:  # 下降趋势
                if trend_analysis['r_squared'] > 0.7:  # 强趋势
                    severity = AlertSeverity.WARNING if trend_analysis['slope'] > -2.0 else AlertSeverity.CRITICAL

                    return {
                        'type': 'trend_based',
                        'severity': severity,
                        'trend_direction': 'decreasing',
                        'slope': trend_analysis['slope'],
                        'r_squared': trend_analysis['r_squared'],
                        'confidence': trend_analysis['r_squared'],
                        'message': f"趋势告警: {context.metric_name} 呈现下降趋势 (斜率: {trend_analysis['slope']:.3f})"
                    }

        except Exception as e:
            logger.error(f"Error in trend-based evaluation for {context.metric_name}: {e}")

        return None

    async def _evaluate_seasonal_alerts(self, context: SmartAlertContext) -> Optional[Dict]:
        """评估季节性告警"""
        try:
            # 获取历史季节性模式
            seasonal_pattern = self._calculate_seasonal_pattern(context.historical_data)

            if not seasonal_pattern:
                return None

            # 当前时间特征
            current_time = context.timestamp
            hour_of_day = current_time.hour
            day_of_week = current_time.weekday()

            # 获取季节性基准
            seasonal_baseline = seasonal_pattern.get('hourly', {}).get(hour_of_day, {})
            expected_value = seasonal_baseline.get('mean')
            expected_std = seasonal_baseline.get('std', 1)

            if expected_value is None:
                return None

            # 计算偏差
            deviation = abs(context.current_value - expected_value) / max(expected_std, 1)

            # 如果偏差超过阈值
            if deviation > 2.5:  # 2.5个标准差
                severity = AlertSeverity.WARNING if deviation < 4.0 else AlertSeverity.CRITICAL

                return {
                    'type': 'seasonal_based',
                    'severity': severity,
                    'expected_value': expected_value,
                    'actual_value': context.current_value,
                    'deviation_score': deviation,
                    'seasonal_context': f"{hour_of_day}:00, 星期{day_of_week + 1}",
                    'confidence': min(0.9, deviation / 5.0),
                    'message': f"季节性告警: {context.metric_name} 偏离季节性模式 {deviation:.1f} 个标准差"
                }

        except Exception as e:
            logger.error(f"Error in seasonal evaluation for {context.metric_name}: {e}")

        return None

    async def _evaluate_correlation_alerts(self, context: SmartAlertContext) -> Optional[Dict]:
        """评估关联告警"""
        try:
            # 获取最近的告警历史
            recent_alerts = self._get_recent_alerts(minutes=self.correlation_window_minutes)

            # 检查是否有相关指标的告警
            correlated_metrics = self._get_correlated_metrics(context.metric_name)

            for correlated_metric in correlated_metrics:
                if correlated_metric in recent_alerts:
                    # 发现关联告警
                    correlated_alert = recent_alerts[correlated_metric]

                    return {
                        'type': 'correlation_based',
                        'severity': correlated_alert['severity'],
                        'correlated_metric': correlated_metric,
                        'correlated_alert': correlated_alert,
                        'confidence': 0.7,
                        'message': f"关联告警: {context.metric_name} 与 {correlated_metric} 同时出现异常"
                    }

        except Exception as e:
            logger.error(f"Error in correlation evaluation for {context.metric_name}: {e}")

        return None

    def _combine_alert_results(self, context: SmartAlertContext, *results) -> Optional[SmartAlert]:
        """综合评估结果"""
        valid_results = [r for r in results if r is not None]

        if not valid_results:
            return None

        # 检查抑制规则
        if self._is_suppressed(context.metric_name, context.timestamp):
            return None

        # 选择最高严重程度的结果
        severity_order = {'critical': 3, 'warning': 2, 'info': 1}
        primary_result = max(
            valid_results,
            key=lambda r: severity_order.get(r['severity'].value, 0)
        )

        # 计算综合置信度
        confidences = [r.get('confidence', 0.5) for r in valid_results]
        combined_confidence = np.mean(confidences)

        # 置信度过低则不告警
        if combined_confidence < self.min_confidence_threshold:
            return None

        # 构建贡献因素
        contributing_factors = []
        for result in valid_results:
            contributing_factors.append(result['type'])

        # 构建上下文信息
        alert_context = {
            'metric_value': context.current_value,
            'timestamp': context.timestamp.isoformat(),
            'historical_stats': self._calculate_historical_stats(context.historical_data),
            'business_context': context.business_context,
            'system_context': context.system_context,
            'all_detections': valid_results
        }

        # 生成告警消息
        alert_message = self._generate_composite_message(context, valid_results)

        return SmartAlert(
            metric_name=context.metric_name,
            alert_type='hybrid' if len(valid_results) > 1 else valid_results[0]['type'],
            severity=primary_result['severity'],
            confidence=combined_confidence,
            message=alert_message,
            context=alert_context,
            recommendations=[],  # 稍后生成
            contributing_factors=contributing_factors,
            triggered_at=context.timestamp
        )

    def _determine_severity_from_anomaly_score(self, score: float) -> AlertSeverity:
        """根据异常分数确定严重程度"""
        if score < -0.5:
            return AlertSeverity.CRITICAL
        elif score < -0.2:
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO

    def _analyze_trend(self, historical_data: List[Dict]) -> Dict:
        """分析趋势"""
        try:
            values = [point['value'] for point in historical_data[-20:]]  # 最近20个数据点
            x = np.arange(len(values))

            # 线性回归
            coeffs = np.polyfit(x, values, 1)
            slope = coeffs[0]

            # 计算R²
            y_pred = np.polyval(coeffs, x)
            ss_res = np.sum((values - y_pred) ** 2)
            ss_tot = np.sum((values - np.mean(values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            return {
                'slope': slope,
                'r_squared': r_squared,
                'direction': 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'
            }

        except Exception as e:
            logger.error(f"Error analyzing trend: {e}")
            return {'slope': 0, 'r_squared': 0, 'direction': 'stable'}

    def _calculate_seasonal_pattern(self, historical_data: List[Dict]) -> Optional[Dict]:
        """计算季节性模式"""
        try:
            if len(historical_data) < 168:  # 至少需要一周的数据
                return None

            # 按小时分组
            hourly_values = defaultdict(list)
            for point in historical_data:
                time = datetime.fromisoformat(point['timestamp'])
                hourly_values[time.hour].append(point['value'])

            # 计算每小时统计
            hourly_stats = {}
            for hour, values in hourly_values.items():
                if len(values) >= 5:  # 至少5个样本
                    hourly_stats[hour] = {
                        'mean': statistics.mean(values),
                        'std': statistics.stdev(values) if len(values) > 1 else 1,
                        'min': min(values),
                        'max': max(values),
                        'count': len(values)
                    }

            # 按星期几分组
            weekly_values = defaultdict(list)
            for point in historical_data:
                time = datetime.fromisoformat(point['timestamp'])
                weekly_values[time.weekday()].append(point['value'])

            weekly_stats = {}
            for day, values in weekly_values.items():
                if len(values) >= 5:
                    weekly_stats[day] = {
                        'mean': statistics.mean(values),
                        'std': statistics.stdev(values) if len(values) > 1 else 1,
                        'count': len(values)
                    }

            return {
                'hourly': hourly_stats,
                'weekly': weekly_stats,
                'data_points': len(historical_data)
            }

        except Exception as e:
            logger.error(f"Error calculating seasonal pattern: {e}")
            return None

    def _get_correlated_metrics(self, metric_name: str) -> List[str]:
        """获取关联指标"""
        # 预定义的关联关系
        correlations = {
            'cpu_usage': ['memory_usage', 'api_response_time', 'load_average'],
            'memory_usage': ['cpu_usage', 'disk_usage', 'api_response_time'],
            'api_response_time': ['cpu_usage', 'memory_usage', 'active_users'],
            'error_rate': ['api_response_time', 'cpu_usage', 'memory_usage'],
            'disk_usage': ['memory_usage'],
            'ai_model_response_time': ['api_response_time', 'cpu_usage'],
            'ai_model_error_rate': ['error_rate', 'api_response_time']
        }

        return correlations.get(metric_name, [])

    def _get_recent_alerts(self, minutes: int = 10) -> Dict[str, Dict]:
        """获取最近的告警"""
        recent_alerts = {}
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        for metric_name, alerts in self.alert_history.items():
            for alert in reversed(alerts):  # 从最新的开始检查
                if alert['triggered_at'] >= cutoff_time:
                    recent_alerts[metric_name] = alert
                    break

        return recent_alerts

    def _is_suppressed(self, metric_name: str, timestamp: datetime) -> bool:
        """检查告警是否被抑制"""
        if metric_name not in self.suppression_rules:
            return False

        suppression_config = self.suppression_rules[metric_name]

        # 时间窗口抑制
        if 'cooldown_minutes' in suppression_config:
            recent_alerts = self.alert_history.get(metric_name, deque(maxlen=self.max_history_size))
            if recent_alerts:
                last_alert = recent_alerts[-1]
                if (timestamp - last_alert['triggered_at']).total_seconds() < suppression_config['cooldown_minutes'] * 60:
                    return True

        # 工作时间抑制
        if 'suppress_hours' in suppression_config:
            if timestamp.hour in suppression_config['suppress_hours']:
                return True

        return False

    def _get_historical_data(self, metric_name: str, lookback_hours: int = 48) -> List[Dict]:
        """获取历史数据"""
        # 这里应该从实际的数据源获取
        # 为了演示，返回模拟数据
        historical_data = []

        # 尝试从业务监控获取
        if hasattr(business_monitor, 'metrics'):
            business_metrics = [m for m in business_monitor.metrics if m.name == metric_name]
            for metric in business_metrics[-100:]:  # 最近100条
                historical_data.append({
                    'value': metric.value,
                    'timestamp': metric.timestamp.isoformat()
                })

        # 如果没有数据，生成模拟数据
        if not historical_data:
            base_value = 50
            for i in range(100):
                timestamp = datetime.utcnow() - timedelta(hours=lookback_hours) + timedelta(minutes=i * 30)
                value = base_value + np.sin(i * 0.1) * 10 + np.random.normal(0, 5)
                historical_data.append({
                    'value': max(0, value),
                    'timestamp': timestamp.isoformat()
                })

        return historical_data

    def _get_business_context(self, metric_name: str) -> Optional[Dict]:
        """获取业务上下文"""
        try:
            # 获取实时业务统计
            real_time_stats = business_monitor.get_real_time_stats()

            context = {
                'active_users': real_time_stats.get('current_active_users', 0),
                'requests_per_minute': real_time_stats.get('requests_per_minute', 0),
                'error_rate_percent': real_time_stats.get('error_rate_percent', 0),
                'current_response_time_ms': real_time_stats.get('current_response_time_ms', 0)
            }

            return context

        except Exception as e:
            logger.error(f"Error getting business context: {e}")
            return None

    def _get_system_context(self) -> Optional[Dict]:
        """获取系统上下文"""
        try:
            latest_metrics = system_monitor.get_latest_metrics()
            if not latest_metrics:
                return None

            return {
                'cpu_usage': latest_metrics.cpu['usage_percent'],
                'memory_usage': latest_metrics.memory['percent'],
                'disk_usage': latest_metrics.disk['percent'],
                'host_name': latest_metrics.host_name
            }

        except Exception as e:
            logger.error(f"Error getting system context: {e}")
            return None

    def _calculate_historical_stats(self, historical_data: List[Dict]) -> Dict:
        """计算历史统计"""
        if not historical_data:
            return {}

        values = [point['value'] for point in historical_data]

        return {
            'count': len(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'std': statistics.stdev(values) if len(values) > 1 else 0,
            'min': min(values),
            'max': max(values),
            'p95': np.percentile(values, 95),
            'p99': np.percentile(values, 99)
        }

    def _generate_composite_message(self, context: SmartAlertContext, results: List[Dict]) -> str:
        """生成复合告警消息"""
        if len(results) == 1:
            return results[0]['message']

        # 多个检测结果，生成综合消息
        types = [r['type'] for r in results]
        severity_counts = {}
        for result in results:
            severity = result['severity'].value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        max_severity = max(severity_counts.keys(), key=lambda x: {'critical': 3, 'warning': 2, 'info': 1}[x])

        message_parts = [
            f"智能告警: {context.metric_name} 出现多重异常",
            f"检测类型: {', '.join(types)}",
            f"严重程度: {max_severity}",
            f"当前值: {context.current_value}"
        ]

        return ' | '.join(message_parts)

    def _generate_recommendations(self, alert: SmartAlert, context: SmartAlertContext) -> List[str]:
        """生成处理建议"""
        recommendations = []

        # 基于告警类型生成建议
        if 'rule_based' in alert.contributing_factors:
            recommendations.append("检查告警规则阈值是否合理")

        if 'anomaly_based' in alert.contributing_factors:
            recommendations.append("分析异常模式，确认是否为系统问题")
            recommendations.append("检查最近的系统变更或配置修改")

        if 'trend_based' in alert.contributing_factors:
            recommendations.append("监控趋势变化，考虑容量规划")
            recommendations.append("分析趋势变化的原因")

        if 'seasonal_based' in alert.contributing_factors:
            recommendations.append("检查是否存在周期性业务影响")
            recommendations.append("调整告警阈值以适应季节性模式")

        if 'correlation_based' in alert.contributing_factors:
            recommendations.append("检查关联指标，排查系统性问题")
            recommendations.append("考虑是否存在级联故障")

        # 基于指标类型生成特定建议
        metric_specific_recommendations = {
            'cpu_usage': [
                "检查高CPU占用的进程",
                "考虑扩容或优化算法",
                "检查是否存在死循环或异常计算"
            ],
            'memory_usage': [
                "检查内存泄漏",
                "分析内存使用模式",
                "考虑增加内存或优化内存使用"
            ],
            'api_response_time': [
                "检查数据库查询性能",
                "分析API调用链路",
                "考虑增加缓存或优化代码"
            ],
            'error_rate': [
                "检查错误日志",
                "分析错误模式",
                "检查外部依赖状态"
            ]
        }

        if alert.metric_name in metric_specific_recommendations:
            recommendations.extend(metric_specific_recommendations[alert.metric_name])

        # 去重并限制数量
        unique_recommendations = list(set(recommendations))
        return unique_recommendations[:5]  # 最多返回5条建议

    def _record_alert_history(self, metric_name: str, alert: SmartAlert):
        """记录告警历史"""
        alert_record = {
            'metric_name': alert.metric_name,
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'confidence': alert.confidence,
            'message': alert.message,
            'triggered_at': alert.triggered_at,
            'contributing_factors': alert.contributing_factors
        }

        if metric_name not in self.alert_history:
            self.alert_history[metric_name] = deque(maxlen=self.max_history_size)

        self.alert_history[metric_name].append(alert_record)

    def get_smart_alerting_stats(self, hours: int = 24) -> Dict:
        """获取智能告警统计"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        total_alerts = 0
        alert_types = defaultdict(int)
        severity_counts = defaultdict(int)

        for metric_name, alerts in self.alert_history.items():
            for alert in alerts:
                if alert['triggered_at'] >= cutoff_time:
                    total_alerts += 1
                    alert_types[alert['alert_type']] += 1
                    severity_counts[alert['severity'].value] += 1

        return {
            'period_hours': hours,
            'total_alerts': total_alerts,
            'alert_types': dict(alert_types),
            'severity_distribution': dict(severity_counts),
            'monitored_metrics': len(self.alert_history),
            'correlation_rules_count': len(self.correlation_rules)
        }

# 全局智能告警实例
smart_alerting = SmartAlerting()