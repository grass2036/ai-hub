"""
并发性能优化模块
Week 6 Day 2: 性能优化和调优 - 并发性能优化策略
实现异步处理、任务队列、资源池管��、负载均衡等功能
"""

import asyncio
import time
import logging
import threading
import multiprocessing
from typing import Dict, List, Any, Optional, Callable, Union, Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from contextlib import asynccontextmanager
from queue import Queue, PriorityQueue
import psutil
import numpy as np

from backend.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

@dataclass
class ConcurrencyMetrics:
    """并发性能指标"""
    task_type: str
    execution_time: float
    worker_type: str  # thread, process, async
    queue_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: Optional[str] = None

@dataclass
class ResourceLimits:
    """资源限制配置"""
    max_threads: int = multiprocessing.cpu_count() * 2
    max_processes: int = multiprocessing.cpu_count()
    max_async_tasks: int = 1000
    memory_limit_mb: float = 1024  # 1GB
    cpu_limit_percent: float = 80.0

class ThreadPoolManager:
    """线程池管理器"""

    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or ResourceLimits().max_threads
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.active_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self._lock = threading.Lock()

    async def submit_task(self, func: Callable, *args, **kwargs) -> Any:
        """提交任务到线程池"""
        loop = asyncio.get_event_loop()

        with self._lock:
            self.active_tasks += 1

        try:
            start_time = time.time()
            result = await loop.run_in_executor(self.executor, func, *args, **kwargs)
            execution_time = time.time() - start_time

            with self._lock:
                self.completed_tasks += 1
                self.active_tasks -= 1

            logger.debug(f"线程任务完成，耗时: {execution_time:.3f}秒")
            return result

        except Exception as e:
            with self._lock:
                self.failed_tasks += 1
                self.active_tasks -= 1

            logger.error(f"线程任务执行失败: {e}")
            raise

    async def submit_batch(self, tasks: List[tuple]) -> List[Any]:
        """批量提交任务"""
        futures = []
        for task_args in tasks:
            func, *args = task_args
            kwargs = {}
            if len(args) > 0 and isinstance(args[-1], dict):
                kwargs = args[-1]
                args = args[:-1]

            future = self.submit_task(func, *args, **kwargs)
            futures.append(future)

        results = await asyncio.gather(*futures, return_exceptions=True)
        return [r for r in results if not isinstance(r, Exception)]

    def get_stats(self) -> Dict[str, Any]:
        """获取线程池统计"""
        with self._lock:
            return {
                "max_workers": self.max_workers,
                "active_tasks": self.active_tasks,
                "completed_tasks": self.completed_tasks,
                "failed_tasks": self.failed_tasks,
                "success_rate": (
                    self.completed_tasks / (self.completed_tasks + self.failed_tasks) * 100
                    if (self.completed_tasks + self.failed_tasks) > 0 else 100
                )
            }

    def shutdown(self):
        """关闭线程池"""
        self.executor.shutdown(wait=True)

