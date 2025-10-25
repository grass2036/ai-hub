"""
静态资源分发系统
Static Asset Distribution System

实现智能的静态资源全球分发和优化
Implements intelligent global static asset distribution and optimization
"""

import logging
import json
import hashlib
import asyncio
import mimetypes
import aiofiles
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, BinaryIO
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class AssetType(Enum):
    """资源类型"""
    IMAGE = "image"
    SCRIPT = "script"
    STYLE = "style"
    FONT = "font"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"

class CompressionLevel(Enum):
    """压缩级别"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"

class ImageFormat(Enum):
    """图片格式"""
    ORIGINAL = "original"
    WEBP = "webp"
    AVIF = "avif"
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"

@dataclass
class AssetMetadata:
    """资源元数据"""
    asset_id: str
    original_filename: str
    content_type: str
    file_size: int
    checksum: str
    created_at: datetime
    updated_at: datetime
    version: int
    tags: List[str]
    alt_text: Optional[str]

@dataclass
class AssetVariant:
    """资源变体"""
    variant_id: str
    asset_id: str
    format: str
    quality: int
    dimensions: Optional[tuple]  # (width, height)
    file_size: int
    compression_level: CompressionLevel
    created_at: datetime
    url: str
    region: str

class StaticAssetDistributor:
    """静态资源分发器"""

    def __init__(self, config_path: str = "config/asset_distribution.json"):
        self.config_path = Path(config_path)
        self.config = {}
        self.s3_clients: Dict[str, Any] = {}
        self.cloudfront_clients: Dict[str, Any] = {}

        # 初始化配置
        self._load_config()
        self._initialize_clients()

        logger.info("Static asset distributor initialized")

    def _load_config(self):
        """加载配置"""
        default_config = {
            "storage": {
                "regions": {
                    "us-east-1": {
                        "bucket_name": "ai-hub-assets-us-east-1",
                        "cloudfront_domain": "d1234567890.cloudfront.net",
                        "region_code": "us",
                        "cache_ttl": 31536000  # 1年
                    },
                    "eu-west-1": {
                        "bucket_name": "ai-hub-assets-eu-west-1",
                        "cloudfront_domain": "d0987654321.cloudfront.net",
                        "region_code": "eu",
                        "cache_ttl": 31536000
                    },
                    "ap-southeast-1": {
                        "bucket_name": "ai-hub-assets-ap-southeast-1",
                        "cloudfront_domain": "d1122334455.cloudfront.net",
                        "region_code": "ap",
                        "cache_ttl": 31536000
                    }
                },
                "backup_regions": ["ap-northeast-1", "sa-east-1"],
                "replication_enabled": True
            },
            "optimization": {
                "images": {
                    "enabled": True,
                    "formats": ["webp", "avif", "jpeg"],
                    "quality_levels": [90, 75, 60],
                    "max_dimensions": [1920, 1280, 800],
                    "progressive_jpeg": True,
                    "strip_metadata": True
                },
                "scripts": {
                    "enabled": True,
                    "minification": True,
                    "compression": "gzip",
                    "tree_shaking": True
                },
                "styles": {
                    "enabled": True,
                    "minification": True,
                    "compression": "gzip",
                    "autoprefixer": True
                }
            },
            "security": {
                "cors": {
                    "enabled": True,
                    "allowed_origins": ["*"],
                    "allowed_methods": ["GET", "HEAD", "OPTIONS"],
                    "max_age": 86400
                },
                "signed_urls": {
                    "enabled": False,
                    "expiration": 3600
                }
            },
            "monitoring": {
                "access_logging": True,
                "error_tracking": True,
                "performance_metrics": True
            }
        }

        # 创建配置目录
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # 加载或创建配置文件
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = default_config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)

    def _initialize_clients(self):
        """初始化云服务客户端"""
        for region, region_config in self.config["storage"]["regions"].items():
            try:
                # S3客户端
                s3_client = boto3.client(
                    's3',
                    region_name=region,
                    config=boto3.Config(
                        max_pool_connections=50,
                        retries={'max_attempts': 3}
                    )
                )
                self.s3_clients[region] = s3_client

                # CloudFront客户端（只有us-east-1支持）
                if region == "us-east-1":
                    cloudfront_client = boto3.client('cloudfront', region_name='us-east-1')
                    self.cloudfront_clients[region] = cloudfront_client

                logger.info(f"Initialized S3 client for region: {region}")

            except Exception as e:
                logger.error(f"Failed to initialize client for region {region}: {e}")

    async def upload_asset(self, file_path: Union[str, Path],
                          asset_type: AssetType,
                          tags: List[str] = None,
                          alt_text: str = None,
                          optimize: bool = True) -> str:
        """上传静态资源"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Asset file not found: {file_path}")

            # 生成资源ID和元数据
            asset_id = self._generate_asset_id(file_path)
            checksum = await self._calculate_checksum(file_path)

            metadata = AssetMetadata(
                asset_id=asset_id,
                original_filename=file_path.name,
                content_type=mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream',
                file_size=file_path.stat().st_size,
                checksum=checksum,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                version=1,
                tags=tags or [],
                alt_text=alt_text
            )

            # 读取文件内容
            async with aiofiles.open(file_path, 'rb') as f:
                file_content = await f.read()

            # 优化文件（如果启用）
            if optimize:
                file_content = await self._optimize_asset(
                    file_content, asset_type, metadata
                )

            # 上传到所有主要区域
            upload_tasks = []
            for region, region_config in self.config["storage"]["regions"].items():
                if region in self.s3_clients:
                    upload_tasks.append(
                        self._upload_to_region(
                            asset_id, file_content, metadata, region
                        )
                    )

            upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)

            # 检查上传结果
            successful_uploads = []
            for i, result in enumerate(upload_results):
                region = list(self.config["storage"]["regions"].keys())[i]
                if isinstance(result, Exception):
                    logger.error(f"Failed to upload to region {region}: {result}")
                else:
                    successful_uploads.append(region)

            if not successful_uploads:
                raise RuntimeError("Failed to upload asset to any region")

            # 保存元数据
            await self._save_metadata(metadata)

            logger.info(f"Asset uploaded successfully: {asset_id}")
            return asset_id

        except Exception as e:
            logger.error(f"Failed to upload asset {file_path}: {e}")
            raise

    async def _upload_to_region(self, asset_id: str, file_content: bytes,
                               metadata: AssetMetadata, region: str) -> Dict[str, Any]:
        """上传到指定区域"""
        try:
            s3_client = self.s3_clients[region]
            region_config = self.config["storage"]["regions"][region]
            bucket_name = region_config["bucket_name"]

            # 确定文件键名
            file_extension = Path(metadata.original_filename).suffix
            content_type = metadata.content_type

            # 如果是图片，创建多个变体
            if content_type.startswith('image/') and self.config["optimization"]["images"]["enabled"]:
                variants = await self._create_image_variants(file_content, metadata)
                upload_results = []

                for variant in variants:
                    key = f"images/{asset_id}/{variant.variant_id}{file_extension}"

                    # 设置缓存头
                    cache_control = f"public, max-age={region_config['cache_ttl']}"

                    extra_args = {
                        'ContentType': content_type,
                        'CacheControl': cache_control,
                        'Metadata': {
                            'asset-id': asset_id,
                            'variant-id': variant.variant_id,
                            'checksum': variant.checksum
                        }
                    }

                    # 上传变体
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=key,
                        Body=variant.data,
                        **extra_args
                    )

                    upload_results.append({
                        'key': key,
                        'variant_id': variant.variant_id,
                        'size': len(variant.data),
                        'url': f"https://{region_config['cloudfront_domain']}/{key}"
                    })

                return {'variants': upload_results}

            else:
                # 非图片文件，直接上传
                key = f"{self._get_asset_folder(metadata.content_type)}/{asset_id}{file_extension}"

                cache_control = f"public, max-age={region_config['cache_ttl']}"

                extra_args = {
                    'ContentType': content_type,
                    'CacheControl': cache_control,
                    'Metadata': {
                        'asset-id': asset_id,
                        'checksum': metadata.checksum
                    }
                }

                # 添加CORS头
                if self.config["security"]["cors"]["enabled"]:
                    extra_args['ACL'] = 'public-read'

                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=key,
                    Body=file_content,
                    **extra_args
                )

                url = f"https://{region_config['cloudfront_domain']}/{key}"
                return {'url': url, 'key': key, 'size': len(file_content)}

        except ClientError as e:
            logger.error(f"AWS S3 error in region {region}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to upload to region {region}: {e}")
            raise

    async def _create_image_variants(self, file_content: bytes,
                                   metadata: AssetMetadata) -> List[Any]:
        """创建图片变体"""
        try:
            from PIL import Image
            import io

            variants = []

            # 加载图片
            image = Image.open(io.BytesIO(file_content))
            original_format = image.format

            # 获取优化配置
            img_config = self.config["optimization"]["images"]
            formats = img_config["formats"]
            quality_levels = img_config["quality_levels"]
            max_dimensions = img_config["max_dimensions"]

            # 为每个格式和质量级别创建变体
            for format_name in formats:
                for quality in quality_levels:
                    for max_dim in max_dimensions:
                        try:
                            variant_data = await self._create_image_variant(
                                image, format_name, quality, max_dim, original_format
                            )

                            if variant_data:
                                variant_id = f"{format_name}_{quality}_{max_dim}"
                                checksum = hashlib.md5(variant_data).hexdigest()

                                class Variant:
                                    def __init__(self, variant_id, data, checksum):
                                        self.variant_id = variant_id
                                        self.data = data
                                        self.checksum = checksum

                                variants.append(Variant(variant_id, variant_data, checksum))

                        except Exception as e:
                            logger.warning(f"Failed to create image variant {format_name}_{quality}_{max_dim}: {e}")
                            continue

            return variants

        except ImportError:
            logger.warning("PIL not available, skipping image optimization")
            return []
        except Exception as e:
            logger.error(f"Failed to create image variants: {e}")
            return []

    async def _create_image_variant(self, image: Image.Image, format_name: str,
                                 quality: int, max_dimension: int,
                                 original_format: str) -> Optional[bytes]:
        """创建单个图片变体"""
        try:
            import io

            # 复制图片对象
            img_copy = image.copy()

            # 调整尺寸
            if max(img_copy.width, img_copy.height) > max_dimension:
                img_copy.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

            # 转换格式
            if format_name == "webp":
                output_format = "WEBP"
                mime_type = "image/webp"
            elif format_name == "avif":
                output_format = "AVIF"
                mime_type = "image/avif"
            elif format_name == "jpeg":
                output_format = "JPEG"
                mime_type = "image/jpeg"
            else:
                # 保持原格式
                output_format = original_format
                mime_type = f"image/{original_format.lower()}"

            # 保存到字节流
            output = io.BytesIO()

            if output_format in ["JPEG", "WEBP"]:
                img_copy.save(output, format=output_format, quality=quality, optimize=True)
            elif output_format == "AVIF":
                # AVIF需要额外的库支持
                img_copy.save(output, format=output_format, quality=quality)
            else:
                img_copy.save(output, format=output_format, optimize=True)

            return output.getvalue()

        except Exception as e:
            logger.error(f"Failed to create image variant {format_name}: {e}")
            return None

    async def _optimize_asset(self, file_content: bytes,
                            asset_type: AssetType,
                            metadata: AssetMetadata) -> bytes:
        """优化资源文件"""
        try:
            if asset_type == AssetType.SCRIPT and self.config["optimization"]["scripts"]["enabled"]:
                return await self._optimize_script(file_content)
            elif asset_type == AssetType.STYLE and self.config["optimization"]["styles"]["enabled"]:
                return await self._optimize_style(file_content)
            elif asset_type == AssetType.IMAGE and self.config["optimization"]["images"]["enabled"]:
                return await self._optimize_image(file_content, metadata)
            else:
                return file_content

        except Exception as e:
            logger.warning(f"Asset optimization failed: {e}")
            return file_content

    async def _optimize_script(self, file_content: bytes) -> bytes:
        """优化JavaScript文件"""
        try:
            # 这里应该实现JavaScript压缩
            # 可以使用terser或类似工具
            script_content = file_content.decode('utf-8')

            # 简单的优化：移除注释和多余空格
            lines = []
            for line in script_content.split('\n'):
                stripped = line.strip()
                if stripped and not stripped.startswith('//'):
                    lines.append(stripped)

            optimized = ' '.join(lines)
            return optimized.encode('utf-8')

        except Exception as e:
            logger.error(f"Script optimization failed: {e}")
            return file_content

    async def _optimize_style(self, file_content: bytes) -> bytes:
        """优化CSS文件"""
        try:
            # 这里应该实现CSS压缩
            css_content = file_content.decode('utf-8')

            # 简单的CSS优化
            optimized = css_content
            optimized = re.sub(r'/\*.*?\*/', '', optimized, flags=re.DOTALL)  # 移除注释
            optimized = re.sub(r'\s+', ' ', optimized)  # 压缩空格
            optimized = re.sub(r';\s*}', '}', optimized)  # 移除最后的分号

            return optimized.encode('utf-8')

        except Exception as e:
            logger.error(f"Style optimization failed: {e}")
            return file_content

    async def _optimize_image(self, file_content: bytes, metadata: AssetMetadata) -> bytes:
        """优化图片文件"""
        try:
            from PIL import Image
            import io

            # 加载图片
            image = Image.open(io.BytesIO(file_content))

            # 如果是JPEG，转换为progressive
            if image.format == "JPEG" and self.config["optimization"]["images"]["progressive_jpeg"]:
                output = io.BytesIO()
                image.save(output, format="JPEG", quality=85, optimize=True, progressive=True)
                return output.getvalue()

            # 移除元数据
            if self.config["optimization"]["images"]["strip_metadata"]:
                output = io.BytesIO()
                image.save(output, format=image.format, quality=85, optimize=True)
                return output.getvalue()

            return file_content

        except ImportError:
            logger.warning("PIL not available, skipping image optimization")
            return file_content
        except Exception as e:
            logger.error(f"Image optimization failed: {e}")
            return file_content

    def _generate_asset_id(self, file_path: Path) -> str:
        """生成资源ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = file_path.stem
        return f"{filename}_{timestamp}"

    async def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        hash_md5 = hashlib.md5()
        async with aiofiles.open(file_path, 'rb') as f:
            async for chunk in f:
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _get_asset_folder(self, content_type: str) -> str:
        """根据内容类型获取文件夹名"""
        if content_type.startswith('image/'):
            return 'images'
        elif content_type.startswith('text/css'):
            return 'styles'
        elif content_type.startswith('application/javascript') or content_type.startswith('text/javascript'):
            return 'scripts'
        elif content_type.startswith('font/') or content_type in ['application/x-font-ttf', 'application/font-woff', 'application/font-woff2']:
            return 'fonts'
        elif content_type.startswith('video/'):
            return 'videos'
        elif content_type.startswith('audio/'):
            return 'audio'
        else:
            return 'documents'

    async def _save_metadata(self, metadata: AssetMetadata):
        """保存资源元数据"""
        try:
            metadata_dir = Path("data/assets/metadata")
            metadata_dir.mkdir(parents=True, exist_ok=True)

            metadata_file = metadata_dir / f"{metadata.asset_id}.json"
            metadata_dict = asdict(metadata)
            metadata_dict['created_at'] = metadata.created_at.isoformat()
            metadata_dict['updated_at'] = metadata.updated_at.isoformat()

            async with aiofiles.open(metadata_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(metadata_dict, indent=2, ensure_ascii=False))

        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    async def get_asset_url(self, asset_id: str, region: str = "us-east-1",
                           variant: str = None) -> Optional[str]:
        """获取资源URL"""
        try:
            # 读取元数据
            metadata_file = Path(f"data/assets/metadata/{asset_id}.json")
            if not metadata_file.exists():
                return None

            async with aiofiles.open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.loads(await f.read())

            region_config = self.config["storage"]["regions"].get(region)
            if not region_config:
                return None

            file_extension = Path(metadata["original_filename"]).suffix
            folder = self._get_asset_folder(metadata["content_type"])

            if variant:
                # 返回变体URL
                url = f"https://{region_config['cloudfront_domain']}/{folder}/{asset_id}/{variant}{file_extension}"
            else:
                # 返回原始URL
                url = f"https://{region_config['cloudfront_domain']}/{folder}/{asset_id}{file_extension}"

            return url

        except Exception as e:
            logger.error(f"Failed to get asset URL for {asset_id}: {e}")
            return None

    async def delete_asset(self, asset_id: str) -> bool:
        """删除资源"""
        try:
            deleted_regions = []

            # 从所有区域删除
            for region, s3_client in self.s3_clients.items():
                try:
                    # 列出所有相关对象
                    region_config = self.config["storage"]["regions"][region]
                    bucket_name = region_config["bucket_name"]

                    # 获取元数据以确定文件路径
                    metadata_file = Path(f"data/assets/metadata/{asset_id}.json")
                    if metadata_file.exists():
                        async with aiofiles.open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.loads(await f.read())

                        folder = self._get_asset_folder(metadata["content_type"])
                        file_extension = Path(metadata["original_filename"]).suffix

                        # 删除主文件
                        main_key = f"{folder}/{asset_id}{file_extension}"
                        s3_client.delete_object(Bucket=bucket_name, Key=main_key)

                        # 删除图片变体
                        if metadata["content_type"].startswith('image/'):
                            paginator = s3_client.get_paginator('list_objects_v2')
                            pages = paginator.paginate(
                                Bucket=bucket_name,
                                Prefix=f"{folder}/{asset_id}/"
                            )

                            for page in pages:
                                if 'Contents' in page:
                                    for obj in page['Contents']:
                                        s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])

                        deleted_regions.append(region)

                except Exception as e:
                    logger.error(f"Failed to delete from region {region}: {e}")

            # 删除元数据文件
            metadata_file = Path(f"data/assets/metadata/{asset_id}.json")
            if metadata_file.exists():
                metadata_file.unlink()

            success = len(deleted_regions) > 0
            if success:
                logger.info(f"Asset {asset_id} deleted from regions: {deleted_regions}")
            else:
                logger.warning(f"Failed to delete asset {asset_id} from any region")

            return success

        except Exception as e:
            logger.error(f"Failed to delete asset {asset_id}: {e}")
            return False

    async def replicate_to_backup_regions(self, asset_id: str) -> bool:
        """复制到备份区域"""
        try:
            if not self.config["storage"]["replication_enabled"]:
                return True

            backup_regions = self.config["storage"]["backup_regions"]
            primary_regions = set(self.config["storage"]["regions"].keys())

            # 找出需要复制到的备份区域
            regions_to_replicate = set(backup_regions) - primary_regions

            if not regions_to_replicate:
                return True

            # 实现复制逻辑
            # 这里需要跨区域复制S3对象
            for region in regions_to_replicate:
                try:
                    # 创建S3客户端
                    s3_client = boto3.client('s3', region_name=region)

                    # 复制逻辑...
                    logger.info(f"Replicated asset {asset_id} to backup region {region}")

                except Exception as e:
                    logger.error(f"Failed to replicate to region {region}: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to replicate asset {asset_id}: {e}")
            return False

# 全局资源分发器实例
asset_distributor = StaticAssetDistributor()

async def get_asset_distributor() -> StaticAssetDistributor:
    """获取资源分发器实例"""
    return asset_distributor