"""
AI模型管理器
Week 5 Day 4: 高级AI功能 - 多模型管理
"""

import asyncio
import time
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from abc import ABC, abstractmethod

from backend.config.settings import get_settings
from backend.core.ai_service import AIServiceManager
from backend.core.openrouter_service import OpenRouterService
from backend.core.providers.gemini_service import GeminiService

logger = logging.getLogger(__name__)
settings = get_settings()


class ModelStatus(Enum):
    """模型状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class ModelProvider(Enum):
    """模型提供商"""
    OPENROUTER = "openrouter"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    CUSTOM = "custom"


class TaskType(Enum):
    """任务类型"""
    CHAT = "chat"
    COMPLETION = "completion"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CODE_GENERATION = "code_generation"
    ANALYSIS = "analysis"
    CREATIVE = "creative"


@dataclass
class ModelMetrics:
    """模型性能指标"""
    model_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    avg_tokens_per_request: float = 0.0
    cost_per_1k_tokens: float = 0.0
    quality_score: float = 0.0
    user_satisfaction: float = 0.0
    error_rate: float = 0.0
    uptime_percentage: float = 100.0
    last_updated: datetime = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.utcnow()

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['success_rate'] = self.success_rate
        data['last_updated'] = self.last_updated.isoformat()
        return data


@dataclass
class ModelCapabilities:
    """模型能力描述"""
    model_id: str
    supported_tasks: List[TaskType]
    max_tokens: int
    context_window: int
    supports_streaming: bool
    supports_function_calling: bool
    supports_vision: bool
    supports_code_execution: bool
    languages: List[str]
    cost_per_input_token: float
    cost_per_output_token: float
    strengths: List[str]
    weaknesses: List[str]


@dataclass
class AIModel:
    """AI模型定义"""
    model_id: str
    name: str
    provider: ModelProvider
    version: str
    status: ModelStatus
    capabilities: ModelCapabilities
    metrics: ModelMetrics
    priority: int = 1  # 优先级，数字越大优先级越高
    is_fallback: bool = False  # 是否作为备用模型
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class ModelPerformanceTracker:
    """模型性能跟踪器"""

    def __init__(self):
        self.request_history: Dict[str, List[Dict]] = {}
        self.performance_data: Dict[str, ModelMetrics] = {}

    def record_request(self, model_id: str, request_data: Dict):
        """记录请求数据"""
        if model_id not in self.request_history:
            self.request_history[model_id] = []

        request_data['timestamp'] = datetime.utcnow()
        self.request_history[model_id].append(request_data)

        # 保持最近1000条记录
        if len(self.request_history[model_id]) > 1000:
            self.request_history[model_id] = self.request_history[model_id][-1000:]

    def calculate_metrics(self, model_id: str, time_window: int = 3600) -> ModelMetrics:
        """计算模型性能指标"""
        now = datetime.utcnow()
        cutoff_time = now - timedelta(seconds=time_window)

        # 获取时间窗口内的请求
        recent_requests = [
            req for req in self.request_history.get(model_id, [])
            if req['timestamp'] > cutoff_time
        ]

        if not recent_requests:
            return ModelMetrics(model_id=model_id)

        # 基础统计
        total_requests = len(recent_requests)
        successful_requests = len([req for req in recent_requests if req.get('success', False)])
        failed_requests = total_requests - successful_requests

        # 响应时间统计
        response_times = [req.get('response_time', 0) for req in recent_requests if req.get('response_time')]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times) if response_times else 0
        p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else max(response_times) if response_times else 0

        # Token统计
        total_tokens = [req.get('total_tokens', 0) for req in recent_requests if req.get('total_tokens')]
        avg_tokens = statistics.mean(total_tokens) if total_tokens else 0

        # 成本统计
        costs = [req.get('cost', 0) for req in recent_requests if req.get('cost')]
        total_cost = sum(costs)
        total_tokens_sum = sum(total_tokens)
        cost_per_1k_tokens = (total_cost / total_tokens_sum * 1000) if total_tokens_sum > 0 else 0

        # 质量评分（如果有用户反馈）
        quality_scores = [req.get('quality_score', 0) for req in recent_requests if req.get('quality_score')]
        avg_quality = statistics.mean(quality_scores) if quality_scores else 0

        # 用户满意度
        satisfaction_scores = [req.get('user_satisfaction', 0) for req in recent_requests if req.get('user_satisfaction')]
        avg_satisfaction = statistics.mean(satisfaction_scores) if satisfaction_scores else 0

        # 错误率
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0

        # 可用性（简化计算，基于连续错误）
        uptime_percentage = 100.0 - error_rate

        return ModelMetrics(
            model_id=model_id,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            avg_tokens_per_request=avg_tokens,
            cost_per_1k_tokens=cost_per_1k_tokens,
            quality_score=avg_quality,
            user_satisfaction=avg_satisfaction,
            error_rate=error_rate,
            uptime_percentage=uptime_percentage,
            last_updated=now
        )


class ModelSelector:
    """模型选择器"""

    def __init__(self, model_manager: 'ModelManager'):
        self.model_manager = model_manager

    def select_best_model(
        self,
        task_type: TaskType,
        requirements: Optional[Dict[str, Any]] = None,
        budget_constraint: Optional[float] = None,
        latency_constraint: Optional[float] = None
    ) -> Optional[AIModel]:
        """选择最佳模型"""
        candidate_models = self._get_candidate_models(task_type)

        if not candidate_models:
            return None

        # 根据约束条件过滤
        if budget_constraint:
            candidate_models = [
                model for model in candidate_models
                if self._estimate_cost(model, requirements) <= budget_constraint
            ]

        if latency_constraint:
            candidate_models = [
                model for model in candidate_models
                if model.metrics.avg_response_time <= latency_constraint
            ]

        if not candidate_models:
            return None

        # 综合评分选择最佳模型
        best_model = max(candidate_models, key=lambda m: self._calculate_score(m, requirements))
        return best_model

    def _get_candidate_models(self, task_type: TaskType) -> List[AIModel]:
        """获取候选模型"""
        candidates = []
        for model in self.model_manager.models.values():
            if (model.status == ModelStatus.ACTIVE and
                task_type in model.capabilities.supported_tasks):
                candidates.append(model)
        return candidates

    def _calculate_score(self, model: AIModel, requirements: Optional[Dict] = None) -> float:
        """计算模型综合评分"""
        score = 0.0

        # 性能评分 (40%)
        performance_score = (
            model.metrics.success_rate * 0.3 +
            (100 - model.metrics.error_rate) * 0.3 +
            model.metrics.quality_score * 0.2 +
            model.metrics.user_satisfaction * 0.2
        )
        score += performance_score * 0.4

        # 成本评分 (25%)
        cost_score = max(0, 100 - model.metrics.cost_per_1k_tokens)
        score += cost_score * 0.25

        # 速度评分 (20%)
        speed_score = max(0, 100 - model.metrics.avg_response_time / 10)  # 10秒为0分
        score += speed_score * 0.2

        # 可靠性评分 (15%)
        reliability_score = model.metrics.uptime_percentage
        score += reliability_score * 0.15

        # 优先级加分
        score += model.priority * 2

        return score

    def _estimate_cost(self, model: AIModel, requirements: Optional[Dict] = None) -> float:
        """估算请求成本"""
        if not requirements:
            return model.capabilities.cost_per_input_token + model.capabilities.cost_per_output_token

        estimated_input_tokens = requirements.get('input_tokens', 100)
        estimated_output_tokens = requirements.get('output_tokens', 200)

        input_cost = (estimated_input_tokens / 1000) * model.capabilities.cost_per_input_token
        output_cost = (estimated_output_tokens / 1000) * model.capabilities.cost_per_output_token

        return input_cost + output_cost


class ModelManager:
    """AI模型管理器"""

    def __init__(self):
        self.models: Dict[str, AIModel] = {}
        self.performance_tracker = ModelPerformanceTracker()
        self.model_selector = ModelSelector(self)
        self.ai_service_manager = AIServiceManager()
        self._load_default_models()

    def _load_default_models(self):
        """加载默认模型配置"""
        default_models = [
            # OpenRouter 模型
            AIModel(
                model_id="grok-4-fast:free",
                name="Grok 4 Fast (Free)",
                provider=ModelProvider.OPENROUTER,
                version="1.0",
                status=ModelStatus.ACTIVE,
                capabilities=ModelCapabilities(
                    model_id="grok-4-fast:free",
                    supported_tasks=[
                        TaskType.CHAT, TaskType.COMPLETION, TaskType.CODE_GENERATION,
                        TaskType.ANALYSIS, TaskType.CREATIVE
                    ],
                    max_tokens=4096,
                    context_window=8192,
                    supports_streaming=True,
                    supports_function_calling=False,
                    supports_vision=False,
                    supports_code_execution=False,
                    languages=["en", "zh"],
                    cost_per_input_token=0.0,
                    cost_per_output_token=0.0,
                    strengths=["快速响应", "免费使用", "代码生成"],
                    weaknesses=["上下文窗口较小", "功能有限"]
                ),
                metrics=ModelMetrics(model_id="grok-4-fast:free"),
                priority=8,
                is_fallback=False
            ),

            AIModel(
                model_id="deepseek-chat-v3.1:free",
                name="DeepSeek Chat V3.1 (Free)",
                provider=ModelProvider.OPENROUTER,
                version="3.1",
                status=ModelStatus.ACTIVE,
                capabilities=ModelCapabilities(
                    model_id="deepseek-chat-v3.1:free",
                    supported_tasks=[
                        TaskType.CHAT, TaskType.COMPLETION, TaskType.TRANSLATION,
                        TaskType.SUMMARIZATION, TaskType.ANALYSIS
                    ],
                    max_tokens=4096,
                    context_window=32768,
                    supports_streaming=True,
                    supports_function_calling=False,
                    supports_vision=False,
                    supports_code_execution=False,
                    languages=["en", "zh", "ja", "ko"],
                    cost_per_input_token=0.0,
                    cost_per_output_token=0.0,
                    strengths=["大上下文窗口", "多语言支持", "免费使用"],
                    weaknesses=["推理速度较慢"]
                ),
                metrics=ModelMetrics(model_id="deepseek-chat-v3.1:free"),
                priority=7,
                is_fallback=False
            ),

            # Gemini 模型作为备用
            AIModel(
                model_id="gemini-pro",
                name="Gemini Pro",
                provider=ModelProvider.GEMINI,
                version="1.0",
                status=ModelStatus.ACTIVE,
                capabilities=ModelCapabilities(
                    model_id="gemini-pro",
                    supported_tasks=[
                        TaskType.CHAT, TaskType.COMPLETION, TaskType.TRANSLATION,
                        TaskType.SUMMARIZATION, TaskType.ANALYSIS
                    ],
                    max_tokens=2048,
                    context_window=32768,
                    supports_streaming=True,
                    supports_function_calling=False,
                    supports_vision=False,
                    supports_code_execution=False,
                    languages=["en", "zh", "ja", "ko", "es", "fr"],
                    cost_per_input_token=0.00025,
                    cost_per_output_token=0.0005,
                    strengths=["多语言支持", "谷歌生态", "稳定可靠"],
                    weaknesses ["成本较高", "上下文限制"]
                ),
                metrics=ModelMetrics(model_id="gemini-pro"),
                priority=5,
                is_fallback=True
            )
        ]

        for model in default_models:
            self.models[model.model_id] = model

    async def get_best_model(
        self,
        task_type: TaskType,
        requirements: Optional[Dict[str, Any]] = None,
        budget_constraint: Optional[float] = None,
        latency_constraint: Optional[float] = None
    ) -> Optional[str]:
        """获取最佳模型ID"""
        model = self.model_selector.select_best_model(
            task_type=task_type,
            requirements=requirements,
            budget_constraint=budget_constraint,
            latency_constraint=latency_constraint
        )
        return model.model_id if model else None

    async def get_fallback_model(self, primary_model_id: str) -> Optional[str]:
        """获取备用模型"""
        primary_model = self.models.get(primary_model_id)
        if not primary_model:
            return None

        # 寻找同类型的备用模型
        fallback_candidates = [
            model for model in self.models.values()
            if (model.model_id != primary_model_id and
                model.is_fallback and
                model.status == ModelStatus.ACTIVE and
                any(task in model.capabilities.supported_tasks
                    for task in primary_model.capabilities.supported_tasks))
        ]

        if fallback_candidates:
            return max(fallback_candidates, key=lambda m: m.priority).model_id

        return None

    def record_model_usage(
        self,
        model_id: str,
        success: bool,
        response_time: float,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        quality_score: Optional[float] = None,
        user_satisfaction: Optional[float] = None,
        error_message: Optional[str] = None
    ):
        """记录模型使用情况"""
        request_data = {
            'success': success,
            'response_time': response_time,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'cost': cost,
            'quality_score': quality_score,
            'user_satisfaction': user_satisfaction,
            'error_message': error_message
        }

        self.performance_tracker.record_request(model_id, request_data)

        # 更新模型指标
        updated_metrics = self.performance_tracker.calculate_metrics(model_id)
        self.models[model_id].metrics = updated_metrics

    def get_model_metrics(self, model_id: str, time_window: int = 3600) -> Optional[ModelMetrics]:
        """获取模型性能指标"""
        return self.performance_tracker.calculate_metrics(model_id, time_window)

    def get_all_models(self) -> List[AIModel]:
        """获取所有模型"""
        return list(self.models.values())

    def get_active_models(self) -> List[AIModel]:
        """获取活跃模型"""
        return [model for model in self.models.values() if model.status == ModelStatus.ACTIVE]

    def update_model_status(self, model_id: str, status: ModelStatus):
        """更新模型状态"""
        if model_id in self.models:
            self.models[model_id].status = status
            logger.info(f"Model {model_id} status updated to {status.value}")

    def add_model(self, model: AIModel):
        """添加新模型"""
        self.models[model.model_id] = model
        logger.info(f"Added new model: {model.model_id}")

    def remove_model(self, model_id: str):
        """移除模型"""
        if model_id in self.models:
            del self.models[model_id]
            logger.info(f"Removed model: {model_id}")

    async def health_check_models(self) -> Dict[str, bool]:
        """健康检查所有模型"""
        health_results = {}

        for model_id, model in self.models.items():
            try:
                # 简单的健康检查 - 尝试获取服务
                service = await self.ai_service_manager.get_service(model.provider.value)
                if service:
                    health_results[model_id] = True
                    if model.status == ModelStatus.ERROR:
                        self.update_model_status(model_id, ModelStatus.ACTIVE)
                else:
                    health_results[model_id] = False
                    self.update_model_status(model_id, ModelStatus.ERROR)
            except Exception as e:
                logger.error(f"Health check failed for model {model_id}: {e}")
                health_results[model_id] = False
                self.update_model_status(model_id, ModelStatus.ERROR)

        return health_results

    def get_model_recommendations(self, task_type: TaskType, limit: int = 3) -> List[Dict[str, Any]]:
        """获取模型推荐"""
        candidates = self.model_selector._get_candidate_models(task_type)

        # 按评分排序
        sorted_candidates = sorted(
            candidates,
            key=lambda m: self.model_selector._calculate_score(m),
            reverse=True
        )

        recommendations = []
        for model in sorted_candidates[:limit]:
            recommendations.append({
                'model_id': model.model_id,
                'name': model.name,
                'provider': model.provider.value,
                'score': self.model_selector._calculate_score(model),
                'cost_per_1k_tokens': model.metrics.cost_per_1k_tokens,
                'avg_response_time': model.metrics.avg_response_time,
                'success_rate': model.metrics.success_rate,
                'quality_score': model.metrics.quality_score
            })

        return recommendations


# 全局模型管理器实例
model_manager = ModelManager()


async def get_model_manager() -> ModelManager:
    """获取模型管理器实例"""
    return model_manager


# 模型管理装饰器
def with_model_selection(task_type: TaskType):
    """模型选择装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 获取模型管理器
            manager = await get_model_manager()

            # 选择最佳模型
            model_id = await manager.get_best_model(task_type)
            if not model_id:
                raise ValueError(f"No suitable model found for task: {task_type}")

            # 将模型ID添加到参数中
            kwargs['selected_model'] = model_id

            try:
                start_time = time.time()
                result = await func(*args, **kwargs)
                response_time = time.time() - start_time

                # 记录成功使用
                manager.record_model_usage(
                    model_id=model_id,
                    success=True,
                    response_time=response_time,
                    input_tokens=kwargs.get('input_tokens', 0),
                    output_tokens=kwargs.get('output_tokens', 0),
                    cost=kwargs.get('cost', 0)
                )

                return result

            except Exception as e:
                response_time = time.time() - start_time

                # 记录失败使用
                manager.record_model_usage(
                    model_id=model_id,
                    success=False,
                    response_time=response_time,
                    input_tokens=kwargs.get('input_tokens', 0),
                    output_tokens=0,
                    cost=0,
                    error_message=str(e)
                )

                # 尝试使用备用模型
                fallback_model = await manager.get_fallback_model(model_id)
                if fallback_model:
                    logger.warning(f"Primary model {model_id} failed, trying fallback {fallback_model}")
                    kwargs['selected_model'] = fallback_model
                    return await func(*args, **kwargs)
                else:
                    raise

        return wrapper
    return decorator