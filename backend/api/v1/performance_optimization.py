"""
API性能优化管理接口
提供性能监控、分析、建议和管理功能的REST API
"""

import asyncio
import time
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field

from backend.middleware.performance_middleware import get_performance_middleware
from backend.core.performance.resource_manager import get_resource_manager
from backend.core.performance.performance_analyzer import get_performance_analyzer
from backend.core.performance.optimization_engine import get_optimization_engine
from backend.core.base import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance-optimization", tags=["performance-optimization"])


# Pydantic模型
class PerformanceStatsResponse(BaseResponse):
    """性能统计响应"""
    data: Dict[str, Any] = Field(..., description="性能统计数据")


class OptimizationRequest(BaseModel):
    """优化请求"""
    endpoint: Optional[str] = Field(None, description="要优化的端点")
    optimization_types: List[str] = Field(default=[], description="优化类型")
    priority: str = Field(default="medium", description="优先级")
    auto_apply: bool = Field(default=False, description="是否自动应用")


class OptimizationSuggestionResponse(BaseResponse):
    """优化建议响应"""
    data: Dict[str, Any] = Field(..., description="优化建议数据")


class ResourcePoolCreateRequest(BaseModel):
    """资源池创建请求"""
    pool_id: str = Field(..., description="资源池ID")
    pool_type: str = Field(..., description="资源池类型 (database/redis)")
    host: str = Field(default="localhost", description="主机地址")
    port: int = Field(default=5432, description="端口")
    db: int = Field(default=0, description="数据库编号")
    password: Optional[str] = Field(None, description="密码")
    min_size: int = Field(default=5, description="最小连接数")
    max_size: int = Field(default=20, description="最大连接数")


# 性能监控API
@router.get("/stats", response_model=PerformanceStatsResponse)
async def get_performance_stats():
    """获取性能统计信息"""
    try:
        # 获取中间件性能统计
        middleware = get_performance_middleware()
        middleware_stats = middleware.get_performance_stats() if middleware else {}

        # 获取资源管理器统计
        resource_manager = await get_resource_manager()
        resource_stats = resource_manager.get_comprehensive_stats() if resource_manager else {}

        # 获取性能分析器统计
        analyzer = await get_performance_analyzer()
        analyzer_stats = analyzer.get_analysis_summary() if analyzer else {}

        # 合并所有统计数据
        combined_stats = {
            "timestamp": time.time(),
            "middleware_performance": middleware_stats,
            "resource_utilization": resource_stats,
            "performance_analysis": analyzer_stats,
            "system_health": {
                "middleware_available": middleware is not None,
                "resource_manager_available": resource_manager is not None,
                "analyzer_available": analyzer is not None
            }
        }

        return PerformanceStatsResponse(
            success=True,
            message="Performance statistics retrieved successfully",
            data=combined_stats
        )

    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_performance_dashboard():
    """获取性能监控仪表盘"""
    try:
        # 获取综合性能数据
        stats = await get_performance_stats()

        # 获取实时性能指标
        middleware = get_performance_middleware()
        recent_metrics = middleware.get_recent_metrics(50) if middleware else []

        # 计算关键性能指标
        performance_summary = {
            "total_requests": len(recent_metrics),
            "avg_response_time": sum(m.get("duration", 0) for m in recent_metrics) / max(1, len(recent_metrics)),
            "error_rate": sum(1 for m in recent_metrics if m.get("status_code", 200) >= 400) / max(1, len(recent_metrics)),
            "cache_hit_rate": middleware.compressor.get_compression_stats().get("compression_rate", 0) if middleware else 0,
            "compression_savings": middleware.compressor.get_compression_stats().get("space_saved_bytes", 0) if middleware else 0
        }

        # 获取系统资源状态
        resource_manager = await get_resource_manager()
        resource_status = resource_manager.get_comprehensive_stats() if resource_manager else {}

        # 获取性能分析结果
        analyzer = await get_performance_analyzer()
        analysis_results = await analyzer.analyze_performance() if analyzer else {}

        dashboard_data = {
            "timestamp": time.time(),
            "performance_summary": performance_summary,
            "recent_metrics": recent_metrics,
            "resource_status": resource_status,
            "performance_analysis": analysis_results,
            "alerts": [],
            "recommendations": []
        }

        return PerformanceStatsResponse(
            success=True,
            message="Performance dashboard retrieved successfully",
            data=dashboard_data
        )

    except Exception as e:
        logger.error(f"Error getting performance dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_detailed_metrics(
    endpoint: Optional[str] = Query(None, description="端点过滤"),
    duration_minutes: int = Query(default=60, description="时间范围(分钟)"),
    metric_type: Optional[str] = Query(None, description="指标类型过滤")
):
    """获取详细性能指标"""
    try:
        analyzer = await get_performance_analyzer()

        if endpoint:
            # 获取特定端点的性能分析
            analysis = await analyzer.analyze_performance(endpoint)
            return PerformanceStatsResponse(
                success=True,
                message="Endpoint performance metrics retrieved successfully",
                data=analysis
            )
        else:
            # 获取系统级性能分析
            analysis = await analyzer.analyze_performance()
            return PerformanceStatsResponse(
                success=True,
                message="System performance metrics retrieved successfully",
                data=analysis
            )

    except Exception as e:
        logger.error(f"Error getting detailed metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends")
