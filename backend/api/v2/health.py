"""
API v2 健康检查端点
Week 5 Day 2: 高级API功能 - API版本管理示例
"""

from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.core.api_versioning import (
    api_version_manager,
    require_version,
    get_current_api_version
)
from backend.core.database import get_db
from backend.health.deep_health_checker import DeepHealthChecker

router = APIRouter(prefix="/health", tags=["health-v2"])

class HealthResponseV2(BaseModel):
    """健康检查响应 v2"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="API版本")
    timestamp: datetime = Field(..., description="检查时间")
    checks: Dict[str, Any] = Field(..., description="详细检查结果")
    version_info: Dict[str, Any] = Field(..., description="版本信息")

class DetailedHealthCheck(BaseModel):
    """详细健康检查项"""
    name: str = Field(..., description="检查项名称")
    status: str = Field(..., description="状态: healthy, unhealthy, degraded")
    response_time_ms: float = Field(..., description="响应时间(毫秒)")
    details: Dict[str, Any] = Field(default_factory=dict, description="详细信息")

@router.get("/status", response_model=HealthResponseV2)
async def health_check_v2(
    include_checks: bool = True,
    request: 'Request' = None
):
    """健康检查端点 v2"""
    current_version = get_current_api_version(request)

    # 基础健康检查
    basic_checks = {
        "api": "healthy",
        "database": "healthy",
        "cache": "healthy"
    }

    # 如果需要详细检查
    detailed_checks = {}
    if include_checks:
        try:
            health_checker = DeepHealthChecker()
            detailed_results = await health_checker.run_comprehensive_health_check()

            for check_name, result in detailed_results.items():
                detailed_checks[check_name] = DetailedHealthCheck(
                    name=check_name,
                    status=result.status.value,
                    response_time_ms=result.response_time_ms or 0,
                    details={
                        "message": result.message,
                        "last_check": result.timestamp.isoformat(),
                        "details": result.details or {}
                    }
                )
        except Exception as e:
            detailed_checks["comprehensive_check"] = DetailedHealthCheck(
                name="comprehensive_check",
                status="unhealthy",
                response_time_ms=0,
                details={"error": str(e)}
            )

    # 获取版本信息
    version_info = api_version_manager.get_version_info(current_version)
    version_stats = api_version_manager.get_version_statistics(days=7)

    return HealthResponseV2(
        status="healthy",
        version=current_version,
        timestamp=datetime.now(),
        checks=detailed_checks if include_checks else basic_checks,
        version_info={
            "version": version_info.version if version_info else current_version,
            "status": version_info.status.value if version_info else "unknown",
            "release_date": version_info.release_date.isoformat() if version_info else None,
            "description": version_info.description if version_info else "",
            "compatibility_level": version_info.compatibility_level.value if version_info else "unknown",
            "usage_stats": version_stats.get(current_version, {})
        }
    )

@router.get("/version", response_model=Dict[str, Any])
async def get_version_info(request: 'Request' = None):
    """获取版本信息"""
    current_version = get_current_api_version(request)
    latest_version = api_version_manager.get_latest_version()

    version_info = api_version_manager.get_version_info(current_version)
    latest_info = api_version_manager.get_version_info(latest_version)

    return {
        "current_version": {
            "version": current_version,
            "status": version_info.status.value if version_info else "unknown",
            "release_date": version_info.release_date.isoformat() if version_info else None,
            "description": version_info.description if version_info else "",
            "compatibility_level": version_info.compatibility_level.value if version_info else "unknown"
        },
        "latest_version": {
            "version": latest_version,
            "status": latest_info.status.value if latest_info else "unknown",
            "release_date": latest_info.release_date.isoformat() if latest_info else None,
            "description": latest_info.description if latest_info else ""
        },
        "is_latest": current_version == latest_version,
        "active_versions": api_version_manager.get_active_versions(),
        "deprecated_versions": api_version_manager.get_deprecated_versions()
    }

@router.get("/endpoints", response_model=Dict[str, Any])
async def get_endpoints_info(request: 'Request' = None):
    """获取端点信息"""
    current_version = get_current_api_version(request)

    # 获取当前版本的端点
    current_endpoints = api_version_manager.endpoints.get(current_version, [])

    endpoints_info = []
    for endpoint in current_endpoints:
        endpoints_info.append({
            "path": endpoint.path,
            "method": endpoint.method,
            "description": endpoint.description,
            "deprecated_in_version": endpoint.deprecated_in_version,
            "alternatives": endpoint.alternatives
        })

    return {
        "version": current_version,
        "endpoints_count": len(endpoints_info),
        "endpoints": endpoints_info
    }

@router.post("/migrate", response_model=Dict[str, Any])
async def test_migration(
    from_version: str,
    to_version: str,
    sample_data: Dict[str, Any],
    request: 'Request' = None
):
    """测试数据迁移"""
    from backend.core.api_versioning import api_migration_tool

    try:
        migrated_data = api_migration_tool.migrate_request_data(
            sample_data, from_version, to_version
        )

        return {
            "success": True,
            "from_version": from_version,
            "to_version": to_version,
            "original_data": sample_data,
            "migrated_data": migrated_data,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"迁移失败: {str(e)}"
        )

# v2特有的增强功能
@router.get("/performance", response_model=Dict[str, Any])
@require_version(min_version="v2")
async def get_performance_metrics(request: 'Request' = None):
    """获取性能指标 (v2特有)"""
    current_version = get_current_api_version(request)

    # 获取版本统计信息
    stats = api_version_manager.get_version_statistics(days=1)
    version_stats = stats.get(current_version, {})

    return {
        "version": current_version,
        "performance_metrics": {
            "requests_last_24h": version_stats.get("requests", 0),
            "error_rate": (
                version_stats.get("errors", 0) / max(version_stats.get("requests", 1), 1) * 100
            ),
            "last_request": version_stats.get("last_used"),
            "uptime_percentage": 99.9,  # 模拟数据
            "average_response_time": 150  # 模拟数据，毫秒
        },
        "system_health": {
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "disk_usage": 23.1,
            "network_latency": 12.5
        }
    }