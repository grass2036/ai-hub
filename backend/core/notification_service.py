"""
告警通知服务
Week 5 Day 3: 系统监控和运维自动化
"""

import asyncio
import json
import smtplib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base64 import MIMEBase64
import requests

from backend.config.settings import get_settings
from backend.core.monitoring_service import Alert, AlertSeverity
from backend.core.logging_service import get_logger, LogLevel

logger = get_logger(LogLevel.SYSTEM, module="notification_service")

settings = get_settings()


class NotificationChannel(Enum):
    """通知渠道"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    DINGTALK = "dingtalk"
    WECHAT_WORK = "wechat_work"
    SMS = "sms"
    DESKTOP = "desktop"


@dataclass
class NotificationMessage:
    """通知消息"""
    id: str
    channel: NotificationChannel
    recipient: str
    subject: str
    content: str
    severity: AlertSeverity
    timestamp: datetime
    metadata: Dict[str, Any] = None
    attachments: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.attachments is None:
            self.attachments = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "channel": self.channel.value,
            "recipient": self.recipient,
            "subject": self.subject,
            "content": self.content,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "attachments": self.attachments
        }


class NotificationService:
    """通知服务"""

    def __init__(self):
        self.enabled_channels = self._get_enabled_channels()
        self.notification_queue = asyncio.Queue(maxsize=1000)
        self.failed_notifications = []
        self.notification_history = []

    def _get_enabled_channels(self) -> List[NotificationChannel]:
        """获取启用的通知渠道"""
        channels = []

        # 从环境变量读取启用的渠道
        if settings.smtp_server and settings.smtp_port:
            channels.append(NotificationChannel.EMAIL)

        if settings.webhook_url:
            channels.append(NotificationChannel.WEBHOOK)

        if settings.slack_webhook_url:
            channels.append(NotificationChannel.SLACK)

        if settings.dingtalk_webhook_url:
            channels.append(NotificationChannel.DINGTALK)

        return channels

    async def send_notification(self, message: NotificationMessage) -> bool:
        """发送通知"""
        try:
            # 检查渠道是否启用
            if message.channel not in self.enabled_channels:
                logger.warning(f"Notification channel {message.channel.value} is not enabled")
                return False

            # 根据渠道发送通知
            success = await self._send_by_channel(message)

            if success:
                # 记录到历史
                self._add_to_history(message)
                logger.info(f"Notification sent successfully via {message.channel.value}: {message.subject}")
            else:
                # 添加到失败列表
                self.failed_notifications.append(message)
                logger.error(f"Failed to send notification via {message.channel.value}: {message.subject}")

            return success

        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            self.failed_notifications.append(message)
            return False

    async def _send_by_channel(self, message: NotificationMessage) -> bool:
        """根据渠道发送通知"""
        if message.channel == NotificationChannel.EMAIL:
            return await self._send_email(message)
        elif message.channel == NotificationChannel.WEBHOOK:
            return await self._send_webhook(message)
        elif message.channel == NotificationChannel.SLACK:
            return await self._send_slack(message)
        elif message.channel == NotificationChannel.DINGTALK:
            return await self._send_dingtalk(message)
        elif message.channel == NotificationChannel.SMS:
            return await self._send_sms(message)
        else:
            logger.warning(f"Unsupported notification channel: {message.channel.value}")
            return False

    async def _send_email(self, message: NotificationMessage) -> bool:
        """发送邮件通知"""
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.smtp_from_email
            msg['To'] = message.recipient
            msg['Subject'] = message.subject

            # 添加HTML内容
            html_content = self._generate_email_html(message)
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # 连接SMTP服务器
            server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)

            if settings.smtp_username and settings.smtp_password:
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)

            # 发送邮件
            server.send_message(msg)
            server.quit()

            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def _send_webhook(self, message: NotificationMessage) -> bool:
        """发送Webhook通知"""
        try:
            payload = {
                "id": message.id,
                "subject": message.subject,
                "content": message.content,
                "severity": message.severity.value,
                "timestamp": message.timestamp.isoformat(),
                "metadata": message.metadata,
                "attachments": message.attachments
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    return response.status == 200

        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")
            return False

    async def _send_slack(self, message: NotificationMessage) -> bool:
        """发送Slack通知"""
        try:
            color = self._get_slack_color(message.severity)
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": message.subject,
                        "text": message.content,
                        "ts": int(message.timestamp.timestamp()),
                        "fields": [
                            {
                                "title": "严重程度",
                                "value": message.severity.value,
                                "short": True
                            },
                            {
                                "title": "时间",
                                "value": message.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                "short": True
                            }
                        ],
                        "footer": "AI Hub Platform",
                        "footer_icon": "https://platform.ai-hub.com/icon.png"
                    }
                ]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.slack_webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    return response.status == 200

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    async def _send_dingtalk(self, message: NotificationMessage) -> bool:
        """发送钉钉通知"""
        try:
            # 根据严重程度选择图标
            at_mobile = "true" if message.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL] else "false"

            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"**{message.severity.value.upper()}** - {message.subject}",
                    "text": message.content,
                    "at": {
                        "atMobiles": [at_mobile]
                    }
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.dingtalk_webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    result = await response.json()
                    return result.get("errcode") == 0

        except Exception as e:
            logger.error(f"Failed to send DingTalk notification: {e}")
            return False

    async def _send_sms(self, message: NotificationMessage) -> bool:
        """发送短信通知（示例实现）"""
        try:
            # 这里可以集成第三方短信服务
            # 例如：阿里云短信、腾讯云短信、Twilio等

            logger.info(f"SMS notification would be sent to {message.recipient}: {message.content}")
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False

    def _generate_email_html(self, message: NotificationMessage) -> str:
        """生成邮件HTML内容"""
        severity_colors = {
            AlertSeverity.INFO: "#3178c6",
            AlertSeverity.WARNING: "#f59e0b",
            AlertSeverity.ERROR: "#ef4444",
            AlertSeverity.CRITICAL: "#dc2626"
        }

        color = severity_colors.get(message.severity, "#3178c6")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{message.subject}</title>
        </head>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="background-color: {color}; padding: 20px; border-radius: 8px 8px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">{message.subject}</h1>
                    <div style="color: rgba(255,255,255,0.8); font-size: 14px; margin-top: 5px;">
                        {message.severity.value.upper()} • {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
                    </div>
                </div>
                <div style="padding: 20px;">
                    <div style="margin-bottom: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 6px; border-left: 4px solid {color};">
                        <p style="margin: 0; line-height: 1.6;">{message.content}</p>
                    </div>

                    {message.attachments and message.attachments.length > 0 and (
                    <div style="margin-bottom: 20px;">
                        <h3 style="margin-top: 0; margin-bottom: 10px; color: #333;">附件</h3>
                        {message.attachments.map((attachment, index) => (
                            <div key={index} style="padding: 10px; background-color: #f1f3f4; border-radius: 4px; margin-bottom: 10px;">
                                <div style="font-weight: medium;">{attachment.get('name', 'Attachment ' + str(index + 1))}</div>
                                {attachment.get('url') and (
                                    <div style="margin-top: 5px;">
                                        <a href={attachment['url']} style="color: #007bff; text-decoration: none;">下载</a>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                    )}

                    {message.metadata and Object.keys(message.metadata).length > 0 and (
                    <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 6px;">
                        <h3 style="margin-top: 0; margin-bottom: 10px; color: #333;">详细信息</h3>
                        {Object.entries(message.metadata).map(([key, value]) => (
                            <div key={key} style="margin-bottom: 5px;">
                                <strong style="color: #555;">{key}:</strong> {value}
                            </div>
                        ))}
                    </div>
                    )}

                    <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #e9ecef; text-align: center; color: #6c757d; font-size: 12px;">
                        <p style="margin: 0;">
                            此邮件由 AI Hub Platform 自动发送<br>
                            如有疑问，请联系系统管理员
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def _get_slack_color(self, severity: AlertSeverity) -> str:
        """获取Slack颜色"""
        colors = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9800",
            AlertSeverity.ERROR: "#f44336",
            AlertSeverity.CRITICAL: "#dc2626"
        }
        return colors.get(severity, "#36a64f")

    def _add_to_history(self, message: NotificationMessage):
        """添加到历史记录"""
        self.notification_history.append(message.to_dict())

        # 保持历史记录大小
        if len(self.notification_history) > 1000:
            self.notification_history = self.notification_history[-1000:]

    async def get_notification_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取通知历史"""
        return self.notification_history[-limit:]

    async def get_failed_notifications(self) -> List[Dict[str, Any]]:
        """获取失败的通知"""
        return [asdict(notification) for notification in self.failed_notifications]

    async def retry_failed_notifications(self) -> int:
        """重试失败的通知"""
        retry_count = 0
        notifications_to_retry = self.failed_notifications.copy()
        self.failed_notifications.clear()

        for notification in notifications_to_retry:
            success = await self.send_notification(NotificationMessage(**notification))
            if success:
                retry_count += 1
            else:
                self.failed_notifications.append(notification)

        return retry_count

    async def create_notification_from_alert(self, alert: Alert) -> List[NotificationMessage]:
        """从告警创建通知消息"""
        messages = []

        # 邮件通知
        if NotificationChannel.EMAIL in self.enabled_channels:
            email_message = NotificationMessage(
                id=f"email_{alert.id}_{int(alert.timestamp.timestamp())}",
                channel=NotificationChannel.EMAIL,
                recipient=settings.alert_email_recipients or [],
                subject=f"[AI Hub Alert] {alert.rule_name}",
                content=alert.message,
                severity=alert.severity,
                timestamp=alert.timestamp,
                metadata={
                    "alert_id": alert.id,
                    "rule_id": alert.rule_id,
                    "tags": alert.tags
                }
            )
            messages.append(email_message)

        # Slack通知
        if NotificationChannel.SLACK in self.enabled_channels:
            slack_message = NotificationMessage(
                id=f"slack_{alert.id}_{int(alert.timestamp.timestamp())}",
                channel=NotificationChannel.SLACK,
                recipient=settings.slack_webhook_url,
                subject=alert.rule_name,
                content=alert.message,
                severity=alert.severity,
                timestamp=alert.timestamp,
                metadata={
                    "alert_id": alert.id,
                    "rule_id": alert.rule_id,
                    "tags": alert.tags
                }
            )
            messages.append(slack_message)

        # 钉钉通知
        if NotificationChannel.DINGTALK in self.enabled_channels:
            dingtalk_message = NotificationMessage(
                id=f"dingtalk_{alert.id}_{int(alert.timestamp.timestamp())}",
                channel=NotificationChannel.DINGTALK,
                recipient=settings.dingtalk_webhook_url,
                subject=alert.rule_name,
                content=alert.message,
                severity=alert.severity,
                timestamp=alert.timestamp,
                metadata={
                    "alert_id": alert.id,
                    "rule_id": alert.rule_id,
                    "tags": alert.tags
                }
            )
            messages.append(dingtalk_message)

        # Webhook通知
        if NotificationChannel.WEBHOOK in self.enabled_channels:
            webhook_message = NotificationMessage(
                id=f"webhook_{alert.id}_{int(alert.timestamp.timestamp())}",
                channel=NotificationChannel.WEBHOOK,
                recipient=settings.webhook_url,
                subject=alert.rule_name,
                content=alert.message,
                severity=alert.severity,
                timestamp=alert.timestamp,
                metadata={
                    "alert_id": alert.id,
                    "rule_id": alert.rule_id,
                    "tags": alert.tags
                }
            )
            messages.append(webhook_message)

        return messages