async def get_performance_trends(
    metric_name: str = Query(..., description="指标名称"),
    hours: int = Query(default=24, description="时间范围(小时)")
):
    """获取性能趋势数据"""
    try:
        middleware = get_performance_middleware()
        if not middleware:
            raise HTTPException(status_code=503, detail="Performance middleware not available")

        # 获取趋势数据
        recent_metrics = middleware.get_recent_metrics(1000)  # 获取更多数据用于趋势分析

        # 按时间排序并提取趋势数据
        trend_data = []
        for metric in recent_metrics:
            if metric_name in ["duration", "response_size", "cpu_usage", "memory_usage"]:
                value = metric.get(metric_name, 0)
                trend_data.append({
                    "timestamp": metric.get("end_time", metric.get("start_time", time.time())),
                    "value": value,
                    "metric_name": metric_name
                })

        return PerformanceStatsResponse(
            success=True,
            message="Performance trends retrieved successfully",
            data={
                "metric_name": metric_name,
                "trend_data": trend_data,
                "time_range_hours": hours
            }
        )

    except Exception as e:
        logger.error(f"Error getting performance trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 性能优化建议API
@router.post("/analyze", response_model=OptimizationSuggestionResponse)
async def analyze_performance(
    request: OptimizationRequest = Body(...)
):
    """分析性能并生成优化建议"""
    try:
        analyzer = await get_performance_analyzer()

        # 获取性能分析数据
        if request.endpoint:
            analysis_data = await analyzer.analyze_performance(request.endpoint)
        else:
            analysis_data = await analyzer.analyze_performance()

        # 生成优化建议
        from backend.core.performance.optimization_engine import generate_optimization_suggestions
        suggestions = await generate_optimization_suggestions(analysis_data)

        # 如果指定了优化类型，过滤建议
        if request.optimization_types:
            suggestions = [s for s in suggestions if s.get("type") in request.optimization_types]

        # 如果自动应用，执行建议
        applied_suggestions = []
        if request.auto_apply:
            from backend.core.performance.optimization_engine import apply_optimization_suggestion
            for suggestion in suggestions[:3]:  # 最多自动应用前3个
                success = await apply_optimization_suggestion(s["suggestion_id"], {})
                if success:
                    applied_suggestions.append(s["suggestion_id"])

        return OptimizationSuggestionResponse(
            success=True,
            message="Performance analysis completed successfully",
            data={
                "analysis_summary": analysis_data,
                "suggestions": suggestions,
                "applied_suggestions": applied_suggestions,
                "total_suggestions": len(suggestions)
            }
        )

    except Exception as e:
        logger.error(f"Error analyzing performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions")
async def get_optimization_suggestions(
    priority: Optional[str] = Query(None, description="优先级过滤"),
    type_filter: Optional[str] = Query(None, description="类型过滤"),
    limit: int = Query(default=20, description="限制数量")
):
    """获取优化建议列表"""
    try:
        engine = await get_optimization_engine()
        analytics = engine.get_suggestion_analytics()

        # 获取最近的建议
        recent_suggestions = analytics.get("recent_suggestions", [])

        # 应用过滤器
        filtered_suggestions = recent_suggestions
        if priority:
            filtered_suggestions = [s for s in filtered_suggestions if s.get("priority") == priority]
        if type_filter:
            filtered_suggestions = [s for s in filtered_suggestions if s.get("type") == type_filter]

        # 限制数量
        limited_suggestions = filtered_suggestions[:limit]

        return OptimizationSuggestionResponse(
            success=True,
            message="Optimization suggestions retrieved successfully",
            data={
                "suggestions": limited_suggestions,
                "total_available": len(recent_suggestions),
                "filters_applied": {
                    "priority": priority,
                    "type": type_filter,
                    "limit": limit
                }
            }
        )

    except Exception as e:
        logger.error(f"Error getting optimization suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggestions/{suggestion_id}/apply")
async def apply_optimization_suggestion(
    suggestion_id: str,
    params: Dict = Body(default={})
):
    """应用优化建议"""
    try:
        from backend.core.performance.optimization_engine import apply_optimization_suggestion
        success = await apply_optimization_suggestion(suggestion_id, params)

        return OptimizationSuggestionResponse(
            success=success,
            message=f"Optimization suggestion {suggestion_id} {'applied successfully' if success else 'application failed'}",
            data={
                "suggestion_id": suggestion_id,
                "applied": success,
                "execution_params": params
            }
        )

    except Exception as e:
        logger.error(f"Error applying optimization suggestion {suggestion_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions/analytics")
async def get_optimization_analytics():
    """获取优化建议分析数据"""
    try:
        engine = await get_optimization_engine()
        analytics = engine.get_suggestion_analytics()

        return OptimizationSuggestionResponse(
            success=True,
            message="Optimization analytics retrieved successfully",
            data=analytics
        )

    except Exception as e:
        logger.error(f"Error getting optimization analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 资源管理API
@router.get("/resources")
async def get_resource_status():
    """获取资源状态"""
    try:
        resource_manager = await get_resource_manager()
        stats = resource_manager.get_comprehensive_stats()

        return PerformanceStatsResponse(
            success=True,
            message="Resource status retrieved successfully",
            data=stats
        )

    except Exception as e:
        logger.error(f"Error getting resource status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resources/pools")
async def create_resource_pool(request: ResourcePoolCreateRequest = Body(...)):
    """创建资源池"""
    try:
        resource_manager = await get_resource_manager()

        if request.pool_type == "database":
            pool = await resource_manager.create_database_pool(
                pool_id=request.pool_id,
                dsn=f"postgresql://user:pass@{request.host}:{request.port}/{request.db}",
                min_size=request.min_size,
                max_size=request.max_size
            )
        elif request.pool_type == "redis":
            pool = await resource_manager.create_redis_pool(
                pool_id=request.pool_id,
                host=request.host,
                port=request.port,
                db=request.db,
                password=request.password,
                max_connections=request.max_size
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid pool type")

        return PerformanceStatsResponse(
            success=True,
            message=f"Resource pool {request.pool_id} created successfully",
            data={
                "pool_id": request.pool_id,
                "pool_type": request.pool_type,
                "status": "created"
            }
        )

    except Exception as e:
        logger.error(f"Error creating resource pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resources/pools")
async def get_resource_pools():
    """获取资源池列表"""
    try:
        resource_manager = await get_resource_manager()
        stats = resource_manager.get_comprehensive_stats()

        pools = []
        for pool_id, metrics in stats.get("pool_details", {}).items():
            pools.append({
                "pool_id": pool_id,
                "type": metrics["type"],
                "status": metrics["status"],
                "usage_count": metrics["usage_count"],
                "error_rate": metrics["error_rate"],
                "avg_response_time": metrics["avg_response_time"],
                "health_score": metrics["health_score"],
                "current_connections": metrics.get("current_connections", 0),
                "max_connections": metrics.get("max_connections", 0)
            })

        return PerformanceStatsResponse(
            success=True,
            message="Resource pools retrieved successfully",
            data={"pools": pools}
        )

    except Exception as e:
        logger.error(f"Error getting resource pools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/resources/pools/{pool_id}")
async def delete_resource_pool(pool_id: str):
    """删除资源池"""
    try:
        resource_manager = await get_resource_manager()
        pool = await resource_manager.get_pool(pool_id)

        if not pool:
            raise HTTPException(status_code=404, detail=f"Pool {pool_id} not found")

        await pool.close()

        return PerformanceStatsResponse(
            success=True,
            message=f"Resource pool {pool_id} deleted successfully",
            data={"pool_id": pool_id}
        )

    except Exception as e:
        logger.error(f"Error deleting resource pool {pool_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 性能基准测试API
@router.post("/benchmark")
async def run_performance_benchmark(
    iterations: int = Query(default=100, description="测试迭代次数"),
    concurrent_requests: int = Query(default=10, description="并发请求数"),
    endpoint: str = Query(default="/health", description="测试端点")
):
    """运行性能基准测试"""
    try:
        import asyncio
        import aiohttp
        import time

        # 基准测试函数
        async def benchmark_request(session, url):
            start_time = time.time()
            async with session.get(url) as response:
                await response.text()
                end_time = time.time()
                return end_time - start_time

        # 执行基准测试
        async with aiohttp.ClientSession() as session:
            # 并发测试
            tasks = []
            for i in range(concurrent_requests):
                for j in range(iterations // concurrent_requests):
                    tasks.append(benchmark_request(session, f"http://localhost:8001{endpoint}"))

            start_time = time.time()
            response_times = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

        # 计算统计指标
        total_requests = len(response_times)
        avg_time = sum(response_times) / total_requests
        min_time = min(response_times)
        max_time = max(response_times)

        # 计算百分位数
        sorted_times = sorted(response_times)
        p50 = sorted_times[len(sorted_times) // 2]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]

        # 计算吞吐量
        requests_per_sec = total_requests / total_time

        benchmark_results = {
            "test_parameters": {
                "iterations": iterations,
                "concurrent_requests": concurrent_requests,
                "endpoint": endpoint,
                "total_requests": total_requests
            },
            "response_times": {
                "average": avg_time,
                "min": min_time,
                "max": max_time,
                "p50": p50,
                "p95": p95,
                "p99": p99
            },
            "performance_metrics": {
                "requests_per_second": requests_per_sec,
                "total_test_duration": total_time,
                "concurrent_efficiency": (avg_time * concurrent_requests) / total_time
            },
            "timestamp": time.time()
        }

        return PerformanceStatsResponse(
            success=True,
            message="Performance benchmark completed successfully",
            data=benchmark_results
        )

    except Exception as e:
        logger.error(f"Error running performance benchmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 配置管理API
@router.get("/config")
async def get_performance_config():
    """获取性能配置"""
    try:
        config_info = {
            "middleware": {
                "compression_enabled": True,
                "async_pool_enabled": True,
                "max_concurrent_tasks": 50,
                "compression_level": 6,
                "slow_request_threshold": 1.0
            },
            "analyzer": {
                "analysis_window": 100,
                "anomaly_threshold": 0.1,
                "trend_window": 20,
                "ml_training_min_samples": 100
            },
            "optimizer": {
                "auto_execution_enabled": True,
                "suggestion_history_max": 500,
                "optimization_rules_count": 6
            },
            "monitoring": {
                "collection_interval": 30,
                "health_check_interval": 60,
                "cleanup_interval": 300
            }
        }

        return PerformanceStatsResponse(
            success=True,
            message="Performance configuration retrieved successfully",
            data=config_info
        )

    except Exception as e:
        logger.error(f"Error getting performance config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/reset")
async def reset_performance_stats():
    """重置性能统计"""
    try:
        # 重置中间件统计
        middleware = get_performance_middleware()
        if middleware:
            middleware.reset_stats()

        # 重置资源管理器统计
        resource_manager = await get_resource_manager()
        if resource_manager:
            # 这里可以添加重置资源统计的逻辑
            pass

        return PerformanceStatsResponse(
            success=True,
            message="Performance statistics reset successfully",
            data={"reset_timestamp": time.time()}
        )

    except Exception as e:
        logger.error(f"Error resetting performance stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))