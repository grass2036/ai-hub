"""
恢复管理器
Week 6 Day 6: 备份恢复策略实施

负责管理各种类型的恢复任务
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
import aiofiles
import asyncpg
import redis.asyncio as redis

from .storage import StorageBackend
from .backup_manager import BackupMetadata, BackupType


class RecoveryType(Enum):
    """恢复类型"""
    FULL = "full"
    PARTIAL = "partial"
    POINT_IN_TIME = "point_in_time"
    SELECTIVE = "selective"


class RecoveryStatus(Enum):
    """恢复状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    VALIDATION_FAILED = "validation_failed"


@dataclass
class RecoveryMetadata:
    """恢复元数据"""
    recovery_id: str
    backup_id: str
    recovery_type: RecoveryType
    backup_type: BackupType
    created_at: datetime
    completed_at: Optional[datetime]
    status: RecoveryStatus
    source_path: str
    target_path: str
    description: str
    recovered_files: List[str]
    recovery_params: Dict[str, Any]
    validation_results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    rollback_available: bool = False
    rollback_path: Optional[str] = None


@dataclass
class RecoveryConfig:
    """恢复配置"""
    backup_id: str
    recovery_type: RecoveryType
    target_path: str
    validate_after_recovery: bool = True
    create_rollback: bool = True
    overwrite_existing: bool = False
    backup_existing: bool = True
    recovery_params: Dict[str, Any] = None

    def __post_init__(self):
        if self.recovery_params is None:
            self.recovery_params = {}


