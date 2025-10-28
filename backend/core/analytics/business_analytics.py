"""
商业智能分析器
Business Intelligence Analytics Module

提供企业级商业分析功能，包括：
- 收入和增长指标分析
- 用户活跃度分析
- API使用趋势分析
- 模型使用排行分析
- 商业洞察生成
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal
import pandas as pd
import numpy as np
from pathlib import Path

from backend.config.settings import get_settings
from backend.core.cache.multi_level_cache import cache_manager
from backend.core.cost_tracker import cost_tracker

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class RevenueMetrics:
    """收入指标数据结构"""
    total_revenue: Decimal
    monthly_revenue: Decimal
    daily_revenue: Decimal
    revenue_growth_rate: float
    average_revenue_per_user: Decimal
    revenue_by_plan: Dict[str, Decimal]
    revenue_forecast: Dict[str, Decimal]

@dataclass
class UserMetrics:
    """用户指标数据结构"""
    total_users: int
    active_users: int
    new_users_today: int
    new_users_this_month: int
    user_retention_rate: float
    user_growth_rate: float
    churn_rate: float
    user_ltv: Decimal

@dataclass
class UsageMetrics:
    """使用量指标数据结构"""
    total_api_calls: int
    daily_api_calls: int
    average_calls_per_user: float
    top_used_models: List[Dict[str, Any]]
    usage_growth_rate: float
    error_rate: float
    average_response_time: float

@dataclass
class BusinessInsights:
    """商业洞察数据结构"""
    key_insights: List[str]
    growth_opportunities: List[str]
    risk_factors: List[str]
    recommendations: List[str]
    generated_at: datetime


class BusinessAnalytics:
    """商业智能分析器"""

    def __init__(self):
        self.cache_key_prefix = "business_analytics"
        self.data_dir = Path("data/analytics")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化数据存储路径
        self.revenue_data_path = self.data_dir / "revenue_data.json"
        self.user_metrics_path = self.data_dir / "user_metrics.json"
        self.usage_analytics_path = self.data_dir / "usage_analytics.json"

    async def calculate_revenue_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> RevenueMetrics:
        """
        计算收入指标

        Args:
            start_date: 开始日期，默认为30天前
            end_date: 结束日期，默认为今天

        Returns:
            RevenueMetrics: 收入指标对象
        """
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()

            cache_key = f"{self.cache_key_prefix}:revenue_metrics:{start_date.date()}:{end_date.date()}"

            # 尝试从缓存获取
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                return RevenueMetrics(**cached_result)

            logger.info(f"Calculating revenue metrics from {start_date.date()} to {end_date.date()}")

            # 获取计费数据
            billing_data = await self._load_billing_data(start_date, end_date)

            # 计算各项收入指标
            total_revenue = self._calculate_total_revenue(billing_data)
            monthly_revenue = self._calculate_monthly_revenue(billing_data)
            daily_revenue = self._calculate_daily_revenue(billing_data)
            revenue_growth_rate = self._calculate_revenue_growth_rate(billing_data)
            avg_revenue_per_user = self._calculate_avg_revenue_per_user(billing_data)
            revenue_by_plan = self._calculate_revenue_by_plan(billing_data)
            revenue_forecast = await self._forecast_revenue(billing_data)

            metrics = RevenueMetrics(
                total_revenue=total_revenue,
                monthly_revenue=monthly_revenue,
                daily_revenue=daily_revenue,
                revenue_growth_rate=revenue_growth_rate,
                average_revenue_per_user=avg_revenue_per_user,
                revenue_by_plan=revenue_by_plan,
                revenue_forecast=revenue_forecast
            )

            # 缓存结果（缓存1小时）
            await cache_manager.set(
                cache_key,
                asdict(metrics),
                expire_seconds=3600
            )

            # 保存到文件
            await self._save_revenue_metrics(metrics)

            logger.info(f"Revenue metrics calculated: Total=${total_revenue:.2f}, Growth={revenue_growth_rate:.2%}")
            return metrics

        except Exception as e:
            logger.error(f"Error calculating revenue metrics: {e}")
            # 返回默认指标
            return RevenueMetrics(
                total_revenue=Decimal('0'),
                monthly_revenue=Decimal('0'),
                daily_revenue=Decimal('0'),
                revenue_growth_rate=0.0,
                average_revenue_per_user=Decimal('0'),
                revenue_by_plan={},
                revenue_forecast={}
            )

    async def calculate_user_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> UserMetrics:
        """
        计算用户指标

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            UserMetrics: 用户指标对象
        """
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()

            cache_key = f"{self.cache_key_prefix}:user_metrics:{start_date.date()}:{end_date.date()}"

            # 尝试从缓存获取
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                return UserMetrics(**cached_result)

            logger.info(f"Calculating user metrics from {start_date.date()} to {end_date.date()}")

            # 获取用户数据
            user_data = await self._load_user_data(start_date, end_date)

            # 计算各项用户指标
            total_users = self._calculate_total_users(user_data)
            active_users = self._calculate_active_users(user_data)
            new_users_today = self._calculate_new_users_today(user_data)
            new_users_this_month = self._calculate_new_users_month(user_data)
            user_retention_rate = self._calculate_user_retention_rate(user_data)
            user_growth_rate = self._calculate_user_growth_rate(user_data)
            churn_rate = self._calculate_churn_rate(user_data)
            user_ltv = self._calculate_user_ltv(user_data)

            metrics = UserMetrics(
                total_users=total_users,
                active_users=active_users,
                new_users_today=new_users_today,
                new_users_this_month=new_users_this_month,
                user_retention_rate=user_retention_rate,
                user_growth_rate=user_growth_rate,
                churn_rate=churn_rate,
                user_ltv=user_ltv
            )

            # 缓存结果（缓存30分钟）
            await cache_manager.set(
                cache_key,
                asdict(metrics),
                expire_seconds=1800
            )

            # 保存到文件
            await self._save_user_metrics(metrics)

            logger.info(f"User metrics calculated: Total={total_users}, Active={active_users}, Growth={user_growth_rate:.2%}")
            return metrics

        except Exception as e:
            logger.error(f"Error calculating user metrics: {e}")
            return UserMetrics(
                total_users=0,
                active_users=0,
                new_users_today=0,
                new_users_this_month=0,
                user_retention_rate=0.0,
                user_growth_rate=0.0,
                churn_rate=0.0,
                user_ltv=Decimal('0')
            )

    async def calculate_usage_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> UsageMetrics:
        """
        计算使用量指标

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            UsageMetrics: 使用量指标对象
        """
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()

            cache_key = f"{self.cache_key_prefix}:usage_metrics:{start_date.date()}:{end_date.date()}"

            # 尝试从缓存获取
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                return UsageMetrics(**cached_result)

            logger.info(f"Calculating usage metrics from {start_date.date()} to {end_date.date()}")

            # 获取使用量数据
            usage_data = await self._load_usage_data(start_date, end_date)

            # 计算各项使用量指标
            total_api_calls = self._calculate_total_api_calls(usage_data)
            daily_api_calls = self._calculate_daily_api_calls(usage_data)
            avg_calls_per_user = self._calculate_avg_calls_per_user(usage_data)
            top_used_models = self._calculate_top_used_models(usage_data)
            usage_growth_rate = self._calculate_usage_growth_rate(usage_data)
            error_rate = self._calculate_error_rate(usage_data)
            avg_response_time = self._calculate_avg_response_time(usage_data)

            metrics = UsageMetrics(
                total_api_calls=total_api_calls,
                daily_api_calls=daily_api_calls,
                average_calls_per_user=avg_calls_per_user,
                top_used_models=top_used_models,
                usage_growth_rate=usage_growth_rate,
                error_rate=error_rate,
                average_response_time=avg_response_time
            )

            # 缓存结果（缓存15分钟）
            await cache_manager.set(
                cache_key,
                asdict(metrics),
                expire_seconds=900
            )

            # 保存到文件
            await self._save_usage_metrics(metrics)

            logger.info(f"Usage metrics calculated: Total={total_api_calls}, Daily={daily_api_calls}, Growth={usage_growth_rate:.2%}")
            return metrics

        except Exception as e:
            logger.error(f"Error calculating usage metrics: {e}")
            return UsageMetrics(
                total_api_calls=0,
                daily_api_calls=0,
                average_calls_per_user=0.0,
                top_used_models=[],
                usage_growth_rate=0.0,
                error_rate=0.0,
                average_response_time=0.0
            )

    async def generate_business_insights(
        self,
        revenue_metrics: RevenueMetrics,
        user_metrics: UserMetrics,
        usage_metrics: UsageMetrics
    ) -> BusinessInsights:
        """
        生成商业洞察

        Args:
            revenue_metrics: 收入指标
            user_metrics: 用户指标
            usage_metrics: 使用量指标

        Returns:
            BusinessInsights: 商业洞察对象
        """
        try:
            logger.info("Generating business insights")

            key_insights = []
            growth_opportunities = []
            risk_factors = []
            recommendations = []

            # 分析收入洞察
            if revenue_metrics.revenue_growth_rate > 0.2:
                key_insights.append(f"收入增长率表现优异，达到{revenue_metrics.revenue_growth_rate:.1%}")
            elif revenue_metrics.revenue_growth_rate < 0:
                risk_factors.append("收入出现负增长，需要立即关注")

            # 分析用户洞察
            if user_metrics.user_retention_rate > 0.8:
                key_insights.append(f"用户留存率高达{user_metrics.user_retention_rate:.1%}，用户满意度良好")
            elif user_metrics.churn_rate > 0.1:
                risk_factors.append(f"用户流失率较高({user_metrics.churn_rate:.1%})，需要改善用户体验")

            # 分析使用量洞察
            if usage_metrics.error_rate > 0.05:
                risk_factors.append(f"API错误率较高({usage_metrics.error_rate:.1%})，需要提升系统稳定性")

            # 生成增长机会
            if usage_metrics.top_used_models:
                top_model = usage_metrics.top_used_models[0]
                growth_opportunities.append(f"重点推广{top_model['model']}模型，优化相关功能")

            # 生成建议
            if user_metrics.user_growth_rate < 0.05:
                recommendations.append("加强用户获取策略，提升市场推广效果")

            if revenue_metrics.average_revenue_per_user < Decimal('10'):
                recommendations.append("优化定价策略，提升单用户收入贡献")

            insights = BusinessInsights(
                key_insights=key_insights,
                growth_opportunities=growth_opportunities,
                risk_factors=risk_factors,
                recommendations=recommendations,
                generated_at=datetime.now()
            )

            logger.info(f"Generated {len(key_insights)} key insights, {len(recommendations)} recommendations")
            return insights

        except Exception as e:
            logger.error(f"Error generating business insights: {e}")
            return BusinessInsights(
                key_insights=["数据分析暂时不可用"],
                growth_opportunities=[],
                risk_factors=["数据分析系统异常"],
                recommendations=["请检查数据分析系统状态"],
                generated_at=datetime.now()
            )

    # 私有辅助方法

    async def _load_billing_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """加载计费数据"""
        # TODO: 从数据库或文件加载计费数据
        # 这里返回模拟数据
        return [
            {
                "date": (start_date + timedelta(days=i)).date().isoformat(),
                "revenue": Decimal(str(100 + i * 10)),
                "plan": "pro" if i % 3 == 0 else "free",
                "user_id": f"user_{i % 10}"
            }
            for i in range((end_date - start_date).days + 1)
        ]

    async def _load_user_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """加载用户数据"""
        # TODO: 从数据库加载用户数据
        return [
            {
                "date": (start_date + timedelta(days=i)).date().isoformat(),
                "new_users": 5 + i % 8,
                "active_users": 50 + i * 2,
                "churned_users": 1 if i % 7 == 0 else 0
            }
            for i in range((end_date - start_date).days + 1)
        ]

    async def _load_usage_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """加载使用量数据"""
        # TODO: 从数据库加载使用量数据
        models = ["grok-4-fast:free", "deepseek-chat-v3.1:free", "gemini-pro"]
        return [
            {
                "date": (start_date + timedelta(days=i)).date().isoformat(),
                "api_calls": 500 + i * 50,
                "model": models[i % len(models)],
                "response_time": 1.2 + (i % 5) * 0.1,
                "errors": 5 if i % 10 == 0 else 0
            }
            for i in range((end_date - start_date).days + 1)
        ]

    def _calculate_total_revenue(self, billing_data: List[Dict]) -> Decimal:
        """计算总收入"""
        return sum(item["revenue"] for item in billing_data)

    def _calculate_monthly_revenue(self, billing_data: List[Dict]) -> Decimal:
        """计算月收入"""
        current_month = datetime.now().replace(day=1)
        monthly_data = [
            item for item in billing_data
            if datetime.fromisoformat(item["date"]) >= current_month
        ]
        return sum(item["revenue"] for item in monthly_data)

    def _calculate_daily_revenue(self, billing_data: List[Dict]) -> Decimal:
        """计算日收入"""
        today = datetime.now().date()
        daily_data = [
            item for item in billing_data
            if datetime.fromisoformat(item["date"]).date() == today
        ]
        return sum(item["revenue"] for item in daily_data)

    def _calculate_revenue_growth_rate(self, billing_data: List[Dict]) -> float:
        """计算收入增长率"""
        if len(billing_data) < 2:
            return 0.0

        # 简单的同比增长率计算
        current_period = sum(item["revenue"] for item in billing_data[-7:])  # 最近7天
        previous_period = sum(item["revenue"] for item in billing_data[-14:-7])  # 前7天

        if previous_period == 0:
            return 0.0

        return float((current_period - previous_period) / previous_period)

    def _calculate_avg_revenue_per_user(self, billing_data: List[Dict]) -> Decimal:
        """计算平均每用户收入"""
        unique_users = len(set(item["user_id"] for item in billing_data))
        if unique_users == 0:
            return Decimal('0')

        total_revenue = sum(item["revenue"] for item in billing_data)
        return total_revenue / unique_users

    def _calculate_revenue_by_plan(self, billing_data: List[Dict]) -> Dict[str, Decimal]:
        """按计划计算收入"""
        revenue_by_plan = {}
        for item in billing_data:
            plan = item["plan"]
            if plan not in revenue_by_plan:
                revenue_by_plan[plan] = Decimal('0')
            revenue_by_plan[plan] += item["revenue"]
        return revenue_by_plan

    async def _forecast_revenue(self, billing_data: List[Dict]) -> Dict[str, Decimal]:
        """预测未来收入"""
        # 简单的线性预测
        if len(billing_data) < 7:
            return {}

        # 计算最近7天的日均收入
        recent_revenue = [
            item["revenue"] for item in billing_data[-7:]
        ]
        daily_avg = sum(recent_revenue) / len(recent_revenue)

        # 预测未来7天
        forecast = {}
        for i in range(1, 8):
            future_date = (datetime.now() + timedelta(days=i)).date().isoformat()
            # 简单的线性增长预测
            forecast[future_date] = daily_avg * (1 + 0.02 * i)  # 假设2%日增长率

        return forecast

    def _calculate_total_users(self, user_data: List[Dict]) -> int:
        """计算总用户数"""
        # 模拟计算，实际应该从数据库获取
        return 100 + len(user_data) * 2

    def _calculate_active_users(self, user_data: List[Dict]) -> int:
        """计算活跃用户数"""
        if not user_data:
            return 0
        return sum(item["active_users"] for item in user_data[-7:]) // 7  # 最近7天平均

    def _calculate_new_users_today(self, user_data: List[Dict]) -> int:
        """计算今日新用户数"""
        if not user_data:
            return 0
        return user_data[-1]["new_users"]

    def _calculate_new_users_month(self, user_data: List[Dict]) -> int:
        """计算本月新用户数"""
        current_month = datetime.now().replace(day=1)
        month_data = [
            item for item in user_data
            if datetime.fromisoformat(item["date"]) >= current_month
        ]
        return sum(item["new_users"] for item in month_data)

    def _calculate_user_retention_rate(self, user_data: List[Dict]) -> float:
        """计算用户留存率"""
        if not user_data or len(user_data) < 30:
            return 0.85  # 默认值

        # 简化的留存率计算
        active_users = sum(item["active_users"] for item in user_data[-30:])
        total_users = self._calculate_total_users(user_data)

        if total_users == 0:
            return 0.0

        return min(active_users / total_users / 30, 1.0)  # 避免超过100%

    def _calculate_user_growth_rate(self, user_data: List[Dict]) -> float:
        """计算用户增长率"""
        if len(user_data) < 14:
            return 0.0

        recent_growth = sum(item["new_users"] for item in user_data[-7:])
        previous_growth = sum(item["new_users"] for item in user_data[-14:-7])

        if previous_growth == 0:
            return 0.0

        return (recent_growth - previous_growth) / previous_growth

    def _calculate_churn_rate(self, user_data: List[Dict]) -> float:
        """计算用户流失率"""
        if not user_data:
            return 0.0

        total_churned = sum(item["churned_users"] for item in user_data[-30:])
        total_users = self._calculate_total_users(user_data)

        if total_users == 0:
            return 0.0

        return total_churned / total_users

    def _calculate_user_ltv(self, user_data: List[Dict]) -> Decimal:
        """计算用户生命周期价值"""
        # 简化的LTV计算
        avg_monthly_revenue = Decimal('50')  # 假设平均月收入
        retention_months = 12  # 假设平均保留12个月
        return avg_monthly_revenue * retention_months

    def _calculate_total_api_calls(self, usage_data: List[Dict]) -> int:
        """计算总API调用数"""
        return sum(item["api_calls"] for item in usage_data)

    def _calculate_daily_api_calls(self, usage_data: List[Dict]) -> int:
        """计算日API调用数"""
        if not usage_data:
            return 0
        return usage_data[-1]["api_calls"]

    def _calculate_avg_calls_per_user(self, usage_data: List[Dict]) -> float:
        """计算平均每用户API调用数"""
        total_calls = self._calculate_total_api_calls(usage_data)
        total_users = 50  # 假设用户数

        if total_users == 0:
            return 0.0

        return total_calls / total_users

    def _calculate_top_used_models(self, usage_data: List[Dict]) -> List[Dict[str, Any]]:
        """计算最常用模型"""
        model_usage = {}
        for item in usage_data:
            model = item["model"]
            if model not in model_usage:
                model_usage[model] = 0
            model_usage[model] += item["api_calls"]

        # 按使用量排序
        sorted_models = sorted(model_usage.items(), key=lambda x: x[1], reverse=True)

        return [
            {"model": model, "usage": usage, "percentage": usage / self._calculate_total_api_calls(usage_data)}
            for model, usage in sorted_models[:5]
        ]

    def _calculate_usage_growth_rate(self, usage_data: List[Dict]) -> float:
        """计算使用量增长率"""
        if len(usage_data) < 14:
            return 0.0

        recent_usage = sum(item["api_calls"] for item in usage_data[-7:])
        previous_usage = sum(item["api_calls"] for item in usage_data[-14:-7])

        if previous_usage == 0:
            return 0.0

        return (recent_usage - previous_usage) / previous_usage

    def _calculate_error_rate(self, usage_data: List[Dict]) -> float:
        """计算错误率"""
        total_calls = sum(item["api_calls"] for item in usage_data)
        total_errors = sum(item["errors"] for item in usage_data)

        if total_calls == 0:
            return 0.0

        return total_errors / total_calls

    def _calculate_avg_response_time(self, usage_data: List[Dict]) -> float:
        """计算平均响应时间"""
        if not usage_data:
            return 0.0

        total_response_time = sum(item["response_time"] for item in usage_data)
        return total_response_time / len(usage_data)

    async def _save_revenue_metrics(self, metrics: RevenueMetrics):
        """保存收入指标到文件"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "metrics": asdict(metrics)
            }
            with open(self.revenue_data_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving revenue metrics: {e}")

    async def _save_user_metrics(self, metrics: UserMetrics):
        """保存用户指标到文件"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "metrics": asdict(metrics)
            }
            with open(self.user_metrics_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving user metrics: {e}")

    async def _save_usage_metrics(self, metrics: UsageMetrics):
        """保存使用量指标到文件"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "metrics": asdict(metrics)
            }
            with open(self.usage_analytics_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving usage metrics: {e}")


# 全局实例
business_analytics = BusinessAnalytics()