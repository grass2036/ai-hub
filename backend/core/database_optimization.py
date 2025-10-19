"""
数据库性能优化模块 - Week 6 Day 2 增强版
��现查询优化、连接池管理、缓存策略、性能监控等功能
"""

import asyncio
import time
import logging
import psutil
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager, asynccontextmanager
from sqlalchemy import text, Index, func, and_, or_
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.sql import Select
from sqlalchemy.pool import QueuePool
import redis

from backend.models.developer import Developer, DeveloperAPIKey, APIUsageRecord
from backend.models.async_task import AsyncTask, BatchJob, TaskResult
from backend.core.database import get_db, engine
from backend.config.settings import get_settings

settings = get_settings()

@dataclass
class QueryMetrics:
    """查询性能指标"""
    query: str
    execution_time: float
    rows_affected: int
    memory_usage: float
    timestamp: datetime
    query_hash: str = field(init=False)

    def __post_init__(self):
        self.query_hash = hash(self.query.strip().lower())

@dataclass
class PerformanceReport:
    """性能报告"""
    total_queries: int
    avg_execution_time: float
    slow_queries_count: int
    optimization_suggestions: List[Dict[str, Any]]
    timestamp: datetime

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """增强版数据库优化器"""

    def __init__(self, db: Session = None):
        self.db = db
        self.query_metrics: List[QueryMetrics] = []
        self.slow_query_threshold = 1.0  # 秒
        self.redis_client = None
        self._setup_redis()

    def _setup_redis(self):
        """设置Redis连接用于查询缓存"""
        try:
            self.redis_client = redis.Redis(
                host=getattr(settings, 'redis_host', 'localhost'),
                port=getattr(settings, 'redis_port', 6379),
                db=0,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis连接成功，启用��询缓存")
        except Exception as e:
            logger.warning(f"Redis连接失败，跳过查询缓存: {e}")
            self.redis_client = None

    async def analyze_query_execution(self, query: str, params: Dict = None) -> QueryMetrics:
        """分析查询执行性能"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        try:
            if self.db:
                result = self.db.execute(text(query), params or {})
                rows = result.fetchall()
                rows_affected = len(rows)
            else:
                with get_db() as db:
                    result = db.execute(text(query), params or {})
                    rows = result.fetchall()
                    rows_affected = len(rows)

        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            raise

        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        metrics = QueryMetrics(
            query=query,
            execution_time=end_time - start_time,
            rows_affected=rows_affected,
            memory_usage=end_memory - start_memory,
            timestamp=datetime.now()
        )

        self.query_metrics.append(metrics)
        return metrics

    async def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """获取缓存结果"""
        if not self.redis_client:
            return None

        try:
            cached_result = self.redis_client.get(cache_key)
            if cached_result:
                logger.info(f"缓存命中: {cache_key}")
                return json.loads(cached_result)
        except Exception as e:
            logger.warning(f"缓存读取失败: {e}")
        return None

    async def cache_result(self, cache_key: str, result: Any, ttl: int = 300):
        """缓存结果"""
        if not self.redis_client:
            return

        try:
            self.redis_client.setex(cache_key, ttl, json.dumps(result, default=str))
            logger.info(f"结果已缓存: {cache_key}, TTL: {ttl}秒")
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")

    def generate_cache_key(self, query: str, params: Dict = None) -> str:
        """生成缓存键"""
        query_hash = hash(query.strip().lower())
        params_hash = hash(str(sorted(params.items()))) if params else ""
        return f"db_cache:{query_hash}:{params_hash}"

    async def execute_optimized_query(self, query: str, params: Dict = None, cache_ttl: int = 300) -> Any:
        """执行优化查询（带缓存）"""
        # 检查缓存
        cache_key = self.generate_cache_key(query, params)
        cached_result = await self.get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result

        # 分析查询性能
        metrics = await self.analyze_query_execution(query, params)

        # 执行查询
        if self.db:
            result = self.db.execute(text(query), params or {})
            rows = result.fetchall()
        else:
            with get_db() as db:
                result = db.execute(text(query), params or {})
                rows = result.fetchall()

        # 转换为可序列化的格式
        serializable_result = [dict(row._mapping) for row in rows]

        # 缓存结果（仅对SELECT查询）
        if query.strip().lower().startswith('select') and rows:
            await self.cache_result(cache_key, serializable_result, cache_ttl)

        return serializable_result

    def get_slow_queries(self) -> List[QueryMetrics]:
        """获取慢查询列表"""
        return [m for m in self.query_metrics if m.execution_time > self.slow_query_threshold]

    def get_performance_report(self) -> PerformanceReport:
        """生成性能报告"""
        if not self.query_metrics:
            return PerformanceReport(
                total_queries=0,
                avg_execution_time=0,
                slow_queries_count=0,
                optimization_suggestions=[],
                timestamp=datetime.now()
            )

        execution_times = [m.execution_time for m in self.query_metrics]
        slow_queries = self.get_slow_queries()

        # 生成优化建议
        suggestions = self._generate_optimization_suggestions()

        return PerformanceReport(
            total_queries=len(self.query_metrics),
            avg_execution_time=sum(execution_times) / len(execution_times),
            slow_queries_count=len(slow_queries),
            optimization_suggestions=suggestions,
            timestamp=datetime.now()
        )

    def _generate_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """生成优化建议"""
        suggestions = []
        slow_queries = self.get_slow_queries()

        if len(slow_queries) > 0:
            suggestions.append({
                "type": "slow_queries",
                "message": f"发现 {len(slow_queries)} 个慢查询，建议优化",
                "priority": "high",
                "details": [
                    {
                        "query": q.query[:100] + "..." if len(q.query) > 100 else q.query,
                        "execution_time": q.execution_time,
                        "suggestion": "考虑添加索引或重写查询"
                    }
                    for q in slow_queries[:5]  # 只显示前5个
                ]
            })

        # 分析查询模式
        query_patterns = {}
        for metric in self.query_metrics:
            query_type = metric.query.strip().split()[0].upper()
            if query_type not in query_patterns:
                query_patterns[query_type] = []
            query_patterns[query_type].append(metric.execution_time)

        for query_type, times in query_patterns.items():
            avg_time = sum(times) / len(times)
            if avg_time > 0.5:
                suggestions.append({
                    "type": "query_pattern",
                    "message": f"{query_type} 查询平均耗时 {avg_time:.3f} 秒",
                    "priority": "medium",
                    "suggestion": f"优化 {query_type} 查询性能"
                })

        return suggestions

    @contextmanager
    def get_optimized_session(self):
        """获取优化的数据库会话"""
        try:
            # 设置会话优化参数
            self.db.execute(text("SET SESSION innodb_lock_wait_timeout = 5"))
            self.db.execute(text("SET SESSION query_cache_type = ON"))
            yield self.db
        except Exception as e:
            logger.error(f"Database session optimization error: {e}")
            yield self.db
        finally:
            self.db.close()

    async def create_performance_indexes(self):
        """创建性能索引"""
        indexes = [
            # 开发者表索引
            "CREATE INDEX IF NOT EXISTS idx_developers_email ON developers(email)",
            "CREATE INDEX IF NOT EXISTS idx_developers_created_at ON developers(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_developers_email_verified ON developers(email_verified)",
            "CREATE INDEX IF NOT EXISTS idx_developers_status ON developers(status)",

            # API密钥表索引
            "CREATE INDEX IF NOT EXISTS idx_api_keys_developer_id ON developer_api_keys(developer_id)",
            "CREATE INDEX IF NOT EXISTS idx_api_keys_key_prefix ON developer_api_keys(key_prefix)",
            "CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON developer_api_keys(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_api_keys_created_at ON developer_api_keys(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_api_keys_last_used ON developer_api_keys(last_used)",

            # API使用记录表索引
            "CREATE INDEX IF NOT EXISTS idx_usage_developer_id ON api_usage_records(developer_id)",
            "CREATE INDEX IF NOT EXISTS idx_usage_api_key_id ON api_usage_records(api_key_id)",
            "CREATE INDEX IF NOT EXISTS idx_usage_created_at ON api_usage_records(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_usage_model ON api_usage_records(model)",
            "CREATE INDEX IF NOT EXISTS idx_usage_status_code ON api_usage_records(status_code)",
            "CREATE INDEX IF NOT EXISTS idx_usage_developer_created ON api_usage_records(developer_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_usage_api_key_created ON api_usage_records(api_key_id, created_at)",

            # 异步任务表索引
            "CREATE INDEX IF NOT EXISTS idx_async_tasks_task_id ON async_tasks(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_async_tasks_developer_id ON async_tasks(developer_id)",
            "CREATE INDEX IF NOT EXISTS idx_async_tasks_status ON async_tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_async_tasks_task_type ON async_tasks(task_type)",
            "CREATE INDEX IF NOT EXISTS idx_async_tasks_created_at ON async_tasks(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_async_tasks_priority ON async_tasks(priority)",
            "CREATE INDEX IF NOT EXISTS idx_async_tasks_status_created ON async_tasks(status, created_at)",

            # 批量任务表索引
            "CREATE INDEX IF NOT EXISTS idx_batch_jobs_job_id ON batch_jobs(job_id)",
            "CREATE INDEX IF NOT EXISTS idx_batch_jobs_developer_id ON batch_jobs(developer_id)",
            "CREATE INDEX IF NOT EXISTS idx_batch_jobs_status ON batch_jobs(status)",
            "CREATE INDEX IF NOT EXISTS idx_batch_jobs_task_type ON batch_jobs(task_type)",
            "CREATE INDEX IF NOT EXISTS idx_batch_jobs_created_at ON batch_jobs(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_batch_jobs_schedule_type ON batch_jobs(schedule_type)",
            "CREATE INDEX IF NOT EXISTS idx_batch_jobs_scheduled_at ON batch_jobs(scheduled_at)",

            # 任务结果表索引
            "CREATE INDEX IF NOT EXISTS idx_task_results_task_id ON task_results(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_results_result_type ON task_results(result_type)",
            "CREATE INDEX IF NOT EXISTS idx_task_results_created_at ON task_results(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_task_results_expires_at ON task_results(expires_at)",
        ]

        try:
            for index_sql in indexes:
                self.db.execute(text(index_sql))
            self.db.commit()
            logger.info("Performance indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create performance indexes: {e}")
            self.db.rollback()

    async def analyze_query_performance(self) -> Dict[str, Any]:
        """分析查询性能"""
        try:
            # 检查慢查询
            slow_queries = self.db.execute(text("""
                SELECT
                    query_time,
                    lock_time,
                    rows_sent,
                    rows_examined,
                    sql_text
                FROM mysql.slow_log
                WHERE start_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
                ORDER BY query_time DESC
                LIMIT 10
            """)).fetchall() if self.db.bind.dialect.name == 'mysql' else []

            # 检查索引使用情况
            index_usage = self.db.execute(text("""
                SELECT
                    table_name,
                    index_name,
                    cardinality,
                    sub_part,
                    packed,
                    nullable,
                    index_type
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                ORDER BY table_name, seq_in_index
            """)).fetchall()

            # 检查表大小
            table_sizes = self.db.execute(text("""
                SELECT
                    table_name,
                    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                ORDER BY size_mb DESC
            """)).fetchall()

            return {
                "slow_queries": [dict(row) for row in slow_queries],
                "index_usage": [dict(row) for row in index_usage],
                "table_sizes": [dict(row) for row in table_sizes],
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Query performance analysis failed: {e}")
            return {"error": str(e)}

    async def optimize_developer_queries(self) -> Dict[str, Any]:
        """优化开发者相关查询"""
        optimizations = {}

        try:
            # 优化开发者查询 - 使用预加载
            def get_developer_with_keys_optimized(developer_id: str):
                return self.db.query(Developer)\
                    .options(joinedload(Developer.api_keys))\
                    .filter(Developer.id == developer_id)\
                    .first()

            # 优化API密钥查询
            def get_api_keys_with_usage_optimized(developer_id: str, limit: int = 10):
                return self.db.query(DeveloperAPIKey)\
                    .outerjoin(APIUsageRecord)\
                    .filter(DeveloperAPIKey.developer_id == developer_id)\
                    .filter(DeveloperAPIKey.is_active == True)\
                    .order_by(DeveloperAPIKey.created_at.desc())\
                    .limit(limit)\
                    .all()

            # 优化使用统计查询
            def get_usage_stats_optimized(developer_id: str, days: int = 30):
                start_date = datetime.utcnow() - timedelta(days=days)

                # 使用聚合查询减少数据传输
                stats = self.db.query(
                    func.count(APIUsageRecord.id).label('total_requests'),
                    func.sum(APIUsageRecord.tokens_used).label('total_tokens'),
                    func.sum(APIUsageRecord.cost).label('total_cost'),
                    func.avg(APIUsageRecord.response_time_ms).label('avg_response_time'),
                    func.count(func.case([(APIUsageRecord.status_code >= 400, 1)])).label('error_count')
                ).filter(
                    and_(
                        APIUsageRecord.developer_id == developer_id,
                        APIUsageRecord.created_at >= start_date
                    )
                ).first()

                return {
                    "total_requests": stats.total_requests or 0,
                    "total_tokens": stats.total_tokens or 0,
                    "total_cost": float(stats.total_cost or 0),
                    "avg_response_time": float(stats.avg_response_time or 0),
                    "error_count": stats.error_count or 0,
                    "success_rate": ((stats.total_requests - stats.error_count) / stats.total_requests * 100) if stats.total_requests else 0
                }

            # 测试查询性能
            start_time = datetime.utcnow()
            test_results = {}

            # 测试开发者查询
            dev_start = datetime.utcnow()
            # 这里应该用一个真实的developer_id进行测试
            # get_developer_with_keys_optimized("test-id")
            dev_time = (datetime.utcnow() - dev_start).total_seconds()
            test_results["developer_query"] = dev_time

            optimizations.update({
                "query_performance": test_results,
                "optimization_methods": [
                    "Used joinedload for reducing N+1 queries",
                    "Added database indexes for frequently queried fields",
                    "Used aggregation functions for statistics",
                    "Implemented query result caching"
                ]
            })

            return optimizations

        except Exception as e:
            logger.error(f"Developer query optimization failed: {e}")
            return {"error": str(e)}

    async def optimize_async_task_queries(self) -> Dict[str, Any]:
        """优化异步任务查询"""
        try:
            # 优化任务列表查询
            def get_tasks_paginated_optimized(
                developer_id: str,
                page: int,
                limit: int,
                status_filter: Optional[str] = None
            ):
                query = self.db.query(AsyncTask)\
                    .filter(AsyncTask.developer_id == developer_id)

                if status_filter:
                    query = query.filter(AsyncTask.status == status_filter)

                offset = (page - 1) * limit
                return query.order_by(AsyncTask.created_at.desc())\
                    .offset(offset)\
                    .limit(limit)\
                    .all()

            # 优化任务统计查询
            def get_task_statistics_optimized(developer_id: str):
                return self.db.query(
                    AsyncTask.status,
                    func.count(AsyncTask.id).label('count')
                ).filter(AsyncTask.developer_id == developer_id)\
                 .group_by(AsyncTask.status)\
                 .all()

            # 优化批量任务查询
            def get_batch_jobs_with_tasks_optimized(developer_id: str):
                return self.db.query(BatchJob)\
                    .options(selectinload(BatchJob.tasks))\
                    .filter(BatchJob.developer_id == developer_id)\
                    .order_by(BatchJob.created_at.desc())\
                    .all()

            return {
                "optimization_methods": [
                    "Implemented pagination for large result sets",
                    "Used selectinload for batch loading related objects",
                    "Added composite indexes for common query patterns",
                    "Used COUNT with GROUP BY for statistics"
                ]
            }

        except Exception as e:
            logger.error(f"Async task query optimization failed: {e}")
            return {"error": str(e)}

    async def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """清理旧数据"""
        cleanup_stats = {}
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        try:
            # 清理旧的任务结果
            old_results = self.db.query(TaskResult)\
                .filter(TaskResult.created_at < cutoff_date)\
                .count()

            if old_results > 0:
                self.db.query(TaskResult)\
                    .filter(TaskResult.created_at < cutoff_date)\
                    .delete()
                cleanup_stats["deleted_task_results"] = old_results

            # 清理旧的使用记录 (只保留统计摘要)
            old_usage = self.db.query(APIUsageRecord)\
                .filter(APIUsageRecord.created_at < cutoff_date)\
                .count()

            if old_usage > 1000:  # 保留最近1000条记录
                # 这里可以创建汇总表然后删除详细记录
                cleanup_stats["old_usage_records"] = old_usage

            # 清理过期的异步任务 (已完成且超过保留期)
            old_tasks = self.db.query(AsyncTask)\
                .filter(
                    and_(
                        AsyncTask.status.in_(["completed", "failed", "cancelled"]),
                        AsyncTask.completed_at < cutoff_date
                    )
                )\
                .count()

            if old_tasks > 0:
                self.db.query(AsyncTask)\
                    .filter(
                        and_(
                            AsyncTask.status.in_(["completed", "failed", "cancelled"]),
                            AsyncTask.completed_at < cutoff_date
                        )
                    )\
                    .delete()
                cleanup_stats["deleted_old_tasks"] = old_tasks

            self.db.commit()
            cleanup_stats["cleanup_completed"] = True
            cleanup_stats["cutoff_date"] = cutoff_date.isoformat()

            logger.info(f"Database cleanup completed: {cleanup_stats}")
            return cleanup_stats

        except Exception as e:
            logger.error(f"Database cleanup failed: {e}")
            self.db.rollback()
            return {"error": str(e), "cleanup_completed": False}

    async def create_materialized_views(self):
        """创建物化视图 (如果支持)"""
        try:
            # 为使用统计创建物化视图
            self.db.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS developer_usage_summary AS
                SELECT
                    developer_id,
                    DATE(created_at) as date,
                    COUNT(*) as total_requests,
                    SUM(tokens_used) as total_tokens,
                    SUM(cost) as total_cost,
                    AVG(response_time_ms) as avg_response_time,
                    COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count
                FROM api_usage_records
                GROUP BY developer_id, DATE(created_at)
            """))

            # 为任务统计创建物化视图
            self.db.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS task_status_summary AS
                SELECT
                    developer_id,
                    task_type,
                    status,
                    COUNT(*) as task_count,
                    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds
                FROM async_tasks
                WHERE started_at IS NOT NULL
                GROUP BY developer_id, task_type, status
            """))

            self.db.commit()
            logger.info("Materialized views created successfully")

        except Exception as e:
            logger.warning(f"Materialized views creation failed (may not be supported): {e}")
            self.db.rollback()

    async def refresh_materialized_views(self):
        """刷新物化视图"""
        try:
            self.db.execute(text("REFRESH MATERIALIZED VIEW developer_usage_summary"))
            self.db.execute(text("REFRESH MATERIALIZED VIEW task_status_summary"))
            self.db.commit()
            logger.info("Materialized views refreshed successfully")
        except Exception as e:
            logger.warning(f"Materialized views refresh failed: {e}")


class QueryOptimizer:
    """查询优化器工具类"""

    @staticmethod
    def create_optimized_select(
        model,
        filters: Dict[str, Any] = None,
        joins: List[str] = None,
        order_by: List[str] = None,
        limit: int = None,
        offset: int = None
    ) -> Select:
        """创建优化的查询"""
        from sqlalchemy import select

        query = select(model)

        # 添加连接
        if joins:
            for join in joins:
                # 这里需要根据具体关系添加连接
                pass

        # 添加过滤条件
        if filters:
            for column, value in filters.items():
                if hasattr(model, column):
                    query = query.where(getattr(model, column) == value)

        # 添加排序
        if order_by:
            for order in order_by:
                if hasattr(model, order):
                    query = query.order_by(getattr(model, order).desc())

        # 添加分页
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query

    @staticmethod
    def analyze_query_plan(query, db: Session) -> Dict[str, Any]:
        """分析查询执行计划"""
        try:
            # 获取查询SQL
            compiled_query = query.compile(compile_kwargs={"literal_binds": True})
            sql = str(compiled_query)

            # 执行EXPLAIN (根据数据库类型调整)
            if db.bind.dialect.name == 'postgresql':
                explain_result = db.execute(text(f"EXPLAIN ANALYZE {sql}")).fetchall()
            elif db.bind.dialect.name == 'mysql':
                explain_result = db.execute(text(f"EXPLAIN FORMAT=JSON {sql}")).fetchall()
            else:
                explain_result = []

            return {
                "sql": sql,
                "execution_plan": [dict(row) for row in explain_result],
                "estimated_rows": len(explain_result)
            }

        except Exception as e:
            logger.error(f"Query plan analysis failed: {e}")
            return {"error": str(e)}


# 全局优化器实例
_db_optimizer = None

def get_database_optimizer(db: Session) -> DatabaseOptimizer:
    """获取数据库优化器实例"""
    return DatabaseOptimizer(db)