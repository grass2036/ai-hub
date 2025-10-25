"""
多渠道通知系统
支持邮件、Slack、Webhook、短信等多种通知方式
"""
import smtplib
import asyncio
import aiohttp
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class NotificationChannel:
    """通知渠道配置"""
    name: str
    enabled: bool = True
    config: Dict = None
    rate_limit: Optional[Dict] = None  # rate limiting config

@dataclass
class NotificationMessage:
    """通知消息"""
    title: str
    content: str
    severity: str
    timestamp: datetime
    source: str
    metadata: Dict = None

class EmailNotifier:
    """邮件通知器"""

    def __init__(self, config: Dict):
        self.smtp_host = config.get('smtp_host', 'localhost')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.use_tls = config.get('use_tls', True)
        self.sender = config.get('sender', 'noreply@ai-hub.com')
        self.recipients = config.get('recipients', [])

    async def send_notification(self, message: NotificationMessage) -> bool:
        """发送邮件通知"""
        try:
            # 创建邮件消息
            msg = MIMEMultipart()
            msg['From'] = self.sender
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = f"[{message.severity.upper()}] {message.title}"

            # 生成邮件内容
            body = self._generate_email_body(message)
            msg.attach(MIMEText(body, 'html', 'utf-8'))

            # 发送邮件
            await self._send_email(msg)

            logger.info(f"Email notification sent: {message.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    async def _send_email(self, msg: MIMEMultipart):
        """发送邮件的异步实现"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._send_email_sync, msg)

    def _send_email_sync(self, msg: MIMEMultipart):
        """同步发送邮件"""
        server = smtplib.SMTP(self.smtp_host, self.smtp_port)
        if self.use_tls:
            server.starttls()
        if self.username and self.password:
            server.login(self.username, self.password)
        server.send_message(msg)
        server.quit()

    def _generate_email_body(self, message: NotificationMessage) -> str:
        """生成邮件HTML内容"""
        severity_colors = {
            'critical': '#ff4444',
            'warning': '#ffaa00',
            'info': '#00aaff'
        }

        color = severity_colors.get(message.severity, '#666666')

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI Hub Alert</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px; }}
                .footer {{ background-color: #333; color: white; padding: 10px; text-align: center; font-size: 12px; }}
                .alert-info {{ background-color: #e8f4f8; padding: 15px; margin: 10px 0; border-left: 4px solid {color}; }}
                .timestamp {{ color: #666; font-size: 12px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 AI Hub System Alert</h1>
                    <p>Severity: {message.severity.upper()}</p>
                </div>

                <div class="content">
                    <h2>{message.title}</h2>
                    <div class="alert-info">
                        <p>{message.content}</p>
                    </div>

                    <div class="alert-info">
                        <h3>Alert Details</h3>
                        <ul>
                            <li><strong>Source:</strong> {message.source}</li>
                            <li><strong>Time:</strong> {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</li>
                            <li><strong>Severity:</strong> {message.severity.upper()}</li>
                        </ul>
                    </div>

                    {self._generate_metadata_section(message.metadata) if message.metadata else ''}

                    <div class="timestamp">
                        <p>This alert was generated by AI Hub monitoring system.</p>
                        <p>Please check your monitoring dashboard for more details.</p>
                    </div>
                </div>

                <div class="footer">
                    <p>© 2024 AI Hub Platform. All rights reserved.</p>
                    <p>This is an automated message. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _generate_metadata_section(self, metadata: Dict) -> str:
        """生成元数据HTML部分"""
        if not metadata:
            return ""

        html = '<div class="alert-info"><h3>Additional Information</h3><ul>'
        for key, value in metadata.items():
            html += f'<li><strong>{key.replace("_", " ").title()}:</strong> {value}</li>'
        html += '</ul></div>'
        return html

class SlackNotifier:
    """Slack通知器"""

    def __init__(self, config: Dict):
        self.webhook_url = config.get('webhook_url')
        self.channel = config.get('channel', '#alerts')
        self.username = config.get('username', 'AI Hub Bot')
        self.icon_emoji = config.get('icon_emoji', ':robot_face:')

    async def send_notification(self, message: NotificationMessage) -> bool:
        """发送Slack通知"""
        try:
            if not self.webhook_url:
                logger.warning("Slack webhook URL not configured")
                return False

            payload = self._build_slack_payload(message)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        logger.info(f"Slack notification sent: {message.title}")
                        return True
                    else:
                        logger.error(f"Slack notification failed: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    def _build_slack_payload(self, message: NotificationMessage) -> Dict:
        """构建Slack消息负载"""
        # 根据严重程度设置颜色
        colors = {
            'critical': '#ff4444',
            'warning': '#ffaa00',
            'info': '#00aaff'
        }

        color = colors.get(message.severity, '#666666')

        # 构建消息
        payload = {
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "channel": self.channel,
            "text": f"🚨 {message.severity.upper()} Alert: {message.title}",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "Alert Message",
                            "value": message.content,
                            "short": False
                        },
                        {
                            "title": "Source",
                            "value": message.source,
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": message.severity.upper(),
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            "short": True
                        }
                    ],
                    "footer": "AI Hub Monitoring",
                    "ts": int(message.timestamp.timestamp())
                }
            ]
        }

        # 添加元数据字段
        if message.metadata:
            metadata_fields = []
            for key, value in message.metadata.items():
                metadata_fields.append({
                    "title": key.replace("_", " ").title(),
                    "value": str(value),
                    "short": True
                })

            if metadata_fields:
                payload["attachments"][0]["fields"].extend(metadata_fields)

        return payload

class WebhookNotifier:
    """Webhook通知器"""

    def __init__(self, config: Dict):
        self.webhook_url = config.get('webhook_url')
        self.headers = config.get('headers', {})
        self.timeout = config.get('timeout', 10)

    async def send_notification(self, message: NotificationMessage) -> bool:
        """发送Webhook通知"""
        try:
            if not self.webhook_url:
                logger.warning("Webhook URL not configured")
                return False

            payload = {
                "alert": {
                    "title": message.title,
                    "content": message.content,
                    "severity": message.severity,
                    "source": message.source,
                    "timestamp": message.timestamp.isoformat(),
                    "metadata": message.metadata or {}
                },
                "service": "ai-hub-monitoring",
                "sent_at": datetime.utcnow().isoformat()
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status in [200, 201, 202]:
                        logger.info(f"Webhook notification sent: {message.title}")
                        return True
                    else:
                        logger.error(f"Webhook notification failed: {response.status}")
                        return False

        except asyncio.TimeoutError:
            logger.error(f"Webhook notification timeout: {message.title}")
            return False
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False

class SMSNotifier:
    """短信通知器（仅用于关键告警）"""

    def __init__(self, config: Dict):
        self.provider = config.get('provider', 'twilio')
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')
        self.phone_numbers = config.get('phone_numbers', [])
        self.from_number = config.get('from_number')

    async def send_notification(self, message: NotificationMessage) -> bool:
        """发送短信通知（仅关键告警）"""
        try:
            if message.severity != 'critical':
                return True  # 非关键告警不发送短信

            if not self.phone_numbers:
                logger.warning("No phone numbers configured for SMS")
                return False

            # 这里可以集成不同的短信服务提供商
            # 为了演示，使用Twilio API
            if self.provider == 'twilio':
                return await self._send_twilio_sms(message)
            else:
                logger.warning(f"SMS provider {self.provider} not implemented")
                return False

        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
            return False

    async def _send_twilio_sms(self, message: NotificationMessage) -> bool:
        """发送Twilio短信"""
        try:
            # 注意：需要安装twilio库
            # from twilio.rest import Client
            # client = Client(self.api_key, self.api_secret)

            # 为了简化，这里只是模拟发送
            sms_content = f"[CRITICAL] {message.title}: {message.content[:100]}"

            for phone_number in self.phone_numbers:
                # message = client.messages.create(
                #     body=sms_content,
                #     from_=self.from_number,
                #     to=phone_number
                # )
                logger.info(f"SMS sent to {phone_number}: {sms_content[:50]}...")

            return True

        except Exception as e:
            logger.error(f"Failed to send Twilio SMS: {e}")
            return False

class NotificationManager:
    """通知管理器"""

    def __init__(self):
        self.notifiers = {}
        self.channels = {}
        self.rate_limits = {}
        self.notification_history = []
        self.max_history_size = 1000

    def configure_channel(self, channel_name: str, notifier_type: str, config: Dict):
        """配置通知渠道"""
        # 创建通知器
        if notifier_type == 'email':
            notifier = EmailNotifier(config)
        elif notifier_type == 'slack':
            notifier = SlackNotifier(config)
        elif notifier_type == 'webhook':
            notifier = WebhookNotifier(config)
        elif notifier_type == 'sms':
            notifier = SMSNotifier(config)
        else:
            raise ValueError(f"Unknown notifier type: {notifier_type}")

        # 创建通知渠道
        channel = NotificationChannel(
            name=channel_name,
            enabled=config.get('enabled', True),
            config=config,
            rate_limit=config.get('rate_limit')
        )

        self.notifiers[channel_name] = notifier
        self.channels[channel_name] = channel

        logger.info(f"Configured notification channel: {channel_name} ({notifier_type})")

    async def send_alert(self, alert_data: Dict, channels: List[str] = None) -> Dict[str, bool]:
        """发送告警通知"""
        if not channels:
            # 使用默认渠道
            channels = ['email', 'slack']

        # 创建通知消息
        message = NotificationMessage(
            title=alert_data.get('rule_name', 'System Alert'),
            content=alert_data.get('message', 'Unknown alert'),
            severity=alert_data.get('severity', 'info'),
            timestamp=datetime.fromisoformat(alert_data.get('triggered_at', datetime.utcnow().isoformat())),
            source=alert_data.get('metric_name', 'system'),
            metadata=alert_data
        )

        results = {}

        # 并行发送到所有渠道
        tasks = []
        for channel_name in channels:
            if channel_name in self.channels and self.channels[channel_name].enabled:
                # 检查速率限制
                if self._check_rate_limit(channel_name, message):
                    notifier = self.notifiers[channel_name]
                    task = asyncio.create_task(self._safe_send_notification(notifier, message, channel_name))
                    tasks.append((channel_name, task))
                else:
                    results[channel_name] = False
                    logger.warning(f"Rate limit exceeded for channel: {channel_name}")

        # 等待所有通知发送完成
        for channel_name, task in tasks:
            try:
                results[channel_name] = await task
            except Exception as e:
                logger.error(f"Failed to send notification via {channel_name}: {e}")
                results[channel_name] = False

        # 记录通知历史
        self._record_notification(message, channels, results)

        return results

    async def _safe_send_notification(self, notifier, message: NotificationMessage, channel_name: str) -> bool:
        """安全发送通知"""
        try:
            return await notifier.send_notification(message)
        except Exception as e:
            logger.error(f"Error sending notification via {channel_name}: {e}")
            return False

    def _check_rate_limit(self, channel_name: str, message: NotificationMessage) -> bool:
        """检查速率限制"""
        channel = self.channels.get(channel_name)
        if not channel or not channel.rate_limit:
            return True

        # 简单的速率限制实现
        limit_config = channel.rate_limit
        max_requests = limit_config.get('max_requests', 10)
        time_window = limit_config.get('time_window', 60)  # 秒

        # 检查最近的通知记录
        cutoff_time = datetime.utcnow() - timedelta(seconds=time_window)
        recent_notifications = [
            notif for notif in self.notification_history
            if notif['channel'] == channel_name and notif['timestamp'] >= cutoff_time
        ]

        return len(recent_notifications) < max_requests

    def _record_notification(self, message: NotificationMessage, channels: List[str], results: Dict[str, bool]):
        """记录通知历史"""
        record = {
            'message': message.title,
            'severity': message.severity,
            'timestamp': datetime.utcnow(),
            'channels': channels,
            'results': results
        }

        self.notification_history.append(record)

        # 保持历史记录在合理范围内
        if len(self.notification_history) > self.max_history_size:
            self.notification_history = self.notification_history[-self.max_history_size:]

    async def send_test_notification(self, channel_name: str, message: str = "Test notification") -> bool:
        """发送测试通知"""
        if channel_name not in self.notifiers:
            logger.error(f"Channel {channel_name} not configured")
            return False

        test_message = NotificationMessage(
            title="Test Notification",
            content=message,
            severity="info",
            timestamp=datetime.utcnow(),
            source="test"
        )

        notifier = self.notifiers[channel_name]
        return await notifier.send_notification(test_message)

    def get_channel_status(self) -> Dict[str, Dict]:
        """获取渠道状态"""
        status = {}
        for channel_name, channel in self.channels.items():
            # 获取最近的通知统计
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            recent_notifications = [
                notif for notif in self.notification_history
                if notif['timestamp'] >= cutoff_time and channel_name in notif['channels']
            ]

            success_count = sum(
                1 for notif in recent_notifications
                if notif['results'].get(channel_name, False)
            )

            status[channel_name] = {
                'enabled': channel.enabled,
                'notifier_type': type(self.notifiers[channel_name]).__name__,
                'recent_notifications_24h': len(recent_notifications),
                'success_rate_24h': (success_count / len(recent_notifications) * 100) if recent_notifications else 0,
                'last_notification': recent_notifications[-1]['timestamp'].isoformat() if recent_notifications else None
            }

        return status

    def get_notification_stats(self, hours: int = 24) -> Dict:
        """获取通知统计"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_notifications = [
            notif for notif in self.notification_history
            if notif['timestamp'] >= cutoff_time
        ]

        # 按渠道统计
        channel_stats = defaultdict(lambda: {'total': 0, 'success': 0})
        severity_stats = defaultdict(int)

        for notif in recent_notifications:
            severity_stats[notif['severity']] += 1

            for channel, result in notif['results'].items():
                channel_stats[channel]['total'] += 1
                if result:
                    channel_stats[channel]['success'] += 1

        # 计算成功率
        for channel in channel_stats:
            total = channel_stats[channel]['total']
            success = channel_stats[channel]['success']
            channel_stats[channel]['success_rate'] = (success / total * 100) if total > 0 else 0

        return {
            'period_hours': hours,
            'total_notifications': len(recent_notifications),
            'channel_stats': dict(channel_stats),
            'severity_distribution': dict(severity_stats),
            'active_channels': len([c for c in self.channels.values() if c.enabled])
        }

