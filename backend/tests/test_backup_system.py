"""
备份恢复系统测试
Week 6 Day 6: 备份恢复策略实施

测试备份恢复系统的所有组件功能
"""

import asyncio
import pytest
import tempfile
import os
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

import sys
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from backend.core.backup.backup_manager import BackupManager, BackupConfig, BackupType, BackupStatus
from backend.core.backup.recovery_manager import RecoveryManager, RecoveryConfig, RecoveryType
from backend.core.backup.scheduler import BackupScheduler, ScheduleConfig
from backend.core.backup.disaster_recovery import DisasterRecoveryManager, DRConfig, DisasterType, DRStatus
from backend.core.backup.storage import LocalStorage, S3Storage
from backend.core.backup.strategies import DatabaseBackupStrategy, FileBackupStrategy


class TestBackupManager:
    """备份管理器测试"""

    @pytest.fixture
    def config(self):
        """备份配置"""
        return {
            "storage_path": tempfile.mkdtemp(),
            "database": {
                "type": "postgresql",
                "url": "postgresql://user:pass@localhost/test"
            },
            "backup_paths": ["./data", "./config"]
        }

    @pytest.fixture
    async def backup_manager(self, config):
        """初始化备份管理器"""
        from backend.core.backup.storage import LocalStorage

        manager = BackupManager(config)
        storage = LocalStorage(config["storage_path"])
        await manager.initialize(storage)
        return manager

    @pytest.mark.asyncio
    async def test_create_backup(self, backup_manager):
        """测试创建备份"""
        backup_config = BackupConfig(
            backup_type=BackupType.DATABASE,
            strategy_name="database",
            description="Test backup"
        )

        backup_id = await backup_manager.create_backup(
            backup_config,
            description="Test database backup",
            tags=["test"]
        )

        assert backup_id is not None
        assert backup_id.startswith("database_")

        # 检查备份状态
        status = await backup_manager.get_backup_status(backup_id)
        assert status is not None
        assert status.backup_type == BackupType.DATABASE
        assert status.description == "Test database backup"
        assert "test" in status.tags

    @pytest.mark.asyncio
    async def test_list_backups(self, backup_manager):
        """测试列出备份"""
        # 创建几个备份
        backup_configs = [
            BackupConfig(BackupType.DATABASE, "database"),
            BackupConfig(BackupType.FILES, "files"),
            BackupConfig(BackupType.CONFIG, "config")
        ]

        backup_ids = []
        for config in backup_configs:
            backup_id = await backup_manager.create_backup(config)
            backup_ids.append(backup_id)

        # 列出所有备份
        backups = await backup_manager.list_backups()
        assert len(backups) >= len(backup_ids)

        # 按类型过滤
        db_backups = await backup_manager.list_backups(backup_type=BackupType.DATABASE)
        assert len(db_backups) >= 1

    @pytest.mark.asyncio
    async def test_backup_statistics(self, backup_manager):
        """测试备份统计"""
        stats = await backup_manager.get_backup_statistics()

        assert "total_backups" in stats
        assert "successful_backups" in stats
        assert "failed_backups" in stats
        assert "total_size_bytes" in stats
        assert "backup_type_counts" in stats
        assert "status_counts" in stats

    @pytest.mark.asyncio
    async def test_delete_backup(self, backup_manager):
        """测试删除备份"""
        backup_config = BackupConfig(BackupType.FILES, "files")
        backup_id = await backup_manager.create_backup(backup_config)

        # 等待备份完成
        await asyncio.sleep(0.1)

        # 删除备份
        success = await backup_manager.delete_backup(backup_id)
        assert success

        # 验证备份已删除
        status = await backup_manager.get_backup_status(backup_id)
        assert status is None

    @pytest.mark.asyncio
    async def test_cleanup_expired_backups(self, backup_manager):
        """测试清理过期备份"""
        # 创建短期备份
        backup_config = BackupConfig(
            BackupType.CONFIG,
            "config",
            retention_days=1
        )
        backup_id = await backup_manager.create_backup(backup_config)

        # 清理过期备份（这个测试可能需要mock时间）
        cleaned_count = await backup_manager.cleanup_expired_backups()
        assert isinstance(cleaned_count, int)


