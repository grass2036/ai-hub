"""
存储后端
Week 6 Day 6: 备份恢复策略实施

定义不同类型的存储后端实现
"""

import asyncio
import os
import shutil
import tarfile
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import aiofiles
import aiofiles.os
import boto3
from botocore.exceptions import ClientError
import aioftp
import hashlib


class StorageBackend(ABC):
    """存储后端基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._initialized = False

    async def initialize(self):
        """初始化存储后端"""
        self._initialized = True

    async def shutdown(self):
        """关闭存储后端"""
        pass

    @abstractmethod
    async def store_backup(
        self,
        backup_id: str,
        backup_data: Dict[str, Any],
        filename: str,
        compression: bool = True
    ) -> str:
        """存储备份数据"""
        pass

    @abstractmethod
    async def retrieve_backup(self, backup_path: str) -> str:
        """检索备份数据"""
        pass

    @abstractmethod
    async def delete_backup(self, backup_path: str) -> bool:
        """删除备份数据"""
        pass

    @abstractmethod
    async def list_backups(self, prefix: str = "") -> List[str]:
        """列出备份文件"""
        pass

    @abstractmethod
    async def backup_exists(self, backup_path: str) -> bool:
        """检查备份是否存在"""
        pass


class LocalStorage(StorageBackend):
    """本地存储后端"""

    def __init__(self, base_path: str):
        super().__init__({})
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """初始化本地存储"""
        await super().initialize()

        # 创建必要的目录
        (self.base_path / "database").mkdir(exist_ok=True)
        (self.base_path / "files").mkdir(exist_ok=True)
        (self.base_path / "config").mkdir(exist_ok=True)
        (self.base_path / "redis").mkdir(exist_ok=True)
        (self.base_path / "logs").mkdir(exist_ok=True)

        logging.info(f"Local storage initialized at: {self.base_path}")

    async def store_backup(
        self,
        backup_id: str,
        backup_data: Dict[str, Any],
        filename: str,
        compression: bool = True
    ) -> str:
        """存储备份数据到本地"""
        try:
            temp_dir = backup_data.get("temp_dir")
            if not temp_dir or not os.path.exists(temp_dir):
                raise ValueError("Invalid backup data or temp directory not found")

            # 确定存储路径
            backup_type = backup_data.get("backup_type", "unknown")
            type_dir = self.base_path / backup_type

            # 创建备份目录
            backup_dir = type_dir / backup_id
            backup_dir.mkdir(parents=True, exist_ok=True)

            # 创建归档文件
            archive_path = backup_dir / filename

            if compression:
                # 创建压缩归档
                await self._create_compressed_archive(temp_dir, archive_path)
            else:
                # 创建普通归档
                await self._create_archive(temp_dir, archive_path)

            logging.info(f"Backup stored locally: {archive_path}")
            return str(archive_path)

        except Exception as e:
            logging.error(f"Failed to store backup locally: {str(e)}")
            raise e

    async def _create_compressed_archive(self, source_dir: str, archive_path: Path):
        """创建压缩归档"""
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(source_dir, arcname='')

    async def _create_archive(self, source_dir: str, archive_path: Path):
        """创建普通归档"""
        with tarfile.open(archive_path, 'w') as tar:
            tar.add(source_dir, arcname='')

    async def retrieve_backup(self, backup_path: str) -> str:
        """检索本地备份数据"""
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # 创建临时解压目录
        temp_dir = tempfile.mkdtemp(prefix="backup_restore_")

        try:
            # 解压归档文件
            if backup_path.endswith('.gz'):
                with tarfile.open(backup_path, 'r:gz') as tar:
                    tar.extractall(temp_dir)
            else:
                with tarfile.open(backup_path, 'r') as tar:
                    tar.extractall(temp_dir)

            return temp_dir

        except Exception as e:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e

    async def delete_backup(self, backup_path: str) -> bool:
        """删除本地备份"""
        try:
            if os.path.exists(backup_path):
                await aiofiles.os.remove(backup_path)
                logging.info(f"Local backup deleted: {backup_path}")
                return True
            return False

        except Exception as e:
            logging.error(f"Failed to delete local backup {backup_path}: {str(e)}")
            return False

    async def list_backups(self, prefix: str = "") -> List[str]:
        """列出本地备份"""
        backups = []

        try:
            # 递归搜索备份文件
            for backup_type in ["database", "files", "config", "redis", "logs"]:
                type_dir = self.base_path / backup_type
                if type_dir.exists():
                    for backup_dir in type_dir.iterdir():
                        if backup_dir.is_dir():
                            for backup_file in backup_dir.glob("*.tar*"):
                                backup_path = str(backup_file)
                                if prefix and not backup_path.startswith(prefix):
                                    continue
                                backups.append(backup_path)

        except Exception as e:
            logging.error(f"Failed to list local backups: {str(e)}")

        return sorted(backups)

    async def backup_exists(self, backup_path: str) -> bool:
        """检查本地备份是否存在"""
        return os.path.exists(backup_path)

    async def get_storage_usage(self) -> Dict[str, Any]:
        """获取存储使用情况"""
        total_size = 0
        backup_counts = {}

        try:
            for backup_type in ["database", "files", "config", "redis", "logs"]:
                type_dir = self.base_path / backup_type
                if type_dir.exists():
                    type_size = 0
                    count = 0

                    for backup_file in type_dir.rglob("*.tar*"):
                        if backup_file.is_file():
                            type_size += backup_file.stat().st_size
                            count += 1

                    total_size += type_size
                    backup_counts[backup_type] = {
                        "count": count,
                        "size_bytes": type_size,
                        "size_human": self._format_bytes(type_size)
                    }

        except Exception as e:
            logging.error(f"Failed to get storage usage: {str(e)}")

        return {
            "total_size_bytes": total_size,
            "total_size_human": self._format_bytes(total_size),
            "backup_types": backup_counts,
            "storage_path": str(self.base_path)
        }

    def _format_bytes(self, bytes_count: int) -> str:
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.2f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.2f} PB"


class S3Storage(StorageBackend):
    """S3存储后端"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bucket_name = config.get("bucket_name")
        self.prefix = config.get("prefix", "backups/")
        self.access_key = config.get("access_key")
        self.secret_key = config.get("secret_key")
        self.region = config.get("region", "us-east-1")
        self.endpoint_url = config.get("endpoint_url")

        self.s3_client = None

    async def initialize(self):
        """初始化S3客户端"""
        await super().initialize()

        try:
            s3_config = {
                "aws_access_key_id": self.access_key,
                "aws_secret_access_key": self.secret_key,
                "region_name": self.region
            }

            if self.endpoint_url:
                s3_config["endpoint_url"] = self.endpoint_url

            self.s3_client = boto3.client("s3", **s3_config)

            # 检查bucket是否存在
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
            except ClientError:
                # 创建bucket
                self.s3_client.create_bucket(Bucket=self.bucket_name)

            logging.info(f"S3 storage initialized for bucket: {self.bucket_name}")

        except Exception as e:
            logging.error(f"Failed to initialize S3 storage: {str(e)}")
            raise e

    async def store_backup(
        self,
        backup_id: str,
        backup_data: Dict[str, Any],
        filename: str,
        compression: bool = True
    ) -> str:
        """存储备份数据到S3"""
        try:
            temp_dir = backup_data.get("temp_dir")
            if not temp_dir or not os.path.exists(temp_dir):
                raise ValueError("Invalid backup data or temp directory not found")

            # 创建临时归档文件
            temp_archive = tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False)
            temp_archive.close()

            try:
                # 创建归档
                if compression:
                    with tarfile.open(temp_archive.name, 'w:gz') as tar:
                        tar.add(temp_dir, arcname='')
                else:
                    with tarfile.open(temp_archive.name, 'w') as tar:
                        tar.add(temp_dir, arcname='')

                # 上传到S3
                backup_type = backup_data.get("backup_type", "unknown")
                s3_key = f"{self.prefix}{backup_type}/{backup_id}/{filename}"

                self.s3_client.upload_file(
                    temp_archive.name,
                    self.bucket_name,
                    s3_key
                )

                s3_path = f"s3://{self.bucket_name}/{s3_key}"
                logging.info(f"Backup stored to S3: {s3_path}")
                return s3_path

            finally:
                # 清理临时文件
                os.unlink(temp_archive.name)

        except Exception as e:
            logging.error(f"Failed to store backup to S3: {str(e)}")
            raise e

    async def retrieve_backup(self, backup_path: str) -> str:
        """从S3检索备份数据"""
        try:
            # 解析S3路径
            if backup_path.startswith("s3://"):
                path_parts = backup_path.replace("s3://", "").split("/", 1)
                bucket = path_parts[0]
                key = path_parts[1]
            else:
                bucket = self.bucket_name
                key = backup_path

            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.close()

            try:
                # 下载文件
                self.s3_client.download_file(bucket, key, temp_file.name)

                # 解压到临时目录
                temp_dir = tempfile.mkdtemp(prefix="backup_restore_")
                with tarfile.open(temp_file.name, 'r:gz') as tar:
                    tar.extractall(temp_dir)

                return temp_dir

            finally:
                os.unlink(temp_file.name)

        except Exception as e:
            logging.error(f"Failed to retrieve backup from S3: {str(e)}")
            raise e

    async def delete_backup(self, backup_path: str) -> bool:
        """从S3删除备份"""
        try:
            # 解析S3路径
            if backup_path.startswith("s3://"):
                path_parts = backup_path.replace("s3://", "").split("/", 1)
                bucket = path_parts[0]
                key = path_parts[1]
            else:
                bucket = self.bucket_name
                key = backup_path

            self.s3_client.delete_object(Bucket=bucket, Key=key)
            logging.info(f"S3 backup deleted: {backup_path}")
            return True

        except Exception as e:
            logging.error(f"Failed to delete S3 backup {backup_path}: {str(e)}")
            return False

    async def list_backups(self, prefix: str = "") -> List[str]:
        """列出S3备份"""
        backups = []

        try:
            list_prefix = f"{self.prefix}{prefix}" if prefix else self.prefix

            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=list_prefix)

            for page in pages:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        s3_path = f"s3://{self.bucket_name}/{obj['Key']}"
                        backups.append(s3_path)

        except Exception as e:
            logging.error(f"Failed to list S3 backups: {str(e)}")

        return sorted(backups)

    async def backup_exists(self, backup_path: str) -> bool:
        """检查S3备份是否存在"""
        try:
            # 解析S3路径
            if backup_path.startswith("s3://"):
                path_parts = backup_path.replace("s3://", "").split("/", 1)
                bucket = path_parts[0]
                key = path_parts[1]
            else:
                bucket = self.bucket_name
                key = backup_path

            self.s3_client.head_object(Bucket=bucket, Key=key)
            return True

        except ClientError:
            return False

    async def get_storage_usage(self) -> Dict[str, Any]:
        """获取S3存储使用情况"""
        try:
            total_size = 0
            backup_counts = {}

            # 按类型统计
            for backup_type in ["database", "files", "config", "redis", "logs"]:
                type_prefix = f"{self.prefix}{backup_type}/"
                type_size = 0
                count = 0

                paginator = self.s3_client.get_paginator("list_objects_v2")
                pages = paginator.paginate(Bucket=self.bucket_name, Prefix=type_prefix)

                for page in pages:
                    if "Contents" in page:
                        for obj in page["Contents"]:
                            type_size += obj["Size"]
                            count += 1

                total_size += type_size
                backup_counts[backup_type] = {
                    "count": count,
                    "size_bytes": type_size,
                    "size_human": self._format_bytes(type_size)
                }

            return {
                "total_size_bytes": total_size,
                "total_size_human": self._format_bytes(total_size),
                "backup_types": backup_counts,
                "bucket": self.bucket_name,
                "prefix": self.prefix
            }

        except Exception as e:
            logging.error(f"Failed to get S3 storage usage: {str(e)}")
            return {}

    def _format_bytes(self, bytes_count: int) -> str:
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.2f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.2f} PB"


