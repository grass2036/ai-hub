"""
自动化运维引擎
Week 5 Day 5: 系统监控和运维增强 - 自动化运维系统
"""

import asyncio
import json
import time
import subprocess
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod
import threading
from collections import defaultdict, deque
import uuid

from backend.config.settings import get_settings
from backend.health.deep_health_checker import HealthStatus
from backend.core.logging.advanced_logging import LogAnomaly, AnomalyType
from backend.monitoring.distributed_tracing import SpanStatus

logger = logging.getLogger(__name__)
settings = get_settings()


class AutomationStatus(Enum):
    """自动化状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TriggerType(Enum):
    """触发器类型"""
    HEALTH_CHECK = "health_check"
    LOG_ANOMALY = "log_anomaly"
    METRIC_THRESHOLD = "metric_threshold"
    SCHEDULE = "schedule"
    MANUAL = "manual"


class ActionType(Enum):
    """动作类型"""
    RESTART_SERVICE = "restart_service"
    SCALE_RESOURCES = "scale_resources"
    CLEANUP_LOGS = "cleanup_logs"
    BACKUP_DATA = "backup_data"
    SEND_ALERT = "send_alert"
    EXECUTE_SCRIPT = "execute_script"
    ADJUST_CONFIG = "adjust_config"


@dataclass
class Trigger:
    """触发器"""
    trigger_id: str
    name: str
    description: str
    trigger_type: TriggerType
    condition: Dict[str, Any]
    enabled: bool = True
    cooldown_seconds: int = 300
    last_triggered: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def should_trigger(self, context: Dict[str, Any]) -> bool:
        """检查是否应该触发"""
        if not self.enabled:
            return False

        # 冷却期检查
        if self.last_triggered:
            time_since_last = datetime.utcnow() - self.last_triggered
            if time_since_last.total_seconds() < self.cooldown_seconds:
                return False

        # 根据触发类型检查条件
        if self.trigger_type == TriggerType.HEALTH_CHECK:
            return self._check_health_condition(context)
        elif self.trigger_type == TriggerType.LOG_ANOMALY:
            return self._check_log_anomaly_condition(context)
        elif self.trigger_type == TriggerType.METRIC_THRESHOLD:
            return self._check_metric_condition(context)
        elif self.trigger_type == TriggerType.SCHEDULE:
            return self._check_schedule_condition(context)

        return False

    def _check_health_condition(self, context: Dict[str, Any]) -> bool:
        """检查健康状态条件"""
        health_status = context.get("health_status")
        if not health_status:
            return False

        required_status = self.condition.get("status")
        component_id = self.condition.get("component_id")

        if component_id:
            component_health = health_status.get("components", {}).get(component_id)
            if component_health and component_health.get("status") == required_status:
                return True
        elif health_status.get("status") == required_status:
            return True

        return False

    def _check_log_anomaly_condition(self, context: Dict[str, Any]) -> bool:
        """检查日志异常条件"""
        anomalies = context.get("log_anomalies", [])
        anomaly_type = self.condition.get("anomaly_type")

        if anomaly_type:
            for anomaly in anomalies:
                if anomaly.get("anomaly_type") == anomaly_type:
                    return True

        return len(anomalies) > 0

    def _check_metric_condition(self, context: Dict[str, Any]) -> bool:
        """检查指标条件"""
        metrics = context.get("metrics", {})
        metric_name = self.condition.get("metric_name")
        operator = self.condition.get("operator", "gt")
        threshold = self.condition.get("threshold")

        if not metric_name or threshold is None:
            return False

        value = metrics.get(metric_name)
        if value is None:
            return False

        if operator == "gt":
            return value > threshold
        elif operator == "lt":
            return value < threshold
        elif operator == "eq":
            return value == threshold
        elif operator == "ne":
            return value != threshold

        return False

    def _check_schedule_condition(self, context: Dict[str, Any]) -> bool:
        """检查调度条件"""
        schedule_config = self.condition.get("schedule", {})
        current_time = datetime.utcnow()

        # 简化的调度检查 - 每小时检查
        if schedule_config.get("type") == "hourly":
            return current_time.minute == 0

        # 每日检查
        elif schedule_config.get("type") == "daily":
            target_hour = schedule_config.get("hour", 0)
            return current_time.hour == target_hour and current_time.minute == 0

        # 每周检查
        elif schedule_config.get("type") == "weekly":
            target_day = schedule_config.get("day", 0)  # 0 = Monday
            target_hour = schedule_config.get("hour", 0)
            return (current_time.weekday() == target_day and
                    current_time.hour == target_hour and current_time.minute == 0)

        return False

    def mark_triggered(self):
        """标记为已触发"""
        self.last_triggered = datetime.utcnow()


@dataclass
class Action:
    """动作"""
    action_id: str
    name: str
    description: str
    action_type: ActionType
    parameters: Dict[str, Any]
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['action_type'] = self.action_type.value
        return data


@dataclass
class AutomationRule:
    """自动化规则"""
    rule_id: str
    name: str
    description: str
    triggers: List[Trigger]
    actions: List[Action]
    enabled: bool = True
    created_at: datetime = None
    last_executed: Optional[datetime] = None
    execution_count: int = 0
    success_count: int = 0

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['triggers'] = [t.to_dict() for t in self.triggers]
        data['actions'] = [a.to_dict() for a in self.actions]
        data['created_at'] = self.created_at.isoformat()
        if self.last_executed:
            data['last_executed'] = self.last_executed.isoformat()
        return data


@dataclass
class AutomationExecution:
    """自动化执行记录"""
    execution_id: str
    rule_id: str
    trigger_id: str
    status: AutomationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    results: List[Dict[str, Any]] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []

    @property
    def duration_seconds(self) -> Optional[float]:
        """执行持续时间"""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data


class ActionExecutor(ABC):
    """动作执行器基类"""

    @abstractmethod
    async def execute(self, action: Action, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行动作"""
        pass


