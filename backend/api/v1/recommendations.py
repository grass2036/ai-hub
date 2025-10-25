"""
推荐系统API接口
Week 7 Day 2: 用户体验优化

提供个性化推荐API：
- 用户行为追踪
- 智能推荐获取
- 推荐结果反馈
- 推荐统计分析
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from backend.core.recommendation_engine import (
    recommendation_engine,
    UserBehavior,
    RecommendationType,
    ItemType
)
from backend.core.logging_service import logging_service

router = APIRouter()
logger = logging.getLogger(__name__)


# 请求模型
class UserBehaviorRequest(BaseModel):
    """用户行为请求"""
    user_id: str = Field(..., description="用户ID")
    item_id: str = Field(..., description="项目ID")
    item_type: ItemType = Field(..., description="项目类型")
    action: str = Field(..., description="行为类型")
    rating: Optional[float] = Field(None, ge=0, le=5, description="评分(0-5)")
    duration: Optional[int] = Field(None, ge=0, description="使用时长(秒)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外元数据")


class RecommendationRequest(BaseModel):
    """推荐请求"""
    user_id: str = Field(..., description="用户ID")
    rec_type: RecommendationType = Field(RecommendationType.HYBRID, description="推荐类型")
    n: int = Field(10, ge=1, le=50, description="推荐数量")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="过滤条件")


class FeedbackRequest(BaseModel):
    """推荐反馈请求"""
    user_id: str = Field(..., description="用户ID")
    item_id: str = Field(..., description="项目ID")
    recommendation_id: Optional[str] = Field(None, description="推荐ID")
    feedback_type: str = Field(..., description="反馈类型(click, use, like, dislike, ignore)")
    rating: Optional[float] = Field(None, ge=0, le=5, description="评分")
    comment: Optional[str] = Field(None, description="评论")


# 响应模型
class RecommendationResponse(BaseModel):
    """推荐响应"""
    item_id: str
    item_type: str
    score: float
    reason: str
    confidence: float
    metadata: Dict[str, Any]
    item_details: Optional[Dict[str, Any]] = None


class RecommendationListResponse(BaseModel):
    """推荐列表响应"""
    recommendations: List[RecommendationResponse]
    user_id: str
    rec_type: str
    total_count: int
    generated_at: datetime
    metadata: Dict[str, Any]


class StatisticsResponse(BaseModel):
    """统计响应"""
    total_users: int
    total_items: int
    total_behaviors: int
    popular_items: List[Dict[str, Any]]
    user_activity_summary: Dict[str, Any]


@router.post("/behavior", summary="记录用户行为")
async def record_user_behavior(
    request: UserBehaviorRequest,
    background_tasks: BackgroundTasks
):
    """
    记录用户行为数据，用于推荐算法训练

    - **user_id**: 用户唯一标识
    - **item_id**: 交互项目ID
    - **item_type**: 项目类型(ai_model, api_endpoint, workflow等)
    - **action**: 行为类型(view, use, like, share, save)
    - **rating**: 评分(0-5分)
    - **duration**: 使用时长
    """
    try:
        # 创建用户行为对象
        behavior = UserBehavior(
            user_id=request.user_id,
            item_id=request.item_id,
            item_type=request.item_type,
            action=request.action,
            rating=request.rating,
            duration=request.duration,
            timestamp=datetime.now()
        )

        # 异步保存行为数据
        background_tasks.add_task(recommendation_engine.add_user_behavior, behavior)

        # 记录日志
        await logging_service.log_user_behavior(
            user_id=request.user_id,
            action=f"recommendation_behavior_{request.action}",
            resource_type=request.item_type.value,
            details={
                "item_id": request.item_id,
                "rating": request.rating,
                "duration": request.duration,
                "metadata": request.metadata
            }
        )

        return {
            "success": True,
            "message": "用户行为记录成功",
            "timestamp": datetime.now()
        }

    except Exception as e:
        logger.error(f"Failed to record user behavior: {e}")
        raise HTTPException(status_code=500, detail="记录用户行为失败")


@router.post("/recommendations", response_model=RecommendationListResponse, summary="获取个性化推荐")
async def get_recommendations(request: RecommendationRequest):
    """
    获取个性化推荐内容

    - **rec_type**: 推荐类型
      - collaborative: 协同过滤推荐
      - content_based: 基于内容推荐
      - context_aware: 上下文感知推荐
      - hybrid: 混合推荐(推荐)
      - popular: 热门推荐
    - **context**: 上下文信息(时间、设备、地点等)
    - **filters**: 过滤条件(类别、标签等)
    """
    try:
        # 获取推荐
        recommendations = await recommendation_engine.get_recommendations(
            user_id=request.user_id,
            rec_type=request.rec_type,
            context=request.context,
            n=request.n
        )

        # 应用过滤条件
        if request.filters:
            recommendations = _apply_filters(recommendations, request.filters)

        # 获取项目详细信息
        rec_responses = []
        for rec in recommendations:
            item_details = None
            if rec.item_id in recommendation_engine.items:
                item = recommendation_engine.items[rec.item_id]
                item_details = {
                    "title": item.title,
                    "description": item.description,
                    "category": item.category,
                    "tags": item.tags,
                    "popularity_score": item.popularity_score,
                    "rating_avg": item.rating_avg,
                    "rating_count": item.rating_count
                }

            rec_responses.append(RecommendationResponse(
                item_id=rec.item_id,
                item_type=rec.item_type.value,
                score=rec.score,
                reason=rec.reason,
                confidence=rec.confidence,
                metadata=rec.metadata,
                item_details=item_details
            ))

        # 记录推荐日志
        await logging_service.log_user_behavior(
            user_id=request.user_id,
            action="recommendation_generated",
            resource_type="recommendation",
            details={
                "rec_type": request.rec_type.value,
                "context": request.context,
                "count": len(rec_responses)
            }
        )

        return RecommendationListResponse(
            recommendations=rec_responses,
            user_id=request.user_id,
            rec_type=request.rec_type.value,
            total_count=len(rec_responses),
            generated_at=datetime.now(),
            metadata={
                "context": request.context,
                "filters": request.filters
            }
        )

    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail="获取推荐失败")


@router.post("/feedback", summary="推荐反馈")
async def recommendation_feedback(request: FeedbackRequest):
    """
    提供推荐结果反馈，用于优化推荐算法

    - **feedback_type**: 反馈类型
      - click: 点击推荐
      - use: 使用推荐项目
      - like: 喜欢推荐
      - dislike: 不喜欢推荐
      - ignore: 忽略推荐
    """
    try:
        # 将反馈转换为用户行为
        action_mapping = {
            "click": "view",
            "use": "use",
            "like": "like",
            "dislike": "dislike",
            "ignore": "view"
        }

        action = action_mapping.get(request.feedback_type, "view")
        rating = request.rating

        # 根据反馈类型设置评分
        if request.feedback_type == "like":
            rating = rating or 5.0
        elif request.feedback_type == "dislike":
            rating = rating or 1.0
        elif request.feedback_type == "use":
            rating = rating or 4.0

        # 创建反馈行为
        behavior = UserBehavior(
            user_id=request.user_id,
            item_id=request.item_id,
            item_type=ItemType.AI_MODEL,  # 默认类型，实际应该查询
            action=action,
            rating=rating,
            timestamp=datetime.now()
        )

        # 保存反馈
        await recommendation_engine.add_user_behavior(behavior)

        # 记录反馈日志
        await logging_service.log_user_behavior(
            user_id=request.user_id,
            action="recommendation_feedback",
            resource_type="recommendation",
            details={
                "item_id": request.item_id,
                "feedback_type": request.feedback_type,
                "rating": rating,
                "comment": request.comment
            }
        )

        return {
            "success": True,
            "message": "反馈记录成功",
            "timestamp": datetime.now()
        }

    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(status_code=500, detail="记录反馈失败")


@router.get("/popular", summary="获取热门推荐")
async def get_popular_items(
    n: int = 10,
    category: Optional[str] = None,
    item_type: Optional[ItemType] = None
):
    """
    获取热门项目推荐
    """
    try:
        recommendations = await recommendation_engine.popular_items_recommend(n)

        # 应用过滤条件
        if category or item_type:
            filtered_recs = []
            for rec in recommendations:
                if rec.item_id in recommendation_engine.items:
                    item = recommendation_engine.items[rec.item_id]
                    if category and item.category != category:
                        continue
                    if item_type and item.item_type != item_type:
                        continue
                    filtered_recs.append(rec)
            recommendations = filtered_recs

        return {
            "popular_items": [
                {
                    "item_id": rec.item_id,
                    "item_type": rec.item_type.value,
                    "score": rec.score,
                    "reason": rec.reason,
                    "item_details": {
                        "title": recommendation_engine.items[rec.item_id].title,
                        "category": recommendation_engine.items[rec.item_id].category,
                        "usage_count": recommendation_engine.items[rec.item_id].usage_count,
                        "rating_avg": recommendation_engine.items[rec.item_id].rating_avg
                    } if rec.item_id in recommendation_engine.items else None
                }
                for rec in recommendations
            ],
            "category": category,
            "item_type": item_type,
            "count": len(recommendations)
        }

    except Exception as e:
        logger.error(f"Failed to get popular items: {e}")
        raise HTTPException(status_code=500, detail="获取热门推荐失败")


@router.get("/statistics", response_model=StatisticsResponse, summary="获取推荐系统统计")
async def get_recommendation_statistics():
    """
    获取推荐系统统计信息
    """
    try:
        total_users = len(recommendation_engine.user_behaviors)
        total_items = len(recommendation_engine.items)

        total_behaviors = 0
        for behaviors in recommendation_engine.user_behaviors.values():
            total_behaviors += len(behaviors)

        # 获取热门项目
        popular_items = []
        for item_id, item in list(recommendation_engine.items.items())[:10]:
            popular_items.append({
                "item_id": item_id,
                "title": item.title,
                "category": item.category,
                "usage_count": item.usage_count,
                "rating_avg": item.rating_avg,
                "rating_count": item.rating_count
            })

        # 用户活动摘要
        user_activity_summary = {}
        if recommendation_engine.user_behaviors:
            behaviors_per_user = [len(behaviors) for behaviors in recommendation_engine.user_behaviors.values()]
            user_activity_summary = {
                "avg_behaviors_per_user": sum(behaviors_per_user) / len(behaviors_per_user),
                "max_behaviors_per_user": max(behaviors_per_user),
                "min_behaviors_per_user": min(behaviors_per_user),
                "total_active_users": len([b for b in behaviors_per_user if b > 0])
            }

        return StatisticsResponse(
            total_users=total_users,
            total_items=total_items,
            total_behaviors=total_behaviors,
            popular_items=popular_items,
            user_activity_summary=user_activity_summary
        )

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")


@router.delete("/cache", summary="清除推荐缓存")
async def clear_recommendation_cache(user_id: Optional[str] = None):
    """
    清除推荐缓存
    """
    try:
        if user_id:
            # 清除特定用户的缓存
            cache_keys_to_remove = [key for key in recommendation_engine.recommendation_cache.keys() if key.startswith(f"{user_id}_")]
            for key in cache_keys_to_remove:
                del recommendation_engine.recommendation_cache[key]
        else:
            # 清除所有缓存
            recommendation_engine.recommendation_cache.clear()
            recommendation_engine.similarity_cache.clear()

        return {
            "success": True,
            "message": f"推荐缓存已清除",
            "cleared_user": user_id,
            "timestamp": datetime.now()
        }

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail="清除缓存失败")


def _apply_filters(recommendations: List, filters: Dict[str, Any]) -> List:
    """应用过滤条件"""
    if not filters:
        return recommendations

    filtered_recs = []
    for rec in recommendations:
        if rec.item_id not in recommendation_engine.items:
            continue

        item = recommendation_engine.items[rec.item_id]

        # 类别过滤
        if "category" in filters and item.category != filters["category"]:
            continue

        # 标签过滤
        if "tags" in filters:
            required_tags = set(filters["tags"])
            item_tags = set(item.tags)
            if not required_tags.issubset(item_tags):
                continue

        # 项目类型过滤
        if "item_type" in filters and item.item_type != filters["item_type"]:
            continue

        # 最小评分过滤
        if "min_rating" in filters and item.rating_avg < filters["min_rating"]:
            continue

        # 最小使用次数过滤
        if "min_usage" in filters and item.usage_count < filters["min_usage"]:
            continue

        filtered_recs.append(rec)

    return filtered_recs