"""
智能告警引��
支持多种告警条件、持续时间检查、告警抑制等功能
"""
import asyncio
import json
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertStatus(Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

@dataclass
class AlertCondition:
    """告警条件定义"""
    id: str
    name: str
    metric_name: str
    operator: str  # '>', '<', '>=', '<=', '=', '!=', 'in', 'not_in'
    threshold: Any
    duration_minutes: int = 5
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True
    tags: Optional[Dict[str, str]] = None
    description: Optional[str] = None

@dataclass
class AlertIncident:
    """告警事件记录"""
    id: str
    rule_id: str
    status: AlertStatus
    trigger_value: Any
    severity: AlertSeverity
    message: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    notes: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    notification_sent: bool = False

class AlertEngine:
    """告警引擎核心"""

    def __init__(self):
        self.rules: Dict[str, AlertCondition] = {}
        self.incidents: Dict[str, AlertIncident] = {}  # rule_id -> incident
        self.active_conditions: Dict[str, datetime] = {}  # rule_id -> start_time
        self.notification_handlers: List[Callable] = []
        self.suppression_rules: Dict[str, Dict] = {}  # rule_id -> suppression_config
        self.evaluation_history: List[Dict] = []
        self.max_history_size = 1000

    def add_rule(self, condition: AlertCondition):
        """添加告警���则"""
        self.rules[condition.id] = condition
        logger.info(f"Added alert rule: {condition.name} ({condition.id})")

    def remove_rule(self, rule_id: str):
        """移除告警规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            # 清理相关告警事件
            if rule_id in self.incidents:
                self.incidents[rule_id].status = AlertStatus.RESOLVED
                self.incidents[rule_id].resolved_at = datetime.utcnow()
            if rule_id in self.active_conditions:
                del self.active_conditions[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")

    def enable_rule(self, rule_id: str):
        """启用告警规则"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            logger.info(f"Enabled alert rule: {rule_id}")

    def disable_rule(self, rule_id: str):
        """禁用告警规则"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            logger.info(f"Disabled alert rule: {rule_id}")

    def add_notification_handler(self, handler: Callable):
        """添加通知处理器"""
        self.notification_handlers.append(handler)

    def add_suppression_rule(self, rule_id: str, config: Dict):
        """添加告警抑制规则"""
        self.suppression_rules[rule_id] = config

    async def evaluate_metric(self, metric_name: str, value: Any, timestamp: datetime = None, context: Dict = None):
        """评估指标是否触发告警"""
        if timestamp is None:
            timestamp = datetime.utcnow()

        # 记录评估历史
        evaluation_record = {
            'timestamp': timestamp.isoformat(),
            'metric_name': metric_name,
            'value': value,
            'triggered_rules': []
        }

        # 检查所有相关规则
        for rule_id, condition in self.rules.items():
            if not condition.enabled or condition.metric_name != metric_name:
                continue

            try:
                # 评估条件
                is_triggered = self._evaluate_condition(value, condition)

                if is_triggered:
                    await self._handle_condition_trigger(rule_id, condition, value, timestamp, context)
                    evaluation_record['triggered_rules'].append(rule_id)
                else:
                    await self._handle_condition_resolve(rule_id, condition, timestamp)

            except Exception as e:
                logger.error(f"Error evaluating rule {rule_id}: {e}")

        # 保存评估历史
        self.evaluation_history.append(evaluation_record)
        if len(self.evaluation_history) > self.max_history_size:
            self.evaluation_history = self.evaluation_history[-self.max_history_size:]

    def _evaluate_condition(self, value: Any, condition: AlertCondition) -> bool:
        """评估条件是否满足"""
        operators = {
            '>': lambda a, b: float(a) > float(b),
            '<': lambda a, b: float(a) < float(b),
            '>=': lambda a, b: float(a) >= float(b),
            '<=': lambda a, b: float(a) <= float(b),
            '=': lambda a, b: a == b,
            '!=': lambda a, b: a != b,
            'in': lambda a, b: a in b,
            'not_in': lambda a, b: a not in b,
            'contains': lambda a, b: str(b) in str(a),
            'not_contains': lambda a, b: str(b) not in str(a),
            'regex': lambda a, b: bool(re.search(str(b), str(a))),
        }

        operator_func = operators.get(condition.operator)
        if not operator_func:
            logger.warning(f"Unknown operator: {condition.operator}")
            return False

        try:
            return operator_func(value, condition.threshold)
        except Exception as e:
            logger.error(f"Error evaluating condition {condition.id}: {e}")
            return False

    async def _handle_condition_trigger(self, rule_id: str, condition: AlertCondition,
                                      value: Any, timestamp: datetime, context: Dict = None):
        """处理条件触发"""
        # 检查抑制规则
        if self._is_suppressed(rule_id, timestamp):
            return

        # 记录触发时间
        if rule_id not in self.active_conditions:
            self.active_conditions[rule_id] = timestamp
            return

        # 检查持续时间
        trigger_duration = timestamp - self.active_conditions[rule_id]
        if trigger_duration >= timedelta(minutes=condition.duration_minutes):
            await self._create_alert_incident(rule_id, condition, value, timestamp, context)

    async def _handle_condition_resolve(self, rule_id: str, condition: AlertCondition, timestamp: datetime):
        """处理条件解决"""
        if rule_id in self.active_conditions:
            del self.active_conditions[rule_id]

        # 解决告警事件
        if rule_id in self.incidents and self.incidents[rule_id].status == AlertStatus.ACTIVE:
            incident = self.incidents[rule_id]
            incident.status = AlertStatus.RESOLVED
            incident.resolved_at = timestamp
            logger.info(f"Resolved alert incident: {rule_id}")

    async def _create_alert_incident(self, rule_id: str, condition: AlertCondition,
                                   value: Any, timestamp: datetime, context: Dict = None):
        """创建告警事件"""
        # 检查是否已存在活跃告警
        if rule_id in self.incidents and self.incidents[rule_id].status == AlertStatus.ACTIVE:
            return  # 已存在活跃告警，不重复创建

        # 生成告警消息
        message = self._generate_alert_message(condition, value, context)

        # 创建告警事件
        incident = AlertIncident(
            id=f"alert_{timestamp.strftime('%Y%m%d_%H%M%S')}_{rule_id}",
            rule_id=rule_id,
            status=AlertStatus.ACTIVE,
            trigger_value=value,
            severity=condition.severity,
            message=message,
            triggered_at=timestamp,
            context=context or {}
        )

        self.incidents[rule_id] = incident
        logger.warning(f"Alert triggered: {message}")

        # 发送通知
        await self._send_notifications(incident)

    def _generate_alert_message(self, condition: AlertCondition, value: Any, context: Dict = None) -> str:
        """生成告警消息"""
        operator_symbols = {
            '>': '>', '<': '<', '>=': '>=', '<=': '<=', '=': '=', '!=': '!=',
            'in': 'in', 'not_in': 'not in', 'contains': 'contains',
            'not_contains': 'not contains', 'regex': 'matches'
        }

        operator_symbol = operator_symbols.get(condition.operator, condition.operator)

        base_message = f"{condition.name}: {condition.metric_name} {operator_symbol} {condition.threshold} (当前值: {value})"

        if condition.description:
            base_message = f"{condition.description} - {base_message}"

        return base_message

    async def _send_notifications(self, incident: AlertIncident):
        """发送告警通知"""
        if incident.notification_sent:
            return

        notification_data = {
            'incident_id': incident.id,
            'rule_id': incident.rule_id,
            'severity': incident.severity.value,
            'message': incident.message,
            'trigger_value': incident.trigger_value,
            'triggered_at': incident.triggered_at.isoformat(),
            'context': incident.context
        }

        # 并行发送所有通知
        notification_tasks = []
        for handler in self.notification_handlers:
            task = asyncio.create_task(self._safe_send_notification(handler, notification_data))
            notification_tasks.append(task)

        if notification_tasks:
            await asyncio.gather(*notification_tasks, return_exceptions=True)

        incident.notification_sent = True

    async def _safe_send_notification(self, handler: Callable, notification_data: Dict):
        """安全发送通知"""
        try:
            await handler(notification_data)
        except Exception as e:
            logger.error(f"Failed to send notification via {handler.__name__}: {e}")

    def _is_suppressed(self, rule_id: str, timestamp: datetime) -> bool:
        """检查告警是否被抑制"""
        if rule_id not in self.suppression_rules:
            return False

        suppression_config = self.suppression_rules[rule_id]

        # 时间窗口抑制
        if 'time_window_minutes' in suppression_config:
            window_minutes = suppression_config['time_window_minutes']

            # 检查最近是否有相同告警
            for incident in self.incidents.values():
                if (incident.rule_id == rule_id and
                    incident.status == AlertStatus.ACTIVE and
                    (timestamp - incident.triggered_at).total_seconds() < window_minutes * 60):
                    return True

        # 时间段抑制
        if 'suppress_hours' in suppression_config:
            suppress_hours = suppression_config['suppress_hours']
            if timestamp.hour in suppress_hours:
                return True

        # 工作日/周末抑制
        if 'suppress_weekends' in suppression_config and suppression_config['suppress_weekends']:
            if timestamp.weekday() >= 5:  # 周六、周日
                return True

        return False

    async def acknowledge_alert(self, incident_id: str, acknowledged_by: str, notes: str = None):
        """确认告警"""
        for incident in self.incidents.values():
            if incident.id == incident_id and incident.status == AlertStatus.ACTIVE:
                incident.acknowledged_at = datetime.utcnow()
                incident.acknowledged_by = acknowledged_by
                incident.notes = notes
                logger.info(f"Alert acknowledged: {incident_id} by {acknowledged_by}")
                return True
        return False

    async def resolve_alert(self, incident_id: str, resolved_by: str, notes: str = None):
        """手动解决告警"""
        for incident in self.incidents.values():
            if incident.id == incident_id and incident.status == AlertStatus.ACTIVE:
                incident.status = AlertStatus.RESOLVED
                incident.resolved_at = datetime.utcnow()
                incident.notes = notes
                logger.info(f"Alert resolved: {incident_id} by {resolved_by}")
                return True
        return False

    def get_active_alerts(self, severity: AlertSeverity = None) -> List[AlertIncident]:
        """获取活跃告警"""
        alerts = [incident for incident in self.incidents.values() if incident.status == AlertStatus.ACTIVE]

        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]

        return sorted(alerts, key=lambda x: x.triggered_at, reverse=True)

    def get_alert_history(self, hours: int = 24) -> List[AlertIncident]:
        """获取告警历史"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            incident for incident in self.incidents.values()
            if incident.triggered_at >= cutoff_time
        ]

    def get_rules_status(self) -> Dict[str, Dict]:
        """获取规则状态"""
        return {
            rule_id: {
                'name': rule.name,
                'enabled': rule.enabled,
                'severity': rule.severity.value,
                'metric_name': rule.metric_name,
                'current_status': 'active' if rule_id in self.active_conditions else 'normal',
                'active_since': self.active_conditions.get(rule_id).isoformat() if rule_id in self.active_conditions else None,
                'last_triggered': None
            }
            for rule_id, rule in self.rules.items()
        }

    def get_evaluation_stats(self, hours: int = 1) -> Dict:
        """获取评估统计"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_evaluations = [
            eval for eval in self.evaluation_history
            if datetime.fromisoformat(eval['timestamp']) >= cutoff_time
        ]

        total_evaluations = len(recent_evaluations)
        triggered_evaluations = len([eval for eval in recent_evaluations if eval['triggered_rules']])

        # 统计各指标的触发次数
        metric_triggers = defaultdict(int)
        for eval in recent_evaluations:
            for rule_id in eval['triggered_rules']:
                if rule_id in self.rules:
                    metric_triggers[self.rules[rule_id].metric_name] += 1

        return {
            'period_hours': hours,
            'total_evaluations': total_evaluations,
            'triggered_evaluations': triggered_evaluations,
            'trigger_rate_percent': (triggered_evaluations / total_evaluations * 100) if total_evaluations > 0 else 0,
            'metric_trigger_counts': dict(metric_triggers),
            'active_alerts_count': len(self.get_active_alerts())
        }

    def export_incidents(self, hours: int = 24) -> List[Dict]:
        """导出告警事件数据"""
        incidents = self.get_alert_history(hours)
        return [
            {
                'id': incident.id,
                'rule_id': incident.rule_id,
                'status': incident.status.value,
                'severity': incident.severity.value,
                'message': incident.message,
                'trigger_value': incident.trigger_value,
                'triggered_at': incident.triggered_at.isoformat(),
                'resolved_at': incident.resolved_at.isoformat() if incident.resolved_at else None,
                'acknowledged_at': incident.acknowledged_at.isoformat() if incident.acknowledged_at else None,
                'acknowledged_by': incident.acknowledged_by,
                'notes': incident.notes,
                'context': incident.context
            }
            for incident in incidents
        ]

# 全局告警引擎实例
alert_engine = AlertEngine()