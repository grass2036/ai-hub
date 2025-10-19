"""
生产环境日志配置系统
Week 6 Day 4: 系统监控和日志配置

提供结构化日志、日志聚合、分析和存储功能
"""

import asyncio
import json
import logging
import logging.handlers
import gzip
import aiofiles
import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import re
import uuid
from collections import defaultdict, deque
import elasticsearch
from elasticsearch import Elasticsearch

class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogCategory(Enum):
    """日志分类"""
    SYSTEM = "system"
    APPLICATION = "application"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BUSINESS = "business"
    AUDIT = "audit"

@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    service: str
    message: str
    module: str
    function: str
    line_number: Optional[int] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    duration_ms: Optional[float] = None
    error_traceback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category.value,
            "service": self.service,
            "message": self.message,
            "module": self.module,
            "function": self.function,
            "line_number": self.line_number,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "tags": self.tags or [],
            "metadata": self.metadata or {},
            "duration_ms": self.duration_ms,
            "error_traceback": self.error_traceback
        }

class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def __init__(self, service_name: str = "ai-hub"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        log_entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created),
            level=LogLevel(record.levelname),
            category=self._get_category(record),
            service=self.service_name,
            service_instance=getattr(record, 'service_instance', 'default'),
            message=record.getMessage(),
            module=record.module,
            function=record.funcName,
            line_number=record.lineno,
            user_id=getattr(record, 'user_id', None),
            session_id=getattr(record, 'session_id', None),
            request_id=getattr(record, 'request_id', None),
            correlation_id=getattr(record, 'correlation_id', None),
            tags=getattr(record, 'tags', []),
            metadata=getattr(record, 'metadata', {}),
            duration_ms=getattr(record, 'duration_ms', None),
            error_traceback=self._format_traceback(record) if record.exc_info else None
        )

        return json.dumps(log_entry.to_dict(), ensure_ascii=False)

    def _get_category(self, record: logging.LogRecord) -> LogCategory:
        """获取日志分类"""
        if hasattr(record, 'category'):
            return LogCategory(record.category)

        # 根据模块名自动分类
        module_name = record.module.lower()
        if 'auth' in module_name or 'security' in module_name:
            return LogCategory.SECURITY
        elif 'performance' in module_name or 'metrics' in module_name:
            return LogCategory.PERFORMANCE
        elif 'api' in module_name or 'service' in module_name:
            return LogCategory.APPLICATION
        elif 'audit' in module_name:
            return LogCategory.AUDIT
        elif 'business' in module_name or 'billing' in module_name:
            return LogCategory.BUSINESS
        else:
            return LogCategory.SYSTEM

    def _format_traceback(self, record: logging.LogRecord) -> Optional[str]:
        """格式化异常堆栈"""
        if record.exc_info:
            return self.formatException(record.exc_info)
        return None