class RestartServiceExecutor(ActionExecutor):
    """服务重启执行器"""

    async def execute(self, action: Action, context: Dict[str, Any]) -> Dict[str, Any]:
        """重启服务"""
        service_name = action.parameters.get("service_name")
        if not service_name:
            raise ValueError("Service name not specified")

        try:
            # 这里应该实现实际的服务重启逻辑
            # 例如：systemctl restart service_name
            # 或者 Docker 容器重启

            # 模拟重启过程
            logger.info(f"Restarting service: {service_name}")

            # 执行重启命令
            result = subprocess.run(
                ["systemctl", "restart", service_name],
                capture_output=True,
                text=True,
                timeout=action.timeout_seconds
            )

            # 检查服务状态
            status_result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True
            )

            return {
                "success": result.returncode == 0,
                "service_name": service_name,
                "restart_output": result.stdout,
                "restart_error": result.stderr,
                "status_output": status_result.stdout.strip(),
                "executed_at": datetime.utcnow().isoformat()
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "service_name": service_name,
                "error": "Restart timeout",
                "executed_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "service_name": service_name,
                "error": str(e),
                "executed_at": datetime.utcnow().isoformat()
            }


class ScaleResourcesExecutor(ActionExecutor):
    """资源扩缩容执行器"""

    async def execute(self, action: Action, context: Dict[str, Any]) -> Dict[str, Any]:
        """扩缩容资源"""
        resource_type = action.parameters.get("resource_type")  # cpu, memory, replicas
        target_value = action.parameters.get("target_value")
        component = action.parameters.get("component")

        if not all([resource_type, target_value, component]):
            raise ValueError("Missing required parameters for scaling")

        try:
            logger.info(f"Scaling {component} {resource_type} to {target_value}")

            # 这里应该实现实际的扩缩容逻辑
            # 例如：kubectl scale deployment --replicas=target_value

            if resource_type == "replicas":
                # 模拟副本数调整
                return {
                    "success": True,
                    "component": component,
                    "resource_type": resource_type,
                    "old_value": context.get("current_replicas", 1),
                    "new_value": target_value,
                    "executed_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"Scaling resource type {resource_type} not implemented",
                    "executed_at": datetime.utcnow().isoformat()
                }

        except Exception as e:
            return {
                "success": False,
                "component": component,
                "resource_type": resource_type,
                "error": str(e),
                "executed_at": datetime.utcnow().isoformat()
            }


