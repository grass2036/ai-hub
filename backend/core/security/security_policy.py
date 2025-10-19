"""
安全策略管理
Week 6 Day 4: 安全加固和权限配置

提供安全策略定义、执行和监控功能
"""

import asyncio
import re
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import redis
import logging
from fastapi import HTTPException, Request

class PolicyType(Enum):
    """策略类型"""
    PASSWORD_POLICY = "password_policy"
    SESSION_POLICY = "session_policy"
    RATE_LIMIT_POLICY = "rate_limit_policy"
    IP_WHITELIST_POLICY = "ip_whitelist_policy"
    IP_BLACKLIST_POLICY = "ip_blacklist_policy"
    ACCESS_TIME_POLICY = "access_time_policy"
    DATA_RETENTION_POLICY = "data_retention_policy"
    ENCRYPTION_POLICY = "encryption_policy"

class PolicyAction(Enum):
    """策略动作"""
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"
    LOG = "log"
    QUARANTINE = "quarantine"

@dataclass
class PolicyRule:
    """策略规则"""
    id: str
    name: str
    description: str
    policy_type: PolicyType
    conditions: Dict[str, Any]
    action: PolicyAction
    priority: int = 0
    enabled: bool = True
    created_at: datetime = None
    updated_at: datetime = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "policy_type": self.policy_type.value,
            "conditions": self.conditions,
            "action": self.action.value,
            "priority": self.priority,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

@dataclass
class PolicyViolation:
    """策略违规"""
    id: str
    rule_id: str
    rule_name: str
    policy_type: PolicyType
    user_id: Optional[str]
    ip_address: Optional[str]
    resource: Optional[str]
    details: Dict[str, Any]
    severity: str
    action_taken: PolicyAction
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "policy_type": self.policy_type.value,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "resource": self.resource,
            "details": self.details,
            "severity": self.severity,
            "action_taken": self.action_taken.value,
            "timestamp": self.timestamp.isoformat()
        }

