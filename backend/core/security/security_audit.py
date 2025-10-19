"""
安全审计系统
Week 6 Day 4: 安全加固和权限配置

提供全面的安全事件记录、分析和报告功能
"""

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import redis
import logging
from collections import defaultdict, deque
import geoip2.database
import geoip2.errors

class SecurityEventType(Enum):
    """安全事件类型"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    ROLE_CHANGED = "role_changed"
    API_KEY_CREATED = "api_key_created"
    API_KEY_DELETED = "api_key_deleted"
    API_KEY_USED = "api_key_used"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_POLICY_VIOLATION = "security_policy_violation"
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    ENCRYPTION_KEY_ROTATION = "encryption_key_rotation"
    BACKUP_ACCESS = "backup_access"
    ADMIN_ACTION = "admin_action"

class SecurityEventSeverity(Enum):
    """安全事件严重级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatLevel(Enum):
    """威胁级别"""
    SAFE = "safe"
    LOW_RISK = "low_risk"
    MEDIUM_RISK = "medium_risk"
    HIGH_RISK = "high_risk"
    CRITICAL = "critical"

@dataclass
class SecurityEvent:
    """安全事件"""
    id: str
    event_type: SecurityEventType
    severity: SecurityEventSeverity
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: str
    user_agent: str
    resource: Optional[str]
    action: str
    details: Dict[str, Any]
    timestamp: datetime
    success: bool
    risk_score: float = 0.0
    threat_indicators: List[str] = None
    location: Optional[Dict[str, str]] = None
    device_fingerprint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource": self.resource,
            "action": self.action,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "risk_score": self.risk_score,
            "threat_indicators": self.threat_indicators or [],
            "location": self.location,
            "device_fingerprint": self.device_fingerprint
        }

@dataclass
class ThreatPattern:
    """威胁模式"""
    id: str
    name: str
    description: str
    pattern_type: str
    conditions: Dict[str, Any]
    risk_score: float
    severity: SecurityEventSeverity
    enabled: bool = True
    created_at: datetime = None

@dataclass
class SecurityAlert:
    """安全告警"""
    id: str
    alert_type: str
    severity: SecurityEventSeverity
    title: str
    description: str
    events: List[str]  # 事件ID列表
    risk_score: float
    status: str = "open"  # open, acknowledged, resolved, false_positive
    created_at: datetime = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    metadata: Dict[str, Any] = None

