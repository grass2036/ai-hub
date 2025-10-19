"""
Task Tracking and Result Export Service
Week 4 Day 25: Batch Processing and Async Tasks
"""

import os
import json
import csv
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import zipfile
import tempfile

from backend.models.async_task import (
    AsyncTask, BatchJob, TaskResult, TaskStatus, TaskType,
    TaskExecution, TaskTemplate
)
from backend.core.task_queue import get_task_queue

logger = logging.getLogger(__name__)


class TaskTrackingService:
    """任务跟踪服务"""

    def __init__(self, db: Session):
        self.db = db

    async def get_task_detail(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详细信息"""
        try:
            task = self.db.query(AsyncTask).filter(AsyncTask.task_id == task_id).first()
            if not task:
                return None

            # 获取执行记录
            executions = self.db.query(TaskExecution).filter(
                TaskExecution.task_id == task.id
            ).order_by(TaskExecution.created_at.desc()).all()

            # 获取结果
            result = self.db.query(TaskResult).filter(TaskResult.task_id == task.id).first()

            return {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": task.status,
                "priority": task.priority,
                "progress": task.progress,
                "total_items": task.total_items,
                "processed_items": task.processed_items,
                "failed_items": task.failed_items,
                "estimated_duration": task.estimated_duration,
                "actual_duration": task.actual_duration,
                "tokens_used": task.tokens_used,
                "cost_incurred": task.cost_incurred,
                "task_config": task.task_config,
                "input_data": task.input_data,
                "error_message": task.error_message,
                "created_at": task.created_at.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "updated_at": task.updated_at.isoformat(),
                "executions": [
                    {
                        "execution_id": exec.execution_id,
                        "status": exec.status,
                        "worker_id": exec.worker_id,
                        "server_instance": exec.server_instance,
                        "started_at": exec.started_at.isoformat() if exec.started_at else None,
                        "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
                        "duration_seconds": exec.duration_seconds,
                        "memory_usage_mb": exec.memory_usage_mb,
                        "cpu_usage_percent": exec.cpu_usage_percent,
                        "retry_count": exec.retry_count,
                        "created_at": exec.created_at.isoformat()
                    }
                    for exec in executions
                ],
                "result": {
                    "result_type": result.result_type,
                    "result_data": result.result_data,
                    "result_text": result.result_text,
                    "file_path": result.file_path,
                    "file_size": result.file_size,
                    "mime_type": result.mime_type,
                    "metadata": result.metadata,
                    "created_at": result.created_at.isoformat()
                } if result else None
            }

        except Exception as e:
            logger.error(f"Failed to get task detail: {e}")
            return None

    async def get_task_timeline(self, task_id: str) -> List[Dict[str, Any]]:
        """获取任务时间线"""
        try:
            task = self.db.query(AsyncTask).filter(AsyncTask.task_id == task_id).first()
            if not task:
                return []

            timeline = []

            # 添加任务创建事件
            timeline.append({
                "event": "created",
                "timestamp": task.created_at.isoformat(),
                "message": "任务已创建",
                "details": {
                    "task_type": task.task_type,
                    "priority": task.priority
                }
            })

            # 添加开始执行事件
            if task.started_at:
                timeline.append({
                    "event": "started",
                    "timestamp": task.started_at.isoformat(),
                    "message": "任务开始执行",
                    "details": {
                        "worker_id": self._get_primary_worker(task.id)
                    }
                })

            # 添加执行记录事件
            executions = self.db.query(TaskExecution).filter(
                TaskExecution.task_id == task.id
            ).order_by(TaskExecution.created_at.asc()).all()

            for exec in executions:
                if exec.started_at:
                    timeline.append({
                        "event": "execution_started",
                        "timestamp": exec.started_at.isoformat(),
                        "message": f"任务执行开始 (工作器: {exec.worker_id or 'unknown'})",
                        "details": {
                            "execution_id": exec.execution_id,
                            "worker_id": exec.worker_id,
                            "retry_count": exec.retry_count
                        }
                    })

                if exec.completed_at:
                    status_map = {
                        TaskStatus.COMPLETED: "执行完成",
                        TaskStatus.FAILED: "执行失败",
                        TaskStatus.CANCELLED: "执行取消"
                    }
                    message = status_map.get(exec.status, "执行结束")

                    timeline.append({
                        "event": "execution_completed",
                        "timestamp": exec.completed_at.isoformat(),
                        "message": message,
                        "details": {
                            "execution_id": exec.execution_id,
                            "duration_seconds": exec.duration_seconds,
                            "final_status": exec.status
                        }
                    })

            # 添加任务完成事件
            if task.completed_at:
                status_map = {
                    TaskStatus.COMPLETED: "任务完成",
                    TaskStatus.FAILED: "任务失败",
                    TaskStatus.CANCELLED: "任务取消"
                }
                message = status_map.get(task.status, "任务结束")

                timeline.append({
                    "event": "completed",
                    "timestamp": task.completed_at.isoformat(),
                    "message": message,
                    "details": {
                        "final_status": task.status,
                        "progress": task.progress,
                        "total_items": task.total_items,
                        "processed_items": task.processed_items,
                        "failed_items": task.failed_items,
                        "duration": task.actual_duration
                    }
                })

            return timeline

        except Exception as e:
            logger.error(f"Failed to get task timeline: {e}")
            return []

    def _get_primary_worker(self, task_id: str) -> Optional[str]:
        """获取主要工作器ID"""
        try:
            execution = self.db.query(TaskExecution).filter(
                TaskExecution.task_id == task_id,
                TaskExecution.worker_id.isnot(None)
            ).first()
            return execution.worker_id if execution else None
        except:
            return None

    async def get_real_time_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取实时任务状态（从Redis）"""
        try:
            task_queue = await get_task_queue()
            if not task_queue.redis_client:
                return None

            # 从Redis获取任务状态
            redis_status = await task_queue.get_task_status(task_id)
            if not redis_status:
                return None

            # 结合数据库信息
            task = self.db.query(AsyncTask).filter(AsyncTask.task_id == task_id).first()
            if not task:
                return None

            return {
                "task_id": task_id,
                "status": redis_status.get("status"),
                "progress": float(redis_status.get("progress", 0)),
                "error_message": redis_status.get("error_message"),
                "updated_at": redis_status.get("updated_at"),
                "database_status": task.status,
                "database_progress": task.progress
            }

        except Exception as e:
            logger.error(f"Failed to get real-time task status: {e}")
            return None


class ResultExportService:
    """结果导出服务"""

    def __init__(self, db: Session):
        self.db = db
        self.export_dir = "data/exports"
        os.makedirs(self.export_dir, exist_ok=True)

    async def export_task_results(
        self,
        task_ids: List[str],
        format: str = "json",
        include_metadata: bool = False
    ) -> str:
        """导出任务结果"""
        try:
            # 获取任务结果
            results = []
            for task_id in task_ids:
                task_result = await self._get_task_result_data(task_id, include_metadata)
                if task_result:
                    results.append(task_result)

            # 生成导出文件
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"task_results_{timestamp}.{format}"
            file_path = os.path.join(self.export_dir, filename)

            if format == "json":
                await self._export_json(results, file_path)
            elif format == "csv":
                await self._export_csv(results, file_path)
            elif format == "xlsx":
                await self._export_xlsx(results, file_path)
            else:
                raise ValueError(f"Unsupported export format: {format}")

            return file_path

        except Exception as e:
            logger.error(f"Failed to export task results: {e}")
            raise

    async def _get_task_result_data(self, task_id: str, include_metadata: bool) -> Optional[Dict[str, Any]]:
        """获取单个任务的结果数据"""
        try:
            task = self.db.query(AsyncTask).filter(AsyncTask.task_id == task_id).first()
            if not task:
                return None

            result = self.db.query(TaskResult).filter(TaskResult.task_id == task.id).first()

            data = {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "progress": task.progress,
                "total_items": task.total_items,
                "processed_items": task.processed_items,
                "failed_items": task.failed_items,
                "tokens_used": task.tokens_used,
                "cost_incurred": task.cost_incurred
            }

            if result:
                if result.result_data:
                    data["result"] = result.result_data
                elif result.result_text:
                    data["result"] = {"text": result.result_text}

                data["file_path"] = result.file_path
                data["file_size"] = result.file_size

            if include_metadata:
                data["task_config"] = task.task_config
                data["input_data"] = task.input_data
                data["error_message"] = task.error_message
                data["metadata"] = result.metadata if result else None

            return data

        except Exception as e:
            logger.error(f"Failed to get task result data: {e}")
            return None

    async def _export_json(self, data: List[Dict[str, Any]], file_path: str):
        """导出为JSON格式"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def _export_csv(self, data: List[Dict[str, Any]], file_path: str):
        """导出为CSV格式"""
        if not data:
            return

        # 扁平化数据结构
        flattened_data = []
        for item in data:
            flat_item = {
                "task_id": item.get("task_id"),
                "task_type": item.get("task_type"),
                "status": item.get("status"),
                "created_at": item.get("created_at"),
                "completed_at": item.get("completed_at"),
                "progress": item.get("progress"),
                "total_items": item.get("total_items"),
                "processed_items": item.get("processed_items"),
                "failed_items": item.get("failed_items"),
                "tokens_used": item.get("tokens_used"),
                "cost_incurred": item.get("cost_incurred")
            }

            # 处理结果数据
            result = item.get("result", {})
            if isinstance(result, dict):
                if "results" in result:
                    # 批量结果
                    for i, sub_result in enumerate(result["results"]):
                        if i == 0:
                            flat_item.update({
                                "prompt": sub_result.get("prompt", ""),
                                "response": sub_result.get("response", ""),
                                "status": sub_result.get("status", "")
                            })
                        else:
                            # 为每个结果创建新行
                            new_item = flat_item.copy()
                            new_item.update({
                                "prompt": sub_result.get("prompt", ""),
                                "response": sub_result.get("response", ""),
                                "status": sub_result.get("status", "")
                            })
                            flattened_data.append(new_item)
                else:
                    # 单个结果
                    flat_item["result"] = json.dumps(result, ensure_ascii=False)

            if "results" not in result or len(result.get("results", [])) == 0:
                flattened_data.append(flat_item)

        # 写入CSV文件
        if flattened_data:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=flattened_data[0].keys())
                writer.writeheader()
                writer.writerows(flattened_data)

    async def _export_xlsx(self, data: List[Dict[str, Any]], file_path: str):
        """导出为Excel格式"""
        try:
            import pandas as pd

            # 扁平化数据
            flattened_data = []
            for item in data:
                flat_item = {
                    "Task ID": item.get("task_id"),
                    "Task Type": item.get("task_type"),
                    "Status": item.get("status"),
                    "Created At": item.get("created_at"),
                    "Completed At": item.get("completed_at"),
                    "Progress (%)": item.get("progress"),
                    "Total Items": item.get("total_items"),
                    "Processed Items": item.get("processed_items"),
                    "Failed Items": item.get("failed_items"),
                    "Tokens Used": item.get("tokens_used"),
                    "Cost Incurred": item.get("cost_incurred")
                }

                result = item.get("result", {})
                if isinstance(result, dict) and "results" in result:
                    # 批量结果
                    for i, sub_result in enumerate(result["results"]):
                        if i == 0:
                            flat_item.update({
                                "Prompt": sub_result.get("prompt", ""),
                                "Response": sub_result.get("response", ""),
                                "Result Status": sub_result.get("status", "")
                            })
                        else:
                            new_item = flat_item.copy()
                            new_item.update({
                                "Prompt": sub_result.get("prompt", ""),
                                "Response": sub_result.get("response", ""),
                                "Result Status": sub_result.get("status", "")
                            })
                            flattened_data.append(new_item)
                else:
                    flat_item["Result"] = json.dumps(result, ensure_ascii=False) if result else ""

                if "results" not in result or len(result.get("results", [])) == 0:
                    flattened_data.append(flat_item)

            # 创建DataFrame并导出
            if flattened_data:
                df = pd.DataFrame(flattened_data)
                df.to_excel(file_path, index=False, engine='openpyxl')

        except ImportError:
            # 如果没有pandas，回退到CSV
            await self._export_csv(data, file_path.replace('.xlsx', '.csv'))
        except Exception as e:
            logger.error(f"Failed to export XLSX: {e}")
            raise

    async def export_batch_job_results(self, job_id: str, format: str = "json") -> str:
        """导出批量任务结果"""
        try:
            # 获取批量任务的所有子任务
            from backend.models.async_task import TaskExecution
            batch_job = self.db.query(BatchJob).filter(BatchJob.job_id == job_id).first()
            if not batch_job:
                raise ValueError(f"Batch job {job_id} not found")

            task_ids = self.db.query(AsyncTask.task_id).filter(
                AsyncTask.id.in_(
                    self.db.query(TaskExecution.task_id).filter(TaskExecution.job_id == batch_job.id)
                )
            ).all()

            task_id_list = [tid[0] for tid in task_ids]

            # 导出结果
            file_path = await self.export_task_results(task_id_list, format, include_metadata=True)

            # 重命名文件
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            new_filename = f"batch_job_{job_id}_{timestamp}.{format}"
            new_file_path = os.path.join(self.export_dir, new_filename)
            os.rename(file_path, new_file_path)

            return new_file_path

        except Exception as e:
            logger.error(f"Failed to export batch job results: {e}")
            raise

    async def create_export_archive(self, file_paths: List[str], archive_name: str) -> str:
        """创建导出文件归档"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"{archive_name}_{timestamp}.zip"
            archive_path = os.path.join(self.export_dir, archive_filename)

            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in file_paths:
                    if os.path.exists(file_path):
                        filename = os.path.basename(file_path)
                        zipf.write(file_path, filename)

            return archive_path

        except Exception as e:
            logger.error(f"Failed to create export archive: {e}")
            raise

    async def cleanup_expired_exports(self, days: int = 7):
        """清理过期导出文件"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            export_files = os.listdir(self.export_dir)

            deleted_count = 0
            for filename in export_files:
                file_path = os.path.join(self.export_dir, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} expired export files")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired exports: {e}")
            return 0

    async def get_export_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取导出文件信息"""
        try:
            if not os.path.exists(file_path):
                return None

            stat = os.stat(file_path)
            return {
                "file_path": file_path,
                "filename": os.path.basename(file_path),
                "file_size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "mime_type": self._get_mime_type(file_path)
            }

        except Exception as e:
            logger.error(f"Failed to get export file info: {e}")
            return None

    def _get_mime_type(self, file_path: str) -> str:
        """获取文件MIME类型"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"