"""
缓存系统API接口
提供缓存管理、监控、预热和配置的REST API
"""

import asyncio
import time
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field

from backend.core.cache.multi_level_cache import (
    get_cache_manager, CacheLevel, MultiLevelCacheManager
)
from backend.core.cache.cache_warmup import (
    get_warmup_manager, CacheWarmupManager, WarmupPriority, WarmupTask
)
from backend.core.cache.cache_monitor import (
    get_monitoring_system, CacheMonitoringSystem, AlertSeverity
)
from backend.middleware.cache_middleware import (
    get_cache_middleware, APICacheMiddleware, CacheRule, CacheStrategy
)
from backend.core.base import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["cache"])


# Pydantic模型
class CacheStatsResponse(BaseResponse):
    """缓存统计响应"""
    data: Dict[str, Any] = Field(..., description="缓存统计数据")


class CacheKeyRequest(BaseModel):
    """缓存键请求"""
    key: str = Field(..., description="缓存键")
    levels: List[str] = Field(default=["l1_memory", "l2_redis"], description="缓存级别")


class CacheValueRequest(BaseModel):
    """缓存值请求"""
    key: str = Field(..., description="缓存键")
    value: Any = Field(..., description="缓存值")
    ttl: int = Field(default=300, description="TTL(秒)")
    levels: List[str] = Field(default=["l1_memory", "l2_redis"], description="缓存级别")


class WarmupRequest(BaseModel):
    """预热请求"""
    keys: List[str] = Field(..., description="要预热的缓存键")
    priority: str = Field(default="medium", description="优先级")
    ttl: int = Field(default=300, description="TTL(秒)")


class CacheRuleCreate(BaseModel):
    """缓存规则创建请求"""
    path_pattern: str = Field(..., description="路径模式")
    methods: List[str] = Field(..., description="HTTP方法")
    cache_ttl: int = Field(default=300, description="缓存TTL")
    strategy: str = Field(default="multi_level", description="缓存策略")
    key_strategy: str = Field(default="path_params", description="键策略")
    user_specific: bool = Field(default=False, description="用户特定缓存")
    tags: List[str] = Field(default=[], description="标签")


class AlertResolveRequest(BaseModel):
    """告警解决请求"""
    alert_id: str = Field(..., description="告警ID")


# 缓存操作API
@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """获取缓存系统统计信息"""
    try:
        cache_manager = await get_cache_manager()
        stats = await cache_manager.get_comprehensive_stats()
        return CacheStatsResponse(
            success=True,
            message="Cache statistics retrieved successfully",
            data=stats
        )
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_cache_dashboard():
    """获取缓存监控仪表盘"""
    try:
        monitoring_system = await get_monitoring_system()
        dashboard = await monitoring_system.get_monitoring_dashboard()
        return CacheStatsResponse(
            success=True,
            message="Cache dashboard retrieved successfully",
            data=dashboard
        )
    except Exception as e:
        logger.error(f"Error getting cache dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get")
async def get_cache_value(request: CacheKeyRequest):
    """获取缓存值"""
    try:
        cache_manager = await get_cache_manager()

        # 转换级别字符串到枚举
        levels = []
        for level_str in request.levels:
            try:
                level = CacheLevel(level_str)
                levels.append(level)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid cache level: {level_str}"
                )

        value = await cache_manager.get(request.key, levels)

        return CacheStatsResponse(
            success=True,
            message="Cache value retrieved successfully",
            data={
                "key": request.key,
                "value": value,
                "found": value is not None
            }
        )
    except Exception as e:
        logger.error(f"Error getting cache value: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/set")
async def set_cache_value(request: CacheValueRequest):
    """设置缓存值"""
    try:
        cache_manager = await get_cache_manager()

        # 转换级别字符串到枚举
        levels = []
        for level_str in request.levels:
            try:
                level = CacheLevel(level_str)
                levels.append(level)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid cache level: {level_str}"
                )

        await cache_manager.set(request.key, request.value, request.ttl, levels)

        return CacheStatsResponse(
            success=True,
            message="Cache value set successfully",
            data={
                "key": request.key,
                "ttl": request.ttl,
                "levels": request.levels
            }
        )
    except Exception as e:
        logger.error(f"Error setting cache value: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_cache(
    levels: List[str] = Query(default=["l1_memory", "l2_redis"], description="要清空的缓存级别")
):
    """清空缓存"""
    try:
        cache_manager = await get_cache_manager()

        # 转换级别字符串到枚举
        level_enums = []
        for level_str in levels:
            try:
                level = CacheLevel(level_str)
                level_enums.append(level)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid cache level: {level_str}"
                )

        await cache_manager.clear(level_enums)

        return CacheStatsResponse(
            success=True,
            message="Cache cleared successfully",
            data={"cleared_levels": levels}
        )
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 缓存预热API
@router.get("/warmup/stats")
async def get_warmup_stats():
    """获取预热统计信息"""
    try:
        warmup_manager = await get_warmup_manager()
        stats = await warmup_manager.get_warmup_stats()
        return CacheStatsResponse(
            success=True,
            message="Warmup statistics retrieved successfully",
            data=stats
        )
    except Exception as e:
        logger.error(f"Error getting warmup stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/warmup/schedule")
async def schedule_warmup(request: WarmupRequest):
    """调度缓存预热"""
    try:
        warmup_manager = await get_warmup_manager()

        # 转换优先级
        try:
            priority = WarmupPriority(request.priority)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid priority: {request.priority}"
            )

        scheduled_count = await warmup_manager.force_warmup(request.keys, priority)

        return CacheStatsResponse(
            success=True,
            message="Warmup tasks scheduled successfully",
            data={
                "scheduled_count": scheduled_count,
                "keys": request.keys,
                "priority": request.priority
            }
        )
    except Exception as e:
        logger.error(f"Error scheduling warmup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/warmup/user/{user_id}")
async def schedule_user_warmup(user_id: str):
    """为特定用户调度预热"""
    try:
        warmup_manager = await get_warmup_manager()
        await warmup_manager.schedule_user_based_warmup(user_id)

        return CacheStatsResponse(
            success=True,
            message=f"User-based warmup scheduled for {user_id}",
            data={"user_id": user_id}
        )
    except Exception as e:
        logger.error(f"Error scheduling user warmup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 性能监控API
@router.get("/monitoring/metrics")
async def get_detailed_metrics(
    metric_name: Optional[str] = Query(None, description="指标名称"),
    duration_minutes: int = Query(default=60, description="时间范围(分钟)")
):
    """获取详细性能指标"""
    try:
        monitoring_system = await get_monitoring_system()
        metrics = await monitoring_system.get_detailed_metrics(metric_name, duration_minutes)
        return CacheStatsResponse(
            success=True,
            message="Performance metrics retrieved successfully",
            data=metrics
        )
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/alerts")
async def get_alerts(
    active_only: bool = Query(default=False, description="仅获取活跃告警"),
    limit: int = Query(default=50, description="限制数量")
):
    """获取告警信息"""
    try:
        monitoring_system = await get_monitoring_system()

        if active_only:
            # 获取活跃告警
            dashboard = await monitoring_system.get_monitoring_dashboard()
            alerts = dashboard.get("recent_alerts", [])
            # 过滤未解决的告警
            active_alerts = [alert for alert in alerts if not alert.get("resolved", True)]
            alerts_data = active_alerts[:limit]
        else:
            # 获取告警历史
            alerts_data = await monitoring_system.get_alert_history(limit)

        return CacheStatsResponse(
            success=True,
            message="Alerts retrieved successfully",
            data={"alerts": alerts_data, "active_only": active_only}
        )
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/alerts/resolve")
async def resolve_alert(request: AlertResolveRequest):
    """解决告警"""
    try:
        monitoring_system = await get_monitoring_system()
        success = await monitoring_system.resolve_alert(request.alert_id)

        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")

        return CacheStatsResponse(
            success=True,
            message="Alert resolved successfully",
            data={"alert_id": request.alert_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 缓存规则管理API
@router.get("/rules")
async def get_cache_rules():
    """获取缓存规则"""
    try:
        cache_middleware = get_cache_middleware()
        rules = []

        if hasattr(cache_middleware, 'rules'):
            for rule in cache_middleware.rules:
                rule_dict = {
                    "path_pattern": rule.path_pattern,
                    "methods": rule.methods,
                    "cache_ttl": rule.cache_ttl,
                    "strategy": rule.strategy.value,
                    "key_strategy": rule.key_strategy.value,
                    "user_specific": rule.user_specific,
                    "tags": rule.tags
                }
                rules.append(rule_dict)

        return CacheStatsResponse(
            success=True,
            message="Cache rules retrieved successfully",
            data={"rules": rules}
        )
    except Exception as e:
        logger.error(f"Error getting cache rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules")
async def create_cache_rule(request: CacheRuleCreate):
    """创建缓存规则"""
    try:
        # 转换策略枚举
        try:
            strategy = CacheStrategy(request.strategy)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid cache strategy: {request.strategy}"
            )

        # 导入键策略枚举
        from backend.middleware.cache_middleware import CacheKeyStrategy

        try:
            key_strategy = CacheKeyStrategy(request.key_strategy)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid key strategy: {request.key_strategy}"
            )

        # 创建缓存规则
        rule = CacheRule(
            path_pattern=request.path_pattern,
            methods=request.methods,
            cache_ttl=request.cache_ttl,
            strategy=strategy,
            key_strategy=key_strategy,
            user_specific=request.user_specific,
            tags=request.tags
        )

        # 添加规则到中间件
        cache_middleware = get_cache_middleware()
        if hasattr(cache_middleware, 'add_rule'):
            cache_middleware.add_rule(rule)
        else:
            logger.warning("Cache middleware not properly initialized")

        return CacheStatsResponse(
            success=True,
            message="Cache rule created successfully",
            data={
                "path_pattern": request.path_pattern,
                "strategy": request.strategy,
                "cache_ttl": request.cache_ttl
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating cache rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{path_pattern:path}")
async def delete_cache_rule(path_pattern: str):
    """删除缓存规则"""
    try:
        cache_middleware = get_cache_middleware()
        if hasattr(cache_middleware, 'remove_rule'):
            cache_middleware.remove_rule(path_pattern)
        else:
            logger.warning("Cache middleware not properly initialized")

        return CacheStatsResponse(
            success=True,
            message="Cache rule deleted successfully",
            data={"path_pattern": path_pattern}
        )
    except Exception as e:
        logger.error(f"Error deleting cache rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 健康检查API
@router.get("/health")
async def get_cache_health():
    """获取缓存系统健康状态"""
    try:
        health_info = {
            "timestamp": time.time(),
            "status": "healthy",
            "components": {}
        }

        # 检查缓存管理器
        try:
            cache_manager = await get_cache_manager()
            stats = await cache_manager.get_comprehensive_stats()
            health_info["components"]["cache_manager"] = {
                "status": "healthy",
                "overall_hit_rate": stats.get("overall", {}).get("hit_rate", 0),
                "total_requests": stats.get("overall", {}).get("total_requests", 0)
            }
        except Exception as e:
            health_info["components"]["cache_manager"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_info["status"] = "degraded"

        # 检查预热管理器
        try:
            warmup_manager = await get_warmup_manager()
            warmup_stats = await warmup_manager.get_warmup_stats()
            health_info["components"]["warmup_manager"] = {
                "status": "healthy",
                "scheduler_running": warmup_stats.get("scheduler_running", False),
                "queue_size": warmup_stats.get("queue_size", 0)
            }
        except Exception as e:
            health_info["components"]["warmup_manager"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_info["status"] = "degraded"

        # 检查监控系统
        try:
            monitoring_system = await get_monitoring_system()
            dashboard = await monitoring_system.get_monitoring_dashboard()
            health_info["components"]["monitoring_system"] = {
                "status": "healthy",
                "monitoring_active": dashboard.get("monitoring_active", False),
                "performance_score": dashboard.get("performance_score", 0)
            }
        except Exception as e:
            health_info["components"]["monitoring_system"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_info["status"] = "degraded"

        status_code = 200 if health_info["status"] == "healthy" else 503

        return CacheStatsResponse(
            success=health_info["status"] == "healthy",
            message=f"Cache system is {health_info['status']}",
            data=health_info
        )

    except Exception as e:
        logger.error(f"Error checking cache health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 配置管理API
@router.get("/config")
async def get_cache_config():
    """获取缓存配置信息"""
    try:
        config_info = {
            "cache_levels": {
                "l1_memory": {
                    "description": "内存缓存 - 最快访问",
                    "default_ttl": 300,
                    "max_size": "configurable"
                },
                "l2_redis": {
                    "description": "Redis缓存 - 快速访问",
                    "default_ttl": 3600,
                    "persistent": True
                },
                "l3_persistent": {
                    "description": "持久化缓存 - 中等速度",
                    "default_ttl": 86400,
                    "storage": "filesystem"
                }
            },
            "strategies": [strategy.value for strategy in CacheStrategy],
            "key_strategies": ["path_only", "path_params", "path_headers", "path_user", "full"],
            "monitoring": {
                "collection_interval": 30,
                "analysis_interval": 300,
                "alert_rules": "configurable"
            },
            "warmup": {
                "max_concurrent_tasks": 10,
                "warmup_interval": 300,
                "pattern_analysis": True
            }
        }

        return CacheStatsResponse(
            success=True,
            message="Cache configuration retrieved successfully",
            data=config_info
        )
    except Exception as e:
        logger.error(f"Error getting cache config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 实用工具API
@router.post("/benchmark")
async def benchmark_cache_performance(
    iterations: int = Query(default=1000, description="测试迭代次数"),
    key_size: int = Query(default=100, description="键大小")
):
    """缓存性能基准测试"""
    try:
        cache_manager = await get_cache_manager()

        # 生成测试数据
        test_data = {"message": "benchmark_data", "timestamp": time.time()}

        results = {
            "iterations": iterations,
            "key_size": key_size,
            "set_times": [],
            "get_times": [],
            "hit_rate": 0
        }

        # 设置操作测试
        for i in range(iterations):
            key = f"benchmark_{i:04d}"

            # 测试设置
            start_time = time.time()
            await cache_manager.set(key, test_data, 300)
            set_time = time.time() - start_time
            results["set_times"].append(set_time)

        # 获取操作测试
        hits = 0
        for i in range(iterations):
            key = f"benchmark_{i:04d}"

            # 测试获取
            start_time = time.time()
            value = await cache_manager.get(key)
            get_time = time.time() - start_time
            results["get_times"].append(get_time)

            if value is not None:
                hits += 1

        # 计算统计数据
        results["avg_set_time"] = sum(results["set_times"]) / len(results["set_times"])
        results["avg_get_time"] = sum(results["get_times"]) / len(results["get_times"])
        results["hit_rate"] = hits / iterations
        results["total_time"] = sum(results["set_times"]) + sum(results["get_times"])

        return CacheStatsResponse(
            success=True,
            message="Cache benchmark completed successfully",
            data=results
        )

    except Exception as e:
        logger.error(f"Error in cache benchmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))