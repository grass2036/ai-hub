"""
分析API端点
Week 5 Day 3: 智能数据分析平台 - 分析API
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.user import User
from backend.models.analytics import (
    UserBehavior, UserSession, AnalyticsMetric,
    UserBehaviorCreate, UserBehaviorResponse,
    UserSessionResponse, AnalyticsQuery, AnalyticsResponse,
    FunnelAnalysis, FunnelResponse
)
from backend.analytics.behavior_tracker import get_behavior_tracker, track_user_event

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.post("/events/track", response_model=UserBehaviorResponse)
async def track_event(
    event_data: UserBehaviorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """跟踪用户事件"""
    try:
        # 使用行为跟踪器
        behavior = track_user_event(event_data.dict(), db)
        return UserBehaviorResponse.from_orm(behavior)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"事件跟踪失败: {str(e)}"
        )

@router.post("/events/batch", response_model=List[UserBehaviorResponse])
async def track_events_batch(
    events_data: List[UserBehaviorCreate],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量跟踪用户事件"""
    try:
        results = []
        for event_data in events_data:
            behavior = track_user_event(event_data.dict(), db)
            results.append(UserBehaviorResponse.from_orm(behavior))
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"批量事件跟踪失败: {str(e)}"
        )

@router.get("/events", response_model=List[UserBehaviorResponse])
async def get_user_events(
    limit: int = Query(100, ge=1, le=1000),
    event_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户事件列表"""
    try:
        query = db.query(UserBehavior).filter(UserBehavior.user_id == current_user.id)

        # 添加过滤条件
        if event_type:
            query = query.filter(UserBehavior.event_type == event_type)
        if start_date:
            query = query.filter(UserBehavior.created_at >= start_date)
        if end_date:
            query = query.filter(UserBehavior.created_at <= end_date)

        events = query.order_by(UserBehavior.created_at.desc()).limit(limit).all()
        return [UserBehaviorResponse.from_orm(event) for event in events]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取事件列表失败: {str(e)}"
        )

@router.get("/sessions", response_model=List[UserSessionResponse])
async def get_user_sessions(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户会话列表"""
    try:
        sessions = db.query(UserSession).filter(
            UserSession.user_id == current_user.id
        ).order_by(UserSession.start_time.desc()).limit(limit).all()
        return [UserSessionResponse.from_orm(session) for session in sessions]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取会话列表失败: {str(e)}"
        )

