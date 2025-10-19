"""
高级运维功能API
Week 5 Day 5: 系统监控和运维增强 - 运维API
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from backend.monitoring.distributed_tracing import distributed_tracing
from backend.core.logging.advanced_logging import advanced_log_manager
from backend.health.deep_health_checker import deep_health_checker
from backend.operations.automation_engine import automation_engine, AutomationStatus, TriggerType, ActionType

router = APIRouter()


# 请求/响应模型
class TraceSearchRequest(BaseModel):
    """追踪搜索请求"""
    service_name: Optional[str] = None
    operation_name: Optional[str] = None
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    min_duration_ms: Optional[float] = None
    max_duration_ms: Optional[float] = None
    limit: int = 100


class LogSearchRequest(BaseModel):
    """日志搜索请求"""
    query: Optional[str] = None
    level: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    trace_id: Optional[str] = None
    limit: int = 100


class AutomationRuleRequest(BaseModel):
    """自动化规则请求"""
    name: str
    description: str
    triggers: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    enabled: bool = True


class HealthCheckRequest(BaseModel):
    """健康检查请求"""
    check_type: Optional[str] = None
    component_id: Optional[str] = None
    force_execution: bool = False


# 分布式追踪API
@router.get("/traces")
async def get_traces(request: TraceSearchRequest):
    """获取分布式追踪数据"""
    try:
        traces = await distributed_tracing.search_traces(
            service_name=request.service_name,
            operation_name=request.operation_name,
            status=request.status,
            start_time=request.start_time,
            end_time=request.end_time,
            min_duration_ms=request.min_duration_ms,
            max_duration_ms=request.max_duration_ms,
            limit=request.limit
        )

        return {
            "success": True,
            "data": traces,
            "total": len(traces)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get traces: {str(e)}")


@router.get("/traces/{trace_id}")
async def get_trace_details(trace_id: str):
    """获取特定追踪详情"""
    try:
        trace = await distributed_tracing.get_trace(trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")

        return {
            "success": True,
            "data": trace
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trace details: {str(e)}")


@router.get("/traces/statistics")
async def get_trace_statistics(hours: int = Query(24, ge=1, le=168)):
    """获取追踪统计"""
    try:
        stats = await distributed_tracing.get_service_statistics(hours)
        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trace statistics: {str(e)}")


# 高级日志分析API
@router.post("/logs/search")
async def search_logs(request: LogSearchRequest):
    """搜索日志"""
    try:
        manager = await advanced_log_manager
        logs = await manager.search_logs(
            query=request.query,
            level=request.level,
            category=request.category,
            source=request.source,
            start_time=request.start_time,
            end_time=request.end_time,
            trace_id=request.trace_id,
            limit=request.limit
        )

        return {
            "success": True,
            "data": [log.to_dict() for log in logs],
            "total": len(logs)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search logs: {str(e)}")


@router.get("/logs/anomalies")
async def get_log_anomalies(
    unresolved_only: bool = Query(True, description="仅显示未解决的异常"),
    anomaly_type: Optional[str] = Query(None, description="异常类型"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制")
):
    """获取日志异常"""
    try:
        manager = await advanced_log_manager
        anomalies = await manager.get_log_anomalies(
            unresolved_only=unresolved_only,
            anomaly_type=anomaly_type,
            limit=limit
        )

        return {
            "success": True,
            "data": [anomaly.to_dict() for anomaly in anomalies],
            "total": len(anomalies)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get log anomalies: {str(e)}")


@router.post("/logs/anomalies/{anomaly_id}/resolve")
async def resolve_log_anomaly(anomaly_id: str):
    """解决日志异常"""
    try:
        manager = await advanced_log_manager
        success = await manager.resolve_anomaly(anomaly_id)

        if success:
            return {
                "success": True,
                "message": "Anomaly resolved successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Anomaly not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve anomaly: {str(e)}")


@router.get("/logs/statistics")
async def get_log_statistics(
    hours: int = Query(24, ge=1, le=168, description="时间范围（小时）"),
    category: Optional[str] = Query(None, description="日志分类")
):
    """获取日志统计"""
    try:
        manager = await advanced_log_manager
        stats = await manager.get_log_statistics(hours, category)
        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get log statistics: {str(e)}")


@router.get("/logs/aggregations")
async def get_log_aggregations(
    time_window: str = Query("5m", description="时间窗口"),
    category: Optional[str] = Query(None, description="日志分类"),
    hours: int = Query(24, ge=1, le=168, description="时间范围（小时）")
):
    """获取日志聚合"""
    try:
        manager = await advanced_log_manager
        from backend.core.logging.advanced_logging import LogCategory

        cat = None
        if category:
            try:
                cat = LogCategory(category)
            except ValueError:
                pass

        aggregations = await manager.aggregate_logs(time_window, cat, hours)
        return {
            "success": True,
            "data": [agg.to_dict() for agg in aggregations],
            "total": len(aggregations)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get log aggregations: {str(e)}")


@router.post("/logs/export")
async def export_logs(
    format: str = Query("json", description="导出格式"),
    filters: Optional[str] = Query(None, description="过滤条件（JSON格式）")
):
    """导出日志"""
    try:
        manager = await advanced_log_manager

        # 解析过滤条件
        filter_dict = {}
        if filters:
            import json
            try:
                filter_dict = json.loads(filters)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON in filters")

        exported_data = await manager.export_logs(format, filter_dict)

        # 设置响应头
        from fastapi.responses import Response
        media_type = "application/json" if format == "json" else "text/csv"
        filename = f"logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}"

        return Response(
            content=exported_data,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export logs: {str(e)}")


# 深度健康检查API
@router.get("/health/checks")
async def get_health_checks(
    check_type: Optional[str] = Query(None, description="检查类型"),
    component_id: Optional[str] = Query(None, description="组件ID")
):
    """获取深度健康检查结果"""
    try:
        from backend.health.deep_health_checker import CheckType

        check = None
        if check_type:
            try:
                check = CheckType(check_type)
            except ValueError:
                pass

        results = await deep_health_checker.run_all_checks(check)

        if component_id:
            results = {k: v for k, v in results.items() if k == component_id}

        return {
            "success": True,
            "data": [result.to_dict() for result in results.values()],
            "summary": {
                "total": len(results),
                "healthy": len([r for r in results.values() if r.is_healthy]),
                "unhealthy": len([r for r in results.values() if not r.is_healthy])
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health checks: {str(e)}")


@router.post("/health/checks/{check_id}")
async def run_specific_health_check(check_id: str, request: HealthCheckRequest):
    """运行特定的健康检查"""
    try:
        result = await deep_health_checker.run_check(check_id)
        if not result:
            raise HTTPException(status_code=404, detail="Health check not found")

        return {
            "success": True,
            "data": result.to_dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run health check: {str(e)}")


@router.get("/health/overview")
async def get_overall_health():
    """获取整体健康状态"""
    try:
        overall_health = await deep_health_checker.get_overall_health()
        return {
            "success": True,
            "data": overall_health
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get overall health: {str(e)}")


@router.get("/health/history")
async def get_health_history(
    hours: int = Query(24, ge=1, le=168, description="时间范围（小时）"),
    check_id: Optional[str] = Query(None, description="检查ID")
):
    """获取健康检查历史"""
    try:
        history = await deep_health_checker.get_health_history(hours, check_id)
        return {
            "success": True,
            "data": history,
            "total": len(history)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health history: {str(e)}")


@router.get("/health/components/{component_id}")
async def get_component_health(component_id: str):
    """获取组件健康状态"""
    try:
        component = await deep_health_checker.get_component_health(component_id)
        if not component:
            raise HTTPException(status_code=404, detail="Component not found")

        return {
            "success": True,
            "data": component
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get component health: {str(e)}")


# 自动化运维API
@router.get("/automation/rules")
async def get_automation_rules():
    """获取自动化规则列表"""
    try:
        rules = [rule.to_dict() for rule in automation_engine.rules]
        return {
            "success": True,
            "data": rules,
            "total": len(rules)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get automation rules: {str(e)}")


@router.post("/automation/rules")
async def create_automation_rule(request: AutomationRuleRequest):
    """创建自动化规则"""
    try:
        from backend.operations.automation_engine import AutomationRule, Trigger, Action
        import uuid

        # 创建触发器
        triggers = []
        for trigger_data in request.triggers:
            trigger = Trigger(
                trigger_id=str(uuid.uuid4()),
                name=trigger_data["name"],
                description=trigger_data.get("description", ""),
                trigger_type=TriggerType(trigger_data["trigger_type"]),
                condition=trigger_data["condition"],
                enabled=trigger_data.get("enabled", True),
                cooldown_seconds=trigger_data.get("cooldown_seconds", 300)
            )
            triggers.append(trigger)

        # 创建动作
        actions = []
        for action_data in request.actions:
            action = Action(
                action_id=str(uuid.uuid4()),
                name=action_data["name"],
                description=action_data.get("description", ""),
                action_type=ActionType(action_data["action_type"]),
                parameters=action_data["parameters"],
                timeout_seconds=action_data.get("timeout_seconds", 300),
                max_retries=action_data.get("max_retries", 3),
                enabled=action_data.get("enabled", True)
            )
            actions.append(action)

        # 创建规则
        rule = AutomationRule(
            rule_id=str(uuid.uuid4()),
            name=request.name,
            description=request.description,
            triggers=triggers,
            actions=actions,
            enabled=request.enabled
        )

        automation_engine.add_rule(rule)

        return {
            "success": True,
            "data": {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "message": "Automation rule created successfully"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create automation rule: {str(e)}")


@router.delete("/automation/rules/{rule_id}")
async def delete_automation_rule(rule_id: str):
    """删除自动化规则"""
    try:
        success = automation_engine.remove_rule(rule_id)
        if success:
            return {
                "success": True,
                "message": "Automation rule deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Rule not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete automation rule: {str(e)}")


@router.post("/automation/rules/{rule_id}/enable")
async def enable_automation_rule(rule_id: str, enabled: bool = True):
    """启用/禁用自动化规则"""
    try:
        success = automation_engine.enable_rule(rule_id, enabled)
        if success:
            return {
                "success": True,
                "message": f"Rule {'enabled' if enabled else 'disabled'} successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Rule not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable/disable rule: {str(e)}")


@router.get("/automation/executions")
async def get_automation_executions(
    rule_id: Optional[str] = Query(None, description="规则ID"),
    status: Optional[str] = Query(None, description="执行状态"),
    hours: int = Query(24, ge=1, le=168, description="时间范围（小时）")
):
    """获取自动化执行历史"""
    try:
        status_enum = None
        if status:
            try:
                status_enum = AutomationStatus(status)
            except ValueError:
                pass

        executions = await automation_engine.get_rule_executions(
            rule_id=rule_id,
            status=status_enum,
            hours=hours
        )

        return {
            "success": True,
            "data": [execution.to_dict() for execution in executions],
            "total": len(executions)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get automation executions: {str(e)}")


@router.get("/automation/statistics")
async def get_automation_statistics():
    """获取自动化统计"""
    try:
        stats = automation_engine.get_rule_statistics()
        return {
            "success": True,
            "data": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get automation statistics: {str(e)}")


@router.post("/automation/evaluate-triggers")
async def evaluate_triggers():
    """评估触发器（手动触发）"""
    try:
        # 收集系统上下文
        context = await automation_engine._collect_system_context()

        # 评估触发器
        triggered_rules = await automation_engine.evaluate_triggers(context)

        return {
            "success": True,
            "data": {
                "triggered_rules": triggered_rules,
                "context": context,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate triggers: {str(e)}")


# 综合监控仪表板API
@router.get("/dashboard/overview")
async def get_monitoring_dashboard():
    """获取综合监控仪表板数据"""
    try:
        # 收集所有监控数据
        health_overview = await deep_health_checker.get_overall_health()

        # 日志统计
        manager = await advanced_log_manager
        log_stats = await manager.get_log_statistics(hours=1)

        # 自动化统计
        automation_stats = automation_engine.get_rule_statistics()

        # 追踪统计
        trace_stats = await distributed_tracing.get_service_statistics(1)

        # 综合统计
        total_checks = len(health_overview.get("components", {}))
        healthy_checks = len([
            c for c in health_overview.get("components", {}).values()
            if c.get("status") == "healthy"
        ])

        total_anomalies = log_stats.get("anomaly_statistics", {}).get("total_anomalies", 0)
        unresolved_anomalies = log_stats.get("anomaly_statistics", {}).get("unresolved_anomalies", 0)

        total_rules = automation_stats.get("total_rules", 0)
        enabled_rules = automation_stats.get("enabled_rules", 0)

        dashboard_data = {
            "health": {
                "overall_status": health_overview.get("status"),
                "total_components": total_checks,
                "healthy_components": healthy_checks,
                "unhealthy_components": total_checks - healthy_checks,
                "overall_success_rate": health_overview.get("summary", {}).get("overall_success_rate", 0),
                "avg_response_time": health_overview.get("summary", {}).get("avg_response_time", 0)
            },
            "logs": {
                "total_logs": log_stats.get("total_logs", 0),
                "error_rate": log_stats.get("error_rate", 0),
                "total_anomalies": total_anomalies,
                "unresolved_anomalies": unresolved_anomalies,
                "by_level": log_stats.get("level_distribution", {}),
                "by_category": log_stats.get("category_distribution", {})
            },
            "automation": {
                "total_rules": total_rules,
                "enabled_rules": enabled_rules,
                "rule_statistics": automation_stats.get("rule_statistics", []),
                "total_executions": automation_stats.get("total_executions", 0)
            },
            "traces": {
                "total_traces": trace_stats.get("total_traces", 0),
                "avg_duration": trace_stats.get("avg_duration_ms", 0),
                "error_rate": trace_stats.get("error_rate", 0),
                "services": list(trace_stats.get("services", {}).keys())
            },
            "last_updated": datetime.utcnow().isoformat()
        }

        return {
            "success": True,
            "data": dashboard_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")


@router.get("/system/health")
async def get_system_health():
    """获取系统健康状态"""
    try:
        # 检查各子系统状态
        system_health = {
            "tracing_system": "healthy",
            "logging_system": "healthy",
            "health_checker": "healthy",
            "automation_engine": "healthy",
            "issues": [],
            "last_check": datetime.utcnow().isoformat()
        }

        # 检查分布式追踪
        try:
            trace_stats = await distributed_tracing.get_service_statistics(1)
            if trace_stats.get("total_traces", 0) == 0:
                system_health["tracing_system"] = "warning"
                system_health["issues"].append("No traces collected in the last hour")
        except Exception as e:
            system_health["tracing_system"] = "error"
            system_health["issues"].append(f"Tracing system error: {str(e)}")

        # 检查日志系统
        try:
            log_stats = await manager.get_log_statistics(1) if 'manager' in locals() else {}
            if log_stats.get("total_logs", 0) == 0:
                system_health["logging_system"] = "warning"
                system_health["issues"].append("No logs collected in the last hour")
        except Exception as e:
            system_health["logging_system"] = "error"
            system_health["issues"].append(f"Logging system error: {str(e)}")

        # 检查自动化引擎
        try:
            rules = automation_engine.rules
            if len(rules) == 0:
                system_health["automation_engine"] = "warning"
                system_health["issues"].append("No automation rules configured")
        except Exception as e:
            system_health["automation_engine"] = "error"
            system_health["issues"].append(f"Automation engine error: {str(e)}")

        # 确定整体状态
        if "error" in system_health.values():
            overall_status = "unhealthy"
        elif "warning" in system_health.values():
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        system_health["overall_status"] = overall_status

        return {
            "success": True,
            "data": system_health
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")


# 导入缺失的模块
from backend.core.logging.advanced_logging import advanced_log_manager
from backend.health.deep_health_checker import deep_health_checker
from backend.monitoring.distributed_tracing import distributed_tracing
from backend.operations.automation_engine import automation_engine
from backend.operations.automation_engine import AutomationRule, Trigger, Action
from backend.operations.automation_engine import TriggerType, ActionType
from backend.health.deep_health_checker import CheckType
from backend.monitoring.distributed_tracing import SpanStatus