"""
Batch Processing Service
Week 4 Day 25: Batch Processing and Async Tasks
"""

import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.models.async_task import (
    AsyncTask, BatchJob, TaskStatus, TaskType,
    TaskResult, TaskTemplate, TaskExecution
)
from backend.models.developer import Developer
from backend.core.task_queue import TaskQueue, QueuePriority, get_task_queue
from backend.core.ai_service import ai_manager

logger = logging.getLogger(__name__)


class BatchProcessingService:
    """批量处理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.task_queue: Optional[TaskQueue] = None

    async def initialize(self):
        """初始化服务"""
        self.task_queue = await get_task_queue()
        # 注册任务处理器
        self.task_queue.register_handler("batch_generation", self._handle_batch_generation)
        self.task_queue.register_handler("batch_analysis", self._handle_batch_analysis)
        self.task_queue.register_handler("data_export", self._handle_data_export)

    async def create_batch_job(
        self,
        developer_id: str,
        name: str,
        task_type: TaskType,
        batch_config: Dict[str, Any],
        schedule_type: str = "immediate",
        scheduled_at: Optional[datetime] = None,
        max_concurrent_tasks: int = 5
    ) -> str:
        """创建批量任务"""
        try:
            job_id = str(uuid.uuid4())

            batch_job = BatchJob(
                job_id=job_id,
                name=name,
                task_type=task_type.value,
                developer_id=developer_id,
                batch_config=batch_config,
                total_tasks=len(batch_config.get("tasks", [])),
                schedule_type=schedule_type,
                scheduled_at=scheduled_at,
                max_concurrent_tasks=max_concurrent_tasks,
                status=TaskStatus.PENDING
            )

            self.db.add(batch_job)
            self.db.commit()

            # 如果是立即执行，开始处理批量任务
            if schedule_type == "immediate":
                await self._start_batch_job(job_id)

            logger.info(f"Batch job {job_id} created successfully")
            return job_id

        except Exception as e:
            logger.error(f"Failed to create batch job: {e}")
            self.db.rollback()
            raise

    async def _start_batch_job(self, job_id: str):
        """开始执行批量任务"""
        try:
            batch_job = self.db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
            if not batch_job:
                return

            batch_job.status = TaskStatus.RUNNING
            batch_job.started_at = datetime.utcnow()
            self.db.commit()

            tasks = batch_job.batch_config.get("tasks", [])
            concurrent_limit = batch_job.max_concurrent_tasks

            # 使用信号量控制并发数量
            semaphore = asyncio.Semaphore(concurrent_limit)

            async def process_single_task(task_data: Dict[str, Any]):
                async with semaphore:
                    return await self._create_and_enqueue_task(
                        batch_job.job_id,
                        batch_job.task_type,
                        task_data,
                        batch_job.developer_id
                    )

            # 并发处理所有任务
            task_futures = [process_single_task(task) for task in tasks]
            await asyncio.gather(*task_futures, return_exceptions=True)

        except Exception as e:
            logger.error(f"Failed to start batch job {job_id}: {e}")
            # 更新任务状态为失败
            batch_job = self.db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
            if batch_job:
                batch_job.status = TaskStatus.FAILED
                batch_job.completed_at = datetime.utcnow()
                self.db.commit()

    async def _create_and_enqueue_task(
        self,
        job_id: str,
        task_type: str,
        task_data: Dict[str, Any],
        developer_id: str
    ) -> str:
        """创建并加入单个任务到队列"""
        try:
            task_id = str(uuid.uuid4())

            # 在数据库中创建任务记录
            async_task = AsyncTask(
                task_id=task_id,
                task_type=task_type,
                developer_id=developer_id,
                task_config=task_data,
                input_data=task_data.get("input_data"),
                status=TaskStatus.PENDING,
                priority=task_data.get("priority", 5),
                total_items=task_data.get("total_items", 1)
            )

            self.db.add(async_task)

            # 创建任务执行记录
            execution = TaskExecution(
                task_id=async_task.id,
                job_id=job_id,
                execution_id=str(uuid.uuid4()),
                status=TaskStatus.PENDING
            )

            self.db.add(execution)
            self.db.commit()

            # 将任务加入队列
            await self.task_queue.enqueue_task(
                task_type=task_type,
                task_data={
                    "task_id": task_id,
                    "job_id": job_id,
                    "developer_id": developer_id,
                    "task_data": task_data
                },
                priority=QueuePriority.NORMAL,
                max_retries=3
            )

            return task_id

        except Exception as e:
            logger.error(f"Failed to create and enqueue task: {e}")
            self.db.rollback()
            raise

    async def _handle_batch_generation(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        db: Session,
        update_callback: Callable
    ) -> Dict[str, Any]:
        """处理批量文本生成任务"""
        try:
            input_data = task_data.get("input_data", {})
            model = input_data.get("model", "gpt-4o-mini")
            prompts = input_data.get("prompts", [])
            parameters = input_data.get("parameters", {})

            results = []
            total_prompts = len(prompts)

            for i, prompt in enumerate(prompts):
                try:
                    # 更新进度
                    progress = (i / total_prompts) * 100
                    await update_callback(progress)

                    # 调用AI服务生成文本
                    service = await ai_manager.get_service("openrouter")
                    if not service:
                        raise ValueError("AI service not available")

                    response = await service.generate_response(
                        prompt=prompt,
                        model=model,
                        **parameters
                    )

                    results.append({
                        "prompt": prompt,
                        "response": response,
                        "status": "success",
                        "index": i
                    })

                except Exception as e:
                    results.append({
                        "prompt": prompt,
                        "error": str(e),
                        "status": "failed",
                        "index": i
                    })

            # 保存结果
            task_result = TaskResult(
                task_id=db.query(AsyncTask).filter(AsyncTask.task_id == task_id).first().id,
                result_type="json",
                result_data={"results": results, "total": total_prompts},
                metadata={"model": model, "parameters": parameters}
            )

            db.add(task_result)
            db.commit()

            return {
                "task_id": task_id,
                "results": results,
                "total_processed": total_prompts,
                "success_count": len([r for r in results if r.get("status") == "success"]),
                "failed_count": len([r for r in results if r.get("status") == "failed"])
            }

        except Exception as e:
            logger.error(f"Batch generation task {task_id} failed: {e}")
            raise

    async def _handle_batch_analysis(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        db: Session,
        update_callback: Callable
    ) -> Dict[str, Any]:
        """处理批量分析任务"""
        try:
            input_data = task_data.get("input_data", {})
            analysis_type = input_data.get("analysis_type", "sentiment")
            texts = input_data.get("texts", [])

            results = []
            total_texts = len(texts)

            for i, text in enumerate(texts):
                try:
                    # 更新进度
                    progress = (i / total_texts) * 100
                    await update_callback(progress)

                    # 根据分析类型执行不同的分析
                    if analysis_type == "sentiment":
                        result = await self._analyze_sentiment(text)
                    elif analysis_type == "keywords":
                        result = await self._extract_keywords(text)
                    elif analysis_type == "classification":
                        result = await self._classify_text(text)
                    else:
                        result = {"error": f"Unknown analysis type: {analysis_type}"}

                    results.append({
                        "text": text,
                        "analysis": result,
                        "status": "success",
                        "index": i
                    })

                except Exception as e:
                    results.append({
                        "text": text,
                        "error": str(e),
                        "status": "failed",
                        "index": i
                    })

            # 保存结果
            task_result = TaskResult(
                task_id=db.query(AsyncTask).filter(AsyncTask.task_id == task_id).first().id,
                result_type="json",
                result_data={"results": results, "total": total_texts},
                metadata={"analysis_type": analysis_type}
            )

            db.add(task_result)
            db.commit()

            return {
                "task_id": task_id,
                "results": results,
                "total_processed": total_texts,
                "analysis_type": analysis_type
            }

        except Exception as e:
            logger.error(f"Batch analysis task {task_id} failed: {e}")
            raise

    async def _handle_data_export(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        db: Session,
        update_callback: Callable
    ) -> Dict[str, Any]:
        """处理数据导出任务"""
        try:
            input_data = task_data.get("input_data", {})
            export_type = input_data.get("export_type", "usage_data")
            export_format = input_data.get("format", "csv")
            date_range = input_data.get("date_range", {})
            developer_id = task_data.get("developer_id")

            # 更新进度
            await update_callback(25)

            # 根据导出类型获取数据
            if export_type == "usage_data":
                data = await self._export_usage_data(developer_id, date_range, db)
            elif export_type == "task_history":
                data = await self._export_task_history(developer_id, date_range, db)
            elif export_type == "billing_data":
                data = await self._export_billing_data(developer_id, date_range, db)
            else:
                raise ValueError(f"Unknown export type: {export_type}")

            # 更新进度
            await update_callback(75)

            # 生成导出文件
            file_path = await self._generate_export_file(data, export_format, export_type)

            # 更新进度
            await update_callback(100)

            # 保存文件信息
            task_result = TaskResult(
                task_id=db.query(AsyncTask).filter(AsyncTask.task_id == task_id).first().id,
                result_type="file",
                file_path=file_path,
                metadata={
                    "export_type": export_type,
                    "format": export_format,
                    "record_count": len(data) if isinstance(data, list) else 1
                }
            )

            db.add(task_result)
            db.commit()

            return {
                "task_id": task_id,
                "file_path": file_path,
                "export_type": export_type,
                "format": export_format,
                "record_count": len(data) if isinstance(data, list) else 1
            }

        except Exception as e:
            logger.error(f"Data export task {task_id} failed: {e}")
            raise

    async def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """情感分析"""
        try:
            service = await ai_manager.get_service("openrouter")
            prompt = f"Please analyze the sentiment of the following text and provide a score from -1 (very negative) to 1 (very positive). Also provide the confidence score. Text: {text}"

            response = await service.generate_response(prompt, model="gpt-4o-mini")
            return {"analysis": "sentiment", "result": response}
        except Exception as e:
            return {"error": str(e)}

    async def _extract_keywords(self, text: str) -> Dict[str, Any]:
        """关键词提取"""
        try:
            service = await ai_manager.get_service("openrouter")
            prompt = f"Please extract the main keywords from the following text. Return them as a comma-separated list. Text: {text}"

            response = await service.generate_response(prompt, model="gpt-4o-mini")
            return {"analysis": "keywords", "result": response}
        except Exception as e:
            return {"error": str(e)}

    async def _classify_text(self, text: str) -> Dict[str, Any]:
        """文本分类"""
        try:
            service = await ai_manager.get_service("openrouter")
            prompt = f"Please classify the following text into categories like 'business', 'technology', 'health', 'education', etc. Text: {text}"

            response = await service.generate_response(prompt, model="gpt-4o-mini")
            return {"analysis": "classification", "result": response}
        except Exception as e:
            return {"error": str(e)}

    async def _export_usage_data(self, developer_id: str, date_range: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
        """导出使用数据"""
        # 这里应该调用之前创建的使用量服务
        # 为简化，返回空列表
        return []

    async def _export_task_history(self, developer_id: str, date_range: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
        """导出任务历史"""
        tasks = db.query(AsyncTask).filter(
            AsyncTask.developer_id == developer_id,
            AsyncTask.created_at >= date_range.get("start_date"),
            AsyncTask.created_at <= date_range.get("end_date")
        ).all()

        return [
            {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "progress": task.progress
            }
            for task in tasks
        ]

    async def _export_billing_data(self, developer_id: str, date_range: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
        """导出账单数据"""
        # 这里应该调用之前创建的计费服务
        # 为简化，返回空列表
        return []

    async def _generate_export_file(self, data: List[Dict[str, Any]], format: str, export_type: str) -> str:
        """生成导出文件"""
        import os
        import csv
        import json

        # 创建导出目录
        export_dir = "data/exports"
        os.makedirs(export_dir, exist_ok=True)

        # 生成文件名
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{export_type}_{timestamp}.{format}"
        file_path = os.path.join(export_dir, filename)

        # 根据格式生成文件
        if format == "csv":
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                if data:
                    fieldnames = data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
        elif format == "json":
            with open(file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=2, ensure_ascii=False)

        return file_path

    async def get_batch_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取批量任务状态"""
        try:
            batch_job = self.db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
            if not batch_job:
                return None

            # 获取相关任务的状态
            tasks = self.db.query(AsyncTask).filter(
                AsyncTask.task_id.in_(
                    self.db.query(TaskExecution.task_id).filter(
                        TaskExecution.job_id == batch_job.id
                    )
                )
            ).all()

            task_stats = {
                "total": len(tasks),
                "pending": len([t for t in tasks if t.status == TaskStatus.PENDING]),
                "running": len([t for t in tasks if t.status == TaskStatus.RUNNING]),
                "completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
                "failed": len([t for t in tasks if t.status == TaskStatus.FAILED])
            }

            return {
                "job_id": job_id,
                "name": batch_job.name,
                "status": batch_job.status,
                "total_tasks": batch_job.total_tasks,
                "completed_tasks": batch_job.completed_tasks,
                "failed_tasks": batch_job.failed_tasks,
                "task_statistics": task_stats,
                "started_at": batch_job.started_at.isoformat() if batch_job.started_at else None,
                "completed_at": batch_job.completed_at.isoformat() if batch_job.completed_at else None,
                "created_at": batch_job.created_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get batch job status: {e}")
            return None

    async def cancel_batch_job(self, job_id: str) -> bool:
        """取消批量任务"""
        try:
            batch_job = self.db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
            if not batch_job:
                return False

            # 更新批量任务状态
            batch_job.status = TaskStatus.CANCELLED
            batch_job.completed_at = datetime.utcnow()

            # 取消所有相关的运行中任务
            tasks = self.db.query(AsyncTask).filter(
                AsyncTask.task_id.in_(
                    self.db.query(TaskExecution.task_id).filter(
                        TaskExecution.job_id == batch_job.id
                    )
                ),
                AsyncTask.status.in_([TaskStatus.PENDING, TaskStatus.RUNNING])
            ).all()

            for task in tasks:
                task.status = TaskStatus.CANCELLED
                if self.task_queue:
                    await self.task_queue.cancel_task(task.task_id)

            self.db.commit()
            logger.info(f"Batch job {job_id} cancelled")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel batch job: {e}")
            return False

    async def get_developer_batch_jobs(self, developer_id: str, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """获取开发者的批量任务列表"""
        try:
            offset = (page - 1) * limit

            batch_jobs = self.db.query(BatchJob).filter(
                BatchJob.developer_id == developer_id
            ).order_by(BatchJob.created_at.desc()).offset(offset).limit(limit).all()

            total = self.db.query(BatchJob).filter(BatchJob.developer_id == developer_id).count()

            return {
                "batch_jobs": [
                    {
                        "job_id": job.job_id,
                        "name": job.name,
                        "task_type": job.task_type,
                        "status": job.status,
                        "total_tasks": job.total_tasks,
                        "completed_tasks": job.completed_tasks,
                        "failed_tasks": job.failed_tasks,
                        "created_at": job.created_at.isoformat(),
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None
                    }
                    for job in batch_jobs
                ],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            }

        except Exception as e:
            logger.error(f"Failed to get developer batch jobs: {e}")
            return {"batch_jobs": [], "pagination": {"page": page, "limit": limit, "total": 0, "pages": 0}}