class ProcessPoolManager:
    """进程池管理器"""

    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or ResourceLimits().max_processes
        self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
        self.active_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self._lock = threading.Lock()

    async def submit_task(self, func: Callable, *args, **kwargs) -> Any:
        """提交任务到进程池"""
        loop = asyncio.get_event_loop()

        with self._lock:
            self.active_tasks += 1

        try:
            start_time = time.time()
            result = await loop.run_in_executor(self.executor, func, *args, **kwargs)
            execution_time = time.time() - start_time

            with self._lock:
                self.completed_tasks += 1
                self.active_tasks -= 1

            logger.debug(f"进程任务完成，耗时: {execution_time:.3f}秒")
            return result

        except Exception as e:
            with self._lock:
                self.failed_tasks += 1
                self.active_tasks -= 1

            logger.error(f"进程任务执行失败: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """获取进程池统计"""
        with self._lock:
            return {
                "max_workers": self.max_workers,
                "active_tasks": self.active_tasks,
                "completed_tasks": self.completed_tasks,
                "failed_tasks": self.failed_tasks,
                "success_rate": (
                    self.completed_tasks / (self.completed_tasks + self.failed_tasks) * 100
                    if (self.completed_tasks + self.failed_tasks) > 0 else 100
                )
            }

    def shutdown(self):
        """关闭进程池"""
        self.executor.shutdown(wait=True)

class AsyncTaskScheduler:
    """异步任务调度器"""

    def __init__(self, max_concurrent: int = None):
        self.max_concurrent = max_concurrent or ResourceLimits().max_async_tasks
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.task_queue = asyncio.Queue()
        self.running_tasks = set()
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.metrics: List[ConcurrencyMetrics] = []

    async def submit_task(self, coro: Coroutine, task_type: str = "unknown") -> Any:
        """提交异步任务"""
        async with self.semaphore:
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            start_cpu = psutil.cpu_percent()

            self.running_tasks.add(coro)

            try:
                result = await coro
                execution_time = time.time() - start_time
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                end_cpu = psutil.cpu_percent()

                # 记录性能指标
                metric = ConcurrencyMetrics(
                    task_type=task_type,
                    execution_time=execution_time,
                    worker_type="async",
                    memory_usage=end_memory - start_memory,
                    cpu_usage=end_cpu - start_cpu,
                    success=True
                )
                self.metrics.append(metric)
                self.completed_tasks += 1

                logger.debug(f"异步任务完成，耗时: {execution_time:.3f}秒")
                return result

            except Exception as e:
                execution_time = time.time() - start_time

                metric = ConcurrencyMetrics(
                    task_type=task_type,
                    execution_time=execution_time,
                    worker_type="async",
                    success=False,
                    error_message=str(e)
                )
                self.metrics.append(metric)
                self.failed_tasks += 1

                logger.error(f"异步任务执行失败: {e}")
                raise

            finally:
                self.running_tasks.discard(coro)

    async def submit_batch(self, tasks: List[tuple]) -> List[Any]:
        """批量提交异步任务"""
        futures = []
        for task_args in tasks:
            if len(task_args) == 1:
                coro, task_type = task_args[0], "unknown"
            else:
                coro, task_type = task_args

            future = self.submit_task(coro, task_type)
            futures.append(future)

        results = await asyncio.gather(*futures, return_exceptions=True)
        return [r for r in results if not isinstance(r, Exception)]

    async def get_running_task_count(self) -> int:
        """获取正在运行的任务数"""
        return len(self.running_tasks)

    def get_stats(self) -> Dict[str, Any]:
        """获取异步任务统计"""
        return {
            "max_concurrent": self.max_concurrent,
            "running_tasks": len(self.running_tasks),
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": (
                self.completed_tasks / (self.completed_tasks + self.failed_tasks) * 100
                if (self.completed_tasks + self.failed_tasks) > 0 else 100
            ),
            "metrics_count": len(self.metrics)
        }

class LoadBalancer:
    """负载均衡器"""

    def __init__(self, workers: List[str]):
        self.workers = workers
        self.current_index = 0
        self.worker_stats = {worker: {"requests": 0, "response_time": 0.0} for worker in workers}
        self._lock = threading.Lock()

    def get_worker_round_robin(self) -> str:
        """轮询选择工作节点"""
        with self._lock:
            worker = self.workers[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.workers)
            return worker

    def get_worker_least_connections(self) -> str:
        """最少连接选择工作节点"""
        with self._lock:
            min_requests = min(self.worker_stats[w]["requests"] for w in self.workers)
            candidates = [w for w in self.workers if self.worker_stats[w]["requests"] == min_requests]
            return candidates[0] if candidates else self.workers[0]

    def get_worker_best_response_time(self) -> str:
        """最佳响应时间选择工作节点"""
        with self._lock:
            best_worker = min(
                self.workers,
                key=lambda w: self.worker_stats[w]["response_time"]
            )
            return best_worker

    def update_worker_stats(self, worker: str, response_time: float):
        """更新工作节点统计"""
        with self._lock:
            stats = self.worker_stats[worker]
            stats["requests"] += 1
            # 使用移动平均
            stats["response_time"] = (
                stats["response_time"] * 0.9 + response_time * 0.1
            )

    def get_stats(self) -> Dict[str, Any]:
        """获取负载均衡统计"""
        with self._lock:
            return {
                "total_workers": len(self.workers),
                "worker_stats": dict(self.worker_stats)
            }

class ConcurrencyOptimizer:
    """并发性能优化器"""

    def __init__(self):
        self.thread_pool = ThreadPoolManager()
        self.process_pool = ProcessPoolManager()
        self.async_scheduler = AsyncTaskScheduler()
        self.load_balancer = None
        self.resource_limits = ResourceLimits()
        self.metrics: List[ConcurrencyMetrics] = []

    async def optimize_task_execution(
        self,
        func: Callable,
        *args,
        execution_type: str = "auto",
        task_type: str = "unknown",
        **kwargs
    ) -> Any:
        """智能任务执行优化"""

        # 自动选择执行类型
        if execution_type == "auto":
            execution_type = await self._select_optimal_execution_type(func, args, kwargs)

        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        start_cpu = psutil.cpu_percent()

        try:
            if execution_type == "thread":
                result = await self.thread_pool.submit_task(func, *args, **kwargs)
            elif execution_type == "process":
                result = await self.process_pool.submit_task(func, *args, **kwargs)
            elif execution_type == "async":
                if asyncio.iscoroutinefunction(func):
                    result = await self.async_scheduler.submit_task(func(*args, **kwargs), task_type)
                else:
                    # 将同步函数转换为异步
                    result = await self.async_scheduler.submit_task(
                        asyncio.to_thread(func, *args, **kwargs),
                        task_type
                    )
            else:
                raise ValueError(f"不支持的执行类型: {execution_type}")

            # 记录性能指标
            execution_time = time.time() - start_time
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            end_cpu = psutil.cpu_percent()

            metric = ConcurrencyMetrics(
                task_type=task_type,
                execution_time=execution_time,
                worker_type=execution_type,
                memory_usage=end_memory - start_memory,
                cpu_usage=end_cpu - start_cpu,
                success=True
            )
            self.metrics.append(metric)

            logger.debug(f"任务执行完成，类型: {execution_type}, 耗时: {execution_time:.3f}秒")
            return result

        except Exception as e:
            execution_time = time.time() - start_time

            metric = ConcurrencyMetrics(
                task_type=task_type,
                execution_time=execution_time,
                worker_type=execution_type,
                success=False,
                error_message=str(e)
            )
            self.metrics.append(metric)

            logger.error(f"任务执行失败: {e}")
            raise

    async def _select_optimal_execution_type(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """智能选择最优执行类型"""
        # 检查CPU使用率
        cpu_usage = psutil.cpu_percent()

        # 检查内存使用率
        memory = psutil.virtual_memory()
        memory_usage = memory.percent

        # 基于当前系统负载和任务特性选择
        if cpu_usage < 50 and memory_usage < 70:
            # 系统负载较低，可以使用进程池
            return "process"
        elif cpu_usage < 70:
            # 系统负载中等，使用线程池
            return "thread"
        else:
            # 系统负载较高，使用异步
            return "async"

    async def execute_parallel_tasks(
        self,
        tasks: List[tuple],
        max_concurrent: int = None,
        execution_type: str = "auto"
    ) -> List[Any]:
        """并行执行多个任务"""
        if max_concurrent is None:
            max_concurrent = min(len(tasks), 10)

        # 分批执行以避免资源过载
        results = []
        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i:i + max_concurrent]
            batch_results = await self._execute_task_batch(batch, execution_type)
            results.extend(batch_results)

            # 在批次之间稍作停顿
            if i + max_concurrent < len(tasks):
                await asyncio.sleep(0.1)

        return results

    async def _execute_task_batch(self, tasks: List[tuple], execution_type: str) -> List[Any]:
        """执行任务批次"""
        futures = []
        for task_args in tasks:
            if len(task_args) == 1:
                func, = task_args
                task_type = "unknown"
            else:
                func, task_type = task_args

            future = self.optimize_task_execution(
                func,
                execution_type=execution_type,
                task_type=task_type
            )
            futures.append(future)

        results = await asyncio.gather(*futures, return_exceptions=True)
        return [r for r in results if not isinstance(r, Exception)]

    def get_performance_report(self, minutes: int = 60) -> Dict[str, Any]:
        """生成并发性能报告"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [m for m in self.metrics if m.timestamp > cutoff_time]

        if not recent_metrics:
            return {"status": "no_data", "message": "暂无并发性能数据"}

        # 按工作类型分组统计
        worker_stats = {}
        for metric in recent_metrics:
            worker_type = metric.worker_type
            if worker_type not in worker_stats:
                worker_stats[worker_type] = {
                    "count": 0,
                    "execution_times": [],
                    "success_count": 0,
                    "memory_usage": [],
                    "cpu_usage": []
                }

            stats = worker_stats[worker_type]
            stats["count"] += 1
            stats["execution_times"].append(metric.execution_time)
            if metric.success:
                stats["success_count"] += 1
            if metric.memory_usage > 0:
                stats["memory_usage"].append(metric.memory_usage)
            if metric.cpu_usage > 0:
                stats["cpu_usage"].append(metric.cpu_usage)

        # 计算统计信息
        for worker_type, stats in worker_stats.items():
            times = stats["execution_times"]
            stats["avg_execution_time"] = sum(times) / len(times)
            stats["max_execution_time"] = max(times)
            stats["min_execution_time"] = min(times)
            stats["success_rate"] = (
                stats["success_count"] / stats["count"] * 100
            )

            if stats["memory_usage"]:
                stats["avg_memory_usage"] = sum(stats["memory_usage"]) / len(stats["memory_usage"])
            if stats["cpu_usage"]:
                stats["avg_cpu_usage"] = sum(stats["cpu_usage"]) / len(stats["cpu_usage"])

        return {
            "summary": {
                "total_tasks": len(recent_metrics),
                "successful_tasks": len([m for m in recent_metrics if m.success]),
                "failed_tasks": len([m for m in recent_metrics if not m.success]),
                "overall_success_rate": (
                    len([m for m in recent_metrics if m.success]) / len(recent_metrics) * 100
                ),
                "period_minutes": minutes
            },
            "worker_performance": worker_stats,
            "resource_stats": {
                "thread_pool": self.thread_pool.get_stats(),
                "process_pool": self.process_pool.get_stats(),
                "async_scheduler": self.async_scheduler.get_stats()
            },
            "slow_tasks": [
                {
                    "task_type": m.task_type,
                    "worker_type": m.worker_type,
                    "execution_time": m.execution_time,
                    "timestamp": m.timestamp.isoformat(),
                    "error": m.error_message
                }
                for m in sorted(recent_metrics, key=lambda x: x.execution_time, reverse=True)[:10]
                if m.execution_time > 2.0  # 超过2秒的任务
            ]
        }

    def clear_old_metrics(self, hours: int = 24):
        """清理旧的性能指标"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        original_count = len(self.metrics)

        self.metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
        cleaned_count = original_count - len(self.metrics)

        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 条旧的并发性能指标")

    async def shutdown(self):
        """关闭所有资源"""
        self.thread_pool.shutdown()
        self.process_pool.shutdown()

# 全局并发优化器实例
concurrency_optimizer = ConcurrencyOptimizer()

# 装饰器函数
def run_in_thread_pool(func: Callable):
    """在线程池中运行的装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await concurrency_optimizer.optimize_task_execution(
            func, *args, execution_type="thread", task_type=func.__name__, **kwargs
        )
    return wrapper

def run_in_process_pool(func: Callable):
    """在进程池中运行的装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await concurrency_optimizer.optimize_task_execution(
            func, *args, execution_type="process", task_type=func.__name__, **kwargs
        )
    return wrapper

def run_async_optimized(func: Callable):
    """优化的异步执行装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            return await concurrency_optimizer.optimize_task_execution(
                func, *args, execution_type="async", task_type=func.__name__, **kwargs
            )
        else:
            return await concurrency_optimizer.optimize_task_execution(
                func, *args, execution_type="async", task_type=func.__name__, **kwargs
            )
    return wrapper

# 测试函数
async def test_concurrency_optimization():
    """测试并发性能优化功能"""
    print("🚀 测试并发性能优化功能...")

    def cpu_intensive_task(n: int) -> int:
        """CPU密集型任务"""
        total = 0
        for i in range(n):
            total += i * i
        return total

    def io_intensive_task(delay: float) -> str:
        """IO密集型任务"""
        time.sleep(delay)
        return f"IO任务完成，延迟: {delay}秒"

    async def async_task(message: str) -> str:
        """异步任务"""
        await asyncio.sleep(0.1)
        return f"异步任务: {message}"

    # 测试不同类型的任务
    tasks = [
        (cpu_intensive_task, "cpu_task"),
        (io_intensive_task, "io_task"),
        (async_task, "async_task")
    ]

    # 并行执行任务
    start_time = time.time()
    results = await concurrency_optimizer.execute_parallel_tasks([
        (lambda: cpu_intensive_task(10000), "cpu_intensive"),
        (lambda: io_intensive_task(0.2), "io_intensive"),
        (lambda: async_task("test"), "async_task")
    ])
    end_time = time.time()

    print(f"并行执行完成，耗时: {end_time - start_time:.3f}秒")
    print(f"任务结果: {results}")

    # 获取性能报告
    report = concurrency_optimizer.get_performance_report()
    print(f"\n📊 并发性能报告:")
    print(f"总任务数: {report['summary']['total_tasks']}")
    print(f"成功率: {report['summary']['overall_success_rate']:.1f}%")

    for worker_type, stats in report['worker_performance'].items():
        print(f"{worker_type}: 平均执行时间 {stats['avg_execution_time']:.3f}秒")

if __name__ == "__main__":
    import asyncio
    from functools import wraps

    asyncio.run(test_concurrency_optimization())