"""
数据库优化API - Database Optimization API
提供数据库性能优化、监控和分析的RESTful API接口
"""

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
import logging

from ..optimization.query_optimizer import get_query_optimizer
from ..optimization.index_manager import get_index_manager
from ..optimization.connection_pool import get_connection_pool_manager
from ..optimization.read_write_split import get_read_write_engine
from ..optimization.database_health import get_health_monitor
from ..core.security import get_current_user, require_admin_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/database-optimization", tags=["database-optimization"])


# 查询优化相关API
@router.get("/query/performance", summary="获取查询性能统计")
async def get_query_performance_stats(
    hours: int = Query(24, description="统计时间范围（小时）", ge=1, le=168),
    limit: int = Query(100, description="返回记录数限制", ge=1, le=1000),
    current_user: dict = Depends(get_current_user)
):
    """获取查询性能统计信息"""
    try:
        optimizer = get_query_optimizer()
        if not optimizer:
            raise HTTPException(status_code=503, detail="Query optimizer not available")

        # 获取性能报告
        performance_report = await optimizer.get_performance_report(hours)

        # 获取慢查询
        slow_queries = await optimizer.get_slow_queries(limit)

        # 获取优化建议
        recommendations = await optimizer.get_optimization_recommendations()

        return {
            "success": True,
            "data": {
                "performance_report": performance_report,
                "slow_queries": slow_queries,
                "recommendations": recommendations,
                "query_history": await optimizer.get_query_history(limit)
            },
            "meta": {
                "hours": hours,
                "limit": limit,
                "generated_at": datetime.utcnow().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get query performance stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance stats: {str(e)}")


@router.post("/query/optimize", summary="执行查询优化")
async def optimize_query(
    query_text: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin_role)
):
    """执行查询优化分析"""
    try:
        optimizer = get_query_optimizer()
        if not optimizer:
            raise HTTPException(status_code=503, detail="Query optimizer not available")

        # 分析查询并生成优化建议
        optimization_result = await optimizer.optimize_query(query_text)

        # 后台任务：记录优化历史
        background_tasks.add_task(
            _record_optimization_history,
            user_id=current_user["id"],
            query_text=query_text,
            result=optimization_result
        )

        return {
            "success": True,
            "data": optimization_result,
            "message": "Query optimization completed successfully"
        }

    except Exception as e:
        logger.error(f"Failed to optimize query: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to optimize query: {str(e)}")


@router.get("/query/slow", summary="获取慢查询列表")
async def get_slow_queries(
    limit: int = Query(50, description="返回记录数限制", ge=1, le=500),
    min_execution_time: float = Query(1000.0, description="最小执行时间（毫秒）", ge=100.0),
    current_user: dict = Depends(get_current_user)
):
    """获取慢查询列表"""
    try:
        optimizer = get_query_optimizer()
        if not optimizer:
            raise HTTPException(status_code=503, detail="Query optimizer not available")

        slow_queries = await optimizer.get_slow_queries(limit, min_execution_time)

        return {
            "success": True,
            "data": {
                "slow_queries": slow_queries,
                "count": len(slow_queries),
                "min_execution_time": min_execution_time
            }
        }

    except Exception as e:
        logger.error(f"Failed to get slow queries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get slow queries: {str(e)}")


# 索引管理相关API
@router.get("/indexes/analysis", summary="获取索引分析报告")
async def get_index_analysis(
    table_name: Optional[str] = Query(None, description="指定表名，不指定则分析所有表"),
    current_user: dict = Depends(get_current_user)
):
    """获取索引分析报告"""
    try:
        index_manager = get_index_manager()
        if not index_manager:
            raise HTTPException(status_code=503, detail="Index manager not available")

        if table_name:
            # 分析单个表
            analysis = await index_manager.analyze_table_indexes(table_name)
        else:
            # 分析所有表
            analysis = await index_manager.analyze_all_indexes()

        return {
            "success": True,
            "data": analysis,
            "meta": {
                "table_name": table_name,
                "analyzed_at": datetime.utcnow().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get index analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get index analysis: {str(e)}")


@router.post("/indexes/recommendations", summary="生成索引优化建议")
async def generate_index_recommendations(
    table_names: Optional[List[str]] = None,
    current_user: dict = Depends(get_current_user)
):
    """生成索引优化建议"""
    try:
        index_manager = get_index_manager()
        if not index_manager:
            raise HTTPException(status_code=503, detail="Index manager not available")

        recommendations = await index_manager.generate_recommendations(table_names)

        return {
            "success": True,
            "data": {
                "recommendations": recommendations,
                "count": len(recommendations),
                "generated_at": datetime.utcnow().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Failed to generate index recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")


@router.post("/indexes/create", summary="创建推荐索引")
async def create_recommended_index(
    table_name: str,
    column_names: List[str],
    index_type: str = "btree",
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin_role)
):
    """创建推荐索引"""
    try:
        index_manager = get_index_manager()
        if not index_manager:
            raise HTTPException(status_code=503, detail="Index manager not available")

        # 创建索引
        result = await index_manager.create_index(table_name, column_names, index_type)

        # 后台任务：记录索引创建历史
        background_tasks.add_task(
            _record_index_creation,
            user_id=current_user["id"],
            table_name=table_name,
            column_names=column_names,
            index_type=index_type,
            result=result
        )

        return {
            "success": True,
            "data": result,
            "message": f"Index created successfully on {table_name}({', '.join(column_names)})"
        }

    except Exception as e:
        logger.error(f"Failed to create index: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create index: {str(e)}")


# 连接池监控相关API
@router.get("/connection-pool/stats", summary="获取连接池统计")
async def get_connection_pool_stats(
    current_user: dict = Depends(get_current_user)
):
    """获取连接池统计信息"""
    try:
        pool_manager = get_connection_pool_manager()
        if not pool_manager:
            raise HTTPException(status_code=503, detail="Connection pool manager not available")

        stats = await pool_manager.get_pool_stats()
        health_status = await pool_manager.get_health_status()

        return {
            "success": True,
            "data": {
                "pool_stats": stats,
                "health_status": health_status,
                "recommendations": await pool_manager.get_optimization_recommendations()
            }
        }

    except Exception as e:
        logger.error(f"Failed to get connection pool stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pool stats: {str(e)}")


@router.post("/connection-pool/optimize", summary="优化连接池配置")
async def optimize_connection_pool(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin_role)
):
    """优化连接池配置"""
    try:
        pool_manager = get_connection_pool_manager()
        if not pool_manager:
            raise HTTPException(status_code=503, detail="Connection pool manager not available")

        # 执行优化
        optimization_result = await pool_manager.optimize_pool_configuration()

        # 后台任务：记录优化历史
        background_tasks.add_task(
            _record_pool_optimization,
            user_id=current_user["id"],
            result=optimization_result
        )

        return {
            "success": True,
            "data": optimization_result,
            "message": "Connection pool optimization completed"
        }

    except Exception as e:
        logger.error(f"Failed to optimize connection pool: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to optimize pool: {str(e)}")


# 读写分离相关API
@router.get("/read-write-split/stats", summary="获取读写分离统计")
async def get_read_write_split_stats(
    current_user: dict = Depends(get_current_user)
):
    """获取读写分离统计信息"""
    try:
        rw_engine = get_read_write_engine()
        if not rw_engine:
            raise HTTPException(status_code=503, detail="Read-write split engine not available")

        system_stats = await rw_engine.get_system_stats()
        query_performance = await rw_engine.get_query_performance()
        performance_analysis = await rw_engine.analyze_performance()

        return {
            "success": True,
            "data": {
                "system_stats": system_stats,
                "query_performance": query_performance,
                "performance_analysis": performance_analysis
            }
        }

    except Exception as e:
        logger.error(f"Failed to get read-write split stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/read-write-split/nodes", summary="获取数据库节点状态")
async def get_database_nodes_status(
    current_user: dict = Depends(get_current_user)
):
    """获取数据库节点状态"""
    try:
        rw_engine = get_read_write_engine()
        if not rw_engine:
            raise HTTPException(status_code=503, detail="Read-write split engine not available")

        # 获取所有节点信息
        all_nodes = [rw_engine.master_node] + rw_engine.replica_nodes + rw_engine.analytics_nodes

        nodes_status = []
        for node in all_nodes:
            stats = rw_engine.load_balance_stats.get(node.id)
            if stats:
                nodes_status.append({
                    "id": node.id,
                    "role": node.role.value,
                    "host": f"{node.host}:{node.port}",
                    "is_available": node.is_available,
                    "response_time": node.response_time,
                    "error_count": node.error_count,
                    "weight": node.weight,
                    "stats": {
                        "request_count": stats.request_count,
                        "avg_response_time": stats.avg_response_time,
                        "current_connections": stats.current_connections,
                        "error_rate": stats.error_rate,
                        "last_used": stats.last_used
                    }
                })

        return {
            "success": True,
            "data": {
                "nodes": nodes_status,
                "total_nodes": len(nodes_status),
                "healthy_nodes": sum(1 for node in nodes_status if node["is_available"]),
                "load_balance_strategy": rw_engine.load_balance_strategy.value
            }
        }

    except Exception as e:
        logger.error(f"Failed to get nodes status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get nodes status: {str(e)}")


# 健康监控相关API
@router.get("/health/summary", summary="获取数据库健康摘要")
async def get_database_health_summary(
    current_user: dict = Depends(get_current_user)
):
    """获取数据库健康状态摘要"""
    try:
        health_monitor = get_health_monitor()
        if not health_monitor:
            raise HTTPException(status_code=503, detail="Health monitor not available")

        summary = await health_monitor.get_health_summary()
        active_alerts = await health_monitor.get_active_alerts()

        return {
            "success": True,
            "data": {
                "summary": summary,
                "active_alerts": active_alerts
            }
        }

    except Exception as e:
        logger.error(f"Failed to get health summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get health summary: {str(e)}")


@router.get("/health/nodes/{node_id}", summary="获取特定节点健康状态")
async def get_node_health_status(
    node_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取特定数据库节点的健康状态"""
    try:
        health_monitor = get_health_monitor()
        if not health_monitor:
            raise HTTPException(status_code=503, detail="Health monitor not available")

        node_health = await health_monitor.get_node_health(node_id)
        if not node_health:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

        return {
            "success": True,
            "data": node_health
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get node health: {str(e)}")


@router.get("/health/metrics/{node_id}/{metric_name}", summary="获取指标历史数据")
async def get_metric_history(
    node_id: str,
    metric_name: str,
    hours: int = Query(24, description="时间范围（小时）", ge=1, le=168),
    current_user: dict = Depends(get_current_user)
):
    """获取特定指标的历史数据"""
    try:
        health_monitor = get_health_monitor()
        if not health_monitor:
            raise HTTPException(status_code=503, detail="Health monitor not available")

        history = await health_monitor.get_metrics_history(node_id, metric_name, hours)

        return {
            "success": True,
            "data": {
                "node_id": node_id,
                "metric_name": metric_name,
                "history": history,
                "hours": hours
            }
        }

    except Exception as e:
        logger.error(f"Failed to get metric history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metric history: {str(e)}")


@router.post("/health/alerts/{alert_id}/resolve", summary="解决告警")
async def resolve_health_alert(
    alert_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin_role)
):
    """解决健康告警"""
    try:
        health_monitor = get_health_monitor()
        if not health_monitor:
            raise HTTPException(status_code=503, detail="Health monitor not available")

        await health_monitor.resolve_alert(alert_id)

        # 后台任务：记录告警解决历史
        background_tasks.add_task(
            _record_alert_resolution,
            user_id=current_user["id"],
            alert_id=alert_id
        )

        return {
            "success": True,
            "message": f"Alert {alert_id} resolved successfully"
        }

    except Exception as e:
        logger.error(f"Failed to resolve alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resolve alert: {str(e)}")


# 综合优化报告API
@router.get("/optimization-report", summary="获取综合优化报告")
async def get_optimization_report(
    hours: int = Query(24, description="分析时间范围（小时）", ge=1, le=168),
    current_user: dict = Depends(get_current_user)
):
    """获取数据库综合优化报告"""
    try:
        # 并发获取各项数据
        tasks = []

        # 查询性能数据
        optimizer = get_query_optimizer()
        if optimizer:
            tasks.append(optimizer.get_performance_report(hours))

        # 索引分析数据
        index_manager = get_index_manager()
        if index_manager:
            tasks.append(index_manager.analyze_all_indexes())

        # 连接池数据
        pool_manager = get_connection_pool_manager()
        if pool_manager:
            tasks.append(pool_manager.get_pool_stats())

        # 读写分离数据
        rw_engine = get_read_write_engine()
        if rw_engine:
            tasks.append(rw_engine.get_system_stats())

        # 健康监控数据
        health_monitor = get_health_monitor()
        if health_monitor:
            tasks.append(health_monitor.get_health_summary())

        # 执行并发任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 组织报告数据
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "analysis_period_hours": hours,
            "sections": {}
        }

        if len(results) > 0 and not isinstance(results[0], Exception):
            report["sections"]["query_performance"] = results[0]

        if len(results) > 1 and not isinstance(results[1], Exception):
            report["sections"]["index_analysis"] = results[1]

        if len(results) > 2 and not isinstance(results[2], Exception):
            report["sections"]["connection_pool"] = results[2]

        if len(results) > 3 and not isinstance(results[3], Exception):
            report["sections"]["read_write_split"] = results[3]

        if len(results) > 4 and not isinstance(results[4], Exception):
            report["sections"]["health_monitoring"] = results[4]

        # 生成综合建议
        report["recommendations"] = _generate_comprehensive_recommendations(report["sections"])

        return {
            "success": True,
            "data": report
        }

    except Exception as e:
        logger.error(f"Failed to generate optimization report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


# 后台任务函数
async def _record_optimization_history(user_id: str, query_text: str, result: Dict[str, Any]):
    """记录查询优化历史"""
    try:
        logger.info(f"Recorded optimization history for user {user_id}")
        # 这里可以保存到数据库或文件
    except Exception as e:
        logger.error(f"Failed to record optimization history: {e}")


async def _record_index_creation(user_id: str, table_name: str, column_names: List[str], index_type: str, result: Dict[str, Any]):
    """记录索引创建历史"""
    try:
        logger.info(f"Recorded index creation for user {user_id}: {table_name}({', '.join(column_names)})")
        # 这里可以保存到数据库或文件
    except Exception as e:
        logger.error(f"Failed to record index creation: {e}")


async def _record_pool_optimization(user_id: str, result: Dict[str, Any]):
    """记录连接池优化历史"""
    try:
        logger.info(f"Recorded pool optimization for user {user_id}")
        # 这里可以保存到数据库或文件
    except Exception as e:
        logger.error(f"Failed to record pool optimization: {e}")


async def _record_alert_resolution(user_id: str, alert_id: str):
    """记录告警解决历史"""
    try:
        logger.info(f"Recorded alert resolution for user {user_id}: {alert_id}")
        # 这里可以保存到数据库或文件
    except Exception as e:
        logger.error(f"Failed to record alert resolution: {e}")


def _generate_comprehensive_recommendations(sections: Dict[str, Any]) -> List[Dict[str, Any]]:
    """生成综合优化建议"""
    recommendations = []

    # 查询性能建议
    if "query_performance" in sections:
        qp_data = sections["query_performance"]
        if qp_data.get("slow_queries_count", 0) > 10:
            recommendations.append({
                "category": "query_performance",
                "priority": "high",
                "title": "慢查询数量过多",
                "description": f"发现 {qp_data['slow_queries_count']} 个慢查询，建议优化SQL语句或添加适当索引",
                "action_items": ["分析慢查询执行计划", "添加缺失的索引", "重写复杂查询"]
            })

    # 索引优化建议
    if "index_analysis" in sections:
        index_data = sections["index_analysis"]
        unused_indexes = index_data.get("unused_indexes", [])
        if len(unused_indexes) > 5:
            recommendations.append({
                "category": "index_optimization",
                "priority": "medium",
                "title": "存在未使用的索引",
                "description": f"发现 {len(unused_indexes)} 个未使用的索引，占用存储空间并影响写入性能",
                "action_items": ["评估索引使用情况", "删除不必要的索引", "优化索引结构"]
            })

    # 连接池建议
    if "connection_pool" in sections:
        pool_data = sections["connection_pool"]
        if pool_data.get("utilization_rate", 0) > 80:
            recommendations.append({
                "category": "connection_pool",
                "priority": "high",
                "title": "连接池使用率过高",
                "description": f"连接池使用率达到 {pool_data['utilization_rate']:.1f}%，可能影响应用性能",
                "action_items": ["增加连接池大小", "优化连接使用", "检查连接泄漏"]
            })

    return recommendations