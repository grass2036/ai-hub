"""
AI模型管理API
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from backend.core.ai_service import ai_manager
from backend.core.cache_service import cache_result

router = APIRouter()


class ModelInfo(BaseModel):
    """模型信息模型"""
    id: str = Field(..., description="模型ID")
    name: str = Field(..., description="模型名称")
    description: Optional[str] = Field(default=None, description="模型描述")
    context_length: Optional[int] = Field(default=None, description="上下文长度")
    pricing: Optional[Dict[str, float]] = Field(default=None, description="定价信息")
    capabilities: Optional[List[str]] = Field(default=None, description="模型能力")


class ModelsListResponse(BaseModel):
    """模型列表响应"""
    service: str = Field(..., description="AI服务名称")
    models: List[ModelInfo] = Field(..., description="模型列表")
    total_count: int = Field(..., description="模型总数")
    popular_models: List[str] = Field(..., description="热门模型")


class ServiceModelsResponse(BaseModel):
    """服务模型响应"""
    service: str = Field(..., description="服务名称")
    available: bool = Field(..., description="服务是否可用")
    models: Optional[List[ModelInfo]] = Field(default=None, description="模型列表")
    error: Optional[str] = Field(default=None, description="错误信息")


@router.get("/models", response_model=List[ServiceModelsResponse])
@cache_result(ttl=300, key_prefix="models_list")  # 缓存5分钟
async def get_available_models():
    """
    获取所有AI服务的可用模型
    """
    try:
        services = await ai_manager.list_available_services()
        results = []

        for service_name in services["services"]:
            try:
                models_data = await ai_manager.get_models(service_name)

                models = []
                for model in models_data.get("models", []):
                    models.append(ModelInfo(**model))

                results.append(ServiceModelsResponse(
                    service=service_name,
                    available=True,
                    models=models,
                    total_count=len(models)
                ))

            except Exception as e:
                results.append(ServiceModelsResponse(
                    service=service_name,
                    available=False,
                    error=str(e)
                ))

        return results

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取模型列表失败: {str(e)}"
        )


@router.get("/models/{service}", response_model=ModelsListResponse)
@cache_result(ttl=600, key_prefix="service_models")  # 缓存10分钟
async def get_service_models(service: str):
    """
    获取指定AI服务的模型列表
    """
    try:
        models_data = await ai_manager.get_models(service)

        models = []
        for model in models_data.get("models", []):
            models.append(ModelInfo(**model))

        return ModelsListResponse(
            service=service,
            models=models,
            total_count=len(models),
            popular_models=models_data.get("popular_models", [])
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取 {service} 模型失败: {str(e)}"
        )


@router.get("/models/{service}/{model_id}")
async def get_model_details(service: str, model_id: str):
    """
    获取指定模型的详细信息
    """
    try:
        models_data = await ai_manager.get_models(service)

        # 查找指定模型
        model_info = None
        for model in models_data.get("models", []):
            if model.get("id") == model_id:
                model_info = model
                break

        if not model_info:
            raise HTTPException(
                status_code=404,
                detail=f"模型 {model_id} 在服务 {service} 中未找到"
            )

        return {
            "service": service,
            "model": model_info,
            "usage_example": {
                "endpoint": f"/api/v1/chat/completions",
                "parameters": {
                    "model": model_id,
                    "messages": [{"role": "user", "content": "Hello!"}]
                }
            }
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取模型详情失败: {str(e)}"
        )


@router.get("/models/popular")
@cache_result(ttl=1800, key_prefix="popular_models")  # 缓存30分钟
async def get_popular_models():
    """
    获取热门模型推荐
    """
    try:
        popular_models = {
            "openrouter": [
                {
                    "id": "anthropic/claude-3.5-sonnet",
                    "name": "Claude 3.5 Sonnet",
                    "description": "最新的Claude模型，性能优异",
                    "use_case": "通用对话、编程、写作"
                },
                {
                    "id": "openai/gpt-4o",
                    "name": "GPT-4o",
                    "description": "OpenAI最新模型，多模态能力强",
                    "use_case": "图像理解、复杂推理"
                },
                {
                    "id": "google/gemini-pro-1.5",
                    "name": "Gemini Pro 1.5",
                    "description": "Google最新模型，长文本处理优秀",
                    "use_case": "长文档分析、代码生成"
                },
                {
                    "id": "meta-llama/llama-3.1-70b-instruct",
                    "name": "Llama 3.1 70B",
                    "description": "开源模型，性价比高",
                    "use_case": "预算有限的通用任务"
                },
                {
                    "id": "microsoft/wizardlm-2-8x22b",
                    "name": "WizardLM-2 8x22B",
                    "description": "免费模型，适合测试",
                    "use_case": "开发测试、简单任务"
                }
            ],
            "gemini": [
                {
                    "id": "gemini-2.5-flash",
                    "name": "Gemini 2.5 Flash",
                    "description": "快速响应的通用模型",
                    "use_case": "实时对话、快速响应"
                },
                {
                    "id": "gemini-2.5-pro",
                    "name": "Gemini 2.5 Pro",
                    "description": "高性能专业模型",
                    "use_case": "复杂推理、专业任务"
                }
            ]
        }

        return {
            "popular_models": popular_models,
            "recommendations": {
                "best_overall": "anthropic/claude-3.5-sonnet",
                "fastest": "gemini-2.5-flash",
                "free_option": "microsoft/wizardlm-2-8x22b",
                "cost_effective": "meta-llama/llama-3.1-70b-instruct"
            },
            "usage_tips": [
                "💡 Claude 3.5 Sonnet：最适合复杂对话和编程任务",
                "💡 GPT-4o：最佳多模态能力，支持图像理解",
                "💡 Gemini 2.5 Flash：响应速度最快，适合实时应用",
                "💡 Llama 3.1：开源选择，数据隐私友好",
                "💡 WizardLM-2：免费选项，适合开发和测试"
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取热门模型失败: {str(e)}"
        )


@router.get("/models/recommendations")
async def get_model_recommendations(
    task_type: str = Query(..., description="任务类型: chat, coding, writing, analysis, image"),
    budget: str = Query(default="balanced", description="预算级别: free, low, balanced, high")
):
    """
    根据任务类型和预算获取模型推荐
    """
    try:
        recommendations = {
            "chat": {
                "free": ["microsoft/wizardlm-2-8x22b"],
                "low": ["meta-llama/llama-3.1-70b-instruct", "google/gemini-pro-1.5"],
                "balanced": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o-mini"],
                "high": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"]
            },
            "coding": {
                "free": ["microsoft/wizardlm-2-8x22b"],
                "low": ["meta-llama/llama-3.1-70b-instruct"],
                "balanced": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"],
                "high": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"]
            },
            "writing": {
                "free": ["microsoft/wizardlm-2-8x22b"],
                "low": ["meta-llama/llama-3.1-70b-instruct"],
                "balanced": ["anthropic/claude-3.5-sonnet", "google/gemini-pro-1.5"],
                "high": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"]
            },
            "analysis": {
                "free": ["microsoft/wizardlm-2-8x22b"],
                "low": ["google/gemini-pro-1.5"],
                "balanced": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"],
                "high": ["anthropic/claude-3.5-sonnet", "openai/gpt-4o"]
            },
            "image": {
                "free": [],
                "low": ["openai/gpt-4o-mini"],
                "balanced": ["openai/gpt-4o"],
                "high": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet"]
            }
        }

        task_recommendations = recommendations.get(task_type, {})
        budget_recommendations = task_recommendations.get(budget, [])

        return {
            "task_type": task_type,
            "budget": budget,
            "recommended_models": budget_recommendations,
            "alternative_budgets": {
                b: task_recommendations.get(b, [])
                for b in ["free", "low", "balanced", "high"]
                if b != budget and task_recommendations.get(b)
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取模型推荐失败: {str(e)}"
        )