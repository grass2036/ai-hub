"""
备份策略
Week 6 Day 6: 备份恢复策略实施

定义各种类型的备份策略实现
"""

import asyncio
import gzip
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import aiofiles
import aiofiles.os
import asyncpg
import redis.asyncio as redis

from .storage import StorageBackend


class BackupStrategy(ABC):
    """备份策略基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._initialized = False

    async def initialize(self):
        """初始化策略"""
        self._initialized = True

    async def shutdown(self):
        """关闭策略"""
        pass

    @abstractmethod
    async def execute_backup(self, backup_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行备份"""
        pass

    @abstractmethod
    async def cleanup(self, backup_data: Dict[str, Any]):
        """清理备份数据"""
        pass


class DatabaseBackupStrategy(BackupStrategy):
    """数据库备份策略"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.db_config = config.get("database", {})
        self.backup_path = config.get("backup_path", "./backups")

    async def execute_backup(self, backup_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据库备份"""
        if backup_type != "database":
            raise ValueError("This strategy only supports database backups")

        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="db_backup_")

        try:
            # 执行数据库备份
            backup_files = []

            # PostgreSQL备份
            if self.db_config.get("type", "").lower() == "postgresql":
                backup_files.extend(await self._backup_postgresql(temp_dir, params))

            # SQLite备份
            elif self.db_config.get("type", "").lower() == "sqlite":
                backup_files.extend(await self._backup_sqlite(temp_dir, params))

            # 创建备份信息文件
            info_file = await self._create_backup_info(temp_dir, backup_files)
            backup_files.append(info_file)

            return {
                "temp_dir": temp_dir,
                "backup_files": backup_files,
                "backup_type": "database",
                "created_at": datetime.now().isoformat(),
                "params": params
            }

        except Exception as e:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e

    async def _backup_postgresql(self, temp_dir: str, params: Dict[str, Any]) -> List[str]:
        """备份PostgreSQL数据库"""
        db_url = self.db_config.get("url", "")
        if not db_url:
            raise ValueError("PostgreSQL database URL not configured")

        backup_files = []

        try:
            # 解析数据库连接信息
            # 格式: postgresql://user:password@host:port/database
            import urllib.parse
            parsed = urllib.parse.urlparse(db_url)

            db_name = parsed.path[1:]  # 去掉开头的 /

            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(temp_dir, f"postgresql_{db_name}_{timestamp}.sql")

            # 执行pg_dump
            cmd = [
                "pg_dump",
                "--no-password",
                "--verbose",
                "--clean",
                "--no-acl",
                "--no-owner",
                "--format=custom",
                "--file", backup_file,
                db_url
            ]

            # 设置密码环境变量
            env = os.environ.copy()
            if parsed.password:
                env["PGPASSWORD"] = parsed.password

            # 执行备份命令
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise Exception(f"PostgreSQL backup failed: {stderr.decode()}")

            backup_files.append(backup_file)
            logging.info(f"PostgreSQL backup completed: {backup_file}")

        except Exception as e:
            logging.error(f"PostgreSQL backup error: {str(e)}")
            raise e

        return backup_files

    async def _backup_sqlite(self, temp_dir: str, params: Dict[str, Any]) -> List[str]:
        """备份SQLite数据库"""
        db_path = self.db_config.get("path", "")
        if not db_path or not os.path.exists(db_path):
            raise ValueError("SQLite database file not found")

        backup_files = []

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(temp_dir, f"sqlite_backup_{timestamp}.db")

            # 直接复制数据库文件
            async with aiofiles.open(db_path, 'rb') as src:
                content = await src.read()
                async with aiofiles.open(backup_file, 'wb') as dst:
                    await dst.write(content)

            backup_files.append(backup_file)
            logging.info(f"SQLite backup completed: {backup_file}")

        except Exception as e:
            logging.error(f"SQLite backup error: {str(e)}")
            raise e

        return backup_files

    async def _create_backup_info(self, temp_dir: str, backup_files: List[str]) -> str:
        """创建备份信息文件"""
        info_file = os.path.join(temp_dir, "backup_info.json")

        info = {
            "backup_type": "database",
            "database_type": self.db_config.get("type", "unknown"),
            "created_at": datetime.now().isoformat(),
            "backup_files": [os.path.basename(f) for f in backup_files],
            "file_sizes": {os.path.basename(f): os.path.getsize(f) for f in backup_files},
            "total_size": sum(os.path.getsize(f) for f in backup_files),
            "config": {
                "type": self.db_config.get("type"),
                "host": self.db_config.get("host"),
                "port": self.db_config.get("port"),
                "database": self.db_config.get("database")
            }
        }

        async with aiofiles.open(info_file, 'w') as f:
            await f.write(json.dumps(info, indent=2, ensure_ascii=False))

        return info_file

    async def cleanup(self, backup_data: Dict[str, Any]):
        """清理备份数据"""
        temp_dir = backup_data.get("temp_dir")
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


