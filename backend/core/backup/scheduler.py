"""
备份调度器
Week 6 Day 6: 备份恢复策略实施

负责定时执行备份任务
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import logging
from croniter import croniter

from .backup_manager import BackupManager, BackupConfig, BackupType


@dataclass
class ScheduleConfig:
    """调度配置"""
    name: str
    backup_type: BackupType
    strategy_name: str
    cron_expression: str
    enabled: bool = True
    retention_days: int = 30
    description: str = ""
    custom_params: Dict[str, Any] = None
    max_concurrent: int = 1
    timeout_seconds: int = 3600
    retry_attempts: int = 3

    def __post_init__(self):
        if self.custom_params is None:
            self.custom_params = {}


@dataclass
class ScheduledJob:
    """调度任务"""
    job_id: str
    schedule_config: ScheduleConfig
    next_run: datetime
    last_run: Optional[datetime] = None
    last_status: str = "pending"
    last_backup_id: Optional[str] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    is_running: bool = False
    task: Optional[asyncio.Task] = None


class BackupScheduler:
    """备份调度器"""

    def __init__(self, backup_manager: BackupManager):
        self.backup_manager = backup_manager
        self.schedules: Dict[str, ScheduleConfig] = {}
        self.jobs: Dict[str, ScheduledJob] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()

    async def start(self):
        """启动调度器"""
        if self._running:
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logging.info("Backup scheduler started")

    async def stop(self):
        """停止调度器"""
        if not self._running:
            return

        self._running = False

        # 停止调度器循环
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        # 停止所有运行中的任务
        for task in self.running_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self.running_tasks.clear()
        logging.info("Backup scheduler stopped")

    async def add_schedule(self, schedule_config: ScheduleConfig) -> str:
        """添加调度配置"""
        async with self._lock:
            job_id = self._generate_job_id(schedule_config)

            # 验证cron表达式
            try:
                cron = croniter(schedule_config.cron_expression)
                next_run = cron.get_next(datetime)
            except Exception as e:
                raise ValueError(f"Invalid cron expression: {str(e)}")

            # 创建调度任务
            job = ScheduledJob(
                job_id=job_id,
                schedule_config=schedule_config,
                next_run=next_run
            )

            self.schedules[job_id] = schedule_config
            self.jobs[job_id] = job

            logging.info(f"Backup schedule added: {job_id} - {schedule_config.name}")
            return job_id

    async def remove_schedule(self, job_id: str) -> bool:
        """移除调度配置"""
        async with self._lock:
            if job_id not in self.schedules:
                return False

            # 取消正在运行的任务
            if job_id in self.running_tasks:
                self.running_tasks[job_id].cancel()
                del self.running_tasks[job_id]

            # 删除调度配置
            del self.schedules[job_id]
            del self.jobs[job_id]

            logging.info(f"Backup schedule removed: {job_id}")
            return True

    async def update_schedule(self, job_id: str, schedule_config: ScheduleConfig) -> bool:
        """更新调度配置"""
        async with self._lock:
            if job_id not in self.schedules:
                return False

            # 验证cron表达式
            try:
                cron = croniter(schedule_config.cron_expression)
                next_run = cron.get_next(datetime)
            except Exception as e:
                raise ValueError(f"Invalid cron expression: {str(e)}")

            # 更新配置
            self.schedules[job_id] = schedule_config
            job = self.jobs[job_id]
            job.schedule_config = schedule_config
            job.next_run = next_run

            logging.info(f"Backup schedule updated: {job_id}")
            return True

    async def enable_schedule(self, job_id: str) -> bool:
        """启用调度"""
        async with self._lock:
            if job_id in self.schedules:
                self.schedules[job_id].enabled = True
                logging.info(f"Backup schedule enabled: {job_id}")
                return True
            return False

    async def disable_schedule(self, job_id: str) -> bool:
        """禁用调度"""
        async with self._lock:
            if job_id in self.schedules:
                self.schedules[job_id].enabled = False
                logging.info(f"Backup schedule disabled: {job_id}")
                return True
            return False

    async def run_schedule_now(self, job_id: str) -> Optional[str]:
        """立即运行调度任务"""
        async with self._lock:
            if job_id not in self.schedules:
                return None

            schedule_config = self.schedules[job_id]
            if not schedule_config.enabled:
                return None

            # 创建备份配置
            backup_config = BackupConfig(
                backup_type=schedule_config.backup_type,
                strategy_name=schedule_config.strategy_name,
                schedule=schedule_config.cron_expression,
                retention_days=schedule_config.retention_days,
                custom_params=schedule_config.custom_params
            )

            # 启动备份任务
            backup_id = await self.backup_manager.create_backup(
                backup_config,
                description=f"Scheduled backup: {schedule_config.name}",
                tags=["scheduled", job_id],
                manual=False
            )

            logging.info(f"Schedule run triggered: {job_id} -> {backup_id}")
            return backup_id

    async def get_schedule_status(self, job_id: str) -> Optional[ScheduledJob]:
        """获取调度状态"""
        return self.jobs.get(job_id)

    async def list_schedules(self, enabled_only: bool = False) -> List[ScheduledJob]:
        """列出调度任务"""
        jobs = list(self.jobs.values())

        if enabled_only:
            jobs = [job for job in jobs if job.schedule_config.enabled]

        # 按下次运行时间排序
        jobs.sort(key=lambda x: x.next_run)
        return jobs

    async def get_next_runs(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取即将运行的任务"""
        next_runs = []
        current_time = datetime.now()

        for job in self.jobs.values():
            if not job.schedule_config.enabled:
                continue

            if job.next_run > current_time:
                next_runs.append({
                    "job_id": job.job_id,
                    "name": job.schedule_config.name,
                    "backup_type": job.schedule_config.backup_type.value,
                    "next_run": job.next_run,
                    "remaining_seconds": (job.next_run - current_time).total_seconds()
                })

        # 按时间排序
        next_runs.sort(key=lambda x: x["next_run"])
        return next_runs[:count]

    async def get_scheduler_statistics(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        total_schedules = len(self.schedules)
        enabled_schedules = sum(1 for s in self.schedules.values() if s.enabled)
        running_jobs = len(self.running_tasks)

        # 统计各类型的任务数量
        type_counts = {}
        for job in self.jobs.values():
            backup_type = job.schedule_config.backup_type.value
            type_counts[backup_type] = type_counts.get(backup_type, 0) + 1

        # 统计运行状态
        status_counts = {}
        for job in self.jobs.values():
            status = "running" if job.is_running else "idle"
            status_counts[status] = status_counts.get(status, 0) + 1

        # 计算成功率
        total_runs = sum(job.run_count for job in self.jobs.values())
        total_successes = sum(job.success_count for job in self.jobs.values())
        success_rate = (total_successes / max(total_runs, 1)) * 100 if total_runs > 0 else 0

        return {
            "total_schedules": total_schedules,
            "enabled_schedules": enabled_schedules,
            "disabled_schedules": total_schedules - enabled_schedules,
            "running_jobs": running_jobs,
            "backup_type_counts": type_counts,
            "status_counts": status_counts,
            "total_runs": total_runs,
            "total_successes": total_successes,
            "success_rate_percent": round(success_rate, 2),
            "scheduler_running": self._running
        }

    async def _scheduler_loop(self):
        """调度器主循环"""
        logging.info("Backup scheduler loop started")

        while self._running:
            try:
                current_time = datetime.now()

                # 检查需要运行的任务
                jobs_to_run = []
                async with self._lock:
                    for job_id, job in self.jobs.items():
                        if (job.schedule_config.enabled and
                            not job.is_running and
                            job.next_run <= current_time and
                            job_id not in self.running_tasks):
                            jobs_to_run.append(job)

                # 运行任务
                for job in jobs_to_run:
                    await self._run_scheduled_job(job)

                # 计算下次运行时间
                await asyncio.sleep(60)  # 每分钟检查一次

            except Exception as e:
                logging.error(f"Scheduler loop error: {str(e)}")
                await asyncio.sleep(60)

        logging.info("Backup scheduler loop stopped")

    async def _run_scheduled_job(self, job: ScheduledJob):
        """运行调度任务"""
        try:
            job.is_running = True
            job.run_count += 1

            # 创建备份配置
            backup_config = BackupConfig(
                backup_type=job.schedule_config.backup_type,
                strategy_name=job.schedule_config.strategy_name,
                schedule=job.schedule_config.cron_expression,
                retention_days=job.schedule_config.retention_days,
                timeout_seconds=job.schedule_config.timeout_seconds,
                retry_attempts=job.schedule_config.retry_attempts,
                custom_params=job.schedule_config.custom_params
            )

            # 启动备份任务
            task = asyncio.create_task(
                self._execute_backup_job(job, backup_config)
            )
            self.running_tasks[job.job_id] = task
            job.task = task

            logging.info(f"Scheduled backup started: {job.job_id}")

        except Exception as e:
            job.is_running = False
            job.failure_count += 1
            job.last_status = f"failed: {str(e)}"
            logging.error(f"Failed to start scheduled job {job.job_id}: {str(e)}")

    async def _execute_backup_job(self, job: ScheduledJob, backup_config: BackupConfig):
        """执行备份任务"""
        try:
            # 执行备份
            backup_id = await self.backup_manager.create_backup(
                backup_config,
                description=f"Scheduled backup: {job.schedule_config.name}",
                tags=["scheduled", job.job_id],
                manual=False
            )

            # 等待备份完成
            while True:
                backup_status = await self.backup_manager.get_backup_status(backup_id)
                if not backup_status:
                    break

                if backup_status.status.value in ["completed", "failed", "cancelled"]:
                    break

                await asyncio.sleep(10)  # 每10秒检查一次

            # 更新任务状态
            backup_status = await self.backup_manager.get_backup_status(backup_id)
            if backup_status and backup_status.status.value == "completed":
                job.success_count += 1
                job.last_status = "success"
                logging.info(f"Scheduled backup completed successfully: {job.job_id} -> {backup_id}")
            else:
                job.failure_count += 1
                job.last_status = f"failed: {backup_status.error_message if backup_status else 'unknown'}"
                logging.error(f"Scheduled backup failed: {job.job_id} -> {backup_id}")

            job.last_backup_id = backup_id
            job.last_run = datetime.now()

            # 计算下次运行时间
            cron = croniter(job.schedule_config.cron_expression, job.last_run)
            job.next_run = cron.get_next(datetime)

        except Exception as e:
            job.failure_count += 1
            job.last_status = f"failed: {str(e)}"
            logging.error(f"Scheduled backup error: {job.job_id} - {str(e)}")

        finally:
            job.is_running = False
            if job.job_id in self.running_tasks:
                del self.running_tasks[job.job_id]

    def _generate_job_id(self, schedule_config: ScheduleConfig) -> str:
        """生成任务ID"""
        import hashlib
        content = f"{schedule_config.name}_{schedule_config.backup_type.value}_{schedule_config.cron_expression}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    # 预定义的调度配置
    @staticmethod
    def create_daily_database_backup() -> ScheduleConfig:
        """创建每日数据库备份配置"""
        return ScheduleConfig(
            name="Daily Database Backup",
            backup_type=BackupType.DATABASE,
            strategy_name="database",
            cron_expression="0 2 * * *",  # 每天凌晨2点
            retention_days=7,
            description="Daily database backup at 2 AM"
        )

    @staticmethod
    def create_weekly_files_backup() -> ScheduleConfig:
        """创建每周文件备份配置"""
        return ScheduleConfig(
            name="Weekly Files Backup",
            backup_type=BackupType.FILES,
            strategy_name="files",
            cron_expression="0 3 * * 0",  # 每周日凌晨3点
            retention_days=30,
            description="Weekly files backup on Sunday at 3 AM"
        )

    @staticmethod
    def create_hourly_redis_backup() -> ScheduleConfig:
        """创建每小时Redis备份配置"""
        return ScheduleConfig(
            name="Hourly Redis Backup",
            backup_type=BackupType.REDIS,
            strategy_name="redis",
            cron_expression="0 * * * *",  # 每小时
            retention_days=1,
            description="Hourly Redis backup"
        )

    @staticmethod
    def create_monthly_config_backup() -> ScheduleConfig:
        """创建每月配置备份配置"""
        return ScheduleConfig(
            name="Monthly Config Backup",
            backup_type=BackupType.CONFIG,
            strategy_name="config",
            cron_expression="0 4 1 * *",  # 每月1号凌晨4点
            retention_days=90,
            description="Monthly configuration backup on 1st at 4 AM"
        )

    @staticmethod
    def create_full_daily_backup() -> ScheduleConfig:
        """创建每日完整备份配置"""
        return ScheduleConfig(
            name="Daily Full Backup",
            backup_type=BackupType.FULL,
            strategy_name="database",  # 使用数据库策略，但备份所有内容
            cron_expression="0 1 * * *",  # 每天凌晨1点
            retention_days=7,
            description="Daily full system backup at 1 AM",
            custom_params={
                "include_database": True,
                "include_files": True,
                "include_config": True,
                "include_redis": True
            }
        )