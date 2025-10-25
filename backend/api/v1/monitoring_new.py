"""
监控API端点
提供系统监控、业务指标、性能数据查询接口
"""
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import asyncio

from backend.monitoring.system_monitor import system_monitor, SystemMetrics
from backend.monitoring.business_monitor import business_monitor, BusinessMetric
from backend.core.database import get_db
from backend.core.auth import get_current_user_optional

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

@router.get("/system/info")
async def get_system_info():
    """获取系统基本信息"""
    try:
        info = system_monitor.get_system_info()
        return {
            "success": True,
            "data": info,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system info: {str(e)}")

@router.get("/system/metrics")
async def get_system_metrics(
    hours: int = Query(default=1, ge=1, le=168),  # 1小时到7天
    include_history: bool = Query(default=True)
):
    """获取系统性能指标"""
    try:
        # 获取最新指标
        latest_metrics = system_monitor.get_latest_metrics()

        result = {
            "success": True,
            "current": None,
            "history": [],
            "average": None,
            "period_hours": hours,
            "timestamp": datetime.utcnow().isoformat()
        }

        if latest_metrics:
            result["current"] = {
                "timestamp": latest_metrics.timestamp.isoformat(),
                "host_name": latest_metrics.host_name,
                "cpu": latest_metrics.cpu,
                "memory": latest_metrics.memory,
                "disk": latest_metrics.disk,
                "network": latest_metrics.network,
                "process": latest_metrics.process_info
            }

        # 获取历史数据
        if include_history:
            history = system_monitor.get_metrics_history(hours)
            result["history"] = [
                {
                    "timestamp": metrics.timestamp.isoformat(),
                    "cpu_usage": metrics.cpu["usage_percent"],
                    "memory_usage": metrics.memory["percent"],
                    "disk_usage": metrics.disk["percent"],
                    "network_bytes_sent": metrics.network["bytes_sent"],
                    "network_bytes_recv": metrics.network["bytes_recv"],
                    "process_cpu": metrics.process_info["cpu_percent"],
                    "process_memory": metrics.process_info["memory_percent"]
                }
                for metrics in history
            ]

        # 获取平均指标
        average = system_monitor.get_average_metrics(hours)
        if average:
            result["average"] = average

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system metrics: {str(e)}")

@router.get("/dashboard")
async def get_dashboard_data(
    hours: int = Query(default=1, ge=1, le=24)
):
    """获取仪表板数据"""
    try:
        # 获取基础数据
        latest_metrics = system_monitor.get_latest_metrics()
        api_stats = business_monitor.get_api_stats(hours)
        ai_stats = business_monitor.get_ai_model_stats(hours)
        user_activity = business_monitor.get_user_activity_stats(hours)
        real_time_stats = business_monitor.get_real_time_stats()
        alerts = system_monitor.get_recent_alerts(24)

        # 构建仪表板数据
        dashboard_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "period_hours": hours,

            # 系统概览
            "system_overview": {
                "current": {
                    "cpu_usage": latest_metrics.cpu["usage_percent"] if latest_metrics else 0,
                    "memory_usage": latest_metrics.memory["percent"] if latest_metrics else 0,
                    "disk_usage": latest_metrics.disk["percent"] if latest_metrics else 0,
                    "active_sessions": real_time_stats.get("active_sessions", 0)
                },
                "status": "healthy"
            },

            # API统计
            "api_statistics": api_stats,

            # AI模型统计
            "ai_statistics": ai_stats,

            # 用户活动
            "user_activity": user_activity,

            # 实时指标
            "real_time": real_time_stats,

            # 告警
            "alerts": {
                "recent": alerts[:10],  # 最近10条告警
                "critical_count": len([a for a in alerts if a.get("severity") == "critical"]),
                "warning_count": len([a for a in alerts if a.get("severity") == "warning"])
            },

            # 历史数据用于图表
            "chart_data": {
                "system_metrics": [
                    {
                        "timestamp": metrics.timestamp.isoformat(),
                        "cpu": metrics.cpu["usage_percent"],
                        "memory": metrics.memory["percent"],
                        "disk": metrics.disk["percent"]
                    }
                    for metrics in system_monitor.get_metrics_history(hours)
                ]
            }
        }

        # 计算系统状态
        current = dashboard_data["system_overview"]["current"]
        if (current["cpu_usage"] > 90 or current["memory_usage"] > 90 or current["disk_usage"] > 95):
            dashboard_data["system_overview"]["status"] = "critical"
        elif (current["cpu_usage"] > 80 or current["memory_usage"] > 80 or current["disk_usage"] > 85):
            dashboard_data["system_overview"]["status"] = "warning"

        return {
            "success": True,
            "data": dashboard_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")

@router.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 获取系统指标
        latest_metrics = system_monitor.get_latest_metrics()

        # 检查系统健康状态
        health_status = "healthy"
        issues = []

        if latest_metrics:
            # CPU检查
            if latest_metrics.cpu["usage_percent"] > 90:
                health_status = "critical"
                issues.append(f"High CPU usage: {latest_metrics.cpu['usage_percent']:.1f}%")
            elif latest_metrics.cpu["usage_percent"] > 80:
                if health_status == "healthy":
                    health_status = "warning"
                issues.append(f"Moderate CPU usage: {latest_metrics.cpu['usage_percent']:.1f}%")

            # 内存检查
            if latest_metrics.memory["percent"] > 90:
                health_status = "critical"
                issues.append(f"High memory usage: {latest_metrics.memory['percent']:.1f}%")
            elif latest_metrics.memory["percent"] > 80:
                if health_status == "healthy":
                    health_status = "warning"
                issues.append(f"Moderate memory usage: {latest_metrics.memory['percent']:.1f}%")

            # 磁盘检查
            if latest_metrics.disk["percent"] > 95:
                health_status = "critical"
                issues.append(f"Critical disk usage: {latest_metrics.disk['percent']:.1f}%")
            elif latest_metrics.disk["percent"] > 85:
                if health_status == "healthy":
                    health_status = "warning"
                issues.append(f"High disk usage: {latest_metrics.disk['percent']:.1f}%")

        # 获取实时业务指标
        real_time_stats = business_monitor.get_real_time_stats()

        return {
            "success": True,
            "data": {
                "status": health_status,
                "timestamp": datetime.utcnow().isoformat(),
                "system": {
                    "cpu_usage": latest_metrics.cpu["usage_percent"] if latest_metrics else 0,
                    "memory_usage": latest_metrics.memory["percent"] if latest_metrics else 0,
                    "disk_usage": latest_metrics.disk["percent"] if latest_metrics else 0
                },
                "business": {
                    "active_users": real_time_stats.get("current_active_users", 0),
                    "requests_per_minute": real_time_stats.get("requests_per_minute", 0),
                    "error_rate_percent": real_time_stats.get("error_rate_percent", 0)
                },
                "issues": issues
            }
        }

    except Exception as e:
        return {
            "success": False,
            "data": {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        }

@router.post("/frontend-metrics")
async def receive_frontend_metrics(
    metrics: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """接收前端性能指标"""
    try:
        # 处理前端指标
        metric_type = metrics.get("type", "unknown")
        value = metrics.get("value", 0)
        metadata = metrics.get("metadata", {})

        # 创建业务指标
        business_metric = BusinessMetric(
            id=metadata.get("id", f"frontend_{datetime.utcnow().timestamp()}"),
            name=f"frontend_{metric_type}",
            value=value,
            unit=metadata.get("unit", "ms"),
            timestamp=datetime.utcnow(),
            user_id=metadata.get("user_id"),
            tags={
                "source": "frontend",
                "type": metric_type,
                **metadata.get("tags", {})
            },
            metadata=metadata
        )

        # 添加到业务监控
        business_monitor.add_metric(business_metric)

        return {
            "success": True,
            "message": "Frontend metrics received successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process frontend metrics: {str(e)}")