"""
Developer Usage Statistics and Billing Service
Week 4 Day 24: API Usage Statistics and Billing
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, extract
from decimal import Decimal

from backend.models.developer import Developer, APIUsageRecord, DeveloperAPIKey
from backend.models.subscription import Subscription, Invoice, Payment

class UsageService:
    """开发者使用量统计和计费服务"""

    def __init__(self, db: Session):
        self.db = db

    def _calculate_model_cost(self, model: str, tokens: int) -> Decimal:
        """计算模型使用成本"""
        # 模型定价表（每1000 tokens的成本）
        pricing = {
            "gpt-4o": Decimal("0.015"),
            "gpt-4o-mini": Decimal("0.00015"),
            "claude-3.5-sonnet": Decimal("0.003"),
            "llama-3.1-70b": Decimal("0.001"),
            "gemini-1.5-pro": Decimal("0.0025"),
            "gemini-1.5-flash": Decimal("0.000075"),
            "deepseek-chat-v3.1:free": Decimal("0.0"),
            "grok-4-fast:free": Decimal("0.0")
        }

        per_thousand_cost = pricing.get(model, Decimal("0.001"))
        return (Decimal(tokens) / Decimal("1000")) * per_thousand_cost

    async def get_developer_usage_overview(
        self,
        developer_id: str,
        days: int = 30
    ) -> Dict:
        """获取开发者使用量概览"""

        # 计算时间范围
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 查询使用记录
        usage_records = await self.db.query(APIUsageRecord).filter(
            and_(
                APIUsageRecord.developer_id == developer_id,
                APIUsageRecord.created_at >= start_date,
                APIUsageRecord.created_at <= end_date
            )
        ).all()

        if not usage_records:
            return {
                "period_days": days,
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "unique_models": 0,
                "avg_response_time": 0.0,
                "success_rate": 0.0,
                "daily_stats": {},
                "model_breakdown": {},
                "error_breakdown": {}
            }

        # 基础统计
        total_requests = len(usage_records)
        total_tokens = sum(record.tokens_used for record in usage_records)
        total_cost = sum(float(record.cost) for record in usage_records)

        # 响应时间统计
        response_times = [record.response_time_ms for record in usage_records if record.response_time_ms]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        # 成功率统计
        success_requests = sum(1 for record in usage_records if 200 <= record.status_code < 300)
        success_rate = (success_requests / total_requests) * 100 if total_requests > 0 else 0

        # 模型统计
        model_usage = {}
        for record in usage_records:
            model = record.model or "unknown"
            if model not in model_usage:
                model_usage[model] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0.0,
                    "avg_response_time": 0,
                    "success_rate": 0.0
                }
            model_usage[model]["requests"] += 1
            model_usage[model]["tokens"] += record.tokens_used
            model_usage[model]["cost"] += float(record.cost)

        # 每日统计
        daily_stats = {}
        for record in usage_records:
            date_key = record.created_at.strftime("%Y-%m-%d")
            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0.0,
                    "unique_models": set()
                }
            daily_stats[date_key]["requests"] += 1
            daily_stats[date_key]["tokens"] += record.tokens_used
            daily_stats[date_key]["cost"] += float(record.cost)
            daily_stats[date_key]["unique_models"].add(record.model or "unknown")

        # 转换unique_models为count
        for date_data in daily_stats.values():
            date_data["unique_models"] = len(date_data["unique_models"])

        # 错误统计
        error_breakdown = {}
        for record in usage_records:
            if record.status_code >= 400:
                error_type = self._get_error_type(record.status_code)
                if error_type not in error_breakdown:
                    error_breakdown[error_type] = 0
                error_breakdown[error_type] += 1

        return {
            "period_days": days,
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "unique_models": len(model_usage),
            "avg_response_time": round(avg_response_time, 2),
            "success_rate": round(success_rate, 2),
            "daily_stats": daily_stats,
            "model_breakdown": model_usage,
            "error_breakdown": error_breakdown
        }

    def _get_error_type(self, status_code: int) -> str:
        """获取错误类型"""
        if 400 <= status_code < 500:
            return "客户端错误"
        elif status_code >= 500:
            return "服务器错误"
        return "其他错误"

    async def get_usage_trends(
        self,
        developer_id: str,
        days: int = 30,
        granularity: str = "daily"
    ) -> Dict:
        """获取使用量趋势数据"""

        if granularity not in ["daily", "weekly", "monthly"]:
            granularity = "daily"

        # 计算时间范围
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 根据粒度分组查询
        if granularity == "daily":
            date_trunc = func.date(APIUsageRecord.created_at)
            date_format = "%Y-%m-%d"
        elif granularity == "weekly":
            date_trunc = func.date_trunc('week', APIUsageRecord.created_at)
            date_format = "%Y-W%W"
        else:  # monthly
            date_trunc = func.date_trunc('month', APIUsageRecord.created_at)
            date_format = "%Y-%m"

        # 查询分组统计
        query = await self.db.query(
            date_trunc.label('date'),
            func.count(APIUsageRecord.id).label('requests'),
            func.sum(APIUsageRecord.tokens_used).label('tokens'),
            func.sum(func.cast(APIUsageRecord.cost, func.Numeric)).label('cost'),
            func.avg(APIUsageRecord.response_time_ms).label('avg_response_time'),
            func.count(func.case([(APIUsageRecord.status_code >= 400, 1)])).label('errors')
        ).filter(
            and_(
                APIUsageRecord.developer_id == developer_id,
                APIUsageRecord.created_at >= start_date,
                APIUsageRecord.created_at <= end_date
            )
        ).group_by(date_trunc).order_by(date_trunc).all()

        # 格式化结果
        trends = []
        for row in query:
            date_str = row.date.strftime(date_format)
            trends.append({
                "date": date_str,
                "requests": row.requests,
                "tokens": int(row.tokens or 0),
                "cost": float(row.cost or 0),
                "avg_response_time": round(float(row.avg_response_time or 0), 2),
                "errors": row.errors,
                "success_rate": round(((row.requests - row.errors) / row.requests) * 100, 2) if row.requests > 0 else 0
            })

        return {
            "granularity": granularity,
            "period_days": days,
            "trends": trends
        }

    async def get_top_models_usage(
        self,
        developer_id: str,
        days: int = 30,
        limit: int = 10
    ) -> List[Dict]:
        """获取使用量最高的模型"""

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        query = await self.db.query(
            APIUsageRecord.model,
            func.count(APIUsageRecord.id).label('requests'),
            func.sum(APIUsageRecord.tokens_used).label('tokens'),
            func.sum(func.cast(APIUsageRecord.cost, func.Numeric)).label('cost'),
            func.avg(APIUsageRecord.response_time_ms).label('avg_response_time')
        ).filter(
            and_(
                APIUsageRecord.developer_id == developer_id,
                APIUsageRecord.created_at >= start_date,
                APIUsageRecord.created_at <= end_date,
                APIUsageRecord.model.isnot(None)
            )
        ).group_by(APIUsageRecord.model).order_by(
            desc(func.sum(APIUsageRecord.tokens_used))
        ).limit(limit).all()

        result = []
        for row in query:
            result.append({
                "model": row.model,
                "requests": row.requests,
                "tokens": int(row.tokens or 0),
                "cost": float(row.cost or 0),
                "avg_response_time": round(float(row.avg_response_time or 0), 2)
            })

        return result

    async def get_hourly_usage_pattern(
        self,
        developer_id: str,
        days: int = 7
    ) -> Dict:
        """获取按小时的使用模式分析"""

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 查询每小时的使用量
        query = await self.db.query(
            extract('hour', APIUsageRecord.created_at).label('hour'),
            func.count(APIUsageRecord.id).label('requests'),
            func.sum(APIUsageRecord.tokens_used).label('tokens'),
            func.sum(func.cast(APIUsageRecord.cost, func.Numeric)).label('cost')
        ).filter(
            and_(
                APIUsageRecord.developer_id == developer_id,
                APIUsageRecord.created_at >= start_date,
                APIUsageRecord.created_at <= end_date
            )
        ).group_by(extract('hour', APIUsageRecord.created_at)).order_by(
            extract('hour', APIUsageRecord.created_at)
        ).all()

        # 初始化24小时的数据
        hourly_data = {}
        for hour in range(24):
            hourly_data[hour] = {
                "hour": hour,
                "requests": 0,
                "tokens": 0,
                "cost": 0.0,
                "label": f"{hour:02d}:00"
            }

        # 填充查询结果
        for row in query:
            hour = int(row.hour)
            hourly_data[hour] = {
                "hour": hour,
                "requests": row.requests,
                "tokens": int(row.tokens or 0),
                "cost": float(row.cost or 0),
                "label": f"{hour:02d}:00"
            }

        return {
            "period_days": days,
            "hourly_data": list(hourly_data.values()),
            "peak_hour": max(hourly_data.values(), key=lambda x: x["requests"])["hour"]
        }

    async def get_usage_analytics(
        self,
        developer_id: str,
        days: int = 30
    ) -> Dict:
        """获取详细的使用分析报告"""

        # 获取基础概览
        overview = await self.get_developer_usage_overview(developer_id, days)

        # 获取趋势数据
        trends = await self.get_usage_trends(developer_id, days, "daily")

        # 获取热门模型
        top_models = await self.get_top_models_usage(developer_id, days, 5)

        # 获取使用模式
        hourly_pattern = await self.get_hourly_usage_pattern(developer_id, min(days, 7))

        # 计算一些额外的分析指标
        total_requests = overview["total_requests"]
        total_cost = overview["total_cost"]
        total_tokens = overview["total_tokens"]

        # 成本效率分析
        cost_per_request = total_cost / total_requests if total_requests > 0 else 0
        cost_per_1k_tokens = (total_cost / total_tokens * 1000) if total_tokens > 0 else 0

        # 使用活跃度分析
        active_days = len([d for d in overview["daily_stats"].values() if d["requests"] > 0])
        daily_avg_requests = total_requests / active_days if active_days > 0 else 0

        return {
            "overview": overview,
            "trends": trends,
            "top_models": top_models,
            "hourly_pattern": hourly_pattern,
            "analytics": {
                "cost_per_request": round(cost_per_request, 6),
                "cost_per_1k_tokens": round(cost_per_1k_tokens, 6),
                "active_days": active_days,
                "daily_avg_requests": round(daily_avg_requests, 1),
                "peak_usage_day": max(overview["daily_stats"].items(), key=lambda x: x[1]["requests"], default=(None, {}))[0] if overview["daily_stats"] else None,
                "most_used_model": top_models[0]["model"] if top_models else None
            }
        }

    async def export_usage_data(
        self,
        developer_id: str,
        start_date: datetime,
        end_date: datetime,
        format: str = "json"
    ) -> Dict:
        """导出使用数据"""

        # 查询指定时间范围内的所有使用记录
        usage_records = await self.db.query(APIUsageRecord).filter(
            and_(
                APIUsageRecord.developer_id == developer_id,
                APIUsageRecord.created_at >= start_date,
                APIUsageRecord.created_at <= end_date
            )
        ).order_by(APIUsageRecord.created_at.desc()).all()

        # 格式化数据
        export_data = []
        for record in usage_records:
            export_data.append({
                "timestamp": record.created_at.isoformat(),
                "endpoint": record.endpoint,
                "method": record.method,
                "model": record.model,
                "tokens_used": record.tokens_used,
                "cost": float(record.cost),
                "response_time_ms": record.response_time_ms,
                "status_code": record.status_code,
                "ip_address": record.ip_address,
                "request_id": record.request_id
            })

        # 计算汇总统计
        total_records = len(export_data)
        total_tokens = sum(item["tokens_used"] for item in export_data)
        total_cost = sum(item["cost"] for item in export_data)

        if format == "csv":
            # 简化CSV格式，实际实现可能需要更复杂的处理
            return {
                "format": "csv",
                "data": export_data,
                "summary": {
                    "total_records": total_records,
                    "total_tokens": total_tokens,
                    "total_cost": total_cost,
                    "export_date": datetime.utcnow().isoformat()
                }
            }
        else:
            return {
                "format": "json",
                "data": export_data,
                "summary": {
                    "total_records": total_records,
                    "total_tokens": total_tokens,
                    "total_cost": total_cost,
                    "export_date": datetime.utcnow().isoformat()
                }
            }

    async def get_usage_alerts(
        self,
        developer_id: str
    ) -> List[Dict]:
        """获取使用量告警信息"""

        # 获取开发者信息
        developer = await self.db.query(Developer).filter(
            Developer.id == developer_id
        ).first()

        if not developer:
            return []

        alerts = []

        # 检查月度配额使用情况
        current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_usage = await self.db.query(APIUsageRecord).filter(
            and_(
                APIUsageRecord.developer_id == developer_id,
                APIUsageRecord.created_at >= current_month_start
            )
        ).all()

        total_tokens_used = sum(record.tokens_used for record in monthly_usage)
        usage_percentage = (total_tokens_used / developer.api_quota_limit) * 100 if developer.api_quota_limit > 0 else 0

        # 配额使用告警
        if usage_percentage >= 90:
            alerts.append({
                "type": "quota_warning",
                "severity": "high" if usage_percentage >= 95 else "medium",
                "message": f"月度配额使用已达到 {usage_percentage:.1f}%",
                "used": total_tokens_used,
                "limit": developer.api_quota_limit,
                "percentage": usage_percentage
            })

        # 检查异常使用模式
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_usage = await self.db.query(APIUsageRecord).filter(
            and_(
                APIUsageRecord.developer_id == developer_id,
                APIUsageRecord.created_at >= last_24h
            )
        ).all()

        # 24小时内错误率告警
        if recent_usage:
            error_count = sum(1 for record in recent_usage if record.status_code >= 400)
            error_rate = (error_count / len(recent_usage)) * 100

            if error_rate > 10:  # 错误率超过10%
                alerts.append({
                    "type": "high_error_rate",
                    "severity": "medium" if error_rate < 20 else "high",
                    "message": f"24小时内错误率过高: {error_rate:.1f}%",
                    "error_rate": error_rate,
                    "total_requests": len(recent_usage),
                    "errors": error_count
                })

        # 检查API密钥使用情况
        api_keys = await self.db.query(DeveloperAPIKey).filter(
            and_(
                DeveloperAPIKey.developer_id == developer_id,
                DeveloperAPIKey.is_active == True
            )
        ).all()

        unused_keys = []
        for key in api_keys:
            key_usage = await self.db.query(APIUsageRecord).filter(
                and_(
                    APIUsageRecord.api_key_id == key.id,
                    APIUsageRecord.created_at >= last_24h
                )
            ).count()

            if key_usage == 0:
                unused_keys.append(key.name)

        if unused_keys:
            alerts.append({
                "type": "unused_keys",
                "severity": "low",
                "message": f"有 {len(unused_keys)} 个API密钥在24小时内未使用",
                "unused_keys": unused_keys
            })

        return alerts