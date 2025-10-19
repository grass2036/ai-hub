"""
备份恢复模块
Week 6 Day 6: 备份恢复策略实施

提供完整的数据备份、恢复和灾难恢复功能
"""

from .backup_manager import BackupManager, BackupConfig, BackupType
from .recovery_manager import RecoveryManager, RecoveryConfig, RecoveryType
from .strategies import (
    DatabaseBackupStrategy,
    FileBackupStrategy,
    RedisBackupStrategy,
    ConfigBackupStrategy
)
from .scheduler import BackupScheduler, ScheduleConfig
from .storage import (
    LocalStorage,
    S3Storage,
    FTPStorage,
    StorageBackend
)
from .disaster_recovery import DisasterRecoveryManager, DRConfig
from .validation import BackupValidator, ValidationConfig

__all__ = [
    # 核心组件
    "BackupManager",
    "RecoveryManager",
    "DisasterRecoveryManager",
    "BackupScheduler",
    "BackupValidator",

    # 配置类
    "BackupConfig",
    "RecoveryConfig",
    "DRConfig",
    "ScheduleConfig",
    "ValidationConfig",

    # 枚举类型
    "BackupType",
    "RecoveryType",

    # 备份策略
    "DatabaseBackupStrategy",
    "FileBackupStrategy",
    "RedisBackupStrategy",
    "ConfigBackupStrategy",

    # 存储后端
    "StorageBackend",
    "LocalStorage",
    "S3Storage",
    "FTPStorage"
]