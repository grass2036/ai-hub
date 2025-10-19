"""
Redis Task Queue and Task Manager
Week 4 Day 25: Batch Processing and Async Tasks
"""

import json
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import redis.asyncio as redis
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.models.async_task import AsyncTask, BatchJob, TaskStatus, TaskType
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)


class QueuePriority(Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TaskQueue:
    """Redis异步任务队列管理器"""

    def __init__(self):
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
        self.task_handlers: Dict[str, Callable] = {}
        self.worker_tasks: Dict[str, asyncio.Task] = {}

    async def initialize(self):
        """初始化Redis连接"""
        if self.redis_client:
            return

        try:
            self.redis_client = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # 测试连接
            await self.redis_client.ping()
            logger.info("Redis task queue initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            # 如果Redis不可用，使用内存队列作为备选
            self.redis_client = None

    def register_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self.task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")

    async def enqueue_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        priority: QueuePriority = QueuePriority.NORMAL,
        delay_seconds: int = 0,
        max_retries: int = 3
    ) -> str:
        """将任务加入队列"""
        task_id = str(uuid.uuid4())

        task_payload = {
            "task_id": task_id,
            "task_type": task_type,
            "task_data": task_data,
            "priority": priority.value,
            "max_retries": max_retries,
            "retry_count": 0,
            "created_at": datetime.utcnow().isoformat(),
            "scheduled_at": (datetime.utcnow() + timedelta(seconds=delay_seconds)).isoformat()
        }

        if not self.redis_client:
            # 使用内存队列备选方案
            logger.warning("Redis not available, using in-memory queue")
            return await self._enqueue_memory_task(task_payload)

        try:
            # 根据优先级选择队列
            queue_name = f"tasks:{priority.value}"

            # 如果有延迟，加入延迟队列
            if delay_seconds > 0:
                await self.redis_client.zadd(
                    "delayed_tasks",
                    {json.dumps(task_payload): delay_seconds}
                )
            else:
                await self.redis_client.lpush(queue_name, json.dumps(task_payload))

            # 记录任务状态
            await self.redis_client.hset(
                f"task_status:{task_id}",
                mapping={
                    "status": TaskStatus.PENDING,
                    "created_at": task_payload["created_at"]
                }
            )

            logger.info(f"Task {task_id} enqueued successfully")
            return task_id

        except Exception as e:
            logger.error(f"Failed to enqueue task: {e}")
            raise

    async def _enqueue_memory_task(self, task_payload: Dict[str, Any]) -> str:
        """内存队列备选方案"""
        # 这里可以实现一个简单的内存队列
        # 为简化，暂时返回task_id
        logger.warning("Memory queue not implemented, returning task_id")
        return task_payload["task_id"]

    async def dequeue_task(self, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """从队列中取出任务"""
        if not self.redis_client:
            return None

        try:
            # 按优先级顺序检查队列
            queues = ["tasks:high", "tasks:normal", "tasks:low"]

            for queue_name in queues:
                # 使用BLPOP阻塞式获取任务
                result = await self.redis_client.brpop(queue_name, timeout=timeout)
                if result:
                    _, task_json = result
                    task_payload = json.loads(task_json)

                    # 检查任务是否已过期或被取消
                    task_status = await self.redis_client.hget(f"task_status:{task_payload['task_id']}", "status")
                    if task_status != TaskStatus.CANCELLED:
                        return task_payload

            return None

        except Exception as e:
            logger.error(f"Failed to dequeue task: {e}")
            return None

    async def update_task_status(self, task_id: str, status: TaskStatus, progress: float = None, error_message: str = None):
        """更新任务状态"""
        if not self.redis_client:
            return

        try:
            status_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }

            if progress is not None:
                status_data["progress"] = progress

            if error_message:
                status_data["error_message"] = error_message

            await self.redis_client.hset(
                f"task_status:{task_id}",
                mapping=status_data
            )

            # 发布状态更新通知
            await self.redis_client.publish(
                f"task_updates:{task_id}",
                json.dumps({
                    "task_id": task_id,
                    "status": status,
                    "progress": progress,
                    "error_message": error_message,
                    "timestamp": datetime.utcnow().isoformat()
                })
            )

        except Exception as e:
            logger.error(f"Failed to update task status: {e}")

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if not self.redis_client:
            return None

        try:
            status_data = await self.redis_client.hgetall(f"task_status:{task_id}")
            if status_data:
                return dict(status_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
            return None

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if not self.redis_client:
            return False

        try:
            # 更新任务状态为已取消
            await self.update_task_status(task_id, TaskStatus.CANCELLED)

            # 从延迟队列中移除（如果存在）
            await self.redis_client.zrem("delayed_tasks", task_id)

            logger.info(f"Task {task_id} cancelled")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel task: {e}")
            return False

    async def retry_task(self, task_id: str, task_payload: Dict[str, Any]) -> bool:
        """重试任务"""
        if not self.redis_client:
            return False

        try:
            # 增加重试次数
            task_payload["retry_count"] += 1

            # 检查是否超过最大重试次数
            if task_payload["retry_count"] > task_payload["max_retries"]:
                await self.update_task_status(task_id, TaskStatus.FAILED, error_message="Max retries exceeded")
                return False

            # 重新加入队列
            queue_name = f"tasks:{task_payload['priority']}"
            await self.redis_client.lpush(queue_name, json.dumps(task_payload))

            await self.update_task_status(task_id, TaskStatus.PENDING)
            logger.info(f"Task {task_id} retried ({task_payload['retry_count']}/{task_payload['max_retries']})")
            return True

        except Exception as e:
            logger.error(f"Failed to retry task: {e}")
            return False

    async def process_delayed_tasks(self):
        """处理延迟任务"""
        if not self.redis_client:
            return

        try:
            # 获取到期的延迟任务
            current_time = datetime.utcnow().timestamp()
            expired_tasks = await self.redis_client.zrangebyscore(
                "delayed_tasks",
                0,
                current_time,
                withscores=True
            )

            for task_json, score in expired_tasks:
                task_payload = json.loads(task_json)
                task_id = task_payload["task_id"]

                # 从延迟队列移除
                await self.redis_client.zrem("delayed_tasks", task_json)

                # 加入普通队列
                queue_name = f"tasks:{task_payload['priority']}"
                await self.redis_client.lpush(queue_name, task_json)

                logger.info(f"Delayed task {task_id} moved to active queue")

        except Exception as e:
            logger.error(f"Failed to process delayed tasks: {e}")

    async def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        if not self.redis_client:
            return {}

        try:
            stats = {}

            # 各优先级队列长度
            for priority in ["high", "normal", "low"]:
                queue_name = f"tasks:{priority}"
                length = await self.redis_client.llen(queue_name)
                stats[f"queue_{priority}"] = length

            # 延迟任务数量
            delayed_count = await self.redis_client.zcard("delayed_tasks")
            stats["delayed_tasks"] = delayed_count

            # 活跃任务数量
            active_keys = await self.redis_client.keys("task_status:*")
            stats["active_tasks"] = len(active_keys)

            return stats

        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}


class TaskWorker:
    """任务工作器"""

    def __init__(self, worker_id: str, task_queue: TaskQueue, db_session: Session):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.db = db_session
        self.is_running = False
        self.current_task = None

    async def start(self):
        """启动工作器"""
        self.is_running = True
        logger.info(f"Worker {self.worker_id} started")

        while self.is_running:
            try:
                # 获取任务
                task_payload = await self.task_queue.dequeue_task(timeout=5)
                if not task_payload:
                    continue

                await self.process_task(task_payload)

            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                await asyncio.sleep(1)

    async def stop(self):
        """停止工作器"""
        self.is_running = False
        logger.info(f"Worker {self.worker_id} stopped")

    async def process_task(self, task_payload: Dict[str, Any]):
        """处理单个任务"""
        task_id = task_payload["task_id"]
        task_type = task_payload["task_type"]

        self.current_task = task_id

        try:
            # 更新任务状态为运行中
            await self.task_queue.update_task_status(task_id, TaskStatus.RUNNING, progress=0)

            # 更新数据库中的任务状态
            await self._update_db_task_status(task_id, TaskStatus.RUNNING)

            # 获取任务处理器
            handler = self.task_queue.task_handlers.get(task_type)
            if not handler:
                raise ValueError(f"No handler registered for task type: {task_type}")

            # 执行任务
            logger.info(f"Worker {self.worker_id} processing task {task_id} ({task_type})")

            result = await handler(
                task_id=task_id,
                task_data=task_payload["task_data"],
                db=self.db,
                update_callback=lambda progress: self.task_queue.update_task_status(task_id, TaskStatus.RUNNING, progress)
            )

            # 任务完成
            await self.task_queue.update_task_status(task_id, TaskStatus.COMPLETED, progress=100)
            await self._update_db_task_status(task_id, TaskStatus.COMPLETED, result=result)

            logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            error_message = str(e)
            logger.error(f"Task {task_id} failed: {error_message}")

            # 更新失败状态
            await self.task_queue.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error_message=error_message
            )

            # 检查是否需要重试
            if task_payload["retry_count"] < task_payload["max_retries"]:
                await self.task_queue.retry_task(task_id, task_payload)
            else:
                await self._update_db_task_status(task_id, TaskStatus.FAILED, error_message=error_message)

        finally:
            self.current_task = None

    async def _update_db_task_status(self, task_id: str, status: TaskStatus, result: Any = None, error_message: str = None):
        """更新数据库中的任务状态"""
        try:
            task = self.db.query(AsyncTask).filter(AsyncTask.task_id == task_id).first()
            if task:
                task.status = status
                if status == TaskStatus.RUNNING:
                    task.started_at = datetime.utcnow()
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    task.completed_at = datetime.utcnow()
                    if result:
                        task.result = result
                    if error_message:
                        task.error_message = error_message

                self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update DB task status: {e}")


# 全局任务队列实例
task_queue = TaskQueue()


async def get_task_queue() -> TaskQueue:
    """获取任务队列实例"""
    await task_queue.initialize()
    return task_queue