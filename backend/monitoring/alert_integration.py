"""
智能告警系统集成
将告警引擎、异常检测、智能策略和多渠道通知整合
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from backend.monitoring.alert_engine import alert_engine, AlertSeverity
from backend.monitoring.anomaly_detection import anomaly_detector
from backend.monitoring.smart_alerting import smart_alerting, SmartAlert
from backend.monitoring.notifications import notification_manager
from backend.monitoring.system_monitor import system_monitor
from backend.monitoring.business_monitor import business_monitor

logger = logging.getLogger(__name__)

@dataclass
class AlertEvaluationResult:
    """告警评估结果"""
    smart_alerts: List[SmartAlert]
    rule_alerts: List[Dict]
    anomaly_alerts: List[Dict]
    notifications_sent: Dict[str, bool]
    evaluation_time: datetime
    metrics_evaluated: List[str]

class IntegratedAlertSystem:
    """集成告警系统"""

    def __init__(self):
        self.enabled = True
        self.evaluation_interval = 30  # 秒
        self.running = False
        self.last_evaluation = None
        self.evaluation_history = []
        self.max_history_size = 1000

        # 配置
        self.auto_train_models = True
        self.model_training_interval_hours = 24
        self.min_samples_for_training = 500

    async def start_monitoring(self):
        """启动智能告警监控"""
        self.running = True
        logger.info("Integrated alert system started")

        # 加载默认告警规则
        from backend.monitoring.default_alert_rules import load_default_alert_rules, configure_suppression_rules
        load_default_alert_rules()
        configure_suppression_rules()

        # 添加通知处理器
        alert_engine.add_notification_handler(self._handle_alert_engine_notification)

        # 启动主监控循环
        await asyncio.gather(
            self._monitoring_loop(),
            self._model_training_loop(),
            self._system_health_check_loop()
        )

    def stop_monitoring(self):
        """停止智能告警监控"""
        self.running = False
        logger.info("Integrated alert system stopped")

    async def _monitoring_loop(self):
        """主监控循环"""
        while self.running:
            try:
                # 执行告警评估
                result = await self.evaluate_alerts()

                if result:
                    self.evaluation_history.append(result)
                    if len(self.evaluation_history) > self.max_history_size:
                        self.evaluation_history = self.evaluation_history[-self.max_history_size:]

                self.last_evaluation = datetime.utcnow()

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

            await asyncio.sleep(self.evaluation_interval)

    async def _model_training_loop(self):
        """模型训��循环"""
        while self.running:
            try:
                await self._train_anomaly_models()
            except Exception as e:
                logger.error(f"Error in model training loop: {e}")

            # 每天训练一次
            await asyncio.sleep(self.model_training_interval_hours * 3600)

    async def _system_health_check_loop(self):
        """系统健康检查循环"""
        while self.running:
            try:
                await self._check_system_health()
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

            # 每小时检查一次
            await asyncio.sleep(3600)

    async def evaluate_alerts(self) -> Optional[AlertEvaluationResult]:
        """执行告警评估"""
        start_time = datetime.utcnow()

        try:
            # 获取当前指标数据
            current_metrics = await self._collect_current_metrics()

            if not current_metrics:
                logger.warning("No current metrics available for alert evaluation")
                return None

            smart_alerts = []
            rule_alerts = []
            anomaly_alerts = []
            all_notifications = {}

            # 对每个指标进行智能告警评估
            for metric_name, metric_data in current_metrics.items():
                try:
                    # 智能告警评估
                    smart_alert = await smart_alerting.evaluate_smart_alert(
                        metric_name, metric_data['value'], metric_data['timestamp']
                    )

                    if smart_alert:
                        smart_alerts.append(smart_alert)

                        # 发送通知
                        channels = self._determine_notification_channels(smart_alert)
                        notification_results = await notification_manager.send_alert(
                            self._smart_alert_to_dict(smart_alert), channels
                        )

                        # 合并通知结果
                        for channel, result in notification_results.items():
                            all_notifications[f"{channel}_{metric_name}"] = result

                except Exception as e:
                    logger.error(f"Error evaluating alerts for {metric_name}: {e}")

            # 评估结果
            result = AlertEvaluationResult(
                smart_alerts=smart_alerts,
                rule_alerts=rule_alerts,
                anomaly_alerts=anomaly_alerts,
                notifications_sent=all_notifications,
                evaluation_time=start_time,
                metrics_evaluated=list(current_metrics.keys())
            )

            logger.info(f"Alert evaluation completed: {len(smart_alerts)} smart alerts, {len(all_notifications)} notifications sent")
            return result

        except Exception as e:
            logger.error(f"Error in alert evaluation: {e}")
            return None

    async def _collect_current_metrics(self) -> Dict[str, Dict]:
        """收集当前指标数据"""
        metrics = {}

        try:
            # 系统指标
            latest_system = system_monitor.get_latest_metrics()
            if latest_system:
                metrics['cpu_usage'] = {
                    'value': latest_system.cpu['usage_percent'],
                    'timestamp': latest_system.timestamp
                }
                metrics['memory_usage'] = {
                    'value': latest_system.memory['percent'],
                    'timestamp': latest_system.timestamp
                }
                metrics['disk_usage'] = {
                    'value': latest_system.disk['percent'],
                    'timestamp': latest_system.timestamp
                }

            # 业务指标
            real_time_stats = business_monitor.get_real_time_stats()
            if real_time_stats:
                metrics['active_users'] = {
                    'value': real_time_stats.get('current_active_users', 0),
                    'timestamp': datetime.utcnow()
                }
                metrics['requests_per_minute'] = {
                    'value': real_time_stats.get('requests_per_minute', 0),
                    'timestamp': datetime.utcnow()
                }
                metrics['error_rate'] = {
                    'value': real_time_stats.get('error_rate_percent', 0),
                    'timestamp': datetime.utcnow()
                }
                metrics['response_time'] = {
                    'value': real_time_stats.get('current_response_time_ms', 0) / 1000,  # 转换为秒
                    'timestamp': datetime.utcnow()
                }

            # API统计
            api_stats = business_monitor.get_api_stats(1)
            if api_stats and api_stats.get('total_requests', 0) > 0:
                metrics['api_response_time_avg'] = {
                    'value': api_stats.get('avg_response_time_ms', 0) / 1000,  # 转换为秒
                    'timestamp': datetime.utcnow()
                }
                metrics['api_success_rate'] = {
                    'value': api_stats.get('success_rate_percent', 100),
                    'timestamp': datetime.utcnow()
                }

            # AI模型统计
            ai_stats = business_monitor.get_ai_model_stats(1)
            if ai_stats and ai_stats.get('total_calls', 0) > 0:
                metrics['ai_model_response_time'] = {
                    'value': ai_stats.get('avg_response_time_s', 0),
                    'timestamp': datetime.utcnow()
                }
                metrics['ai_model_success_rate'] = {
                    'value': ai_stats.get('success_rate_percent', 100),
                    'timestamp': datetime.utcnow()
                }
                metrics['ai_cost_per_hour'] = {
                    'value': ai_stats.get('total_cost_usd', 0),
                    'timestamp': datetime.utcnow()
                }

        except Exception as e:
            logger.error(f"Error collecting current metrics: {e}")

        return metrics

    async def _handle_alert_engine_notification(self, alert_data: Dict):
        """处理告警引擎通知"""
        try:
            # 转换为智能告警格式
            channels = self._determine_notification_channels_from_severity(alert_data.get('severity', 'warning'))

            # 发送通知
            await notification_manager.send_alert(alert_data, channels)

            logger.info(f"Alert engine notification handled: {alert_data.get('rule_name', 'Unknown rule')}")

        except Exception as e:
            logger.error(f"Error handling alert engine notification: {e}")

    def _determine_notification_channels(self, smart_alert: SmartAlert) -> List[str]:
        """根据智能告警确定通知渠道"""
        channels = []

        # 基于严重程度确定渠道
        if smart_alert.severity == AlertSeverity.CRITICAL:
            channels.extend(['email', 'slack', 'webhook'])
            # 关键告警可以考虑发送短信
            # if self._is_business_hours():
            #     channels.append('sms')
        elif smart_alert.severity == AlertSeverity.WARNING:
            channels.extend(['email', 'slack'])
        else:  # INFO
            channels.extend(['slack'])

        # 基于置信度调整
        if smart_alert.confidence < 0.7:
            # 低置信度告警只发送到Slack
            channels = ['slack']

        # 基于告警类型调整
        if 'anomaly_based' in smart_alert.alert_type:
            # 异常检��告警需要更多渠道确认
            if smart_alert.severity == AlertSeverity.WARNING:
                channels.append('email')

        # 去重
        return list(set(channels))

    def _determine_notification_channels_from_severity(self, severity: str) -> List[str]:
        """根据严重程度确定通知渠道（用于规则告警）"""
        severity_mapping = {
            'critical': ['email', 'slack', 'webhook'],
            'warning': ['email', 'slack'],
            'info': ['slack']
        }
        return severity_mapping.get(severity, ['slack'])

    def _is_business_hours(self) -> bool:
        """检查是否为工作时间"""
        now = datetime.utcnow()
        return 9 <= now.hour <= 17 and now.weekday() < 5

    def _smart_alert_to_dict(self, smart_alert: SmartAlert) -> Dict:
        """将智能告警转换为字典格式"""
        return {
            'rule_name': smart_alert.message,
            'metric_name': smart_alert.metric_name,
            'message': smart_alert.message,
            'severity': smart_alert.severity.value,
            'triggered_at': smart_alert.triggered_at.isoformat(),
            'context': {
                'alert_type': smart_alert.alert_type,
                'confidence': smart_alert.confidence,
                'contributing_factors': smart_alert.contributing_factors,
                'recommendations': smart_alert.recommendations
            }
        }

    async def _train_anomaly_models(self):
        """训练异常检测模型"""
        if not self.auto_train_models:
            return

        try:
            logger.info("Starting anomaly model training...")

            # 收集历史数据
            training_data = await self._collect_training_data()

            if not training_data:
                logger.warning("No training data available")
                return

            # 训练模型
            results = anomaly_detector.retrain_all_models(training_data)

            trained_count = sum(1 for success in results.values() if success)
            total_count = len(results)

            logger.info(f"Model training completed: {trained_count}/{total_count} models trained")

        except Exception as e:
            logger.error(f"Error in model training: {e}")

    async def _collect_training_data(self) -> Dict[str, List[Dict]]:
        """收集训练数据"""
        training_data = {}

        try:
            # 收集过去7天的数据
            hours = 24 * 7

            # 从业务监控获取数据
            business_metrics = business_monitor.metrics
            for metric in business_metrics:
                metric_name = metric.name
                if metric_name not in training_data:
                    training_data[metric_name] = []

                # 转换为训练数据格式
                training_data[metric_name].append({
                    'value': metric.value,
                    'timestamp': metric.timestamp.isoformat()
                })

            # 从系统监控获取数据
            system_history = system_monitor.get_metrics_history(hours)
            for metrics in system_history:
                # CPU使用率
                if 'cpu_usage' not in training_data:
                    training_data['cpu_usage'] = []
                training_data['cpu_usage'].append({
                    'value': metrics.cpu['usage_percent'],
                    'timestamp': metrics.timestamp.isoformat()
                })

                # 内存使用率
                if 'memory_usage' not in training_data:
                    training_data['memory_usage'] = []
                training_data['memory_usage'].append({
                    'value': metrics.memory['percent'],
                    'timestamp': metrics.timestamp.isoformat()
                })

                # 磁盘使用率
                if 'disk_usage' not in training_data:
                    training_data['disk_usage'] = []
                training_data['disk_usage'].append({
                    'value': metrics.disk['percent'],
                    'timestamp': metrics.timestamp.isoformat()
                })

        except Exception as e:
            logger.error(f"Error collecting training data: {e}")

        # 过滤数据量足够的指标
        filtered_data = {}
        for metric_name, data in training_data.items():
            if len(data) >= self.min_samples_for_training:
                filtered_data[metric_name] = data
                logger.info(f"Collected {len(data)} training samples for {metric_name}")
            else:
                logger.warning(f"Insufficient training data for {metric_name}: {len(data)} < {self.min_samples_for_training}")

        return filtered_data

    async def _check_system_health(self):
        """检查系统健康状态"""
        try:
            health_status = await self._get_system_health_status()

            # 如果系统不健康，发送健康告警
            if health_status['overall_status'] != 'healthy':
                alert_data = {
                    'rule_name': 'System Health Check',
                    'metric_name': 'system_health',
                    'message': f"System health status: {health_status['overall_status']}",
                    'severity': 'critical' if health_status['overall_status'] == 'unhealthy' else 'warning',
                    'triggered_at': datetime.utcnow().isoformat(),
                    'context': health_status
                }

                await notification_manager.send_alert(alert_data, ['email', 'slack'])

        except Exception as e:
            logger.error(f"Error in system health check: {e}")

    async def _get_system_health_status(self) -> Dict:
        """获取系统健康状态"""
        try:
            # 检查各个组件状态
            checks = {}

            # 检查监控系统
            checks['monitoring'] = {
                'status': 'healthy' if self.running else 'stopped',
                'last_evaluation': self.last_evaluation.isoformat() if self.last_evaluation else None
            }

            # 检查告警引擎
            active_alerts = alert_engine.get_active_alerts()
            checks['alert_engine'] = {
                'status': 'healthy',
                'active_alerts_count': len(active_alerts),
                'rules_count': len(alert_engine.rules)
            }

            # 检查异常检测模型
            trained_models = anomaly_detector.list_trained_models()
            checks['anomaly_detection'] = {
                'status': 'healthy' if len(trained_models) > 0 else 'warning',
                'trained_models_count': len(trained_models)
            }

            # 检查通知系统
            channel_status = notification_manager.get_channel_status()
            enabled_channels = [name for name, status in channel_status.items() if status['enabled']]
            checks['notifications'] = {
                'status': 'healthy' if len(enabled_channels) > 0 else 'warning',
                'enabled_channels_count': len(enabled_channels),
                'channels': channel_status
            }

            # 综合健康状态
            statuses = [check['status'] for check in checks.values()]
            if 'unhealthy' in statuses:
                overall_status = 'unhealthy'
            elif 'warning' in statuses or 'stopped' in statuses:
                overall_status = 'warning'
            else:
                overall_status = 'healthy'

            return {
                'overall_status': overall_status,
                'checks': checks,
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting system health status: {e}")
            return {
                'overall_status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    def get_system_status(self) -> Dict:
        """获取系统状态"""
        return {
            'enabled': self.enabled,
            'running': self.running,
            'evaluation_interval': self.evaluation_interval,
            'last_evaluation': self.last_evaluation.isoformat() if self.last_evaluation else None,
            'evaluation_history_size': len(self.evaluation_history),
            'alert_rules_count': len(alert_engine.rules),
            'active_alerts_count': len(alert_engine.get_active_alerts()),
            'trained_models_count': len(anomaly_detector.list_trained_models()),
            'enabled_notification_channels': len([
                name for name, status in notification_manager.get_channel_status().items()
                if status['enabled']
            ])
        }

    def get_recent_alerts(self, hours: int = 24) -> Dict:
        """获取最近的告警"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # 获取智能告警
        smart_alerts = []
        for result in self.evaluation_history:
            if result.evaluation_time >= cutoff_time:
                smart_alerts.extend(result.smart_alerts)

        # 获取规则告警
        rule_alerts = alert_engine.get_alert_history(hours)

        return {
            'period_hours': hours,
            'smart_alerts_count': len(smart_alerts),
            'rule_alerts_count': len(rule_alerts),
            'smart_alerts': [
                {
                    'metric_name': alert.metric_name,
                    'severity': alert.severity.value,
                    'message': alert.message,
                    'triggered_at': alert.triggered_at.isoformat(),
                    'alert_type': alert.alert_type,
                    'confidence': alert.confidence
                }
                for alert in smart_alerts
            ],
            'rule_alerts': [
                {
                    'rule_id': incident.rule_id,
                    'severity': incident.severity.value,
                    'message': incident.message,
                    'triggered_at': incident.triggered_at.isoformat()
                }
                for incident in rule_alerts
            ]
        }

# 全局集成告警系统实例
integrated_alert_system = IntegratedAlertSystem()