# 全局通知服务实例
notification_service = NotificationService()


async def send_alert_notifications(alert: Alert) -> List[bool]:
    """发送告警通知"""
    try:
        messages = await notification_service.create_notification_from_alert(alert)

        results = []
        for message in messages:
            success = await notification_service.send_notification(message)
            results.append(success)

        return results

    except Exception as e:
        logger.error(f"Failed to create notification messages from alert: {e}")
        return []


async def start_notification_service():
    """启动通知服务"""
    logger.info("Starting notification service...")

    # 定期重试失败的通知
    while True:
        try:
            await asyncio.sleep(300)  # 5分钟
            retry_count = await notification_service.retry_failed_notifications()
            if retry_count > 0:
                logger.info(f"Retried {retry_count} failed notifications")
        except Exception as e:
            logger.error(f"Error in notification service: {e}")
            await asyncio.sleep(300)


# 简化的通知接口
class Notifier:
    """简化的通知接口"""

    @staticmethod
    async def send_email(recipients: Union[str, List[str]], subject: str, content: str, severity: AlertSeverity = AlertSeverity.INFO):
        """发送邮件通知"""
        if isinstance(recipients, str):
            recipients = [recipients]

        for recipient in recipients:
            message = NotificationMessage(
                id=f"manual_email_{int(datetime.now().timestamp())}_{len(notification_service.notification_history)}",
                channel=NotificationChannel.EMAIL,
                recipient=recipient,
                subject=subject,
                content=content,
                severity=severity,
                timestamp=datetime.now(timezone.utc)
            )
            await notification_service.send_notification(message)

    @staticmethod
    async def send_webhook(url: str, data: Dict[str, Any], severity: AlertSeverity = AlertSeverity.INFO):
        """发送Webhook通知"""
        message = NotificationMessage(
            id=f"manual_webhook_{int(datetime.now().timestamp())}_{len(notification_service.notification_history)}",
            channel=NotificationChannel.WEBHOOK,
            recipient=url,
            subject=data.get("title", "Webhook Notification"),
            content=data.get("message", ""),
            severity=severity,
            timestamp=datetime.now(timezone.utc),
            metadata=data
        )
        await notification_service.send_notification(message)

    @staticmethod
    async def send_alert(title: str, message: str, severity: AlertSeverity = AlertSeverity.WARNING, metadata: Dict[str, Any] = None):
        """发送告警通知"""
        # 这里可以根据需要选择合适的通知渠道
        # 目前使用Webhook作为默认方式
        await Notifier.send_webhook(
            url=settings.webhook_url,
            data={
                "title": title,
                "message": message,
                "severity": severity.value,
                "metadata": metadata or {}
            },
            severity=severity
        )