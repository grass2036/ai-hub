"""
高级日志分析系统
Week 5 Day 5: 系统监控和运维增强 - 高级日志分析
"""

import asyncio
import json
import re
import gzip
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from collections import defaultdict, Counter
import threading
from concurrent.futures import ThreadPoolExecutor
import uuid

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LogLevel(Enum):
    """日志级别"""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class LogCategory(Enum):
    """日志分类"""
    SYSTEM = "system"
    APPLICATION = "application"
    DATABASE = "database"
    NETWORK = "network"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BUSINESS = "business"
    AUDIT = "audit"


class AnomalyType(Enum):
    """异常类型"""
    SPIKE = "spike"                     # 峰值异常
    DROP = "drop"                       # 下降异常
    PATTERN_CHANGE = "pattern_change"   # 模式变化
    ERROR_BURST = "error_burst"         # 错误爆发
    SILENCE = "silence"                 # 异常静默


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    message: str
    source: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    raw_data: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

    @property
    def severity_score(self) -> int:
        """严重程度评分"""
        severity_scores = {
            LogLevel.TRACE: 1,
            LogLevel.DEBUG: 2,
            LogLevel.INFO: 3,
            LogLevel.WARN: 4,
            LogLevel.ERROR: 5,
            LogLevel.FATAL: 6
        }
        return severity_scores.get(self.level, 3)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['level'] = self.level.value
        data['category'] = self.category.value
        data['severity_score'] = self.severity_score
        return data


@dataclass
class LogPattern:
    """日志模式"""
    pattern_id: str
    name: str
    regex: str
    category: LogCategory
    severity: LogLevel
    description: str
    sample_messages: List[str]
    created_at: datetime
    match_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data


@dataclass
class LogAnomaly:
    """日志异常"""
    anomaly_id: str
    anomaly_type: AnomalyType
    description: str
    detected_at: datetime
    severity: LogLevel
    affected_logs: List[str]  # log_entry_ids
    metrics: Dict[str, float]
    pattern_id: Optional[str] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['anomaly_type'] = self.anomaly_type.value
        data['severity'] = self.severity.value
        data['detected_at'] = self.detected_at.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data


@dataclass
class LogAggregation:
    """日志聚合"""
    aggregation_id: str
    time_window: str  # 1m, 5m, 15m, 1h, 1d
    category: LogCategory
    timestamp: datetime
    total_count: int
    level_counts: Dict[LogLevel, int]
    source_counts: Dict[str, int]
    top_errors: List[Dict[str, Any]]
    performance_metrics: Dict[str, float]
    anomaly_indicators: List[str]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['category'] = self.category.value
        data['level_counts'] = {level.value: count for level, count in self.level_counts.items()}
        return data