class PasswordPolicyValidator:
    """密码策略验证器"""

    @staticmethod
    def validate_password(password: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        """验证密码是否符合策略"""
        result = {
            "valid": True,
            "errors": [],
            "score": 0
        }

        # 长度检查
        min_length = policy.get("min_length", 8)
        max_length = policy.get("max_length", 128)

        if len(password) < min_length:
            result["valid"] = False
            result["errors"].append(f"密码长度不能少于{min_length}位")

        if len(password) > max_length:
            result["valid"] = False
            result["errors"].append(f"密码长度不能超过{max_length}位")

        # 复杂度检查
        if policy.get("require_uppercase", False):
            if not re.search(r'[A-Z]', password):
                result["valid"] = False
                result["errors"].append("密码必须包含大写字母")

        if policy.get("require_lowercase", False):
            if not re.search(r'[a-z]', password):
                result["valid"] = False
                result["errors"].append("密码必须包含小写字母")

        if policy.get("require_digits", False):
            if not re.search(r'\d', password):
                result["valid"] = False
                result["errors"].append("密码必须包含数字")

        if policy.get("require_special_chars", False):
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                result["valid"] = False
                result["errors"].append("密码必须包含特殊字符")

        # 禁用模式检查
        forbidden_patterns = policy.get("forbidden_patterns", [])
        for pattern in forbidden_patterns:
            if re.search(pattern, password, re.IGNORECASE):
                result["valid"] = False
                result["errors"].append("密码包含禁止使用的模式")

        # 常见密码检查
        common_passwords = policy.get("common_passwords", [])
        if password.lower() in [p.lower() for p in common_passwords]:
            result["valid"] = False
            result["errors"].append("不能使用常见密码")

        # 计算密码强度分数
        result["score"] = PasswordPolicyValidator._calculate_password_score(password, policy)

        return result

    @staticmethod
    def _calculate_password_score(password: str, policy: Dict[str, Any]) -> int:
        """计算密码强度分数"""
        score = 0

        # 长度分数
        length_score = min(len(password) / 12, 1) * 30
        score += length_score

        # 字符类型分数
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 15

        # 复杂性分数
        unique_chars = len(set(password))
        complexity_score = min(unique_chars / len(password), 1) * 25
        score += complexity_score

        return min(int(score), 100)

class SessionPolicyValidator:
    """会话策略验证器"""

    @staticmethod
    def validate_session(
        session_data: Dict[str, Any],
        policy: Dict[str, Any],
        current_request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """验证会话是否符合策略"""
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # 会话超时检查
        max_idle_time = policy.get("max_idle_time", 3600)  # 1小时
        max_session_time = policy.get("max_session_time", 86400)  # 24小时

        now = datetime.utcnow()
        last_activity = session_data.get("last_activity", session_data.get("created_at", now))

        idle_time = (now - last_activity).total_seconds()
        session_time = (now - session_data.get("created_at", now)).total_seconds()

        if idle_time > max_idle_time:
            result["valid"] = False
            result["errors"].append("会话因闲置时间过长而失效")

        if session_time > max_session_time:
            result["valid"] = False
            result["errors"].append("会话因持续时间过长而失效")

        # IP地址检查
        if policy.get("require_same_ip", False) and current_request:
            current_ip = current_request.client.host if current_request.client else None
            original_ip = session_data.get("ip_address")

            if current_ip and original_ip and current_ip != original_ip:
                result["valid"] = False
                result["errors"].append("会话IP地址不匹配")

        # 并发会话检查
        max_concurrent_sessions = policy.get("max_concurrent_sessions", 5)
        user_id = session_data.get("user_id")
        if user_id and policy.get("enforce_concurrent_limit", False):
            # 这里应该检查用户当前的活跃会话数
            # 简化实现
            pass

        # 设备指纹检查
        if policy.get("require_device_fingerprint", False):
            current_fingerprint = current_request.headers.get("X-Device-Fingerprint") if current_request else None
            original_fingerprint = session_data.get("device_fingerprint")

            if current_fingerprint and original_fingerprint and current_fingerprint != original_fingerprint:
                result["warnings"].append("设备指纹发生变化")

        return result

class RateLimitPolicyValidator:
    """速率限制策略验证器"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client

    async def validate_rate_limit(
        self,
        identifier: str,  # 用户ID、IP地址等
        resource: str,    # API端点、操作类型等
        policy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证速率限制"""
        result = {
            "allowed": True,
            "remaining": 0,
            "reset_time": None,
            "retry_after": None
        }

        if not self.redis_client:
            return result

        # 获取策略参数
        window_size = policy.get("window_size", 3600)  # 时间窗口（秒）
        max_requests = policy.get("max_requests", 100)  # 最大请求数
        burst_size = policy.get("burst_size", max_requests // 10)  # 突发大小

        current_time = int(datetime.now().timestamp())
        window_start = current_time - window_size

        # Redis键
        key = f"rate_limit:{identifier}:{resource}"
        sliding_window_key = f"rate_limit:sliding:{identifier}:{resource}"

        # 使用滑动窗口算法
        await self.redis_client.zremrangebyscore(sliding_window_key, 0, window_start)
        current_requests = await self.redis_client.zcard(sliding_window_key)

        if current_requests >= max_requests:
            # 超出限制
            result["allowed"] = False

            # 计算重试时间
            oldest_request = await self.redis_client.zrange(sliding_window_key, 0, 0, withscores=True)
            if oldest_request:
                _, timestamp = oldest_request[0]
                retry_after = int(timestamp + window_size - current_time)
                result["retry_after"] = max(retry_after, 1)

        else:
            # 记录当前请求
            await self.redis_client.zadd(sliding_window_key, {str(current_time): current_time})
            await self.redis_client.expire(sliding_window_key, window_size)

            result["remaining"] = max(0, max_requests - current_requests - 1)

        result["reset_time"] = current_time + window_size

        return result

class IPAccessPolicyValidator:
    """IP访问策略验证器"""

    @staticmethod
    def validate_ip_access(
        ip_address: str,
        whitelist: List[str] = None,
        blacklist: List[str] = None
    ) -> Dict[str, Any]:
        """验证IP访问权限"""
        result = {
            "allowed": True,
            "reason": "",
            "matched_rule": None
        }

        try:
            ip = ipaddress.ip_address(ip_address)
        except ValueError:
            result["allowed"] = False
            result["reason"] = "无效的IP地址"
            return result

        # 检查黑名单
        if blacklist:
            for blocked_ip in blacklist:
                try:
                    if ip in ipaddress.ip_network(blocked_ip, strict=False):
                        result["allowed"] = False
                        result["reason"] = "IP地址在黑名单中"
                        result["matched_rule"] = blocked_ip
                        return result
                except ValueError:
                    continue

        # 检查白名单
        if whitelist:
            for allowed_ip in whitelist:
                try:
                    if ip in ipaddress.ip_network(allowed_ip, strict=False):
                        result["matched_rule"] = allowed_ip
                        return result
                except ValueError:
                    continue

            # 如果有白名单但IP不在其中，则拒绝访问
            result["allowed"] = False
            result["reason"] = "IP地址不在白名单中"
            return result

        return result

class AccessTimePolicyValidator:
    """访问时间策略验证器"""

    @staticmethod
    def validate_access_time(
        current_time: datetime,
        policy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证访问时间"""
        result = {
            "allowed": True,
            "reason": "",
            "next_allowed_time": None
        }

        if not policy.get("enabled", False):
            return result

        # 获取时区设置
        timezone = policy.get("timezone", "UTC")

        # 检查工作日限制
        allowed_weekdays = policy.get("allowed_weekdays")
        if allowed_weekdays:
            current_weekday = current_time.weekday()  # 0=Monday, 6=Sunday
            if current_weekday not in allowed_weekdays:
                result["allowed"] = False
                result["reason"] = "当前时间不在允许的工作日内"
                return result

        # 检查时间范围限制
        time_ranges = policy.get("allowed_time_ranges")
        if time_ranges:
            current_time_only = current_time.time()
            allowed = False

            for time_range in time_ranges:
                start_time = datetime.strptime(time_range["start"], "%H:%M").time()
                end_time = datetime.strptime(time_range["end"], "%H:%M").time()

                if start_time <= current_time_only <= end_time:
                    allowed = True
                    break

            if not allowed:
                result["allowed"] = False
                result["reason"] = "当前时间不在允许的时间范围内"

                # 计算下一个允许访问的时间
                next_allowed = AccessTimePolicyValidator._calculate_next_allowed_time(
                    current_time, time_ranges, allowed_weekdays
                )
                if next_allowed:
                    result["next_allowed_time"] = next_allowed

        return result

    @staticmethod
    def _calculate_next_allowed_time(
        current_time: datetime,
        time_ranges: List[Dict[str, str]],
        allowed_weekdays: Optional[List[int]] = None
    ) -> Optional[datetime]:
        """计算下一个允许访问的时间"""
        # 简化实现，实际应该更精确地计算
        tomorrow = current_time + timedelta(days=1)
        return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)

class SecurityPolicyManager:
    """安全策略管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.rules: Dict[str, PolicyRule] = {}
        self.validators = {
            PolicyType.PASSWORD_POLICY: PasswordPolicyValidator(),
            PolicyType.SESSION_POLICY: SessionPolicyValidator(),
            PolicyType.RATE_LIMIT_POLICY: RateLimitPolicyValidator(),
            PolicyType.IP_WHITELIST_POLICY: IPAccessPolicyValidator(),
            PolicyType.IP_BLACKLIST_POLICY: IPAccessPolicyValidator(),
            PolicyType.ACCESS_TIME_POLICY: AccessTimePolicyValidator()
        }

    async def initialize(self, redis_client: Optional[redis.Redis] = None) -> None:
        """初始化安全策略管理器"""
        self.redis_client = redis_client

        # 初始化默认策略
        await self._initialize_default_policies()

    async def create_policy_rule(
        self,
        name: str,
        description: str,
        policy_type: PolicyType,
        conditions: Dict[str, Any],
        action: PolicyAction,
        priority: int = 0
    ) -> PolicyRule:
        """创建策略规则"""
        rule = PolicyRule(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            policy_type=policy_type,
            conditions=conditions,
            action=action,
            priority=priority,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # 存储到Redis
        if self.redis_client:
            await self._store_policy_rule(rule)

        self.rules[rule.id] = rule
        return rule

    async def evaluate_policy(
        self,
        policy_type: PolicyType,
        context: Dict[str, Any],
        user_id: Optional[str] = None,
        resource: Optional[str] = None
    ) -> Dict[str, Any]:
        """评估策略"""
        result = {
            "allowed": True,
            "action": PolicyAction.ALLOW,
            "violations": [],
            "applied_rules": []
        }

        # 获取适用的策略规则
        applicable_rules = await self._get_applicable_rules(policy_type, context, user_id, resource)

        # 按优先级排序
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)

        for rule in applicable_rules:
            if not rule.enabled:
                continue

            # 评估规则条件
            if await self._evaluate_rule_conditions(rule, context):
                result["applied_rules"].append(rule)

                # 执行策略动作
                action_result = await self._execute_policy_action(rule, context)
                result["violations"].append(action_result)

                # 如果是拒绝动作，立即返回
                if rule.action == PolicyAction.DENY:
                    result["allowed"] = False
                    result["action"] = PolicyAction.DENY
                    break

        return result

    async def validate_password(self, password: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """验证密码"""
        context = {"password": password, "user_id": user_id}
        result = await self.evaluate_policy(PolicyType.PASSWORD_POLICY, context, user_id)

        # 使用专门的密码验证器
        password_policy = self._get_password_policy()
        if password_policy:
            validation_result = PasswordPolicyValidator.validate_password(password, password_policy)
            result["password_validation"] = validation_result

            if not validation_result["valid"]:
                result["allowed"] = False
                result["action"] = PolicyAction.DENY

        return result

    async def validate_session(
        self,
        session_data: Dict[str, Any],
        current_request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """验证会话"""
        context = {
            "session_data": session_data,
            "request": current_request
        }
        user_id = session_data.get("user_id")

        result = await self.evaluate_policy(PolicyType.SESSION_POLICY, context, user_id)

        # 使用专门的会话验证器
        session_policy = self._get_session_policy()
        if session_policy:
            validation_result = SessionPolicyValidator.validate_session(
                session_data, session_policy, current_request
            )
            result["session_validation"] = validation_result

            if not validation_result["valid"]:
                result["allowed"] = False
                result["action"] = PolicyAction.DENY

        return result

    async def check_rate_limit(
        self,
        identifier: str,
        resource: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """检查速率限制"""
        context = {
            "identifier": identifier,
            "resource": resource
        }

        result = await self.evaluate_policy(PolicyType.RATE_LIMIT_POLICY, context, user_id)

        # 使用专门的速率限制验证器
        rate_limit_policy = self._get_rate_limit_policy()
        if rate_limit_policy:
            validator = RateLimitPolicyValidator(self.redis_client)
            validation_result = await validator.validate_rate_limit(identifier, resource, rate_limit_policy)
            result["rate_limit_validation"] = validation_result

            if not validation_result["allowed"]:
                result["allowed"] = False
                result["action"] = PolicyAction.DENY

        return result

    async def validate_ip_access(
        self,
        ip_address: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """验证IP访问"""
        context = {"ip_address": ip_address}
        result = await self.evaluate_policy(PolicyType.IP_WHITELIST_POLICY, context, user_id)

        # 检查黑名单策略
        blacklist_result = await self.evaluate_policy(PolicyType.IP_BLACKLIST_POLICY, context, user_id)

        # 使用专门的IP访问验证器
        whitelist = self._get_ip_whitelist()
        blacklist = self._get_ip_blacklist()

        validation_result = IPAccessPolicyValidator.validate_ip_access(ip_address, whitelist, blacklist)
        result["ip_validation"] = validation_result

        if not validation_result["allowed"]:
            result["allowed"] = False
            result["action"] = PolicyAction.DENY

        return result

    async def validate_access_time(
        self,
        current_time: Optional[datetime] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """验证访问时间"""
        if current_time is None:
            current_time = datetime.utcnow()

        context = {"current_time": current_time}
        result = await self.evaluate_policy(PolicyType.ACCESS_TIME_POLICY, context, user_id)

        # 使用专门的访问时间验证器
        access_time_policy = self._get_access_time_policy()
        if access_time_policy:
            validation_result = AccessTimePolicyValidator.validate_access_time(current_time, access_time_policy)
            result["access_time_validation"] = validation_result

            if not validation_result["allowed"]:
                result["allowed"] = False
                result["action"] = PolicyAction.DENY

        return result

    async def _initialize_default_policies(self) -> None:
        """初始化默认策略"""
        # 密码策略
        await self.create_policy_rule(
            "default_password_policy",
            "默认密码策略",
            PolicyType.PASSWORD_POLICY,
            {
                "min_length": 8,
                "max_length": 128,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_digits": True,
                "require_special_chars": True,
                "forbidden_patterns": ["password", "123456", "qwerty"],
                "min_score": 60
            },
            PolicyAction.DENY,
            priority=100
        )

        # 会话策略
        await self.create_policy_rule(
            "default_session_policy",
            "默认会话策略",
            PolicyType.SESSION_POLICY,
            {
                "max_idle_time": 3600,  # 1小时
                "max_session_time": 28800,  # 8小时
                "require_same_ip": False,
                "max_concurrent_sessions": 5
            },
            PolicyAction.WARN,
            priority=100
        )

        # 速率限制策略
        await self.create_policy_rule(
            "default_rate_limit_policy",
            "默认速率限制策略",
            PolicyType.RATE_LIMIT_POLICY,
            {
                "window_size": 3600,  # 1小时
                "max_requests": 1000,
                "burst_size": 100
            },
            PolicyAction.DENY,
            priority=100
        )

    async def _store_policy_rule(self, rule: PolicyRule) -> None:
        """存储策略规则到Redis"""
        if not self.redis_client:
            return

        key = f"policy_rule:{rule.id}"
        await self.redis_client.hset(key, mapping={
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "policy_type": rule.policy_type.value,
            "conditions": json.dumps(rule.conditions),
            "action": rule.action.value,
            "priority": str(rule.priority),
            "enabled": str(rule.enabled),
            "created_at": rule.created_at.isoformat(),
            "updated_at": rule.updated_at.isoformat()
        })
        await self.redis_client.sadd(f"policy_rules:{rule.policy_type.value}", rule.id)

    async def _get_applicable_rules(
        self,
        policy_type: PolicyType,
        context: Dict[str, Any],
        user_id: Optional[str] = None,
        resource: Optional[str] = None
    ) -> List[PolicyRule]:
        """获取适用的策略规则"""
        if not self.redis_client:
            return []

        rule_ids = await self.redis_client.smembers(f"policy_rules:{policy_type.value}")
        rules = []

        for rule_id in rule_ids:
            rule = await self._get_policy_rule_by_id(rule_id)
            if rule and rule.enabled:
                rules.append(rule)

        return rules

    async def _get_policy_rule_by_id(self, rule_id: str) -> Optional[PolicyRule]:
        """根据ID获取策略规则"""
        if rule_id in self.rules:
            return self.rules[rule_id]

        if not self.redis_client:
            return None

        data = await self.redis_client.hgetall(f"policy_rule:{rule_id}")
        if not data:
            return None

        rule = PolicyRule(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            policy_type=PolicyType(data["policy_type"]),
            conditions=json.loads(data["conditions"]),
            action=PolicyAction(data["action"]),
            priority=int(data["priority"]),
            enabled=data["enabled"] == "True",
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )

        self.rules[rule_id] = rule
        return rule

    async def _evaluate_rule_conditions(self, rule: PolicyRule, context: Dict[str, Any]) -> bool:
        """评估规则条件"""
        # 这里应该根据规则类型和条件进行评估
        # 简化实现，总是返回True
        return True

    async def _execute_policy_action(self, rule: PolicyRule, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行策略动作"""
        violation = {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "policy_type": rule.policy_type,
            "action_taken": rule.action,
            "timestamp": datetime.utcnow(),
            "details": context
        }

        # 记录违规
        if self.redis_client:
            await self._record_policy_violation(violation)

        return violation

    async def _record_policy_violation(self, violation: Dict[str, Any]) -> None:
        """记录策略违规"""
        if not self.redis_client:
            return

        violation_id = str(uuid.uuid4())
        key = f"policy_violation:{violation_id}"
        await self.redis_client.hset(key, mapping={
            "id": violation_id,
            "rule_id": violation["rule_id"],
            "rule_name": violation["rule_name"],
            "policy_type": violation["policy_type"].value,
            "action_taken": violation["action_taken"].value,
            "timestamp": violation["timestamp"].isoformat(),
            "details": json.dumps(violation["details"])
        })

        # 保留30天
        await self.redis_client.expire(key, 30 * 24 * 3600)

    def _get_password_policy(self) -> Optional[Dict[str, Any]]:
        """获取密码策略"""
        # 从配置或数据库获取密码策略
        return self.config.get("password_policy", {
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_digits": True,
            "require_special_chars": True
        })

    def _get_session_policy(self) -> Optional[Dict[str, Any]]:
        """获取会话策略"""
        return self.config.get("session_policy", {
            "max_idle_time": 3600,
            "max_session_time": 28800,
            "require_same_ip": False
        })

    def _get_rate_limit_policy(self) -> Optional[Dict[str, Any]]:
        """获取速率限制策略"""
        return self.config.get("rate_limit_policy", {
            "window_size": 3600,
            "max_requests": 1000,
            "burst_size": 100
        })

    def _get_ip_whitelist(self) -> List[str]:
        """获取IP白名单"""
        return self.config.get("ip_whitelist", [])

    def _get_ip_blacklist(self) -> List[str]:
        """获取IP黑名单"""
        return self.config.get("ip_blacklist", [])

    def _get_access_time_policy(self) -> Optional[Dict[str, Any]]:
        """获取访问时间策略"""
        return self.config.get("access_time_policy", {
            "enabled": False
        })

# 导入uuid
import uuid