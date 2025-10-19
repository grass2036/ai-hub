"""
Billing and Invoicing Service
Week 4 Day 24: API Usage Statistics and Billing
"""

from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, extract
from decimal import Decimal, ROUND_HALF_UP

from backend.models.developer import Developer, APIUsageRecord
from backend.models.subscription import Subscription, Invoice, Payment

class BillingService:
    """计费和发票管理服务"""

    def __init__(self, db: Session):
        self.db = db

    def _get_model_pricing(self, model: str) -> Decimal:
        """获取模型定价（每1000 tokens的成本）"""
        pricing = {
            # OpenRouter定价（示例价格）
            "gpt-4o": Decimal("0.015"),
            "gpt-4o-mini": Decimal("0.00015"),
            "claude-3.5-sonnet": Decimal("0.003"),
            "claude-3.5-haiku": Decimal("0.00025"),
            "llama-3.1-70b": Decimal("0.001"),
            "llama-3.1-8b": Decimal("0.0002"),
            "gemini-1.5-pro": Decimal("0.0025"),
            "gemini-1.5-flash": Decimal("0.000075"),
            # 免费模型
            "deepseek-chat-v3.1:free": Decimal("0.0"),
            "grok-4-fast:free": Decimal("0.0"),
            # 默认价格
            "default": Decimal("0.001")
        }
        return pricing.get(model, pricing["default"])

    async def calculate_monthly_bill(
        self,
        developer_id: str,
        year: int,
        month: int
    ) -> Dict:
        """计算月度账单"""

        # 获取月份的开始和结束时间
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(microseconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(microseconds=1)

        # 查询该月的所有使用记录
        usage_records = await self.db.query(APIUsageRecord).filter(
            and_(
                APIUsageRecord.developer_id == developer_id,
                APIUsageRecord.created_at >= start_date,
                APIUsageRecord.created_at <= end_date
            )
        ).all()

        if not usage_records:
            return {
                "developer_id": developer_id,
                "year": year,
                "month": month,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "model_breakdown": {},
                "daily_breakdown": {},
                "status": "no_usage"
            }

        # 计算总体统计
        total_requests = len(usage_records)
        total_tokens = sum(record.tokens_used for record in usage_records)
        total_cost = Decimal("0")

        # 按模型统计
        model_breakdown = {}
        for record in usage_records:
            model = record.model or "unknown"
            if model not in model_breakdown:
                model_breakdown[model] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": Decimal("0")
                }

            # 计算成本
            cost_per_1k_tokens = self._get_model_pricing(model)
            cost = (Decimal(record.tokens_used) / Decimal("1000")) * cost_per_1k_tokens

            model_breakdown[model]["requests"] += 1
            model_breakdown[model]["tokens"] += record.tokens_used
            model_breakdown[model]["cost"] += cost
            total_cost += cost

        # 按日期统计
        daily_breakdown = {}
        for record in usage_records:
            date_key = record.created_at.date().isoformat()
            if date_key not in daily_breakdown:
                daily_breakdown[date_key] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": Decimal("0")
                }

            cost_per_1k_tokens = self._get_model_pricing(record.model or "default")
            cost = (Decimal(record.tokens_used) / Decimal("1000")) * cost_per_1k_tokens

            daily_breakdown[date_key]["requests"] += 1
            daily_breakdown[date_key]["tokens"] += record.tokens_used
            daily_breakdown[date_key]["cost"] += cost

        # 转换cost为float以便JSON序列化
        model_breakdown_float = {}
        for model, stats in model_breakdown.items():
            model_breakdown_float[model] = {
                "requests": stats["requests"],
                "tokens": stats["tokens"],
                "cost": float(stats["cost"].quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
            }

        daily_breakdown_float = {}
        for date, stats in daily_breakdown.items():
            daily_breakdown_float[date] = {
                "requests": stats["requests"],
                "tokens": stats["tokens"],
                "cost": float(stats["cost"].quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
            }

        return {
            "developer_id": developer_id,
            "year": year,
            "month": month,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost": float(total_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)),
            "model_breakdown": model_breakdown_float,
            "daily_breakdown": daily_breakdown_float,
            "status": "calculated"
        }

    async def generate_monthly_invoice(
        self,
        developer_id: str,
        year: int,
        month: int,
        auto_generate: bool = False
    ) -> Optional[Invoice]:
        """生成月度发票"""

        # 检查是否已经存在该月的发票
        existing_invoice = await self.db.query(Invoice).filter(
            and_(
                Invoice.developer_id == developer_id,
                Invoice.year == year,
                Invoice.month == month
            )
        ).first()

        if existing_invoice and not auto_generate:
            return existing_invoice

        # 计算账单
        bill_data = await self.calculate_monthly_bill(developer_id, year, month)

        if bill_data["total_cost"] == 0:
            # 无使用量，不生成发票
            return None

        # 获取开发者信息
        developer = await self.db.query(Developer).filter(
            Developer.id == developer_id
        ).first()

        if not developer:
            return None

        # 生成发票号
        invoice_number = f"INV-{year}{month:02d}-{developer_id[:8].upper()}"

        # 检查订阅信息（如果有）
        subscription = await self.db.query(Subscription).filter(
            and_(
                Subscription.developer_id == developer_id,
                Subscription.is_active == True
            )
        ).first()

        # 确定发票状态和到期日期
        status = "draft"  # 默认草稿状态
        due_date = date(year, month + 1, 15) if month < 12 else date(year + 1, 1, 15)

        # 如果是免费用户且使用量在免费配额内，标记为免费
        if developer.developer_type == "individual" and bill_data["total_tokens"] <= developer.api_quota_limit:
            status = "paid"  # 免费额度内，直接标记为已支付
            due_date = None

        # 创建发票
        if existing_invoice:
            # 更新现有发票
            existing_invoice.number = invoice_number
            existing_invoice.amount_due = Decimal(str(bill_data["total_cost"]))
            existing_invoice.amount_paid = Decimal(str(bill_data["total_cost"])) if status == "paid" else Decimal("0")
            existing_invoice.status = status
            existing_invoice.due_date = due_date
            existing_invoice.period_start = datetime.fromisoformat(bill_data["period_start"])
            existing_invoice.period_end = datetime.fromisoformat(bill_data["period_end"])
            existing_invoice.line_items = [
                {
                    "description": f"AI Hub API使用费 - {year}年{month}月",
                    "quantity": bill_data["total_tokens"],
                    "unit_price": Decimal("0.001"),  # 平均单价
                    "amount": Decimal(str(bill_data["total_cost"]))
                }
            ]
            await self.db.save(existing_invoice)
            return existing_invoice
        else:
            # 创建新发票
            invoice = Invoice(
                developer_id=developer_id,
                number=invoice_number,
                amount_due=Decimal(str(bill_data["total_cost"])),
                amount_paid=Decimal(str(bill_data["total_cost"])) if status == "paid" else Decimal("0"),
                currency="USD",
                status=status,
                due_date=due_date,
                period_start=datetime.fromisoformat(bill_data["period_start"]),
                period_end=datetime.fromisoformat(bill_data["period_end"]),
                line_items=[
                    {
                        "description": f"AI Hub API使用费 - {year}年{month}月",
                        "quantity": bill_data["total_tokens"],
                        "unit_price": Decimal("0.001"),
                        "amount": Decimal(str(bill_data["total_cost"]))
                    }
                ],
                metadata={
                    "total_requests": bill_data["total_requests"],
                    "model_breakdown": bill_data["model_breakdown"],
                    "daily_breakdown": bill_data["daily_breakdown"]
                }
            )

            await self.db.save(invoice)
            return invoice

    async def get_developer_billing_overview(
        self,
        developer_id: str,
        months: int = 12
    ) -> Dict:
        """获取开发者计费概览"""

        # 获取开发者信息
        developer = await self.db.query(Developer).filter(
            Developer.id == developer_id
        ).first()

        if not developer:
            raise ValueError("开发者不存在")

        # 获取订阅信息
        subscription = await self.db.query(Subscription).filter(
            and_(
                Subscription.developer_id == developer_id,
                Subscription.is_active == True
            )
        ).first()

        # 获取发票历史
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 30)

        invoices = await self.db.query(Invoice).filter(
            and_(
                Invoice.developer_id == developer_id,
                Invoice.created_at >= start_date,
                Invoice.created_at <= end_date
            )
        ).order_by(desc(Invoice.created_at)).all()

        # 计算统计信息
        total_invoices = len(invoices)
        total_amount_due = sum(invoice.amount_due for invoice in invoices)
        total_amount_paid = sum(invoice.amount_paid for invoice in invoices)
        outstanding_balance = total_amount_due - total_amount_paid

        # 按状态分组统计
        status_counts = {}
        for invoice in invoices:
            status = invoice.status
            status_counts[status] = status_counts.get(status, 0) + 1

        # 获取最近月份的使用情况
        current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_usage = await self.calculate_monthly_bill(
            developer_id,
            current_month.year,
            current_month.month
        )

        return {
            "developer_info": {
                "id": str(developer.id),
                "email": developer.email,
                "developer_type": developer.developer_type,
                "api_quota_limit": developer.api_quota_limit
            },
            "subscription": {
                "has_active_subscription": subscription is not None,
                "plan_name": subscription.plan_type if subscription else "Free",
                "monthly_quota": subscription.monthly_quota_limit if subscription else developer.api_quota_limit,
                "status": subscription.status if subscription else None
            },
            "billing_summary": {
                "total_invoices": total_invoices,
                "total_amount_due": float(total_amount_due),
                "total_amount_paid": float(total_amount_paid),
                "outstanding_balance": float(outstanding_balance),
                "status_counts": status_counts
            },
            "current_month_usage": current_month_usage,
            "recent_invoices": [
                {
                    "id": str(invoice.id),
                    "number": invoice.number,
                    "amount_due": float(invoice.amount_due),
                    "amount_paid": float(invoice.amount_paid),
                    "status": invoice.status,
                    "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                    "created_at": invoice.created_at.isoformat()
                }
                for invoice in invoices[:6]  # 最近6张发票
            ]
        }

    async def get_cost_optimization_suggestions(
        self,
        developer_id: str
    ) -> List[Dict]:
        """获取成本优化建议"""

        suggestions = []

        # 获取最近30天的使用数据
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

        usage_records = await self.db.query(APIUsageRecord).filter(
            and_(
                APIUsageRecord.developer_id == developer_id,
                APIUsageRecord.created_at >= start_date,
                APIUsageRecord.created_at <= end_date
            )
        ).all()

        if not usage_records:
            return [{
                "type": "no_usage",
                "priority": "info",
                "title": "暂无使用记录",
                "description": "开始使用API以获取成本优化建议",
                "potential_savings": 0
            }]

        # 分析模型使用情况
        model_costs = {}
        for record in usage_records:
            model = record.model or "unknown"
            if model not in model_costs:
                model_costs[model] = {
                    "tokens": 0,
                    "requests": 0,
                    "cost": Decimal("0")
                }

            cost_per_1k_tokens = self._get_model_pricing(model)
            cost = (Decimal(record.tokens_used) / Decimal("1000")) * cost_per_1k_tokens

            model_costs[model]["tokens"] += record.tokens_used
            model_costs[model]["requests"] += 1
            model_costs[model]["cost"] += cost

        # 按成本排序模型
        sorted_models = sorted(model_costs.items(), key=lambda x: x[1]["cost"], reverse=True)

        # 生成建议
        total_cost = sum(model["cost"] for model in model_costs.values())

        # 建议1: 如果使用了昂贵模��，建议使用更便宜的替代方案
        expensive_models = [model for model, data in sorted_models if data["cost"] > total_cost * 0.3]
        if expensive_models:
            for model, data in expensive_models:
                cheaper_alternatives = []

                if "gpt-4o" in model.lower():
                    cheaper_alternatives = {
                        "gpt-4o-mini": "成本降低99%",
                        "claude-3.5-haiku": "成本降低95%"
                    }
                elif "claude-3.5-sonnet" in model.lower():
                    cheaper_alternatives = {
                        "claude-3.5-haiku": "成本降低92%",
                        "gpt-4o-mini": "成本降低95%"
                    }

                if cheaper_alternatives:
                    savings = data["cost"] * Decimal("0.95")  # 假设95%的成本节省
                    suggestions.append({
                        "type": "model_optimization",
                        "priority": "high",
                        "title": f"优化 {model} 的使用",
                        "description": f"{model} 占用了您总成本的 {(data['cost']/total_cost)*100:.1f}%，考虑使用更便宜的替代方案。",
                        "details": {
                            "current_model": model,
                            "current_cost": float(data["cost"]),
                            "alternatives": cheaper_alternatives
                        },
                        "potential_savings": float(savings.quantize(Decimal("0.01")))
                    })

        # 建议2: 检查是否有免费模型可用
        has_paid_usage = any(model not in ["deepseek-chat-v3.1:free", "grok-4-fast:free"]
                          for model in model_costs.keys())

        if has_paid_usage and "deepseek-chat-v3.1:free" not in model_costs:
            suggestions.append({
                "type": "free_models",
                "priority": "medium",
                "title": "考虑使用免费模型",
                "description": "平台提供免费的AI模型，可以在测试和开发阶段大幅降低成本。",
                "details": {
                    "available_free_models": [
                        "deepseek-chat-v3.1:free",
                        "grok-4-fast:free"
                    ]
                },
                "potential_savings": total_cost * Decimal("0.8")  # 假设80%的成本节省
            })

        # 建议3: 检查使用模式
        daily_usage = {}
        for record in usage_records:
            date_key = record.created_at.date()
            if date_key not in daily_usage:
                daily_usage[date_key] = {"requests": 0, "cost": Decimal("0")}
            daily_usage[date_key]["requests"] += 1

            cost_per_1k_tokens = self._get_model_pricing(record.model or "default")
            cost = (Decimal(record.tokens_used) / Decimal("1000")) * cost_per_1k_tokens
            daily_usage[date_key]["cost"] += cost

        avg_daily_cost = sum(day["cost"] for day in daily_usage.values()) / len(daily_usage)
        high_usage_days = [day for day, data in daily_usage.items() if data["cost"] > avg_daily_cost * 2]

        if len(high_usage_days) > len(daily_usage) * 0.3:  # 30%以上的天使用量超过平均2倍
            suggestions.append({
                "type": "usage_pattern",
                "priority": "medium",
                "title": "优化使用模式",
                "description": f"您有 {len(high_usage_days)} 天的使用量超过平均水平的2倍，建议优化API调用模式或实施批量处理。",
                "details": {
                    "avg_daily_cost": float(avg_daily_cost),
                    "high_usage_days": len(high_usage_days),
                    "total_days": len(daily_usage)
                },
                "potential_savings": float(avg_daily_cost * Decimal("0.2") * len(high_usage_days))
            })

        # 建议4: 检查是否有大量小额请求
        request_sizes = [record.tokens_used for record in usage_records if record.tokens_used > 0]
        if request_sizes:
            avg_request_size = sum(request_sizes) / len(request_sizes)
            small_requests = [size for size in request_sizes if size < avg_request_size * 0.1]

            if len(small_requests) > len(request_sizes) * 0.5:  # 超过50%的请求都很小
                suggestions.append({
                    "type": "batch_processing",
                    "priority": "low",
                    "title": "考虑批量处理",
                    "description": f"您有 {len(small_requests)} 个小请求，考虑使用批量处理API可以提高效率并降低成本。",
                    "details": {
                        "small_requests_count": len(small_requests),
                        "total_requests": len(request_sizes),
                        "avg_request_size": avg_request_size
                    },
                    "potential_savings": float(total_cost * Decimal("0.1"))  # 假设10%的成本节省
                })

        return suggestions

    async def predict_monthly_bill(
        self,
        developer_id: str
    ) -> Dict:
        """预测当月账单"""

        current_date = datetime.utcnow()
        current_month_start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 获取本月至今的使用记录
        current_usage = await self.db.query(APIUsageRecord).filter(
            and_(
                APIUsageRecord.developer_id == developer_id,
                APIUsageRecord.created_at >= current_month_start,
                APIUsageRecord.created_at <= current_date
            )
        ).all()

        if not current_usage:
            return {
                "prediction": {
                    "estimated_monthly_tokens": 0,
                    "estimated_monthly_cost": 0.0,
                    "confidence": "low"
                },
                "current_usage": {
                    "tokens_used": 0,
                    "cost": 0.0,
                    "days_used": 0
                }
            }

        # 计算当前使用情况
        days_used = (current_date - current_month_start).days + 1
        tokens_used = sum(record.tokens_used for record in current_usage)

        current_cost = Decimal("0")
        for record in current_usage:
            cost_per_1k_tokens = self._get_model_pricing(record.model or "default")
            cost += (Decimal(record.tokens_used) / Decimal("1000")) * cost_per_1k_tokens

        # 计算平均每日使用量
        avg_daily_tokens = tokens_used / days_used
        avg_daily_cost = current_cost / days_used

        # 计算本月剩余天数
        days_in_month = (current_month_start.replace(month=current_month_start.month % 12 + 1, day=1) - current_month_start).days
        remaining_days = days_in_month - days_used

        # 预测本月总使用量
        estimated_monthly_tokens = int(tokens_used + (avg_daily_tokens * remaining_days))
        estimated_monthly_cost = float(current_cost + (avg_daily_cost * remaining_days))

        # 计算置信度
        confidence = "medium" if days_used >= 7 else "low"
        if days_used >= 20:
            confidence = "high"

        return {
            "prediction": {
                "estimated_monthly_tokens": estimated_monthly_tokens,
                "estimated_monthly_cost:": round(estimated_monthly_cost, 4),
                "confidence": confidence
            },
            "current_usage": {
                "tokens_used": tokens_used,
                "cost": float(current_cost),
                "days_used": days_used,
                "avg_daily_tokens": round(avg_daily_tokens),
                "avg_daily_cost": round(float(avg_daily_cost), 4)
            },
            "period": {
                "month_start": current_month_start.isoformat(),
                "current_date": current_date.isoformat(),
                "remaining_days": remaining_days,
                "total_days": days_in_month
            }
        }