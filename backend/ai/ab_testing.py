"""
AI模型A/B测试系统
Week 5 Day 4: 高级AI功能 - 模型A/B测试
"""

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import uuid
from abc import ABC, abstractmethod

from backend.ai.model_manager import model_manager, AIModel, TaskType
from backend.core.cache.smart_cache import get_smart_cache

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """测试状态"""
    DRAFT = "draft"           # 草稿
    RUNNING = "running"       # 运行中
    PAUSED = "paused"         # 暂停
    COMPLETED = "completed"   # 已完成
    CANCELLED = "cancelled"   # 已取消


class TrafficSplitStrategy(Enum):
    """流量分配策略"""
    EQUAL = "equal"           # 平均分配
    WEIGHTED = "weighted"     # 加权分配
    BANDIT = "bandit"         # 赌徒算法
    THOMPSON_SAMPLING = "thompson_sampling"  # 汤普森采样


class SuccessMetric(Enum):
    """成功指标"""
    USER_SATISFACTION = "user_satisfaction"      # 用户满意度
    RESPONSE_TIME = "response_time"              # 响应时间
    COST_EFFICIENCY = "cost_efficiency"          # 成本效率
    ACCURACY_SCORE = "accuracy_score"            # 准确性评分
    CONVERSION_RATE = "conversion_rate"          # 转化率
    ERROR_RATE = "error_rate"                    # 错误率


@dataclass
class TestVariant:
    """测试变体"""
    variant_id: str
    model_id: str
    name: str
    description: str
    traffic_weight: float = 0.5  # 流量权重
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ABTest:
    """A/B测试定义"""
    test_id: str
    name: str
    description: str
    task_type: TaskType
    variants: List[TestVariant]
    success_metrics: List[SuccessMetric]
    traffic_strategy: TrafficSplitStrategy
    sample_size: Optional[int] = None
    confidence_level: float = 0.95
    min_runtime_hours: int = 24
    max_runtime_hours: int = 168  # 7天
    status: TestStatus = TestStatus.DRAFT
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    target_audience: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.target_audience is None:
            self.target_audience = {}

    @property
    def is_running(self) -> bool:
        return self.status == TestStatus.RUNNING

    @property
    def runtime_hours(self) -> float:
        if not self.started_at:
            return 0
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds() / 3600

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['task_type'] = self.task_type.value
        data['traffic_strategy'] = self.traffic_strategy.value
        data['success_metrics'] = [m.value for m in self.success_metrics]
        data['variants'] = [v.to_dict() for v in self.variants]
        data['is_running'] = self.is_running
        data['runtime_hours'] = self.runtime_hours
        # 处理日期序列化
        for field in ['created_at', 'started_at', 'completed_at']:
            if data[field]:
                data[field] = data[field].isoformat()
        return data


@dataclass
class TestResult:
    """测试结果记录"""
    result_id: str
    test_id: str
    variant_id: str
    user_id: Optional[str]
    session_id: str
    request_data: Dict[str, Any]
    response_data: Dict[str, Any]
    metrics: Dict[str, float]
    timestamp: datetime
    success: bool

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class TestStatistics:
    """测试统计"""
    variant_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    avg_user_satisfaction: float = 0.0
    avg_cost: float = 0.0
    conversion_rate: float = 0.0
    error_rate: float = 0.0
    statistical_significance: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['success_rate'] = self.success_rate
        return data


