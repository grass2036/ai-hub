"""
系统健康检查API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from backend.core.health_service import get_system_health
from backend.core.ai_service import ai_manager
from backend.core.cache_service import cache_stats, cleanup_expired_cache

router = APIRouter()


class ServiceHealthResponse(BaseModel):
    """服务健康响应模型"""
    name: str = Field(..., description="服务名称")
    status: str = Field(..., description="健康状态")
    response_time: float = Field(..., description="响应时间(秒)")
    last_check: str = Field(..., description="最后检查时间")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    details: Optional[Dict[str, Any]] = Field(default=None, description="详细信息")


class SystemHealthResponse(BaseModel):
    """系统健康响应模型"""
    status: str = Field(..., description="整体状态")
    timestamp: str = Field(..., description="检查时间")
    uptime: float = Field(..., description="运行时间(秒)")
    services: List[ServiceHealthResponse] = Field(..., description="服务状态列表")
    performance_metrics: Dict[str, Any] = Field(..., description="性能指标")
    cache_stats: Dict[str, Any] = Field(..., description="缓存统计")


class DetailedHealthResponse(BaseModel):
    """详细健康检查响应"""
    system: SystemHealthResponse = Field(..., description="系统状态")
    ai_services: Dict[str, Any] = Field(..., description="AI服务状态")
    recommendations: List[str] = Field(..., description="优化建议")


@router.get("/health", response_model=SystemHealthResponse)
async def get_health():
    """
    获取系统健康状态
    """
    try:
        health_data = await get_system_health()
        return SystemHealthResponse(**health_data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"健康检查失败: {str(e)}"
        )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def get_detailed_health():
    """
    获取详细的系统健康状态
    """
    try:
        # 获取系统健康状态
        system_health = await get_system_health()

        # 获取AI服务状态
        ai_services = await ai_manager.list_available_services()

        # 生成优化建议
        recommendations = _generate_recommendations(system_health, ai_services)

        return DetailedHealthResponse(
            system=SystemHealthResponse(**system_health),
            ai_services=ai_services,
            recommendations=recommendations
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"详细健康检查失败: {str(e)}"
        )


@router.get("/health/services")
async def get_services_health():
    """
    获取各个服务的健康状态
    """
    try:
        health_data = await get_system_health()
        return {
            "timestamp": health_data["timestamp"],
            "overall_status": health_data["status"],
            "services": health_data["services"],
            "summary": {
                "total": len(health_data["services"]),
                "healthy": len([s for s in health_data["services"] if s["status"] == "healthy"]),
                "degraded": len([s for s in health_data["services"] if s["status"] == "degraded"]),
                "unhealthy": len([s for s in health_data["services"] if s["status"] == "unhealthy"])
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"服务健康检查失败: {str(e)}"
        )


@router.post("/health/cache/cleanup")
async def cleanup_cache():
    """
    清理过期缓存
    """
    try:
        cleaned_count = cleanup_expired_cache()
        return {
            "message": f"已清理 {cleaned_count} 个过期缓存项",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"缓存清理失败: {str(e)}"
        )


@router.get("/health/metrics")
async def get_health_metrics():
    """
    获取健康指标统计
    """
    try:
        system_health = await get_system_health()
        cache_stats_data = cache_stats()

        return {
            "timestamp": datetime.now().isoformat(),
            "system_status": system_health["status"],
            "uptime": {
                "seconds": system_health["uptime"],
                "human_readable": system_health["performance_metrics"]["uptime_human"]
            },
            "services": {
                "total": len(system_health["services"]),
                "healthy": len([s for s in system_health["services"] if s["status"] == "healthy"]),
                "average_response_time": sum(s["response_time"] for s in system_health["services"]) / len(system_health["services"])
            },
            "cache": cache_stats_data,
            "performance": system_health["performance_metrics"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取健康指标失败: {str(e)}"
        )


def _generate_recommendations(system_health: Dict[str, Any], ai_services: Dict[str, Any]) -> List[str]:
    """生成优化建议"""
    recommendations = []

    # 分析服务状态
    unhealthy_services = [s for s in system_health["services"] if s["status"] == "unhealthy"]
    degraded_services = [s for s in system_health["services"] if s["status"] == "degraded"]

    if unhealthy_services:
        recommendations.append(f"🔴 {len(unhealthy_services)} 个服务不健康: {', '.join(s['name'] for s in unhealthy_services)}")

    if degraded_services:
        recommendations.append(f"🟡 {len(degraded_services)} 个服务降级: {', '.join(s['name'] for s in degraded_services)}")

    # 分析响应时间
    slow_services = [s for s in system_health["services"] if s["response_time"] > 2.0]
    if slow_services:
        recommendations.append(f"⏱️ {len(slow_services)} 个服务响应较慢 (>2s): {', '.join(s['name'] for s in slow_services)}")

    # 分析缓存
    cache_hit_rate = system_health["cache_stats"].get("hit_rate", 0)
    if cache_hit_rate < 0.3:
        recommendations.append("💾 缓存命中率较低，建议增加缓存使用")
    elif cache_hit_rate > 0.8:
        recommendations.append("✅ 缓存效果良好")

    # 分析运行时间
    uptime_hours = system_health["uptime"] / 3600
    if uptime_hours > 24:
        recommendations.append(f"⏰ 系统已稳定运行 {uptime_hours:.1f} 小时")

    # AI服务建议
    available_services = ai_services.get("services", [])
    if len(available_services) >= 2:
        recommendations.append("🤖 多AI服务可用，具备故障转移能力")

    # 如果没有问题
    if not recommendations:
        recommendations.append("✅ 系统运行状态良好")

    return recommendations