"""
发票生成器

提供发票生成、PDF导出、账单管理等功能。
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from decimal import Decimal
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class InvoiceLineItem:
    """发票项目"""
    description: str
    quantity: int
    unit_price: float
    amount: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "amount": self.amount,
            "metadata": self.metadata
        }


@dataclass
class InvoiceTemplate:
    """发票模板"""
    company_name: str
    company_address: str
    company_phone: str
    company_email: str
    company_tax_id: str
    logo_url: Optional[str] = None
    footer_text: str = "感谢您的业务！"
    currency_symbol: str = "$"
    tax_rate: float = 0.08  # 8% 税率

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "company_name": self.company_name,
            "company_address": self.company_address,
            "company_phone": self.company_phone,
            "company_email": self.company_email,
            "company_tax_id": self.company_tax_id,
            "logo_url": self.logo_url,
            "footer_text": self.footer_text,
            "currency_symbol": self.currency_symbol,
            "tax_rate": self.tax_rate
        }


class InvoiceGenerator:
    """发票生成器"""

    def __init__(self, storage_backend=None):
        """
        初始化发票生成器

        Args:
            storage_backend: 存储后端（数据库/文件系统）
        """
        self.storage = storage_backend

        # 发票模板配置
        self.template = InvoiceTemplate(
            company_name="AI Hub Platform Inc.",
            company_address="123 Tech Street, San Francisco, CA 94105",
            company_phone="+1 (555) 123-4567",
            company_email="billing@aihub.com",
            company_tax_id="US-123456789",
            logo_url="https://aihub.com/logo.png",
            footer_text="如有任何问题，请联系我们的客服团队。",
            currency_symbol="$",
            tax_rate=0.08
        )

    async def generate_monthly_invoice(
        self,
        user_id: str,
        subscription_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        生成月度发票

        Args:
            user_id: 用户ID
            subscription_id: 订阅ID
            period_start: 开始时间
            period_end: 结束时间

        Returns:
            发票数据或None
        """
        try:
            # 获取用户信息
            user = await self._get_user(user_id)
            if not user:
                logger.error(f"用户不存在: {user_id}")
                return None

            # 获取订阅信息
            subscription = await self._get_subscription(subscription_id)
            if not subscription:
                logger.error(f"订阅不存在: {subscription_id}")
                return None

            # 获取价格计划信息
            plan = await self._get_pricing_plan(subscription.plan_id)
            if not plan:
                logger.error(f"价格计划不存在: {subscription.plan_id}")
                return None

            # 计算使用量费用
            usage_charges = await self._calculate_usage_charges(
                user_id, period_start, period_end
            )

            # 构建发票项目
            line_items = []

            # 基础订阅费用
            base_amount = plan.price
            if subscription.billing_cycle.value == "yearly":
                base_amount = base_amount / 12  # 月度分摊

            line_items.append(InvoiceLineItem(
                description=f"{plan.name} - {subscription.billing_cycle.value.title()} Subscription",
                quantity=1,
                unit_price=base_amount,
                amount=base_amount
            ))

            # 使用量超限费用
            if usage_charges.get("overage_amount", 0) > 0:
                line_items.append(InvoiceLineItem(
                    description="API调用超限费用",
                    quantity=usage_charges.get("overage_requests", 0),
                    unit_price=usage_charges.get("overage_rate", 0),
                    amount=usage_charges.get("overage_amount", 0)
                ))

            # 计算小计
            subtotal = sum(item.amount for item in line_items)

            # 计算税费
            tax_amount = subtotal * self.template.tax_rate
            total_amount = subtotal + tax_amount

            # 生成发票号
            invoice_number = await self._generate_invoice_number()

            # 创建发票数据
            invoice_data = {
                "invoice_number": invoice_number,
                "user_id": user_id,
                "subscription_id": subscription_id,
                "customer": {
                    "name": user.get("name", ""),
                    "email": user.get("email", ""),
                    "address": user.get("address", ""),
                    "phone": user.get("phone", "")
                },
                "company": self.template.to_dict(),
                "period": {
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat(),
                    "type": "monthly"
                },
                "line_items": [item.to_dict() for item in line_items],
                "amounts": {
                    "subtotal": round(subtotal, 2),
                    "tax_amount": round(tax_amount, 2),
                    "total_amount": round(total_amount, 2),
                    "currency": "USD"
                },
                "usage_summary": {
                    "total_requests": usage_charges.get("total_requests", 0),
                    "total_tokens": usage_charges.get("total_tokens", 0),
                    "overage_requests": usage_charges.get("overage_requests", 0)
                },
                "dates": {
                    "issued_at": datetime.now(timezone.utc).isoformat(),
                    "due_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                },
                "metadata": {
                    "generated_by": "invoice_generator",
                    "plan_type": plan.type.value,
                    "subscription_status": subscription.status.value
                }
            }

            # 保存发票到数据库
            saved_invoice = await self._save_invoice(invoice_data)
            if saved_invoice:
                invoice_data["id"] = saved_invoice["id"]
                invoice_data["status"] = saved_invoice["status"]

            logger.info(f"生成月度发票成功: {invoice_number} for user {user_id}")
            return invoice_data

        except Exception as e:
            logger.error(f"生成月度发票失败: {e}")
            return None

    async def generate_usage_invoice(
        self,
        user_id: str,
        usage_data: Dict[str, Any],
        description: str = "API使用量账单"
    ) -> Optional[Dict[str, Any]]:
        """
        生成使用量发票

        Args:
            user_id: 用户ID
            usage_data: 使用量数据
            description: 发票描述

        Returns:
            发票数据或None
        """
        try:
            # 获取用户信息
            user = await self._get_user(user_id)
            if not user:
                return None

            # 构建发票项目
            line_items = []

            # API调用费用
            if usage_data.get("api_calls", 0) > 0:
                line_items.append(InvoiceLineItem(
                    description="API调用费用",
                    quantity=usage_data.get("api_calls", 0),
                    unit_price=usage_data.get("api_call_rate", 0),
                    amount=usage_data.get("api_calls_cost", 0)
                ))

            # Token使用费用
            if usage_data.get("tokens", 0) > 0:
                line_items.append(InvoiceLineItem(
                    description="Token使用费用",
                    quantity=usage_data.get("tokens", 0),
                    unit_price=usage_data.get("token_rate", 0),
                    amount=usage_data.get("tokens_cost", 0)
                ))

            # 存储费用
            if usage_data.get("storage_gb", 0) > 0:
                line_items.append(InvoiceLineItem(
                    description="存储费用",
                    quantity=usage_data.get("storage_gb", 0),
                    unit_price=usage_data.get("storage_rate", 0),
                    amount=usage_data.get("storage_cost", 0)
                ))

            # 计算金额
            subtotal = sum(item.amount for item in line_items)
            tax_amount = subtotal * self.template.tax_rate
            total_amount = subtotal + tax_amount

            # 生成发票号
            invoice_number = await self._generate_invoice_number(prefix="USAGE")

            # 创建发票数据
            invoice_data = {
                "invoice_number": invoice_number,
                "user_id": user_id,
                "customer": {
                    "name": user.get("name", ""),
                    "email": user.get("email", ""),
                    "address": user.get("address", ""),
                    "phone": user.get("phone", "")
                },
                "company": self.template.to_dict(),
                "description": description,
                "line_items": [item.to_dict() for item in line_items],
                "amounts": {
                    "subtotal": round(subtotal, 2),
                    "tax_amount": round(tax_amount, 2),
                    "total_amount": round(total_amount, 2),
                    "currency": "USD"
                },
                "dates": {
                    "issued_at": datetime.now(timezone.utc).isoformat(),
                    "due_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
                },
                "metadata": {
                    "generated_by": "invoice_generator",
                    "invoice_type": "usage"
                }
            }

            # 保存发票到数据库
            saved_invoice = await self._save_invoice(invoice_data)
            if saved_invoice:
                invoice_data["id"] = saved_invoice["id"]
                invoice_data["status"] = saved_invoice["status"]

            logger.info(f"生成使用量发票成功: {invoice_number} for user {user_id}")
            return invoice_data

        except Exception as e:
            logger.error(f"生成使用量发票失败: {e}")
            return None

    async def generate_credit_invoice(
        self,
        user_id: str,
        amount: float,
        reason: str,
        related_invoice_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        生成信用发票（退款/调整）

        Args:
            user_id: 用户ID
            amount: 金额（负数表示退款）
            reason: 原因
            related_invoice_id: 相关发票ID

        Returns:
            发票数据或None
        """
        try:
            # 获取用户信息
            user = await self._get_user(user_id)
            if not user:
                return None

            # 构建发票项目
            line_items = [
                InvoiceLineItem(
                    description=reason,
                    quantity=1,
                    unit_price=amount,
                    amount=amount
                )
            ]

            # 计算税费（退款通常不计算税费）
            subtotal = amount
            tax_amount = 0.0
            total_amount = subtotal

            # 生成发票号
            invoice_number = await self._generate_invoice_number(prefix="CREDIT")

            # 创建发票数据
            invoice_data = {
                "invoice_number": invoice_number,
                "user_id": user_id,
                "related_invoice_id": related_invoice_id,
                "customer": {
                    "name": user.get("name", ""),
                    "email": user.get("email", ""),
                    "address": user.get("address", ""),
                    "phone": user.get("phone", "")
                },
                "company": self.template.to_dict(),
                "description": reason,
                "line_items": [item.to_dict() for item in line_items],
                "amounts": {
                    "subtotal": round(subtotal, 2),
                    "tax_amount": round(tax_amount, 2),
                    "total_amount": round(total_amount, 2),
                    "currency": "USD"
                },
                "dates": {
                    "issued_at": datetime.now(timezone.utc).isoformat(),
                    "due_at": datetime.now(timezone.utc).isoformat()  # 即时生效
                },
                "metadata": {
                    "generated_by": "invoice_generator",
                    "invoice_type": "credit",
                    "reason": reason
                }
            }

            # 保存发票到数据库
            saved_invoice = await self._save_invoice(invoice_data)
            if saved_invoice:
                invoice_data["id"] = saved_invoice["id"]
                invoice_data["status"] = saved_invoice["status"]

            logger.info(f"生成信用发票成功: {invoice_number} for user {user_id}")
            return invoice_data

        except Exception as e:
            logger.error(f"生成信用发票失败: {e}")
            return None

    async def get_invoice_pdf(
        self,
        invoice_id: str,
        template_path: Optional[str] = None
    ) -> Optional[bytes]:
        """
        生成发票PDF

        Args:
            invoice_id: 发票ID
            template_path: 模板文件路径

        Returns:
            PDF文件内容或None
        """
        try:
            # 获取发票数据
            invoice = await self._get_invoice(invoice_id)
            if not invoice:
                return None

            # 使用默认模板或指定模板
            template = template_path or self._get_default_template()

            # 生成HTML发票
            html_content = await self._render_invoice_html(invoice, template)

            # 转换为PDF
            pdf_content = await self._html_to_pdf(html_content)

            logger.info(f"生成发票PDF成功: {invoice_id}")
            return pdf_content

        except Exception as e:
            logger.error(f"生成发票PDF失败: {e}")
            return None

    async def preview_invoice(
        self,
        invoice_data: Dict[str, Any],
        template_path: Optional[str] = None
    ) -> Optional[str]:
        """
        预览发票HTML

        Args:
            invoice_data: 发票数据
            template_path: 模板文件路径

        Returns:
            HTML内容或None
        """
        try:
            template = template_path or self._get_default_template()
            html_content = await self._render_invoice_html(invoice_data, template)
            return html_content

        except Exception as e:
            logger.error(f"预览发票失败: {e}")
            return None

    # 私有方法

    async def _generate_invoice_number(self, prefix: str = "INV") -> str:
        """生成发票号"""
        # 格式: INV-YYYYMMDD-NNNN
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

        # 获取当日发票序号
        sequence = await self._get_invoice_sequence(date_str)

        return f"{prefix}-{date_str}-{sequence:04d}"

    async def _get_invoice_sequence(self, date_str: str) -> int:
        """获取发票序号"""
        # TODO: 实现数据库查询和序列号生成
        # 这里使用简单的内存计数器
        if not hasattr(self, '_invoice_sequences'):
            self._invoice_sequences = {}

        if date_str not in self._invoice_sequences:
            self._invoice_sequences[date_str] = 1
        else:
            self._invoice_sequences[date_str] += 1

        return self._invoice_sequences[date_str]

    async def _calculate_usage_charges(
        self,
        user_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> Dict[str, Any]:
        """计算使用量费用"""
        # TODO: 实现实际的使用量查询和费用计算
        # 返回示例数据
        return {
            "total_requests": 150,
            "total_tokens": 50000,
            "overage_requests": 50,
            "overage_rate": 0.002,
            "overage_amount": 0.10
        }

    async def _render_invoice_html(
        self,
        invoice_data: Dict[str, Any],
        template_path: str
    ) -> str:
        """渲染发票HTML"""
        # TODO: 实现模板渲染（可以使用Jinja2）
        # 这里返回简单的HTML示例
        return f"""
        <html>
        <head><title>Invoice {invoice_data['invoice_number']}</title></head>
        <body>
            <h1>Invoice {invoice_data['invoice_number']}</h1>
            <p>Customer: {invoice_data['customer']['name']}</p>
            <p>Total: {invoice_data['amounts']['total_amount']} {invoice_data['amounts']['currency']}</p>
        </body>
        </html>
        """

    async def _html_to_pdf(self, html_content: str) -> bytes:
        """将HTML转换为PDF"""
        # TODO: 实现PDF转换（可以使用WeasyPrint或pdfkit）
        # 这里返回模拟数据
        return html_content.encode('utf-8')

    def _get_default_template(self) -> str:
        """获取默认模板路径"""
        return os.path.join(
            os.path.dirname(__file__),
            "templates",
            "invoice.html"
        )

    # 数据库操作方法（需要根据实际存储后端实现）

    async def _save_invoice(self, invoice_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """保存发票到数据库"""
        # TODO: 实现数据库保存
        return {
            "id": "temp_invoice_id",
            "status": "draft"
        }

    async def _get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """从数据库获取发票"""
        # TODO: 实现数据库查询
        return None

    async def _get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        # TODO: 实现数据库查询
        return {
            "id": user_id,
            "name": "Test User",
            "email": "test@example.com",
            "address": "123 Test St",
            "phone": "+1-555-0123"
        }

    async def _get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """获取订阅信息"""
        # TODO: 实现数据库查询
        return {
            "id": subscription_id,
            "plan_id": "pro_monthly",
            "status": "active",
            "billing_cycle": "monthly"
        }

    async def _get_pricing_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """获取价格计划信息"""
        # TODO: 实现数据库查询
        return {
            "id": plan_id,
            "name": "Professional Plan",
            "type": "pro",
            "price": 29.0,
            "billing_cycle": "monthly"
        }