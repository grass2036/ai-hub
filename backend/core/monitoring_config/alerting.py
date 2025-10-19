"""
生产环境告警系统
Week 6 Day 4: 系统监控和日志配置

提供智能告警规则、通知渠道和升级策略
"""

import asyncio
import smtplib
import json
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import jinja2
import redis
from abc import ABC, abstractmethod

class AlertSeverity(Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

class NotificationChannel(Enum):
    """通知渠道"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    DINGTALK = "dingtalk"
    WECHAT = "wechat"

@dataclass
class AlertRule:
    """告警规则"""
    id: str
    name: str
    description: str
    severity: AlertSeverity
    condition: str  # 告警条件表达式
    threshold: float
    time_window: int  # 时间窗口（秒）
    evaluation_interval: int  # 评估间隔（秒）
    enabled: bool = True
    tags: List[str] = None
    notification_channels: List[NotificationChannel] = None
    escalation_policy: str = None
    cooldown_period: int = 300  # 冷却期（秒）

@dataclass
class Alert:
    """告警实例"""
    id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    details: Dict[str, Any]
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class NotificationConfig:
    """通知配置"""
    channel: NotificationChannel
    config: Dict[str, Any]
    enabled: bool = True
    rate_limit: int = 0  # 速率限制（每分钟最大通知数）

class EscalationLevel:
    """升级级别"""
    def __init__(self, level: int, delay_minutes: int, channels: List[NotificationChannel]):
        self.level = level
        self.delay_minutes = delay_minutes
        self.channels = channels

class EscalationPolicy:
    """升级策略"""
    def __init__(self, name: str, levels: List[EscalationLevel]):
        self.name = name
        self.levels = levels

class NotificationProvider(ABC):
    """通知提供者基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', True)

    @abstractmethod
    async def send_notification(self, alert: Alert, message: str) -> bool:
        """发送通知"""
        pass

class EmailNotificationProvider(NotificationProvider):
    """邮件通知提供者"""

    async def send_notification(self, alert: Alert, message: str) -> bool:
        """发送邮件通知"""
        try:
            smtp_config = self.config['smtp']
            recipients = self.config.get('recipients', [])

            if not recipients:
                return False

            # 创建邮件
            msg = MimeMultipart()
            msg['From'] = smtp_config['from_email']
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.rule_name}"

            # 邮件内容
            body = self._render_email_template(alert, message)
            msg.attach(MimeText(body, 'html', 'utf-8'))

            # 发送邮件
            server = smtplib.SMTP(smtp_config['host'], smtp_config['port'])
            if smtp_config.get('use_tls', True):
                server.starttls()
            if 'username' in smtp_config and 'password' in smtp_config:
                server.login(smtp_config['username'], smtp_config['password'])

            server.send_message(msg)
            server.quit()

            logging.info(f"Email notification sent for alert {alert.id}")
            return True

        except Exception as e:
            logging.error(f"Failed to send email notification: {str(e)}")
            return False

    def _render_email_template(self, alert: Alert, message: str) -> str:
        """渲染邮件模板"""
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>AI Hub 告警通知</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #f8f9fa; padding: 15px; border-radius: 5px; }
                .critical { border-left: 4px solid #dc3545; }
                .error { border-left: 4px solid #fd7e14; }
                .warning { border-left: 4px solid #ffc107; }
                .info { border-left: 4px solid #17a2b8; }
                .content { margin-top: 20px; }
                .details { background-color: #f8f9fa; padding: 10px; margin-top: 10px; }
                .footer { margin-top: 20px; font-size: 12px; color: #6c757d; }
            </style>
        </head>
        <body>
            <div class="header {{ severity }}">
                <h2>🚨 {{ severity.upper() }} 告警</h2>
                <h3>{{ rule_name }}</h3>
            </div>

            <div class="content">
                <p><strong>告警时间:</strong> {{ triggered_at }}</p>
                <p><strong>告警ID:</strong> {{ alert_id }}</p>
                <p><strong>消息:</strong> {{ message }}</p>

                <div class="details">
                    <h4>详细信息:</h4>
                    <pre>{{ details_json }}</pre>
                </div>
            </div>

            <div class="footer">
                <p>此邮件由 AI Hub 监控系统自动发送</p>
                <p>如需查看详情，请登录控制台</p>
            </div>
        </body>
        </html>
        """

        template = jinja2.Template(template_str)
        return template.render(
            severity=alert.severity.value,
            rule_name=alert.rule_name,
            triggered_at=alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S'),
            alert_id=alert.id,
            message=message,
            details_json=json.dumps(alert.details, indent=2, ensure_ascii=False)
        )

class SlackNotificationProvider(NotificationProvider):
    """Slack通知提供者"""

    async def send_notification(self, alert: Alert, message: str) -> bool:
        """发送Slack通知"""
        try:
            webhook_url = self.config['webhook_url']
            channel = self.config.get('channel', '#alerts')

            # 构建Slack消息
            slack_message = {
                "channel": channel,
                "username": "AI Hub Monitor",
                "icon_emoji": self._get_emoji_for_severity(alert.severity),
                "attachments": [
                    {
                        "color": self._get_color_for_severity(alert.severity),
                        "title": f"[{alert.severity.value.upper()}] {alert.rule_name}",
                        "text": message,
                        "fields": [
                            {
                                "title": "告警ID",
                                "value": alert.id,
                                "short": True
                            },
                            {
                                "title": "触发时间",
                                "value": alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S'),
                                "short": True
                            },
                            {
                                "title": "状态",
                                "value": alert.status.value,
                                "short": True
                            }
                        ],
                        "footer": "AI Hub Monitoring",
                        "ts": int(alert.triggered_at.timestamp())
                    }
                ]
            }

            # 如果有详细信息，添加到附件
            if alert.details:
                slack_message["attachments"][0]["fields"].append({
                    "title": "详细信息",
                    "value": f"```{json.dumps(alert.details, indent=2, ensure_ascii=False)}```",
                    "short": False
                })

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=slack_message) as response:
                    if response.status == 200:
                        logging.info(f"Slack notification sent for alert {alert.id}")
                        return True
                    else:
                        logging.error(f"Slack notification failed: {response.status}")
                        return False

        except Exception as e:
            logging.error(f"Failed to send Slack notification: {str(e)}")
            return False

    def _get_emoji_for_severity(self, severity: AlertSeverity) -> str:
        """根据严重级别获取emoji"""
        emoji_map = {
            AlertSeverity.INFO: ":information_source:",
            AlertSeverity.WARNING: ":warning:",
            AlertSeverity.ERROR: ":x:",
            AlertSeverity.CRITICAL: ":rotating_light:"
        }
        return emoji_map.get(severity, ":warning:")

    def _get_color_for_severity(self, severity: AlertSeverity) -> str:
        """根据严重级别获取颜色"""
        color_map = {
            AlertSeverity.INFO: "#17a2b8",
            AlertSeverity.WARNING: "#ffc107",
            AlertSeverity.ERROR: "#fd7e14",
            AlertSeverity.CRITICAL: "#dc3545"
        }
        return color_map.get(severity, "#ffc107")

class WebhookNotificationProvider(NotificationProvider):
    """Webhook通知提供者"""

    async def send_notification(self, alert: Alert, message: str) -> bool:
        """发送Webhook通知"""
        try:
            webhook_url = self.config['url']
            headers = self.config.get('headers', {})
            method = self.config.get('method', 'POST')

            payload = {
                "alert": {
                    "id": alert.id,
                    "rule_id": alert.rule_id,
                    "rule_name": alert.rule_name,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "message": message,
                    "details": alert.details,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "tags": alert.tags,
                    "metadata": alert.metadata
                },
                "timestamp": datetime.now().isoformat()
            }

            # 添加自定义字段
            if 'custom_fields' in self.config:
                payload.update(self.config['custom_fields'])

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status in [200, 201, 204]:
                        logging.info(f"Webhook notification sent for alert {alert.id}")
                        return True
                    else:
                        logging.error(f"Webhook notification failed: {response.status}")
                        return False

        except Exception as e:
            logging.error(f"Failed to send webhook notification: {str(e)}")
            return False

class DingTalkNotificationProvider(NotificationProvider):
    """钉钉通知提供者"""

    async def send_notification(self, alert: Alert, message: str) -> bool:
        """发送钉钉通知"""
        try:
            webhook_url = self.config['webhook_url']
            secret = self.config.get('secret')

            # 构建钉钉消息
            dingtalk_message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"AI Hub 告警 - {alert.rule_name}",
                    "text": self._render_dingtalk_message(alert, message)
                }
            }

            # 如果有密钥，添加签名
            if secret:
                import hmac
                import hashlib
                import base64
                import urllib.parse

                timestamp = str(round(datetime.now().timestamp() * 1000))
                secret_enc = secret.encode('utf-8')
                string_to_sign = f'{timestamp}\n{secret}'
                string_to_sign_enc = string_to_sign.encode('utf-8')
                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

                webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=dingtalk_message) as response:
                    result = await response.json()
                    if result.get('errcode') == 0:
                        logging.info(f"DingTalk notification sent for alert {alert.id}")
                        return True
                    else:
                        logging.error(f"DingTalk notification failed: {result}")
                        return False

        except Exception as e:
            logging.error(f"Failed to send DingTalk notification: {str(e)}")
            return False

    def _render_dingtalk_message(self, alert: Alert, message: str) -> str:
        """渲染钉钉消息"""
        severity_emoji = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.CRITICAL: "🚨"
        }

        return f"""
## {severity_emoji.get(alert.severity, '⚠️')} {alert.rule_name}

**告警级别**: {alert.severity.value.upper()}

**告警信息**: {message}

**告警时间**: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}

**告警ID**: {alert.id}

**详细信息**:
```json
{json.dumps(alert.details, indent=2, ensure_ascii=False)}
```

---
*AI Hub 监控系统自动发送*
        """.strip()

class AlertManager:
    """告警管理器"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_providers: Dict[NotificationChannel, NotificationProvider] = {}
        self.escalation_policies: Dict[str, EscalationPolicy] = {}
        self.is_running = False
        self._evaluation_loop = None

        # 初始化通知提供者
        self._init_default_providers()

        # 初始化默认升级策略
        self._init_default_escalation_policies()

    def _init_default_providers(self) -> None:
        """初始化默认通知提供者"""
        # 这些提供者需要在使用时配置
        self.notification_providers = {
            NotificationChannel.EMAIL: None,
            NotificationChannel.SLACK: None,
            NotificationChannel.WEBHOOK: None,
            NotificationChannel.DINGTALK: None
        }

    def _init_default_escalation_policies(self) -> None:
        """初始化默认升级策略"""
        # 默认升级策略
        default_policy = EscalationPolicy(
            name="default",
            levels=[
                EscalationLevel(1, 0, [NotificationChannel.EMAIL]),  # 立即邮件通知
                EscalationLevel(2, 15, [NotificationChannel.SLACK]),  # 15分钟后Slack通知
                EscalationLevel(3, 30, [NotificationChannel.SLACK, NotificationChannel.WEBHOOK]),  # 30分钟后多重通知
            ]
        )
        self.escalation_policies["default"] = default_policy

        # 紧急升级策略
        urgent_policy = EscalationPolicy(
            name="urgent",
            levels=[
                EscalationLevel(1, 0, [NotificationChannel.EMAIL, NotificationChannel.SLACK]),  # 立即多重通知
                EscalationLevel(2, 5, [NotificationChannel.WEBHOOK]),  # 5分钟后Webhook通知
                EscalationLevel(3, 10, [NotificationChannel.DINGTALK]),  # 10分钟后钉钉通知
            ]
        )
        self.escalation_policies["urgent"] = urgent_policy

    def register_notification_provider(self, channel: NotificationChannel, provider: NotificationProvider) -> None:
        """注册通知提供者"""
        self.notification_providers[channel] = provider

    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        self.rules[rule.id] = rule
        logging.info(f"Alert rule added: {rule.name}")

    def remove_rule(self, rule_id: str) -> None:
        """移除告警规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logging.info(f"Alert rule removed: {rule_id}")

    def get_rules(self) -> List[AlertRule]:
        """获取所有规则"""
        return list(self.rules.values())

    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        return self.alert_history[-limit:]

    async def start_evaluation(self) -> None:
        """启动告警评估"""
        if self.is_running:
            return

        self.is_running = True
        self._evaluation_loop = asyncio.create_task(self._evaluation_loop_task())
        logging.info("Alert evaluation started")

    async def stop_evaluation(self) -> None:
        """停止告警评估"""
        self.is_running = False
        if self._evaluation_loop:
            self._evaluation_loop.cancel()
            try:
                await self._evaluation_loop
            except asyncio.CancelledError:
                pass
        logging.info("Alert evaluation stopped")

    async def _evaluation_loop_task(self) -> None:
        """告警评估循环"""
        while self.is_running:
            try:
                await self._evaluate_all_rules()
                await asyncio.sleep(30)  # 每30秒评估一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in alert evaluation loop: {str(e)}")
                await asyncio.sleep(30)

    async def _evaluate_all_rules(self) -> None:
        """评估所有规则"""
        for rule in self.rules.values():
            if not rule.enabled:
                continue

            try:
                await self._evaluate_rule(rule)
            except Exception as e:
                logging.error(f"Error evaluating rule {rule.name}: {str(e)}")

    async def _evaluate_rule(self, rule: AlertRule) -> None:
        """评估单个规则"""
        # 这里需要根据规则条件获取相应的指标数据
        # 示例实现，实际应该根据规则条件查询相应的监控系统
        metric_value = await self._get_metric_value(rule)

        if metric_value is None:
            return

        # 检查是否触发告警
        is_triggered = self._check_condition(metric_value, rule)

        alert_id = f"{rule.id}_{int(datetime.now().timestamp())}"

        if is_triggered:
            # 检查是否已有活跃告警
            existing_alert = self._get_existing_alert(rule.id)
            if existing_alert:
                # 更新现有告警
                await self._update_alert(existing_alert, metric_value)
            else:
                # 创建新告警
                alert = Alert(
                    id=alert_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    status=AlertStatus.ACTIVE,
                    message=f"{rule.name}: 当前值 {metric_value} 超过阈值 {rule.threshold}",
                    details={
                        "metric_value": metric_value,
                        "threshold": rule.threshold,
                        "condition": rule.condition,
                        "evaluation_time": datetime.now().isoformat()
                    },
                    triggered_at=datetime.now(),
                    tags=rule.tags,
                    metadata={"rule_id": rule.id}
                )

                await self._create_alert(alert)

    async def _get_metric_value(self, rule: AlertRule) -> Optional[float]:
        """获取指标值"""
        # 这里应该根据规则条件查询相应的监控系统
        # 示例实现，返回模拟数据
        if "cpu_usage" in rule.condition:
            # 这里应该调用系统监控获取CPU使用率
            return 75.0  # 模拟值
        elif "error_rate" in rule.condition:
            # 这里应该调用应用监控获取错误率
            return 0.05  # 模拟值
        elif "response_time" in rule.condition:
            # 这里应该调用性能监控获取响应时间
            return 1500.0  # 模拟值

        return None

    def _check_condition(self, value: float, rule: AlertRule) -> bool:
        """检查条件"""
        if rule.condition.startswith(">"):
            return value > rule.threshold
        elif rule.condition.startswith("<"):
            return value < rule.threshold
        elif rule.condition.startswith(">="):
            return value >= rule.threshold
        elif rule.condition.startswith("<="):
            return value <= rule.threshold
        elif rule.condition.startswith("=="):
            return abs(value - rule.threshold) < 0.001
        else:
            return False

    def _get_existing_alert(self, rule_id: str) -> Optional[Alert]:
        """获取现有告警"""
        for alert in self.active_alerts.values():
            if alert.rule_id == rule_id and alert.status == AlertStatus.ACTIVE:
                return alert
        return None

    async def _create_alert(self, alert: Alert) -> None:
        """创建告警"""
        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)

        # 保持历史记录在合理范围内
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]

        # 存储到Redis（如果可用）
        if self.redis_client:
            try:
                alert_key = f"alert:{alert.id}"
                await self.redis_client.hset(alert_key, mapping={
                    "id": alert.id,
                    "rule_id": alert.rule_id,
                    "rule_name": alert.rule_name,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "message": alert.message,
                    "details": json.dumps(alert.details),
                    "triggered_at": alert.triggered_at.isoformat(),
                    "tags": json.dumps(alert.tags or []),
                    "metadata": json.dumps(alert.metadata or {})
                })
                await self.redis_client.expire(alert_key, 86400)  # 24小时过期
            except Exception as e:
                logging.error(f"Failed to store alert in Redis: {str(e)}")

        # 发送通知
        await self._send_notifications(alert)

        # 启动升级策略
        await self._start_escalation(alert)

        logging.warning(f"Alert created: {alert.id} - {alert.message}")

    async def _update_alert(self, alert: Alert, metric_value: float) -> None:
        """更新告警"""
        alert.details["metric_value"] = metric_value
        alert.details["last_evaluation"] = datetime.now().isoformat()

        # 更新Redis中的告警
        if self.redis_client:
            try:
                alert_key = f"alert:{alert.id}"
                await self.redis_client.hset(alert_key, "details", json.dumps(alert.details))
            except Exception as e:
                logging.error(f"Failed to update alert in Redis: {str(e)}")

    async def _send_notifications(self, alert: Alert) -> None:
        """发送通知"""
        rule = self.rules.get(alert.rule_id)
        if not rule:
            return

        channels = rule.notification_channels or [NotificationChannel.EMAIL]

        for channel in channels:
            provider = self.notification_providers.get(channel)
            if provider and provider.enabled:
                try:
                    await provider.send_notification(alert, alert.message)
                except Exception as e:
                    logging.error(f"Failed to send {channel.value} notification: {str(e)}")

    async def _start_escalation(self, alert: Alert) -> None:
        """启动升级策略"""
        rule = self.rules.get(alert.rule_id)
        if not rule or not rule.escalation_policy:
            return

        policy = self.escalation_policies.get(rule.escalation_policy)
        if not policy:
            return

        # 为每个升级级别创建定时任务
        for level in policy.levels:
            if level.delay_minutes > 0:
                asyncio.create_task(self._escalation_task(alert, level, level.delay_minutes * 60))

    async def _escalation_task(self, alert: Alert, level: EscalationLevel, delay_seconds: int) -> None:
        """升级任务"""
        await asyncio.sleep(delay_seconds)

        # 检查告警是否仍然活跃
        current_alert = self.active_alerts.get(alert.id)
        if not current_alert or current_alert.status != AlertStatus.ACTIVE:
            return

        # 发送升级通知
        for channel in level.channels:
            provider = self.notification_providers.get(channel)
            if provider and provider.enabled:
                try:
                    escalation_message = f"[ESCALATION L{level.level}] {alert.message}"
                    await provider.send_notification(alert, escalation_message)
                    logging.info(f"Escalation notification sent for alert {alert.id} via {channel.value}")
                except Exception as e:
                    logging.error(f"Failed to send escalation notification: {str(e)}")

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """确认告警"""
        if alert_id not in self.active_alerts:
            return False

        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now()
        alert.acknowledged_by = acknowledged_by

        # 更新Redis
        if self.redis_client:
            try:
                alert_key = f"alert:{alert_id}"
                await self.redis_client.hset(alert_key, mapping={
                    "status": alert.status.value,
                    "acknowledged_at": alert.acknowledged_at.isoformat(),
                    "acknowledged_by": alert.acknowledged_by
                })
            except Exception as e:
                logging.error(f"Failed to update alert status in Redis: {str(e)}")

        logging.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return True

    async def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """解决告警"""
        if alert_id not in self.active_alerts:
            return False

        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()
        alert.resolved_by = resolved_by

        # 从活跃告警中移除
        del self.active_alerts[alert_id]

        # 更新Redis
        if self.redis_client:
            try:
                alert_key = f"alert:{alert_id}"
                await self.redis_client.hset(alert_key, mapping={
                    "status": alert.status.value,
                    "resolved_at": alert.resolved_at.isoformat(),
                    "resolved_by": alert.resolved_by
                })
            except Exception as e:
                logging.error(f"Failed to update alert status in Redis: {str(e)}")

        logging.info(f"Alert {alert_id} resolved by {resolved_by}")
        return True

    def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计"""
        total_alerts = len(self.alert_history)
        active_alerts = len(self.active_alerts)

        # 按严重级别统计
        severity_stats = defaultdict(int)
        for alert in self.active_alerts.values():
            severity_stats[alert.severity.value] += 1

        # 按状态统计
        status_stats = defaultdict(int)
        for alert in self.active_alerts.values():
            status_stats[alert.status.value] += 1

        # 最近24小时的告警趋势
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        recent_alerts = [a for a in self.alert_history if a.triggered_at >= last_24h]

        hourly_counts = defaultdict(int)
        for alert in recent_alerts:
            hour = alert.triggered_at.replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour] += 1

        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "severity_distribution": dict(severity_stats),
            "status_distribution": dict(status_stats),
            "hourly_trend": {hour.isoformat(): count for hour, count in hourly_counts.items()},
            "last_updated": now.isoformat()
        }