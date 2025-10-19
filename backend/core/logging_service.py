"""
实时日志收集系统
Week 5 Day 3: 系统监控和运维自动化
"""

import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import sys
import traceback
from pathlib import Path
import gzip
import threading
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import redis
from pythonjsonlogger import jsonlogger

from backend.config.settings import get_settings

settings = get_settings()


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """日志分类"""
    API = "api"
    AUTH = "auth"
    DATABASE = "database"
    SYSTEM = "system"
    MONITORING = "monitoring"
    SECURITY = "security"
    BUSINESS = "business"
    PERFORMANCE = "performance"


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    message: str
    module: str
    function: str
    line_number: int
    thread_id: int
    process_id: int
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    duration_ms: Optional[float] = None
    status_code: Optional[int] = None
    error_info: Optional[Dict[str, Any]] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category.value,
            "message": self.message,
            "module": self.module,
            "function": self.function,
            "line_number": self.line_number,
            "thread_id": self.thread_id,
            "process_id": self.process_id,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "duration_ms": self.duration_ms,
            "status_code": self.status_code,
            "error_info": self.error_info,
            "tags": self.tags,
            "metadata": self.metadata
        }


class StructuredLogger(jsonlogger.JsonLogger):
    """结构化日志记录器"""

    def __init__(self, name: str, category: LogCategory):
        super().__init__(name, fmt="%(message) %(level)s %(name)s %(pathname)s %(lineno)s")
        self.category = category
        self.addHandler(self._get_handler())

    def _get_handler(self):
        """获取日志处理器"""
        from logging.handlers import RotatingFileHandler

        handler = RotatingFileHandler(
            f"logs/{self.category.value}.log",
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=5
        )

        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
        handler.setFormatter(formatter)

        return handler

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None):
        """创建日志记录"""
        record = super().makeRecord(name, level, fn, lno, msg, args, exc_info, func, extra)

        # 添加分类信息
        record.category = self.category.value

        return record


