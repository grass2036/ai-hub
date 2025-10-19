"""
备份恢复API端点
Week 6 Day 6: 备份恢复策略实施

提供完整的备份恢复管理API
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Body
from pydantic import BaseModel, Field

from backend.core.backup.backup_manager import BackupManager, BackupConfig, BackupType, BackupStatus
from backend.core.backup.recovery_manager import RecoveryManager, RecoveryConfig, RecoveryType, RecoveryStatus
from backend.core.backup.scheduler import BackupScheduler, ScheduleConfig
from backend.core.backup.disaster_recovery import DisasterRecoveryManager, DRConfig, DisasterType
from backend.core.backup.storage import StorageFactory

router = APIRouter(prefix="/backup", tags=["backup-recovery"])

# 全局实例
backup_manager: Optional[BackupManager] = None
recovery_manager: Optional[RecoveryManager] = None
backup_scheduler: Optional[BackupScheduler] = None
dr_manager: Optional[DisasterRecoveryManager] = None


def get_backup_manager() -> BackupManager:
    """获取备份管理器实例"""
    global backup_manager
    if backup_manager is None:
        raise HTTPException(status_code=503, detail="Backup manager not initialized")
    return backup_manager


def get_recovery_manager() -> RecoveryManager:
    """获取恢复管理器实例"""
    global recovery_manager
    if recovery_manager is None:
        raise HTTPException(status_code=503, detail="Recovery manager not initialized")
    return recovery_manager


def get_backup_scheduler() -> BackupScheduler:
    """获取备份调度器实例"""
    global backup_scheduler
    if backup_scheduler is None:
        raise HTTPException(status_code=503, detail="Backup scheduler not initialized")
    return backup_scheduler


def get_dr_manager() -> DisasterRecoveryManager:
    """获取灾难恢复管理器实例"""
    global dr_manager
    if dr_manager is None:
        raise HTTPException(status_code=503, detail="Disaster recovery manager not initialized")
    return dr_manager


# 请求/响应模型
class BackupRequest(BaseModel):
    """备份请求"""
    backup_type: str = Field(..., description="备份类型")
    strategy_name: str = Field(..., description="备份策略")
    description: str = Field("", description="备份描述")
    tags: List[str] = Field(default_factory=list, description="备份标签")
    retention_days: int = Field(30, ge=1, le=365, description="保留天数")
    compression: bool = Field(True, description="是否压缩")
    custom_params: Dict[str, Any] = Field(default_factory=dict, description="自定义参数")


class RecoveryRequest(BaseModel):
    """恢复请求"""
    backup_id: str = Field(..., description="备份ID")
    recovery_type: str = Field("full", description="恢复类型")
    target_path: str = Field("./recovery", description="恢复目标路径")
    validate_after_recovery: bool = Field(True, description="恢复后验证")
    create_rollback: bool = Field(True, description="创建回滚点")
    overwrite_existing: bool = Field(False, description="覆盖现有文件")
    custom_params: Dict[str, Any] = Field(default_factory=dict, description="自定义参数")


class ScheduleRequest(BaseModel):
    """调度请求"""
    name: str = Field(..., description="调度名称")
    backup_type: str = Field(..., description="备份类型")
    strategy_name: str = Field(..., description="备份策略")
    cron_expression: str = Field(..., description="Cron表达式")
    retention_days: int = Field(30, ge=1, le=365, description="保留天数")
    description: str = Field("", description="描述")
    enabled: bool = Field(True, description="是否启用")
    custom_params: Dict[str, Any] = Field(default_factory=dict, description="自定义参数")


class DisasterDeclarationRequest(BaseModel):
    """灾难宣告请求"""
    disaster_type: str = Field(..., description="灾难类型")
    severity: str = Field(..., regex="^(low|medium|high|critical)$", description="严重程度")
    description: str = Field(..., description="灾难描述")
    affected_systems: List[str] = Field(default_factory=list, description="受影响系统")


# 备份管理API
@router.post("/create", summary="创建备份")
async def create_backup(
    request: BackupRequest,
    backup_mgr: BackupManager = Depends(get_backup_manager)
):
    """创建新的备份任务"""
    try:
        # 验证备份类型
        backup_type = BackupType(request.backup_type)

        # 创建备份配置
        backup_config = BackupConfig(
            backup_type=backup_type,
            strategy_name=request.strategy_name,
            retention_days=request.retention_days,
            compression=request.compression,
            custom_params=request.custom_params
        )

        # 启动备份任务
        backup_id = await backup_mgr.create_backup(
            backup_config,
            description=request.description,
            tags=request.tags,
            manual=True
        )

        return {
            "success": True,
            "backup_id": backup_id,
            "message": "Backup task created successfully",
            "estimated_duration": "Depends on data size"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create backup: {str(e)}")


@router.get("/status/{backup_id}", summary="获取备份状态")
async def get_backup_status(
    backup_id: str,
    backup_mgr: BackupManager = Depends(get_backup_manager)
):
    """获取备份任务状态"""
    backup_status = await backup_mgr.get_backup_status(backup_id)

    if not backup_status:
        raise HTTPException(status_code=404, detail="Backup not found")

    return {
        "success": True,
        "data": {
            "backup_id": backup_status.backup_id,
            "backup_type": backup_status.backup_type.value,
            "status": backup_status.status.value,
            "created_at": backup_status.created_at.isoformat(),
            "completed_at": backup_status.completed_at.isoformat() if backup_status.completed_at else None,
            "file_size": backup_status.file_size,
            "compressed_size": backup_status.compressed_size,
            "description": backup_status.description,
            "tags": backup_status.tags,
            "error_message": backup_status.error_message
        }
    }


@router.get("/list", summary="列出备份")
async def list_backups(
    backup_type: Optional[str] = Query(None, description="备份类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    backup_mgr: BackupManager = Depends(get_backup_manager)
):
    """列出备份任务"""
    try:
        # 转换过滤参数
        backup_type_enum = BackupType(backup_type) if backup_type else None
        status_enum = BackupStatus(status) if status else None

        backups = await backup_mgr.list_backups(
            backup_type=backup_type_enum,
            status=status_enum,
            limit=limit,
            offset=offset
        )

        backup_list = []
        for backup in backups:
            backup_list.append({
                "backup_id": backup.backup_id,
                "backup_type": backup.backup_type.value,
                "status": backup.status.value,
                "created_at": backup.created_at.isoformat(),
                "completed_at": backup.completed_at.isoformat() if backup.completed_at else None,
                "file_size": backup.file_size,
                "compressed_size": backup.compressed_size,
                "description": backup.description,
                "tags": backup.tags,
                "retention_days": backup.retention_days
            })

        return {
            "success": True,
            "data": backup_list,
            "count": len(backup_list)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")


@router.delete("/{backup_id}", summary="删除备份")
async def delete_backup(
    backup_id: str,
    backup_mgr: BackupManager = Depends(get_backup_manager)
):
    """删除备份"""
    success = await backup_mgr.delete_backup(backup_id)

    if not success:
        raise HTTPException(status_code=404, detail="Backup not found")

    return {
        "success": True,
        "message": f"Backup {backup_id} deleted successfully"
    }


@router.post("/verify/{backup_id}", summary="验证备份")
async def verify_backup(
    backup_id: str,
    backup_mgr: BackupManager = Depends(get_backup_manager)
):
    """验证备份完整性"""
    result = await backup_mgr.verify_backup(backup_id)

    return {
        "success": True,
        "data": result
    }


@router.post("/cleanup", summary="清理过期备份")
async def cleanup_expired_backups(
    backup_mgr: BackupManager = Depends(get_backup_manager)
):
    """清理过期备份"""
    cleaned_count = await backup_mgr.cleanup_expired_backups()

    return {
        "success": True,
        "message": f"Cleaned up {cleaned_count} expired backups",
        "cleaned_count": cleaned_count
    }


# 恢复管理API
@router.post("/recover", summary="创建恢复任务")
async def create_recovery(
    request: RecoveryRequest,
    recovery_mgr: RecoveryManager = Depends(get_recovery_manager)
):
    """创建新的恢复任务"""
    try:
        # 验证恢复类型
        recovery_type = RecoveryType(request.recovery_type)

        # 创建恢复配置
        recovery_config = RecoveryConfig(
            backup_id=request.backup_id,
            recovery_type=recovery_type,
            target_path=request.target_path,
            validate_after_recovery=request.validate_after_recovery,
            create_rollback=request.create_rollback,
            overwrite_existing=request.overwrite_existing,
            custom_params=request.custom_params
        )

        # 启动恢复任务
        recovery_id = await recovery_mgr.create_recovery(
            recovery_config,
            description=f"Recovery from backup {request.backup_id}"
        )

        return {
            "success": True,
            "recovery_id": recovery_id,
            "message": "Recovery task created successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create recovery: {str(e)}")


@router.get("/recover/status/{recovery_id}", summary="获取恢复状态")
async def get_recovery_status(
    recovery_id: str,
    recovery_mgr: RecoveryManager = Depends(get_recovery_manager)
):
    """获取恢复任务状态"""
    recovery_status = await recovery_mgr.get_recovery_status(recovery_id)

    if not recovery_status:
        raise HTTPException(status_code=404, detail="Recovery not found")

    return {
        "success": True,
        "data": {
            "recovery_id": recovery_status.recovery_id,
            "backup_id": recovery_status.backup_id,
            "recovery_type": recovery_status.recovery_type.value,
            "backup_type": recovery_status.backup_type.value,
            "status": recovery_status.status.value,
            "created_at": recovery_status.created_at.isoformat(),
            "completed_at": recovery_status.completed_at.isoformat() if recovery_status.completed_at else None,
            "target_path": recovery_status.target_path,
            "recovered_files": recovery_status.recovered_files,
            "rollback_available": recovery_status.rollback_available,
            "error_message": recovery_status.error_message
        }
    }


@router.post("/recover/rollback/{recovery_id}", summary="回滚恢复")
async def rollback_recovery(
    recovery_id: str,
    recovery_mgr: RecoveryManager = Depends(get_recovery_manager)
):
    """回滚恢复任务"""
    success = await recovery_mgr.rollback_recovery(recovery_id)

    if not success:
        raise HTTPException(status_code=404, detail="Recovery not found or rollback not available")

    return {
        "success": True,
        "message": f"Recovery {recovery_id} rolled back successfully"
    }


@router.delete("/recover/{recovery_id}", summary="取消恢复任务")
async def cancel_recovery(
    recovery_id: str,
    recovery_mgr: RecoveryManager = Depends(get_recovery_manager)
):
    """取消恢复任务"""
    success = await recovery_mgr.cancel_recovery(recovery_id)

    if not success:
        raise HTTPException(status_code=404, detail="Recovery not found or not cancellable")

    return {
        "success": True,
        "message": f"Recovery {recovery_id} cancelled successfully"
    }


# 调度管理API
@router.post("/schedule", summary="创建备份调度")
async def create_schedule(
    request: ScheduleRequest,
    scheduler: BackupScheduler = Depends(get_backup_scheduler)
):
    """创建备份调度任务"""
    try:
        # 验证备份类型
        backup_type = BackupType(request.backup_type)

        # 创建调度配置
        schedule_config = ScheduleConfig(
            name=request.name,
            backup_type=backup_type,
            strategy_name=request.strategy_name,
            cron_expression=request.cron_expression,
            retention_days=request.retention_days,
            description=request.description,
            enabled=request.enabled,
            custom_params=request.custom_params
        )

        # 添加调度
        job_id = await scheduler.add_schedule(schedule_config)

        return {
            "success": True,
            "job_id": job_id,
            "message": "Backup schedule created successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")


@router.get("/schedule/list", summary="列出调度任务")
async def list_schedules(
    enabled_only: bool = Query(False, description="仅显示启用的任务"),
    scheduler: BackupScheduler = Depends(get_backup_scheduler)
):
    """列出备份调度任务"""
    schedules = await scheduler.list_schedules(enabled_only=enabled_only)

    schedule_list = []
    for job in schedules:
        schedule_list.append({
            "job_id": job.job_id,
            "name": job.schedule_config.name,
            "backup_type": job.schedule_config.backup_type.value,
            "cron_expression": job.schedule_config.cron_expression,
            "enabled": job.schedule_config.enabled,
            "next_run": job.next_run.isoformat(),
            "last_run": job.last_run.isoformat() if job.last_run else None,
            "last_status": job.last_status,
            "run_count": job.run_count,
            "success_count": job.success_count,
            "failure_count": job.failure_count,
            "is_running": job.is_running
        })

    return {
        "success": True,
        "data": schedule_list,
        "count": len(schedule_list)
    }


@router.post("/schedule/{job_id}/run", summary="立即运行调度任务")
async def run_schedule_now(
    job_id: str,
    scheduler: BackupScheduler = Depends(get_backup_scheduler)
):
    """立即运行调度任务"""
    backup_id = await scheduler.run_schedule_now(job_id)

    if backup_id is None:
        raise HTTPException(status_code=404, detail="Schedule not found or disabled")

    return {
        "success": True,
        "backup_id": backup_id,
        "message": f"Schedule {job_id} triggered successfully"
    }


@router.put("/schedule/{job_id}/enable", summary="启用调度任务")
async def enable_schedule(
    job_id: str,
    scheduler: BackupScheduler = Depends(get_backup_scheduler)
):
    """启用调度任务"""
    success = await scheduler.enable_schedule(job_id)

    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {
        "success": True,
        "message": f"Schedule {job_id} enabled successfully"
    }


@router.put("/schedule/{job_id}/disable", summary="禁用调度任务")
async def disable_schedule(
    job_id: str,
    scheduler: BackupScheduler = Depends(get_backup_scheduler)
):
    """禁用调度任务"""
    success = await scheduler.disable_schedule(job_id)

    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {
        "success": True,
        "message": f"Schedule {job_id} disabled successfully"
    }


@router.delete("/schedule/{job_id}", summary="删除调度任务")
async def delete_schedule(
    job_id: str,
    scheduler: BackupScheduler = Depends(get_backup_scheduler)
):
    """删除调度任务"""
    success = await scheduler.remove_schedule(job_id)

    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {
        "success": True,
        "message": f"Schedule {job_id} removed successfully"
    }


# 灾难恢复API
@router.post("/disaster/declare", summary="宣告灾难")
async def declare_disaster(
    request: DisasterDeclarationRequest,
    dr_mgr: DisasterRecoveryManager = Depends(get_dr_manager)
):
    """宣告灾难事件"""
    try:
        # 验证灾难类型
        disaster_type = DisasterType(request.disaster_type)

        # 宣告灾难
        event_id = await dr_mgr.declare_disaster(
            disaster_type=disaster_type,
            severity=request.severity,
            description=request.description,
            affected_systems=request.affected_systems
        )

        return {
            "success": True,
            "event_id": event_id,
            "message": "Disaster declared successfully",
            "severity": request.severity
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to declare disaster: {str(e)}")


@router.post("/disaster/{event_id}/recover", summary="启动灾难恢复")
async def initiate_disaster_recovery(
    event_id: str,
    recovery_plan_id: Optional[str] = Query(None, description="恢复计划ID"),
    dr_mgr: DisasterRecoveryManager = Depends(get_dr_manager)
):
    """启动灾难恢复流程"""
    success = await dr_mgr.initiate_recovery(event_id, recovery_plan_id)

    if not success:
        raise HTTPException(status_code=404, detail="Disaster event not found or no recovery plan available")

    return {
        "success": True,
        "message": f"Disaster recovery initiated for event {event_id}"
    }


@router.get("/disaster/status", summary="获取灾难恢复状态")
async def get_disaster_status(dr_mgr: DisasterRecoveryManager = Depends(get_dr_manager)):
    """获取灾难恢复系统状态"""
    status = await dr_mgr.get_disaster_status()

    return {
        "success": True,
        "data": status
    }


@router.get("/disaster/events", summary="获取灾难事件列表")
async def get_disaster_events(
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    dr_mgr: DisasterRecoveryManager = Depends(get_dr_manager)
):
    """获取灾难事件列表"""
    events = await dr_mgr.get_disaster_events(limit)

    event_list = []
    for event in events:
        event_list.append({
            "event_id": event.event_id,
            "disaster_type": event.disaster_type.value,
            "severity": event.severity,
            "description": event.description,
            "detected_at": event.detected_at.isoformat(),
            "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
            "status": event.status.value,
            "affected_systems": event.affected_systems,
            "recovery_actions": event.recovery_actions
        })

    return {
        "success": True,
        "data": event_list,
        "count": len(event_list)
    }


# 统计信息API
@router.get("/statistics", summary="获取备份恢复统计信息")
async def get_statistics(
    backup_mgr: BackupManager = Depends(get_backup_manager),
    recovery_mgr: RecoveryManager = Depends(get_recovery_manager),
    scheduler: BackupScheduler = Depends(get_backup_scheduler),
    dr_mgr: DisasterRecoveryManager = Depends(get_dr_manager)
):
    """获取备份恢复系统统计信息"""
    try:
        backup_stats = await backup_mgr.get_backup_statistics()
        recovery_stats = await recovery_mgr.get_recovery_statistics()
        scheduler_stats = await scheduler.get_scheduler_statistics()
        dr_stats = await dr_mgr.get_disaster_status()

        return {
            "success": True,
            "data": {
                "backup": backup_stats,
                "recovery": recovery_stats,
                "scheduler": scheduler_stats,
                "disaster_recovery": dr_stats,
                "timestamp": datetime.now().isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/health", summary="健康检查")
async def health_check():
    """备份恢复系统健康检查"""
    return {
        "status": "healthy",
        "components": {
            "backup_manager": backup_manager is not None,
            "recovery_manager": recovery_manager is not None,
            "backup_scheduler": backup_scheduler is not None,
            "disaster_recovery": dr_manager is not None
        },
        "timestamp": datetime.now().isoformat()
    }


# 初始化函数
def initialize_backup_system(config: Dict[str, Any]):
    """初始化备份恢复系统"""
    global backup_manager, recovery_manager, backup_scheduler, dr_manager

    try:
        # 创建存储后端
        storage_config = config.get("storage", {})
        storage_type = storage_config.get("type", "local")
        storage = StorageFactory.create_storage(storage_type, storage_config)

        # 创建管理器
        backup_manager = BackupManager(config)
        recovery_manager = RecoveryManager(config)
        backup_scheduler = BackupScheduler(backup_manager)

        dr_config = DRConfig(**config.get("disaster_recovery", {}))
        dr_manager = DisasterRecoveryManager(dr_config)

        # 初始化所有组件
        asyncio.create_task(storage.initialize())
        asyncio.create_task(backup_manager.initialize(storage))
        asyncio.create_task(recovery_manager.initialize(storage))
        asyncio.create_task(backup_scheduler.start())
        asyncio.create_task(dr_manager.initialize(backup_manager, recovery_manager, storage))

        return True

    except Exception as e:
        logging.error(f"Failed to initialize backup system: {str(e)}")
        return False


# 清理函数
async def shutdown_backup_system():
    """关闭备份恢复系统"""
    global backup_manager, recovery_manager, backup_scheduler, dr_manager

    try:
        if backup_scheduler:
            await backup_scheduler.stop()
        if dr_manager:
            await dr_manager.shutdown()
        if recovery_manager:
            await recovery_manager.shutdown()
        if backup_manager:
            await backup_manager.shutdown()

    except Exception as e:
        logging.error(f"Error during backup system shutdown: {str(e)}")