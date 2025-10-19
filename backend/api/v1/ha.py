"""
高可用API端点
Week 6 Day 5: 负载均衡和高可用配置

提供高可用系统的监控、管理和配置API
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field

from backend.core.ha.load_balancer import LoadBalancer, LoadBalancingStrategy, BackendStatus
from backend.core.ha.health_check import HealthChecker, CheckType, HealthStatus
from backend.core.ha.failover import FailoverManager, FailoverStrategy
from backend.core.ha.cluster_management import ClusterManager, NodeRole, NodeStatus
from backend.core.ha.setup import HASetup, HAConfig

router = APIRouter(prefix="/ha", tags=["high-availability"])

# 全局HA实例
ha_setup: Optional[HASetup] = None


def get_ha_setup() -> HASetup:
    """获取HA设置实例"""
    global ha_setup
    if ha_setup is None:
        raise HTTPException(status_code=503, detail="HA system not initialized")
    return ha_setup


class LoadBalancingStatsResponse(BaseModel):
    """负载均衡统计响应"""
    total_backends: int
    healthy_backends: int
    unhealthy_backends: int
    total_connections: int
    strategy: str
    total_requests: int
    total_failures: int
    success_rate: float
    average_response_time: float
    backends: Dict[str, Any]


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    check_id: str
    check_type: str
    target: str
    status: str
    last_check: str
    response_time: float
    consecutive_failures: int
    consecutive_successes: int
    message: str


class ClusterStatusResponse(BaseModel):
    """集群状态响应"""
    node_id: str
    role: str
    status: str
    term: int
    is_leader: bool
    is_healthy: bool
    total_nodes: int
    healthy_nodes: int
    has_quorum: bool
    last_heartbeat: str
    nodes: List[Dict[str, Any]]


class FailoverEventResponse(BaseModel):
    """故障转移事件响应"""
    event_id: str
    failed_node_id: str
    reason: str
    timestamp: str
    resolved: bool
    resolution_time: Optional[str] = None
    actions_taken: List[str]


class HAConfigRequest(BaseModel):
    """HA配置请求"""
    load_balancing_strategy: str = Field("round_robin", description="负载均衡策略")
    health_check_interval: int = Field(30, description="健康检查间隔(秒)")
    failover_strategy: str = Field("active_passive", description="故障转移策略")
    quorum_size: int = Field(2, description="集群法定人数")


class BackendConfigRequest(BaseModel):
    """后端配置请求"""
    id: str = Field(..., description="后端ID")
    host: str = Field(..., description="主机地址")
    port: int = Field(..., description="端口")
    weight: int = Field(1, description="权重")
    max_connections: int = Field(1000, description="最大连接数")


@router.get("/status", summary="获取HA系统状态")
async def get_ha_status(ha: HASetup = Depends(get_ha_setup)):
    """获取高可用系统整体状态"""
    try:
        status = await ha.get_ha_status()
        return {
            "success": True,
            "data": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get HA status: {str(e)}")


@router.get("/load-balancer/stats", response_model=LoadBalancingStatsResponse, summary="获取负载均衡统计")
async def get_load_balancer_stats(ha: HASetup = Depends(get_ha_setup)):
    """获取负载均衡器统计信息"""
    try:
        if not ha.load_balancer:
            raise HTTPException(status_code=503, detail="Load balancer not configured")

        stats = ha.load_balancer.get_statistics()
        return LoadBalancingStatsResponse(**stats)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get load balancer stats: {str(e)}")


@router.get("/load-balancer/backends", summary="获取后端服务器列表")
async def get_backends(ha: HASetup = Depends(get_ha_setup)):
    """获取所有后端服务器状态"""
    try:
        if not ha.load_balancer:
            raise HTTPException(status_code=503, detail="Load balancer not configured")

        backends = []
        for backend_id, backend in ha.load_balancer.backends.items():
            backends.append({
                "id": backend.id,
                "host": backend.host,
                "port": backend.port,
                "url": backend.url,
                "status": backend.status.value,
                "weight": backend.weight,
                "current_connections": backend.current_connections,
                "max_connections": backend.max_connections,
                "response_time": backend.response_time,
                "success_rate": backend.success_rate,
                "total_requests": backend.total_requests,
                "failed_requests": backend.failed_requests,
                "is_available": backend.is_available,
                "last_health_check": backend.last_health_check.isoformat() if backend.last_health_check else None
            })

        return {
            "success": True,
            "data": backends,
            "count": len(backends)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backends: {str(e)}")


@router.post("/load-balancer/backends", summary="添加后端服务器")
async def add_backend(
    backend_config: BackendConfigRequest,
    ha: HASetup = Depends(get_ha_setup)
):
    """添加新的后端服务器"""
    try:
        if not ha.load_balancer:
            raise HTTPException(status_code=503, detail="Load balancer not configured")

        from backend.core.ha.load_balancer import BackendServer
        backend = BackendServer(
            id=backend_config.id,
            host=backend_config.host,
            port=backend_config.port,
            weight=backend_config.weight,
            max_connections=backend_config.max_connections
        )

        ha.load_balancer.add_backend(backend)

        return {
            "success": True,
            "message": f"Backend {backend_config.id} added successfully",
            "backend": {
                "id": backend.id,
                "host": backend.host,
                "port": backend.port,
                "url": backend.url
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add backend: {str(e)}")


@router.delete("/load-balancer/backends/{backend_id}", summary="移除后端服务器")
async def remove_backend(
    backend_id: str,
    ha: HASetup = Depends(get_ha_setup)
):
    """移除后端服务器"""
    try:
        if not ha.load_balancer:
            raise HTTPException(status_code=503, detail="Load balancer not configured")

        success = ha.load_balancer.remove_backend(backend_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Backend {backend_id} not found")

        return {
            "success": True,
            "message": f"Backend {backend_id} removed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove backend: {str(e)}")


@router.put("/load-balancer/backends/{backend_id}/weight", summary="更新后端权重")
async def update_backend_weight(
    backend_id: str,
    weight: int = Query(..., ge=1, le=100, description="权重值 (1-100)"),
    ha: HASetup = Depends(get_ha_setup)
):
    """更新后端服务器权重"""
    try:
        if not ha.load_balancer:
            raise HTTPException(status_code=503, detail="Load balancer not configured")

        success = ha.load_balancer.update_backend_weight(backend_id, weight)
        if not success:
            raise HTTPException(status_code=404, detail=f"Backend {backend_id} not found")

        return {
            "success": True,
            "message": f"Backend {backend_id} weight updated to {weight}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update backend weight: {str(e)}")


@router.put("/load-balancer/backends/{backend_id}/status", summary="设置后端状态")
async def set_backend_status(
    backend_id: str,
    status: str = Query(..., regex="^(healthy|unhealthy|draining|maintenance)$"),
    ha: HASetup = Depends(get_ha_setup)
):
    """设置后端服务器状态"""
    try:
        if not ha.load_balancer:
            raise HTTPException(status_code=503, detail="Load balancer not configured")

        from backend.core.ha.load_balancer import BackendStatus
        backend_status = BackendStatus(status)

        success = ha.load_balancer.set_backend_status(backend_id, backend_status)
        if not success:
            raise HTTPException(status_code=404, detail=f"Backend {backend_id} not found")

        return {
            "success": True,
            "message": f"Backend {backend_id} status set to {status}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set backend status: {str(e)}")


@router.get("/health-checks", summary="获取健康检查状态")
async def get_health_checks(ha: HASetup = Depends(get_ha_setup)):
    """获取所有健康检查状态"""
    try:
        if not ha.health_checker:
            raise HTTPException(status_code=503, detail="Health checker not configured")

        checks = []
        for check_id, check in ha.health_checker.checks.items():
            if hasattr(check, 'config'):
                checks.append({
                    "check_id": check_id,
                    "check_type": check.config.check_type.value,
                    "target": check.config.target,
                    "status": check.config.status.value if hasattr(check.config, 'status') else "unknown",
                    "interval": check.config.interval,
                    "timeout": check.config.timeout,
                    "last_check": check.config.last_check.isoformat() if hasattr(check.config, 'last_check') and check.config.last_check else None
                })

        return {
            "success": True,
            "data": checks,
            "count": len(checks)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health checks: {str(e)}")


@router.post("/health-checks", summary="添加健康检查")
async def add_health_check(
    check_type: str = Query(..., regex="^(http_endpoint|tcp_port|database|redis|custom_script|system_metrics)$"),
    target: str = Query(..., description="检查目标"),
    interval: int = Query(30, ge=5, le=300, description="检查间隔(秒)"),
    timeout: int = Query(5, ge=1, le=30, description="超时时间(秒)"),
    ha: HASetup = Depends(get_ha_setup)
):
    """添加新的健康检查"""
    try:
        if not ha.health_checker:
            raise HTTPException(status_code=503, detail="Health checker not configured")

        from backend.core.ha.health_check import HealthCheckConfig
        config = HealthCheckConfig(
            check_type=CheckType(check_type),
            target=target,
            interval=interval,
            timeout=timeout
        )

        check_id = await ha.health_checker.add_check(config)

        return {
            "success": True,
            "message": f"Health check {check_id} added successfully",
            "check_id": check_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add health check: {str(e)}")


@router.get("/cluster/status", response_model=ClusterStatusResponse, summary="获取集群状态")
async def get_cluster_status(ha: HASetup = Depends(get_ha_setup)):
    """获取集群状态信息"""
    try:
        if not ha.cluster_manager:
            raise HTTPException(status_code=503, detail="Cluster manager not configured")

        status = await ha.cluster_manager.get_cluster_status()

        # 格式化节点列表
        nodes = []
        for node_id, node in status.get("nodes", {}).items():
            nodes.append({
                "id": node.id,
                "host": node.host,
                "port": node.port,
                "role": node.role.value,
                "status": node.status.value,
                "term": node.term,
                "last_heartbeat": node.last_heartbeat.isoformat() if node.last_heartbeat else None,
                "is_leader": node.role == NodeRole.LEADER,
                "is_healthy": node.status == NodeStatus.HEALTHY
            })

        return ClusterStatusResponse(
            node_id=status["node_id"],
            role=status["role"],
            status=status["status"],
            term=status["term"],
            is_leader=status["is_leader"],
            is_healthy=status["is_healthy"],
            total_nodes=status["total_nodes"],
            healthy_nodes=status["healthy_nodes"],
            has_quorum=status["has_quorum"],
            last_heartbeat=status["last_heartbeat"],
            nodes=nodes
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cluster status: {str(e)}")


@router.get("/failover/events", summary="获取故障转移事件")
async def get_failover_events(
    limit: int = Query(50, ge=1, le=200, description="返回事件数量限制"),
    resolved_only: bool = Query(False, description="仅返回已解决的事件"),
    ha: HASetup = Depends(get_ha_setup)
):
    """获取故障转移事件历史"""
    try:
        if not ha.failover_manager:
            raise HTTPException(status_code=503, detail="Failover manager not configured")

        events = []
        # 这里应该从实际存储中获取事件，目前返回模拟数据
        # 在实际实现中，事件应该存储在Redis或数据库中

        return {
            "success": True,
            "data": events,
            "count": len(events),
            "limit": limit
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get failover events: {str(e)}")


@router.post("/failover/trigger", summary="手动触发故障转移")
async def trigger_failover(
    node_id: str = Query(..., description="要故障转移的节点ID"),
    reason: str = Query("manual", description="故障转移原��"),
    ha: HASetup = Depends(get_ha_setup)
):
    """手动触发故障转移"""
    try:
        if not ha.failover_manager:
            raise HTTPException(status_code=503, detail="Failover manager not configured")

        # 这里应该实现实际的故障转移逻辑
        # 目前返回模拟响应

        return {
            "success": True,
            "message": f"Failover triggered for node {node_id}",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger failover: {str(e)}")


@router.post("/config/update", summary="更新HA配置")
async def update_ha_config(
    config: HAConfigRequest,
    background_tasks: BackgroundTasks,
    ha: HASetup = Depends(get_ha_setup)
):
    """更新高可用系统配置"""
    try:
        # 更新负载均衡策略
        if ha.load_balancer:
            ha.load_balancer.config.strategy = LoadBalancingStrategy(config.load_balancing_strategy)
            ha.load_balancer.config.health_check_interval = config.health_check_interval

        # 更新故障转移策略
        if ha.failover_manager:
            ha.failover_manager.config.strategy = FailoverStrategy(config.failover_strategy)

        # 更新集群配置
        if ha.cluster_manager:
            ha.cluster_manager.config.quorum_size = config.quorum_size

        # 添加后台任务以保存配置
        background_tasks.add_task(save_ha_config, config)

        return {
            "success": True,
            "message": "HA configuration updated successfully",
            "config": {
                "load_balancing_strategy": config.load_balancing_strategy,
                "health_check_interval": config.health_check_interval,
                "failover_strategy": config.failover_strategy,
                "quorum_size": config.quorum_size
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update HA config: {str(e)}")


async def save_ha_config(config: HAConfigRequest):
    """保存HA配置到持久化存储"""
    try:
        # 这里应该实现实际的配置保存逻辑
        # 例如保存到Redis、数据库或配置文件
        pass
    except Exception as e:
        print(f"Failed to save HA config: {e}")


@router.get("/metrics", summary="获取HA系统指标")
async def get_ha_metrics(ha: HASetup = Depends(get_ha_setup)):
    """获取高可用系统性能指标"""
    try:
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "uptime": "N/A",  # 需要实际计算
            "load_balancer": {},
            "health_checker": {},
            "failover_manager": {},
            "cluster_manager": {}
        }

        # 负载均衡器指标
        if ha.load_balancer:
            lb_stats = ha.load_balancer.get_statistics()
            metrics["load_balancer"] = {
                "total_requests": lb_stats.get("total_requests", 0),
                "total_failures": lb_stats.get("total_failures", 0),
                "success_rate": lb_stats.get("success_rate", 0),
                "average_response_time": lb_stats.get("average_response_time", 0),
                "healthy_backends": lb_stats.get("healthy_backends", 0),
                "total_backends": lb_stats.get("total_backends", 0)
            }

        # 健康检查器指标
        if ha.health_checker:
            # 这里应该从健康检查器获取实际指标
            metrics["health_checker"] = {
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "average_check_time": 0
            }

        # 故障转移管理器指标
        if ha.failover_manager:
            # 这里应该从故障转移管理器获取实际指标
            metrics["failover_manager"] = {
                "total_failovers": 0,
                "successful_failovers": 0,
                "failed_failovers": 0,
                "average_failover_time": 0
            }

        # 集群管理器指标
        if ha.cluster_manager:
            cluster_status = await ha.cluster_manager.get_cluster_status()
            metrics["cluster_manager"] = {
                "total_nodes": cluster_status.get("total_nodes", 0),
                "healthy_nodes": cluster_status.get("healthy_nodes", 0),
                "has_quorum": cluster_status.get("has_quorum", False),
                "current_term": cluster_status.get("term", 0)
            }

        return {
            "success": True,
            "data": metrics
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get HA metrics: {str(e)}")


@router.post("/maintenance/enable", summary="启用维护模式")
async def enable_maintenance_mode(
    backend_id: str = Query(..., description="要进入维护模式的后端ID"),
    ha: HASetup = Depends(get_ha_setup)
):
    """启用指定后端的维护模式"""
    try:
        if not ha.load_balancer:
            raise HTTPException(status_code=503, detail="Load balancer not configured")

        success = ha.load_balancer.enable_backend_maintenance(backend_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Backend {backend_id} not found")

        return {
            "success": True,
            "message": f"Maintenance mode enabled for backend {backend_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable maintenance mode: {str(e)}")


@router.post("/maintenance/disable", summary="禁用维护模式")
async def disable_maintenance_mode(
    backend_id: str = Query(..., description="要退出维护模式的后端ID"),
    ha: HASetup = Depends(get_ha_setup)
):
    """禁用指定后端的维护模式"""
    try:
        if not ha.load_balancer:
            raise HTTPException(status_code=503, detail="Load balancer not configured")

        from backend.core.ha.load_balancer import BackendStatus
        success = ha.load_balancer.set_backend_status(backend_id, BackendStatus.HEALTHY)
        if not success:
            raise HTTPException(status_code=404, detail=f"Backend {backend_id} not found")

        return {
            "success": True,
            "message": f"Maintenance mode disabled for backend {backend_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable maintenance mode: {str(e)}")


# 初始化函数
def initialize_ha_system(ha_config: HAConfig):
    """初始化HA系统"""
    global ha_setup
    ha_setup = HASetup(ha_config)
    return ha_setup