@router.get("/sessions/{session_id}", response_model=UserSessionResponse)
async def get_session_details(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取会话详情"""
    try:
        session = db.query(UserSession).filter(
            and_(
                UserSession.session_id == session_id,
                UserSession.user_id == current_user.id
            )
        ).first()

        if not session:
            raise HTTPException(
                status_code=404,
                detail="会话不存在"
            )

        return UserSessionResponse.from_orm(session)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取会话详情失败: {str(e)}"
        )

@router.get("/dashboard/overview", response_model=Dict[str, Any])
async def get_dashboard_overview(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取仪表板概览"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)

        # 获取行为跟踪器的统计信息
        tracker = get_behavior_tracker()
        behavior_stats = tracker.get_event_statistics(hours=days * 24)

        # 从数据库获取更详细的信息
        user_events = db.query(UserBehavior).filter(
            and_(
                UserBehavior.user_id == current_user.id,
                UserBehavior.created_at >= cutoff_date
            )
        ).all()

        user_sessions = db.query(UserSession).filter(
            and_(
                UserSession.user_id == current_user.id,
                UserSession.start_time >= cutoff_date
            )
        ).all()

        # 计算统计数据
        total_events = len(user_events)
        total_sessions = len(user_sessions)
        total_page_views = len([e for e in user_events if e.event_type == "page_view"])
        total_api_calls = len([e for e in user_events if e.event_type == "api_call"])
        total_errors = len([e for e in user_events if e.event_type == "error_occurred"])

        # 计算平均会话时长
        session_durations = [s.duration_seconds for s in user_sessions if s.duration_seconds]
        avg_session_duration = sum(session_durations) / len(session_durations) if session_durations else 0

        # 转化事件统计
        conversion_events = len([s for s in user_sessions if s.conversion_events > 0])
        conversion_rate = (conversion_events / total_sessions * 100) if total_sessions > 0 else 0

        return {
            "period_days": days,
            "summary": {
                "total_events": total_events,
                "total_sessions": total_sessions,
                "total_page_views": total_page_views,
                "total_api_calls": total_api_calls,
                "total_errors": total_errors,
                "avg_session_duration": round(avg_session_duration, 2),
                "conversion_rate": round(conversion_rate, 2)
            },
            "behavior_stats": behavior_stats,
            "top_pages": _get_top_pages(user_events, limit=10),
            "event_types": _get_event_type_distribution(user_events),
            "daily_activity": _get_daily_activity(user_events, days)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取仪表板概览失败: {str(e)}"
        )

@router.get("/metrics/query", response_model=AnalyticsResponse)
async def query_metrics(
    query: AnalyticsQuery,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """查询分析指标"""
    try:
        # 查询指标数据
        metrics_query = db.query(AnalyticsMetric).filter(
            and_(
                AnalyticsMetric.metric_name == query.metric_name,
                AnalyticsMetric.metric_date >= query.start_date,
                AnalyticsMetric.metric_date <= query.end_date,
                AnalyticsMetric.period == query.period
            )
        )

        # 应用过滤条件
        if query.filters:
            for key, value in query.filters.items():
                metrics_query = metrics_query.filter(
                    AnalyticsMetric.dimensions[key].astext == str(value)
                )

        metrics = metrics_query.order_by(AnalyticsMetric.metric_date).all()

        # 格式化响应数据
        data = []
        total_value = 0
        for metric in metrics:
            data.append({
                "date": metric.metric_date.isoformat(),
                "value": metric.value,
                "dimensions": metric.dimensions or {},
                "sample_count": metric.sample_count
            })
            total_value += metric.value

        return AnalyticsResponse(
            metric_name=query.metric_name,
            period=query.period,
            data=data,
            total_count=len(metrics),
            aggregated_value=total_value if data else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"查询指标失败: {str(e)}"
        )

@router.post("/funnel/analyze", response_model=FunnelResponse)
async def analyze_funnel(
    funnel_data: FunnelAnalysis,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """分析用户转化漏斗"""
    try:
        # 获取漏斗数据
        funnel_steps = []
        total_users = 0

        for i, step in enumerate(funnel_data.steps):
            # 查询完成该步骤的用户数
            step_users = db.query(func.count(func.distinct(UserBehavior.user_id))).filter(
                and_(
                    UserBehavior.event_type == "user_action",
                    UserBehavior.properties.contains({"action": step}),
                    UserBehavior.created_at >= funnel_data.start_date,
                    UserBehavior.created_at <= funnel_data.end_date
                )
            ).scalar()

            if i == 0:
                total_users = step_users

            conversion_rate = (step_users / total_users * 100) if total_users > 0 else 0
            dropoff_rate = 100 - conversion_rate if i < len(funnel_data.steps) - 1 else 0

            funnel_steps.append({
                "step": step,
                "step_order": i + 1,
                "users": step_users,
                "conversion_rate": round(conversion_rate, 2),
                "dropoff_rate": round(dropoff_rate, 2)
            })

        # 计算整体转化率
        last_step_users = funnel_steps[-1]["users"] if funnel_steps else 0
        overall_conversion = (last_step_users / total_users * 100) if total_users > 0 else 0

        return FunnelResponse(
            funnel_name=funnel_data.funnel_name,
            steps=funnel_steps,
            total_users=total_users,
            conversion_rates=[step["conversion_rate"] for step in funnel_steps],
            dropoff_rates=[step["dropoff_rate"] for step in funnel_steps]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"漏斗分析失败: {str(e)}"
        )

@router.get("/realtime/stats", response_model=Dict[str, Any])
async def get_realtime_stats(
    current_user: User = Depends(get_current_user)
):
    """获取实时统计信息"""
    try:
        tracker = get_behavior_tracker()

        # 获取实时事件统计（最近5分钟）
        recent_stats = tracker.get_event_statistics(hours=0.083)  # 5分钟

        # 获取活跃会话
        active_sessions = tracker.get_active_sessions(minutes=30)

        # 获取用户当前活动
        user_events = tracker.get_user_events(current_user.id, limit=10)

        return {
            "realtime_stats": recent_stats,
            "active_sessions": len(active_sessions),
            "user_recent_activity": [
                {
                    "event_type": event.event_type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "properties": event.properties
                }
                for event in user_events[:5]
            ],
            "system_health": {
                "status": "healthy",
                "last_updated": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取实时统计失败: {str(e)}"
        )

# 辅助函数
def _get_top_pages(events: List[UserBehavior], limit: int = 10) -> List[Dict[str, Any]]:
    """获取热门页面"""
    page_counts = {}
    for event in events:
        if event.url:
            page_counts[event.url] = page_counts.get(event.url, 0) + 1

    sorted_pages = sorted(page_counts.items(), key=lambda x: x[1], reverse=True)
    return [{"page": page, "views": count} for page, count in sorted_pages[:limit]]

def _get_event_type_distribution(events: List[UserBehavior]) -> List[Dict[str, Any]]:
    """获取事件类型分布"""
    type_counts = {}
    for event in events:
        type_counts[event.event_type] = type_counts.get(event.event_type, 0) + 1

    total = sum(type_counts.values())
    return [
        {"type": event_type, "count": count, "percentage": round(count / total * 100, 2)}
        for event_type, count in type_counts.items()
    ]

def _get_daily_activity(events: List[UserBehavior], days: int) -> List[Dict[str, Any]]:
    """获取每日活动统计"""
    daily_counts = {}
    for event in events:
        date_key = event.created_at.strftime("%Y-%m-%d")
        daily_counts[date_key] = daily_counts.get(date_key, 0) + 1

    return [
        {"date": date, "events": count}
        for date, count in sorted(daily_counts.items())
    ]