class FileBackupStrategy(BackupStrategy):
    """文件备份策略"""

    def __init__(self, config: Dict[str, Any], backup_logs: bool = False):
        super().__init__(config)
        self.backup_logs = backup_logs
        self.backup_paths = config.get("backup_paths", [])
        self.exclude_patterns = config.get("exclude_patterns", [])
        self.max_file_size = config.get("max_file_size", 100 * 1024 * 1024)  # 100MB

    async def execute_backup(self, backup_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行文件备份"""
        if backup_type not in ["files", "logs"]:
            raise ValueError("This strategy only supports files and logs backups")

        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="file_backup_")

        try:
            # 确定备份路径
            if self.backup_logs:
                paths_to_backup = self._get_log_paths()
            else:
                paths_to_backup = self.backup_paths or params.get("paths", [])

            if not paths_to_backup:
                raise ValueError("No paths specified for backup")

            backup_files = []
            total_files = 0

            # 备份每个路径
            for path in paths_to_backup:
                if os.path.exists(path):
                    files = await self._backup_path(path, temp_dir)
                    backup_files.extend(files)
                    total_files += len(files)

            # 创建备份清单
            manifest_file = await self._create_backup_manifest(
                temp_dir, backup_files, total_files
            )
            backup_files.append(manifest_file)

            return {
                "temp_dir": temp_dir,
                "backup_files": backup_files,
                "backup_type": backup_type,
                "total_files": total_files,
                "created_at": datetime.now().isoformat(),
                "paths_backed_up": paths_to_backup
            }

        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e

    def _get_log_paths(self) -> List[str]:
        """获取日志路径"""
        default_log_paths = [
            "./logs",
            "/var/log/ai-hub",
            "./data/logs"
        ]
        return default_log_paths

    async def _backup_path(self, source_path: str, temp_dir: str) -> List[str]:
        """备份指定路径"""
        backup_files = []

        if os.path.isfile(source_path):
            # 备份单个文件
            await self._backup_file(source_path, temp_dir, backup_files)
        elif os.path.isdir(source_path):
            # 备份目录
            await self._backup_directory(source_path, temp_dir, backup_files)

        return backup_files

    async def _backup_file(self, source_file: str, temp_dir: str, backup_files: List[str]):
        """备份单个文件"""
        try:
            # 检查文件大小
            file_size = os.path.getsize(source_file)
            if file_size > self.max_file_size:
                logging.warning(f"Skipping large file: {source_file} ({file_size} bytes)")
                return

            # 检查排除模式
            if self._should_exclude(source_file):
                return

            # 创建目标路径
            relative_path = os.path.relpath(source_file, "/")
            target_file = os.path.join(temp_dir, relative_path)

            # 确保目标目录存在
            os.makedirs(os.path.dirname(target_file), exist_ok=True)

            # 复制文件
            async with aiofiles.open(source_file, 'rb') as src:
                content = await src.read()
                async with aiofiles.open(target_file, 'wb') as dst:
                    await dst.write(content)

            backup_files.append(target_file)

        except Exception as e:
            logging.error(f"Failed to backup file {source_file}: {str(e)}")

    async def _backup_directory(self, source_dir: str, temp_dir: str, backup_files: List[str]):
        """备份目录"""
        for root, dirs, files in os.walk(source_dir):
            # 过滤目录
            dirs[:] = [d for d in dirs if not self._should_exclude(os.path.join(root, d))]

            for file in files:
                file_path = os.path.join(root, file)
                await self._backup_file(file_path, temp_dir, backup_files)

    def _should_exclude(self, path: str) -> bool:
        """检查是否应该排除该路径"""
        import fnmatch

        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
                return True

        return False

    async def _create_backup_manifest(
        self, temp_dir: str, backup_files: List[str], total_files: int
    ) -> str:
        """创建备份清单"""
        manifest_file = os.path.join(temp_dir, "backup_manifest.json")

        manifest = {
            "backup_type": "files" if not self.backup_logs else "logs",
            "created_at": datetime.now().isoformat(),
            "total_files": total_files,
            "total_size": sum(os.path.getsize(f) for f in backup_files if os.path.isfile(f)),
            "backup_files": [
                {
                    "path": os.path.relpath(f, temp_dir),
                    "size": os.path.getsize(f),
                    "modified": datetime.fromtimestamp(os.path.getmtime(f)).isoformat()
                }
                for f in backup_files if os.path.isfile(f)
            ]
        }

        async with aiofiles.open(manifest_file, 'w') as f:
            await f.write(json.dumps(manifest, indent=2, ensure_ascii=False))

        return manifest_file

    async def cleanup(self, backup_data: Dict[str, Any]):
        """清理备份数据"""
        temp_dir = backup_data.get("temp_dir")
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


class RedisBackupStrategy(BackupStrategy):
    """Redis备份策略"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.redis_config = config.get("redis", {})

    async def execute_backup(self, backup_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行Redis备份"""
        if backup_type != "redis":
            raise ValueError("This strategy only supports Redis backups")

        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="redis_backup_")

        try:
            backup_files = []

            # 获取Redis连接
            redis_client = await self._get_redis_client()

            # 执行Redis备份
            if self.redis_config.get("backup_method", "rdb") == "rdb":
                backup_files.extend(await self._backup_rdb(redis_client, temp_dir, params))
            else:
                backup_files.extend(await self._backup_aof(redis_client, temp_dir, params))

            # 关闭Redis连接
            await redis_client.close()

            # 创建备份信息
            info_file = await self._create_redis_backup_info(temp_dir, backup_files)
            backup_files.append(info_file)

            return {
                "temp_dir": temp_dir,
                "backup_files": backup_files,
                "backup_type": "redis",
                "created_at": datetime.now().isoformat(),
                "params": params
            }

        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e

    async def _get_redis_client(self) -> redis.Redis:
        """获取Redis客户端"""
        redis_url = self.redis_config.get("url", "redis://localhost:6379/0")
        return redis.from_url(redis_url, decode_responses=True)

    async def _backup_rdb(self, redis_client: redis.Redis, temp_dir: str, params: Dict[str, Any]) -> List[str]:
        """执行RDB备份"""
        backup_files = []

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rdb_file = os.path.join(temp_dir, f"redis_backup_{timestamp}.rdb")

            # 使用BGSAVE创建后台RDB快照
            await redis_client.bgsave()

            # 等待备份完成
            last_save_time = await redis_client.lastsave()
            while True:
                current_save_time = await redis_client.lastsave()
                if current_save_time > last_save_time:
                    break
                await asyncio.sleep(1)

            # 复制RDB文件
            rdb_path = self.redis_config.get("rdb_path", "/var/lib/redis/dump.rdb")
            if os.path.exists(rdb_path):
                async with aiofiles.open(rdb_path, 'rb') as src:
                    content = await src.read()
                    async with aiofiles.open(rdb_file, 'wb') as dst:
                        await dst.write(content)

                backup_files.append(rdb_file)
                logging.info(f"Redis RDB backup completed: {rdb_file}")
            else:
                raise Exception(f"Redis RDB file not found: {rdb_path}")

        except Exception as e:
            logging.error(f"Redis RDB backup error: {str(e)}")
            raise e

        return backup_files

    async def _backup_aof(self, redis_client: redis.Redis, temp_dir: str, params: Dict[str, Any]) -> List[str]:
        """执行AOF备份"""
        backup_files = []

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            aof_file = os.path.join(temp_dir, f"redis_backup_{timestamp}.aof")

            # 复制AOF文件
            aof_path = self.redis_config.get("aof_path", "/var/lib/redis/appendonly.aof")
            if os.path.exists(aof_path):
                async with aiofiles.open(aof_path, 'rb') as src:
                    content = await src.read()
                    async with aiofiles.open(aof_file, 'wb') as dst:
                        await dst.write(content)

                backup_files.append(aof_file)
                logging.info(f"Redis AOF backup completed: {aof_file}")
            else:
                raise Exception(f"Redis AOF file not found: {aof_path}")

        except Exception as e:
            logging.error(f"Redis AOF backup error: {str(e)}")
            raise e

        return backup_files

    async def _create_redis_backup_info(self, temp_dir: str, backup_files: List[str]) -> str:
        """创建Redis备份信息"""
        info_file = os.path.join(temp_dir, "redis_backup_info.json")

        info = {
            "backup_type": "redis",
            "backup_method": self.redis_config.get("backup_method", "rdb"),
            "created_at": datetime.now().isoformat(),
            "backup_files": [os.path.basename(f) for f in backup_files],
            "file_sizes": {os.path.basename(f): os.path.getsize(f) for f in backup_files},
            "total_size": sum(os.path.getsize(f) for f in backup_files),
            "redis_config": {
                "host": self.redis_config.get("host", "localhost"),
                "port": self.redis_config.get("port", 6379),
                "database": self.redis_config.get("database", 0)
            }
        }

        async with aiofiles.open(info_file, 'w') as f:
            await f.write(json.dumps(info, indent=2, ensure_ascii=False))

        return info_file

    async def cleanup(self, backup_data: Dict[str, Any]):
        """清理备份数据"""
        temp_dir = backup_data.get("temp_dir")
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


class ConfigBackupStrategy(BackupStrategy):
    """配置备份策略"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.config_paths = config.get("config_paths", [])
        self.environment_vars = config.get("environment_vars", [])

    async def execute_backup(self, backup_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行配置备份"""
        if backup_type != "config":
            raise ValueError("This strategy only supports config backups")

        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="config_backup_")

        try:
            backup_files = []

            # 备份配置文件
            await self._backup_config_files(temp_dir, backup_files)

            # 备份环境变量
            env_file = await self._backup_environment_variables(temp_dir)
            backup_files.append(env_file)

            # 备份Docker配置
            docker_file = await self._backup_docker_config(temp_dir)
            if docker_file:
                backup_files.append(docker_file)

            # 创建配置清单
            manifest_file = await self._create_config_manifest(temp_dir, backup_files)
            backup_files.append(manifest_file)

            return {
                "temp_dir": temp_dir,
                "backup_files": backup_files,
                "backup_type": "config",
                "created_at": datetime.now().isoformat(),
                "params": params
            }

        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e

    async def _backup_config_files(self, temp_dir: str, backup_files: List[str]):
        """备份配置文件"""
        default_config_paths = [
            ".env",
            ".env.example",
            "./backend/config",
            "./deployment/config",
            "./docker-compose.yml",
            "./docker-compose.ha.yml",
            "./nginx/nginx.conf",
            "./redis/redis.conf"
        ]

        paths_to_backup = self.config_paths or default_config_paths

        for path in paths_to_backup:
            if os.path.exists(path):
                if os.path.isfile(path):
                    await self._backup_single_config_file(path, temp_dir, backup_files)
                elif os.path.isdir(path):
                    await self._backup_config_directory(path, temp_dir, backup_files)

    async def _backup_single_config_file(self, source_file: str, temp_dir: str, backup_files: List[str]):
        """备份单个配置文件"""
        try:
            relative_path = os.path.relpath(source_file, ".")
            target_file = os.path.join(temp_dir, relative_path)

            os.makedirs(os.path.dirname(target_file), exist_ok=True)

            async with aiofiles.open(source_file, 'rb') as src:
                content = await src.read()
                async with aiofiles.open(target_file, 'wb') as dst:
                    await dst.write(content)

            backup_files.append(target_file)

        except Exception as e:
            logging.error(f"Failed to backup config file {source_file}: {str(e)}")

    async def _backup_config_directory(self, source_dir: str, temp_dir: str, backup_files: List[str]):
        """备份配置目录"""
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                await self._backup_single_config_file(file_path, temp_dir, backup_files)

    async def _backup_environment_variables(self, temp_dir: str) -> str:
        """备份环境变量"""
        env_file = os.path.join(temp_dir, "environment_variables.json")

        # 收集相关环境变量
        env_vars = {}

        # 备份所有环境变量（过滤敏感信息）
        for key, value in os.environ.items():
            if any(keyword in key.lower() for keyword in [
                'ai_hub', 'database', 'redis', 'secret', 'key', 'token', 'password'
            ]):
                # 隐藏敏感信息
                if any(keyword in key.lower() for keyword in ['secret', 'key', 'token', 'password']):
                    value = "***HIDDEN***"
                env_vars[key] = value

        # 添加配置的环境变量
        for var in self.environment_vars:
            if var in os.environ:
                env_vars[var] = os.environ[var]

        env_data = {
            "backup_type": "environment_variables",
            "created_at": datetime.now().isoformat(),
            "variables": env_vars,
            "total_count": len(env_vars)
        }

        async with aiofiles.open(env_file, 'w') as f:
            await f.write(json.dumps(env_data, indent=2, ensure_ascii=False))

        return env_file

    async def _backup_docker_config(self, temp_dir: str) -> Optional[str]:
        """备份Docker配置"""
        try:
            # 备份Docker Compose配置
            docker_files = []
            for compose_file in ["docker-compose.yml", "docker-compose.ha.yml"]:
                if os.path.exists(compose_file):
                    docker_files.append(compose_file)

            if not docker_files:
                return None

            docker_backup_file = os.path.join(temp_dir, "docker_config.tar")

            with tarfile.open(docker_backup_file, 'w') as tar:
                for docker_file in docker_files:
                    tar.add(docker_file, arcname=os.path.basename(docker_file))

            return docker_backup_file

        except Exception as e:
            logging.error(f"Failed to backup Docker config: {str(e)}")
            return None

    async def _create_config_manifest(self, temp_dir: str, backup_files: List[str]) -> str:
        """创建配置清单"""
        manifest_file = os.path.join(temp_dir, "config_manifest.json")

        manifest = {
            "backup_type": "config",
            "created_at": datetime.now().isoformat(),
            "total_files": len(backup_files),
            "config_files": [
                {
                    "path": os.path.relpath(f, temp_dir),
                    "size": os.path.getsize(f),
                    "type": "config" if "config" in f else "env" if "env" in f else "docker"
                }
                for f in backup_files if os.path.isfile(f)
            ]
        }

        async with aiofiles.open(manifest_file, 'w') as f:
            await f.write(json.dumps(manifest, indent=2, ensure_ascii=False))

        return manifest_file

    async def cleanup(self, backup_data: Dict[str, Any]):
        """清理备份数据"""
        temp_dir = backup_data.get("temp_dir")
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)