class RecoveryManager:
    """恢复管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage: Optional[StorageBackend] = None
        self.active_recoveries: Dict[str, asyncio.Task] = {}
        self.recovery_metadata: Dict[str, RecoveryMetadata] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

        # 恢复统计
        self.total_recoveries = 0
        self.successful_recoveries = 0
        self.failed_recoveries = 0
        self.current_recovery_id = None

    async def initialize(self, storage: StorageBackend):
        """初始化恢复管理器"""
        if self._initialized:
            return

        self.storage = storage
        await self.storage.initialize()

        # 加载现有恢复元数据
        await self._load_recovery_metadata()

        self._initialized = True
        logging.info("Recovery manager initialized successfully")

    async def create_recovery(
        self,
        recovery_config: RecoveryConfig,
        description: str = ""
    ) -> str:
        """创建恢复任务"""
        if not self._initialized:
            raise RuntimeError("Recovery manager not initialized")

        recovery_id = self._generate_recovery_id()

        # 验证备份存在
        backup_metadata = await self._get_backup_metadata(recovery_config.backup_id)
        if not backup_metadata:
            raise ValueError(f"Backup {recovery_config.backup_id} not found")

        # 创建恢复元数据
        metadata = RecoveryMetadata(
            recovery_id=recovery_id,
            backup_id=recovery_config.backup_id,
            recovery_type=recovery_config.recovery_type,
            backup_type=backup_metadata.backup_type,
            created_at=datetime.now(),
            completed_at=None,
            status=RecoveryStatus.PENDING,
            source_path=backup_metadata.storage_path,
            target_path=recovery_config.target_path,
            description=description,
            recovered_files=[],
            recovery_params=recovery_config.recovery_params or {}
        )

        async with self._lock:
            self.recovery_metadata[recovery_id] = metadata

        # 启动恢复任务
        task = asyncio.create_task(
            self._execute_recovery(recovery_id, recovery_config)
        )
        self.active_recoveries[recovery_id] = task

        logging.info(f"Recovery task created: {recovery_id}")
        return recovery_id

    async def _execute_recovery(
        self,
        recovery_id: str,
        recovery_config: RecoveryConfig
    ):
        """执行恢复任务"""
        metadata = self.recovery_metadata[recovery_id]

        try:
            # 更新状态为运行中
            await self._mark_recovery_running(recovery_id)
            self.current_recovery_id = recovery_id

            logging.info(f"Starting recovery: {recovery_id}")

            # 创建回滚点
            if recovery_config.create_rollback:
                rollback_path = await self._create_rollback_point(
                    recovery_config.target_path,
                    recovery_id
                )
                metadata.rollback_path = rollback_path
                metadata.rollback_available = True

            # 下载备份数据
            backup_data = await self.storage.retrieve_backup(metadata.source_path)

            try:
                # 执行恢复
                recovered_files = await self._execute_recovery_strategy(
                    metadata.backup_type,
                    backup_data,
                    recovery_config
                )
                metadata.recovered_files = recovered_files

                # 验证恢复结果
                if recovery_config.validate_after_recovery:
                    validation_results = await self._validate_recovery(
                        metadata.backup_type,
                        recovered_files,
                        recovery_config
                    )
                    metadata.validation_results = validation_results

                    if not validation_results.get("valid", False):
                        await self._mark_recovery_validation_failed(
                            recovery_id,
                            validation_results.get("error", "Validation failed")
                        )
                        return

                # 标记恢复完成
                await self._mark_recovery_completed(recovery_id)
                self.successful_recoveries += 1
                logging.info(f"Recovery completed successfully: {recovery_id}")

            finally:
                # 清理临时备份数据
                await self._cleanup_backup_data(backup_data)

        except Exception as e:
            await self._mark_recovery_failed(recovery_id, str(e))
            self.failed_recoveries += 1
            logging.error(f"Recovery failed: {recovery_id} - {str(e)}")

        finally:
            self.current_recovery_id = None
            if recovery_id in self.active_recoveries:
                del self.active_recoveries[recovery_id]

    async def _execute_recovery_strategy(
        self,
        backup_type: BackupType,
        backup_data: str,
        recovery_config: RecoveryConfig
    ) -> List[str]:
        """执行特定类型的恢复策略"""
        if backup_type == BackupType.DATABASE:
            return await self._recover_database(backup_data, recovery_config)
        elif backup_type == BackupType.FILES:
            return await self._recover_files(backup_data, recovery_config)
        elif backup_type == BackupType.CONFIG:
            return await self._recover_config(backup_data, recovery_config)
        elif backup_type == BackupType.REDIS:
            return await self._recover_redis(backup_data, recovery_config)
        else:
            raise ValueError(f"Unsupported backup type: {backup_type}")

    async def _recover_database(
        self,
        backup_data: str,
        recovery_config: RecoveryConfig
    ) -> List[str]:
        """恢复数据库"""
        recovered_files = []

        try:
            # 查找数据库备份文件
            backup_files = []
            for root, dirs, files in os.walk(backup_data):
                for file in files:
                    if file.endswith(('.sql', '.db')):
                        backup_files.append(os.path.join(root, file))

            if not backup_files:
                raise Exception("No database backup files found")

            # 恢复PostgreSQL数据库
            if self.config.get("database", {}).get("type", "").lower() == "postgresql":
                recovered_files.extend(
                    await self._recover_postgresql(backup_files, recovery_config)
                )

            # 恢复SQLite数据库
            elif self.config.get("database", {}).get("type", "").lower() == "sqlite":
                recovered_files.extend(
                    await self._recover_sqlite(backup_files, recovery_config)
                )

        except Exception as e:
            logging.error(f"Database recovery error: {str(e)}")
            raise e

        return recovered_files

    async def _recover_postgresql(
        self,
        backup_files: List[str],
        recovery_config: RecoveryConfig
    ) -> List[str]:
        """恢复PostgreSQL数据库"""
        recovered_files = []
        db_config = self.config.get("database", {})

        try:
            db_url = db_config.get("url", "")
            if not db_url:
                raise ValueError("PostgreSQL database URL not configured")

            # 查找.sql或.dump文件
            sql_files = [f for f in backup_files if f.endswith(('.sql', '.dump'))]
            if not sql_files:
                raise Exception("No PostgreSQL backup files found")

            for sql_file in sql_files:
                # 执行psql恢复
                cmd = [
                    "psql",
                    "--no-password",
                    "--verbose",
                    "--file", sql_file,
                    db_url
                ]

                # 设置密码环境变量
                import urllib.parse
                parsed = urllib.parse.urlparse(db_url)
                env = os.environ.copy()
                if parsed.password:
                    env["PGPASSWORD"] = parsed.password

                # 执行恢复命令
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    raise Exception(f"PostgreSQL recovery failed: {stderr.decode()}")

                recovered_files.append(sql_file)
                logging.info(f"PostgreSQL recovery completed: {sql_file}")

        except Exception as e:
            logging.error(f"PostgreSQL recovery error: {str(e)}")
            raise e

        return recovered_files

    async def _recover_sqlite(
        self,
        backup_files: List[str],
        recovery_config: RecoveryConfig
    ) -> List[str]:
        """恢复SQLite数据库"""
        recovered_files = []
        db_config = self.config.get("database", {})

        try:
            target_db_path = db_config.get("path", "")
            if not target_db_path:
                raise ValueError("SQLite database path not configured")

            # 查找.db文件
            db_files = [f for f in backup_files if f.endswith('.db')]
            if not db_files:
                raise Exception("No SQLite backup files found")

            for db_file in db_files:
                # 备份现有数据库
                if recovery_config.backup_existing and os.path.exists(target_db_path):
                    backup_name = f"{target_db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    import shutil
                    shutil.copy2(target_db_path, backup_name)
                    recovered_files.append(backup_name)

                # 恢复数据库
                import shutil
                shutil.copy2(db_file, target_db_path)

                recovered_files.append(target_db_path)
                logging.info(f"SQLite recovery completed: {target_db_path}")

        except Exception as e:
            logging.error(f"SQLite recovery error: {str(e)}")
            raise e

        return recovered_files

    async def _recover_files(
        self,
        backup_data: str,
        recovery_config: RecoveryConfig
    ) -> List[str]:
        """恢复文件"""
        recovered_files = []

        try:
            target_path = Path(recovery_config.target_path)
            target_path.mkdir(parents=True, exist_ok=True)

            # 递归复制文件
            for root, dirs, files in os.walk(backup_data):
                # 跳过元数据文件
                dirs[:] = [d for d in dirs if not d.endswith('_info') and not d.endswith('_manifest')]

                for file in files:
                    if file.endswith(('.json', '.txt', '.log')):
                        continue  # 跳过元数据文件

                    source_file = os.path.join(root, file)
                    relative_path = os.path.relpath(source_file, backup_data)
                    target_file = target_path / relative_path

                    # 确保目标目录存在
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    # 备份现有文件
                    if recovery_config.backup_existing and target_file.exists():
                        backup_name = f"{target_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        import shutil
                        shutil.copy2(target_file, backup_name)
                        recovered_files.append(str(backup_name))

                    # 复制文件
                    import shutil
                    shutil.copy2(source_file, target_file)
                    recovered_files.append(str(target_file))

        except Exception as e:
            logging.error(f"File recovery error: {str(e)}")
            raise e

        return recovered_files

    async def _recover_config(
        self,
        backup_data: str,
        recovery_config: RecoveryConfig
    ) -> List[str]:
        """恢复配置"""
        recovered_files = []

        try:
            target_path = Path(recovery_config.target_path)
            target_path.mkdir(parents=True, exist_ok=True)

            # 恢复配置文件
            for root, dirs, files in os.walk(backup_data):
                for file in files:
                    if file.endswith(('.yml', '.yaml', '.conf', '.env')):
                        source_file = os.path.join(root, file)
                        target_file = target_path / file

                        # 备份现有配置
                        if recovery_config.backup_existing and target_file.exists():
                            backup_name = f"{target_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                            import shutil
                            shutil.copy2(target_file, backup_name)
                            recovered_files.append(str(backup_name))

                        # 复制配置文件
                        import shutil
                        shutil.copy2(source_file, target_file)
                        recovered_files.append(str(target_file))

        except Exception as e:
            logging.error(f"Config recovery error: {str(e)}")
            raise e

        return recovered_files

    async def _recover_redis(
        self,
        backup_data: str,
        recovery_config: RecoveryConfig
    ) -> List[str]:
        """恢复Redis数据"""
        recovered_files = []

        try:
            # 查找Redis备份文件
            redis_files = []
            for root, dirs, files in os.walk(backup_data):
                for file in files:
                    if file.endswith(('.rdb', '.aof')):
                        redis_files.append(os.path.join(root, file))

            if not redis_files:
                raise Exception("No Redis backup files found")

            # 恢复Redis数据
            for redis_file in redis_files:
                # 获取Redis数据目录
                redis_config = self.config.get("redis", {})
                redis_data_dir = redis_config.get("data_dir", "/var/lib/redis")

                # 停止Redis服务
                await self._stop_redis_service()

                try:
                    # 备份现有数据
                    if recovery_config.backup_existing:
                        for data_file in os.listdir(redis_data_dir):
                            if data_file.endswith(('.rdb', '.aof')):
                                source_path = os.path.join(redis_data_dir, data_file)
                                backup_name = f"{source_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                import shutil
                                shutil.copy2(source_path, backup_name)
                                recovered_files.append(backup_name)

                    # 复制备份文件
                    import shutil
                    target_file = os.path.join(redis_data_dir, os.path.basename(redis_file))
                    shutil.copy2(redis_file, target_file)
                    recovered_files.append(target_file)

                finally:
                    # 启动Redis服务
                    await self._start_redis_service()

        except Exception as e:
            logging.error(f"Redis recovery error: {str(e)}")
            raise e

        return recovered_files

    async def _stop_redis_service(self):
        """停止Redis服务"""
        try:
            process = await asyncio.create_subprocess_exec(
                "systemctl", "stop", "redis",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
        except Exception:
            pass  # Redis可能没有使用systemctl管理

    async def _start_redis_service(self):
        """启动Redis服务"""
        try:
            process = await asyncio.create_subprocess_exec(
                "systemctl", "start", "redis",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
        except Exception:
            pass  # Redis可能没有使用systemctl管理

    async def _validate_recovery(
        self,
        backup_type: BackupType,
        recovered_files: List[str],
        recovery_config: RecoveryConfig
    ) -> Dict[str, Any]:
        """验证恢复结果"""
        validation_results = {
            "valid": True,
            "checks": {},
            "errors": []
        }

        try:
            if backup_type == BackupType.DATABASE:
                validation_results.update(await self._validate_database_recovery(recovered_files))
            elif backup_type == BackupType.FILES:
                validation_results.update(await self._validate_files_recovery(recovered_files))
            elif backup_type == BackupType.CONFIG:
                validation_results.update(await self._validate_config_recovery(recovered_files))
            elif backup_type == BackupType.REDIS:
                validation_results.update(await self._validate_redis_recovery(recovered_files))

        except Exception as e:
            validation_results["valid"] = False
            validation_results["errors"].append(str(e))

        return validation_results

    async def _validate_database_recovery(self, recovered_files: List[str]) -> Dict[str, Any]:
        """验证数据库恢复"""
        validation = {
            "database_connected": False,
            "tables_exist": False,
            "data_integrity": False
        }

        try:
            # 测试数据库连接
            db_config = self.config.get("database", {})
            db_type = db_config.get("type", "").lower()

            if db_type == "postgresql":
                # 验证PostgreSQL连接
                import asyncpg
                conn = await asyncpg.connect(db_config.get("url"))
                validation["database_connected"] = True

                # 检查表是否存在
                tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                validation["tables_exist"] = len(tables) > 0

                # 简单的数据完整性检查
                if tables:
                    table_count = await conn.fetchval("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
                    validation["data_integrity"] = table_count > 0

                await conn.close()

            elif db_type == "sqlite":
                # 验证SQLite连接
                db_path = db_config.get("path")
                if os.path.exists(db_path):
                    validation["database_connected"] = True
                    validation["tables_exist"] = True
                    validation["data_integrity"] = True

        except Exception as e:
            logging.error(f"Database validation error: {str(e)}")

        return validation

    async def _validate_files_recovery(self, recovered_files: List[str]) -> Dict[str, Any]:
        """验证文件恢复"""
        validation = {
            "files_exist": False,
            "file_count": 0,
            "total_size": 0
        }

        try:
            existing_files = [f for f in recovered_files if os.path.exists(f)]
            validation["files_exist"] = len(existing_files) > 0
            validation["file_count"] = len(existing_files)
            validation["total_size"] = sum(os.path.getsize(f) for f in existing_files)

        except Exception as e:
            logging.error(f"Files validation error: {str(e)}")

        return validation

    async def _validate_config_recovery(self, recovered_files: List[str]) -> Dict[str, Any]:
        """验证配置恢复"""
        validation = {
            "configs_valid": False,
            "config_count": 0
        }

        try:
            valid_configs = []
            for config_file in recovered_files:
                if config_file.endswith(('.yml', '.yaml', '.conf')):
                    # 简单的配置文件格式验证
                    try:
                        async with aiofiles.open(config_file, 'r') as f:
                            content = await f.read()
                            if content.strip():  # 文件不为空
                                valid_configs.append(config_file)
                    except Exception:
                        pass

            validation["configs_valid"] = len(valid_configs) > 0
            validation["config_count"] = len(valid_configs)

        except Exception as e:
            logging.error(f"Config validation error: {str(e)}")

        return validation

    async def _validate_redis_recovery(self, recovered_files: List[str]) -> Dict[str, Any]:
        """验证Redis恢复"""
        validation = {
            "redis_connected": False,
            "data_loaded": False
        }

        try:
            # 测试Redis连接
            redis_config = self.config.get("redis", {})
            redis_url = redis_config.get("url", "redis://localhost:6379/0")

            client = redis.from_url(redis_url, decode_responses=True)
            await client.ping()
            validation["redis_connected"] = True

            # 检查是否有数据
            info = await client.info()
            validation["data_loaded"] = info.get("used_memory", 0) > 0

            await client.close()

        except Exception as e:
            logging.error(f"Redis validation error: {str(e)}")

        return validation

    async def _create_rollback_point(self, target_path: str, recovery_id: str) -> str:
        """创建回滚点"""
        try:
            rollback_dir = tempfile.mkdtemp(prefix=f"rollback_{recovery_id}_")

            # 复制目标目录到回滚目录
            if os.path.exists(target_path):
                import shutil
                shutil.copytree(target_path, rollback_dir, dirs_exist_ok=True)

            return rollback_dir

        except Exception as e:
            logging.error(f"Failed to create rollback point: {str(e)}")
            return ""

    async def rollback_recovery(self, recovery_id: str) -> bool:
        """回滚恢复"""
        if recovery_id not in self.recovery_metadata:
            return False

        metadata = self.recovery_metadata[recovery_id]

        if not metadata.rollback_available or not metadata.rollback_path:
            return False

        try:
            # 执行回滚
            target_path = metadata.target_path
            rollback_path = metadata.rollback_path

            if os.path.exists(rollback_path):
                import shutil
                if os.path.exists(target_path):
                    shutil.rmtree(target_path)
                shutil.copytree(rollback_path, target_path)

            logging.info(f"Recovery rolled back: {recovery_id}")
            return True

        except Exception as e:
            logging.error(f"Failed to rollback recovery {recovery_id}: {str(e)}")
            return False

    async def cancel_recovery(self, recovery_id: str) -> bool:
        """取消恢复任务"""
        if recovery_id not in self.active_recoveries:
            return False

        task = self.active_recoveries[recovery_id]
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        async with self._lock:
            if recovery_id in self.recovery_metadata:
                self.recovery_metadata[recovery_id].status = RecoveryStatus.CANCELLED
                self.recovery_metadata[recovery_id].completed_at = datetime.now()

        if recovery_id in self.active_recoveries:
            del self.active_recoveries[recovery_id]

        logging.info(f"Recovery cancelled: {recovery_id}")
        return True

    async def get_recovery_status(self, recovery_id: str) -> Optional[RecoveryMetadata]:
        """获取恢复状态"""
        return self.recovery_metadata.get(recovery_id)

    async def list_recoveries(
        self,
        backup_type: Optional[BackupType] = None,
        status: Optional[RecoveryStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[RecoveryMetadata]:
        """列出恢复任务"""
        recoveries = list(self.recovery_metadata.values())

        # 过滤条件
        if backup_type:
            recoveries = [r for r in recoveries if r.backup_type == backup_type]
        if status:
            recoveries = [r for r in recoveries if r.status == status]

        # 按创建时间排序
        recoveries.sort(key=lambda x: x.created_at, reverse=True)

        # 分页
        return recoveries[offset:offset + limit]

    async def get_recovery_statistics(self) -> Dict[str, Any]:
        """获取恢复统计信息"""
        recovery_type_counts = {}
        status_counts = {}

        for metadata in self.recovery_metadata.values():
            # 按类型统计
            recovery_type = metadata.recovery_type.value
            recovery_type_counts[recovery_type] = recovery_type_counts.get(recovery_type, 0) + 1

            # 按状态统计
            status = metadata.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_recoveries": self.total_recoveries,
            "successful_recoveries": self.successful_recoveries,
            "failed_recoveries": self.failed_recoveries,
            "active_recoveries": len(self.active_recoveries),
            "recovery_type_counts": recovery_type_counts,
            "status_counts": status_counts,
            "current_recovery_id": self.current_recovery_id
        }

    def _generate_recovery_id(self) -> str:
        """生成恢复ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"recovery_{timestamp}_{os.getpid()}"

    async def _get_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """获取备份元数据"""
        # 这里应该从备份管理器获取元数据
        # 简化实现，返回None
        return None

    async def _mark_recovery_running(self, recovery_id: str):
        """标记恢复为运行中"""
        async with self._lock:
            if recovery_id in self.recovery_metadata:
                self.recovery_metadata[recovery_id].status = RecoveryStatus.RUNNING

    async def _mark_recovery_completed(self, recovery_id: str):
        """标记恢复为完成"""
        async with self._lock:
            if recovery_id in self.recovery_metadata:
                self.recovery_metadata[recovery_id].status = RecoveryStatus.COMPLETED
                self.recovery_metadata[recovery_id].completed_at = datetime.now()

    async def _mark_recovery_failed(self, recovery_id: str, error_message: str):
        """标记恢复为失败"""
        async with self._lock:
            if recovery_id in self.recovery_metadata:
                self.recovery_metadata[recovery_id].status = RecoveryStatus.FAILED
                self.recovery_metadata[recovery_id].error_message = error_message
                self.recovery_metadata[recovery_id].completed_at = datetime.now()

    async def _mark_recovery_validation_failed(self, recovery_id: str, error_message: str):
        """标记恢复验证失败"""
        async with self._lock:
            if recovery_id in self.recovery_metadata:
                self.recovery_metadata[recovery_id].status = RecoveryStatus.VALIDATION_FAILED
                self.recovery_metadata[recovery_id].error_message = error_message
                self.recovery_metadata[recovery_id].completed_at = datetime.now()

    async def _cleanup_backup_data(self, backup_data: str):
        """清理备份数据"""
        if backup_data and os.path.exists(backup_data):
            import shutil
            shutil.rmtree(backup_data, ignore_errors=True)

    async def _load_recovery_metadata(self):
        """加载恢复元数据"""
        # 简化实现，实际应该从存储加载
        pass

    async def shutdown(self):
        """关闭恢复管理器"""
        # 取消所有活跃的恢复任务
        for recovery_id in list(self.active_recoveries.keys()):
            await self.cancel_recovery(recovery_id)

        logging.info("Recovery manager shutdown completed")