class TrafficSplitter:
    """流量分配器"""

    def __init__(self):
        self.bandit_stats: Dict[str, Dict] = {}  # 赌徒算法统计

    def assign_variant(
        self,
        test: ABTest,
        user_id: Optional[str] = None,
        session_id: str = None
    ) -> TestVariant:
        """分配测试变体"""
        if test.traffic_strategy == TrafficSplitStrategy.EQUAL:
            return self._equal_split(test.variants, session_id)
        elif test.traffic_strategy == TrafficSplitStrategy.WEIGHTED:
            return self._weighted_split(test.variants, session_id)
        elif test.traffic_strategy == TrafficSplitStrategy.BANDIT:
            return self._bandit_split(test.test_id, test.variants, session_id)
        elif test.traffic_strategy == TrafficSplitStrategy.THOMPSON_SAMPLING:
            return self._thompson_sampling_split(test.test_id, test.variants, session_id)
        else:
            return self._equal_split(test.variants, session_id)

    def _equal_split(self, variants: List[TestVariant], session_id: str) -> TestVariant:
        """平均分配"""
        if not variants:
            raise ValueError("No variants available")

        # 基于会话ID的一致性哈希
        hash_value = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
        index = hash_value % len(variants)
        return variants[index]

    def _weighted_split(self, variants: List[TestVariant], session_id: str) -> TestVariant:
        """加权分配"""
        if not variants:
            raise ValueError("No variants available")

        # 归一化权重
        total_weight = sum(v.traffic_weight for v in variants)
        if total_weight == 0:
            return self._equal_split(variants, session_id)

        normalized_weights = [v.traffic_weight / total_weight for v in variants]

        # 基于会话ID的确定性随机选择
        hash_value = int(hashlib.md5(session_id.encode()).hexdigest(), 16)
        random_value = (hash_value % 1000) / 1000.0

        cumulative_weight = 0
        for variant, weight in zip(variants, normalized_weights):
            cumulative_weight += weight
            if random_value <= cumulative_weight:
                return variant

        return variants[-1]

    def _bandit_split(self, test_id: str, variants: List[TestVariant], session_id: str) -> TestVariant:
        """赌徒算法分配"""
        if test_id not in self.bandit_stats:
            self.bandit_stats[test_id] = {
                variant.variant_id: {"impressions": 0, "rewards": 0}
                for variant in variants
            }

        stats = self.bandit_stats[test_id]

        # UCB1算法
        total_impressions = sum(s["impressions"] for s in stats.values())
        if total_impressions == 0:
            return self._equal_split(variants, session_id)

        best_variant = None
        best_score = -float('inf')

        for variant in variants:
            variant_stats = stats[variant.variant_id]
            if variant_stats["impressions"] == 0:
                return variant  # 探索未尝试的变体

            # 计算UCB1分数
            avg_reward = variant_stats["rewards"] / variant_stats["impressions"]
            exploration_bonus = (2 * math.log(total_impressions) / variant_stats["impressions"]) ** 0.5
            ucb1_score = avg_reward + exploration_bonus

            if ucb1_score > best_score:
                best_score = ucb1_score
                best_variant = variant

        return best_variant or variants[0]

    def _thompson_sampling_split(self, test_id: str, variants: List[TestVariant], session_id: str) -> TestVariant:
        """汤普森采样分配"""
        import math

        if test_id not in self.bandit_stats:
            self.bandit_stats[test_id] = {
                variant.variant_id: {"successes": 0, "failures": 0}
                for variant in variants
            }

        stats = self.bandit_stats[test_id]

        best_variant = None
        best_sample = -1

        for variant in variants:
            variant_stats = stats[variant.variant_id]
            successes = variant_stats["successes"]
            failures = variant_stats["failures"]

            # Beta分布采样
            if successes + failures == 0:
                sample = random.random()
            else:
                sample = random.betavariate(successes + 1, failures + 1)

            if sample > best_sample:
                best_sample = sample
                best_variant = variant

        return best_variant or variants[0]

    def update_stats(self, test_id: str, variant_id: str, reward: float):
        """更新统计信息"""
        if test_id not in self.bandit_stats:
            return

        stats = self.bandit_stats[test_id]
        if variant_id in stats:
            if "impressions" in stats[variant_id]:
                stats[variant_id]["impressions"] += 1
                stats[variant_id]["rewards"] += reward
            else:
                # Thompson采样模式
                if reward > 0.5:
                    stats[variant_id]["successes"] += 1
                else:
                    stats[variant_id]["failures"] += 1


