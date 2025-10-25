"""
数据库索引管理系统
提供智能索引创建、监控、分析和优化功能
"""
import asyncio
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from sqlalchemy import text, Index, MetaData, Table
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateIndex, DropIndex
import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class IndexInfo:
    """索引信息"""
    name: str
    table_name: str
    columns: List[str]
    index_type: str  # btree, hash, gist, gin, brin
    unique: bool
    partial: bool
    columns_types: List[str]
    size_bytes: int
    usage_stats: Dict[str, Any]
    created_at: datetime
    last_analyzed: Optional[datetime] = None

@dataclass
class IndexRecommendation:
    """索引推荐"""
    table_name: str
    columns: List[str]
    index_type: str
    reason: str
    impact_score: float
    estimated_improvement: str
    query_patterns: List[str]
    priority: str  # high, medium, low

class IndexManager:
    """索引管理器"""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.recommendations = []
        self.index_monitoring_enabled = True
        self.auto_index_creation = False  # 生产环境建议手动创建
        self.analysis_history = []
        self.index_metrics = {}

    async def analyze_table_indexes(self, table_name: str) -> Dict[str, Any]:
        """分析表的索引情况"""
        try:
            # 获取表的基本信息
            table_info = await self._get_table_info(table_name)

            # 获取现有索引
            existing_indexes = await self._get_existing_indexes(table_name)

            # 分析查询模式
            query_patterns = await self._analyze_query_patterns(table_name)

            # 分析列的分布和选择性
            column_stats = await self._analyze_column_statistics(table_name)

            # 生成索引推荐
            recommendations = await self._generate_index_recommendations(
                table_name, table_info, existing_indexes, query_patterns, column_stats
            )

            return {
                'table_name': table_name,
                'table_info': table_info,
                'existing_indexes': existing_indexes,
                'query_patterns': query_patterns,
                'column_stats': column_stats,
                'recommendations': recommendations,
                'analysis_time': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to analyze indexes for table {table_name}: {e}")
            return {'error': str(e)}

    async def _get_table_info(self, table_name: str) -> Dict[str, Any]:
        """获取表的基本信息"""
        try:
            # 表大小和行数
            size_sql = """
            SELECT
                pg_size_pretty(pg_total_relation_size(?)) as total_size,
                pg_size_pretty(pg_relation_size(?)) as table_size,
                pg_size_pretty(pg_total_relation_size(?) - pg_relation_size(?)) as indexes_size,
                (SELECT COUNT(*) FROM ?) as row_count
            """

            result = await self.db.execute(text(size_sql), (table_name, table_name, table_name, table_name, table_name))
            size_info = result.fetchone()

            return {
                'total_size': size_info.total_size,
                'table_size': size_info.table_size,
                'indexes_size': size_info.indexes_size,
                'row_count': size_info.row_count
            }

        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {e}")
            return {}

    async def _get_existing_indexes(self, table_name: str) -> List[IndexInfo]:
        """获取现有索引信息"""
        try:
            # 获取索引信息
            index_sql = f"""
            SELECT
                i.indexname as name,
                i.indexrelid,
                pg_size_pretty(pg_relation_size(i.indexrelid)) as size_bytes,
                ix.idx_scan as scan_count,
                ix.idx_tup_read as tuples_read,
                ix.idx_tup_fetch as tuples_fetched,
                schemaname,
                tablename
            FROM pg_indexes i
            JOIN pg_stat_user_indexes ix ON i.indexrelid = ix.indexrelid
            WHERE i.tablename = '{table_name}'
            ORDER BY i.indexname
            """

            result = await self.db.execute(text(index_sql))
            index_rows = result.fetchall()

            indexes = []
            for row in index_rows:
                # 获取索引列信息
                columns_sql = f"""
                SELECT
                    a.attname,
                    t.typname as type
                FROM pg_attribute a
                JOIN pg_type t ON a.atttypid = t.oid
                JOIN pg_index i ON i.indexrelid = ?
                JOIN pg_attribute a2 ON i.indexrelid = a2.attrelid
                WHERE a.attnum = ANY(i.indkey)
                AND a2.attrelid = a.attrelid
                ORDER BY a.attnum
                """

                cols_result = await self.db.execute(text(columns_sql), (row.indexrelid,))
                columns_info = cols_result.fetchall()

                columns = [col.attname for col in columns_info]
                column_types = [col.type for col in columns_info]

                indexes.append(IndexInfo(
                    name=row.name,
                    table_name=table_name,
                    columns=columns,
                    index_type='btree',  # 默认类型，实际需要从pg_class获取
                    unique=False,  # 需要从pg_index获取
                    partial=False,
                    columns_types=column_types,
                    size_bytes=int(row.size_bytes.replace('bytes', '').strip()) if row.size_bytes else 0,
                    usage_stats={
                        'scan_count': row.scan_count,
                        'tuples_read': row.tuples_read,
                        'tuples_fetched': row.tuples_fetched
                    },
                    created_at=datetime.utcnow()
                ))

            return indexes

        except Exception as e:
            logger.error(f"Failed to get existing indexes for {table_name}: {e}")
            return []

    async def _analyze_query_patterns(self, table_name: str) -> List[Dict]:
        """分析查询模式"""
        try:
            # 从pg_stat_statements分析查询模式
            query_patterns_sql = f"""
            SELECT
                query,
                calls,
                total_exec_time,
                mean_exec_time,
                rows
            FROM pg_stat_statements
            WHERE query LIKE '%{table_name}%'
            ORDER BY calls DESC
            LIMIT 20
            """

            result = await self.db.execute(text(query_patterns_sql))
            queries = result.fetchall()

            patterns = []
            for query in queries:
                # 提取WHERE条件中的列
                where_columns = self._extract_where_columns(query.query)
                # 提取JOIN条件中的列
                join_columns = self._extract_join_columns(query.query)
                # 提取ORDER BY中的列
                order_columns = self._extract_order_columns(query.query)
                # 提取GROUP BY中的列
                group_columns = self._extract_group_columns(query.query)

                patterns.append({
                    'query_preview': query.query[:100] + '...' if len(query.query) > 100 else query.query,
                    'calls': query.calls,
                    'avg_time_ms': query.mean_exec_time,
                    'where_columns': where_columns,
                    'join_columns': join_columns,
                    'order_columns': order_columns,
                    'group_columns': group_columns,
                    'rows_returned': query.rows
                })

            return patterns

        except Exception as e:
            logger.error(f"Failed to analyze query patterns for {table_name}: {e}")
            return []

    async def _analyze_column_statistics(self, table_name: str) -> Dict[str, Dict]:
        """分析列统计信息"""
        try:
            # 获取列的基本统计
            column_stats_sql = f"""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            AND table_schema = current_schema()
            """

            result = await self.db.execute(text(column_stats_sql))
            columns = result.fetchall()

            stats = {}
            for col in columns:
                try:
                    # 获取列的详细统计
                    if col.data_type in ('integer', 'bigint', 'smallint', 'numeric', 'decimal'):
                        stat_sql = f"""
                        SELECT
                            COUNT(*) as total_rows,
                            COUNT(DISTINCT {col.column_name}) as distinct_count,
                            MIN({col.column_name}) as min_value,
                            MAX({col.column_name}) as max_value,
                            AVG({col.column_name}) as avg_value
                        FROM {table_name}
                        """
                    else:
                        stat_sql = f"""
                        SELECT
                            COUNT(*) as total_rows,
                            COUNT(DISTINCT {col.column_name}) as distinct_count
                        FROM {table_name}
                        """

                    stat_result = await self.db.execute(text(stat_sql))
                    stat_data = stat_result.fetchone()

                    # 计算选择性（distinct_count / total_rows）
                    selectivity = stat_data.distinct_count / stat_data.total_rows if stat_data.total_rows > 0 else 0

                    stats[col.column_name] = {
                        'data_type': col.data_type,
                        'is_nullable': col.is_nullable == 'YES',
                        'default_value': col.column_default,
                        'total_rows': stat_data.total_rows,
                        'distinct_count': stat_data.distinct_count,
                        'selectivity': selectivity,
                        'is_selective': selectivity < 0.1,  # 选择性高的列（<10%）
                        'is_low_cardinality': selectivity < 0.01,  # 基数低的列（<1%）
                        'has_stats': True
                    }

                    # 为数值类型添加范围信息
                    if col.data_type in ('integer', 'bigint', 'smallint', 'numeric', 'decimal') and hasattr(stat_data, 'min_value'):
                        stats[col.column_name].update({
                            'min_value': stat_data.min_value,
                            'max_value': stat_data.max_value,
                            'avg_value': stat_data.avg_value
                        })

                except Exception as e:
                    # 如果统计查询失败，只保存基本信息
                    stats[col.column_name] = {
                        'data_type': col.data_type,
                        'is_nullable': col.is_nullable == 'YES',
                        'default_value': col.column_default,
                        'has_stats': False
                    }

            return stats

        except Exception as e:
            logger.error(f"Failed to analyze column statistics for {table_name}: {e}")
            return {}

    async def _generate_index_recommendations(self, table_name: str, table_info: Dict,
                                           existing_indexes: List[IndexInfo], query_patterns: List[Dict],
                                           column_stats: Dict[str, Dict]) -> List[IndexRecommendation]:
        """生成索引推荐"""
        recommendations = []

        # 分析现有索引覆盖的列
        indexed_columns = set()
        for index in existing_indexes:
            indexed_columns.update(index.columns)

        # 分析查询模式中的列
        all_query_columns = set()
        column_priority = defaultdict(int)  # 列在查询中出现的次数

        for pattern in query_patterns:
            all_query_columns.update(pattern['where_columns'])
            all_query_columns.update(pattern['join_columns'])
            all_query_columns.update(pattern['order_columns'])
            all_query_columns.update(pattern['group_columns'])

            for column in list(all_query_columns):
                column_priority[column] += pattern['calls']

        # 为高频查询且未索引的列生成推荐
        for column, priority in sorted(column_priority.items(), key=lambda x: x[1], reverse=True):
            if column not in indexed_columns and column in column_stats:
                col_stat = column_stats[column]

                # 跳过不适合索引的列
                if not self._should_index_column(column, col_stat):
                    continue

                # 计算推荐分数
                impact_score = self._calculate_impact_score(column, col_stat, priority, query_patterns)

                # 确定索引类型
                index_type = self._determine_index_type(column, col_stat, query_patterns)

                # 确定优先级
                priority_level = self._determine_priority(impact_score)

                # 生成推荐
                recommendation = IndexRecommendation(
                    table_name=table_name,
                    columns=[column],
                    index_type=index_type,
                    reason=self._generate_recommendation_reason(column, col_stat, priority, query_patterns),
                    impact_score=impact_score,
                    estimated_improvement=self._estimate_improvement(impact_score),
                    query_patterns=[p['query_preview'] for p in query_patterns[:3] if column in p['where_columns']],
                    priority=priority_level
                )

                recommendations.append(recommendation)

        # 分析复合索引推荐
        composite_recommendations = await self._generate_composite_index_recommendations(
            table_name, existing_indexes, query_patterns, column_stats
        )
        recommendations.extend(composite_recommendations)

        # 按影响分数排序
        recommendations.sort(key=lambda x: x.impact_score, reverse=True)

        return recommendations[:10]  # 最多返回10个推荐

    def _should_index_column(self, column: str, col_stat: Dict) -> bool:
        """判断列是否应该创建索引"""
        # 不索引的列类型
        non_indexable_types = ['text', 'bytea', 'json', 'jsonb', 'xml']
        if col_stat['data_type'] in non_indexable_types:
            return False

        # 不索引低基数的列（除非是外键）
        if col_stat.get('is_low_cardinality', False) and col_stat['data_type'] not in ['integer', 'bigint']:
            return False

        # 不索引布尔值列（除非是状态标志）
        if col_stat['data_type'] in ['boolean', 'bool']:
            return False

        # 不索引选择性太高的列（几乎所有值都不同）
        if col_stat.get('selectivity', 0) > 0.9:
            return False

        return True

    def _calculate_impact_score(self, column: str, col_stat: Dict, priority: int, query_patterns: List[Dict]) -> float:
        """计算索引影响分数"""
        score = 0.0

        # 基础分数（查询优先级）
        score += min(priority / 100.0, 1.0) * 30

        # 选择性分数
        if col_stat.get('is_selective', False):
            score += 20
        elif col_stat.get('selectivity', 0) < 0.5:
            score += 15
        elif col_stat.get('selectivity', 0) < 0.8:
            score += 10

        # 数据类型分数
        if col_stat['data_type'] in ['integer', 'bigint', 'timestamp', 'date']:
            score += 15
        elif col_stat['data_type'] in ['varchar', 'character varying']:
            score += 10

        # 查询模式分数
        in_where_count = sum(1 for p in query_patterns if column in p['where_columns'])
        in_order_count = sum(1 for p in query_patterns if column in p['order_columns'])
        in_join_count = sum(1 for p in query_patterns if column in p['join_columns'])

        if in_where_count > 0:
            score += 25  # WHERE条件中的列最重要
        if in_order_count > 0:
            score += 15  # ORDER BY中的列也很重要
        if in_join_count > 0:
            score += 20  # JOIN条件中的列很重要

        return min(score, 100.0)

    def _determine_index_type(self, column: str, col_stat: Dict, query_patterns: List[Dict]) -> str:
        """确定索引类型"""
        # 检查是否需要特殊索引类型
        for pattern in query_patterns:
            query = pattern['query_preview'].lower()

            # 数组索引
            if any(array_type in query for array_type in ['array(', 'json', 'jsonb']) and column in query:
                return 'gin'

            # 全文搜索索引
            if any(search_type in query for search_type in ['like', 'textsearch', 'to_tsvector']) and column in query:
                return 'gin'

            # 空间索引
            if any(spatial_type in query for spatial_type in ['st_', 'postgis']) and column in query:
                return 'gist'

            # 范围索引
            if any(range_op in query for range_op in ['>', '<', '>=', '<=']) and column in query:
                return 'btree'

        # 默认使用B-tree索引
        return 'btree'

    def _determine_priority(self, impact_score: float) -> str:
        """确定优先级"""
        if impact_score >= 80:
            return 'high'
        elif impact_score >= 50:
            return 'medium'
        else:
            return 'low'

    def _generate_recommendation_reason(self, column: str, col_stat: Dict, priority: int, query_patterns: List[Dict]) -> str:
        """生成推荐原因"""
        reasons = []

        # 查询频率原因
        if priority > 100:
            reasons.append(f"列 '{column}' 在查询中出现频率高（{priority}次）")

        # 选择性原因
        if col_stat.get('is_selective', False):
            reasons.append(f"列 '{column}' 选择性好（{col_stat.get('selectivity', 0):.2f}）")

        # 查询模式原因
        in_where = sum(1 for p in query_patterns if column in p['where_columns'])
        if in_where > 0:
            reasons.append(f"列 '{column}' 经常在WHERE条件中使用")

        in_order = sum(1 for p in query_patterns if column in p['order_columns'])
        if in_order > 0:
            reasons.append(f"列 '{column}' 经常在ORDER BY中使用")

        in_join = sum(1 for p in query_patterns if column in p['join_columns'])
        if in_join > 0:
            reasons.append(f"列 '{column}' 经常在JOIN条件中使用")

        return "；".join(reasons) if reasons else f"列 '{column}' 适合创建索引"

    def _estimate_improvement(self, impact_score: float) -> str:
        """估算性能提升"""
        if impact_score >= 90:
            return "显著提升（预计查询速度提升50-80%）"
        elif impact_score >= 70:
            return "明显提升（预计查询速度提升30-50%）"
        elif impact_score >= 50:
            return "适度提升（预计查询速度提升20-30%）"
        elif impact_score >= 30:
            return "轻微提升（预计查询速度提升10-20%）"
        else:
            return "少量提升（预计查询速度提升5-10%）"

    async def _generate_composite_index_recommendations(self, table_name: str, existing_indexes: List[IndexInfo],
                                                      query_patterns: List[Dict], column_stats: Dict[str, Dict]) -> List[IndexRecommendation]:
        """生成复合索引推荐"""
        recommendations = []

        # 分析常用的列组合
        column_combinations = self._analyze_column_combinations(query_patterns, column_stats)

        for combo, frequency in column_combinations:
            # 跳过已存在的复合索引
            existing_combo = any(
                set(index.columns) == set(combo) for index in existing_indexes
            )
            if existing_combo:
                continue

            # 检查组合中的列是否都适合索引
            if not all(col in column_stats and self._should_index_column(col, column_stats[col]) for col in combo):
                continue

            # 计算复合索引的影响分数
            impact_score = self._calculate_composite_impact_score(combo, column_stats, frequency, query_patterns)

            if impact_score > 40:  # 只推荐高影响的复合索引
                recommendation = IndexRecommendation(
                    table_name=table_name,
                    columns=combo,
                    index_type='btree',
                    reason=f"列组合 '{', '.join(combo)}' 经常一起使用（{frequency}次）",
                    impact_score=impact_score,
                    estimated_improvement=self._estimate_improvement(impact_score),
                    query_patterns=[p['query_preview'] for p in query_patterns[:2] if any(col in p['query_preview'] for col in combo)] or p['query_preview'] for p in query_patterns if any(col in p['query_preview'] for col in combo)],
                    priority=self._determine_priority(impact_score)
                )

                recommendations.append(recommendation)

        return recommendations

    def _analyze_column_combinations(self, query_patterns: List[Dict], column_stats: Dict[str, Dict]) -> List[Tuple]:
        """分析列组合"""
        combinations = defaultdict(int)

        for pattern in query_patterns:
            # 分析WHERE条件中的列组合
            where_cols = pattern['where_columns']
            for i in range(len(where_cols)):
                for j in range(i + 1, min(len(where_cols), i + 3)):  # 最多3列组合
                    combo = tuple(sorted(where_cols[i:j+1]))
                    combinations[combo] += pattern['calls']

            # 分析ORDER BY中的列组合
            order_cols = pattern['order_columns']
            for i in range(len(order_cols)):
                for j in range(i + 1, min(len(order_cols), i + 2)):
                    combo = tuple(sorted(order_cols[i:j+1]))
                    combinations[combo] += pattern['calls']

        # 按频率排序
        return sorted(combinations.items(), key=lambda x: x[1], reverse=True)

    def _calculate_composite_impact_score(self, combo: tuple, column_stats: Dict[str, Dict], frequency: int, query_patterns: List[Dict]) -> float:
        """计算复合索引影响分数"""
        score = 0.0

        # 基础分数（组合频率）
        score += min(frequency / 50.0, 1.0) * 40

        # 列数量分数（2-3列最佳）
        if len(combo) == 2:
            score += 20
        elif len(combo) == 3:
            score += 15

        # 列选择性分数
        selectivity_sum = sum(column_stats.get(col, {}).get('selectivity', 0) for col in combo)
        avg_selectivity = selectivity_sum / len(combo)
        if avg_selectivity < 0.5:
            score += 20
        elif avg_selectivity < 0.8:
            score += 10

        # 查询模式分数
        combo_in_where = sum(1 for p in query_patterns if all(col in p['query_preview'] for col in combo))
        if combo_in_where > 0:
            score += 20

        return min(score, 100.0)

    def _extract_where_columns(self, query: str) -> List[str]:
        """提取WHERE条件中的列"""
        # 简化的列提取，实际应用中需要更复杂的SQL解析
        where_match = re.search(r'where\s+(.+?)(?:\s+order|$|group\s+)', query, re.IGNORECASE)
        if where_match:
            where_clause = where_match.group(1)
            # 提取列名（简化处理）
            columns = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*[\=<>!]+|\b([a-zA-Z_][a-zA-Z0-9_]*)\s+in\b', where_clause)
            return [col[0] if col[0] else col[1] for col in columns]
        return []

    def _extract_join_columns(self, query: str) -> List[str]:
        """提取JOIN条件中的列"""
        join_columns = []
        join_matches = re.findall(r'join\s+\w+\s+(?:as\s+\w+\s+)?on\s+([^=\s]+)\s*=\s*([^=\s]+)', query, re.IGNORECASE)
        for match in join_matches:
            join_columns.extend([match[0].strip(), match[1].strip()])
        return list(set(join_columns))

    def _extract_order_columns(self, query: str) -> List[str]:
        """提取ORDER BY中的列"""
        order_match = re.search(r'order\s+by\s+(.+?)(?:\s+limit|$|group\s+)', query, re.IGNORECASE)
        if order_match:
            order_clause = order_match.group(1)
            return [col.strip() for col in order_clause.split(',')]
        return []

    def _extract_group_columns(self, query: str) -> List[str]:
        """提取GROUP BY中的列"""
        group_match = re.search(r'group\s+by\s+(.+?)(?:\s+order|$|having\s+)', query, re.IGNORECASE)
        if group_match:
            group_clause = group_match.group(1)
            return [col.strip() for col in group_clause.split(',')]
        return []

    async def create_recommended_indexes(self, recommendations: List[IndexRecommendation], auto_create: bool = False) -> Dict[str, bool]:
        """创建推荐的索引"""
        results = {}

        for rec in recommendations:
            if auto_create and rec.priority == 'high':
                # 自动创建高优先级索引
                success = await self._create_index(rec)
                results[rec.name] = success
                if success:
                    logger.info(f"Auto-created index: {rec.name}")
            else:
                # 记录推荐但不创建
                results[rec.name] = False
                logger.info(f"Index recommendation (manual creation required): {rec.name} - {rec.reason}")

        return results

    async def _create_index(self, recommendation: IndexRecommendation) -> bool:
        """创建单个索引"""
        try:
            # 生成索引名称
            index_name = f"idx_{recommendation.table_name}_{'_'.join(recommendation.columns)}"

            # 构建SQL语句
            columns_str = ', '.join(recommendation.columns)
            sql = f"CREATE INDEX CONCURRENTLY {index_name} ON {recommendation.table_name} ({columns_str})"

            # 执行索引创建
            await self.db.execute(text(sql))
            await self.db.commit()

            logger.info(f"Successfully created index: {index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create index for {recommendation.table_name}: {e}")
            await self.db.rollback()
            return False

    async def drop_unused_indexes(self, unused_threshold_days: int = 30) -> List[str]:
        """删除未使用的索引"""
        try:
            # 找出长时间未使用的索引
            unused_sql = f"""
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan
            FROM pg_stat_user_indexes
            WHERE idx_scan = 0
            AND schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY tablename, indexname
            """

            result = await self.db.execute(text(unused_sql))
            unused_indexes = result.fetchall()

            dropped_indexes = []
            for index in unused_indexes:
                try:
                    # 删除索引
                    drop_sql = f"DROP INDEX CONCURRENTLY {index.indexname}"
                    await self.db.execute(text(drop_sql))
                    await self.db.commit()

                    dropped_indexes.append(index.indexname)
                    logger.info(f"Dropped unused index: {index.indexname}")

                except Exception as e:
                    logger.error(f"Failed to drop index {index.indexname}: {e}")
                    await self.db.rollback()

            return dropped_indexes

        except Exception as e:
            logger.error(f"Failed to drop unused indexes: {e}")
            return []

    async def get_index_recommendations_summary(self) -> Dict[str, Any]:
        """获取索引推荐摘要"""
        return {
            'total_recommendations': len(self.recommendations),
            'high_priority_count': len([r for r in self.recommendations if r.priority == 'high']),
            'medium_priority_count': len([r for r in self.recommendations if r.priority == 'medium']),
            'low_priority_count': len([r for r in self.recommendations if r.priority == 'low']),
            'recommendations': [asdict(r) for r in self.recommendations[:20]]  # 返回前20个推荐
        }

# 全局索引管理器实例
index_manager = None

def get_index_manager(db_session: Session) -> IndexManager:
    """获取索引管理器实例"""
    global index_manager
    if index_manager is None:
        index_manager = IndexManager(db_session)
    return index_manager