class ThreatDetector:
    """威胁检测器"""

    def __init__(self):
        self.patterns: Dict[str, ThreatPattern] = []
        self._setup_default_patterns()

    def add_pattern(self, pattern: ThreatPattern) -> None:
        """添加威胁模式"""
        self.patterns.append(pattern)

    def detect_threats(self, event: SecurityEvent) -> List[ThreatPattern]:
        """检测威胁"""
        detected_threats = []

        for pattern in self.patterns:
            if not pattern.enabled:
                continue

            if self._match_pattern(event, pattern):
                detected_threats.append(pattern)

        return detected_threats

    def _match_pattern(self, event: SecurityEvent, pattern: ThreatPattern) -> bool:
        """匹配威胁模式"""
        conditions = pattern.conditions

        # 事件类型匹配
        if "event_types" in conditions:
            if event.event_type not in [SecurityEventType(t) for t in conditions["event_types"]]:
                return False

        # 失败次数检测
        if "failure_count" in conditions:
            # 这里需要查询历史事件来检测失败次数
            # 简化实现
            pass

        # IP地址检测
        if "suspicious_ips" in conditions:
            if event.ip_address in conditions["suspicious_ips"]:
                return True

        # 时间模式检测
        if "time_pattern" in conditions:
            time_pattern = conditions["time_pattern"]
            current_hour = event.timestamp.hour

            if time_pattern.get("unusual_hours"):
                if current_hour in time_pattern["unusual_hours"]:
                    return True

        # 地理位置检测
        if "geo_anomaly" in conditions and event.location:
            if self._is_geo_anomaly(event.location, conditions["geo_anomaly"]):
                return True

        # 设备指纹检测
        if "new_device" in conditions and event.device_fingerprint:
            # 检查是否是新设备
            # 简化实现
            pass

        return False

    def _is_geo_anomaly(self, location: Dict[str, str], geo_config: Dict[str, Any]) -> bool:
        """检测地理位置异常"""
        # 检查是否在风险国家/地区
        if "risk_countries" in geo_config:
            country = location.get("country", "")
            if country in geo_config["risk_countries"]:
                return True

        # 检查是否在异常时间从异常位置访问
        # 简化实现
        return False

    def _setup_default_patterns(self) -> None:
        """设置默认威胁模式"""
        default_patterns = [
            ThreatPattern(
                id="brute_force_attack",
                name="暴力破解攻击",
                description="检测短时间内大量登录失败",
                pattern_type="frequency",
                conditions={
                    "event_types": ["login_failure"],
                    "failure_count": 5,
                    "time_window": 300  # 5分钟内
                },
                risk_score=8.0,
                severity=SecurityEventSeverity.HIGH,
                created_at=datetime.utcnow()
            ),
            ThreatPattern(
                id="suspicious_location",
                name="可疑地理位置",
                description="检测来自异常地理位置的访问",
                pattern_type="geo",
                conditions={
                    "event_types": ["login_success", "login_failure"],
                    "geo_anomaly": {
                        "risk_countries": ["CN", "RU", "KP"]  # 示例风险国家
                    }
                },
                risk_score=6.0,
                severity=SecurityEventSeverity.MEDIUM,
                created_at=datetime.utcnow()
            ),
            ThreatPattern(
                id="unusual_access_time",
                name="异常访问时间",
                description="检测在非正常时间的访问",
                pattern_type="time",
                conditions={
                    "event_types": ["login_success"],
                    "time_pattern": {
                        "unusual_hours": [2, 3, 4, 5]  # 凌晨2-5点
                    }
                },
                risk_score=4.0,
                severity=SecurityEventSeverity.MEDIUM,
                created_at=datetime.utcnow()
            ),
            ThreatPattern(
                id="privilege_escalation",
                name="权限提升",
                description="检测权限提升尝试",
                pattern_type="privilege",
                conditions={
                    "event_types": ["permission_denied", "role_changed"]
                },
                risk_score=7.0,
                severity=SecurityEventSeverity.HIGH,
                created_at=datetime.utcnow()
            )
        ]

        for pattern in default_patterns:
            self.patterns.append(pattern)