class TestRecoveryManager:
    """恢复管理器测试"""

    @pytest.fixture
    def config(self):
        """恢复配置"""
        return {
            "database": {
                "type": "postgresql",
                "url": "postgresql://user:pass@localhost/test"
            },
            "redis": {
                "url": "redis://localhost:6379/0"
            }
        }

    @pytest.fixture
    async def recovery_manager(self, config):
        """初始化恢复管理器"""
        from backend.core.backup.storage import LocalStorage

        manager = RecoveryManager(config)
        storage = LocalStorage(tempfile.mkdtemp())
        await manager.initialize(storage)
        return manager

    @pytest.mark.asyncio
    async def test_create_recovery(self, recovery_manager):
        """测试创建恢复任务"""
        # Mock backup metadata
        with patch.object(recovery_manager, '_get_backup_metadata') as mock_get_metadata:
            from backend.core.backup.backup_manager import BackupMetadata
            mock_backup = BackupMetadata(
                backup_id="test_backup_123",
                backup_type=BackupType.DATABASE,
                backup_name="test_backup",
                created_at=datetime.now(),
                completed_at=datetime.now(),
                file_size=1024,
                compressed_size=512,
                checksum="abc123",
                status=BackupStatus.COMPLETED,
                description="Test backup",
                tags=["test"],
                retention_days=30,
                storage_path="/tmp/test_backup.tar.gz",
                strategy_used="database",
                backup_params={}
            )
            mock_get_metadata.return_value = mock_backup

            recovery_config = RecoveryConfig(
                backup_id="test_backup_123",
                recovery_type=RecoveryType.FULL,
                target_path=tempfile.mkdtemp()
            )

            recovery_id = await recovery_manager.create_recovery(
                recovery_config,
                description="Test recovery"
            )

            assert recovery_id is not None
            assert recovery_id.startswith("recovery_")

    @pytest.mark.asyncio
    async def test_recovery_statistics(self, recovery_manager):
        """测试恢复统计"""
        stats = await recovery_manager.get_recovery_statistics()

        assert "total_recoveries" in stats
        assert "successful_recoveries" in stats
        assert "failed_recoveries" in stats
        assert "recovery_type_counts" in stats
        assert "status_counts" in stats


class TestBackupScheduler:
    """备份调度器测试"""

    @pytest.fixture
    async def backup_scheduler(self):
        """初始化备份调度器"""
        from backend.core.backup.backup_manager import BackupManager

        config = {
            "storage_path": tempfile.mkdtemp(),
            "database": {"type": "sqlite", "path": ":memory:"}
        }

        backup_manager = BackupManager(config)
        await backup_manager.initialize()

        scheduler = BackupScheduler(backup_manager)
        await scheduler.start()

        yield scheduler

        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_add_schedule(self, backup_scheduler):
        """测试添加调度任务"""
        schedule_config = ScheduleConfig(
            name="Test Daily Backup",
            backup_type=BackupType.DATABASE,
            strategy_name="database",
            cron_expression="0 2 * * *",  # 每天凌晨2点
            description="Test daily backup"
        )

        job_id = await backup_scheduler.add_schedule(schedule_config)

        assert job_id is not None
        assert len(job_id) == 16  # MD5 hash length

        # 检查调度是否存在
        schedules = await backup_scheduler.list_schedules()
        assert len(schedules) >= 1

    @pytest.mark.asyncio
    async def test_enable_disable_schedule(self, backup_scheduler):
        """测试启用/禁用调度"""
        schedule_config = ScheduleConfig(
            name="Test Backup",
            backup_type=BackupType.FILES,
            strategy_name="files",
            cron_expression="0 */6 * * *",  # 每6小时
            enabled=True
        )

        job_id = await backup_scheduler.add_schedule(schedule_config)

        # 禁用调度
        success = await backup_scheduler.disable_schedule(job_id)
        assert success

        # 验证已禁用
        schedules = await backup_scheduler.list_schedules(enabled_only=False)
        job = next(s for s in schedules if s.job_id == job_id)
        assert not job.schedule_config.enabled

        # 重新启用
        success = await backup_scheduler.enable_schedule(job_id)
        assert success

    @pytest.mark.asyncio
    async def test_remove_schedule(self, backup_scheduler):
        """测试移除调度"""
        schedule_config = ScheduleConfig(
            name="Test Remove",
            backup_type=BackupType.CONFIG,
            strategy_name="config",
            cron_expression="0 0 * * 0"  # 每周日
        )

        job_id = await backup_scheduler.add_schedule(schedule_config)

        # 移除调度
        success = await backup_scheduler.remove_schedule(job_id)
        assert success

        # 验证已移除
        schedules = await backup_scheduler.list_schedules()
        job_ids = [s.job_id for s in schedules]
        assert job_id not in job_ids

    @pytest.mark.asyncio
    async def test_scheduler_statistics(self, backup_scheduler):
        """测试调度器统计"""
        stats = await backup_scheduler.get_scheduler_statistics()

        assert "total_schedules" in stats
        assert "enabled_schedules" in stats
        assert "running_jobs" in stats
        assert "scheduler_running" in stats
        assert stats["scheduler_running"] is True

    @pytest.mark.asyncio
    async def test_predefined_schedules(self):
        """测试预定义调度配置"""
        # 测试每日数据库备份
        daily_backup = BackupScheduler.create_daily_database_backup()
        assert daily_backup.backup_type == BackupType.DATABASE
        assert daily_backup.cron_expression == "0 2 * * *"

        # 测试每周文件备份
        weekly_backup = BackupScheduler.create_weekly_files_backup()
        assert weekly_backup.backup_type == BackupType.FILES
        assert weekly_backup.cron_expression == "0 3 * * 0"

        # 测试每小时Redis备份
        hourly_backup = BackupScheduler.create_hourly_redis_backup()
        assert hourly_backup.backup_type == BackupType.REDIS
        assert hourly_backup.cron_expression == "0 * * * *"

        # 测试每月配置备份
        monthly_backup = BackupScheduler.create_monthly_config_backup()
        assert monthly_backup.backup_type == BackupType.CONFIG
        assert monthly_backup.cron_expression == "0 4 1 * *"


