"""
备份管理器
Week 6 Day 6: 备份恢复策略实施

负责管理各种类型的备份任务
"""

import asyncio
import gzip
import json
import os
import shutil
import tarfile
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
import logging
import hashlib
import aiofiles
import aiofiles.os

from .storage import StorageBackend, LocalStorage
from .strategies import BackupStrategy


class BackupType(Enum):
    """备份类型"""
    DATABASE = "database"
    FILES = "files"
    CONFIG = "config"
    REDIS = "redis"
    LOGS = "logs"
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class BackupStatus(Enum):
    """备份状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class BackupMetadata:
    """备份元数据"""
    backup_id: str
    backup_type: BackupType
    backup_name: str
    created_at: datetime
    completed_at: Optional[datetime]
    file_size: int
    compressed_size: int
    checksum: str
    status: BackupStatus
    description: str
    tags: List[str]
    retention_days: int
    storage_path: str
    strategy_used: str
    backup_params: Dict[str, Any]
    error_message: Optional[str] = None
    recovery_point: Optional[str] = None


@dataclass
class BackupConfig:
    """备份配置"""
    backup_type: BackupType
    strategy_name: str
    schedule: str  # cron表达式
    retention_days: int = 30
    compression: bool = True
    encryption: bool = False
    encryption_key: Optional[str] = None
    max_parallel_backups: int = 3
    timeout_seconds: int = 3600
    retry_attempts: int = 3
    retry_delay: int = 30
    notify_on_success: bool = True
    notify_on_failure: bool = True
    custom_params: Dict[str, Any] = None

    def __post_init__(self):
        if self.custom_params is None:
            self.custom_params = {}


class BackupManager:
    """备份管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage: Optional[StorageBackend] = None
        self.strategies: Dict[str, BackupStrategy] = {}
        self.active_backups: Dict[str, asyncio.Task] = {}
        self.backup_metadata: Dict[str, BackupMetadata] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

        # 备份统计
        self.total_backups = 0
        self.successful_backups = 0
        self.failed_backups = 0
        self.current_backup_id = None

    async def initialize(self, storage: StorageBackend = None):
        """初始化备份管理器"""
        if self._initialized:
            return

        # 设置存储后端
        self.storage = storage or LocalStorage(self.config.get("storage_path", "./backups"))
        await self.storage.initialize()

        # 注册备份策略
        await self._register_strategies()

        # 加载现有备份元数据
        await self._load_backup_metadata()

        self._initialized = True
        logging.info("Backup manager initialized successfully")

    async def _register_strategies(self):
        """注册备份策略"""
        from .strategies import (
            DatabaseBackupStrategy,
            FileBackupStrategy,
            RedisBackupStrategy,
            ConfigBackupStrategy
        )

        self.strategies["database"] = DatabaseBackupStrategy(self.config)
        self.strategies["files"] = FileBackupStrategy(self.config)
        self.strategies["redis"] = RedisBackupStrategy(self.config)
        self.strategies["config"] = ConfigBackupStrategy(self.config)
        self.strategies["logs"] = FileBackupStrategy(self.config, backup_logs=True)

        # 初始化所有策略
        for strategy in self.strategies.values():
            await strategy.initialize()

    async def create_backup(
        self,
        backup_config: BackupConfig,
        description: str = "",
        tags: List[str] = None,
        manual: bool = False
    ) -> str:
        """创建备份任务"""
        if not self._initialized:
            raise RuntimeError("Backup manager not initialized")

        backup_id = self._generate_backup_id(backup_config.backup_type)
        tags = tags or []

        # 创建备份元数据
        metadata = BackupMetadata(
            backup_id=backup_id,
            backup_type=backup_config.backup_type,
            backup_name=f"{backup_config.backup_type.value}_{backup_id}",
            created_at=datetime.now(),
            completed_at=None,
            file_size=0,
            compressed_size=0,
            checksum="",
            status=BackupStatus.PENDING,
            description=description,
            tags=tags,
            retention_days=backup_config.retention_days,
            storage_path="",
            strategy_used=backup_config.strategy_name,
            backup_params=backup_config.custom_params or {}
        )

        async with self._lock:
            self.backup_metadata[backup_id] = metadata

        # 启动备份任务
        task = asyncio.create_task(
            self._execute_backup(backup_id, backup_config, manual)
        )
        self.active_backups[backup_id] = task

        logging.info(f"Backup task created: {backup_id} ({backup_config.backup_type.value})")
        return backup_id

    async def _execute_backup(
        self,
        backup_id: str,
        backup_config: BackupConfig,
        manual: bool = False
    ):
        """执行备份任务"""
        metadata = self.backup_metadata[backup_id]
        strategy = self.strategies.get(backup_config.strategy_name)

        if not strategy:
            await self._mark_backup_failed(backup_id, f"Strategy {backup_config.strategy_name} not found")
            return

        try:
            # 更新状态为运行中
            await self._mark_backup_running(backup_id)
            self.current_backup_id = backup_id

            logging.info(f"Starting backup: {backup_id}")

            # 执行备份策略
            backup_data = await strategy.execute_backup(
                backup_config.backup_type,
                backup_config.custom_params or {}
            )

            # 保存备份数据
            storage_path = await self._save_backup_data(
                backup_id,
                backup_data,
                backup_config
            )

            # 更新元数据
            await self._update_backup_metadata(
                backup_id,
                storage_path,
                backup_data
            )

            # 清理临时数据
            await strategy.cleanup(backup_data)

            # 标记备份完成
            await self._mark_backup_completed(backup_id)

            self.successful_backups += 1
            logging.info(f"Backup completed successfully: {backup_id}")

        except Exception as e:
            await self._mark_backup_failed(backup_id, str(e))
            self.failed_backups += 1
            logging.error(f"Backup failed: {backup_id} - {str(e)}")

        finally:
            self.current_backup_id = None
            if backup_id in self.active_backups:
                del self.active_backups[backup_id]

    async def _save_backup_data(
        self,
        backup_id: str,
        backup_data: Dict[str, Any],
        backup_config: BackupConfig
    ) -> str:
        """保存备份数据到存储"""
        metadata = self.backup_metadata[backup_id]

        # 创建备份文件
        backup_filename = f"{metadata.backup_name}.tar"
        if backup_config.compression:
            backup_filename += ".gz"

        storage_path = await self.storage.store_backup(
            backup_id,
            backup_data,
            backup_filename,
            backup_config.compression
        )

        return storage_path

    async def _update_backup_metadata(
        self,
        backup_id: str,
        storage_path: str,
        backup_data: Dict[str, Any]
    ):
        """更新备份元数据"""
        metadata = self.backup_metadata[backup_id]

        # 计算文件大小和校验和
        file_info = await self._get_file_info(storage_path)

        metadata.storage_path = storage_path
        metadata.file_size = file_info["size"]
        metadata.compressed_size = file_info["compressed_size"]
        metadata.checksum = file_info["checksum"]
        metadata.completed_at = datetime.now()

        # 保存元数据
        await self._save_backup_metadata(backup_id)

    async def _get_file_info(self, file_path: str) -> Dict[str, int]:
        """获取文件信息"""
        if not os.path.exists(file_path):
            return {"size": 0, "compressed_size": 0, "checksum": ""}

        file_size = os.path.getsize(file_path)

        # 计算校验和
        checksum = ""
        async with aiofiles.open(file_path, 'rb') as f:
            content = await f.read()
            checksum = hashlib.sha256(content).hexdigest()

        return {
            "size": file_size,
            "compressed_size": file_size,  # 压缩后的实际大小
            "checksum": checksum
        }

    async def _mark_backup_running(self, backup_id: str):
        """标记备份为运行中"""
        async with self._lock:
            if backup_id in self.backup_metadata:
                self.backup_metadata[backup_id].status = BackupStatus.RUNNING
                await self._save_backup_metadata(backup_id)

    async def _mark_backup_completed(self, backup_id: str):
        """标记备份为完成"""
        async with self._lock:
            if backup_id in self.backup_metadata:
                self.backup_metadata[backup_id].status = BackupStatus.COMPLETED
                await self._save_backup_metadata(backup_id)

    async def _mark_backup_failed(self, backup_id: str, error_message: str):
        """标记备份为失败"""
        async with self._lock:
            if backup_id in self.backup_metadata:
                self.backup_metadata[backup_id].status = BackupStatus.FAILED
                self.backup_metadata[backup_id].error_message = error_message
                self.backup_metadata[backup_id].completed_at = datetime.now()
                await self._save_backup_metadata(backup_id)

    async def cancel_backup(self, backup_id: str) -> bool:
        """取消备份任务"""
        if backup_id not in self.active_backups:
            return False

        # 取消任务
        task = self.active_backups[backup_id]
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # 更新状态
        async with self._lock:
            if backup_id in self.backup_metadata:
                self.backup_metadata[backup_id].status = BackupStatus.CANCELLED
                self.backup_metadata[backup_id].completed_at = datetime.now()
                await self._save_backup_metadata(backup_id)

        if backup_id in self.active_backups:
            del self.active_backups[backup_id]

        logging.info(f"Backup cancelled: {backup_id}")
        return True

    async def get_backup_status(self, backup_id: str) -> Optional[BackupMetadata]:
        """获取备份状态"""
        return self.backup_metadata.get(backup_id)

    async def list_backups(
        self,
        backup_type: Optional[BackupType] = None,
        status: Optional[BackupStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[BackupMetadata]:
        """列出备份"""
        backups = list(self.backup_metadata.values())

        # 过滤条件
        if backup_type:
            backups = [b for b in backups if b.backup_type == backup_type]
        if status:
            backups = [b for b in backups if b.status == status]

        # 按创建时间排序
        backups.sort(key=lambda x: x.created_at, reverse=True)

        # 分页
        return backups[offset:offset + limit]

    async def delete_backup(self, backup_id: str) -> bool:
        """删除备份"""
        if backup_id not in self.backup_metadata:
            return False

        metadata = self.backup_metadata[backup_id]

        try:
            # 从存储删除文件
            if metadata.storage_path and os.path.exists(metadata.storage_path):
                await self.storage.delete_backup(metadata.storage_path)

            # 删除元数据
            async with self._lock:
                del self.backup_metadata[backup_id]
                await self._save_all_backup_metadata()

            logging.info(f"Backup deleted: {backup_id}")
            return True

        except Exception as e:
            logging.error(f"Failed to delete backup {backup_id}: {str(e)}")
            return False

    async def cleanup_expired_backups(self) -> int:
        """清理过期备份"""
        cleaned_count = 0
        current_time = datetime.now()

        for backup_id, metadata in list(self.backup_metadata.items()):
            if metadata.status == BackupStatus.COMPLETED:
                days_since_creation = (current_time - metadata.created_at).days
                if days_since_creation > metadata.retention_days:
                    if await self.delete_backup(backup_id):
                        cleaned_count += 1

        logging.info(f"Cleaned up {cleaned_count} expired backups")
        return cleaned_count

    async def get_backup_statistics(self) -> Dict[str, Any]:
        """获取备份统计信息"""
        total_size = sum(
            metadata.file_size for metadata in self.backup_metadata.values()
            if metadata.status == BackupStatus.COMPLETED
        )

        backup_type_counts = {}
        status_counts = {}

        for metadata in self.backup_metadata.values():
            # 按类型统计
            backup_type = metadata.backup_type.value
            backup_type_counts[backup_type] = backup_type_counts.get(backup_type, 0) + 1

            # 按状态统计
            status = metadata.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_backups": self.total_backups,
            "successful_backups": self.successful_backups,
            "failed_backups": self.failed_backups,
            "active_backups": len(self.active_backups),
            "total_size_bytes": total_size,
            "total_size_human": self._format_bytes(total_size),
            "backup_type_counts": backup_type_counts,
            "status_counts": status_counts,
            "current_backup_id": self.current_backup_id
        }

    async def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        """验证备份完整性"""
        if backup_id not in self.backup_metadata:
            return {"valid": False, "error": "Backup not found"}

        metadata = self.backup_metadata[backup_id]

        if metadata.status != BackupStatus.COMPLETED:
            return {"valid": False, "error": f"Backup not completed (status: {metadata.status.value})"}

        try:
            # 检查文件是否存在
            if not metadata.storage_path or not os.path.exists(metadata.storage_path):
                return {"valid": False, "error": "Backup file not found"}

            # 验证校验和
            current_checksum = await self._calculate_checksum(metadata.storage_path)
            if current_checksum != metadata.checksum:
                return {"valid": False, "error": "Checksum mismatch"}

            # 验证文件大小
            current_size = os.path.getsize(metadata.storage_path)
            if current_size != metadata.compressed_size:
                return {"valid": False, "error": "File size mismatch"}

            return {
                "valid": True,
                "verified_at": datetime.now().isoformat(),
                "file_size": current_size,
                "checksum": current_checksum
            }

        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def _calculate_checksum(self, file_path: str) -> str:
        """计算文件校验和"""
        async with aiofiles.open(file_path, 'rb') as f:
            content = await f.read()
            return hashlib.sha256(content).hexdigest()

    def _generate_backup_id(self, backup_type: BackupType) -> str:
        """生成备份ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{backup_type.value}_{timestamp}_{os.getpid()}"

    def _format_bytes(self, bytes_count: int) -> str:
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.2f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.2f} PB"

    async def _load_backup_metadata(self):
        """加载备份元数据"""
        metadata_file = os.path.join(
            self.storage.base_path,
            "backup_metadata.json"
        )

        if os.path.exists(metadata_file):
            try:
                async with aiofiles.open(metadata_file, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)

                for backup_id, metadata_dict in data.items():
                    metadata = BackupMetadata(**metadata_dict)
                    # 转换日期字符串
                    metadata.created_at = datetime.fromisoformat(metadata.created_at)
                    if metadata.completed_at:
                        metadata.completed_at = datetime.fromisoformat(metadata.completed_at)

                    self.backup_metadata[backup_id] = metadata

                logging.info(f"Loaded {len(self.backup_metadata)} backup metadata records")

            except Exception as e:
                logging.error(f"Failed to load backup metadata: {str(e)}")

    async def _save_backup_metadata(self, backup_id: str = None):
        """保存备份元数据"""
        metadata_file = os.path.join(
            self.storage.base_path,
            "backup_metadata.json"
        )

        # 确保目录存在
        os.makedirs(os.path.dirname(metadata_file), exist_ok=True)

        try:
            # 准备保存数据
            data = {}
            for bid, metadata in self.backup_metadata.items():
                if backup_id is None or bid == backup_id:
                    metadata_dict = asdict(metadata)
                    # 转换日期对象为字符串
                    metadata_dict["created_at"] = metadata.created_at.isoformat()
                    if metadata.completed_at:
                        metadata_dict["completed_at"] = metadata.completed_at.isoformat()
                    # 转换枚举为字符串
                    metadata_dict["backup_type"] = metadata.backup_type.value
                    metadata_dict["status"] = metadata.status.value
                    data[bid] = metadata_dict

            async with aiofiles.open(metadata_file, 'w') as f:
                await f.write(json.dumps(data, indent=2, ensure_ascii=False))

        except Exception as e:
            logging.error(f"Failed to save backup metadata: {str(e)}")

    async def _save_all_backup_metadata(self):
        """保存所有备份元数据"""
        await self._save_backup_metadata(None)

    async def shutdown(self):
        """关闭备份管理器"""
        # 取消所有活跃的备份任务
        for backup_id in list(self.active_backups.keys()):
            await self.cancel_backup(backup_id)

        # 关闭存储后端
        if self.storage:
            await self.storage.shutdown()

        # 关闭所有策略
        for strategy in self.strategies.values():
            await strategy.shutdown()

        logging.info("Backup manager shutdown completed")