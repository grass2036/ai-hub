"""
高级AI功能API
Week 5 Day 4: 高级AI功能集成API
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from backend.ai.model_manager import (
    model_manager,
    TaskType,
    AIModel,
    ModelStatus
)
from backend.ai.content_enhancement import (
    content_enhancer,
    ContentEnhancement,
    ContentType,
    QualityMetric
)
from backend.ai.ab_testing import (
    ab_test_manager,
    ABTest,
    TestStatus,
    TrafficSplitStrategy,
    SuccessMetric
)
from backend.ai.cost_optimizer import (
    cost_optimizer,
    CostOptimizationStrategy,
    BudgetAlertType
)

router = APIRouter()


# 请求/响应模型
class ModelSelectionRequest(BaseModel):
    """模型选择请求"""
    task_type: str
    requirements: Dict[str, Any] = {}
    budget_constraint: Optional[float] = None
    latency_constraint: Optional[float] = None


class ContentEnhancementRequest(BaseModel):
    """内容增强请求"""
    content: str
    enhancement_type: str = "quality"
    target_length: Optional[int] = None
    style: Optional[str] = None
    content_type: Optional[str] = None


class ABTestCreateRequest(BaseModel):
    """A/B测试创建请求"""
    name: str
    description: str
    task_type: str
    variants: List[Dict[str, Any]]
    success_metrics: List[str]
    traffic_strategy: str = "equal"
    sample_size: Optional[int] = None
    confidence_level: float = 0.95
    min_runtime_hours: int = 24
    max_runtime_hours: int = 168


class BudgetLimitRequest(BaseModel):
    """预算限制请求"""
    name: str
    amount: float
    time_period: str
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    model_ids: Optional[List[str]] = None
    task_types: Optional[List[str]] = None


# 模型管理API
@router.get("/models")
async def get_models(
    status: Optional[str] = Query(None, description="模型状态过滤"),
    provider: Optional[str] = Query(None, description="提供商过滤"),
    task_type: Optional[str] = Query(None, description="任务类型过滤")
):
    """获取模型列表"""
    try:
        manager = await model_manager
        models = manager.get_all_models()

        # 应用过滤器
        if status:
            try:
                status_enum = ModelStatus(status)
                models = [m for m in models if m.status == status_enum]
            except ValueError:
                pass

        if provider:
            models = [m for m in models if m.provider.value == provider]

        if task_type:
            try:
                task_enum = TaskType(task_type)
                models = [m for m in models if task_enum in m.capabilities.supported_tasks]
            except ValueError:
                pass

        return {
            "success": True,
            "data": [
                {
                    "model_id": model.model_id,
                    "name": model.name,
                    "provider": model.provider.value,
                    "status": model.status.value,
                    "capabilities": {
                        "supported_tasks": [t.value for t in model.capabilities.supported_tasks],
                        "max_tokens": model.capabilities.max_tokens,
                        "context_window": model.capabilities.context_window,
                        "supports_streaming": model.capabilities.supports_streaming,
                        "cost_per_input_token": model.capabilities.cost_per_input_token,
                        "cost_per_output_token": model.capabilities.cost_per_output_token
                    },
                    "metrics": model.metrics.to_dict(),
                    "priority": model.priority,
                    "is_fallback": model.is_fallback
                }
                for model in models
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")


@router.get("/models/{model_id}/metrics")
async def get_model_metrics(
    model_id: str,
    time_window: int = Query(3600, description="时间窗口（秒）")
):
    """获取模型性能指标"""
    try:
        manager = await model_manager
        metrics = manager.get_model_metrics(model_id, time_window)

        if not metrics:
            raise HTTPException(status_code=404, detail="Model not found")

        return {
            "success": True,
            "data": metrics.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model metrics: {str(e)}")


@router.post("/models/select-best")
async def select_best_model(request: ModelSelectionRequest):
    """选择最佳模型"""
    try:
        task_type = TaskType(request.task_type)
        manager = await model_manager

        model_id = await manager.get_best_model(
            task_type=task_type,
            requirements=request.requirements,
            budget_constraint=request.budget_constraint,
            latency_constraint=request.latency_constraint
        )

        if not model_id:
            return {
                "success": False,
                "message": "No suitable model found"
            }

        return {
            "success": True,
            "data": {
                "selected_model": model_id,
                "task_type": request.task_type,
                "requirements": request.requirements
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid task type: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to select model: {str(e)}")


@router.get("/models/recommendations")
async def get_model_recommendations(
    task_type: str = Query(..., description="任务类型"),
    limit: int = Query(3, description="推荐数量限制")
):
    """获取模型推荐"""
    try:
        task_enum = TaskType(task_type)
        manager = await model_manager
        recommendations = manager.get_model_recommendations(task_enum, limit)

        return {
            "success": True,
            "data": recommendations
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid task type: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


# 内容增强API
@router.post("/content/enhance")
async def enhance_content(request: ContentEnhancementRequest):
    """增强内容"""
    try:
        enhancer = await content_enhancer

        # 解析内容类型
        content_type = ContentType.TEXT
        if request.content_type:
            try:
                content_type = ContentType(request.content_type)
            except ValueError:
                pass

        enhancement = await enhancer.enhance_content(
            content=request.content,
            enhancement_type=request.enhancement_type,
            target_length=request.target_length,
            style=request.style
        )

        return {
            "success": True,
            "data": enhancement.to_dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enhance content: {str(e)}")


@router.post("/content/analyze-quality")
async def analyze_content_quality(
    content: str,
    content_type: str = "text"
):
    """分析内容质量"""
    try:
        analyzer = (await content_enhancer).analyzer
        content_enum = ContentType(content_type)

        quality_score = await analyzer.analyze_quality(content, content_enum)

        return {
            "success": True,
            "data": quality_score.to_dict()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid content type: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze quality: {str(e)}")


@router.post("/content/summarize")
async def summarize_content(
    content: str,
    max_length: int = Query(200, description="最大长度"),
    detail_level: str = Query("medium", description="详细级别")
):
    """生成内容摘要"""
    try:
        summarizer = (await content_enhancer).summarizer
        summary = await summarizer.generate_summary(
            content=content,
            max_length=max_length,
            detail_level=detail_level
        )

        return {
            "success": True,
            "data": summary.to_dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to summarize content: {str(e)}")


# A/B测试API
@router.get("/ab-tests")
async def get_ab_tests(
    status: Optional[str] = Query(None, description="测试状态过滤")
):
    """获取A/B测试列表"""
    try:
        manager = await ab_test_manager

        status_filter = None
        if status:
            try:
                status_filter = TestStatus(status)
            except ValueError:
                pass

        tests = await manager.get_all_tests(status_filter)

        return {
            "success": True,
            "data": tests
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get A/B tests: {str(e)}")


@router.post("/ab-tests")
async def create_ab_test(request: ABTestCreateRequest):
    """创建A/B测试"""
    try:
        manager = await ab_test_manager

        task_type = TaskType(request.task_type)
        success_metrics = [SuccessMetric(metric) for metric in request.success_metrics]
        traffic_strategy = TrafficSplitStrategy(request.traffic_strategy)

        test_id = await manager.create_test(
            name=request.name,
            description=request.description,
            task_type=task_type,
            variants=request.variants,
            success_metrics=success_metrics,
            traffic_strategy=traffic_strategy,
            sample_size=request.sample_size,
            confidence_level=request.confidence_level,
            min_runtime_hours=request.min_runtime_hours,
            max_runtime_hours=request.max_runtime_hours
        )

        return {
            "success": True,
            "data": {
                "test_id": test_id,
                "message": "A/B test created successfully"
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create A/B test: {str(e)}")


@router.post("/ab-tests/{test_id}/start")
async def start_ab_test(test_id: str):
    """启动A/B测试"""
    try:
        manager = await ab_test_manager
        success = await manager.start_test(test_id)

        if success:
            return {
                "success": True,
                "message": "A/B test started successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to start test")

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start A/B test: {str(e)}")


@router.post("/ab-tests/{test_id}/stop")
async def stop_ab_test(test_id: str):
    """停止A/B测试"""
    try:
        manager = await ab_test_manager
        success = await manager.stop_test(test_id)

        if success:
            return {
                "success": True,
                "message": "A/B test stopped successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to stop test")

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop A/B test: {str(e)}")


@router.get("/ab-tests/{test_id}/results")
async def get_ab_test_results(test_id: str):
    """获取A/B测试结果"""
    try:
        manager = await ab_test_manager
        results = await manager.get_test_results(test_id)

        return {
            "success": True,
            "data": results
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get A/B test results: {str(e)}")


@router.delete("/ab-tests/{test_id}")
async def delete_ab_test(test_id: str):
    """删除A/B测试"""
    try:
        manager = await ab_test_manager
        success = await manager.delete_test(test_id)

        if success:
            return {
                "success": True,
                "message": "A/B test deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Test not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete A/B test: {str(e)}")


# 成本优化API
@router.get("/cost/analysis")
async def get_cost_analysis(
    period: str = Query("daily", description="分析周期"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    organization_id: Optional[str] = Query(None, description="组织ID")
):
    """获取成本分析"""
    try:
        optimizer = await cost_optimizer
        analysis = optimizer.cost_tracker.get_cost_analysis(period, user_id, organization_id)

        return {
            "success": True,
            "data": analysis.to_dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cost analysis: {str(e)}")


@router.get("/cost/recommendations")
async def get_cost_recommendations(
    period: str = Query("weekly", description="分析周期"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    organization_id: Optional[str] = Query(None, description="组织ID")
):
    """获取成本优化建议"""
    try:
        optimizer = await cost_optimizer
        recommendations = await optimizer.get_cost_optimization_recommendations(
            user_id=user_id,
            organization_id=organization_id,
            period=period
        )

        return {
            "success": True,
            "data": recommendations
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cost recommendations: {str(e)}")


@router.post("/cost/budget-limits")
async def set_budget_limit(request: BudgetLimitRequest):
    """设置预算限制"""
    try:
        optimizer = await cost_optimizer
        limit_id = optimizer.set_budget_limit(
            name=request.name,
            amount=request.amount,
            time_period=request.time_period,
            user_id=request.user_id,
            organization_id=request.organization_id,
            model_ids=request.model_ids,
            task_types=request.task_types
        )

        return {
            "success": True,
            "data": {
                "limit_id": limit_id,
                "message": "Budget limit set successfully"
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set budget limit: {str(e)}")


@router.get("/cost/budget-alerts")
async def get_budget_alerts(
    unresolved_only: bool = Query(True, description="仅显示未解决告警")
):
    """获取预算告警"""
    try:
        optimizer = await cost_optimizer
        alerts = optimizer.cost_tracker.get_budget_alerts(unresolved_only)

        return {
            "success": True,
            "data": [alert.to_dict() for alert in alerts]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get budget alerts: {str(e)}")


@router.post("/cost/budget-alerts/{alert_id}/resolve")
async def resolve_budget_alert(alert_id: str):
    """解决预算告警"""
    try:
        optimizer = await cost_optimizer
        success = optimizer.cost_tracker.resolve_alert(alert_id)

        if success:
            return {
                "success": True,
                "message": "Budget alert resolved successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Alert not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve budget alert: {str(e)}")


@router.post("/cost/optimize-model")
async def optimize_model_cost(request: ModelSelectionRequest):
    """优化模型成本"""
    try:
        task_type = TaskType(request.task_type)
        strategy = CostOptimizationStrategy.BEST_VALUE

        optimizer = await cost_optimizer
        model_id = await optimizer.optimize_model_selection(
            task_type=task_type,
            requirements=request.requirements,
            strategy=strategy,
            budget_constraint=request.budget_constraint
        )

        if not model_id:
            return {
                "success": False,
                "message": "No suitable model found within constraints"
            }

        return {
            "success": True,
            "data": {
                "optimized_model": model_id,
                "strategy": strategy.value,
                "task_type": request.task_type,
                "budget_constraint": request.budget_constraint
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid task type: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to optimize model: {str(e)}")


# 综合仪表板API
@router.get("/dashboard/overview")
async def get_ai_dashboard_overview(
    user_id: Optional[str] = Query(None, description="用户ID"),
    organization_id: Optional[str] = Query(None, description="组织ID")
):
    """获取AI功能仪表板概览"""
    try:
        manager = await model_manager
        optimizer = await cost_optimizer

        # 模型统计
        all_models = manager.get_all_models()
        active_models = manager.get_active_models()

        # 成本统计
        cost_analysis = optimizer.cost_tracker.get_cost_analysis("daily", user_id, organization_id)

        # 预算告警
        budget_alerts = optimizer.cost_tracker.get_budget_alerts(True)

        # A/B测试统计
        ab_manager = await ab_test_manager
        all_tests = await ab_manager.get_all_tests()
        running_tests = await ab_manager.get_all_tests(TestStatus.RUNNING)

        overview = {
            "models": {
                "total": len(all_models),
                "active": len(active_models),
                "by_provider": {
                    provider.value: len([m for m in all_models if m.provider == provider])
                    for provider in set(m.provider for m in all_models)
                }
            },
            "costs": {
                "today_total": cost_analysis.total_cost,
                "today_requests": cost_analysis.total_requests,
                "avg_cost_per_request": cost_analysis.avg_cost_per_request,
                "cost_trend": cost_analysis.cost_trend[-7:] if cost_analysis.cost_trend else []
            },
            "budgets": {
                "active_alerts": len(budget_alerts),
                "critical_alerts": len([a for a in budget_alerts if a.alert_type == BudgetAlertType.CRITICAL]),
                "exceeded_alerts": len([a for a in budget_alerts if a.alert_type == BudgetAlertType.EXCEEDED])
            },
            "ab_tests": {
                "total": len(all_tests),
                "running": len(running_tests),
                "completed": len([t for t in all_tests if t.get('status') == 'completed'])
            },
            "recommendations": cost_analysis.recommendations[:5],  # 前5个建议
            "last_updated": datetime.utcnow().isoformat()
        }

        return {
            "success": True,
            "data": overview
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard overview: {str(e)}")


@router.get("/health")
async def get_ai_systems_health():
    """获取AI系统健康状态"""
    try:
        health_status = {
            "model_manager": "healthy",
            "content_enhancer": "healthy",
            "ab_testing": "healthy",
            "cost_optimizer": "healthy",
            "cache_system": "healthy",
            "issues": [],
            "last_check": datetime.utcnow().isoformat()
        }

        # 检查各系统状态
        try:
            manager = await model_manager
            health_results = await manager.health_check_models()
            unhealthy_models = [model_id for model_id, healthy in health_results.items() if not healthy]
            if unhealthy_models:
                health_status["issues"].append(f"Unhealthy models: {unhealthy_models}")
                health_status["model_manager"] = "degraded"
        except Exception as e:
            health_status["model_manager"] = "error"
            health_status["issues"].append(f"Model manager error: {str(e)}")

        try:
            optimizer = await cost_optimizer
            # 简单的健康检查
            if not optimizer.cost_tracker.cost_records:
                health_status["cost_optimizer"] = "warning"
                health_status["issues"].append("No cost records found")
        except Exception as e:
            health_status["cost_optimizer"] = "error"
            health_status["issues"].append(f"Cost optimizer error: {str(e)}")

        # 检查缓存系统
        try:
            from backend.core.cache.smart_cache import get_smart_cache
            cache = await get_smart_cache()
            stats = await cache.get_stats()
            if stats["global"]["hit_rate"] < 50:
                health_status["cache_system"] = "warning"
                health_status["issues"].append("Low cache hit rate")
        except Exception as e:
            health_status["cache_system"] = "error"
            health_status["issues"].append(f"Cache system error: {str(e)}")

        return {
            "success": True,
            "data": health_status
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health status: {str(e)}")