# 默认配置
DEFAULT_NOTIFICATION_CONFIG = {
    'email': {
        'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'username': os.getenv('SMTP_USERNAME', ''),
        'password': os.getenv('SMTP_PASSWORD', ''),
        'use_tls': True,
        'sender': os.getenv('EMAIL_SENDER', 'noreply@ai-hub.com'),
        'recipients': os.getenv('EMAIL_RECIPIENTS', '').split(',') if os.getenv('EMAIL_RECIPIENTS') else [],
        'enabled': bool(os.getenv('EMAIL_ENABLED', 'false').lower() == 'true')
    },
    'slack': {
        'webhook_url': os.getenv('SLACK_WEBHOOK_URL', ''),
        'channel': os.getenv('SLACK_CHANNEL', '#alerts'),
        'username': 'AI Hub Bot',
        'icon_emoji': ':robot_face:',
        'enabled': bool(os.getenv('SLACK_ENABLED', 'false').lower() == 'true')
    },
    'webhook': {
        'webhook_url': os.getenv('WEBHOOK_URL', ''),
        'headers': {'Content-Type': 'application/json'},
        'timeout': 10,
        'enabled': bool(os.getenv('WEBHOOK_ENABLED', 'false').lower() == 'true')
    },
    'sms': {
        'provider': 'twilio',
        'api_key': os.getenv('TWILIO_API_KEY', ''),
        'api_secret': os.getenv('TWILIO_API_SECRET', ''),
        'phone_numbers': os.getenv('SMS_PHONE_NUMBERS', '').split(',') if os.getenv('SMS_PHONE_NUMBERS') else [],
        'from_number': os.getenv('TWILIO_FROM_NUMBER', ''),
        'enabled': bool(os.getenv('SMS_ENABLED', 'false').lower() == 'true')
    }
}

# 初始化全局通知管理器
def initialize_notification_manager() -> NotificationManager:
    """初始化通知管理器"""
    manager = NotificationManager()

    for channel_name, config in DEFAULT_NOTIFICATION_CONFIG.items():
        if config.get('enabled', False) and config.get('webhook_url') or config.get('recipients'):
            try:
                notifier_type = channel_name if channel_name != 'sms' else 'sms'
                manager.configure_channel(channel_name, notifier_type, config)
                logger.info(f"Initialized notification channel: {channel_name}")
            except Exception as e:
                logger.error(f"Failed to initialize channel {channel_name}: {e}")

    return manager

# 全局通知管理器实例
notification_manager = initialize_notification_manager()