class StatisticalAnalyzer:
    """统计分析器"""

    def __init__(self):
        pass

    async def calculate_statistical_significance(
        self,
        control_stats: TestStatistics,
        treatment_stats: TestStatistics,
        metric: SuccessMetric
    ) -> Dict[str, Any]:
        """计算统计显著性"""
        try:
            # 根据指标选择测试方法
            if metric in [SuccessMetric.USER_SATISFACTION, SuccessMetric.CONVERSION_RATE]:
                return self._proportion_test(control_stats, treatment_stats)
            elif metric in [SuccessMetric.RESPONSE_TIME, SuccessMetric.COST_EFFICIENCY]:
                return self._t_test(control_stats, treatment_stats)
            else:
                return self._mann_whitney_test(control_stats, treatment_stats)
        except Exception as e:
            logger.error(f"Statistical analysis failed: {e}")
            return {"significant": False, "p_value": 1.0, "error": str(e)}

    def _proportion_test(self, control: TestStatistics, treatment: TestStatistics) -> Dict[str, Any]:
        """比例检验（适用于转化率等）"""
        import math

        p1 = control.conversion_rate / 100 if control.conversion_rate else 0
        p2 = treatment.conversion_rate / 100 if treatment.conversion_rate else 0
        n1 = control.total_requests
        n2 = treatment.total_requests

        if n1 == 0 or n2 == 0:
            return {"significant": False, "p_value": 1.0}

        # 计算Z统计量
        p_pooled = (control.successful_requests + treatment.successful_requests) / (n1 + n2)
        se = math.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))

        if se == 0:
            return {"significant": False, "p_value": 1.0}

        z_score = (p2 - p1) / se
        p_value = 2 * (1 - self._normal_cdf(abs(z_score)))

        # 计算置信区间
        margin_error = 1.96 * se
        ci_lower = (p2 - p1) - margin_error
        ci_upper = (p2 - p1) + margin_error

        return {
            "significant": p_value < 0.05,
            "p_value": p_value,
            "z_score": z_score,
            "confidence_interval": (ci_lower, ci_upper),
            "effect_size": p2 - p1
        }

    def _t_test(self, control: TestStatistics, treatment: TestStatistics) -> Dict[str, Any]:
        """t检验（适用于连续变量）"""
        # 简化的t检验实现
        n1 = control.total_requests
        n2 = treatment.total_requests
        mean1 = control.avg_response_time
        mean2 = treatment.avg_response_time

        if n1 < 2 or n2 < 2:
            return {"significant": False, "p_value": 1.0}

        # 简化计算，假设等方差
        pooled_var = ((n1 - 1) * control.avg_response_time**2 + (n2 - 1) * treatment.avg_response_time**2) / (n1 + n2 - 2)
        se = math.sqrt(pooled_var * (1/n1 + 1/n2))

        if se == 0:
            return {"significant": False, "p_value": 1.0}

        t_score = (mean2 - mean1) / se
        # 简化的p值计算
        p_value = 2 * (1 - self._t_cdf(abs(t_score), n1 + n2 - 2))

        return {
            "significant": p_value < 0.05,
            "p_value": p_value,
            "t_score": t_score,
            "effect_size": mean2 - mean1
        }

    def _mann_whitney_test(self, control: TestStatistics, treatment: TestStatistics) -> Dict[str, Any]:
        """Mann-Whitney U检验（非参数检验）"""
        # 简化实现
        return {
            "significant": False,
            "p_value": 0.5,
            "note": "Simplified Mann-Whitney test"
        }

    def _normal_cdf(self, x: float) -> float:
        """正态分布累积分布函数"""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _t_cdf(self, t: float, df: int) -> float:
        """t分布累积分布函数"""
        # 简化实现，实际应该使用更精确的计算
        return self._normal_cdf(t)