class LogCollector:
    """日志收集器"""

    def __init__(self):
        self.log_queue = Queue(maxsize=10000)
        self.redis_client = None
        self.batch_size = 100
        self.flush_interval = 5  # 秒
        self._init_redis()
        self._init_loggers()

    def _init_redis(self):
        """初始化Redis连接"""
        try:
            if settings.redis_url:
                self.redis_client = redis.from_url(settings.redis_url, decode_responses=False)
                print("Redis log collector connection established")
        except Exception as e:
            print(f"Failed to connect to Redis for log collection: {e}")

    def _init_loggers(self):
        """初始化日志记录器"""
        self.loggers = {}

        for category in LogCategory:
            logger_name = f"aihub.{category.value}"
            self.loggers[category.value] = StructuredLogger(logger_name, category)

    def log(self, entry: LogEntry):
        """记录日志"""
        try:
            # 添加到队列
            self.log_queue.put_nowait(entry)
        except Exception as e:
            print(f"Failed to queue log entry: {e}")
            # 降级到标准日志
            self._fallback_log(entry)

    def _fallback_log(self, entry: LogEntry):
        """降级日志记录"""
        logger = self.loggers.get(entry.category.value, logging.getLogger())
        getattr(logger, entry.level.value.lower())(entry.message)

    async def start_collection(self):
        """启动日志收集"""
        print("Starting log collection...")

        while True:
            try:
                batch = []
                deadline = asyncio.time() + self.flush_interval

                # 收集批量日志
                while len(batch) < self.batch_size and asyncio.time() < deadline:
                    try:
                        entry = self.log_queue.get_nowait()
                        batch.append(entry)
                    except Empty:
                        await asyncio.sleep(0.1)

                if batch:
                    await self._process_batch(batch)

                # 等待下一次处理
                await asyncio.sleep(1)

            except Exception as e:
                print(f"Error in log collection: {e}")
                await asyncio.sleep(5)

    async def _process_batch(self, batch: List[LogEntry]):
        """处理批量日志"""
        try:
            # 转换为字典
            log_dicts = [entry.to_dict() for entry in batch]

            # 存储到Redis
            if self.redis_client:
                pipe = self.redis_client.pipeline()

                # 存储日志到不同的key
                for i, log_dict in enumerate(log_dicts):
                    key = f"logs:{log_dict['category']}:{int(log_dict['timestamp'].replace('.', ''))}"
                    pipe.setex(key, 7 * 24 * 3600, json.dumps(log_dict))  # 保留7天

                # 存储到最近日志列表
                for log_dict in log_dicts:
                    key = f"recent_logs:{log_dict['category']}"
                    pipe.lpush(key, json.dumps(log_dict))
                    pipe.ltrim(key, 0, 1000)  # 保留最近1000条

                pipe.execute()

            # 异步写入文件（如果需要）
            await self._write_to_files(batch)

        except Exception as e:
            print(f"Failed to process log batch: {e}")

    async def _write_to_files(self, batch: List[LogEntry]):
        """异步写入日志文件"""
        # 按分类分组
        by_category = {}
        for entry in batch:
            category = entry.category.value
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(entry)

        # 并发写入
        with ThreadPoolExecutor(max_workers=len(by_category)) as executor:
            loop = asyncio.get_event_loop()
            tasks = []

            for category, entries in by_category.items():
                task = loop.run_in_executor(
                    executor,
                    self._write_category_to_file,
                    category,
                    entries
                )
                tasks.append(task)

            await asyncio.gather(*tasks, return_exceptions=True)

    def _write_category_to_file(self, category: str, entries: List[LogEntry]):
        """写入分类日志文件"""
        try:
            log_file = Path(f"logs/{category}/{datetime.now().strftime('%Y-%m-%d')}.log")
            log_file.parent.mkdir(parents=True, exist_ok=True)

            with open(log_file, 'a', encoding='utf-8') as f:
                for entry in entries:
                    f.write(json.dumps(entry.to_dict(), default=str) + '\n')

        except Exception as e:
            print(f"Failed to write log file for {category}: {e}")

    async def search_logs(
        self,
        category: Optional[LogCategory] = None,
        level: Optional[LogLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        search_term: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """搜索日志"""
        if not self.redis_client:
            return []

        try:
            # 构建搜索键
            if category:
                keys = [f"recent_logs:{category.value}"]
            else:
                keys = [f"recent_logs:{cat.value}" for cat in LogCategory]

            # 获取日志
            all_logs = []
            for key in keys:
                logs = self.redis_client.lrange(key, 0, -1)
                for log_str in logs:
                    try:
                        log_data = json.loads(log_str)
                        log_time = datetime.fromisoformat(log_data['timestamp'])

                        # 时间过滤
                        if start_time and log_time < start_time:
                            continue
                        if end_time and log_time > end_time:
                            continue

                        # 级别过滤
                        if level and log_data['level'] != level.value:
                            continue

                        # 关键词搜索
                        if search_term and search_term.lower() not in log_data['message'].lower():
                            continue

                        all_logs.append(log_data)

                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

            # 按时间排序
            all_logs.sort(key=lambda x: x['timestamp'], reverse=True)

            return all_logs[:limit]

        except Exception as e:
            print(f"Failed to search logs: {e}")
            return []

    async def get_log_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """获取日志统计"""
        if not self.redis_client:
            return {}

        try:
            stats = {
                "total_logs": 0,
                "by_level": {},
                "by_category": {},
                "error_rate": 0.0,
                "top_errors": [],
                "time_range_hours": hours
            }

            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)

            for category in LogCategory:
                key = f"recent_logs:{category.value}"
                logs = self.redis_client.lrange(key, 0, -1)

                category_count = 0
                category_errors = 0

                for log_str in logs:
                    try:
                        log_data = json.loads(log_str)
                        log_time = datetime.fromisoformat(log_data['timestamp'])

                        if log_time < start_time:
                            continue

                        category_count += 1
                        stats["total_logs"] += 1

                        # 级别统计
                        level = log_data['level']
                        stats["by_level"][level] = stats["by_level"].get(level, 0) + 1

                        # 错误统计
                        if level in [LogLevel.ERROR.value, LogLevel.CRITICAL.value]:
                            category_errors += 1
                            stats["top_errors"].append({
                                "message": log_data['message'][:100],
                                "level": level,
                                "timestamp": log_time.isoformat(),
                                "module": log_data.get('module', '')
                            })

                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

                stats["by_category"][category.value] = category_count

            # 计算错误率
            if stats["total_logs"] > 0:
                error_count = stats["by_level"].get(LogLevel.ERROR.value, 0) + \
                             stats["by_level"].get(LogLevel.CRITICAL.value, 0)
                stats["error_rate"] = (error_count / stats["total_logs"]) * 100

            # 排序错误信息
            stats["top_errors"] = sorted(
                stats["top_errors"],
                key=lambda x: x["timestamp"],
                reverse=True
            )[:10]

            return stats

        except Exception as e:
            print(f"Failed to get log statistics: {e}")
            return {}


# 全局日志收集器实例
log_collector = LogCollector()


class ContextLogger:
    """上下文日志记录器"""

    def __init__(self, category: LogCategory, **context):
        self.category = category
        self.context = context

    def log(
        self,
        level: LogLevel,
        message: str,
        **kwargs
    ):
        """记录日志"""
        # 获取调用栈信息
        frame = sys._getframe(2)
        module = frame.f_globals.get('__name__', 'unknown')
        function = frame.f_code.co_name
        line_number = frame.f_lineno

        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=level,
            category=self.category,
            message=message,
            module=module,
            function=function,
            line_number=line_number,
            thread_id=threading.get_ident(),
            process_id=asyncio.current_task().get_name() if asyncio.current_task() else os.getpid(),
            **{**self.context, **kwargs}
        )

        log_collector.log(entry)

    def debug(self, message: str, **kwargs):
        self.log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self.log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, error: Exception = None, **kwargs):
        error_info = None
        if error:
            error_info = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc()
            }

        self.log(LogLevel.ERROR, message, error_info=error_info, **kwargs)

    def critical(self, message: str, error: Exception = None, **kwargs):
        error_info = None
        if error:
            error_info = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc()
            }

        self.log(LogLevel.CRITICAL, message, error_info=error_info, **kwargs)


