"""
使用统计API
"""
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.core.database import get_db
from backend.models.user import User
from backend.core.quota_manager import quota_manager
from backend.api.v1.auth.auth import get_current_active_user

router = APIRouter(prefix="/usage", tags=["Usage"])


# ============ Pydantic模型 ============

class UsageStats(BaseModel):
    """使用统计"""
    quota_used: int
    quota_total: int
    quota_remaining: int
    quota_percentage: float
    quota_reset_at: str
    days_until_reset: int
    plan: str


class DailyUsage(BaseModel):
    """每日使用统计"""
    date: str
    requests: int
    cost: float


class UsageHistory(BaseModel):
    """使用历史"""
    daily_usage: List[DailyUsage]
    total_requests: int
    total_cost: float
    period_start: str
    period_end: str


# ============ API端点 ============

@router.get("/current", response_model=UsageStats)
async def get_current_usage(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前使用统计

    - 需要认证
    - 返回当前配额使用情况
    - 实时数据（来自Redis）
    """
    stats = await quota_manager.get_usage_stats(db, current_user.id)

    if not stats:
        raise HTTPException(
            status_code=404,
            detail="Usage statistics not found"
        )

    return UsageStats(**stats)


@router.get("/history", response_model=UsageHistory)
async def get_usage_history(
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取使用历史

    - 需要认证
    - 返回过去N天的使用统计
    - 参数: days (默认30天)
    """
    # TODO: 实现从usage_records表查询历史数据
    # 这里先返回模拟数据

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # 模拟数据
    daily_usage = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        daily_usage.append(
            DailyUsage(
                date=date.strftime("%Y-%m-%d"),
                requests=0,
                cost=0.0
            )
        )

    return UsageHistory(
        daily_usage=daily_usage,
        total_requests=0,
        total_cost=0.0,
        period_start=start_date.isoformat(),
        period_end=end_date.isoformat()
    )


@router.post("/reset-demo")
async def reset_demo_quota(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    重置演示配额

    - 需要认证
    - 仅用于开发/演示
    - 生产环境应删除此端点
    """
    await quota_manager.reset_monthly_quota(db, current_user.id)

    return {
        "message": "Demo quota reset successfully",
        "quota_used": 0,
        "quota_total": current_user.monthly_quota
    }