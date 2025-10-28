"""
性能优化建议系统
基于性能分析结果生成智能优化建议和自动化建议
"""

import asyncio
import time
import json
import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Set, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from backend.core.performance.performance_analyzer import (
    IntelligentPerformanceAnalyzer, PerformanceIssue, PerformanceIssueType, AlertSeverity
)

logger = logging.getLogger(__name__)


class OptimizationType(Enum):
    """优化类型"""
    DATABASE = "database"
    CACHE = "cache"
    ASYNC_PROCESSING = "async_processing"
    RESPONSE_COMPRESSION = "response_compression"
    LOAD_BALANCING = "load_balancing"
    RESOURCE_SCALING = "resource_scaling"
    CODE_OPTIMIZATION = "code_optimization"
    ARCHITECTURE_IMPROVEMENT = "architecture_improvement"


class OptimizationPriority(Enum):
    """优化优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class OptimizationCategory(Enum):
    """优化分类"""
    QUICK_WIN = "quick_win"  # 快速收益
    MEDIUM_TERM = "medium_term"  # 中期收益
    LONG_TERM = "long_term"  # 长期收益
    AUTOMATED = "automated"  # 自动化执行


@dataclass
class OptimizationSuggestion:
    """优化建议"""
    suggestion_id: str
    title: str
    description: str
    category: OptimizationCategory
    type: OptimizationType
    priority: OptimizationPriority
    impact_score: float  # 影响分数 0-100
    effort_score: float   # 实施难度分数 0-100
    roi_score: float     # 投资回报率分数
    affected_endpoints: List[str]
    estimated_improvement: Dict[str, float]
    actions: List[str]
    auto_executable: bool = False
    execution_plan: Optional[Dict] = None
    dependencies: List[str] = None
    tags: List[str] = None
    created_at: float = None
    last_applied: Optional[float] = None
    applied_count: int = 0
    success_rate: float = 0.0

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []
        if self.execution_plan is None:
            self.execution_plan = {}

    def calculate_roi(self) -> float:
        """计算投资回报率"""
        if self.effort_score == 0:
            return 0.0
        return (self.impact_score * 0.7) / (self.effort_score * 0.3)

    def to_dict(self) -> Dict:
        """转换为字典"""
        result = asdict(self)
        result["roi_score"] = self.calculate_roi()
        return result


class OptimizationRule:
    """优化规则"""

    def __init__(self, name: str, condition: Callable[[Dict], bool],
                 suggestion_generator: Callable, priority: OptimizationPriority):
        self.name = name
        self.condition = condition
        self.suggestion_generator = suggestion_generator
        self.priority = priority

    def evaluate(self, analysis_data: Dict) -> Optional[OptimizationSuggestion]:
        """评估条件并生成建议"""
        try:
            if self.condition(analysis_data):
                suggestion = self.suggestion_generator(analysis_data)
                if suggestion:
                    suggestion.priority = self.priority
                return suggestion
        except Exception as e:
            logger.error(f"Error evaluating optimization rule {self.name}: {e}")
        return None


class DatabaseOptimizations:
    """数据库优化建议生成器"""

    @staticmethod
    def detect_slow_queries(analysis_data: Dict) -> Optional[OptimizationSuggestion]:
        """检测慢查询问题"""
        global_issues = analysis_data.get("global_issues", [])
        slow_issues = [issue for issue in global_issues
                      if issue.type == PerformanceIssueType.SLOW_RESPONSE]

        if len(slow_issues) < 2:  # 需要多个慢查询端点
            return None

        affected_endpoints = list(set([ep for issue in slow_issues for ep in issue.affected_endpoints]))

        return OptimizationSuggestion(
            suggestion_id=f"slow_queries_opt_{int(time.time())}",
            title="Database Query Optimization",
            description="Multiple endpoints show slow response times, likely due to inefficient database queries",
            category=OptimizationCategory.MEDIUM_TERM,
            type=OptimizationType.DATABASE,
            priority=OptimizationPriority.HIGH,
            impact_score=75.0,
            effort_score=60.0,
            affected_endpoints=affected_endpoints,
            estimated_improvement={
                "response_time_reduction": 40.0,
                "throughput_increase": 25.0
            },
            actions=[
                "Analyze slow query logs using EXPLAIN",
                "Add appropriate database indexes",
                "Optimize complex JOIN operations",
                "Implement query result caching",
                "Review database table structures"
            ],
            auto_executable=False,
            execution_plan={
                "steps": [
                    "extract_slow_queries",
                    "analyze_query_plans",
                    "recommend_indexes",
                    "create_migration_script"
                ]
            },
            tags=["database", "query_optimization", "performance"]
        )

    @staticmethod
    def detect_connection_pool_exhaustion(analysis_data: Dict) -> Optional[OptimizationSuggestion]:
        """检测连接池耗尽"""
        system_health = analysis_data.get("system_health", {})
        if system_health.get("health_score", 100) < 70:
            return OptimizationSuggestion(
                suggestion_id=f"connection_pool_opt_{int(time.time())}",
                title="Database Connection Pool Optimization",
                description="System health indicates potential connection pool exhaustion",
                category=OptimizationCategory.QUICK_WIN,
                type=OptimizationType.DATABASE,
                priority=OptimizationPriority.HIGH,
                impact_score=80.0,
                effort_score=30.0,
                estimated_improvement={
                    "connection_availability": 90.0,
                    "error_reduction": 60.0
                },
                actions=[
                    "Increase connection pool max size",
                    "Implement connection timeout settings",
                    "Add connection health monitoring",
                    "Consider connection pooling libraries"
                ],
                auto_executable=True,
                execution_plan={
                    "parameters": {
                        "pool_size_increase": 50,
                        "timeout_settings": {
                            "connect_timeout": 30,
                            "query_timeout": 60
                        }
                    }
                },
                tags=["database", "connection_pool", "availability"]
            )

    @staticmethod
    def detect_inefficient_schema(analysis_data: Dict) -> Optional[OptimizationSuggestion]:
        """检测低效的数据库模式"""
        # 这里可以添加更复杂的数据库模式分析逻辑
        # 基于性能模式推断可能的模式问题
        return None


class CacheOptimizations:
    """缓存优化建议生成器"""

    @staticmethod
    def detect_low_cache_hit_rate(analysis_data: Dict) -> Optional[OptimizationSuggestion]:
        """检测低缓存命中���"""
        cache_issues = [issue for issue in analysis_data.get("global_issues", [])
                     if issue.type == PerformanceIssueType.CACHE_EFFICIENCY]

        if not cache_issues:
            return None

        return OptimizationSuggestion(
            suggestion_id=f"cache_hit_rate_opt_{int(time.time())}",
            title="Cache Hit Rate Improvement",
            description="Cache efficiency is below optimal levels, causing unnecessary load",
            category=OptimizationCategory.QUICK_WIN,
            type=OptimizationType.CACHE,
            priority=OptimizationPriority.HIGH,
            impact_score=70.0,
            effort_score=40.0,
            estimated_improvement={
                "cache_hit_rate_increase": 35.0,
                "response_time_reduction": 25.0,
                "database_load_reduction": 40.0
            },
            actions=[
                "Review cache key patterns",
                "Increase cache TTL for frequently accessed data",
                "Implement cache warming strategies",
                "Add cache invalidation optimization",
                "Consider multi-level caching"
            ],
            auto_executable=False,
            execution_plan={
                "analysis_steps": [
                    "analyze_cache_patterns",
                    "identify_hot_keys",
                    "optimize_cache_strategies"
                ]
            },
            tags=["cache", "hit_rate", "performance"]
        )

    @staticmethod
    def detect_cache_size_issues(analysis_data: Dict) -> Optional[OptimizationSuggestion]:
        """检测缓存大小问题"""
        return None  # 需要具体的缓存分析数据


class AsyncProcessingOptimizations:
    """异步处理优化建议生成器"""

    @staticmethod
    def detect_blocking_operations(analysis_data: Dict) -> Optional[OptimizationSuggestion]:
        """检测阻塞操作"""
        # 分析响应时间分布推断阻塞操作
        endpoints = analysis_data.get("endpoints", {})
        blocking_endpoints = []

        for endpoint, data in endpoints.items():
            response_times = data.get("response_time", {})
            if response_times.get("p99", 0) > response_times.get("p95", 0) * 3:
                blocking_endpoints.append(endpoint)

        if len(blocking_endpoints) >= 2:
            return OptimizationSuggestion(
                suggestion_id=f"async_processing_opt_{int(time.time())}",
                title="Async Processing Optimization",
                description="Some endpoints show high response time variance, suggesting blocking operations",
                category=OptimizationCategory.MEDIUM_TERM,
                type=OptimizationType.ASYNC_PROCESSING,
                priority=OptimizationPriority.MEDIUM,
                impact_score=65.0,
                effort_score=50.0,
                affected_endpoints=blocking_endpoints,
                estimated_improvement={
                    "response_time_reduction": 30.0,
                    "throughput_increase": 40.0
                },
                actions=[
                    "Convert synchronous operations to async",
                    "Implement async database operations",
                    "Add asyncio task queuing",
                    "Use async file I/O operations",
                    "Implement non-blocking HTTP requests"
                ],
                auto_executable=False,
                execution_plan={
                    "migration_strategy": "gradual_async_conversion",
                    "testing_approach": "performance_comparison"
                },
                tags=["async", "processing", "performance"]
            )

        return None


class ArchitectureOptimizations:
    """架构优化建议生成器"""

    @staticmethod
    def detect_microservice_bottlenecks(analysis_data: Dict) -> Optional[OptimizationSuggestion]:
        """检测微服务瓶颈"""
        return OptimizationSuggestion(
            suggestion_id=f"microservice_architecture_opt_{int(time.time())}",
            title="Microservice Architecture Optimization",
            description="Performance analysis suggests potential microservice bottlenecks",
            category=OptimizationCategory.LONG_TERM,
            type=OptimizationType.ARCHITECTURE_IMPROVEMENT,
            priority=OptimizationPriority.MEDIUM,
            impact_score=85.0,
            effort_score=90.0,
            estimated_improvement={
                "system_scalability": 60.0,
                "maintenance_reduction": 40.0,
                "development_velocity": 30.0
            },
            actions=[
                "Identify service boundaries",
                "Implement API Gateway pattern",
                "Add service mesh architecture",
                "Implement circuit breakers",
                "Add distributed tracing"
            ],
            auto_executable=False,
            execution_plan={
                "phases": [
                    "service_boundary_analysis",
                    "api_gateway_implementation",
                    "service_mesh_deployment",
                    "monitoring_integration"
                ]
            },
            tags=["architecture", "microservices", "scalability"]
        )

    @staticmethod
    def detect_load_balancing_needs(analysis_data: Dict) -> Optional[OptimizationSuggestion]:
        """检测负载均衡需求"""
        system_health = analysis_data.get("system_health", {})
        if system_health.get("critical_issues", 0) > 0 or system_health.get("health_score", 100) < 60:
            return OptimizationSuggestion(
                suggestion_id=f"load_balancing_opt_{int(time.time())}",
                title="Load Balancing Implementation",
                description="System health indicates need for load balancing",
                category=OptimizationCategory.MEDIUM_TERM,
                type=OptimizationType.LOAD_BALANCING,
                priority=OptimizationPriority.HIGH,
                impact_score=90.0,
                effort_score=70.0,
                estimated_improvement={
                    "availability": 99.9,
                    "response_time_distribution": 80.0,
                    "throughput": 100.0
                },
                actions=[
                    "Implement round-robin load balancing",
                    "Add health check endpoints",
                    "Configure failover mechanisms",
                    "Add request routing logic",
                    "Implement rate limiting"
                ],
                auto_executable=False,
                execution_plan={
                    "strategy": "active_load_balancing",
                    "health_checks": True,
                    "failover": True
                },
                tags=["load_balancing", "scalability", "availability"]
            )

        return None


class PerformanceOptimizationEngine:
    """性能优化引擎"""

    def __init__(self):
        self.suggestion_history: List[OptimizationSuggestion] = []
        self.optimization_rules: List[OptimizationRule] = []
        self.applied_suggestions: Dict[str, Dict] = {}
        self.auto_execution_enabled = True

        # 初始化优化规则
        self._initialize_rules()

    def _initialize_rules(self):
        """初始化优化规则"""
        self.optimization_rules = [
            # 数据库优化规则
            OptimizationRule(
                name="slow_queries",
                condition=lambda data: len([issue for issue in data.get("global_issues", [])
                                         if issue.type == PerformanceIssueType.SLOW_RESPONSE]) >= 2,
                suggestion_generator=DatabaseOptimizations.detect_slow_queries,
                priority=OptimizationPriority.HIGH
            ),
            OptimizationRule(
                name="connection_pool_exhaustion",
                condition=lambda data: data.get("system_health", {}).get("health_score", 100) < 70,
                suggestion_generator=DatabaseOptimizations.detect_connection_pool_exhaustion,
                priority=OptimizationPriority.HIGH
            ),

            # 缓存优化规则
            OptimizationRule(
                name="low_cache_hit_rate",
                condition=lambda data: len([issue for issue in data.get("global_issues", [])
                                         if issue.type == PerformanceIssueType.CACHE_EFFICIENCY]) > 0,
                suggestion_generator=CacheOptimizations.detect_low_cache_hit_rate,
                priority=OptimizationPriority.HIGH
            ),

            # 异步处理优化规则
            OptimizationRule(
                name="blocking_operations",
                condition=lambda data: self._has_blocking_endpoints(data),
                suggestion_generator=AsyncProcessingOptimizations.detect_blocking_operations,
                priority=OptimizationPriority.MEDIUM
            ),

            # 架构优化规则
            OptimizationRule(
                name="load_balancing_needs",
                condition=lambda data: data.get("system_health", {}).get("health_score", 100) < 60,
                suggestion_generator=ArchitectureOptimizations.detect_load_balancing_needs,
                priority=OptimizationPriority.HIGH
            )
        ]

    def _has_blocking_endpoints(self, data: Dict) -> bool:
        """检查是否有阻塞端点"""
        endpoints = data.get("endpoints", {})
        blocking_count = 0
        total_endpoints = len(endpoints)

        for endpoint_data in endpoints.values():
            response_times = endpoint_data.get("response_time", {})
            if response_times.get("p99", 0) > response_times.get("p95", 0) * 3:
                blocking_count += 1

        return blocking_count >= 2 and (blocking_count / total_endpoints) >= 0.3

    async def analyze_and_suggest(self, performance_analysis: Dict) -> List[OptimizationSuggestion]:
        """分析性能数据并生成建议"""
        suggestions = []

        try:
            # 应用优化规则
            for rule in self.optimization_rules:
                suggestion = rule.evaluate(performance_analysis)
                if suggestion:
                    suggestions.append(suggestion)

            # 去重和优先级排序
            suggestions = self._deduplicate_suggestions(suggestions)
            suggestions = self._prioritize_suggestions(suggestions)

            # 存储建议历史
            self.suggestion_history.extend(suggestions)
            self._maintain_history_size()

            logger.info(f"Generated {len(suggestions)} optimization suggestions")
            return suggestions

        except Exception as e:
            logger.error(f"Error analyzing and suggesting optimizations: {e}")
            return []

    def _deduplicate_suggestions(self, suggestions: List[OptimizationSuggestion]) -> List[OptimizationSuggestion]:
        """去重优化建议"""
        seen = set()
        deduped = []

        for suggestion in suggestions:
            # 基于类型和主要端点去重
            dedup_key = (suggestion.type, tuple(sorted(suggestion.affected_endpoints)))

            if dedup_key not in seen:
                seen.add(dedup_key)
                deduped.append(suggestion)
            else:
                # 合并相似建议
                existing = next((s for s in deduped if
                              s.type == suggestion.type and
                              set(s.affected_endpoints) & set(suggestion.affected_endpoints)), None)
                if existing:
                    # 合并影响和操作
                    existing.affected_endpoints = list(set(existing.affected_endpoints + suggestion.affected_endpoints))
                    existing.actions = list(set(existing.actions + suggestion.actions))

        return deduped

    def _prioritize_suggestions(self, suggestions: List[OptimizationSuggestion]) -> List[OptimizationSuggestion]:
        """优化建议优先级排序"""
        # 综合排序：优先级 > ROI分数 > 影响分数
        def sort_key(suggestion):
            return (
                -suggestion.priority.value,
                -suggestion.calculate_roi(),
                -suggestion.impact_score
            )

        return sorted(suggestions, key=sort_key)

    def _maintain_history_size(self):
        """维护历史记录大小"""
        max_history = 500
        if len(self.suggestion_history) > max_history:
            self.suggestion_history = self.suggestion_history[-max_history:]

    async def apply_optimization(self, suggestion_id: str, execution_params: Dict = None) -> bool:
        """应用优化建议"""
        try:
            # 查找建议
            suggestion = self._find_suggestion(suggestion_id)
            if not suggestion:
                logger.error(f"Suggestion not found: {suggestion_id}")
                return False

            if not suggestion.auto_executable:
                logger.warning(f"Suggestion {suggestion_id} is not auto-executable")
                return False

            # 执行优化
            success = await self._execute_optimization(suggestion, execution_params or suggestion.execution_plan)

            # 记录执行结果
            self.applied_suggestions[suggestion_id] = {
                "applied_at": time.time(),
                "success": success,
                "execution_params": execution_params,
                "suggestion_snapshot": suggestion.to_dict()
            }

            # 更新建议的统计
            for hist_suggestion in self.suggestion_history:
                if hist_suggestion.suggestion_id == suggestion_id:
                    hist_suggestion.applied_count += 1
                    if success:
                        hist_suggestion.success_rate = (
                            (hist_suggestion.success_rate * (hist_suggestion.applied_count - 1) + 1) /
                            hist_suggestion.applied_count
                        )
                    break

            return success

        except Exception as e:
            logger.error(f"Error applying optimization {suggestion_id}: {e}")
            return False

    def _find_suggestion(self, suggestion_id: str) -> Optional[OptimizationSuggestion]:
        """查找优化建议"""
        for suggestion in self.suggestion_history:
            if suggestion.suggestion_id == suggestion_id:
                return suggestion
        return None

    async def _execute_optimization(self, suggestion: OptimizationSuggestion, execution_params: Dict) -> bool:
        """执行优化操作"""
        logger.info(f"Executing optimization: {suggestion.title}")

        try:
            if suggestion.type == OptimizationType.DATABASE:
                return await self._execute_database_optimization(suggestion, execution_params)
            elif suggestion.type == OptimizationType.CACHE:
                return await self._execute_cache_optimization(suggestion, execution_params)
            elif suggestion.type == OptimizationType.ASYNC_PROCESSING:
                return await self._execute_async_optimization(suggestion, execution_params)
            elif suggestion.type == OptimizationType.LOAD_BALANCING:
                return await self._execute_load_balancing_optimization(suggestion, execution_params)
            else:
                logger.warning(f"Optimization type {suggestion.type} not implemented for auto-execution")
                return False

        except Exception as e:
            logger.error(f"Error executing optimization: {e}")
            return False

    async def _execute_database_optimization(self, suggestion: OptimizationSuggestion, params: Dict) -> bool:
        """执行数据库优化"""
        # 这里可以实现具体的数据库优化逻辑
        # 例如：增加连接池大小、创建索引等
        logger.info("Executing database optimization...")
        await asyncio.sleep(1)  # 模拟优化执行
        return True

    async def _execute_cache_optimization(self, suggestion: OptimizationSuggestion, params: Dict) -> bool:
        """执行缓存优化"""
        logger.info("Executing cache optimization...")
        await asyncio.sleep(0.5)
        return True

    async def _execute_async_optimization(self, suggestion: OptimizationSuggestion, params: Dict) -> bool:
        """执行异步处理优化"""
        logger.info("Executing async processing optimization...")
        await asyncio.sleep(0.5)
        return True

    async def _execute_load_balancing_optimization(self, suggestion: OptimizationSuggestion, params: Dict) -> bool:
        """执行负载均衡优化"""
        logger.info("Executing load balancing optimization...")
        await asyncio.sleep(1)
        return True

    def get_suggestion_analytics(self) -> Dict:
        """获取建议分析数据"""
        if not self.suggestion_history:
            return {}

        total_suggestions = len(self.suggestion_history)
        applied_suggestions = len(self.applied_suggestions)

        # 按类型统计
        type_distribution = {}
        success_by_type = {}

        for suggestion in self.suggestion_history:
            type_key = suggestion.type.value
            type_distribution[type_key] = type_distribution.get(type_key, 0) + 1

            if suggestion.suggestion_id in self.applied_suggestions:
                if type_key not in success_by_type:
                    success_by_type[type_key] = {"total": 0, "success": 0}
                success_by_type[type_key]["total"] += 1
                if self.applied_suggestions[suggestion.suggestion_id]["success"]:
                    success_by_type[type_key]["success"] += 1

        # 计算成功率
        success_rates = {}
        for type_key, data in success_by_type.items():
            success_rates[type_key] = data["success"] / data["total"]

        # ROI分析
        roi_suggestions = sorted(self.suggestion_history,
                               key=lambda s: s.calculate_roi(),
                               reverse=True)[:10]

        return {
            "total_suggestions": total_suggestions,
            "applied_suggestions": applied_suggestions,
            "application_rate": applied_suggestions / max(1, total_suggestions),
            "type_distribution": type_distribution,
            "success_rates_by_type": success_rates,
            "top_roi_suggestions": [s.to_dict() for s in roi_suggestions],
            "auto_execution_enabled": self.auto_execution_enabled,
            "analytics_timestamp": time.time()
        }

    def get_recommendations_report(self) -> Dict:
        """获取优化建议报告"""
        suggestions_by_priority = {
            OptimizationPriority.CRITICAL: [],
            OptimizationPriority.HIGH: [],
            OptimizationPriority.MEDIUM: [],
            OptimizationPriority.LOW: []
        }

        # 按优先级分组
        for suggestion in self.suggestion_history:
            suggestions_by_priority[suggestion.priority].append(suggestion.to_dict())

        # 统计信息
        stats = {
            "total_suggestions": len(self.suggestion_history),
            "critical_count": len(suggestions_by_priority[OptimizationPriority.CRITICAL]),
            "high_count": len(suggestions_by_priority[OptimizationPriority.HIGH]),
            "auto_executable_count": sum(1 for s in self.suggestion_history if s.auto_executable),
            "applied_count": len(self.applied_suggestions),
            "success_rate": sum(s.success_rate for s in self.suggestion_history if s.applied_count > 0) /
                          max(1, len([s for s in self.suggestion_history if s.applied_count > 0]))
        }

        # 热门建议
        hot_categories = {}
        for suggestion in self.suggestion_history:
            category = suggestion.category.value
            if category not in hot_categories:
                hot_categories[category] = []
            hot_categories[category].append(suggestion)

        hot_categories = {k: sorted(v, key=lambda s: s.calculate_roi(), reverse=True)[:3]
                        for k, v in hot_categories.items()}

        return {
            "timestamp": time.time(),
            "suggestions_by_priority": {
                priority.value: [s["suggestion_id"] for s in suggestions]
                for priority, suggestions in suggestions_by_priority.items()
            },
            "statistics": stats,
            "hot_categories": hot_categories,
            "recent_suggestions": [s.to_dict() for s in self.suggestion_history[-10:]],
            "execution_history": dict(self.applied_suggestions)
        }


# 全局优化引擎实例
_optimization_engine: Optional[PerformanceOptimizationEngine] = None


async def get_optimization_engine() -> PerformanceOptimizationEngine:
    """获取全局优化引擎实例"""
    global _optimization_engine
    if _optimization_engine is None:
        _optimization_engine = PerformanceOptimizationEngine()
    return _optimization_engine


# 便捷函数
async def generate_optimization_suggestions(performance_analysis: Dict) -> List[Dict]:
    """生成优化建议"""
    engine = await get_optimization_engine()
    suggestions = await engine.analyze_and_suggest(performance_analysis)
    return [s.to_dict() for s in suggestions]


async def apply_optimization_suggestion(suggestion_id: str, params: Dict = None) -> bool:
    """应用优化建议"""
    engine = await get_optimization_engine()
    return await engine.apply_optimization(suggestion_id, params)


async def get_optimization_analytics() -> Dict:
    """获取优化分析数据"""
    engine = await get_optimization_engine()
    return engine.get_suggestion_analytics()