def get_logger(category: LogCategory, **context) -> ContextLogger:
    """获取上下文日志记录器"""
    return ContextLogger(category, **context)


# 日志装饰器
def log_operation(category: LogCategory = LogCategory.API, level: LogLevel = LogLevel.INFO):
    """操作日志装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(
                category=category,
                function=func.__name__,
                module=func.__module__
            )

            start_time = datetime.now()
            request_id = kwargs.get('request_id') or str(uuid.uuid4())

            try:
                logger.log(
                    level=level,
                    f"Operation started: {func.__name__}",
                    request_id=request_id,
                    tags=["operation_start"]
                )

                result = func(*args, **kwargs)

                duration = (datetime.now() - start_time).total_seconds() * 1000

                logger.log(
                    level,
                    f"Operation completed: {func.__name__}",
                    request_id=request_id,
                    duration_ms=duration,
                    tags=["operation_success"]
                )

                return result

            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000

                logger.error(
                    f"Operation failed: {func.__name__}",
                    error=e,
                    request_id=request_id,
                    duration_ms=duration,
                    tags=["operation_error"]
                )
                raise

        return wrapper
    return decorator


async def start_log_collection():
    """启动日志收集服务"""
    print("Starting log collection service...")
    await log_collector.start_collection()


# 简化的日志接口
class Logger:
    """简化的日志接口"""

    @staticmethod
    def debug(message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        get_logger(category=category).debug(message, **kwargs)

    @staticmethod
    def info(message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        get_logger(category=category).info(message, **kwargs)

    @staticmethod
    def warning(message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        get_logger(category=category).warning(message, **kwargs)

    @staticmethod
    def error(message: str, category: LogCategory = LogCategory.SYSTEM, error: Exception = None, **kwargs):
        get_logger(category=category).error(message, error, **kwargs)

    @staticmethod
    def critical(message: str, category: LogCategory = LogCategory.SYSTEM, error: Exception = None, **kwargs):
        get_logger(category=category).critical(message, error, **kwargs)