class CleanupLogsExecutor(ActionExecutor):
    """日志清理执行器"""

    async def execute(self, action: Action, context: Dict[str, Any]) -> Dict[str, Any]:
        """清理日志"""
        log_path = action.parameters.get("log_path", "logs/")
        retention_days = action.parameters.get("retention_days", 7)

        try:
            logger.info(f"Cleaning up logs in {log_path} older than {retention_days} days")

            # 计算截止日期
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            cleaned_files = []
            total_size_freed = 0

            import os
            import glob

            # 查找日志文件
            log_files = glob.glob(os.path.join(log_path, "*.log"))
            log_files.extend(glob.glob(os.path.join(log_path, "*.log.*")))

            for log_file in log_files:
                try:
                    file_stat = os.stat(log_file)
                    file_mtime = datetime.fromtimestamp(file_stat.st_mtime)

                    if file_mtime < cutoff_date:
                        file_size = file_stat.st_size
                        os.remove(log_file)
                        cleaned_files.append(log_file)
                        total_size_freed += file_size

                except Exception as e:
                    logger.warning(f"Failed to remove log file {log_file}: {e}")

            return {
                "success": True,
                "log_path": log_path,
                "retention_days": retention_days,
                "cleaned_files_count": len(cleaned_files),
                "total_size_freed_mb": round(total_size_freed / (1024 * 1024), 2),
                "cleaned_files": cleaned_files[:10],  # 只返回前10个文件名
                "executed_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "log_path": log_path,
                "retention_days": retention_days,
                "error": str(e),
                "executed_at": datetime.utcnow().isoformat()
            }


class SendAlertExecutor(ActionExecutor):
    """告警发送执行器"""

    async def execute(self, action: Action, context: Dict[str, Any]) -> Dict[str, Any]:
        """发送告警"""
        alert_type = action.parameters.get("alert_type", "email")
        recipients = action.parameters.get("recipients", [])
        message = action.parameters.get("message", "Automation alert")
        severity = action.parameters.get("severity", "warning")

        try:
            logger.info(f"Sending {alert_type} alert to {len(recipients)} recipients")

            # 这里应该实现实际的通知发送逻辑
            # 例如：发送邮件、Slack、钉钉等

            # 模拟发送
            sent_count = len(recipients)

            return {
                "success": True,
                "alert_type": alert_type,
                "recipients_count": sent_count,
                "recipients": recipients,
                "message": message,
                "severity": severity,
                "sent_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "alert_type": alert_type,
                "error": str(e),
                "executed_at": datetime.utcnow().isoformat()
            }