class ABTestManager:
    """A/B测试管理器"""

    def __init__(self):
        self.tests: Dict[str, ABTest] = {}
        self.results: Dict[str, List[TestResult]] = {}
        self.traffic_splitter = TrafficSplitter()
        self.statistical_analyzer = StatisticalAnalyzer()
        self.cache = None

    async def _get_cache(self):
        """获取缓存实例"""
        if not self.cache:
            self.cache = await get_smart_cache()
        return self.cache

    async def create_test(
        self,
        name: str,
        description: str,
        task_type: TaskType,
        variants: List[Dict[str, Any]],
        success_metrics: List[SuccessMetric],
        traffic_strategy: TrafficSplitStrategy = TrafficSplitStrategy.EQUAL,
        sample_size: Optional[int] = None,
        confidence_level: float = 0.95,
        min_runtime_hours: int = 24,
        max_runtime_hours: int = 168,
        target_audience: Dict[str, Any] = None
    ) -> str:
        """创建A/B测试"""
        # 生成测试ID
        test_id = str(uuid.uuid4())

        # 创建变体对象
        variant_objects = []
        for i, variant_data in enumerate(variants):
            variant = TestVariant(
                variant_id=str(uuid.uuid4()),
                model_id=variant_data['model_id'],
                name=variant_data.get('name', f'Variant {i+1}'),
                description=variant_data.get('description', ''),
                traffic_weight=variant_data.get('traffic_weight', 1.0),
                config=variant_data.get('config', {})
            )
            variant_objects.append(variant)

        # 创建测试对象
        test = ABTest(
            test_id=test_id,
            name=name,
            description=description,
            task_type=task_type,
            variants=variant_objects,
            success_metrics=success_metrics,
            traffic_strategy=traffic_strategy,
            sample_size=sample_size,
            confidence_level=confidence_level,
            min_runtime_hours=min_runtime_hours,
            max_runtime_hours=max_runtime_hours,
            target_audience=target_audience or {}
        )

        self.tests[test_id] = test
        self.results[test_id] = []

        logger.info(f"Created A/B test: {name} ({test_id})")
        return test_id

    async def start_test(self, test_id: str) -> bool:
        """启动A/B测试"""
        test = self.tests.get(test_id)
        if not test:
            raise ValueError(f"Test not found: {test_id}")

        if test.status != TestStatus.DRAFT:
            raise ValueError(f"Test {test_id} is not in draft status")

        test.status = TestStatus.RUNNING
        test.started_at = datetime.utcnow()

        logger.info(f"Started A/B test: {test.name} ({test_id})")
        return True

    async def stop_test(self, test_id: str) -> bool:
        """停止A/B测试"""
        test = self.tests.get(test_id)
        if not test:
            raise ValueError(f"Test not found: {test_id}")

        if test.status != TestStatus.RUNNING:
            raise ValueError(f"Test {test_id} is not running")

        test.status = TestStatus.COMPLETED
        test.completed_at = datetime.utcnow()

        logger.info(f"Stopped A/B test: {test.name} ({test_id})")
        return True

    async def get_variant_for_request(
        self,
        test_id: str,
        user_id: Optional[str] = None,
        session_id: str = None
    ) -> Optional[TestVariant]:
        """为请求分配测试变体"""
        test = self.tests.get(test_id)
        if not test or not test.is_running:
            return None

        # 检查测试是否应该停止
        if self._should_stop_test(test):
            await self.stop_test(test_id)
            return None

        return self.traffic_splitter.assign_variant(test, user_id, session_id)

    async def record_test_result(
        self,
        test_id: str,
        variant_id: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        metrics: Dict[str, float],
        user_id: Optional[str] = None,
        session_id: str = None
    ) -> bool:
        """记录测试结果"""
        if test_id not in self.tests or test_id not in self.results:
            return False

        # 创建结果记录
        result = TestResult(
            result_id=str(uuid.uuid4()),
            test_id=test_id,
            variant_id=variant_id,
            user_id=user_id,
            session_id=session_id or str(uuid.uuid4()),
            request_data=request_data,
            response_data=response_data,
            metrics=metrics,
            timestamp=datetime.utcnow(),
            success=metrics.get('success', True)
        )

        self.results[test_id].append(result)

        # 更新流量分配器统计
        reward = self._calculate_reward(metrics)
        self.traffic_splitter.update_stats(test_id, variant_id, reward)

        # 检查是否达到停止条件
        test = self.tests[test_id]
        if self._should_stop_test(test):
            await self.stop_test(test_id)

        return True

    def _calculate_reward(self, metrics: Dict[str, float]) -> float:
        """计算奖励值（用于赌徒算法）"""
        # 基于多个指标的综合奖励
        reward = 0.0

        if 'user_satisfaction' in metrics:
            reward += metrics['user_satisfaction'] * 0.3

        if 'response_time' in metrics:
            # 响应时间越短奖励越高
            response_time_reward = max(0, 1 - metrics['response_time'] / 10)  # 10秒为基准
            reward += response_time_reward * 0.2

        if 'cost' in metrics:
            # 成本越低奖励越高
            cost_reward = max(0, 1 - metrics['cost'])
            reward += cost_reward * 0.2

        if 'success' in metrics:
            reward += (1.0 if metrics['success'] else 0.0) * 0.3

        return max(0, min(1, reward))

    def _should_stop_test(self, test: ABTest) -> bool:
        """检查是否应该停止测试"""
        if not test.is_running:
            return False

        # 检查运行时间
        if test.runtime_hours >= test.max_runtime_hours:
            return True

        # 检查样本量
        if test.sample_size:
            total_results = sum(len(self.results[test.test_id]) for result in self.results[test.test_id])
            if total_results >= test.sample_size:
                return True

        # 检查最小运行时间
        if test.runtime_hours < test.min_runtime_hours:
            return False

        # 检查统计显著性（简化版本）
        return False  # 实际应该计算统计显著性

    async def get_test_statistics(self, test_id: str) -> Dict[str, TestStatistics]:
        """获取测试统计"""
        if test_id not in self.tests or test_id not in self.results:
            return {}

        test = self.tests[test_id]
        results = self.results[test_id]
        statistics = {}

        # 按变体分组统计
        for variant in test.variants:
            variant_results = [r for r in results if r.variant_id == variant.variant_id]

            if not variant_results:
                statistics[variant.variant_id] = TestStatistics(variant_id=variant.variant_id)
                continue

            # 计算统计指标
            total_requests = len(variant_results)
            successful_requests = len([r for r in variant_results if r.success])
            failed_requests = total_requests - successful_requests

            # 响应时间统计
            response_times = [r.metrics.get('response_time', 0) for r in variant_results]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0

            # 用户满意度统计
            satisfactions = [r.metrics.get('user_satisfaction', 0) for r in variant_results if r.metrics.get('user_satisfaction')]
            avg_user_satisfaction = sum(satisfactions) / len(satisfactions) if satisfactions else 0

            # 成本统计
            costs = [r.metrics.get('cost', 0) for r in variant_results]
            avg_cost = sum(costs) / len(costs) if costs else 0

            # 转化率统计（如果有满意度评分）
            conversion_count = len([r for r in variant_results if r.metrics.get('user_satisfaction', 0) >= 0.7])
            conversion_rate = (conversion_count / total_requests * 100) if total_requests > 0 else 0

            # 错误率
            error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0

            stats = TestStatistics(
                variant_id=variant.variant_id,
                total_requests=total_requests,
                successful_requests=successful_requests,
                failed_requests=failed_requests,
                avg_response_time=avg_response_time,
                avg_user_satisfaction=avg_user_satisfaction,
                avg_cost=avg_cost,
                conversion_rate=conversion_rate,
                error_rate=error_rate
            )

            statistics[variant.variant_id] = stats

        return statistics

    async def get_test_results(self, test_id: str) -> Dict[str, Any]:
        """获取测试结果"""
        if test_id not in self.tests:
            raise ValueError(f"Test not found: {test_id}")

        test = self.tests[test_id]
        statistics = await self.get_test_statistics(test_id)

        result = {
            "test": test.to_dict(),
            "statistics": {vid: stats.to_dict() for vid, stats in statistics.items()},
            "winner": None,
            "recommendations": []
        }

        # 分析结果并推荐获胜变体
        if len(statistics) > 1:
            winner_analysis = await self._analyze_winner(test, statistics)
            result.update(winner_analysis)

        return result

    async def _analyze_winner(self, test: ABTest, statistics: Dict[str, TestStatistics]) -> Dict[str, Any]:
        """分析获胜变体"""
        if not test.success_metrics or len(statistics) < 2:
            return {"winner": None, "recommendations": ["Insufficient data for analysis"]}

        # 简化的获胜逻辑 - 基于主要指标
        primary_metric = test.success_metrics[0]

        best_variant = None
        best_score = -float('inf')

        for variant_id, stats in statistics.items():
            if primary_metric == SuccessMetric.USER_SATISFACTION:
                score = stats.avg_user_satisfaction
            elif primary_metric == SuccessMetric.RESPONSE_TIME:
                score = -stats.avg_response_time  # 响应时间越低越好
            elif primary_metric == SuccessMetric.COST_EFFICIENCY:
                score = -stats.avg_cost  # 成本越低越好
            elif primary_metric == SuccessMetric.CONVERSION_RATE:
                score = stats.conversion_rate
            else:
                score = stats.success_rate

            if score > best_score:
                best_score = score
                best_variant = variant_id

        recommendations = []
        if best_variant:
            recommendations.append(f"Variant {best_variant} shows best performance for {primary_metric.value}")

        return {
            "winner": best_variant,
            "winning_metric": primary_metric.value,
            "winning_score": best_score,
            "recommendations": recommendations
        }

    async def get_all_tests(self, status: Optional[TestStatus] = None) -> List[Dict[str, Any]]:
        """获取所有测试"""
        tests = []
        for test in self.tests.values():
            if status is None or test.status == status:
                tests.append(test.to_dict())
        return tests

    async def delete_test(self, test_id: str) -> bool:
        """删除测试"""
        if test_id in self.tests:
            del self.tests[test_id]
        if test_id in self.results:
            del self.results[test_id]
        return True


