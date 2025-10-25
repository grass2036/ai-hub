"""
数据库查询优化器
提供查询性能分析、索引建议、慢查询优化等功能
"""
import asyncio
import time
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
from sqlalchemy import text, Index, inspect
from sqlalchemy.orm import Session
from sqlalchemy.engine import create_engine, Engine
import logging
import re
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class QueryProfile:
    """查询性能分析结果"""
    query_name: str
    query: str
    execution_time: float
    rows_returned: int
    bytes_received: int
    index_used: Optional[str]
    timestamp: datetime
    database: str
    plan_analysis: Optional[Dict] = None
    optimization_suggestions: List[str] = None

@dataclass
class SlowQuery:
    """慢查询记录"""
    id: str
    query_name: str
    query: str
    execution_time: float
    threshold: float
    call_count: int
    avg_execution_time: float
    max_execution_time: float
    last_seen: datetime
    database: str
    parameters: Optional[Dict] = None
    stack_trace: Optional[str] = None

class QueryOptimizer:
    """查询优化器"""

    def __init__(self, db_session: Session, engine: Engine = None):
        self.db = db_session
        self.engine = engine or db_session.bind
        self.slow_queries = deque(maxlen=1000)
        self.query_profiles = deque(maxlen=2000)
        self.index_suggestions = {}
        self.query_cache = {}
        self.performance_stats = {
            'total_queries': 0,
            'total_time': 0.0,
            'avg_time': 0.0,
            'slow_queries_count': 0,
            'fast_queries_count': 0
        }

        # 慢查询阈值（毫秒）
        self.slow_query_threshold = 1000  # 1秒

    @asynccontextmanager
    async def profile_query(self, query_name: str):
        """查询性能分析上下文管理器"""
        start_time = time.time()
        query_text = ""

        try:
            # 执行查询前的准备
            logger.debug(f"Starting query profiling for: {query_name}")
            yield

        except Exception as e:
            logger.error(f"Error in query {query_name}: {e}")
            raise
        finally:
            # 记录查询性能
            execution_time = (time.time() - start_time) * 1000  # 转换为毫秒

            profile = QueryProfile(
                query_name=query_name,
                query=query_text,
                execution_time=execution_time,
                rows_returned=0,  # 需要从查询结果中获取
                bytes_received=0,   # 需要从查询结果中获取
                index_used=None,     # 需要从执行计划中获取
                timestamp=datetime.utcnow(),
                database=self.engine.url.database if self.engine.url else "unknown"
            )

            self._record_query_profile(profile)

    def _record_query_profile(self, profile: QueryProfile):
        """记录查询性能"""
        self.query_profiles.append(profile)

        # 更新性能统计
        self.performance_stats['total_queries'] += 1
        self.performance_stats['total_time'] += profile.execution_time
        self.performance_stats['avg_time'] = (
            self.performance_stats['total_time'] / self.performance_stats['total_queries']
        )

        # 检查是否为慢查询
        if profile.execution_time > self.slow_query_threshold:
            self.performance_stats['slow_queries_count'] += 1

            # 分析慢查询
            slow_query = SlowQuery(
                id=f"slow_{int(time.time())}_{len(self.slow_queries)}",
                query_name=profile.query_name,
                query=profile.query,
                execution_time=profile.execution_time,
                threshold=self.slow_query_threshold,
                call_count=1,
                avg_execution_time=profile.execution_time,
                max_execution_time=profile.execution_time,
                last_seen=profile.timestamp,
                database=profile.database
            )

            self._record_slow_query(slow_query)
        else:
            self.performance_stats['fast_queries_count'] += 1

    def _record_slow_query(self, slow_query: SlowQuery):
        """记录慢查询"""
        # 检查是否已存在相同的慢查询
        existing_query = None
        for i, existing in enumerate(self.slow_queries):
            if (existing.query_name == slow_query.query_name and
                self._normalize_query(existing.query) == self._normalize_query(slow_query.query)):
                existing_query = existing
                break

        if existing_query:
            # 更新现有记录
            existing_query.call_count += 1
            existing_query.avg_execution_time = (
                (existing_query.avg_execution_time * (existing_query.call_count - 1) +
                 slow_query.execution_time) / existing_query.call_count
            )
            existing_query.max_execution_time = max(
                existing_query.max_execution_time, slow_query.execution_time
            )
            existing_query.last_seen = slow_query.last_seen
        else:
            # 添加新记录
            self.slow_queries.append(slow_query)

            # 分析并生成优化建议
            suggestions = self.analyze_slow_query(slow_query)
            if suggestions:
                self.index_suggestions[slow_query.query_name] = suggestions

    def _normalize_query(self, query: str) -> str:
        """标准化SQL查询（去除参数差异）"""
        if not query:
            return ""

        # 移除注释
        query = re.sub(r'--.*?\n', '', query)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)

        # 移除多余空白
        query = re.sub(r'\s+', ' ', query).strip()

        # 移除字符串字面量（简化处理）
        query = re.sub(r"'[^']*'", "'VALUE'", query)
        query = re.sub(r'"[^"]*"', '"VALUE"', query)

        # 移除数字
        query = re.sub(r'\b\d+\b', 'N', query)

        return query.lower()

    async def create_optimal_indexes(self):
        """创建优化索引"""
        try:
            # 定义需要创建的索引
            indexes_to_create = [
                # 用户表索引
                {
                    'name': 'idx_users_email_active',
                    'table': 'users',
                    'columns': ['email'],
                    'unique': True,
                    'where': 'is_active = true',
                    'description': '用户邮箱激活状态索引'
                },
                {
                    'name': 'idx_users_org_created',
                    'table': 'users',
                    'columns': ['organization_id', 'created_at'],
                    'description': '组织用户创建时间复合索引'
                },
                {
                    'name': 'idx_users_type_created',
                    'table': 'users',
                    'columns': ['type', 'created_at'],
                    'description': '用户类型创建时间复合索引'
                },

                # API密钥表索引
                {
                    'name': 'idx_api_keys_user_active',
                    'table': 'api_keys',
                    'columns': ['user_id', 'is_active'],
                    'description': '用户API密钥状态索引'
                },
                {
                    'name': 'idx_api_keys_last_used',
                    'table': 'api_keys',
                    'columns': ['last_used_at'],
                    'description': 'API密钥最后使用时间索引'
                },
                {
                    'name': 'idx_api_keys_expires',
                    'table': 'api_keys',
                    'columns': ['expires_at'],
                    'description': 'API密钥过期时间索引'
                },

                # 会话表索引
                {
                    'name': 'idx_sessions_user_created',
                    'table': 'sessions',
                    'columns': ['user_id', 'created_at'],
                    'description': '用户会话创建时间索引'
                },
                {
                    'name': 'idx_sessions_active_created',
                    'table': 'sessions',
                    'columns': ['is_active', 'created_at'],
                    'where': 'is_active = true',
                    'description': '活跃会话创建时间索引'
                },

                # 使用记录表索引
                {
                    'name': 'idx_usage_records_user_date',
                    'table': 'usage_records',
                    'columns': ['user_id', 'created_at'],
                    'description': '用户使用记录日期索引'
                },
                {
                    'name': 'idx_usage_records_model_date',
                    'table': 'usage_records',
                    'columns': ['model_name', 'created_at'],
                    'description': '模型使用记录日期索引'
                },
                {
                    'name': 'idx_usage_records_org_date',
                    'table': 'usage_records',
                    'columns': ['organization_id', 'created_at'],
                    'description': '组织使用记录日期索引'
                },

                # 组织表索引
                {
                    'name': 'idx_organizations_created',
                    'table': 'organizations',
                    'columns': ['created_at'],
                    'description': '组织创建时间索引'
                },
                {
                    'name': 'idx_organizations_plan',
                    'table': 'organizations',
                    'columns': ['subscription_plan'],
                    'description': '组织订阅计划索引'
                },

                # 团队表索引
                {
                    'name': 'idx_teams_org_created',
                    'table': 'teams',
                    'columns': ['organization_id', 'created_at'],
                    'description': '组织团队创建时间索引'
                },

                # 预算表索引
                {
                    'name': 'idx_budgets_org_period',
                    'table': 'budgets',
                    'columns': ['organization_id', 'period_start', 'period_end'],
                    'description': '组织预算周期复合索引'
                },
                {
                    'name': 'idx_budgets_user',
                    'table': 'budgets',
                    'columns': ['user_id'],
                    'description': '用户预算索引'
                },

                # 监控数据索引
                {
                    'name': 'idx_performance_metrics_name_time',
                    'table': 'performance_metrics',
                    'columns': ['metric_name', 'timestamp'],
                    'description': '性能指标名称时间索引'
                },
                {
                    'name': 'idx_business_metrics_user_time',
                    'table': 'business_metrics',
                    'columns': ['user_id', 'timestamp'],
                    'description': '业务指标用户时间索引'
                },
                {
                    'name': 'idx_business_metrics_org_time',
                    'table': 'business_metrics',
                    'columns': ['organization_id', 'timestamp'],
                    'description': '业务指标组织时间索引'
                },
                {
                    'name': 'idx_system_metrics_host_time',
                    'table': 'system_metrics',
                    'columns': ['host_name', 'timestamp'],
                    'description': '系统指标主机时间索引'
                }
            ]

            created_count = 0
            for index_config in indexes_to_create:
                if await self._create_index(index_config):
                    created_count += 1

            logger.info(f"Successfully created {created_count} database indexes")
            return created_count

        except Exception as e:
            logger.error(f"Error creating database indexes: {e}")
            return 0

    async def _create_index(self, index_config: Dict) -> bool:
        """创建单个索引"""
        try:
            table_name = index_config['table']
            index_name = index_config['name']
            columns = index_config['columns']

            # 构建SQL语句
            unique_constraint = "UNIQUE " if index_config.get('unique', False) else ""
            where_clause = f" WHERE {index_config['where']}" if 'where' in index_config else ""

            sql = f"""
            CREATE {unique_constraint}INDEX CONCURRENTLY IF NOT EXISTS {index_name}
            ON {table_name} ({', '.join(columns)}){where_clause}
            """

            # 执行索引创建
            result = await self.db.execute(text(sql))
            await self.db.commit()

            logger.info(f"Created index: {index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create index {index_config['name']}: {e}")
            await self.db.rollback()
            return False

    async def analyze_slow_queries(self) -> List[Dict]:
        """分析慢查询"""
        try:
            # 获取PostgreSQL的慢查询统计
            slow_query_sql = """
            SELECT
                query,
                calls,
                total_time,
                mean_time,
                rows,
                100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
            FROM pg_stat_statements
            WHERE mean_time > 100
            ORDER BY mean_time DESC
            LIMIT 20
            """

            result = await self.db.execute(text(slow_query_sql))
            slow_queries = result.fetchall()

            analysis = []
            for query in slow_queries:
                analysis.append({
                    'query': query.query[:200] + '...' if len(query.query) > 200 else query.query,
                    'calls': query.calls,
                    'total_time_ms': query.total_time,
                    'avg_time_ms': query.mean_time,
                    'rows_returned': query.rows,
                    'cache_hit_percent': query.hit_percent,
                    'optimization_suggestions': self._suggest_optimizations(query.query, query.mean_time)
                })

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze slow queries: {e}")
            return []

    def _suggest_optimizations(self, query: str, execution_time: float) -> List[str]:
        """为查询提供优化建议"""
        suggestions = []
        query_lower = query.lower()

        # 检查缺少WHERE条件
        if 'where' not in query_lower and 'delete' not in query_lower:
            suggestions.append("考虑添加WHERE条件限制结果集，避免全表扫描")

        # 检查是否使用SELECT *
        if 'select *' in query_lower:
            suggestions.append("避免使用SELECT *，只查询需要的列，减少I/O和网络传输")

        # 检查是否有适当的LIMIT
        if 'limit' not in query_lower and 'count(' not in query_lower:
            suggestions.append("考虑添加LIMIT限制返回的行数，特别是在大表查询中")

        # 检查JOIN优化
        if 'join' in query_lower:
            if 'hash join' not in query_lower and 'nested loop' not in query_lower:
                suggestions.append("考虑使用HASH JOIN或优化JOIN条件，确保JOIN列有索引")

            if 'on ' not in query_lower:
                suggestions.append("确保JOIN条件正确，并且JOIN列上有适当索引")

        # 检查ORDER BY优化
        if 'order by' in query_lower:
            if 'limit' not in query_lower:
                suggestions.append("ORDER BY没有LIMIT可能导致内存问题，考虑添加LIMIT或创建索引")

            suggestions.append("确保ORDER BY列有索引支持，或者考虑在应用层排序")

        # 检查子查询优化
        if 'select' in query_lower and query_lower.count('(') > 2:
            suggestions.append("考虑将子查询重写为JOIN，或者使用EXISTS替代IN子查询")

        # 检查聚合函数优化
        if any(func in query_lower for func in ['group by', 'sum(', 'count(', 'avg(', 'max(', 'min(']):
            suggestions.append("确保GROUP BY列有索引，考虑使用物化视图优化复杂聚合查询")

        # 检查IN子句优化
        if ' in (' in query_lower:
            suggestions.append("大IN列表可能导致性能问题，考虑使用临时表或VALUES子句")

        # 基于执行时间的建议
        if execution_time > 5000:  # 超过5秒
            suggestions.append("查询执行时间过长，建议检查执行计划并考虑分页")
        elif execution_time > 2000:  # 超过2秒
            suggestions.append("查询执行时间较长，建议添加缓存或优化查询逻辑")

        # 检查正则表达式使用
        if 'regex' in query_lower or '~' in query_lower:
            suggestions.append("正则表达式查询通常很慢，考虑添加函数索引或使用全文搜索")

        return suggestions

    async def optimize_table_statistics(self):
        """更新表统计信息"""
        try:
            tables = [
                'users', 'organizations', 'teams', 'api_keys', 'sessions',
                'usage_records', 'performance_metrics', 'business_metrics',
                'system_metrics', 'budgets'
            ]

            for table in tables:
                try:
                    await self.db.execute(text(f"ANALYZE {table};"))
                    logger.info(f"Updated statistics for table: {table}")
                except Exception as e:
                    logger.warning(f"Failed to analyze table {table}: {e}")

            await self.db.commit()
            logger.info("Table statistics optimization completed")

        except Exception as e:
            logger.error(f"Failed to optimize table statistics: {e}")
            await self.db.rollback()

    async def get_missing_indexes(self) -> List[Dict]:
        """获取缺失的索引建议"""
        try:
            # 查询未使用的表或列
            missing_indexes = []

            # 检查外键约束是否有索引
            fk_sql = """
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
            """

            result = await self.db.execute(text(fk_sql))
            foreign_keys = result.fetchall()

            for fk in foreign_keys:
                # 检查外键列是否有索引
                index_check_sql = f"""
                SELECT COUNT(*) as has_index
                FROM pg_indexes
                WHERE tablename = '{fk.table_name}'
                AND indexdef LIKE '%{fk.column_name}%'
                """

                index_result = await self.db.execute(text(index_check_sql))
                has_index = index_result.scalar()

                if not has_index:
                    missing_indexes.append({
                        'type': 'foreign_key',
                        'table': fk.table_name,
                        'columns': [fk.column_name],
                        'reason': '外键列缺少索引，可能影响JOIN性能',
                        'impact': 'high',
                        'suggested_index': f"idx_{fk.table_name}_{fk.column_name}"
                    })

            # 检查GROUP BY列是否有索引
            group_by_sql = """
            SELECT DISTINCT query
            FROM pg_stat_statements
            WHERE query LIKE '%GROUP BY%'
            LIMIT 10
            """

            result = await self.db.execute(text(group_by_sql))
            group_by_queries = result.fetchall()

            for query in group_by_queries:
                # 简单的GROUP BY列提取（实际应用中需要更复杂的解析）
                group_by_match = re.search(r'group by\s+(.+?)(?:\s+order|$)', query.query, re.IGNORECASE)
                if group_by_match:
                    group_columns = [col.strip() for col in group_by_match.group(1).split(',')]
                    for column in group_columns:
                        if column and not column.isdigit():
                            missing_indexes.append({
                                'type': 'group_by',
                                'table': 'unknown',  # 需要解析查询确定表
                                'columns': [column],
                                'reason': f'GROUP BY列 {column} 缺少索引',
                                'impact': 'medium',
                                'suggested_index': f"idx_unknown_{column}"
                            })

            return missing_indexes

        except Exception as e:
            logger.error(f"Failed to analyze missing indexes: {e}")
            return []

    async def get_index_usage_stats(self) -> List[Dict]:
        """获取索引使用统计"""
        try:
            index_stats_sql = """
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch,
                pg_size_pretty(pg_relation_size(indexrelid::regclass)) as index_size
            FROM pg_stat_user_indexes
            ORDER BY idx_scan DESC
            """

            result = await self.db.execute(text(index_stats_sql))
            index_stats = result.fetchall()

            stats = []
            for stat in index_stats:
                stats.append({
                    'schema': stat.schemaname,
                    'table': stat.tablename,
                    'index': stat.indexname,
                    'scan_count': stat.idx_scan,
                    'tuples_read': stat.idx_tup_read,
                    'tuples_fetched': stat.idx_tup_fetch,
                    'size': stat.index_size,
                    'usage_rate': 'high' if stat.idx_scan > 1000 else 'medium' if stat.idx_scan > 100 else 'low',
                    'recommendation': self._get_index_recommendation(stat)
                })

            return stats

        except Exception as e:
            logger.error(f"Failed to get index usage stats: {e}")
            return []

    def _get_index_recommendation(self, stat) -> str:
        """获取索引使用建议"""
        if stat.idx_scan == 0:
            return "索引从未被使用，考虑删除以节省空间"
        elif stat.idx_scan < 10:
            return "索引使用频率很低，评估是否真的需要"
        elif stat.idx_scan > 10000:
            return "索引使用频繁，性能良好"
        else:
            return "索引使用正常"

    def get_performance_report(self) -> Dict:
        """获取性能报告"""
        slow_queries_list = list(self.slow_queries)

        return {
            'summary': self.performance_stats,
            'slow_queries': {
                'total_count': len(slow_queries_list),
                'top_10': [
                    {
                        'query_name': sq.query_name,
                        'avg_time_ms': sq.avg_execution_time,
                        'max_time_ms': sq.max_execution_time,
                        'call_count': sq.call_count,
                        'last_seen': sq.last_seen.isoformat()
                    }
                    for sq in sorted(slow_queries_list,
                                    key=lambda x: x.avg_execution_time,
                                    reverse=True)[:10]
                ]
            },
            'index_analysis': {
                'total_profiles': len(self.query_profiles),
                'index_suggestions': self.index_suggestions
            },
            'recommendations': self._generate_performance_recommendations()
        }

    def _generate_performance_recommendations(self) -> List[str]:
        """生成性能优化建议"""
        recommendations = []

        stats = self.performance_stats

        if stats['slow_queries_count'] > stats['fast_queries_count']:
            recommendations.append("慢查询比例过高，需要优化查询逻辑或添加索引")

        if stats['avg_time'] > 100:
            recommendations.append("平均查询时间较长，考虑添加缓存或优化数据库结构")

        if stats['total_queries'] > 1000 and stats['slow_queries_count'] / stats['total_queries'] > 0.1:
            recommendations.append("慢查询率超过10%，建议进行全面的性能调优")

        if len(self.index_suggestions) > 0:
            recommendations.append(f"发现{len(self.index_suggestions)}个索引优化建议")

        return recommendations

# 全局查询优化器实例
query_optimizer = None

def get_query_optimizer(db_session: Session = None, engine: Engine = None) -> QueryOptimizer:
    """获取查询优化器实例"""
    global query_optimizer
    if query_optimizer is None:
        query_optimizer = QueryOptimizer(db_session, engine)
    return query_optimizer