class SecurityAuditor:
    """安全审计器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.threat_detector = ThreatDetector()
        self.events_buffer = deque(maxlen=10000)
        self.alerts: Dict[str, SecurityAlert] = {}
        self.geoip_reader = None  # GeoIP数据库读取器

    async def initialize(self, redis_client: Optional[redis.Redis] = None) -> None:
        """初始化安全审计器"""
        self.redis_client = redis_client

        # 初始化GeoIP数据库
        geoip_db_path = self.config.get("geoip_database_path")
        if geoip_db_path:
            try:
                self.geoip_reader = geoip2.database.Reader(geoip_db_path)
                logging.info("GeoIP database loaded successfully")
            except Exception as e:
                logging.warning(f"Failed to load GeoIP database: {str(e)}")

    async def record_event(
        self,
        event_type: SecurityEventType,
        severity: SecurityEventSeverity,
        ip_address: str,
        user_agent: str,
        action: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        resource: Optional[str] = None,
        success: bool = True
    ) -> str:
        """记录安全事件"""
        # 生成事件ID
        event_id = str(uuid.uuid4())

        # 获取地理位置信息
        location = await self._get_location_info(ip_address)

        # 计算风险分数
        risk_score = self._calculate_risk_score(
            event_type, severity, ip_address, details, location
        )

        # 检测威胁
        event = SecurityEvent(
            id=event_id,
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource=resource,
            action=action,
            details=details,
            timestamp=datetime.utcnow(),
            success=success,
            risk_score=risk_score,
            location=location,
            device_fingerprint=details.get("device_fingerprint")
        )

        # 威胁检测
        detected_threats = self.threat_detector.detect_threats(event)
        if detected_threats:
            event.threat_indicators = [t.name for t in detected_threats]
            # 更新风险分数
            event.risk_score = max(event.risk_score, max(t.risk_score for t in detected_threats))

        # 存储事件
        await self._store_event(event)

        # 添加到缓冲区
        self.events_buffer.append(event)

        # 检查是否需要生成告警
        await self._check_alert_conditions(event)

        return event_id

    async def _store_event(self, event: SecurityEvent) -> None:
        """存储安全事件"""
        if not self.redis_client:
            return

        # 存储事件详情
        event_key = f"security_event:{event.id}"
        event_data = asdict(event)
        event_data["event_type"] = event.event_type.value
        event_data["severity"] = event.severity.value
        event_data["timestamp"] = event.timestamp.isoformat()

        await self.redis_client.hset(event_key, mapping={
            k: str(v) if v is not None else "" for k, v in event_data.items()
        })

        # 设置过期时间（保留90天）
        await self.redis_client.expire(event_key, 90 * 24 * 3600)

        # 添加到索引
        await self._add_to_indexes(event)

    async def _add_to_indexes(self, event: SecurityEvent) -> None:
        """添加到索引"""
        if not self.redis_client:
            return

        # 用户事件索引
        if event.user_id:
            await self.redis_client.lpush(
                f"user_security_events:{event.user_id}",
                event.id
            )
            await self.redis_client.expire(
                f"user_security_events:{event.user_id}",
                7 * 24 * 3600  # 保留7天
            )

        # IP事件索引
        await self.redis_client.lpush(
            f"ip_security_events:{event.ip_address}",
            event.id
        )
        await self.redis_client.expire(
            f"ip_security_events:{event.ip_address}",
            7 * 24 * 3600
        )

        # 事件类型索引
        await self.redis_client.lpush(
            f"events_by_type:{event.event_type.value}",
            event.id
        )
        await self.redis_client.expire(
            f"events_by_type:{event.event_type.value}",
            30 * 24 * 3600  # 保留30天
        )

        # 高风险事件索引
        if event.risk_score >= 7.0:
            await self.redis_client.lpush("high_risk_events", event.id)
            await self.redis_client.expire("high_risk_events", 7 * 24 * 3600)

    async def _check_alert_conditions(self, event: SecurityEvent) -> None:
        """检查告警条件"""
        # 高风险事件告警
        if event.risk_score >= 8.0:
            await self._create_alert(
                alert_type="high_risk_event",
                severity=SecurityEventSeverity.CRITICAL,
                title=f"高风险安全事件: {event.event_type.value}",
                description=f"检测到高风险安全事件，风险分数: {event.risk_score}",
                events=[event.id],
                risk_score=event.risk_score
            )

        # 连续失败登录告警
        if event.event_type == SecurityEventType.LOGIN_FAILURE:
            await self._check_brute_force_alert(event)

        # 异常地理位置告警
        if event.threat_indicators and "suspicious_location" in event.threat_indicators:
            await self._create_alert(
                alert_type="suspicious_location",
                severity=SecurityEventSeverity.HIGH,
                title="可疑地理位置访问",
                description=f"检测到来自可疑地理位置的访问: {event.ip_address}",
                events=[event.id],
                risk_score=event.risk_score
            )

    async def _check_brute_force_alert(self, event: SecurityEvent) -> None:
        """检查暴力破解告警"""
        if not self.redis_client or not event.user_id:
            return

        # 检查最近15分钟的失败登录次数
        recent_failures = await self._get_recent_events(
            SecurityEventType.LOGIN_FAILURE,
            event.user_id,
            minutes=15
        )

        if len(recent_failures) >= 5:
            # 生成暴力破解告警
            await self._create_alert(
                alert_type="brute_force_attack",
                severity=SecurityEventSeverity.HIGH,
                title=f"暴力破解攻击检测: {event.user_id}",
                description=f"用户 {event.user_id} 在15分钟内登录失败 {len(recent_failures)} 次",
                events=[e.id for e in recent_failures],
                risk_score=8.5
            )

    async def _create_alert(
        self,
        alert_type: str,
        severity: SecurityEventSeverity,
        title: str,
        description: str,
        events: List[str],
        risk_score: float,
        metadata: Dict[str, Any] = None
    ) -> str:
        """创建安全告警"""
        alert_id = str(uuid.uuid4())

        alert = SecurityAlert(
            id=alert_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            events=events,
            risk_score=risk_score,
            created_at=datetime.utcnow(),
            metadata=metadata or {}
        )

        # 存储告警
        await self._store_alert(alert)
        self.alerts[alert_id] = alert

        logging.warning(f"Security alert created: {alert_id} - {title}")

        return alert_id

    async def _store_alert(self, alert: SecurityAlert) -> None:
        """存储安全告警"""
        if not self.redis_client:
            return

        alert_key = f"security_alert:{alert.id}"
        alert_data = asdict(alert)
        alert_data["severity"] = alert.severity.value
        alert_data["created_at"] = alert.created_at.isoformat()
        if alert.acknowledged_at:
            alert_data["acknowledged_at"] = alert.acknowledged_at.isoformat()
        if alert.resolved_at:
            alert_data["resolved_at"] = alert.resolved_at.isoformat()

        await self.redis_client.hset(alert_key, mapping={
            k: str(v) if v is not None else "" for k, v in alert_data.items()
        })

        # 添加到索引
        await self.redis_client.lpush("security_alerts", alert.id)
        await self.redis_client.expire("security_alerts", 90 * 24 * 3600)

    async def get_security_events(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None,
        event_type: Optional[SecurityEventType] = None,
        severity: Optional[SecurityEventSeverity] = None,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """获取安全事件"""
        if not self.redis_client:
            return list(self.events_buffer)[-limit:]

        events = []

        # 根据查询条件构建键
        if user_id:
            event_ids = await self.redis_client.lrange(f"user_security_events:{user_id}", 0, -1)
        elif event_type:
            event_ids = await self.redis_client.lrange(f"events_by_type:{event_type.value}", 0, -1)
        else:
            event_ids = await self.redis_client.lrange("all_security_events", 0, -1)

        # 获取事件详情
        for event_id in event_ids[:limit]:
            event = await self._get_event_by_id(event_id)
            if event and start_date <= event.timestamp <= end_date:
                if not severity or event.severity == severity:
                    events.append(event)

        return events

    async def get_security_alerts(
        self,
        status: Optional[str] = None,
        severity: Optional[SecurityEventSeverity] = None,
        limit: int = 50
    ) -> List[SecurityAlert]:
        """获取安全告警"""
        if not self.redis_client:
            return list(self.alerts.values())[:limit]

        alert_ids = await self.redis_client.lrange("security_alerts", 0, -1)
        alerts = []

        for alert_id in alert_ids[:limit]:
            alert = await self._get_alert_by_id(alert_id)
            if alert:
                if (not status or alert.status == status) and \
                   (not severity or alert.severity == severity):
                    alerts.append(alert)

        return alerts

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """确认安全告警"""
        if not self.redis_client:
            return False

        alert = await self._get_alert_by_id(alert_id)
        if not alert or alert.status != "open":
            return False

        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by

        await self._store_alert(alert)
        self.alerts[alert_id] = alert

        logging.info(f"Security alert {alert_id} acknowledged by {acknowledged_by}")
        return True

    async def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """解决安全告警"""
        if not self.redis_client:
            return False

        alert = await self._get_alert_by_id(alert_id)
        if not alert or alert.status in ["resolved", "false_positive"]:
            return False

        alert.status = "resolved"
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = resolved_by

        await self._store_alert(alert)
        self.alerts[alert_id] = alert

        logging.info(f"Security alert {alert_id} resolved by {resolved_by}")
        return True

    async def get_security_statistics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """获取安全统计"""
        events = await self.get_security_events(start_date, end_date)
        alerts = await self.get_security_alerts()

        # 事件统计
        event_stats = defaultdict(int)
        severity_stats = defaultdict(int)
        risk_score_stats = {"low": 0, "medium": 0, "high": 0, "critical": 0}

        for event in events:
            event_stats[event.event_type.value] += 1
            severity_stats[event.severity.value] += 1

            # 风险分数分类
            if event.risk_score < 3:
                risk_score_stats["low"] += 1
            elif event.risk_score < 6:
                risk_score_stats["medium"] += 1
            elif event.risk_score < 8:
                risk_score_stats["high"] += 1
            else:
                risk_score_stats["critical"] += 1

        # 告警统计
        alert_stats = defaultdict(int)
        alert_severity_stats = defaultdict(int)

        for alert in alerts:
            alert_stats[alert.status] += 1
            alert_severity_stats[alert.severity.value] += 1

        # 地理位置统计
        geo_stats = defaultdict(int)
        for event in events:
            if event.location and event.location.get("country"):
                geo_stats[event.location["country"]] += 1

        return {
            "time_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "events": {
                "total": len(events),
                "by_type": dict(event_stats),
                "by_severity": dict(severity_stats),
                "by_risk_score": risk_score_stats
            },
            "alerts": {
                "total": len(alerts),
                "by_status": dict(alert_stats),
                "by_severity": dict(alert_severity_stats)
            },
            "geographic": dict(geo_stats),
            "top_risky_ips": self._get_top_risky_ips(events),
            "top_risky_users": self._get_top_risky_users(events)
        }

    async def _get_event_by_id(self, event_id: str) -> Optional[SecurityEvent]:
        """根据ID获取安全事件"""
        if not self.redis_client:
            return None

        data = await self.redis_client.hgetall(f"security_event:{event_id}")
        if not data:
            return None

        return SecurityEvent(
            id=data["id"],
            event_type=SecurityEventType(data["event_type"]),
            severity=SecurityEventSeverity(data["severity"]),
            user_id=data.get("user_id") or None,
            session_id=data.get("session_id") or None,
            ip_address=data["ip_address"],
            user_agent=data["user_agent"],
            resource=data.get("resource") or None,
            action=data["action"],
            details=json.loads(data.get("details", "{}")),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            success=data["success"] == "True",
            risk_score=float(data.get("risk_score", 0)),
            threat_indicators=json.loads(data.get("threat_indicators", "[]")),
            location=json.loads(data.get("location", "{}")),
            device_fingerprint=data.get("device_fingerprint") or None
        )

    async def _get_alert_by_id(self, alert_id: str) -> Optional[SecurityAlert]:
        """根据ID获取安全告警"""
        if not self.redis_client:
            return None

        data = await self.redis_client.hgetall(f"security_alert:{alert_id}")
        if not data:
            return None

        return SecurityAlert(
            id=data["id"],
            alert_type=data["alert_type"],
            severity=SecurityEventSeverity(data["severity"]),
            title=data["title"],
            description=data["description"],
            events=json.loads(data["events"]),
            risk_score=float(data["risk_score"]),
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"]),
            acknowledged_at=datetime.fromisoformat(data["acknowledged_at"]) if data.get("acknowledged_at") else None,
            acknowledged_by=data.get("acknowledged_by") or None,
            resolved_at=datetime.fromisoformat(data["resolved_at"]) if data.get("resolved_at") else None,
            resolved_by=data.get("resolved_by") or None,
            metadata=json.loads(data.get("metadata", "{}"))
        )

    async def _get_recent_events(
        self,
        event_type: SecurityEventType,
        user_id: str,
        minutes: int = 15
    ) -> List[SecurityEvent]:
        """获取最近��事件"""
        if not self.redis_client:
            return []

        event_ids = await self.redis_client.lrange(f"user_security_events:{user_id}", 0, -1)
        events = []

        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        for event_id in event_ids:
            event = await self._get_event_by_id(event_id)
            if event and event.event_type == event_type and event.timestamp >= cutoff_time:
                events.append(event)

        return events

    async def _get_location_info(self, ip_address: str) -> Optional[Dict[str, str]]:
        """获取地理位置信息"""
        if not self.geoip_reader:
            return None

        try:
            response = self.geoip_reader.city(ip_address)
            return {
                "country": response.country.iso_code,
                "city": response.city.name,
                "latitude": str(response.location.latitude),
                "longitude": str(response.location.longitude)
            }
        except (geoip2.errors.AddressNotFoundError, ValueError):
            return None

    def _calculate_risk_score(
        self,
        event_type: SecurityEventType,
        severity: SecurityEventSeverity,
        ip_address: str,
        details: Dict[str, Any],
        location: Optional[Dict[str, str]]
    ) -> float:
        """计算风险分数"""
        base_score = {
            SecurityEventSeverity.LOW: 1.0,
            SecurityEventSeverity.MEDIUM: 3.0,
            SecurityEventSeverity.HIGH: 6.0,
            SecurityEventSeverity.CRITICAL: 9.0
        }.get(severity, 1.0)

        # 事件类型调整
        type_adjustments = {
            SecurityEventType.LOGIN_FAILURE: 2.0,
            SecurityEventType.ACCOUNT_LOCKED: 5.0,
            SecurityEventType.PERMISSION_DENIED: 3.0,
            SecurityEventType.SUSPICIOUS_ACTIVITY: 7.0,
            SecurityEventType.SECURITY_POLICY_VIOLATION: 6.0
        }

        score = base_score + type_adjustments.get(event_type, 0)

        # 地理位置风险
        if location:
            risk_countries = self.config.get("risk_countries", [])
            if location.get("country") in risk_countries:
                score += 3.0

        # IP地址风险
        if self._is_suspicious_ip(ip_address):
            score += 4.0

        # 时间风险
        current_hour = datetime.utcnow().hour
        if current_hour in [2, 3, 4, 5]:  # 凌晨时段
            score += 1.5

        return min(score, 10.0)  # 最高10分

    def _is_suspicious_ip(self, ip_address: str) -> bool:
        """检查是否为可疑IP"""
        suspicious_patterns = self.config.get("suspicious_ip_patterns", [])
        for pattern in suspicious_patterns:
            if ip_address.startswith(pattern):
                return True
        return False

    def _get_top_risky_ips(self, events: List[SecurityEvent], limit: int = 10) -> List[Dict[str, Any]]:
        """获取风险最高的IP地址"""
        ip_scores = defaultdict(float)
        ip_counts = defaultdict(int)

        for event in events:
            ip_scores[event.ip_address] += event.risk_score
            ip_counts[event.ip_address] += 1

        # 排序并返回前N个
        sorted_ips = sorted(
            ip_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [
            {
                "ip_address": ip,
                "risk_score": score,
                "event_count": ip_counts[ip]
            }
            for ip, score in sorted_ips
        ]

    def _get_top_risky_users(self, events: List[SecurityEvent], limit: int = 10) -> List[Dict[str, Any]]:
        """获取风险最高的用户"""
        user_scores = defaultdict(float)
        user_counts = defaultdict(int)

        for event in events:
            if event.user_id:
                user_scores[event.user_id] += event.risk_score
                user_counts[event.user_id] += 1

        # 排序并返回前N个
        sorted_users = sorted(
            user_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [
            {
                "user_id": user_id,
                "risk_score": score,
                "event_count": user_counts[user_id]
            }
            for user_id, score in sorted_users
        ]

# 导入uuid
import uuid