# 全局A/B测试管理器
ab_test_manager = ABTestManager()


async def get_ab_test_manager() -> ABTestManager:
    """获取A/B测试管理器实例"""
    return ab_test_manager


# A/B测试装饰器
def with_ab_test(
    test_id: str,
    fallback_model: str = None
):
    """A/B测试装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            manager = await get_ab_test_manager()

            # 尝试获取测试变体
            user_id = kwargs.get('user_id')
            session_id = kwargs.get('session_id', str(uuid.uuid4()))

            variant = await manager.get_variant_for_request(test_id, user_id, session_id)

            if variant:
                # 使用测试变体
                kwargs['model'] = variant.model_id
                kwargs['variant_id'] = variant.variant_id

                try:
                    start_time = time.time()
                    result = await func(*args, **kwargs)
                    response_time = time.time() - start_time

                    # 记录测试结果
                    metrics = {
                        'response_time': response_time,
                        'success': True,
                        'cost': kwargs.get('cost', 0),
                        'user_satisfaction': kwargs.get('user_satisfaction', 0.8)
                    }

                    await manager.record_test_result(
                        test_id=test_id,
                        variant_id=variant.variant_id,
                        request_data={'args': args, 'kwargs': kwargs},
                        response_data={'result': result},
                        metrics=metrics,
                        user_id=user_id,
                        session_id=session_id
                    )

                    return result

                except Exception as e:
                    # 记录失败结果
                    metrics = {
                        'response_time': time.time() - start_time,
                        'success': False,
                        'error': str(e)
                    }

                    await manager.record_test_result(
                        test_id=test_id,
                        variant_id=variant.variant_id,
                        request_data={'args': args, 'kwargs': kwargs},
                        response_data={'error': str(e)},
                        metrics=metrics,
                        user_id=user_id,
                        session_id=session_id
                    )

                    # 尝试使用备用模型
                    if fallback_model:
                        kwargs['model'] = fallback_model
                        return await func(*args, **kwargs)
                    else:
                        raise

            else:
                # 不参与测试，使用默认模型
                return await func(*args, **kwargs)

        return wrapper
    return decorator


# 导入math模块
import math