class LogAggregator:
    """日志聚合器"""

    def __init__(self, buffer_size: int = 10000, flush_interval: int = 60):
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.log_buffer = deque(maxlen=buffer_size)
        self.aggregated_stats = defaultdict(lambda: defaultdict(int))
        self.is_running = False
        self._flush_thread = None

    def add_log(self, log_entry: LogEntry) -> None:
        """添加日志条目"""
        self.log_buffer.append(log_entry)
        self._update_stats(log_entry)

    def _update_stats(self, log_entry: LogEntry) -> None:
        """更新统计信息"""
        # 按级别统计
        self.aggregated_stats['by_level'][log_entry.level.value] += 1

        # 按分类统计
        self.aggregated_stats['by_category'][log_entry.category.value] += 1

        # 按服务统计
        self.aggregated_stats['by_service'][log_entry.service] += 1

        # 按模块统计
        self.aggregated_stats['by_module'][log_entry.module] += 1

    def start_aggregation(self) -> None:
        """启动聚合"""
        if self.is_running:
            return

        self.is_running = True
        self._flush_thread = asyncio.create_task(self._flush_loop())

    async def stop_aggregation(self) -> None:
        """停止聚合"""
        self.is_running = False
        if self._flush_thread:
            await self._flush_thread

    async def _flush_loop(self) -> None:
        """刷新循环"""
        while self.is_running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self._flush_logs()
            except Exception as e:
                logging.error(f"Error in log aggregation loop: {str(e)}")

    async def _flush_logs(self) -> None:
        """刷新日志到存储"""
        if not self.log_buffer:
            return

        logs_to_flush = list(self.log_buffer)
        self.log_buffer.clear()

        # 这里可以实现具体的存储逻辑
        # 例如：写入文件、发送到Elasticsearch、上传到S3等
        await self._persist_logs(logs_to_flush)

    async def _persist_logs(self, logs: List[LogEntry]) -> None:
        """持久化日志"""
        try:
            # 示例：写入本地文件
            log_file = Path(f"logs/application-{datetime.now().strftime('%Y-%m-%d')}.jsonl")
            log_file.parent.mkdir(exist_ok=True)

            async with aiofiles.open(log_file, 'a', encoding='utf-8') as f:
                for log_entry in logs:
                    await f.write(json.dumps(log_entry.to_dict(), ensure_ascii=False) + '\n')

        except Exception as e:
            logging.error(f"Failed to persist logs: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """获取聚合统计"""
        return {
            "total_logs": len(self.log_buffer),
            "buffer_usage": len(self.log_buffer) / self.buffer_size,
            "aggregated_stats": dict(self.aggregated_stats),
            "last_updated": datetime.now().isoformat()
        }

class LogAnalyzer:
    """日志分析器"""

    def __init__(self):
        self.patterns = {
            'error': re.compile(r'error|exception|failed', re.IGNORECASE),
            'performance': re.compile(r'slow|timeout|performance', re.IGNORECASE),
            'security': re.compile(r'unauthorized|forbidden|attack', re.IGNORECASE),
            'api': re.compile(r'/api/|request|response', re.IGNORECASE)
        }

    def analyze_logs(self, logs: List[LogEntry], time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """分析日志"""
        cutoff_time = datetime.now() - time_window
        recent_logs = [log for log in logs if log.timestamp >= cutoff_time]

        analysis = {
            "time_window": str(time_window),
            "total_logs": len(recent_logs),
            "error_analysis": self._analyze_errors(recent_logs),
            "performance_analysis": self._analyze_performance(recent_logs),
            "security_analysis": self._analyze_security(recent_logs),
            "trend_analysis": self._analyze_trends(recent_logs),
            "anomaly_detection": self._detect_anomalies(recent_logs)
        }

        return analysis

    def _analyze_errors(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """分析错误日志"""
        error_logs = [log for log in logs if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]]

        # 错误统计
        error_counts = defaultdict(int)
        error_modules = defaultdict(int)
        error_messages = defaultdict(int)

        for log in error_logs:
            error_counts[log.level.value] += 1
            error_modules[log.module] += 1
            # 提取错误模式
            error_pattern = self._extract_error_pattern(log.message)
            error_messages[error_pattern] += 1

        return {
            "total_errors": len(error_logs),
            "error_rate": len(error_logs) / len(logs) if logs else 0,
            "by_level": dict(error_counts),
            "by_module": dict(error_modules),
            "common_patterns": dict(sorted(error_messages.items(), key=lambda x: x[1], reverse=True)[:10])
        }

    def _analyze_performance(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """分析性能日志"""
        performance_logs = [
            log for log in logs
            if log.category == LogCategory.PERFORMANCE or
               self.patterns['performance'].search(log.message)
        ]

        # 分析响应时间
        durations = [log.duration_ms for log in performance_logs if log.duration_ms is not None]

        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            slow_requests = [d for d in durations if d > 1000]  # 超过1秒的请求
        else:
            avg_duration = max_duration = 0
            slow_requests = []

        return {
            "total_performance_logs": len(performance_logs),
            "avg_response_time_ms": avg_duration,
            "max_response_time_ms": max_duration,
            "slow_request_count": len(slow_requests),
            "slow_request_rate": len(slow_requests) / len(durations) if durations else 0
        }

    def _analyze_security(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """分析安全日志"""
        security_logs = [
            log for log in logs
            if log.category == LogCategory.SECURITY or
               self.patterns['security'].search(log.message)
        ]

        # 安全事件统计
        security_events = defaultdict(int)
        user_activities = defaultdict(int)

        for log in security_logs:
            if 'unauthorized' in log.message.lower():
                security_events['unauthorized_access'] += 1
            elif 'forbidden' in log.message.lower():
                security_events['forbidden_access'] += 1
            elif 'attack' in log.message.lower():
                security_events['potential_attack'] += 1

            if log.user_id:
                user_activities[log.user_id] += 1

        return {
            "total_security_events": len(security_logs),
            "security_events": dict(security_events),
            "active_users": dict(user_activities),
            "suspicious_activities": self._detect_suspicious_activities(security_logs)
        }

    def _analyze_trends(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """分析趋势"""
        # 按小时分组
        hourly_counts = defaultdict(int)
        hourly_errors = defaultdict(int)

        for log in logs:
            hour = log.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour] += 1
            if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                hourly_errors[hour] += 1

        return {
            "hourly_volume": dict(sorted(hourly_counts.items())),
            "hourly_errors": dict(sorted(hourly_errors.items())),
            "peak_hours": self._find_peak_hours(hourly_counts),
            "trend_direction": self._calculate_trend(hourly_counts)
        }

    def _detect_anomalies(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """检测异常"""
        # 错误率异常
        error_logs = [log for log in logs if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]]
        error_rate = len(error_logs) / len(logs) if logs else 0

        # 响应时间异常
        durations = [log.duration_ms for log in logs if log.duration_ms is not None]
        if durations:
            avg_duration = sum(durations) / len(durations)
            outliers = [d for d in durations if d > avg_duration + 2 * (sum((x - avg_duration) ** 2 for x in durations) / len(durations)) ** 0.5]
        else:
            outliers = []

        return {
            "high_error_rate": error_rate > 0.1,  # 错误率超过10%
            "slow_response_outliers": len(outliers),
            "unusual_patterns": self._find_unusual_patterns(logs)
        }

    def _extract_error_pattern(self, message: str) -> str:
        """提取错误模式"""
        # 简单的错误模式提取
        if 'connection' in message.lower():
            return 'connection_error'
        elif 'timeout' in message.lower():
            return 'timeout_error'
        elif 'permission' in message.lower() or 'forbidden' in message.lower():
            return 'permission_error'
        elif 'not found' in message.lower():
            return 'not_found_error'
        else:
            return 'general_error'

    def _detect_suspicious_activities(self, security_logs: List[LogEntry]) -> List[Dict[str, Any]]:
        """检测可疑活动"""
        suspicious = []

        # 检测暴力破解尝试
        failed_logins = defaultdict(list)
        for log in security_logs:
            if 'failed' in log.message.lower() and 'login' in log.message.lower():
                if log.user_id:
                    failed_logins[log.user_id].append(log.timestamp)

        for user_id, attempts in failed_logins.items():
            if len(attempts) > 5:  # 5次以上失败登录
                suspicious.append({
                    "type": "brute_force_attempt",
                    "user_id": user_id,
                    "attempt_count": len(attempts),
                    "time_span": (max(attempts) - min(attempts)).total_seconds()
                })

        return suspicious

    def _find_peak_hours(self, hourly_counts: Dict[datetime, int]) -> List[datetime]:
        """找到高峰时间"""
        if not hourly_counts:
            return []

        max_count = max(hourly_counts.values())
        return [hour for hour, count in hourly_counts.items() if count == max_count]

    def _calculate_trend(self, hourly_counts: Dict[datetime, int]) -> str:
        """计算趋势"""
        if len(hourly_counts) < 2:
            return "insufficient_data"

        sorted_hours = sorted(hourly_counts.items())
        first_half = sum(count for _, count in sorted_hours[:len(sorted_hours)//2])
        second_half = sum(count for _, count in sorted_hours[len(sorted_hours)//2:])

        if second_half > first_half * 1.2:
            return "increasing"
        elif second_half < first_half * 0.8:
            return "decreasing"
        else:
            return "stable"

    def _find_unusual_patterns(self, logs: List[LogEntry]) -> List[str]:
        """发现异常模式"""
        patterns = []

        # 检测重复错误
        error_messages = defaultdict(int)
        for log in logs:
            if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                error_messages[log.message] += 1

        repeated_errors = [msg for msg, count in error_messages.items() if count > 3]
        if repeated_errors:
            patterns.append(f"repeated_errors: {len(repeated_errors)}")

        # 检测异常流量
        if len(logs) > 1000:  # 日志量异常大
            patterns.append("high_log_volume")

        return patterns

class ProductionLogger:
    """生产环境日志管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.aggregator = LogAggregator(
            buffer_size=config.get('buffer_size', 10000),
            flush_interval=config.get('flush_interval', 60)
        )
        self.analyzer = LogAnalyzer()
        self.elasticsearch_client = None
        self.s3_client = None
        self.is_initialized = False

    async def initialize(self) -> None:
        """初始化日志系统"""
        if self.is_initialized:
            return

        try:
            # 设置Elasticsearch连接（如果配置了）
            if 'elasticsearch' in self.config:
                await self._setup_elasticsearch()

            # 设置S3连接（如果配置了）
            if 's3' in self.config:
                await self._setup_s3()

            # 启动日志聚合
            self.aggregator.start_aggregation()

            self.is_initialized = True
            logging.info("Production logging system initialized")

        except Exception as e:
            logging.error(f"Failed to initialize logging: {str(e)}")
            raise

    async def _setup_elasticsearch(self) -> None:
        """设置Elasticsearch连接"""
        try:
            es_config = self.config['elasticsearch']
            self.elasticsearch_client = Elasticsearch(
                hosts=es_config['hosts'],
                http_auth=(es_config.get('username'), es_config.get('password')),
                verify_certs=es_config.get('verify_certs', True)
            )

            # 测试连接
            if self.elasticsearch_client.ping():
                logging.info("Elasticsearch connection established")
            else:
                raise Exception("Elasticsearch connection failed")

        except Exception as e:
            logging.error(f"Failed to setup Elasticsearch: {str(e)}")
            raise

    async def _setup_s3(self) -> None:
        """设置S3连接"""
        try:
            s3_config = self.config['s3']
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=s3_config['access_key'],
                aws_secret_access_key=s3_config['secret_key'],
                region_name=s3_config.get('region', 'us-east-1')
            )

            logging.info("S3 connection established")

        except Exception as e:
            logging.error(f"Failed to setup S3: {str(e)}")
            raise

    def create_logger(self, name: str, level: LogLevel = LogLevel.INFO) -> logging.Logger:
        """创建结构化日志器"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.value))

        # 避免重复添加处理器
        if logger.handlers:
            return logger

        # 创建格式化器
        formatter = StructuredFormatter(self.config.get('service_name', 'ai-hub'))

        # 控制台处理器
        if self.config.get('console_logging', True):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # 文件处理器
        if 'file_logging' in self.config:
            file_config = self.config['file_logging']
            log_file = Path(file_config['path'])
            log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_file,
                maxBytes=file_config.get('max_bytes', 100 * 1024 * 1024),  # 100MB
                backupCount=file_config.get('backup_count', 5)
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # 添加聚合器处理器
        class AggregationHandler(logging.Handler):
            def __init__(self, aggregator):
                super().__init__()
                self.aggregator = aggregator

            def emit(self, record):
                try:
                    # 解析日志记录
                    log_data = json.loads(self.format(record))
                    log_entry = LogEntry(
                        timestamp=datetime.fromisoformat(log_data['timestamp']),
                        level=LogLevel(log_data['level']),
                        category=LogCategory(log_data['category']),
                        service=log_data['service'],
                        message=log_data['message'],
                        module=log_data['module'],
                        function=log_data['function'],
                        line_number=log_data.get('line_number'),
                        user_id=log_data.get('user_id'),
                        session_id=log_data.get('session_id'),
                        request_id=log_data.get('request_id'),
                        correlation_id=log_data.get('correlation_id'),
                        tags=log_data.get('tags', []),
                        metadata=log_data.get('metadata', {}),
                        duration_ms=log_data.get('duration_ms'),
                        error_traceback=log_data.get('error_traceback')
                    )
                    self.aggregator.add_log(log_entry)
                except Exception as e:
                    logging.error(f"Failed to aggregate log: {str(e)}")

        aggregation_handler = AggregationHandler(self.aggregator)
        logger.addHandler(aggregation_handler)

        return logger

    async def search_logs(self, query: Dict[str, Any], limit: int = 100) -> List[LogEntry]:
        """搜索日志"""
        try:
            # 如果配置了Elasticsearch，使用ES搜索
            if self.elasticsearch_client:
                return await self._search_elasticsearch(query, limit)

            # 否则搜索本地文件
            return await self._search_local_files(query, limit)

        except Exception as e:
            logging.error(f"Failed to search logs: {str(e)}")
            return []

    async def _search_elasticsearch(self, query: Dict[str, Any], limit: int) -> List[LogEntry]:
        """Elasticsearch搜索"""
        try:
            es_query = self._build_elasticsearch_query(query)
            response = self.elasticsearch_client.search(
                index="ai-hub-logs-*",
                body=es_query,
                size=limit
            )

            logs = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                log_entry = LogEntry(
                    timestamp=datetime.fromisoformat(source['timestamp']),
                    level=LogLevel(source['level']),
                    category=LogCategory(source['category']),
                    service=source['service'],
                    message=source['message'],
                    module=source['module'],
                    function=source['function'],
                    line_number=source.get('line_number'),
                    user_id=source.get('user_id'),
                    session_id=source.get('session_id'),
                    request_id=source.get('request_id'),
                    correlation_id=source.get('correlation_id'),
                    tags=source.get('tags', []),
                    metadata=source.get('metadata', {}),
                    duration_ms=source.get('duration_ms'),
                    error_traceback=source.get('error_traceback')
                )
                logs.append(log_entry)

            return logs

        except Exception as e:
            logging.error(f"Elasticsearch search failed: {str(e)}")
            return []

    async def _search_local_files(self, query: Dict[str, Any], limit: int) -> List[LogEntry]:
        """本地文件搜索"""
        logs = []

        try:
            log_dir = Path("logs")
            if not log_dir.exists():
                return logs

            # 搜索最近的日志文件
            log_files = sorted(log_dir.glob("*.jsonl"), reverse=True)[:5]

            for log_file in log_files:
                async with aiofiles.open(log_file, 'r', encoding='utf-8') as f:
                    async for line in f:
                        try:
                            log_data = json.loads(line.strip())
                            if self._matches_query(log_data, query):
                                log_entry = LogEntry(
                                    timestamp=datetime.fromisoformat(log_data['timestamp']),
                                    level=LogLevel(log_data['level']),
                                    category=LogCategory(log_data['category']),
                                    service=log_data['service'],
                                    message=log_data['message'],
                                    module=log_data['module'],
                                    function=log_data['function'],
                                    line_number=log_data.get('line_number'),
                                    user_id=log_data.get('user_id'),
                                    session_id=log_data.get('session_id'),
                                    request_id=log_data.get('request_id'),
                                    correlation_id=log_data.get('correlation_id'),
                                    tags=log_data.get('tags', []),
                                    metadata=log_data.get('metadata', {}),
                                    duration_ms=log_data.get('duration_ms'),
                                    error_traceback=log_data.get('error_traceback')
                                )
                                logs.append(log_entry)

                                if len(logs) >= limit:
                                    return logs

                        except (json.JSONDecodeError, KeyError):
                            continue

        except Exception as e:
            logging.error(f"Local file search failed: {str(e)}")

        return logs

    def _build_elasticsearch_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """构建Elasticsearch查询"""
        es_query = {
            "query": {
                "bool": {
                    "must": []
                }
            },
            "sort": [
                {"timestamp": {"order": "desc"}}
            ]
        }

        # 时间范围
        if 'time_range' in query:
            time_range = query['time_range']
            es_query['query']['bool']['must'].append({
                "range": {
                    "timestamp": {
                        "gte": time_range.get('start'),
                        "lte": time_range.get('end')
                    }
                }
            })

        # 级别过滤
        if 'level' in query:
            es_query['query']['bool']['must'].append({
                "term": {"level": query['level']}
            })

        # 分类过滤
        if 'category' in query:
            es_query['query']['bool']['must'].append({
                "term": {"category": query['category']}
            })

        # 文本搜索
        if 'text' in query:
            es_query['query']['bool']['must'].append({
                "match": {"message": query['text']}
            })

        return es_query

    def _matches_query(self, log_data: Dict[str, Any], query: Dict[str, Any]) -> bool:
        """检查日志是否匹配查询"""
        # 级别过滤
        if 'level' in query and log_data.get('level') != query['level']:
            return False

        # 分类过滤
        if 'category' in query and log_data.get('category') != query['category']:
            return False

        # 文本搜索
        if 'text' in query and query['text'].lower() not in log_data.get('message', '').lower():
            return False

        # 时间范围
        if 'time_range' in query:
            time_range = query['time_range']
            log_time = datetime.fromisoformat(log_data['timestamp'])
            if 'start' in time_range and log_time < datetime.fromisoformat(time_range['start']):
                return False
            if 'end' in time_range and log_time > datetime.fromisoformat(time_range['end']):
                return False

        return True

    async def get_log_analysis(self, time_window: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """获取日志分析报告"""
        try:
            # 获取最近的日志
            logs = await self.search_logs({
                "time_range": {
                    "start": (datetime.now() - time_window).isoformat(),
                    "end": datetime.now().isoformat()
                }
            }, limit=10000)

            return self.analyzer.analyze_logs(logs, time_window)

        except Exception as e:
            logging.error(f"Failed to get log analysis: {str(e)}")
            return {"error": str(e)}

    async def cleanup(self) -> None:
        """清理资源"""
        try:
            await self.aggregator.stop_aggregation()
            logging.info("Production logger cleaned up")
        except Exception as e:
            logging.error(f"Error during cleanup: {str(e)}")

# 日志装饰器
def log_execution(
    level: LogLevel = LogLevel.INFO,
    category: LogCategory = LogCategory.APPLICATION,
    include_args: bool = False,
    include_result: bool = False
):
    """执行日志装饰器"""
    def decorator(func):
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            start_time = datetime.now()

            # 记录开始
            log_data = {
                'category': category.value,
                'function': func.__name__,
                'module': func.__module__,
                'start_time': start_time.isoformat()
            }

            if include_args:
                log_data['args'] = str(args)[:500]  # 限制长度
                log_data['kwargs'] = str(kwargs)[:500]

            logger.log(getattr(logging, level.value), f"Starting {func.__name__}", extra=log_data)

            try:
                result = await func(*args, **kwargs)
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000

                # 记录成功完成
                log_data['duration_ms'] = duration_ms
                log_data['status'] = 'success'

                if include_result:
                    log_data['result'] = str(result)[:500]

                logger.log(getattr(logging, level.value), f"Completed {func.__name__}", extra=log_data)

                return result

            except Exception as e:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000

                # 记录错误
                log_data['duration_ms'] = duration_ms
                log_data['status'] = 'error'
                log_data['error'] = str(e)

                logger.error(f"Failed {func.__name__}: {str(e)}", extra=log_data, exc_info=True)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            start_time = datetime.now()

            # 记录开始
            log_data = {
                'category': category.value,
                'function': func.__name__,
                'module': func.__module__,
                'start_time': start_time.isoformat()
            }

            if include_args:
                log_data['args'] = str(args)[:500]
                log_data['kwargs'] = str(kwargs)[:500]

            logger.log(getattr(logging, level.value), f"Starting {func.__name__}", extra=log_data)

            try:
                result = func(*args, **kwargs)
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000

                # 记录成功完成
                log_data['duration_ms'] = duration_ms
                log_data['status'] = 'success'

                if include_result:
                    log_data['result'] = str(result)[:500]

                logger.log(getattr(logging, level.value), f"Completed {func.__name__}", extra=log_data)

                return result

            except Exception as e:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000

                # 记录错误
                log_data['duration_ms'] = duration_ms
                log_data['status'] = 'error'
                log_data['error'] = str(e)

                logger.error(f"Failed {func.__name__}: {str(e)}", extra=log_data, exc_info=True)
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator