"""
性能优化API端点
Week 6 Day 2: 性能优化和调优 - 性能优化API
提供性能监控、���化建议、报告生成等API接口
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio

from backend.core.database_optimization import DatabaseOptimizer, get_database_optimizer
from backend.core.api_performance_optimizer import api_performance_optimizer
from backend.core.concurrency_optimizer import concurrency_optimizer
from backend.core.cache_system import cache_manager
from backend.core.performance_monitor import performance_monitor, AlertLevel
from backend.core.database import get_db
from backend.core.security import get_current_user_optional

router = APIRouter(prefix="/performance", tags=["Performance"])

@router.get("/dashboard")
async def get_performance_dashboard(
    hours: int = Query(default=1, ge=1, le=24),
    current_user: Optional[Dict] = Depends(get_current_user_optional)
):
    """获取性能监控仪表板数据"""
    try:
        # 获取性能监控数据
        dashboard_data = performance_monitor.get_dashboard_data(hours)

        # 获取API性能统计
        api_report = api_performance_optimizer.get_performance_report(hours * 60)

        # 获取并发性能统计
        concurrency_report = concurrency_optimizer.get_performance_report(hours * 60)

        # 获取缓存统计
        cache_stats = cache_manager.get_all_stats()

        return JSONResponse({
            "success": True,
            "data": {
                "system_metrics": dashboard_data,
                "api_performance": api_report,
                "concurrency_performance": concurrency_report,
                "cache_statistics": cache_stats,
                "timestamp": datetime.now().isoformat()
            }
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取仪表板数据失败: {str(e)}")

@router.get("/database/analysis")
async def get_database_performance_analysis(
    current_user: Optional[Dict] = Depends(get_current_user_optional)
):
    """获取数据库性能分析"""
    try:
        with get_db() as db:
            db_optimizer = get_database_optimizer(db)

            # 执行性能分析
            performance_analysis = await db_optimizer.analyze_query_performance()

            # 获取性能报告
            performance_report = db_optimizer.get_performance_report()

            # 分析表索引
            # 这里可以添加具体的表分析

            return JSONResponse({
                "success": True,
                "data": {
                    "performance_analysis": performance_analysis,
                    "performance_report": performance_report,
                    "timestamp": datetime.now().isoformat()
                }
            })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据库性能分析失败: {str(e)}")

@router.post("/database/optimize")
async def optimize_database_performance(
    current_user: Dict = Depends(get_current_user_optional)
):
    """执行数据库性能优化"""
    try:
        with get_db() as db:
            db_optimizer = get_database_optimizer(db)

            # 创建性能索引
            await db_optimizer.create_performance_indexes()

            # 创建物化视图
            await db_optimizer.create_materialized_views()

            # 清理旧数据
            cleanup_result = await db_optimizer.cleanup_old_data(days=30)

            return JSONResponse({
                "success": True,
                "message": "数据库性能优化完成",
                "data": {
                    "cleanup_result": cleanup_result,
                    "timestamp": datetime.now().isoformat()
                }
            })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库性能优化失败: {str(e)}")

@router.get("/api/metrics")
async def get_api_performance_metrics(
    minutes: int = Query(default=60, ge=5, le=1440),
    current_user: Optional[Dict] = Depends(get_current_user_optional)
):
    """获取API性能指标"""
    try:
        report = api_performance_optimizer.get_performance_report(minutes)

        return JSONResponse({
            "success": True,
            "data": report
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取API性能指标失败: {str(e)}")

@router.post("/api/cache/clear")
async def clear_api_cache(
    pattern: Optional[str] = None,
    current_user: Dict = Depends(get_current_user_optional)
):
    """清理API缓存"""
    try:
        if pattern:
            # 按模式清理
            cleared_patterns = await api_performance_optimizer.invalidate_cache_pattern(pattern)
            message = f"已清理匹配模式 '{pattern}' 的缓存"
        else:
            # 清理所有API缓存
            cache_stats = api_performance_optimizer.cache_manager.get_cache_stats()
            message = "缓存清理功能需要具体实现"

        return JSONResponse({
            "success": True,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理缓存失败: {str(e)}")

@router.get("/concurrency/stats")
async def get_concurrency_statistics(
    minutes: int = Query(default=60, ge=5, le=1440),
    current_user: Optional[Dict] = Depends(get_current_user_optional)
):
    """获取并发性能统计"""
    try:
        report = concurrency_optimizer.get_performance_report(minutes)

        return JSONResponse({
            "success": True,
            "data": report
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取并发统计失败: {str(e)}")

@router.get("/cache/statistics")
async def get_cache_statistics(
    current_user: Optional[Dict] = Depends(get_current_user_optional)
):
    """获取缓存统计信息"""
    try:
        cache_stats = cache_manager.get_all_stats()

        return JSONResponse({
            "success": True,
            "data": cache_stats,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取缓存统计失败: {str(e)}")

@router.post("/cache/warmup")
async def warm_up_cache(
    cache_name: str,
    keys: List[str],
    current_user: Dict = Depends(get_current_user_optional)
):
    """缓存预热"""
    try:
        # 这里需要根据具体业务实现数据加载器
        # 示例实现
        async def dummy_data_loader(key: str):
            return {"key": key, "data": f"预加载的数据 - {key}", "timestamp": datetime.now().isoformat()}

        await cache_manager.warm_up_cache(cache_name, dummy_data_loader, keys)

        return JSONResponse({
            "success": True,
            "message": f"缓存预热完成: {cache_name}, 预热键数: {len(keys)}",
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"缓存预热失败: {str(e)}")

@router.get("/alerts")
async def get_performance_alerts(
    active_only: bool = Query(default=True),
    hours: int = Query(default=24, ge=1, le=168),
    current_user: Optional[Dict] = Depends(get_current_user_optional)
):
    """获取性能告警"""
    try:
        if active_only:
            alerts = performance_monitor.alert_manager.get_active_alerts()
        else:
            alerts = performance_monitor.alert_manager.get_alert_history(hours)

        alerts_data = []
        for alert in alerts:
            alert_dict = {
                "id": alert.id,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "metric_name": alert.metric_name,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
            }
            alerts_data.append(alert_dict)

        return JSONResponse({
            "success": True,
            "data": {
                "alerts": alerts_data,
                "count": len(alerts_data),
                "active_count": len([a for a in alerts_data if not a["resolved"]])
            }
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取性能告警失败: {str(e)}")

@router.post("/alerts/rules")
async def add_alert_rule(
    rule_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user_optional)
):
    """添加告警规则"""
    try:
        # 验证必需字段
        required_fields = ["name", "metric_name", "threshold", "level"]
        for field in required_fields:
            if field not in rule_data:
                raise HTTPException(status_code=400, detail=f"缺少必需字段: {field}")

        # 转换告警级别
        level_str = rule_data["level"].upper()
        try:
            level = AlertLevel(level_str)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的告警级别: {level_str}")

        # 添加告警规则
        performance_monitor.alert_manager.add_alert_rule(
            name=rule_data["name"],
            metric_name=rule_data["metric_name"],
            threshold=float(rule_data["threshold"]),
            operator=rule_data.get("operator", ">"),
            level=level,
            duration=rule_data.get("duration", 300),
            message_template=rule_data.get("message_template")
        )

        return JSONResponse({
            "success": True,
            "message": f"告警规则已添加: {rule_data['name']}",
            "timestamp": datetime.now().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加告警规则失败: {str(e)}")

@router.delete("/alerts/rules/{rule_name}")
async def delete_alert_rule(
    rule_name: str,
    current_user: Dict = Depends(get_current_user_optional)
):
    """删除告警规则"""
    try:
        performance_monitor.alert_manager.remove_alert_rule(rule_name)

        return JSONResponse({
            "success": True,
            "message": f"告警规则已删除: {rule_name}",
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除告警规则失败: {str(e)}")

@router.get("/reports/comprehensive")
async def get_comprehensive_performance_report(
    hours: int = Query(default=24, ge=1, le=168),
    current_user: Optional[Dict] = Depends(get_current_user_optional)
):
    """获取综合性能报告"""
    try:
        # 生成系统性能报告
        system_report = performance_monitor.analyzer.generate_performance_report(hours)

        # 获取API性能报告
        api_report = api_performance_optimizer.get_performance_report(hours * 60)

        # 获取并发性能报告
        concurrency_report = concurrency_optimizer.get_performance_report(hours * 60)

        # 获取数据库性能报告
        with get_db() as db:
            db_optimizer = get_database_optimizer(db)
            db_report = db_optimizer.get_performance_report()

        # 获取缓存统计
        cache_stats = cache_manager.get_all_stats()

        # 生成综合分析
        comprehensive_analysis = {
            "report_period": {
                "hours": hours,
                "start_time": (datetime.now() - timedelta(hours=hours)).isoformat(),
                "end_time": datetime.now().isoformat()
            },
            "system_performance": system_report,
            "api_performance": api_report,
            "concurrency_performance": concurrency_report,
            "database_performance": db_report,
            "cache_performance": cache_stats,
            "overall_health": {
                "status": "healthy" if system_report["performance_score"] > 80 else "warning" if system_report["performance_score"] > 60 else "critical",
                "score": system_report["performance_score"],
                "active_alerts": len(performance_monitor.alert_manager.get_active_alerts()),
                "recommendations_count": len(system_report["recommendations"])
            },
            "optimization_suggestions": {
                "database": db_report.get("optimization_suggestions", []),
                "api": api_report.get("optimization_suggestions", []),
                "system": system_report.get("recommendations", [])
            }
        }

        return JSONResponse({
            "success": True,
            "data": comprehensive_analysis
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成综合性能报告失败: {str(e)}")

@router.post("/optimization/execute")
async def execute_performance_optimization(
    optimization_type: str,
    current_user: Dict = Depends(get_current_user_optional)
):
    """执行性能优化"""
    try:
        results = {}

        if optimization_type in ["database", "all"]:
            # 数据库优化
            with get_db() as db:
                db_optimizer = get_database_optimizer(db)
                await db_optimizer.create_performance_indexes()
                await db_optimizer.create_materialized_views()
                cleanup_result = await db_optimizer.cleanup_old_data(days=30)
                results["database"] = {"status": "completed", "cleanup_result": cleanup_result}

        if optimization_type in ["cache", "all"]:
            # 缓存优化
            # 清理过期的缓存统计
            api_performance_optimizer.clear_old_metrics()
            concurrency_optimizer.clear_old_metrics()
            results["cache"] = {"status": "completed", "message": "缓存统计已清理"}

        if optimization_type in ["system", "all"]:
            # 系统优化
            # 清理旧的性能指标
            api_performance_optimizer.clear_old_metrics()
            concurrency_optimizer.clear_old_metrics()
            results["system"] = {"status": "completed", "message": "系统性能指标已清理"}

        return JSONResponse({
            "success": True,
            "message": f"性能优化执行完成: {optimization_type}",
            "data": {
                "optimization_type": optimization_type,
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行性能优化失败: {str(e)}")

@router.get("/health/summary")
async def get_performance_health_summary(
    current_user: Optional[Dict] = Depends(get_current_user_optional)
):
    """获取性能健康摘要"""
    try:
        # 获取当前指标
        current_metrics = performance_monitor.metrics_collector.get_current_metrics()

        # 获取活跃告警
        active_alerts = performance_monitor.alert_manager.get_active_alerts()

        # 计算健康评分
        health_score = performance_monitor.analyzer._calculate_performance_score(current_metrics)

        # 确定健康状态
        if health_score >= 90:
            health_status = "excellent"
            status_color = "green"
        elif health_score >= 75:
            health_status = "good"
            status_color = "blue"
        elif health_score >= 60:
            health_status = "warning"
            status_color = "yellow"
        else:
            health_status = "critical"
            status_color = "red"

        # 关键指标
        key_metrics = {
            "cpu_usage": current_metrics.get("cpu_percent", 0),
            "memory_usage": current_metrics.get("memory_percent", 0),
            "disk_usage": current_metrics.get("disk_usage_percent", 0),
            "active_processes": current_metrics.get("active_processes", 0)
        }

        summary = {
            "health_status": health_status,
            "health_score": health_score,
            "status_color": status_color,
            "key_metrics": key_metrics,
            "active_alerts_count": len(active_alerts),
            "critical_alerts_count": len([a for a in active_alerts if a.level == AlertLevel.CRITICAL]),
            "last_updated": datetime.now().isoformat(),
            "recommendations": []
        }

        # 添加紧急建议
        if health_score < 60:
            summary["recommendations"].append("系统性能较低，建议立即执行性能优化")

        if len(active_alerts) > 0:
            summary["recommendations"].append(f"存在 {len(active_alerts)} 个活跃告警需要处理")

        return JSONResponse({
            "success": True,
            "data": summary
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取性能健康摘要失败: {str(e)}")

# 初始化性能监控的启动函数
async def initialize_performance_monitoring():
    """初始化性能监控系统"""
    try:
        await performance_monitor.start()
        logger.info("性能监控系统已初始化")
    except Exception as e:
        logger.error(f"性能监控系统初始化失败: {e}")

# 清理函数
async def cleanup_performance_monitoring():
    """清理性能监控系统"""
    try:
        await performance_monitor.stop()
        await concurrency_optimizer.shutdown()
        logger.info("性能监控系统已清理")
    except Exception as e:
        logger.error(f"性能监控系统清理失败: {e}")