class ExecuteScriptExecutor(ActionExecutor):
    """脚本执行执行器"""

    async def execute(self, action: Action, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行脚本"""
        script_path = action.parameters.get("script_path")
        script_args = action.parameters.get("args", [])
        working_dir = action.parameters.get("working_dir", ".")

        if not script_path:
            raise ValueError("Script path not specified")

        try:
            logger.info(f"Executing script: {script_path}")

            # 构建命令
            cmd = [script_path] + script_args

            # 执行脚本
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=action.timeout_seconds
            )

            return {
                "success": result.returncode == 0,
                "script_path": script_path,
                "args": script_args,
                "working_dir": working_dir,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "executed_at": datetime.utcnow().isoformat()
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "script_path": script_path,
                "error": "Script execution timeout",
                "executed_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "script_path": script_path,
                "error": str(e),
                "executed_at": datetime.utcnow().isoformat()
            }


class AdjustConfigExecutor(ActionExecutor):
    """配置调整执行器"""

    async def execute(self, action: Action, context: Dict[str, Any]) -> Dict[str, Any]:
        """调整配置"""
        config_file = action.parameters.get("config_file")
        config_updates = action.parameters.get("updates", {})
        backup_original = action.parameters.get("backup", True)

        if not config_file or not config_updates:
            raise ValueError("Config file and updates required")

        try:
            logger.info(f"Adjusting config file: {config_file}")

            import os
            import shutil

            # 备份原配置
            if backup_original and os.path.exists(config_file):
                backup_file = f"{config_file}.backup.{int(time.time())}"
                shutil.copy2(config_file, backup_file)
                logger.info(f"Created backup: {backup_file}")

            # 读取配置文件
            with open(config_file, 'r') as f:
                config_content = f.read()

            # 更新配置（简化实现）
            updated_content = config_content
            for key, value in config_updates.items():
                # 这里应该实现更智能的配置更新逻辑
                updated_content = updated_content.replace(
                    f"{key}=", f"{key}={value}"
                )

            # 写入更新后的配置
            with open(config_file, 'w') as f:
                f.write(updated_content)

            return {
                "success": True,
                "config_file": config_file,
                "updates_applied": config_updates,
                "backup_created": backup_original,
                "executed_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "config_file": config_file,
                "updates": config_updates,
                "error": str(e),
                "executed_at": datetime.utcnow().isoformat()
            }


class AutomationEngine:
    """自动化引擎"""

    def __init__(self):
        self.rules: Dict[str, AutomationRule] = []
        self.executors: Dict[ActionType, ActionExecutor] = {}
        self.executions: List[AutomationExecution] = []
        self.max_executions = 10000
        self._register_default_executors()
        self._load_default_rules()

    def _register_default_executors(self):
        """注册默认执行器"""
        self.executors = {
            ActionType.RESTART_SERVICE: RestartServiceExecutor(),
            ActionType.SCALE_RESOURCES: ScaleResourcesExecutor(),
            ActionType.CLEANUP_LOGS: CleanupLogsExecutor(),
            ActionType.SEND_ALERT: SendAlertExecutor(),
            ActionType.EXECUTE_SCRIPT: ExecuteScriptExecutor(),
            ActionType.ADJUST_CONFIG: AdjustConfigExecutor()
        }

    def _load_default_rules(self):
        """加载默认规则"""
        default_rules = [
            # 自动重启失败的服务
            AutomationRule(
                rule_id="auto_restart_failed_service",
                name="Auto Restart Failed Service",
                description="Automatically restart services when they become unhealthy",
                triggers=[
                    Trigger(
                        trigger_id="service_unhealthy",
                        name="Service Unhealthy",
                        description="Trigger when service health check fails",
                        trigger_type=TriggerType.HEALTH_CHECK,
                        condition={
                            "status": "unhealthy",
                            "component_id": "database_connection"
                        },
                        cooldown_seconds=600  # 10分钟冷却期
                    )
                ],
                actions=[
                    Action(
                        action_id="restart_service",
                        name="Restart Service",
                        description="Restart the failed service",
                        action_type=ActionType.RESTART_SERVICE,
                        parameters={
                            "service_name": "aihub-backend"
                        },
                        timeout_seconds=60,
                        max_retries=2
                    )
                ]
            ),

            # 自动清理日志
            AutomationRule(
                rule_id="auto_cleanup_logs",
                name="Auto Cleanup Logs",
                description="Automatically clean up old log files",
                triggers=[
                    Trigger(
                        trigger_id="scheduled_log_cleanup",
                        name="Scheduled Log Cleanup",
                        description="Trigger log cleanup daily",
                        trigger_type=TriggerType.SCHEDULE,
                        condition={
                            "type": "daily",
                            "hour": 2  # 凌晨2点执行
                        }
                    )
                ],
                actions=[
                    Action(
                        action_id="cleanup_application_logs",
                        name="Cleanup Application Logs",
                        description="Clean up old application log files",
                        action_type=ActionType.CLEANUP_LOGS,
                        parameters={
                            "log_path": "logs/",
                            "retention_days": 7
                        },
                        timeout_seconds=300
                    )
                ]
            ),

            # 磁盘空间不足时的清理
            AutomationRule(
                rule_id="auto_cleanup_on_disk_full",
                name="Auto Cleanup on Disk Full",
                description="Automatically clean up when disk space is low",
                triggers=[
                    Trigger(
                        trigger_id="disk_space_low",
                        name="Disk Space Low",
                        description="Trigger when disk usage is high",
                        trigger_type=TriggerType.METRIC_THRESHOLD,
                        condition={
                            "metric_name": "disk_usage_percent",
                            "operator": "gt",
                            "threshold": 90.0
                        },
                        cooldown_seconds=1800  # 30分钟冷却期
                    )
                ],
                actions=[
                    Action(
                        action_id="cleanup_logs_disk_full",
                        name="Cleanup Logs (Emergency)",
                        description="Clean up logs to free disk space",
                        action_type=ActionType.CLEANUP_LOGS,
                        parameters={
                            "log_path": "logs/",
                            "retention_days": 3  # 只保留3天
                        },
                        timeout_seconds=180
                    ),
                    Action(
                        action_id="send_disk_full_alert",
                        name="Send Disk Full Alert",
                        description="Send alert about disk space issue",
                        action_type=ActionType.SEND_ALERT,
                        parameters={
                            "alert_type": "email",
                            "recipients": ["admin@aihub.com"],
                            "message": "Disk usage is critical. Automated cleanup has been initiated.",
                            "severity": "critical"
                        },
                        timeout_seconds=30
                    )
                ]
            ),

            # 错误爆发告警
            AutomationRule(
                rule_id="error_burst_alert",
                name="Error Burst Alert",
                description="Send alert when error burst is detected",
                triggers=[
                    Trigger(
                        trigger_id="error_burst_detected",
                        name="Error Burst Detected",
                        description="Trigger when log anomaly indicates error burst",
                        trigger_type=TriggerType.LOG_ANOMALY,
                        condition={
                            "anomaly_type": "error_burst"
                        },
                        cooldown_seconds=1800  # 30分钟冷却期
                    )
                ],
                actions=[
                    Action(
                        action_id="send_error_burst_alert",
                        name="Send Error Burst Alert",
                        description="Send alert about error burst",
                        action_type=ActionType.SEND_ALERT,
                        parameters={
                            "alert_type": "email",
                            "recipients": ["ops@aihub.com"],
                            "message": "Error burst detected in the system. Please investigate immediately.",
                            "severity": "critical"
                        },
                        timeout_seconds=30
                    )
                ]
            )
        ]

        for rule in default_rules:
            self.rules.append(rule)

    async def evaluate_triggers(self, context: Dict[str, Any]) -> List[str]:
        """评估触发器"""
        triggered_rules = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            # 检查规则的所有触发器
            for trigger in rule.triggers:
                if trigger.should_trigger(context):
                    triggered_rules.append(rule.rule_id)
                    trigger.mark_triggered()
                    logger.info(f"Automation rule triggered: {rule.name} (trigger: {trigger.name})")
                    break  # 一个规则只需要一个触发器激活

        return triggered_rules

    async def execute_rule(self, rule_id: str, trigger_id: str, context: Dict[str, Any]) -> AutomationExecution:
        """执行自动化规则"""
        rule = next((r for r in self.rules if r.rule_id == rule_id), None)
        if not rule:
            raise ValueError(f"Rule not found: {rule_id}")

        execution = AutomationExecution(
            execution_id=str(uuid.uuid4()),
            rule_id=rule_id,
            trigger_id=trigger_id,
            status=AutomationStatus.RUNNING,
            started_at=datetime.utcnow()
        )

        try:
            logger.info(f"Executing automation rule: {rule.name}")

            # 执行所有动作
            for action in rule.actions:
                if not action.enabled:
                    continue

                action_result = await self._execute_action(action, context)
                execution.results.append(action_result)

                # 如果动作失败且设置了重试
                if not action_result.get("success", True) and action.retry_count < action.max_retries:
                    logger.warning(f"Action {action.name} failed, retrying... ({action.retry_count + 1}/{action.max_retries})")
                    action.retry_count += 1
                    await asyncio.sleep(5)  # 等待5秒后重试
                    await self._execute_action(action, context)

            execution.status = AutomationStatus.COMPLETED
            rule.success_count += 1
            logger.info(f"Automation rule completed successfully: {rule.name}")

        except Exception as e:
            execution.status = AutomationStatus.FAILED
            execution.error_message = str(e)
            logger.error(f"Automation rule failed: {rule.name} - {e}")

        finally:
            execution.completed_at = datetime.utcnow()
            rule.last_executed = execution.completed_at
            rule.execution_count += 1

            # 记录执行历史
            self.executions.append(execution)
            if len(self.executions) > self.max_executions:
                self.executions = self.executions[-self.max_executions]

        return execution

    async def _execute_action(self, action: Action, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个动作"""
        executor = self.executors.get(action.action_type)
        if not executor:
            raise ValueError(f"No executor found for action type: {action.action_type}")

        logger.info(f"Executing action: {action.name} ({action.action_type.value})")
        return await executor.execute(action, context)

    def add_rule(self, rule: AutomationRule):
        """添加自动化规则"""
        self.rules.append(rule)
        logger.info(f"Added automation rule: {rule.name}")

    def remove_rule(self, rule_id: str) -> bool:
        """移除自动化规则"""
        original_count = len(self.rules)
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        return len(self.rules) < original_count

    def enable_rule(self, rule_id: str, enabled: bool = True):
        """启用/禁用规则"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.enabled = enabled
                logger.info(f"Rule {rule.name} {'enabled' if enabled else 'disabled'}")
                return True
        return False

    async def get_rule_executions(
        self,
        rule_id: Optional[str] = None,
        status: Optional[AutomationStatus] = None,
        hours: int = 24
    ) -> List[AutomationExecution]:
        """获取规则执行历史"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        executions = self.executions
        if rule_id:
            executions = [e for e in executions if e.rule_id == rule_id]
        if status:
            executions = [e for e in executions if e.status == status]
        if cutoff_time:
            executions = [e for e in executions if e.started_at >= cutoff_time]

        return executions

    def get_rule_statistics(self) -> Dict[str, Any]:
        """获取规则统计"""
        total_rules = len(self.rules)
        enabled_rules = len([r for r in self.rules if r.enabled])

        execution_stats = defaultdict(int)
        success_stats = defaultdict(int)

        for execution in self.executions:
            execution_stats[execution.rule_id] += 1
            if execution.status == AutomationStatus.COMPLETED:
                success_stats[execution.rule_id] += 1

        rule_stats = []
        for rule in self.rules:
            total_exec = execution_stats.get(rule.rule_id, 0)
            success_exec = success_stats.get(rule.rule_id, 0)
            success_rate = (success_exec / total_exec * 100) if total_exec > 0 else 0

            rule_stats.append({
                "rule_id": rule.rule_id,
                "name": rule.name,
                "enabled": rule.enabled,
                "total_executions": total_exec,
                "successful_executions": success_exec,
                "success_rate": round(success_rate, 2),
                "last_executed": rule.last_executed.isoformat() if rule.last_executed else None
            })

        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "rule_statistics": rule_stats,
            "total_executions": len(self.executions)
        }

    async def start_automation_engine(self):
        """启动自动化引擎"""
        logger.info("Starting automation engine...")

        async def monitoring_loop():
            """监控循环"""
            while True:
                try:
                    # 收集系统状态上下文
                    context = await self._collect_system_context()

                    # 评估触发器
                    triggered_rules = await self.evaluate_triggers(context)

                    # 执行触发的规则
                    for rule_id in triggered_rules:
                        try:
                            await self.execute_rule(rule_id, "auto", context)
                        except Exception as e:
                            logger.error(f"Failed to execute rule {rule_id}: {e}")

                    # 等待下一次评估
                    await asyncio.sleep(60)  # 每分钟评估一次

                except Exception as e:
                    logger.error(f"Automation monitoring loop error: {e}")
                    await asyncio.sleep(60)

        asyncio.create_task(monitoring_loop())
        logger.info("Automation engine started")

    async def _collect_system_context(self) -> Dict[str, Any]:
        """收集系统状态上下文"""
        context = {}

        # 收集健康状态
        try:
            from backend.health.deep_health_checker import get_deep_health_checker
            health_checker = await get_deep_health_checker()
            context["health_status"] = await health_checker.get_overall_health()
        except Exception as e:
            logger.error(f"Failed to collect health status: {e}")

        # 收集日志异常
        try:
            from backend.core.logging.advanced_logging import get_advanced_log_manager
            log_manager = await get_advanced_log_manager()
            anomalies = await log_manager.get_log_anomalies(hours=1)
            context["log_anomalies"] = [a.to_dict() for a in anomalies]
        except Exception as e:
            logger.error(f"Failed to collect log anomalies: {e}")

        # 收集系统指标
        try:
            context["metrics"] = {
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
            }
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")

        return context


# 全局自动化引擎实例
automation_engine = AutomationEngine()


async def get_automation_engine() -> AutomationEngine:
    """获取自动化引擎实例"""
    return automation_engine