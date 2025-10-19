"""
Batch Processing API Routes
Week 4 Day 25: Batch Processing and Async Tasks
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.services.batch_service import BatchProcessingService
from backend.models.developer import Developer
from backend.models.async_task import TaskType
from .auth import get_current_developer

router = APIRouter()


# 请求模型
class BatchGenerationRequest(BaseModel):
    name: str = Field(..., description="批量任务名称")
    model: str = Field("gpt-4o-mini", description="使用的AI模型")
    prompts: List[str] = Field(..., description="待生成的提示词列表", min_items=1, max_items=1000)
    parameters: Dict[str, Any] = Field(default_factory=dict, description="模型参数")
    max_concurrent_tasks: int = Field(5, description="最大并发任务数", ge=1, le=20)
    priority: int = Field(5, description="任务优先级", ge=1, le=10)


class BatchAnalysisRequest(BaseModel):
    name: str = Field(..., description="批量任务名称")
    analysis_type: str = Field(..., description="分析类型", regex="^(sentiment|keywords|classification)$")
    texts: List[str] = Field(..., description="待分析的文本列表", min_items=1, max_items=1000)
    max_concurrent_tasks: int = Field(5, description="最大并发任务数", ge=1, le=20)


class DataExportRequest(BaseModel):
    name: str = Field(..., description="导出任务名称")
    export_type: str = Field(..., description="导出类型", regex="^(usage_data|task_history|billing_data)$")
    format: str = Field("csv", description="导出格式", regex="^(csv|json)$")
    start_date: datetime = Field(..., description="开始日期")
    end_date: datetime = Field(..., description="结束日期")


class ScheduledBatchRequest(BaseModel):
    name: str = Field(..., description="批量任务名称")
    task_type: str = Field(..., description="任务类型")
    batch_config: Dict[str, Any] = Field(..., description="批量配置")
    schedule_type: str = Field("immediate", description="调度类型", regex="^(immediate|scheduled|recurring)$")
    scheduled_at: Optional[datetime] = Field(None, description="计划执行时间")
    recurrence_pattern: Optional[Dict[str, Any]] = Field(None, description="重复模式")
    max_concurrent_tasks: int = Field(5, description="最大并发任务数", ge=1, le=20)


@router.post("/generation")
async def create_batch_generation(
    request: BatchGenerationRequest,
    background_tasks: BackgroundTasks,
    current_developer: Developer = Depends(get_current_developer),
    db: Session = Depends(get_db)
):
    """创建批量文本生成任务"""
    try:
        batch_service = BatchProcessingService(db)
        await batch_service.initialize()

        # 验证prompts数量限制
        if len(request.prompts) > 1000:
            raise HTTPException(status_code=400, detail="单次批量任务最多支持1000个提示词")

        # 准备批量配置
        batch_config = {
            "tasks": [
                {
                    "priority": request.priority,
                    "input_data": {
                        "model": request.model,
                        "prompts": [prompt],  # 每个任务一个提示词
                        "parameters": request.parameters
                    },
                    "total_items": 1
                }
                for prompt in request.prompts
            ]
        }

        # 创建批量任务
        job_id = await batch_service.create_batch_job(
            developer_id=current_developer.id,
            name=request.name,
            task_type=TaskType.BATCH_GENERATION,
            batch_config=batch_config,
            max_concurrent_tasks=request.max_concurrent_tasks
        )

        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "name": request.name,
                "total_tasks": len(request.prompts),
                "status": "pending",
                "message": "批量文本生成任务已创建，正在处理中"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建批量生成任务失败: {str(e)}")


@router.post("/analysis")
async def create_batch_analysis(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_developer: Developer = Depends(get_current_developer),
    db: Session = Depends(get_db)
):
    """创建批量分析任务"""
    try:
        batch_service = BatchProcessingService(db)
        await batch_service.initialize()

        # 验证texts数量限制
        if len(request.texts) > 1000:
            raise HTTPException(status_code=400, detail="单次批量任务最多支持1000个文本")

        # 准备批量配置
        batch_config = {
            "tasks": [
                {
                    "input_data": {
                        "analysis_type": request.analysis_type,
                        "texts": [text],  # 每个任务一个文本
                        "parameters": {}
                    },
                    "total_items": 1
                }
                for text in request.texts
            ]
        }

        # 创建批量任务
        job_id = await batch_service.create_batch_job(
            developer_id=current_developer.id,
            name=request.name,
            task_type=TaskType.BATCH_ANALYSIS,
            batch_config=batch_config,
            max_concurrent_tasks=request.max_concurrent_tasks
        )

        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "name": request.name,
                "total_tasks": len(request.texts),
                "analysis_type": request.analysis_type,
                "status": "pending",
                "message": "批量分析任务已创建，正在处理中"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建批量分析任务失败: {str(e)}")


@router.post("/export")
async def create_data_export(
    request: DataExportRequest,
    background_tasks: BackgroundTasks,
    current_developer: Developer = Depends(get_current_developer),
    db: Session = Depends(get_db)
):
    """创建数据导出任务"""
    try:
        batch_service = BatchProcessingService(db)
        await batch_service.initialize()

        # 验证日期范围
        if request.end_date <= request.start_date:
            raise HTTPException(status_code=400, detail="结束日期必须晚于开始日期")

        if (request.end_date - request.start_date).days > 365:
            raise HTTPException(status_code=400, detail="导出时间范围不能超过365天")

        # 准备批量配置
        batch_config = {
            "tasks": [
                {
                    "input_data": {
                        "export_type": request.export_type,
                        "format": request.format,
                        "date_range": {
                            "start_date": request.start_date,
                            "end_date": request.end_date
                        },
                        "developer_id": current_developer.id
                    },
                    "total_items": 1
                }
            ]
        }

        # 创建批量任务
        job_id = await batch_service.create_batch_job(
            developer_id=current_developer.id,
            name=request.name,
            task_type=TaskType.DATA_EXPORT,
            batch_config=batch_config,
            max_concurrent_tasks=1  # 导出任务通常不需要并发
        )

        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "name": request.name,
                "export_type": request.export_type,
                "format": request.format,
                "status": "pending",
                "message": "数据导出任务已创建，正在处理中"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建数据导出任务失败: {str(e)}")


@router.post("/scheduled")
async def create_scheduled_batch(
    request: ScheduledBatchRequest,
    background_tasks: BackgroundTasks,
    current_developer: Developer = Depends(get_current_developer),
    db: Session = Depends(get_db)
):
    """创建计划批量任务"""
    try:
        batch_service = BatchProcessingService(db)
        await batch_service.initialize()

        # 验证计划时间
        if request.schedule_type == "scheduled" and not request.scheduled_at:
            raise HTTPException(status_code=400, detail="计划任务必须指定执行时间")

        if request.schedule_type == "recurring" and not request.recurrence_pattern:
            raise HTTPException(status_code=400, detail="重复任务必须指定重复模式")

        if request.scheduled_at and request.scheduled_at <= datetime.utcnow():
            raise HTTPException(status_code=400, detail="计划执行时间必须是未来时间")

        # 创建批量任务
        job_id = await batch_service.create_batch_job(
            developer_id=current_developer.id,
            name=request.name,
            task_type=TaskType(request.task_type),
            batch_config=request.batch_config,
            schedule_type=request.schedule_type,
            scheduled_at=request.scheduled_at,
            max_concurrent_tasks=request.max_concurrent_tasks
        )

        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "name": request.name,
                "task_type": request.task_type,
                "schedule_type": request.schedule_type,
                "scheduled_at": request.scheduled_at.isoformat() if request.scheduled_at else None,
                "status": "pending",
                "message": "计划批量任务已创建"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建计划批量任务失败: {str(e)}")


@router.get("/jobs")
async def get_batch_jobs(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, regex="^(pending|running|completed|failed|cancelled)$", description="任务状态"),
    current_developer: Developer = Depends(get_current_developer),
    db: Session = Depends(get_db)
):
    """获取批量任务列表"""
    try:
        batch_service = BatchProcessingService(db)
        result = await batch_service.get_developer_batch_jobs(current_developer.id, page, limit)

        # 如果指定了状态过滤
        if status:
            filtered_jobs = [
                job for job in result["batch_jobs"]
                if job["status"] == status
            ]
            result["batch_jobs"] = filtered_jobs
            result["pagination"]["total"] = len(filtered_jobs)
            result["pagination"]["pages"] = (len(filtered_jobs) + limit - 1) // limit

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取批量任务列表失败: {str(e)}")


@router.get("/jobs/{job_id}")
async def get_batch_job_detail(
    job_id: str,
    current_developer: Developer = Depends(get_current_developer),
    db: Session = Depends(get_db)
):
    """获取批量任务详情"""
    try:
        batch_service = BatchProcessingService(db)
        job_status = await batch_service.get_batch_job_status(job_id)

        if not job_status:
            raise HTTPException(status_code=404, detail="批量任务不存在")

        # 验证任务所有权
        from backend.models.async_task import BatchJob
        batch_job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
        if not batch_job or batch_job.developer_id != current_developer.id:
            raise HTTPException(status_code=404, detail="批量任务不存在")

        return {
            "success": True,
            "data": job_status
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取批量任务详情失败: {str(e)}")


@router.post("/jobs/{job_id}/cancel")
async def cancel_batch_job(
    job_id: str,
    current_developer: Developer = Depends(get_current_developer),
    db: Session = Depends(get_db)
):
    """取消批量任务"""
    try:
        # 验证任务所有权
        from backend.models.async_task import BatchJob
        batch_job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
        if not batch_job or batch_job.developer_id != current_developer.id:
            raise HTTPException(status_code=404, detail="批量任务不存在")

        if batch_job.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(status_code=400, detail="任务���完成或已取消，无法取消")

        batch_service = BatchProcessingService(db)
        await batch_service.initialize()

        success = await batch_service.cancel_batch_job(job_id)
        if not success:
            raise HTTPException(status_code=500, detail="取消批量任务失败")

        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "status": "cancelled",
                "message": "批量任务已取消"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消批量任务失败: {str(e)}")


@router.get("/jobs/{job_id}/tasks")
async def get_batch_job_tasks(
    job_id: str,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(50, ge=1, le=100, description="每页数量"),
    current_developer: Developer = Depends(get_current_developer),
    db: Session = Depends(get_db)
):
    """获取批量任务的子任务列表"""
    try:
        # 验证任务所有权
        from backend.models.async_task import BatchJob, TaskExecution, AsyncTask
        batch_job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
        if not batch_job or batch_job.developer_id != current_developer.id:
            raise HTTPException(status_code=404, detail="批量任务不存在")

        # 获取子任务
        offset = (page - 1) * limit

        query = db.query(AsyncTask).filter(
            AsyncTask.id.in_(
                db.query(TaskExecution.task_id).filter(TaskExecution.job_id == batch_job.id)
            )
        ).order_by(AsyncTask.created_at.desc())

        total = query.count()
        tasks = query.offset(offset).limit(limit).all()

        return {
            "success": True,
            "data": {
                "tasks": [
                    {
                        "task_id": task.task_id,
                        "task_type": task.task_type,
                        "status": task.status,
                        "progress": task.progress,
                        "total_items": task.total_items,
                        "processed_items": task.processed_items,
                        "failed_items": task.failed_items,
                        "started_at": task.started_at.isoformat() if task.started_at else None,
                        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                        "created_at": task.created_at.isoformat(),
                        "error_message": task.error_message
                    }
                    for task in tasks
                ],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取子任务列表失败: {str(e)}")


@router.get("/jobs/{job_id}/results")
async def get_batch_job_results(
    job_id: str,
    current_developer: Developer = Depends(get_current_developer),
    db: Session = Depends(get_db)
):
    """获取批量任务结果"""
    try:
        # 验证任务所有权
        from backend.models.async_task import BatchJob, TaskResult, TaskExecution, AsyncTask
        batch_job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
        if not batch_job or batch_job.developer_id != current_developer.id:
            raise HTTPException(status_code=404, detail="批量任务不存在")

        if batch_job.status != "completed":
            raise HTTPException(status_code=400, detail="任务尚未完成")

        # 获取任务结果
        task_ids = db.query(TaskExecution.task_id).filter(TaskExecution.job_id == batch_job.id).subquery()
        async_task_ids = db.query(AsyncTask.id).filter(AsyncTask.task_id.in_(task_ids)).subquery()

        results = db.query(TaskResult).filter(TaskResult.task_id.in_(async_task_ids)).all()

        # 合并结果
        combined_results = []
        for result in results:
            if result.result_data:
                combined_results.extend(result.result_data.get("results", []))
            elif result.result_text:
                combined_results.append({"text": result.result_text})

        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "total_results": len(combined_results),
                "results": combined_results,
                "export_formats": ["json", "csv"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取批量任务结果失败: {str(e)}")


@router.get("/jobs/{job_id}/download")
async def download_batch_results(
    job_id: str,
    format: str = Query("json", regex="^(json|csv)$", description="下载格式"),
    current_developer: Developer = Depends(get_current_developer),
    db: Session = Depends(get_db)
):
    """下载批量任务结果"""
    try:
        # 验证任务所有权和状态
        from backend.models.async_task import BatchJob
        batch_job = db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
        if not batch_job or batch_job.developer_id != current_developer.id:
            raise HTTPException(status_code=404, detail="批量任务不存在")

        if batch_job.status != "completed":
            raise HTTPException(status_code=400, detail="任务尚未完成")

        # 这里应该生成并返回下载链接
        # 为简化，返回一个模拟的下载信息
        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "download_url": f"/api/v1/developer/batch/jobs/{job_id}/download-file",
                "format": format,
                "file_size": "1.2MB",
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成下载链接失败: {str(e)}")


@router.get("/statistics")
async def get_batch_statistics(
    current_developer: Developer = Depends(get_current_developer),
    db: Session = Depends(get_db)
):
    """获取批量任务统计信息"""
    try:
        from backend.models.async_task import BatchJob
        from sqlalchemy import func

        # 统计各种状态的任务数量
        stats = db.query(
            BatchJob.status,
            func.count(BatchJob.id).label('count')
        ).filter(BatchJob.developer_id == current_developer.id).group_by(BatchJob.status).all()

        # 统计各种类型的任务数量
        type_stats = db.query(
            BatchJob.task_type,
            func.count(BatchJob.id).label('count')
        ).filter(BatchJob.developer_id == current_developer.id).group_by(BatchJob.task_type).all()

        # 获取最近的任务
        recent_jobs = db.query(BatchJob).filter(
            BatchJob.developer_id == current_developer.id
        ).order_by(BatchJob.created_at.desc()).limit(5).all()

        status_distribution = {status: count for status, count in stats}
        type_distribution = {task_type: count for task_type, count in type_stats}

        return {
            "success": True,
            "data": {
                "status_distribution": status_distribution,
                "type_distribution": type_distribution,
                "total_jobs": sum(status_distribution.values()),
                "recent_jobs": [
                    {
                        "job_id": job.job_id,
                        "name": job.name,
                        "task_type": job.task_type,
                        "status": job.status,
                        "created_at": job.created_at.isoformat()
                    }
                    for job in recent_jobs
                ]
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")