class FTPStorage(StorageBackend):
    """FTP存储后端"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = config.get("host")
        self.port = config.get("port", 21)
        self.username = config.get("username")
        self.password = config.get("password")
        self.base_path = config.get("base_path", "/backups")
        self.passive = config.get("passive", True)

        self.ftp_client = None

    async def initialize(self):
        """初始化FTP连接"""
        await super().initialize()

        try:
            self.ftp_client = aioftp.Client()
            await self.ftp_client.connect(self.host, self.port)
            await self.ftp_client.login(self.username, self.password)

            # 创建基础目录
            try:
                await self.ftp_client.make_directory(self.base_path)
            except aioftp.StatusCodeError:
                # 目录可能已存在
                pass

            logging.info(f"FTP storage initialized: {self.host}:{self.port}")

        except Exception as e:
            logging.error(f"Failed to initialize FTP storage: {str(e)}")
            raise e

    async def store_backup(
        self,
        backup_id: str,
        backup_data: Dict[str, Any],
        filename: str,
        compression: bool = True
    ) -> str:
        """存储备份数据到FTP"""
        try:
            temp_dir = backup_data.get("temp_dir")
            if not temp_dir or not os.path.exists(temp_dir):
                raise ValueError("Invalid backup data or temp directory not found")

            # 创建临时归档文件
            temp_archive = tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False)
            temp_archive.close()

            try:
                # 创建归档
                if compression:
                    with tarfile.open(temp_archive.name, 'w:gz') as tar:
                        tar.add(temp_dir, arcname='')
                else:
                    with tarfile.open(temp_archive.name, 'w') as tar:
                        tar.add(temp_dir, arcname='')

                # 确定FTP路径
                backup_type = backup_data.get("backup_type", "unknown")
                ftp_dir = f"{self.base_path}/{backup_type}/{backup_id}"
                ftp_path = f"{ftp_dir}/{filename}"

                # 创建目录
                try:
                    await self.ftp_client.make_directory(ftp_dir)
                except aioftp.StatusCodeError:
                    pass

                # 上传文件
                await self.ftp_client.upload(temp_archive.name, ftp_path)

                logging.info(f"Backup stored to FTP: {ftp_path}")
                return ftp_path

            finally:
                os.unlink(temp_archive.name)

        except Exception as e:
            logging.error(f"Failed to store backup to FTP: {str(e)}")
            raise e

    async def retrieve_backup(self, backup_path: str) -> str:
        """从FTP检索备份数据"""
        try:
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.close()

            try:
                # 下载文件
                await self.ftp_client.download(backup_path, temp_file.name)

                # 解压到临时目录
                temp_dir = tempfile.mkdtemp(prefix="backup_restore_")
                with tarfile.open(temp_file.name, 'r:gz') as tar:
                    tar.extractall(temp_dir)

                return temp_dir

            finally:
                os.unlink(temp_file.name)

        except Exception as e:
            logging.error(f"Failed to retrieve backup from FTP: {str(e)}")
            raise e

    async def delete_backup(self, backup_path: str) -> bool:
        """从FTP删除备份"""
        try:
            await self.ftp_client.remove(backup_path)
            logging.info(f"FTP backup deleted: {backup_path}")
            return True

        except Exception as e:
            logging.error(f"Failed to delete FTP backup {backup_path}: {str(e)}")
            return False

    async def list_backups(self, prefix: str = "") -> List[str]:
        """列出FTP备份"""
        backups = []

        try:
            search_path = f"{self.base_path}/{prefix}" if prefix else self.base_path

            async for path, info in self.ftp_client.list(search_path, recursive=True):
                if path.endswith(('.tar', '.tar.gz')):
                    backups.append(path)

        except Exception as e:
            logging.error(f"Failed to list FTP backups: {str(e)}")

        return sorted(backups)

    async def backup_exists(self, backup_path: str) -> bool:
        """检查FTP备份是否存在"""
        try:
            await self.ftp_client.stat(backup_path)
            return True

        except aioftp.StatusCodeError:
            return False

    async def shutdown(self):
        """关闭FTP连接"""
        if self.ftp_client:
            await self.ftp_client.quit()
        await super().shutdown()


# 存储后端工厂
class StorageFactory:
    """存储后端工厂"""

    @staticmethod
    def create_storage(storage_type: str, config: Dict[str, Any]) -> StorageBackend:
        """创建存储后端"""
        if storage_type.lower() == "local":
            base_path = config.get("base_path", "./backups")
            return LocalStorage(base_path)

        elif storage_type.lower() == "s3":
            return S3Storage(config)

        elif storage_type.lower() == "ftp":
            return FTPStorage(config)

        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")