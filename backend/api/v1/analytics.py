"""
企业级分析API端点
Week 9 Day 4: 企业级监控与分析 - Analytics API

提供企业级分析功能的API接口，包括：
- 商业指标分析
- 用户行为分析
- 趋势分析和预测
- 实时指标查询
- 异常检测
- 数据可视化支持
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from decimal import Decimal

from backend.core.analytics.business_analytics import business_analytics, RevenueMetrics, UserMetrics, UsageMetrics, BusinessInsights
from backend.core.analytics.user_behavior import user_behavior_analytics, UserBehaviorMetrics, UserFunnelMetrics, UserPersona, BehaviorAnomaly
from backend.core.analytics.trend_analyzer import trend_analyzer, TrendData, TrendMetrics, TrendForecast, AnomalyDetection
from backend.core.analytics.metrics_collector import metrics_collector, MetricData, MetricAggregation
from backend.core.auth.auth_middleware import get_current_user, require_permissions

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Pydantic模型定义

class DateRangeRequest(BaseModel):
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")


class RevenueMetricsResponse(BaseModel):
    total_revenue: float
    monthly_revenue: float
    daily_revenue: float
    revenue_growth_rate: float
    average_revenue_per_user: float
    revenue_by_plan: Dict[str, float]
    revenue_forecast: Dict[str, float]
    generated_at: datetime


class UserMetricsResponse(BaseModel):
    total_users: int
    active_users: int
    new_users_today: int
    new_users_this_month: int
    user_retention_rate: float
    user_growth_rate: float
    churn_rate: float
    user_ltv: float
    generated_at: datetime


class UsageMetricsResponse(BaseModel):
    total_api_calls: int
    daily_api_calls: int
    average_calls_per_user: float
    top_used_models: List[Dict[str, Any]]
    usage_growth_rate: float
    error_rate: float
    average_response_time: float
    generated_at: datetime


class BusinessInsightsResponse(BaseModel):
    key_insights: List[str]
    growth_opportunities: List[str]
    risk_factors: List[str]
    recommendations: List[str]
    generated_at: datetime


class UserBehaviorMetricsResponse(BaseModel):
    avg_session_duration: float
    bounce_rate: float
    pages_per_session: float
    return_user_rate: float
    daily_active_users: int
    weekly_active_users: int
    monthly_active_users: int
    peak_usage_hours: List[int]
    most_used_features: List[Dict[str, Any]]
    user_segments: Dict[str, int]
    generated_at: datetime


class TrendAnalysisRequest(BaseModel):
    metric_name: str = Field(..., description="指标名称")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    forecast_days: int = Field(30, description="预测天数")


class TrendAnalysisResponse(BaseModel):
    metric_name: str
    trend_metrics: Dict[str, Any]
    forecast: Dict[str, Any]
    generated_at: datetime


class MetricsQueryRequest(BaseModel):
    metric_ids: Optional[List[str]] = Field(None, description="指标ID列表")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    aggregation_period: Optional[str] = Field(None, description="聚合周期")


class DashboardSummaryResponse(BaseModel):
    revenue_metrics: RevenueMetricsResponse
    user_metrics: UserMetricsResponse
    usage_metrics: UsageMetricsResponse
    business_insights: BusinessInsightsResponse
    recent_anomalies: List[Dict[str, Any]]
    generated_at: datetime


# API端点实现

@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user: dict = Depends(get_current_user),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期")
):
    """
    获取仪表盘摘要数据

    包含收入、用户、使用量等关键指标的概览
    """
    try:
        # 设置默认时间范围
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()

        # 并行获取各类指标
        revenue_metrics_task = business_analytics.calculate_revenue_metrics(start_date, end_date)
        user_metrics_task = business_analytics.calculate_user_metrics(start_date, end_date)
        usage_metrics_task = business_analytics.calculate_usage_metrics(start_date, end_date)

        # 等待所有任务完成
        revenue_metrics, user_metrics, usage_metrics = await asyncio.gather(
            revenue_metrics_task,
            user_metrics_task,
            usage_metrics_task
        )

        # 生成商业洞察
        business_insights = await business_analytics.generate_business_insights(
            revenue_metrics, user_metrics, usage_metrics
        )

        # 获取最近的异常
        recent_anomalies = await user_behavior_analytics.detect_behavior_anomalies()

        # 转换为响应格式
        response = DashboardSummaryResponse(
            revenue_metrics=RevenueMetricsResponse(
                total_revenue=float(revenue_metrics.total_revenue),
                monthly_revenue=float(revenue_metrics.monthly_revenue),
                daily_revenue=float(revenue_metrics.daily_revenue),
                revenue_growth_rate=revenue_metrics.revenue_growth_rate,
                average_revenue_per_user=float(revenue_metrics.average_revenue_per_user),
                revenue_by_plan={k: float(v) for k, v in revenue_metrics.revenue_by_plan.items()},
                revenue_forecast={k: float(v) for k, v in revenue_metrics.revenue_forecast.items()},
                generated_at=datetime.now()
            ),
            user_metrics=UserMetricsResponse(
                total_users=user_metrics.total_users,
                active_users=user_metrics.active_users,
                new_users_today=user_metrics.new_users_today,
                new_users_this_month=user_metrics.new_users_this_month,
                user_retention_rate=user_metrics.user_retention_rate,
                user_growth_rate=user_metrics.user_growth_rate,
                churn_rate=user_metrics.churn_rate,
                user_ltv=float(user_metrics.user_ltv),
                generated_at=datetime.now()
            ),
            usage_metrics=UsageMetricsResponse(
                total_api_calls=usage_metrics.total_api_calls,
                daily_api_calls=usage_metrics.daily_api_calls,
                average_calls_per_user=usage_metrics.average_calls_per_user,
                top_used_models=usage_metrics.top_used_models,
                usage_growth_rate=usage_metrics.usage_growth_rate,
                error_rate=usage_metrics.error_rate,
                average_response_time=usage_metrics.average_response_time,
                generated_at=datetime.now()
            ),
            business_insights=BusinessInsightsResponse(
                key_insights=business_insights.key_insights,
                growth_opportunities=business_insights.growth_opportunities,
                risk_factors=business_insights.risk_factors,
                recommendations=business_insights.recommendations,
                generated_at=business_insights.generated_at
            ),
            recent_anomalies=[
                {
                    "anomaly_id": anomaly.anomaly_id,
                    "user_id": anomaly.user_id,
                    "type": anomaly.anomaly_type,
                    "description": anomaly.description,
                    "severity": anomaly.severity,
                    "detected_at": anomaly.detected_at.isoformat()
                }
                for anomaly in recent_anomalies[:5]  # 只返回最近5个异常
            ],
            generated_at=datetime.now()
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取仪表盘摘要失败: {str(e)}")


@router.get("/revenue/metrics", response_model=RevenueMetricsResponse)
async def get_revenue_metrics(
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: dict = Depends(get_current_user)
):
    """获取收入指标"""
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        metrics = await business_analytics.calculate_revenue_metrics(start_date, end_date)

        return RevenueMetricsResponse(
            total_revenue=float(metrics.total_revenue),
            monthly_revenue=float(metrics.monthly_revenue),
            daily_revenue=float(metrics.daily_revenue),
            revenue_growth_rate=metrics.revenue_growth_rate,
            average_revenue_per_user=float(metrics.average_revenue_per_user),
            revenue_by_plan={k: float(v) for k, v in metrics.revenue_by_plan.items()},
            revenue_forecast={k: float(v) for k, v in metrics.revenue_forecast.items()},
            generated_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取收入指标失败: {str(e)}")


@router.get("/users/metrics", response_model=UserMetricsResponse)
async def get_user_metrics(
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: dict = Depends(get_current_user)
):
    """获取用户指标"""
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        metrics = await business_analytics.calculate_user_metrics(start_date, end_date)

        return UserMetricsResponse(
            total_users=metrics.total_users,
            active_users=metrics.active_users,
            new_users_today=metrics.new_users_today,
            new_users_this_month=metrics.new_users_this_month,
            user_retention_rate=metrics.user_retention_rate,
            user_growth_rate=metrics.user_growth_rate,
            churn_rate=metrics.churn_rate,
            user_ltv=float(metrics.user_ltv),
            generated_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户指标失败: {str(e)}")


@router.get("/usage/metrics", response_model=UsageMetricsResponse)
async def get_usage_metrics(
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: dict = Depends(get_current_user)
):
    """获取使用量指标"""
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        metrics = await business_analytics.calculate_usage_metrics(start_date, end_date)

        return UsageMetricsResponse(
            total_api_calls=metrics.total_api_calls,
            daily_api_calls=metrics.daily_api_calls,
            average_calls_per_user=metrics.average_calls_per_user,
            top_used_models=metrics.top_used_models,
            usage_growth_rate=metrics.usage_growth_rate,
            error_rate=metrics.error_rate,
            average_response_time=metrics.average_response_time,
            generated_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取使用量指标失败: {str(e)}")


@router.get("/business/insights", response_model=BusinessInsightsResponse)
async def get_business_insights(
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: dict = Depends(get_current_user)
):
    """获取商业洞察"""
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # 获取各类指标
        revenue_metrics = await business_analytics.calculate_revenue_metrics(start_date, end_date)
        user_metrics = await business_analytics.calculate_user_metrics(start_date, end_date)
        usage_metrics = await business_analytics.calculate_usage_metrics(start_date, end_date)

        # 生成商业洞察
        insights = await business_analytics.generate_business_insights(
            revenue_metrics, user_metrics, usage_metrics
        )

        return BusinessInsightsResponse(
            key_insights=insights.key_insights,
            growth_opportunities=insights.growth_opportunities,
            risk_factors=insights.risk_factors,
            recommendations=insights.recommendations,
            generated_at=insights.generated_at
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取商业洞察失败: {str(e)}")


@router.get("/behavior/metrics", response_model=UserBehaviorMetricsResponse)
async def get_behavior_metrics(
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: dict = Depends(get_current_user)
):
    """获取用户行为指标"""
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        metrics = await user_behavior_analytics.calculate_behavior_metrics(start_date, end_date)

        return UserBehaviorMetricsResponse(
            avg_session_duration=metrics.avg_session_duration,
            bounce_rate=metrics.bounce_rate,
            pages_per_session=metrics.pages_per_session,
            return_user_rate=metrics.return_user_rate,
            daily_active_users=metrics.daily_active_users,
            weekly_active_users=metrics.weekly_active_users,
            monthly_active_users=metrics.monthly_active_users,
            peak_usage_hours=metrics.peak_usage_hours,
            most_used_features=metrics.most_used_features,
            user_segments=metrics.user_segments,
            generated_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户行为指标失败: {str(e)}")


@router.post("/trends/analyze", response_model=TrendAnalysisResponse)
async def analyze_trend(
    request: TrendAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """分析趋势和生成预测"""
    try:
        # 生成模拟数据点
        if not request.start_date:
            request.start_date = datetime.now() - timedelta(days=30)
        if not request.end_date:
            request.end_date = datetime.now()

        data_points = []
        current_date = request.start_date
        while current_date <= request.end_date:
            # 生成模拟数据
            base_value = 100
            trend = (current_date - request.start_date).days * 2
            noise = (hash(current_date.isoformat()) % 20) - 10

            data_points.append(TrendData(
                timestamp=current_date,
                value=base_value + trend + noise,
                metadata={"source": "simulated"}
            ))
            current_date += timedelta(days=1)

        # 执行趋势分析
        trend_metrics, forecast = await trend_analyzer.analyze_trend(
            request.metric_name,
            data_points,
            request.forecast_days
        )

        return TrendAnalysisResponse(
            metric_name=request.metric_name,
            trend_metrics={
                "trend_direction": trend_metrics.trend_direction,
                "trend_strength": trend_metrics.trend_strength,
                "growth_rate": trend_metrics.growth_rate,
                "volatility": trend_metrics.volatility,
                "seasonality": trend_metrics.seasonality,
                "confidence_level": trend_metrics.confidence_level
            },
            forecast={
                "forecast_id": forecast.forecast_id,
                "forecast_period_days": forecast.forecast_period_days,
                "accuracy_score": forecast.accuracy_score,
                "model_used": forecast.model_used,
                "forecast_data": [
                    {
                        "timestamp": point.timestamp.isoformat(),
                        "value": point.value,
                        "metadata": point.metadata
                    }
                    for point in forecast.forecast_data
                ],
                "confidence_intervals": forecast.confidence_intervals
            },
            generated_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"趋势分析失败: {str(e)}")


@router.get("/metrics/realtime")
async def get_realtime_metrics(
    metric_ids: Optional[List[str]] = Query(None, description="指标ID列表"),
    current_user: dict = Depends(get_current_user)
):
    """获取实时指标数据"""
    try:
        if not metric_ids:
            # 返回默认的关键指标
            metric_ids = [
                "api_requests_total",
                "api_response_time",
                "active_users_total",
                "system_cpu_usage",
                "system_memory_usage"
            ]

        results = {}
        for metric_id in metric_ids:
            summary = await metrics_collector.get_metric_summary(metric_id, "5m")
            if summary:
                results[metric_id] = summary

        return {
            "metrics": results,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取实时指标失败: {str(e)}")


@router.post("/metrics/query")
async def query_metrics(
    request: MetricsQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """查询历史指标数据"""
    try:
        metrics = await metrics_collector.get_metrics(
            request.metric_ids,
            request.start_time,
            request.end_time,
            request.aggregation_period
        )

        # 转换为响应格式
        results = []
        for metric in metrics:
            if isinstance(metric, MetricData):
                results.append({
                    "type": "raw",
                    "metric_id": metric.metric_id,
                    "timestamp": metric.timestamp.isoformat(),
                    "value": metric.value,
                    "labels": metric.labels,
                    "source": metric.source.value,
                    "quality_score": metric.quality_score
                })
            elif isinstance(metric, MetricAggregation):
                results.append({
                    "type": "aggregated",
                    "metric_id": metric.metric_id,
                    "timestamp": metric.timestamp.isoformat(),
                    "aggregation_period": metric.aggregation_period,
                    "aggregated_value": metric.aggregated_value,
                    "sample_count": metric.sample_count,
                    "min_value": metric.min_value,
                    "max_value": metric.max_value,
                    "avg_value": metric.avg_value,
                    "sum_value": metric.sum_value
                })

        return {
            "metrics": results,
            "query_params": {
                "metric_ids": request.metric_ids,
                "start_time": request.start_time.isoformat() if request.start_time else None,
                "end_time": request.end_time.isoformat() if request.end_time else None,
                "aggregation_period": request.aggregation_period
            },
            "total_count": len(results)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询指标数据失败: {str(e)}")


@router.get("/anomalies/detect")
async def detect_anomalies(
    metric_name: Optional[str] = Query(None, description="指标名称"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: dict = Depends(get_current_user)
):
    """检测异常"""
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()

        # 检测用户行为异常
        behavior_anomalies = await user_behavior_analytics.detect_behavior_anomalies()

        # 如果指定了指标名称，检测趋势异常
        trend_anomalies = []
        if metric_name:
            # 生成模拟数据进行异常检测
            data_points = []
            current_date = start_date
            while current_date <= end_date:
                data_points.append(TrendData(
                    timestamp=current_date,
                    value=100 + (hash(current_date.isoformat()) % 50),
                    metadata={"source": "simulated"}
                ))
                current_date += timedelta(hours=1)

            trend_anomalies = await trend_analyzer.detect_trend_anomalies(metric_name, data_points)

        # 合并异常结果
        all_anomalies = []

        # 用户行为异常
        for anomaly in behavior_anomalies:
            all_anomalies.append({
                "anomaly_id": anomaly.anomaly_id,
                "metric_name": anomaly.metric_name,
                "type": "user_behavior",
                "description": anomaly.description,
                "severity": anomaly.severity,
                "detected_at": anomaly.detected_at.isoformat(),
                "metadata": {
                    "user_id": anomaly.user_id,
                    "anomaly_type": anomaly.anomaly_type,
                    "deviation_score": anomaly.deviation_score
                }
            })

        # 趋势异常
        for anomaly in trend_anomalies:
            all_anomalies.append({
                "anomaly_id": anomaly.anomaly_id,
                "metric_name": anomaly.metric_name,
                "type": "trend",
                "description": f"趋势异常: {anomaly.anomaly_type}",
                "severity": anomaly.severity,
                "detected_at": anomaly.anomaly_timestamp.isoformat(),
                "metadata": {
                    "expected_value": anomaly.expected_value,
                    "actual_value": anomaly.actual_value,
                    "deviation_score": anomaly.deviation_score
                }
            })

        return {
            "anomalies": all_anomalies,
            "summary": {
                "total_count": len(all_anomalies),
                "critical_count": len([a for a in all_anomalies if a["severity"] == "critical"]),
                "high_count": len([a for a in all_anomalies if a["severity"] == "high"]),
                "medium_count": len([a for a in all_anomalies if a["severity"] == "medium"]),
                "low_count": len([a for a in all_anomalies if a["severity"] == "low"])
            },
            "query_params": {
                "metric_name": metric_name,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"异常检测失败: {str(e)}")


@router.get("/personas")
async def get_user_personas(
    current_user: dict = Depends(get_current_user)
):
    """获取用户画像"""
    try:
        personas = await user_behavior_analytics.generate_user_personas()

        return {
            "personas": [
                {
                    "persona_id": persona.persona_id,
                    "user_count": persona.user_count,
                    "characteristics": persona.characteristics,
                    "behavior_patterns": persona.behavior_patterns,
                    "preferred_features": persona.preferred_features,
                    "engagement_level": persona.engagement_level,
                    "value_score": persona.value_score
                }
                for persona in personas
            ],
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户画像失败: {str(e)}")


@router.get("/funnels/{funnel_name}")
async def analyze_user_funnel(
    funnel_name: str,
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: dict = Depends(get_current_user)
):
    """分析用户转化漏斗"""
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        # 定义标准漏斗
        standard_funnels = {
            "user_onboarding": ["注册", "验证邮箱", "完成资料", "首次使用"],
            "api_adoption": ["查看API文档", "获取API密钥", "首次API调用", "持续使用"],
            "subscription": ["访问定价页面", "选择计划", "支付", "激活服务"]
        }

        funnel_stages = standard_funnels.get(funnel_name, ["阶段1", "阶段2", "阶段3"])

        funnel_metrics = await user_behavior_analytics.analyze_user_funnel(
            funnel_name, funnel_stages, start_date, end_date
        )

        return {
            "funnel_name": funnel_name,
            "total_users": funnel_metrics.total_users,
            "overall_conversion_rate": funnel_metrics.overall_conversion_rate,
            "stage_metrics": funnel_metrics.stage_metrics,
            "drop_off_points": funnel_metrics.drop_off_points,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"漏斗分析失败: {str(e)}")


# 导入必要的模块
import asyncio