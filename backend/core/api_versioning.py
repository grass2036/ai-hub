"""
API版本管理系统
Week 5 Day 2: 高级API功能 - API版本管理
提供完整的API版本控制、兼容性管理和迁移工具
"""

import asyncio
import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
from fastapi import Request, Response, HTTPException, status
from fastapi.routing import APIRoute
from pathlib import Path

logger = logging.getLogger(__name__)

class APIVersion(str, Enum):
    """API版本枚举"""
    V1 = "v1"
    V2 = "v2"
    LATEST = "latest"

class VersionStatus(str, Enum):
    """版本状态枚举"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"
    DEVELOPMENT = "development"

class CompatibilityLevel(str, Enum):
    """兼容性级别"""
    BACKWARD_COMPATIBLE = "backward_compatible"
    FORWARD_COMPATIBLE = "forward_compatible"
    BREAKING_CHANGE = "breaking_change"
    PATCH_UPDATE = "patch_update"

@dataclass
class VersionInfo:
    """版本信息"""
    version: str
    status: VersionStatus
    release_date: datetime
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    compatibility_level: CompatibilityLevel = CompatibilityLevel.BACKWARD_COMPATIBLE
    description: str = ""
    migration_guide: Optional[str] = None
    breaking_changes: List[str] = None

    def __post_init__(self):
        if self.breaking_changes is None:
            self.breaking_changes = []

@dataclass
class APIEndpoint:
    """API端点信息"""
    path: str
    method: str
    version: str
    handler: Callable
    description: str = ""
    deprecated_in_version: Optional[str] = None
    removed_in_version: Optional[str] = None
    alternatives: List[str] = None

    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []

class APIVersionManager:
    """API版本管理器"""

    def __init__(self):
        self.versions: Dict[str, VersionInfo] = {}
        self.endpoints: Dict[str, List[APIEndpoint]] = {}
        self.version_migrations: Dict[Tuple[str, str], Callable] = {}
        self.compatibility_matrix: Dict[Tuple[str, str], bool] = {}
        self.request_logs: List[Dict[str, Any]] = []
        self._initialize_default_versions()

    def _initialize_default_versions(self):
        """初始化默认版本"""
        # v1版本 - 稳定版本
        self.register_version(VersionInfo(
            version=APIVersion.V1,
            status=VersionStatus.ACTIVE,
            release_date=datetime(2024, 1, 1),
            description="稳定版本，提供完整的API功能"
        ))

        # v2版本 - 最新版本
        self.register_version(VersionInfo(
            version=APIVersion.V2,
            status=VersionStatus.ACTIVE,
            release_date=datetime(2024, 10, 1),
            description="增强版本，包含新功能和性能优化"
        ))

    def register_version(self, version_info: VersionInfo):
        """注册新版本"""
        self.versions[version_info.version] = version_info
        logger.info(f"注册API版本: {version_info.version}")

    def register_endpoint(self, endpoint: APIEndpoint):
        """注册API端点"""
        if endpoint.version not in self.endpoints:
            self.endpoints[endpoint.version] = []

        self.endpoints[endpoint.version].append(endpoint)
        logger.info(f"注册API端点: {endpoint.method} {endpoint.path} (版本: {endpoint.version})")

    def set_compatibility(self, from_version: str, to_version: str, compatible: bool = True):
        """设置版本兼容性"""
        self.compatibility_matrix[(from_version, to_version)] = compatible

    def is_compatible(self, from_version: str, to_version: str) -> bool:
        """检查版本兼容性"""
        if from_version == to_version:
            return True

        return self.compatibility_matrix.get((from_version, to_version), False)

    def get_version_info(self, version: str) -> Optional[VersionInfo]:
        """获取版本信息"""
        return self.versions.get(version)

    def get_active_versions(self) -> List[str]:
        """获取活跃版本列表"""
        return [
            version for version, info in self.versions.items()
            if info.status == VersionStatus.ACTIVE
        ]

    def get_deprecated_versions(self) -> List[str]:
        """获取已废弃版本列表"""
        return [
            version for version, info in self.versions.items()
            if info.status == VersionStatus.DEPRECATED
        ]

    def check_version_status(self, version: str) -> Tuple[bool, Optional[str]]:
        """检查版本状态"""
        version_info = self.get_version_info(version)
        if not version_info:
            return False, f"版本 {version} 不存在"

        if version_info.status == VersionStatus.SUNSET:
            return False, f"版本 {version} 已停止支持"

        if version_info.status == VersionStatus.DEPRECATED:
            if version_info.sunset_date and datetime.now() > version_info.sunset_date:
                return False, f"版本 {version} 已停止支持"
            return True, f"版本 {version} 已废弃，请升级到最新版本"

        return True, None

    def get_endpoint_for_version(self, path: str, method: str, version: str) -> Optional[APIEndpoint]:
        """获取指定版本的端点"""
        endpoints = self.endpoints.get(version, [])

        for endpoint in endpoints:
            if endpoint.path == path and endpoint.method == method:
                return endpoint

        return None

    def get_latest_version(self) -> str:
        """获取最新版本"""
        active_versions = self.get_active_versions()
        if not active_versions:
            return APIVersion.V1

        # 返回版本号最大的活跃版本
        return max(active_versions, key=lambda v: self._parse_version_number(v))

    def _parse_version_number(self, version: str) -> int:
        """解析版本号"""
        match = re.match(r'v(\d+)', version)
        if match:
            return int(match.group(1))
        return 0

    def log_request(self, request: Request, version: str, response_status: int):
        """记录API请求日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "version": version,
            "status_code": response_status,
            "user_agent": request.headers.get("user-agent"),
            "ip_address": request.client.host if request.client else None
        }

        self.request_logs.append(log_entry)

        # 保持日志数量在合理范围内
        if len(self.request_logs) > 10000:
            self.request_logs = self.request_logs[-5000:]

    def get_version_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取版本使用统计"""
        cutoff_date = datetime.now() - timedelta(days=days)

        recent_logs = [
            log for log in self.request_logs
            if datetime.fromisoformat(log["timestamp"]) > cutoff_date
        ]

        version_stats = {}
        for log in recent_logs:
            version = log["version"]
            if version not in version_stats:
                version_stats[version] = {
                    "requests": 0,
                    "errors": 0,
                    "last_used": None
                }

            version_stats[version]["requests"] += 1
            if log["status_code"] >= 400:
                version_stats[version]["errors"] += 1

            if (version_stats[version]["last_used"] is None or
                datetime.fromisoformat(log["timestamp"]) >
                datetime.fromisoformat(version_stats[version]["last_used"])):
                version_stats[version]["last_used"] = log["timestamp"]

        return version_stats

class APIVersionMiddleware:
    """API版本中间件"""

    def __init__(self, version_manager: APIVersionManager):
        self.version_manager = version_manager

    async def __call__(self, request: Request, call_next):
        # 提取API版本
        version = self._extract_version_from_request(request)

        if not version:
            # 使用默认版本
            version = self.version_manager.get_latest_version()

        # 检查版本状态
        is_valid, message = self.version_manager.check_version_status(version)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=message
            )

        # 添加版本信息到请求状态
        request.state.api_version = version

        # 处理请求
        response = await call_next(request)

        # 添加版本头
        response.headers["X-API-Version"] = version
        response.headers["X-API-Latest-Version"] = self.version_manager.get_latest_version()

        # 如果使用废弃版本，添加警告头
        version_info = self.version_manager.get_version_info(version)
        if version_info and version_info.status == VersionStatus.DEPRECATED:
            response.headers["X-API-Deprecated"] = "true"
            response.headers["X-API-Sunset-Date"] = (
                version_info.sunset_date.isoformat()
                if version_info.sunset_date else ""
            )

        # 记录请求日志
        self.version_manager.log_request(request, version, response.status_code)

        return response

    def _extract_version_from_request(self, request: Request) -> Optional[str]:
        """从请求中提取API版本"""
        # 1. 从URL路径提取
        path_parts = request.url.path.strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] == "api":
            if path_parts[1].startswith("v"):
                return path_parts[1]

        # 2. 从查询参数提取
        version = request.query_params.get("version")
        if version:
            return version

        # 3. 从请求头提取
        version = request.headers.get("X-API-Version")
        if version:
            return version

        # 4. 从Accept头提取
        accept_header = request.headers.get("Accept", "")
        if "application/vnd.api+json" in accept_header:
            # 解析Accept头中的版本信息
            match = re.search(r'version=(\w+)', accept_header)
            if match:
                return match.group(1)

        return None

def versioned_endpoint(version: str, path: str = None, deprecated_in: str = None, alternatives: List[str] = None):
    """版本化端点装饰器"""
    def decorator(func):
        # 确定路径
        endpoint_path = path or f"/api/{version}/{func.__name__.replace('_', '-')}"

        # 注册端点
        endpoint = APIEndpoint(
            path=endpoint_path,
            method="GET",  # 可以通过其他装饰器覆盖
            version=version,
            handler=func,
            deprecated_in_version=deprecated_in,
            alternatives=alternatives or []
        )

        # 这里需要访问全局版本管理器来注册端点
        # 在实际应用中，可以通过依赖注入或应用状态来获取

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    return decorator

# 全局版本管理器实例
api_version_manager = APIVersionManager()

# 获取版本管理器的依赖注入函数
def get_api_version_manager() -> APIVersionManager:
    """获取API版本管理器实例"""
    return api_version_manager

# 版本检查装饰器
def require_version(min_version: str = None, max_version: str = None):
    """版本要求装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            current_version = getattr(request.state, 'api_version', 'v1')

            if min_version and api_version_manager._parse_version_number(current_version) < api_version_manager._parse_version_number(min_version):
                raise HTTPException(
                    status_code=status.HTTP_426_UPGRADE_REQUIRED,
                    detail=f"需要API版本 >= {min_version}，当前版本: {current_version}"
                )

            if max_version and api_version_manager._parse_version_number(current_version) > api_version_manager._parse_version_number(max_version):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"API版本不兼容，需要版本 <= {max_version}，当前版本: {current_version}"
                )

            return await func(request, *args, **kwargs)

        return wrapper
    return decorator