class LogParser:
    """日志解析器"""

    def __init__(self):
        self.patterns: List[LogPattern] = []
        self.custom_parsers: Dict[str, re.Pattern] = {}
        self._load_default_patterns()

    def _load_default_patterns(self):
        """加载默认模式"""
        default_patterns = [
            LogPattern(
                pattern_id="http_request",
                name="HTTP请求",
                regex=r'(?P<method>\w+)\s+(?P<path>/\S*)\s+(?P<status>\d{3})\s+(?P<duration>\d+)ms',
                category=LogCategory.APPLICATION,
                severity=LogLevel.INFO,
                description="HTTP请求日志",
                sample_messages=["GET /api/v1/chat 200 150ms"],
                created_at=datetime.utcnow()
            ),
            LogPattern(
                pattern_id="database_error",
                name="数据库错误",
                regex=r'Database\s+(?P<error>\w+):\s*(?P<message>.+)',
                category=LogCategory.DATABASE,
                severity=LogLevel.ERROR,
                description="数据库错误日志",
                sample_messages=["Database Connection: Failed to connect to server"],
                created_at=datetime.utcnow()
            ),
            LogPattern(
                pattern_id="security_violation",
                name="安全违规",
                regex=r'Security\s+(?P<volation>\w+):\s*(?P<ip>\d+\.\d+\.\d+\.\d+)',
                category=LogCategory.SECURITY,
                severity=LogLevel.WARN,
                description="安全违规日志",
                sample_messages=["Security Violation: 192.168.1.100 - Failed login attempt"],
                created_at=datetime.utcnow()
            ),
            LogPattern(
                pattern_id="performance_slow",
                name="性能问题",
                regex=r'Performance\s+(?P<issue>\w+):\s*(?P<duration>\d+)ms',
                category=LogCategory.PERFORMANCE,
                severity=LogLevel.WARN,
                description="性能问题日志",
                sample_messages=["Performance Slow: Database query took 5000ms"],
                created_at=datetime.utcnow()
            )
        ]

        self.patterns.extend(default_patterns)

    def parse_log_entry(self, raw_log: str, source: str = "unknown") -> Optional[LogEntry]:
        """解析日志条目"""
        try:
            # 尝试解析为JSON格式
            if raw_log.strip().startswith('{'):
                return self._parse_json_log(raw_log, source)

            # 尝试解析结构化日志
            return self._parse_structured_log(raw_log, source)

        except Exception as e:
            logger.error(f"Failed to parse log entry: {e}")
            return None

    def _parse_json_log(self, raw_log: str, source: str) -> LogEntry:
        """解析JSON格式日志"""
        data = json.loads(raw_log)

        return LogEntry(
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.utcnow().isoformat())),
            level=LogLevel(data.get('level', 'INFO')),
            category=LogCategory(data.get('category', 'application')),
            message=data.get('message', ''),
            source=source,
            trace_id=data.get('trace_id'),
            span_id=data.get('span_id'),
            user_id=data.get('user_id'),
            session_id=data.get('session_id'),
            request_id=data.get('request_id'),
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent'),
            tags=data.get('tags', []),
            metadata=data.get('metadata', {}),
            raw_data=raw_log
        )

    def _parse_structured_log(self, raw_log: str, source: str) -> LogEntry:
        """解析结构化日志"""
        # 提取时间戳
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})', raw_log)
        timestamp = datetime.fromisoformat(timestamp_match.group(1).replace(' ', 'T')) if timestamp_match else datetime.utcnow()

        # 提取日志级别
        level_match = re.search(r'\b(TRACE|DEBUG|INFO|WARN|ERROR|FATAL)\b', raw_log, re.IGNORECASE)
        level = LogLevel(level_match.group().upper()) if level_match else LogLevel.INFO

        # 提取消息
        message_match = re.search(r']\s*(.+)$', raw_log) or re.search(r'\s-\s(.+)$', raw_log)
        message = message_match.group(1).strip() if message_match else raw_log

        # 提取其他字段
        trace_id_match = re.search(r'trace[ _-]?id[=:]\s*([a-f0-9\-]+)', raw_log, re.IGNORECASE)
        user_id_match = re.search(r'user[ _-]?id[=:]\s*(\w+)', raw_log, re.IGNORECASE)

        return LogEntry(
            timestamp=timestamp,
            level=level,
            category=LogCategory.APPLICATION,
            message=message,
            source=source,
            trace_id=trace_id_match.group(1) if trace_id_match else None,
            user_id=user_id_match.group(1) if user_id_match else None,
            raw_data=raw_log
        )

    def match_pattern(self, log_entry: LogEntry) -> Optional[LogPattern]:
        """匹配日志模式"""
        for pattern in self.patterns:
            if re.search(pattern.regex, log_entry.message, re.IGNORECASE):
                pattern.match_count += 1
                return pattern
        return None

    def add_pattern(self, pattern: LogPattern):
        """添加新模式"""
        self.patterns.append(pattern)

    def get_pattern_statistics(self) -> Dict[str, Any]:
        """获取模式统计"""
        return {
            "total_patterns": len(self.patterns),
            "most_common": [
                {
                    "pattern_id": p.pattern_id,
                    "name": p.name,
                    "match_count": p.match_count
                }
                for p in sorted(self.patterns, key=lambda x: x.match_count, reverse=True)[:10]
            ]
        }


