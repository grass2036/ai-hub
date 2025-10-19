"""
AI模型成本优化系统
Week 5 Day 4: 高级AI功能 - 模型成��优化
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from abc import ABC, abstractmethod

from backend.ai.model_manager import model_manager, AIModel, TaskType
from backend.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CostOptimizationStrategy(Enum):
    """成本优化策略"""
    CHEAPEST = "cheapest"                   # 最便宜
    BEST_VALUE = "best_value"              # 最佳性价比
    BUDGET_CONSTRAINED = "budget_constrained"  # 预算约束
    PERFORMANCE_OPTIMIZED = "performance_optimized"  # 性能优化
    HYBRID = "hybrid"                      # 混合策略


class BudgetAlertType(Enum):
    """预算告警类型"""
    WARNING = "warning"     # 警告
    CRITICAL = "critical"   # 严重
    EXCEEDED = "exceeded"   # 超出


@dataclass
class CostLimit:
    """成本限制"""
    limit_id: str
    name: str
    time_period: str  # hourly, daily, weekly, monthly
    amount: float
    currency: str = "USD"
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    model_ids: List[str] = None
    task_types: List[str] = None
    is_active: bool = True
    created_at: datetime = None

    def __post_init__(self):
        if self.model_ids is None:
            self.model_ids = []
        if self.task_types is None:
            self.task_types = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data


@dataclass
class CostRecord:
    """成本记录"""
    record_id: str
    model_id: str
    user_id: Optional[str]
    organization_id: Optional[str]
    task_type: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    currency: str = "USD"
    timestamp: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class CostAnalysis:
    """成本分析"""
    period_start: datetime
    period_end: datetime
    total_cost: float
    total_requests: int
    total_tokens: int
    avg_cost_per_request: float
    avg_cost_per_1k_tokens: float
    cost_by_model: Dict[str, float]
    cost_by_task_type: Dict[str, float]
    cost_trend: List[Dict[str, Any]]
    recommendations: List[str]
    potential_savings: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_cost": self.total_cost,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "avg_cost_per_request": self.avg_cost_per_request,
            "avg_cost_per_1k_tokens": self.avg_cost_per_1k_tokens,
            "cost_by_model": self.cost_by_model,
            "cost_by_task_type": self.cost_by_task_type,
            "cost_trend": self.cost_trend,
            "recommendations": self.recommendations,
            "potential_savings": self.potential_savings
        }


@dataclass
class BudgetAlert:
    """预算告警"""
    alert_id: str
    limit_id: str
    alert_type: BudgetAlertType
    current_spend: float
    limit_amount: float
    percentage_used: float
    message: str
    timestamp: datetime
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data


class CostTracker:
    """成本跟踪器"""

    def __init__(self):
        self.cost_records: List[CostRecord] = []
        self.cost_limits: Dict[str, CostLimit] = {}
        self.budget_alerts: List[BudgetAlert] = []

    def record_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        task_type: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CostRecord:
        """记录成本"""
        record = CostRecord(
            record_id=str(int(time.time() * 1000000)),
            model_id=model_id,
            user_id=user_id,
            organization_id=organization_id,
            task_type=task_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=cost,
            metadata=metadata or {}
        )

        self.cost_records.append(record)

        # 保持最近10000条记录
        if len(self.cost_records) > 10000:
            self.cost_records = self.cost_records[-10000:]

        # 检查预算限制
        self._check_budget_limits(record)

        return record

    def _check_budget_limits(self, record: CostRecord):
        """检查预算限制"""
        for cost_limit in self.cost_limits.values():
            if not cost_limit.is_active:
                continue

            # 检查是否适用于此记录
            if (cost_limit.user_id and cost_limit.user_id != record.user_id):
                continue
            if (cost_limit.organization_id and cost_limit.organization_id != record.organization_id):
                continue
            if (cost_limit.model_ids and record.model_id not in cost_limit.model_ids):
                continue
            if (cost_limit.task_types and record.task_type not in cost_limit.task_types):
                continue

            # 计算当前周期内的成本
            current_spend = self._calculate_period_spend(cost_limit, record)
            percentage = (current_spend / cost_limit.amount) * 100

            # 检查是否需要告警
            if percentage >= 100:
                self._create_alert(
                    cost_limit.limit_id,
                    BudgetAlertType.EXCEEDED,
                    current_spend,
                    cost_limit.amount,
                    percentage,
                    f"Budget exceeded: {current_spend:.2f}/{cost_limit.amount:.2f} ({percentage:.1f}%)"
                )
            elif percentage >= 90:
                self._create_alert(
                    cost_limit.limit_id,
                    BudgetAlertType.CRITICAL,
                    current_spend,
                    cost_limit.amount,
                    percentage,
                    f"Budget critical: {current_spend:.2f}/{cost_limit.amount:.2f} ({percentage:.1f}%)"
                )
            elif percentage >= 75:
                self._create_alert(
                    cost_limit.limit_id,
                    BudgetAlertType.WARNING,
                    current_spend,
                    cost_limit.amount,
                    percentage,
                    f"Budget warning: {current_spend:.2f}/{cost_limit.amount:.2f} ({percentage:.1f}%)"
                )

    def _calculate_period_spend(self, cost_limit: CostLimit, current_record: CostRecord) -> float:
        """计算周期内的支出"""
        now = current_record.timestamp
        period_start = self._get_period_start(now, cost_limit.time_period)

        # 筛选周期内的记录
        period_records = [
            record for record in self.cost_records
            if record.timestamp >= period_start and record.timestamp <= now
        ]

        # 进一步筛选符合限制条件的记录
        filtered_records = []
        for record in period_records:
            if cost_limit.user_id and cost_limit.user_id != record.user_id:
                continue
            if cost_limit.organization_id and cost_limit.organization_id != record.organization_id:
                continue
            if cost_limit.model_ids and record.model_id not in cost_limit.model_ids:
                continue
            if cost_limit.task_types and record.task_type not in cost_limit.task_types:
                continue
            filtered_records.append(record)

        return sum(record.cost for record in filtered_records)

    def _get_period_start(self, timestamp: datetime, period: str) -> datetime:
        """获取周期开始时间"""
        if period == "hourly":
            return timestamp.replace(minute=0, second=0, microsecond=0)
        elif period == "daily":
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            days_since_monday = timestamp.weekday()
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
        elif period == "monthly":
            return timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return timestamp - timedelta(hours=1)

    def _create_alert(
        self,
        limit_id: str,
        alert_type: BudgetAlertType,
        current_spend: float,
        limit_amount: float,
        percentage: float,
        message: str
    ):
        """创建告警"""
        # 检查是否已有未解决的相同类型告警
        existing_alert = next(
            (alert for alert in self.budget_alerts
             if alert.limit_id == limit_id and alert.alert_type == alert_type and not alert.is_resolved),
            None
        )

        if existing_alert:
            return  # 已有未解决的告警

        alert = BudgetAlert(
            alert_id=str(int(time.time() * 1000000)),
            limit_id=limit_id,
            alert_type=alert_type,
            current_spend=current_spend,
            limit_amount=limit_amount,
            percentage=percentage,
            message=message,
            timestamp=datetime.utcnow()
        )

        self.budget_alerts.append(alert)
        logger.warning(f"Budget alert created: {message}")

    def get_cost_analysis(
        self,
        period: str = "daily",
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> CostAnalysis:
        """获取成本分析"""
        now = datetime.utcnow()
        period_start = self._get_period_start(now, period)

        # 筛选记录
        filtered_records = []
        for record in self.cost_records:
            if record.timestamp < period_start:
                continue
            if user_id and record.user_id != user_id:
                continue
            if organization_id and record.organization_id != organization_id:
                continue
            filtered_records.append(record)

        if not filtered_records:
            return CostAnalysis(
                period_start=period_start,
                period_end=now,
                total_cost=0,
                total_requests=0,
                total_tokens=0,
                avg_cost_per_request=0,
                avg_cost_per_1k_tokens=0,
                cost_by_model={},
                cost_by_task_type={},
                cost_trend=[],
                recommendations=[],
                potential_savings=0
            )

        # 计算基础统计
        total_cost = sum(record.cost for record in filtered_records)
        total_requests = len(filtered_records)
        total_tokens = sum(record.total_tokens for record in filtered_records)
        avg_cost_per_request = total_cost / total_requests if total_requests > 0 else 0
        avg_cost_per_1k_tokens = (total_cost / total_tokens * 1000) if total_tokens > 0 else 0

        # 按模型分组
        cost_by_model = {}
        for record in filtered_records:
            cost_by_model[record.model_id] = cost_by_model.get(record.model_id, 0) + record.cost

        # 按任务类型分组
        cost_by_task_type = {}
        for record in filtered_records:
            cost_by_task_type[record.task_type] = cost_by_task_type.get(record.task_type, 0) + record.cost

        # 生成建议
        recommendations = self._generate_recommendations(filtered_records, cost_by_model)
        potential_savings = self._calculate_potential_savings(filtered_records, cost_by_model)

        # 成本趋势（简化版本）
        cost_trend = self._calculate_cost_trend(filtered_records, period)

        return CostAnalysis(
            period_start=period_start,
            period_end=now,
            total_cost=total_cost,
            total_requests=total_requests,
            total_tokens=total_tokens,
            avg_cost_per_request=avg_cost_per_request,
            avg_cost_per_1k_tokens=avg_cost_per_1k_tokens,
            cost_by_model=cost_by_model,
            cost_by_task_type=cost_by_task_type,
            cost_trend=cost_trend,
            recommendations=recommendations,
            potential_savings=potential_savings
        )

    def _generate_recommendations(self, records: List[CostRecord], cost_by_model: Dict[str, float]) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 找出最昂贵的模型
        if cost_by_model:
            most_expensive_model = max(cost_by_model.items(), key=lambda x: x[1])
            recommendations.append(
                f"Most expensive model: {most_expensive_model[0]} (${most_expensive_model[1]:.2f}). "
                "Consider switching to a cheaper alternative."
            )

        # 检查平均token使用量
        avg_tokens = sum(record.total_tokens for record in records) / len(records) if records else 0
        if avg_tokens > 1000:
            recommendations.append(
                f"Average tokens per request: {avg_tokens:.0f}. "
                "Consider optimizing prompts to reduce token usage."
            )

        # 检查高频使用
        total_requests = len(records)
        if total_requests > 1000:
            recommendations.append(
                f"High usage detected: {total_requests} requests. "
                "Consider implementing caching for repeated requests."
            )

        # 检查昂贵的任务类型
        cost_by_task = {}
        for record in records:
            cost_by_task[record.task_type] = cost_by_task.get(record.task_type, 0) + record.cost

        if cost_by_task:
            expensive_task = max(cost_by_task.items(), key=lambda x: x[1])
            if expensive_task[1] > sum(cost_by_task.values()) * 0.5:
                recommendations.append(
                    f"Task type '{expensive_task[0]}' accounts for >50% of costs. "
                    "Consider optimizing this task type."
                )

        return recommendations

    def _calculate_potential_savings(self, records: List[CostRecord], cost_by_model: Dict[str, float]) -> float:
        """计算潜在节省"""
        if not cost_by_model:
            return 0

        # 简化计算：假设可以切换到便宜30%的模型
        total_cost = sum(cost_by_model.values())
        potential_savings = total_cost * 0.3

        return potential_savings

    def _calculate_cost_trend(self, records: List[CostRecord], period: str) -> List[Dict[str, Any]]:
        """计算成本趋势"""
        # 简化的趋势计算
        if not records:
            return []

        # 按时间分组
        trend_data = {}
        for record in records:
            if period == "hourly":
                time_key = record.timestamp.strftime("%Y-%m-%d %H:00")
            elif period == "daily":
                time_key = record.timestamp.strftime("%Y-%m-%d")
            elif period == "weekly":
                time_key = record.timestamp.strftime("%Y-W%U")
            else:  # monthly
                time_key = record.timestamp.strftime("%Y-%m")

            if time_key not in trend_data:
                trend_data[time_key] = {"cost": 0, "requests": 0}
            trend_data[time_key]["cost"] += record.cost
            trend_data[time_key]["requests"] += 1

        # 转换为列表
        trend = [
            {
                "period": period,
                "cost": data["cost"],
                "requests": data["requests"]
            }
            for period, data in sorted(trend_data.items())
        ]

        return trend

    def add_cost_limit(self, cost_limit: CostLimit) -> str:
        """添加成本限制"""
        self.cost_limits[cost_limit.limit_id] = cost_limit
        logger.info(f"Added cost limit: {cost_limit.name} (${cost_limit.amount} {cost_limit.time_period})")
        return cost_limit.limit_id

    def remove_cost_limit(self, limit_id: str) -> bool:
        """移除成本限制"""
        if limit_id in self.cost_limits:
            del self.cost_limits[limit_id]
            logger.info(f"Removed cost limit: {limit_id}")
            return True
        return False

    def get_budget_alerts(self, unresolved_only: bool = True) -> List[BudgetAlert]:
        """获取预算告警"""
        if unresolved_only:
            return [alert for alert in self.budget_alerts if not alert.is_resolved]
        return self.budget_alerts

    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        for alert in self.budget_alerts:
            if alert.alert_id == alert_id:
                alert.is_resolved = True
                alert.resolved_at = datetime.utcnow()
                return True
        return False


class CostOptimizer:
    """成本优化器"""

    def __init__(self):
        self.cost_tracker = CostTracker()
        self.optimization_cache = {}

    async def optimize_model_selection(
        self,
        task_type: TaskType,
        requirements: Dict[str, Any],
        strategy: CostOptimizationStrategy = CostOptimizationStrategy.BEST_VALUE,
        budget_constraint: Optional[float] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> Optional[str]:
        """优化模型选择"""
        try:
            manager = await model_manager
            cache_key = f"{task_type.value}_{strategy.value}_{budget_constraint}_{user_id}_{organization_id}"

            # 检查缓存
            if cache_key in self.optimization_cache:
                cached_result = self.optimization_cache[cache_key]
                if datetime.utcnow() - cached_result['timestamp'] < timedelta(minutes=30):
                    return cached_result['model_id']

            # 获取候选模型
            candidate_models = self._get_candidate_models(manager, task_type, user_id, organization_id)

            if not candidate_models:
                return None

            # 根据策略选择模型
            selected_model = await self._select_model_by_strategy(
                candidate_models, strategy, requirements, budget_constraint
            )

            # 缓存结果
            self.optimization_cache[cache_key] = {
                'model_id': selected_model,
                'timestamp': datetime.utcnow()
            }

            return selected_model

        except Exception as e:
            logger.error(f"Cost optimization failed: {e}")
            return None

    def _get_candidate_models(
        self,
        manager: 'ModelManager',
        task_type: TaskType,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> List[AIModel]:
        """获取候选模型"""
        candidates = []

        for model in manager.get_active_models():
            if task_type in model.capabilities.supported_tasks:
                # 检查预算限制
                if not self._is_model_within_budget(model.model_id, user_id, organization_id):
                    continue
                candidates.append(model)

        return candidates

    def _is_model_within_budget(
        self,
        model_id: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> bool:
        """检查模型是否在预算内"""
        for cost_limit in self.cost_tracker.cost_limits.values():
            if not cost_limit.is_active:
                continue

            if cost_limit.user_id and cost_limit.user_id != user_id:
                continue
            if cost_limit.organization_id and cost_limit.organization_id != organization_id:
                continue
            if cost_limit.model_ids and model_id not in cost_limit.model_ids:
                continue

            current_spend = self.cost_tracker._calculate_period_spend(
                cost_limit,
                CostRecord(
                    record_id="temp",
                    model_id=model_id,
                    task_type="temp",
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    cost=0
                )
            )

            if current_spend >= cost_limit.amount:
                return False

        return True

    async def _select_model_by_strategy(
        self,
        models: List[AIModel],
        strategy: CostOptimizationStrategy,
        requirements: Dict[str, Any],
        budget_constraint: Optional[float]
    ) -> Optional[str]:
        """根据策略选择模型"""
        if strategy == CostOptimizationStrategy.CHEAPEST:
            return self._select_cheapest_model(models, requirements)
        elif strategy == CostOptimizationStrategy.BEST_VALUE:
            return self._select_best_value_model(models, requirements)
        elif strategy == CostOptimizationStrategy.BUDGET_CONSTRAINED:
            return self._select_budget_constrained_model(models, requirements, budget_constraint)
        elif strategy == CostOptimizationStrategy.PERFORMANCE_OPTIMIZED:
            return self._select_performance_optimized_model(models, requirements)
        elif strategy == CostOptimizationStrategy.HYBRID:
            return self._select_hybrid_model(models, requirements)
        else:
            return models[0].model_id if models else None

    def _select_cheapest_model(self, models: List[AIModel], requirements: Dict[str, Any]) -> str:
        """选择最便宜的模型"""
        return min(models, key=lambda m: m.capabilities.cost_per_input_token + m.capabilities.cost_per_output_token).model_id

    def _select_best_value_model(self, models: List[AIModel], requirements: Dict[str, Any]) -> str:
        """选择最佳性价比模型"""
        def value_score(model: AIModel) -> float:
            cost = model.capabilities.cost_per_input_token + model.capabilities.cost_per_output_token
            quality = model.metrics.quality_score or 0.5
            return quality / max(cost, 0.001)  # 避免除零

        return max(models, key=value_score).model_id

    def _select_budget_constrained_model(
        self,
        models: List[AIModel],
        requirements: Dict[str, Any],
        budget_constraint: Optional[float]
    ) -> str:
        """选择预算约束内的模型"""
        if not budget_constraint:
            return self._select_best_value_model(models, requirements)

        # 估算请求成本
        estimated_tokens = requirements.get('estimated_tokens', 500)
        affordable_models = []

        for model in models:
            estimated_cost = (estimated_tokens / 1000) * (
                model.capabilities.cost_per_input_token + model.capabilities.cost_per_output_token
            )
            if estimated_cost <= budget_constraint:
                affordable_models.append(model)

        if affordable_models:
            return self._select_best_value_model(affordable_models, requirements)
        else:
            # 如果没有负担得起的模型，选择最便宜的
            return self._select_cheapest_model(models, requirements)

    def _select_performance_optimized_model(self, models: List[AIModel], requirements: Dict[str, Any]) -> str:
        """选择性能优化的模型"""
        def performance_score(model: AIModel) -> float:
            response_time = model.metrics.avg_response_time or 1000
            quality = model.metrics.quality_score or 0.5
            success_rate = model.metrics.success_rate or 50
            return (quality * success_rate) / max(response_time, 1)

        return max(models, key=performance_score).model_id

    def _select_hybrid_model(self, models: List[AIModel], requirements: Dict[str, Any]) -> str:
        """选择混合策略模型"""
        def hybrid_score(model: AIModel) -> float:
            cost = model.capabilities.cost_per_input_token + model.capabilities.cost_per_output_token
            quality = model.metrics.quality_score or 0.5
            response_time = model.metrics.avg_response_time or 1000
            success_rate = model.metrics.success_rate or 50

            # 综合评分
            return (quality * 0.4 + success_rate * 0.3) / (max(cost, 0.001) * 0.3 + max(response_time, 1) * 0.3)

        return max(models, key=hybrid_score).model_id

    def track_usage_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        task_type: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> float:
        """跟踪使用成本"""
        # 获取模型定价
        manager = model_manager
        model = None
        for m in manager.models.values():
            if m.model_id == model_id:
                model = m
                break

        if not model:
            logger.warning(f"Model not found for cost tracking: {model_id}")
            return 0.0

        # 计算成本
        input_cost = (input_tokens / 1000) * model.capabilities.cost_per_input_token
        output_cost = (output_tokens / 1000) * model.capabilities.cost_per_output_token
        total_cost = input_cost + output_cost

        # 记录成本
        self.cost_tracker.record_cost(
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=total_cost,
            task_type=task_type,
            user_id=user_id,
            organization_id=organization_id,
            metadata=metadata
        )

        return total_cost

    async def get_cost_optimization_recommendations(
        self,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        period: str = "weekly"
    ) -> Dict[str, Any]:
        """获取成本优化建议"""
        # 获取成本分析
        cost_analysis = self.cost_tracker.get_cost_analysis(period, user_id, organization_id)

        # 生成具体建议
        recommendations = []
        potential_total_savings = 0

        # 1. 模型切换建议
        for model_id, cost in cost_analysis.cost_by_model.items():
            if cost > cost_analysis.total_cost * 0.3:  # 占用超过30%成本的模型
                manager = await model_manager
                cheaper_alternatives = []

                for model in manager.get_active_models():
                    if (model.model_id != model_id and
                        model.capabilities.cost_per_input_token < manager.models[model_id].capabilities.cost_per_input_token):
                        cheaper_alternatives.append(model)

                if cheaper_alternatives:
                    best_alternative = min(cheaper_alternatives, key=lambda m: m.capabilities.cost_per_input_token)
                    savings_potential = cost * 0.4  # 估计节省40%
                    potential_total_savings += savings_potential

                    recommendations.append({
                        "type": "model_switch",
                        "model_id": model_id,
                        "current_cost": cost,
                        "recommended_model": best_alternative.model_id,
                        "potential_savings": savings_potential,
                        "description": f"Switch from {model_id} to {best_alternative.model_id} to save ${savings_potential:.2f}"
                    })

        # 2. 缓存建议
        if cost_analysis.avg_cost_per_request > 0.01:  # 平均请求成本超过1分钱
            caching_savings = cost_analysis.total_cost * 0.2  # 估计缓存能节省20%
            potential_total_savings += caching_savings

            recommendations.append({
                "type": "caching",
                "current_avg_cost": cost_analysis.avg_cost_per_request,
                "potential_savings": caching_savings,
                "description": f"Implement caching to save ${caching_savings:.2f} on repeated requests"
            })

        # 3. Token优化建议
        if cost_analysis.total_tokens > 0:
            avg_tokens_per_request = cost_analysis.total_tokens / cost_analysis.total_requests
            if avg_tokens_per_request > 500:  # 平均超过500 tokens
                token_optimization_savings = cost_analysis.total_cost * 0.15  # 估计能节省15%
                potential_total_savings += token_optimization_savings

                recommendations.append({
                    "type": "token_optimization",
                    "avg_tokens_per_request": avg_tokens_per_request,
                    "potential_savings": token_optimization_savings,
                    "description": f"Optimize prompts to reduce token usage and save ${token_optimization_savings:.2f}"
                })

        return {
            "period": period,
            "current_cost_analysis": cost_analysis.to_dict(),
            "recommendations": recommendations,
            "total_potential_savings": potential_total_savings,
            "generated_at": datetime.utcnow().isoformat()
        }

    def set_budget_limit(
        self,
        name: str,
        amount: float,
        time_period: str,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        model_ids: Optional[List[str]] = None,
        task_types: Optional[List[str]] = None
    ) -> str:
        """设置预算限制"""
        limit_id = str(int(time.time() * 1000000))

        cost_limit = CostLimit(
            limit_id=limit_id,
            name=name,
            amount=amount,
            time_period=time_period,
            user_id=user_id,
            organization_id=organization_id,
            model_ids=model_ids or [],
            task_types=task_types or []
        )

        self.cost_tracker.add_cost_limit(cost_limit)
        return limit_id

    def get_budget_status(self, limit_id: str) -> Optional[Dict[str, Any]]:
        """获取预算状态"""
        cost_limit = self.cost_tracker.cost_limits.get(limit_id)
        if not cost_limit:
            return None

        # 计算当前支出
        now = datetime.utcnow()
        current_spend = self.cost_tracker._calculate_period_spend(
            cost_limit,
            CostRecord(
                record_id="temp",
                model_id="temp",
                task_type="temp",
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost=0,
                timestamp=now
            )
        )

        percentage = (current_spend / cost_limit.amount) * 100 if cost_limit.amount > 0 else 0

        return {
            "limit": cost_limit.to_dict(),
            "current_spend": current_spend,
            "remaining_budget": cost_limit.amount - current_spend,
            "percentage_used": percentage,
            "status": "exceeded" if percentage >= 100 else "critical" if percentage >= 90 else "warning" if percentage >= 75 else "healthy"
        }


# 全局成本优化器实例
cost_optimizer = CostOptimizer()


async def get_cost_optimizer() -> CostOptimizer:
    """获取成本优化器实例"""
    return cost_optimizer


# 成本优化装饰器
def optimize_cost(
    strategy: CostOptimizationStrategy = CostOptimizationStrategy.BEST_VALUE,
    budget_constraint: Optional[float] = None,
    track_usage: bool = True
):
    """成本优化装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            optimizer = await get_cost_optimizer()
            task_type = TaskType(kwargs.get('task_type', 'chat'))
            requirements = kwargs.get('requirements', {})
            user_id = kwargs.get('user_id')
            organization_id = kwargs.get('organization_id')

            # 优化模型选择
            optimized_model = await optimizer.optimize_model_selection(
                task_type=task_type,
                requirements=requirements,
                strategy=strategy,
                budget_constraint=budget_constraint,
                user_id=user_id,
                organization_id=organization_id
            )

            if optimized_model:
                kwargs['model'] = optimized_model

            # 执行函数
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            # 跟踪成本
            if track_usage and optimized_model:
                input_tokens = kwargs.get('input_tokens', 0)
                output_tokens = kwargs.get('output_tokens', 0)

                if input_tokens == 0 or output_tokens == 0:
                    # 尝试从响应中估算token数量
                    if isinstance(result, dict):
                        input_tokens = result.get('usage', {}).get('prompt_tokens', 0)
                        output_tokens = result.get('usage', {}).get('completion_tokens', 0)

                cost = optimizer.track_usage_cost(
                    model_id=optimized_model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    task_type=task_type.value,
                    user_id=user_id,
                    organization_id=organization_id,
                    metadata={
                        'execution_time': execution_time,
                        'function': func.__name__,
                        'strategy': strategy.value
                    }
                )

                # 将成本信息添加到结果中
                if isinstance(result, dict):
                    result['cost_info'] = {
                        'model_id': optimized_model,
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'total_tokens': input_tokens + output_tokens,
                        'cost': cost,
                        'currency': 'USD',
                        'optimization_strategy': strategy.value
                    }

            return result

        return wrapper
    return decorator