# 版本迁移工具
class APIMigrationTool:
    """API迁移工具"""

    def __init__(self, version_manager: APIVersionManager):
        self.version_manager = version_manager

    def register_migration(self, from_version: str, to_version: str, migration_func: Callable):
        """注册迁移函数"""
        self.version_manager.version_migrations[(from_version, to_version)] = migration_func
        logger.info(f"注册迁移函数: {from_version} -> {to_version}")

    def migrate_request_data(self, data: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
        """迁移请求数据"""
        if from_version == to_version:
            return data

        migration_key = (from_version, to_version)
        if migration_key in self.version_manager.version_migrations:
            migration_func = self.version_manager.version_migrations[migration_key]
            return migration_func(data)

        # 如果没有直接迁移函数，尝试通过中间版本迁移
        intermediate_versions = self._find_migration_path(from_version, to_version)
        if intermediate_versions:
            current_data = data
            current_version = from_version

            for next_version in intermediate_versions:
                migration_key = (current_version, next_version)
                if migration_key in self.version_manager.version_migrations:
                    migration_func = self.version_manager.version_migrations[migration_key]
                    current_data = migration_func(current_data)
                    current_version = next_version

            return current_data

        raise ValueError(f"无法从版本 {from_version} 迁移到版本 {to_version}")

    def _find_migration_path(self, from_version: str, to_version: str) -> Optional[List[str]]:
        """查找迁移路径"""
        # 简单的路径查找算法
        # 在实际应用中，可以使用更复杂的图算法

        # 直接检查兼容性
        if self.version_manager.is_compatible(from_version, to_version):
            return [to_version]

        # 查找中间版本
        for version in self.version_manager.versions:
            if version != from_version and version != to_version:
                if (self.version_manager.is_compatible(from_version, version) and
                    self.version_manager.is_compatible(version, to_version)):
                    return [version, to_version]

        return None

# 全局迁移工具实例
api_migration_tool = APIMigrationTool(api_version_manager)

# 便捷函数
def get_current_api_version(request: Request) -> str:
    """获取当前请求的API版本"""
    return getattr(request.state, 'api_version', 'v1')

def is_latest_version(request: Request) -> bool:
    """检查是否使用最新版本"""
    current_version = get_current_api_version(request)
    latest_version = api_version_manager.get_latest_version()
    return current_version == latest_version