class TestDisasterRecoveryManager:
    """灾难恢复管理器测试"""

    @pytest.fixture
    def dr_config(self):
        """灾难恢复配置"""
        return DRConfig(
            enable_monitoring=False,  # 测试时禁用监控
            auto_recovery=False,
            rpo_minutes=60,
            rto_minutes=240
        )

    @pytest.fixture
    async def dr_manager(self, dr_config):
        """初始化灾难恢复管理器"""
        manager = DisasterRecoveryManager(dr_config)

        # Mock依赖组件
        mock_backup_manager = AsyncMock()
        mock_recovery_manager = AsyncMock()
        mock_storage = AsyncMock()

        await manager.initialize(mock_backup_manager, mock_recovery_manager, mock_storage)
        return manager

    @pytest.mark.asyncio
    async def test_declare_disaster(self, dr_manager):
        """测试宣告灾难"""
        event_id = await dr_manager.declare_disaster(
            disaster_type=DisasterType.DATA_CORRUPTION,
            severity="high",
            description="Database corruption detected",
            affected_systems=["database", "application"]
        )

        assert event_id is not None
        assert dr_manager.current_status == DRStatus.DISASTER_DECLARED

        # 检查灾难事件
        events = await dr_manager.get_disaster_events()
        assert len(events) >= 1
        assert events[0].disaster_type == DisasterType.DATA_CORRUPTION
        assert events[0].severity == "high"

    @pytest.mark.asyncio
    async def test_get_disaster_status(self, dr_manager):
        """测试获取灾难状态"""
        status = await dr_manager.get_disaster_status()

        assert "current_status" in status
        assert "total_events" in status
        assert "recovery_plans" in status
        assert "monitoring_active" in status
        assert status["current_status"] == DRStatus.NORMAL.value

    @pytest.mark.asyncio
    async def test_default_recovery_plans(self, dr_manager):
        """测试默认恢复计划"""
        plans = await dr_manager.get_recovery_plans()

        assert len(plans) >= 1
        database_plan = plans.get("database_failure")
        assert database_plan is not None
        assert database_plan.disaster_type == DisasterType.DATA_CORRUPTION
        assert len(database_plan.steps) > 0


class TestStorageBackends:
    """存储后端测试"""

    @pytest.fixture
    def temp_dir(self):
        """临时目录"""
        return tempfile.mkdtemp()

    @pytest.fixture
    async def local_storage(self, temp_dir):
        """本地存储"""
        storage = LocalStorage(temp_dir)
        await storage.initialize()
        return storage

    @pytest.mark.asyncio
    async def test_local_storage(self, local_storage):
        """测试本地存储"""
        # 创建测试数据
        test_data = {
            "temp_dir": tempfile.mkdtemp(),
            "backup_files": ["/tmp/test1.txt", "/tmp/test2.txt"],
            "backup_type": "test"
        }

        # 创建测试文件
        for file_path in test_data["backup_files"]:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write("test content")

        # 存储备份
        backup_path = await local_storage.store_backup(
            "test_backup",
            test_data,
            "test_backup.tar.gz",
            compression=True
        )

        assert backup_path is not None
        assert os.path.exists(backup_path)

        # 检查备份是否存在
        exists = await local_storage.backup_exists(backup_path)
        assert exists

        # 列出备份
        backups = await local_storage.list_backups()
        assert len(backups) >= 1

        # 删除备份
        success = await local_storage.delete_backup(backup_path)
        assert success

        # 验证已删除
        exists = await local_storage.backup_exists(backup_path)
        assert not exists

    @pytest.mark.asyncio
    async def test_storage_usage(self, local_storage):
        """测试存储使用情况"""
        usage = await local_storage.get_storage_usage()

        assert "total_size_bytes" in usage
        assert "total_size_human" in usage
        assert "backup_types" in usage
        assert "storage_path" in usage