class LogAnalyzer:
    """日志分析器"""

    def __init__(self):
        self.anomaly_detectors = [
            ErrorSpikeDetector(),
            ErrorBurstDetector(),
            SilenceDetector(),
            PatternChangeDetector()
        ]

    async def analyze_logs(
        self,
        logs: List[LogEntry],
        time_window: timedelta = timedelta(hours=1)
    ) -> List[LogAnomaly]:
        """分析日志异常"""
        anomalies = []

        for detector in self.anomaly_detectors:
            try:
                detector_anomalies = await detector.detect(logs, time_window)
                anomalies.extend(detector_anomalies)
            except Exception as e:
                logger.error(f"Anomaly detection failed for {detector.__class__.__name__}: {e}")

        # 按严重程度排序
        anomalies.sort(key=lambda a: a.severity_score, reverse=True)
        return anomalies

    def get_log_statistics(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """获取日志统计"""
        if not logs:
            return {}

        # 基础统计
        total_logs = len(logs)
        level_counts = Counter(log.level for log in logs)
        category_counts = Counter(log.category for log in logs)
        source_counts = Counter(log.source for log in logs)

        # 时间分布
        time_distribution = defaultdict(int)
        for log in logs:
            hour_key = log.timestamp.strftime("%Y-%m-%d %H:00")
            time_distribution[hour_key] += 1

        # 错误分析
        error_logs = [log for log in logs if log.level in [LogLevel.ERROR, LogLevel.FATAL]]
        top_errors = Counter(log.message[:100] for log in error_logs).most_common(10)

        # 性能指标
        performance_logs = [log for log in logs if log.category == LogCategory.PERFORMANCE]
        avg_severity = sum(log.severity_score for log in logs) / total_logs

        return {
            "total_logs": total_logs,
            "level_distribution": {level.value: count for level, count in level_counts.items()},
            "category_distribution": {category.value: count for category, count in category_counts.items()},
            "source_distribution": dict(source_counts),
            "time_distribution": dict(time_distribution),
            "error_rate": (len(error_logs) / total_logs * 100) if total_logs > 0 else 0,
            "avg_severity": avg_severity,
            "top_errors": [{"message": msg, "count": count} for msg, count in top_errors],
            "performance_logs_count": len(performance_logs)
        }


class AnomalyDetector(ABC):
    """异常检测器基类"""

    @abstractmethod
    async def detect(self, logs: List[LogEntry], time_window: timedelta) -> List[LogAnomaly]:
        """检测异常"""
        pass


class ErrorSpikeDetector(AnomalyDetector):
    """错误峰值检测器"""

    async def detect(self, logs: List[LogEntry], time_window: timedelta) -> List[LogAnomaly]:
        """检测错误峰值"""
        anomalies = []

        # 按时间分组（每5分钟）
        time_buckets = defaultdict(list)
        for log in logs:
            if log.level in [LogLevel.ERROR, LogLevel.FATAL]:
                bucket_key = self._get_time_bucket(log.timestamp, 5)
                time_buckets[bucket_key].append(log)

        if len(time_buckets) < 3:
            return anomalies

        # 计算平均错误数
        error_counts = [len(logs) for logs in time_buckets.values()]
        avg_errors = sum(error_counts) / len(error_counts)
        std_dev = (sum((x - avg_errors) ** 2 for x in error_counts) / len(error_counts)) ** 0.5

        # 检测峰值（超过平均值+2个标准差）
        threshold = avg_errors + (2 * std_dev)

        for bucket_time, bucket_logs in time_buckets.items():
            if len(bucket_logs) > threshold and len(bucket_logs) > 5:  # 至少5个错误
                anomaly = LogAnomaly(
                    anomaly_id=str(uuid.uuid4()),
                    anomaly_type=AnomalyType.SPIKE,
                    description=f"Error spike detected: {len(bucket_logs)} errors in 5 minutes (threshold: {threshold:.1f})",
                    detected_at=datetime.utcnow(),
                    severity=LogLevel.ERROR,
                    affected_logs=[log.id for log in bucket_logs],
                    metrics={
                        "error_count": len(bucket_logs),
                        "threshold": threshold,
                        "std_dev": std_dev,
                        "avg_errors": avg_errors
                    }
                )
                anomalies.append(anomaly)

        return anomalies

    def _get_time_bucket(self, timestamp: datetime, minutes: int) -> datetime:
        """获取时间桶"""
        total_minutes = timestamp.hour * 60 + timestamp.minute
        bucket_minutes = (total_minutes // minutes) * minutes
        return timestamp.replace(hour=bucket_minutes // 60, minute=bucket_minutes % 60, second=0, microsecond=0)


class ErrorBurstDetector(AnomalyDetector):
    """错误爆发检测器"""

    async def detect(self, logs: List[LogEntry], time_window: timedelta) -> List[LogAnomaly]:
        """检测错误爆发"""
        anomalies = []

        # 查找1分钟内的多个错误
        time_sorted_logs = sorted(logs, key=lambda x: x.timestamp)

        for i, log in enumerate(time_sorted_logs):
            if log.level not in [LogLevel.ERROR, LogLevel.FATAL]:
                continue

            # 检查接下来1分钟内的错误数量
            burst_end_time = log.timestamp + timedelta(minutes=1)
            burst_logs = [log]

            for j in range(i + 1, len(time_sorted_logs)):
                if time_sorted_logs[j].timestamp > burst_end_time:
                    break
                if time_sorted_logs[j].level in [LogLevel.ERROR, LogLevel.FATAL]:
                    burst_logs.append(time_sorted_logs[j])

            # 如果1分钟内有超过10个错误，认为是爆发
            if len(burst_logs) > 10:
                anomaly = LogAnomaly(
                    anomaly_id=str(uuid.uuid4()),
                    anomaly_type=AnomalyType.ERROR_BURST,
                    description=f"Error burst detected: {len(burst_logs)} errors in 1 minute",
                    detected_at=datetime.utcnow(),
                    severity=LogLevel.ERROR,
                    affected_logs=[log.id for log in burst_logs],
                    metrics={
                        "error_count": len(burst_logs),
                        "time_window": 60,
                        "start_time": burst_logs[0].timestamp.isoformat(),
                        "end_time": burst_logs[-1].timestamp.isoformat()
                    }
                )
                anomalies.append(anomaly)

        return anomalies


class SilenceDetector(AnomalyDetector):
    """静默检测器"""

    async def detect(self, logs: List[LogEntry], time_window: timedelta) -> List[LogAnomaly]:
        """检测异常静默"""
        anomalies = []

        if len(logs) < 10:
            return anomalies

        # 按时间排序
        time_sorted_logs = sorted(logs, key=lambda x: x.timestamp)

        # 检查时间间隙
        for i in range(1, len(time_sorted_logs)):
            time_gap = time_sorted_logs[i].timestamp - time_sorted_logs[i-1].timestamp

            # 如果有超过10分钟的静默期，可能表示系统问题
            if time_gap > timedelta(minutes=10):
                anomaly = LogAnomaly(
                    anomaly_id=str(uuid.uuid4()),
                    anomaly_type=AnomalyType.SILENCE,
                    description=f"Silence detected: {time_gap.total_seconds():.0f} seconds without logs",
                    detected_at=datetime.utcnow(),
                    severity=LogLevel.WARN,
                    affected_logs=[],
                    metrics={
                        "silence_duration_seconds": time_gap.total_seconds(),
                        "last_log_time": time_sorted_logs[i-1].timestamp.isoformat(),
                        "next_log_time": time_sorted_logs[i].timestamp.isoformat()
                    }
                )
                anomalies.append(anomaly)

        return anomalies


class PatternChangeDetector(AnomalyDetector):
    """模式变化检测器"""

    async def detect(self, logs: List[LogEntry], time_window: timedelta) -> List[LogAnomaly]:
        """检测模式变化"""
        anomalies = []

        if len(logs) < 100:
            return anomalies

        # 简化的模式变化检测：检查错误消息的变化
        error_logs = [log for log in logs if log.level in [LogLevel.ERROR, LogLevel.FATAL]]

        if len(error_logs) < 20:
            return anomalies

        # 分成两半比较
        mid_point = len(error_logs) // 2
        first_half = error_logs[:mid_point]
        second_half = error_logs[mid_point:]

        # 计算错误消息的相似度
        first_patterns = Counter(self._extract_pattern(log.message) for log in first_half)
        second_patterns = Counter(self._extract_pattern(log.message) for log in second_half)

        # 计算模式差异
        all_patterns = set(first_patterns.keys()) | set(second_patterns.keys())
        if not all_patterns:
            return anomalies

        pattern_similarity = 0
        for pattern in all_patterns:
            count1 = first_patterns.get(pattern, 0)
            count2 = second_patterns.get(pattern, 0)
            total = count1 + count2
            if total > 0:
                similarity = min(count1, count2) / total
                pattern_similarity += similarity

        pattern_similarity /= len(all_patterns)

        # 如果相似度低于0.3，认为有模式变化
        if pattern_similarity < 0.3:
            anomaly = LogAnomaly(
                anomaly_id=str(uuid.uuid4()),
                anomaly_type=AnomalyType.PATTERN_CHANGE,
                description=f"Pattern change detected: similarity = {pattern_similarity:.2f}",
                detected_at=datetime.utcnow(),
                severity=LogLevel.WARN,
                affected_logs=[log.id for log in error_logs],
                metrics={
                    "pattern_similarity": pattern_similarity,
                    "first_half_patterns": len(first_patterns),
                    "second_half_patterns": len(second_patterns)
                }
            )
            anomalies.append(anomaly)

        return anomalies

    def _extract_pattern(self, message: str) -> str:
        """提取消息模式"""
        # 简化的模式提取：移除数字、特殊字符等
        pattern = re.sub(r'\d+', '<NUM>', message)
        pattern = re.sub(r'[^\w\s]', ' ', pattern)
        pattern = re.sub(r'\s+', ' ', pattern).strip().lower()
        return pattern


class LogAggregator:
    """日志聚合器"""

    def __init__(self):
        self.aggregations: Dict[str, LogAggregation] = {}

    async def aggregate_logs(
        self,
        logs: List[LogEntry],
        time_window: str = "5m",
        category: Optional[LogCategory] = None
    ) -> List[LogAggregation]:
        """聚合日志"""
        if not logs:
            return []

        # 过滤分类
        if category:
            logs = [log for log in logs if log.category == category]

        # 按时间窗口分组
        window_minutes = self._parse_time_window(time_window)
        time_buckets = defaultdict(list)

        for log in logs:
            bucket_time = self._get_time_bucket(log.timestamp, window_minutes)
            time_buckets[bucket_time].append(log)

        aggregations = []
        for bucket_time, bucket_logs in time_buckets.items():
            aggregation = await self._create_aggregation(bucket_logs, time_window, bucket_time)
            aggregations.append(aggregation)

        return sorted(aggregations, key=lambda x: x.timestamp, reverse=True)

    def _parse_time_window(self, time_window: str) -> int:
        """解析时间窗口"""
        mapping = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "1d": 1440}
        return mapping.get(time_window, 5)

    def _get_time_bucket(self, timestamp: datetime, minutes: int) -> datetime:
        """获取时间桶"""
        total_minutes = timestamp.hour * 60 + timestamp.minute
        bucket_minutes = (total_minutes // minutes) * minutes
        return timestamp.replace(hour=bucket_minutes // 60, minute=bucket_minutes % 60, second=0, microsecond=0)

    async def _create_aggregation(
        self,
        logs: List[LogEntry],
        time_window: str,
        timestamp: datetime
    ) -> LogAggregation:
        """创建聚合"""
        # 基础统计
        level_counts = Counter(log.level for log in logs)
        source_counts = Counter(log.source for log in logs)

        # 错误分析
        error_logs = [log for log in logs if log.level in [LogLevel.ERROR, LogLevel.FATAL]]
        top_errors = Counter(log.message[:100] for log in error_logs).most_common(5)

        # 性能指标
        performance_metrics = {}
        performance_logs = [log for log in logs if log.category == LogCategory.PERFORMANCE]
        if performance_logs:
            performance_metrics["performance_logs"] = len(performance_logs)

        # 异常指标
        anomaly_indicators = []
        if len(error_logs) > len(logs) * 0.1:  # 错误率超过10%
            anomaly_indicators.append("high_error_rate")
        if len(logs) < 10:  # 日志量过少
            anomaly_indicators.append("low_volume")

        return LogAggregation(
            aggregation_id=str(uuid.uuid4()),
            time_window=time_window,
            category=logs[0].category if logs else LogCategory.SYSTEM,
            timestamp=timestamp,
            total_count=len(logs),
            level_counts=dict(level_counts),
            source_counts=dict(source_counts),
            top_errors=[{"message": msg, "count": count} for msg, count in top_errors],
            performance_metrics=performance_metrics,
            anomaly_indicators=anomaly_indicators
        )


class AdvancedLogManager:
    """高级日志管理器"""

    def __init__(self):
        self.parser = LogParser()
        self.analyzer = LogAnalyzer()
        self.aggregator = LogAggregator()
        self.log_entries: List[LogEntry] = []
        self.anomalies: List[LogAnomaly] = []
        self.max_entries = 100000

    async def ingest_log(self, raw_log: str, source: str = "unknown") -> Optional[LogEntry]:
        """摄取日志"""
        log_entry = self.parser.parse_log_entry(raw_log, source)
        if log_entry:
            self.log_entries.append(log_entry)

            # 限制存储数量
            if len(self.log_entries) > self.max_entries:
                self.log_entries = self.log_entries[-self.max_entries:]

            # 异步分析
            asyncio.create_task(self._analyze_new_log(log_entry))

        return log_entry

    async def ingest_logs_batch(self, raw_logs: List[str], source: str = "batch") -> List[LogEntry]:
        """批量摄取日志"""
        log_entries = []
        for raw_log in raw_logs:
            entry = await self.ingest_log(raw_log, source)
            if entry:
                log_entries.append(entry)
        return log_entries

    async def _analyze_new_log(self, log_entry: LogEntry):
        """分析新日志"""
        try:
            # 模式匹配
            pattern = self.parser.match_pattern(log_entry)
            if pattern:
                log_entry.tags.append(f"pattern:{pattern.pattern_id}")

            # 异常检测（如果有足够的日志）
            if len(self.log_entries) > 100:
                recent_logs = self.log_entries[-100:]
                new_anomalies = await self.analyzer.analyze_logs(recent_logs)

                # 只添加新的异常
                for anomaly in new_anomalies:
                    if anomaly.anomaly_id not in [a.anomaly_id for a in self.anomalies]:
                        self.anomalies.append(anomaly)
                        if len(self.anomalies) > 1000:  # 限制异常数量
                            self.anomalies = self.anomalies[-1000:]

        except Exception as e:
            logger.error(f"Failed to analyze log entry: {e}")

    async def search_logs(
        self,
        query: Optional[str] = None,
        level: Optional[LogLevel] = None,
        category: Optional[LogCategory] = None,
        source: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        trace_id: Optional[str] = None,
        limit: int = 100
    ) -> List[LogEntry]:
        """搜索日志"""
        filtered_logs = self.log_entries

        # 应用过滤器
        if query:
            filtered_logs = [log for log in filtered_logs if query.lower() in log.message.lower()]

        if level:
            filtered_logs = [log for log in filtered_logs if log.level == level]

        if category:
            filtered_logs = [log for log in filtered_logs if log.category == category]

        if source:
            filtered_logs = [log for log in filtered_logs if log.source == source]

        if trace_id:
            filtered_logs = [log for log in filtered_logs if log.trace_id == trace_id]

        if start_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp >= start_time]

        if end_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= end_time]

        # 按时间排序并限制结果
        filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_logs[:limit]

    async def get_log_anomalies(
        self,
        unresolved_only: bool = True,
        anomaly_type: Optional[AnomalyType] = None,
        limit: int = 50
    ) -> List[LogAnomaly]:
        """获取日志异常"""
        anomalies = self.anomalies

        if unresolved_only:
            anomalies = [a for a in anomalies if not a.resolved]

        if anomaly_type:
            anomalies = [a for a in anomalies if a.anomaly_type == anomaly_type]

        anomalies.sort(key=lambda x: x.detected_at, reverse=True)
        return anomalies[:limit]

    async def resolve_anomaly(self, anomaly_id: str) -> bool:
        """解决异常"""
        for anomaly in self.anomalies:
            if anomaly.anomaly_id == anomaly_id:
                anomaly.resolved = True
                anomaly.resolved_at = datetime.utcnow()
                return True
        return False

    async def get_log_statistics(
        self,
        hours: int = 24,
        category: Optional[LogCategory] = None
    ) -> Dict[str, Any]:
        """获取日志统计"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_logs = [log for log in self.log_entries if log.timestamp >= cutoff_time]

        if category:
            recent_logs = [log for log in recent_logs if log.category == category]

        stats = self.analyzer.get_log_statistics(recent_logs)
        stats["pattern_statistics"] = self.parser.get_pattern_statistics()

        # 异常统计
        recent_anomalies = [a for a in self.anomalies if a.detected_at >= cutoff_time]
        stats["anomaly_statistics"] = {
            "total_anomalies": len(recent_anomalies),
            "unresolved_anomalies": len([a for a in recent_anomalies if not a.resolved]),
            "by_type": Counter(a.anomaly_type.value for a in recent_anomalies)
        }

        return stats

    async def aggregate_logs(
        self,
        time_window: str = "5m",
        category: Optional[LogCategory] = None,
        hours: int = 24
    ) -> List[LogAggregation]:
        """聚合日志"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_logs = [log for log in self.log_entries if log.timestamp >= cutoff_time]

        return await self.aggregator.aggregate_logs(recent_logs, time_window, category)

    async def export_logs(
        self,
        format: str = "json",
        filters: Optional[Dict[str, Any]] = None
    ) -> Union[str, bytes]:
        """导出日志"""
        logs = self.log_entries

        # 应用过滤器
        if filters:
            if filters.get("level"):
                logs = [log for log in logs if log.level == LogLevel(filters["level"])]
            if filters.get("category"):
                logs = [log for log in logs if log.category == LogCategory(filters["category"])]
            if filters.get("start_time"):
                start_time = datetime.fromisoformat(filters["start_time"])
                logs = [log for log in logs if log.timestamp >= start_time]
            if filters.get("end_time"):
                end_time = datetime.fromisoformat(filters["end_time"])
                logs = [log for log in logs if log.timestamp <= end_time]

        if format == "json":
            return json.dumps([log.to_dict() for log in logs], indent=2)
        elif format == "csv":
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # 写入标题行
            writer.writerow([
                "timestamp", "level", "category", "message", "source",
                "trace_id", "user_id", "tags"
            ])

            # 写入数据行
            for log in logs:
                writer.writerow([
                    log.timestamp.isoformat(),
                    log.level.value,
                    log.category.value,
                    log.message,
                    log.source,
                    log.trace_id or "",
                    log.user_id or "",
                    ",".join(log.tags)
                ])

            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")


# 全局高级日志管理器
advanced_log_manager = AdvancedLogManager()


async def get_advanced_log_manager() -> AdvancedLogManager:
    """获取高级日志管理器"""
    return advanced_log_manager


# 为LogAnomaly添加severity_score属性
@property
def severity_score(self) -> int:
    """异常严重程度评分"""
    severity_scores = {
        LogLevel.TRACE: 1,
        LogLevel.DEBUG: 2,
        LogLevel.INFO: 3,
        LogLevel.WARN: 4,
        LogLevel.ERROR: 5,
        LogLevel.FATAL: 6
    }
    return severity_scores.get(self.severity, 3)

LogAnomaly.severity_score = severity_score