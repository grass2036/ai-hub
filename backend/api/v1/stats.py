"""
Usage Statistics API Routes
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import date
from backend.core.ai_service import ai_manager

router = APIRouter()


class UsageStatsResponse(BaseModel):
    """使用统计响应模型"""
    total_cost: float = Field(..., description="总成本 (USD)")
    total_tokens: int = Field(..., description="总Token数")
    total_requests: int = Field(..., description="总请求数")
    period_days: int = Field(..., description="统计天数")
    daily_breakdown: List[Dict[str, Any]] = Field(..., description="每日明细")


class DailyStatsResponse(BaseModel):
    """每日统计响应模型"""
    date: str = Field(..., description="日期")
    total_requests: int = Field(..., description="请求数")
    total_tokens: int = Field(..., description="Token数")
    total_cost: float = Field(..., description="成本")
    services: Dict[str, Dict[str, Any]] = Field(..., description="服务统计")
    models: Dict[str, Dict[str, Any]] = Field(..., description="模型统计")


@router.get("/usage", response_model=UsageStatsResponse)
async def get_usage_stats(
    days: int = Query(default=7, ge=1, le=365, description="统计天数")
):
    """
    获取使用统计信息
    """
    try:
        stats = await ai_manager.cost_tracker.get_cost_summary(days=days)
        return UsageStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/daily", response_model=DailyStatsResponse)
async def get_daily_stats(
    target_date: Optional[str] = Query(default=None, description="目标日期 (YYYY-MM-DD)")
):
    """
    获取特定日期的统计信息
    """
    try:
        stats = await ai_manager.cost_tracker.get_daily_stats(target_date)
        
        if not stats:
            # 返回空统计
            if target_date is None:
                target_date = date.today().isoformat()
            return DailyStatsResponse(
                date=target_date,
                total_requests=0,
                total_tokens=0,
                total_cost=0.0,
                services={},
                models={}
            )
        
        return DailyStatsResponse(
            date=target_date or date.today().isoformat(),
            total_requests=stats.get("total_requests", 0),
            total_tokens=stats.get("total_tokens", 0),
            total_cost=stats.get("total_cost", 0.0),
            services=stats.get("services", {}),
            models=stats.get("models", {})
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取每日统计失败: {str(e)}")


@router.get("/recent")
async def get_recent_usage(
    limit: int = Query(default=20, ge=1, le=100, description="返回记录数")
):
    """
    获取最近的使用记录
    """
    try:
        records = await ai_manager.cost_tracker.get_recent_usage(limit=limit)
        return {
            "records": records,
            "count": len(records)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取使用记录失败: {str(e)}")


@router.get("/summary")
async def get_summary_stats():
    """
    获取汇总统计信息
    """
    try:
        # 获取不同时间段的统计
        today_stats = await ai_manager.cost_tracker.get_daily_stats()
        week_stats = await ai_manager.cost_tracker.get_cost_summary(days=7)
        month_stats = await ai_manager.cost_tracker.get_cost_summary(days=30)
        
        return {
            "today": {
                "cost": today_stats.get("total_cost", 0.0),
                "tokens": today_stats.get("total_tokens", 0),
                "requests": today_stats.get("total_requests", 0)
            },
            "this_week": {
                "cost": week_stats.get("total_cost", 0.0),
                "tokens": week_stats.get("total_tokens", 0),
                "requests": week_stats.get("total_requests", 0)
            },
            "this_month": {
                "cost": month_stats.get("total_cost", 0.0),
                "tokens": month_stats.get("total_tokens", 0),
                "requests": month_stats.get("total_requests", 0)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取汇总统计失败: {str(e)}")


@router.get("/models")
async def get_model_usage_stats(
    days: int = Query(default=7, ge=1, le=365, description="统计天数")
):
    """
    获取模型使用统计
    """
    try:
        stats = await ai_manager.cost_tracker.get_cost_summary(days=days)
        
        # 聚合所有天的模型统计
        model_stats = {}
        for day_data in stats.get("daily_breakdown", []):
            date_str = day_data["date"]
            if date_str in await _get_all_daily_data():
                daily_data = await ai_manager.cost_tracker.get_daily_stats(date_str)
                models = daily_data.get("models", {})
                
                for model, data in models.items():
                    if model not in model_stats:
                        model_stats[model] = {
                            "requests": 0,
                            "tokens": 0,
                            "cost": 0.0
                        }
                    model_stats[model]["requests"] += data.get("requests", 0)
                    model_stats[model]["tokens"] += data.get("tokens", 0)
                    model_stats[model]["cost"] += data.get("cost", 0.0)
        
        # 按成本排序
        sorted_models = sorted(
            model_stats.items(),
            key=lambda x: x[1]["cost"],
            reverse=True
        )
        
        return {
            "period_days": days,
            "models": dict(sorted_models)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型统计失败: {str(e)}")


async def _get_all_daily_data():
    """获取所有日期的数据（辅助函数）"""
    try:
        import json
        from pathlib import Path
        
        daily_stats_file = Path("data/daily_stats.json")
        if daily_stats_file.exists():
            with open(daily_stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
    except Exception:
        pass
    return {}


@router.delete("/reset")
async def reset_usage_stats():
    """
    重置使用统计（仅开发环境）
    """
    try:
        from pathlib import Path
        
        # 删除统计文件
        data_dir = Path("data")
        usage_file = data_dir / "usage_stats.json"
        daily_file = data_dir / "daily_stats.json"
        
        if usage_file.exists():
            usage_file.unlink()
        if daily_file.exists():
            daily_file.unlink()
            
        return {"message": "统计数据已重置"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置统计失败: {str(e)}")