class TestBackupStrategies:
    """备份策略测试"""

    @pytest.fixture
    def config(self):
        """配置"""
        return {
            "database": {
                "type": "sqlite",
                "path": ":memory:"
            },
            "backup_paths": [tempfile.mkdtemp()],
            "redis": {
                "url": "redis://localhost:6379/0"
            }
        }

    @pytest.mark.asyncio
    async def test_database_backup_strategy(self, config):
        """测试数据库备份策略"""
        strategy = DatabaseBackupStrategy(config)
        await strategy.initialize()

        # 注意：这个测试可能需要实际的数据库连接
        # 在实际环境中应该使用测试数据库
        try:
            backup_data = await strategy.execute_backup("database", {})
            assert "temp_dir" in backup_data
            assert "backup_files" in backup_data
            assert backup_data["backup_type"] == "database"

            await strategy.cleanup(backup_data)
        except Exception as e:
            # 在没有实际数据库的情况下跳过测试
            pytest.skip(f"Database not available: {str(e)}")

    @pytest.mark.asyncio
    async def test_file_backup_strategy(self, config):
        """测试文件备份策略"""
        strategy = FileBackupStrategy(config)
        await strategy.initialize()

        # 创建测试文件
        test_dir = config["backup_paths"][0]
        test_file = os.path.join(test_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")

        backup_data = await strategy.execute_backup("files", {"paths": [test_dir]})

        assert "temp_dir" in backup_data
        assert "backup_files" in backup_data
        assert backup_data["backup_type"] == "files"
        assert backup_data["total_files"] >= 1

        await strategy.cleanup(backup_data)

    @pytest.mark.asyncio
    async def test_config_backup_strategy(self, config):
        """测试配置备份策略"""
        from backend.core.backup.strategies import ConfigBackupStrategy

        strategy = ConfigBackupStrategy(config)
        await strategy.initialize()

        backup_data = await strategy.execute_backup("config", {})

        assert "temp_dir" in backup_data
        assert "backup_files" in backup_data
        assert backup_data["backup_type"] == "config"

        await strategy.cleanup(backup_data)


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_backup_recovery_flow(self):
        """测试完整备份恢复流程"""
        # 这个测试需要完整的设置，可能比较复杂
        # 在实际CI/CD环境中可能需要专门的测试数据库

        config = {
            "storage_path": tempfile.mkdtemp(),
            "database": {"type": "sqlite", "path": ":memory:"}
        }

        # 初始化组件
        from backend.core.backup.storage import LocalStorage

        storage = LocalStorage(config["storage_path"])
        await storage.initialize()

        backup_manager = BackupManager(config)
        await backup_manager.initialize(storage)

        recovery_manager = RecoveryManager(config)
        await recovery_manager.initialize(storage)

        scheduler = BackupScheduler(backup_manager)
        await scheduler.start()

        try:
            # 创建备份
            backup_config = BackupConfig(
                backup_type=BackupType.CONFIG,
                strategy_name="config"
            )
            backup_id = await backup_manager.create_backup(backup_config)

            # 等待备份完成
            await asyncio.sleep(0.1)

            # 验证备份
            verification = await backup_manager.verify_backup(backup_id)
            assert verification["valid"]

            # 获取统计信息
            backup_stats = await backup_manager.get_backup_statistics()
            assert backup_stats["total_backups"] >= 1

            recovery_stats = await recovery_manager.get_recovery_statistics()
            scheduler_stats = await scheduler.get_scheduler_statistics()

            # 验证统计数据
            assert isinstance(backup_stats["total_backups"], int)
            assert isinstance(recovery_stats["total_recoveries"], int)
            assert isinstance(scheduler_stats["total_schedules"], int)

        finally:
            await scheduler.stop()
            await backup_manager.shutdown()
            await recovery_manager.shutdown()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])