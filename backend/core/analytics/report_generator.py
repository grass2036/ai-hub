"""
报告生成器
Report Generator Module

提供企业级报告生成功能，包括：
- 自动化报告生成
- 定期运营报告
- 异常行为检测报告
- 业务趋势预测报告
- 自定义报告模板
- 多格式导出（PDF、Excel、JSON）
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid
from enum import Enum
import io
import base64

from backend.config.settings import get_settings
from backend.core.cache.multi_level_cache import cache_manager
from backend.core.analytics.business_analytics import business_analytics
from backend.core.analytics.user_behavior import user_behavior_analytics

settings = get_settings()
logger = logging.getLogger(__name__)


class ReportType(Enum):
    """报告类型枚举"""
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_BUSINESS = "weekly_business"
    MONTHLY_ANALYTICS = "monthly_analytics"
    USER_BEHAVIOR = "user_behavior"
    PERFORMANCE_METRICS = "performance_metrics"
    ANOMALY_DETECTION = "anomaly_detection"
    CUSTOM = "custom"


class ReportFormat(Enum):
    """报告格式枚举"""
    JSON = "json"
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"


@dataclass
class ReportTemplate:
    """报告模板数据结构"""
    template_id: str
    name: str
    description: str
    report_type: ReportType
    sections: List[Dict[str, Any]]
    schedule_config: Optional[Dict[str, Any]]
    recipients: List[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class GeneratedReport:
    """生成的报告数据结构"""
    report_id: str
    template_id: str
    report_type: ReportType
    title: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    data: Dict[str, Any]
    metrics_summary: Dict[str, Any]
    insights: List[str]
    recommendations: List[str]
    file_path: Optional[str]
    file_format: ReportFormat
    status: str  # generating, completed, failed


@dataclass
class ReportSchedule:
    """报告计划数据结构"""
    schedule_id: str
    template_id: str
    name: str
    frequency: str  # daily, weekly, monthly
    next_run: datetime
    recipients: List[str]
    enabled: bool
    last_run: Optional[datetime]
    created_at: datetime


class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        self.cache_key_prefix = "report_generator"
        self.data_dir = Path("data/analytics/reports")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 存储路径
        self.templates_path = self.data_dir / "templates.json"
        self.reports_path = self.data_dir / "generated_reports"
        self.reports_path.mkdir(exist_ok=True)
        self.schedules_path = self.data_dir / "schedules.json"

        # 默认模板
        self.default_templates = self._create_default_templates()

    async def generate_report(
        self,
        report_type: Union[ReportType, str],
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        template_id: Optional[str] = None,
        format: ReportFormat = ReportFormat.JSON
    ) -> GeneratedReport:
        """
        生成报告

        Args:
            report_type: 报告类型
            period_start: 开始时间
            period_end: 结束时间
            template_id: 模板ID
            format: 报告格式

        Returns:
            GeneratedReport: 生成的报告
        """
        try:
            if isinstance(report_type, str):
                report_type = ReportType(report_type)

            if not period_start:
                period_start = datetime.now() - timedelta(days=1)
            if not period_end:
                period_end = datetime.now()

            report_id = str(uuid.uuid4())
            logger.info(f"Generating report {report_id}: {report_type.value}")

            # 创建报告对象
            report = GeneratedReport(
                report_id=report_id,
                template_id=template_id or f"default_{report_type.value}",
                report_type=report_type,
                title=self._get_report_title(report_type, period_start, period_end),
                generated_at=datetime.now(),
                period_start=period_start,
                period_end=period_end,
                data={},
                metrics_summary={},
                insights=[],
                recommendations=[],
                file_path=None,
                file_format=format,
                status="generating"
            )

            # 生成报告数据
            report_data = await self._generate_report_data(report_type, period_start, period_end)
            report.data = report_data["data"]
            report.metrics_summary = report_data["metrics_summary"]
            report.insights = report_data["insights"]
            report.recommendations = report_data["recommendations"]

            # 生成文件
            if format != ReportFormat.JSON:
                file_path = await self._export_report(report, format)
                report.file_path = file_path

            report.status = "completed"

            # 保存报告
            await self._save_report(report)

            logger.info(f"Report {report_id} generated successfully")
            return report

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            if 'report' in locals():
                report.status = "failed"
                await self._save_report(report)
            raise

    async def create_template(
        self,
        name: str,
        description: str,
        report_type: ReportType,
        sections: List[Dict[str, Any]],
        schedule_config: Optional[Dict[str, Any]] = None,
        recipients: Optional[List[str]] = None
    ) -> ReportTemplate:
        """
        创建报告模板

        Args:
            name: 模板名称
            description: 描述
            report_type: 报告类型
            sections: 报告章节配置
            schedule_config: 计划配置
            recipients: 收件人列表

        Returns:
            ReportTemplate: 创建的模板
        """
        try:
            template_id = str(uuid.uuid4())
            template = ReportTemplate(
                template_id=template_id,
                name=name,
                description=description,
                report_type=report_type,
                sections=sections,
                schedule_config=schedule_config,
                recipients=recipients or [],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

            # 保存模板
            await self._save_template(template)

            logger.info(f"Report template created: {template_id}")
            return template

        except Exception as e:
            logger.error(f"Error creating template: {e}")
            raise

    async def schedule_report(
        self,
        template_id: str,
        name: str,
        frequency: str,
        recipients: List[str],
        enabled: bool = True
    ) -> ReportSchedule:
        """
        计划报告生成

        Args:
            template_id: 模板ID
            name: 计划名称
            frequency: 频率 (daily, weekly, monthly)
            recipients: 收件人列表
            enabled: 是否启用

        Returns:
            ReportSchedule: 创建的计划
        """
        try:
            schedule_id = str(uuid.uuid4())
            next_run = self._calculate_next_run(frequency)

            schedule = ReportSchedule(
                schedule_id=schedule_id,
                template_id=template_id,
                name=name,
                frequency=frequency,
                next_run=next_run,
                recipients=recipients,
                enabled=enabled,
                last_run=None,
                created_at=datetime.now()
            )

            # 保存计划
            await self._save_schedule(schedule)

            logger.info(f"Report scheduled: {schedule_id}, next run: {next_run}")
            return schedule

        except Exception as e:
            logger.error(f"Error scheduling report: {e}")
            raise

    async def get_report(self, report_id: str) -> Optional[GeneratedReport]:
        """
        获取报告

        Args:
            report_id: 报告ID

        Returns:
            Optional[GeneratedReport]: 报告对象
        """
        try:
            report_file = self.reports_path / f"{report_id}.json"
            if not report_file.exists():
                return None

            with open(report_file, 'r') as f:
                report_data = json.load(f)

            # 转换数据类型
            report_data["report_type"] = ReportType(report_data["report_type"])
            report_data["file_format"] = ReportFormat(report_data["file_format"])
            report_data["generated_at"] = datetime.fromisoformat(report_data["generated_at"])
            report_data["period_start"] = datetime.fromisoformat(report_data["period_start"])
            report_data["period_end"] = datetime.fromisoformat(report_data["period_end"])

            return GeneratedReport(**report_data)

        except Exception as e:
            logger.error(f"Error getting report {report_id}: {e}")
            return None

    async def list_reports(
        self,
        report_type: Optional[ReportType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[GeneratedReport]:
        """
        列出报告

        Args:
            report_type: 报告类型过滤
            limit: 限制数量
            offset: 偏移量

        Returns:
            List[GeneratedReport]: 报告列表
        """
        try:
            reports = []
            report_files = list(self.reports_path.glob("*.json"))

            # 排序并分页
            report_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            paginated_files = report_files[offset:offset + limit]

            for file_path in paginated_files:
                try:
                    with open(file_path, 'r') as f:
                        report_data = json.load(f)

                    # 类型过滤
                    if report_type and ReportType(report_data["report_type"]) != report_type:
                        continue

                    # 转换数据类型
                    report_data["report_type"] = ReportType(report_data["report_type"])
                    report_data["file_format"] = ReportFormat(report_data["file_format"])
                    report_data["generated_at"] = datetime.fromisoformat(report_data["generated_at"])
                    report_data["period_start"] = datetime.fromisoformat(report_data["period_start"])
                    report_data["period_end"] = datetime.fromisoformat(report_data["period_end"])

                    reports.append(GeneratedReport(**report_data))

                except Exception as e:
                    logger.error(f"Error loading report from {file_path}: {e}")
                    continue

            return reports

        except Exception as e:
            logger.error(f"Error listing reports: {e}")
            return []

    async def delete_report(self, report_id: str) -> bool:
        """
        删除报告

        Args:
            report_id: 报告ID

        Returns:
            bool: 是否删除成功
        """
        try:
            report_file = self.reports_path / f"{report_id}.json"
            if report_file.exists():
                report_file.unlink()

                # 删除导出的文件
                for ext in ["pdf", "xlsx", "html"]:
                    export_file = self.reports_path / f"{report_id}.{ext}"
                    if export_file.exists():
                        export_file.unlink()

                logger.info(f"Report {report_id} deleted")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting report {report_id}: {e}")
            return False

    # 私有辅助方法

    def _create_default_templates(self) -> Dict[str, ReportTemplate]:
        """创建默认模板"""
        templates = {}

        # 日报模板
        templates["daily_summary"] = ReportTemplate(
            template_id="daily_summary",
            name="每日运营报告",
            description="每日系统运营概况和关键指标",
            report_type=ReportType.DAILY_SUMMARY,
            sections=[
                {"title": "关键指标概览", "type": "metrics", "metrics": ["revenue", "users", "api_calls"]},
                {"title": "用户活跃度", "type": "chart", "chart_type": "line"},
                {"title": "错误分析", "type": "table"},
                {"title": "系统性能", "type": "metrics", "metrics": ["response_time", "uptime"]}
            ],
            schedule_config={"frequency": "daily", "time": "09:00"},
            recipients=["admin@company.com"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # 周报模板
        templates["weekly_business"] = ReportTemplate(
            template_id="weekly_business",
            name="每周业务报告",
            description="每周��务表现和趋势分析",
            report_type=ReportType.WEEKLY_BUSINESS,
            sections=[
                {"title": "收入分析", "type": "chart", "chart_type": "bar"},
                {"title": "用户增长", "type": "chart", "chart_type": "line"},
                {"title": "功能使用排行", "type": "table"},
                {"title": "转化漏斗分析", "type": "funnel"},
                {"title": "建议和行动计划", "type": "insights"}
            ],
            schedule_config={"frequency": "weekly", "day": "monday", "time": "10:00"},
            recipients=["business@company.com"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        return templates

    def _get_report_title(self, report_type: ReportType, start: datetime, end: datetime) -> str:
        """获取报告标题"""
        titles = {
            ReportType.DAILY_SUMMARY: f"每日运营报告 - {start.strftime('%Y-%m-%d')}",
            ReportType.WEEKLY_BUSINESS: f"每周业务报告 - {start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}",
            ReportType.MONTHLY_ANALYTICS: f"月度分析报告 - {start.strftime('%Y年%m月')}",
            ReportType.USER_BEHAVIOR: f"用户行为分析报告 - {start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}",
            ReportType.PERFORMANCE_METRICS: f"性能指标报告 - {start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}",
            ReportType.ANOMALY_DETECTION: f"异常检测报告 - {start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}",
            ReportType.CUSTOM: "自定义报告"
        }
        return titles.get(report_type, "分析报告")

    async def _generate_report_data(
        self,
        report_type: ReportType,
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """生成报告数据"""
        if report_type == ReportType.DAILY_SUMMARY:
            return await self._generate_daily_summary(start, end)
        elif report_type == ReportType.WEEKLY_BUSINESS:
            return await self._generate_weekly_business(start, end)
        elif report_type == ReportType.MONTHLY_ANALYTICS:
            return await self._generate_monthly_analytics(start, end)
        elif report_type == ReportType.USER_BEHAVIOR:
            return await self._generate_user_behavior_report(start, end)
        elif report_type == ReportType.PERFORMANCE_METRICS:
            return await self._generate_performance_metrics(start, end)
        elif report_type == ReportType.ANOMALY_DETECTION:
            return await self._generate_anomaly_detection(start, end)
        else:
            return {"data": {}, "metrics_summary": {}, "insights": [], "recommendations": []}

    async def _generate_daily_summary(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """生成日报数据"""
        # 获取各项指标
        revenue_metrics = await business_analytics.calculate_revenue_metrics(start, end)
        user_metrics = await business_analytics.calculate_user_metrics(start, end)
        usage_metrics = await business_analytics.calculate_usage_metrics(start, end)

        # 生成洞察
        insights = [
            f"今日收入: ${revenue_metrics.daily_revenue:.2f}",
            f"活跃用户: {user_metrics.active_users}",
            f"API调用: {usage_metrics.daily_api_calls} 次"
        ]

        recommendations = []
        if usage_metrics.error_rate > 0.05:
            recommendations.append("系统错误率较高，建议检查系统状态")
        if user_metrics.user_growth_rate < 0.02:
            recommendations.append("用户增长缓慢，建议加强推广活动")

        return {
            "data": {
                "revenue": asdict(revenue_metrics),
                "users": asdict(user_metrics),
                "usage": asdict(usage_metrics)
            },
            "metrics_summary": {
                "total_revenue": float(revenue_metrics.daily_revenue),
                "active_users": user_metrics.active_users,
                "api_calls": usage_metrics.daily_api_calls,
                "error_rate": usage_metrics.error_rate
            },
            "insights": insights,
            "recommendations": recommendations
        }

    async def _generate_weekly_business(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """生成周报数据"""
        # 获取一周的数据
        revenue_metrics = await business_analytics.calculate_revenue_metrics(start, end)
        user_metrics = await business_analytics.calculate_user_metrics(start, end)
        usage_metrics = await business_analytics.calculate_usage_metrics(start, end)
        business_insights = await business_analytics.generate_business_insights(
            revenue_metrics, user_metrics, usage_metrics
        )

        # 用户行为分析
        behavior_metrics = await user_behavior_analytics.calculate_behavior_metrics(start, end)

        return {
            "data": {
                "revenue": asdict(revenue_metrics),
                "users": asdict(user_metrics),
                "usage": asdict(usage_metrics),
                "behavior": asdict(behavior_metrics),
                "insights": asdict(business_insights)
            },
            "metrics_summary": {
                "weekly_revenue": float(revenue_metrics.monthly_revenue),
                "user_growth": user_metrics.user_growth_rate,
                "usage_growth": usage_metrics.usage_growth_rate,
                "revenue_growth": revenue_metrics.revenue_growth_rate
            },
            "insights": business_insights.key_insights,
            "recommendations": business_insights.recommendations
        }

    async def _generate_monthly_analytics(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """生成月度分析数据"""
        # 综合分析
        revenue_metrics = await business_analytics.calculate_revenue_metrics(start, end)
        user_metrics = await business_analytics.calculate_user_metrics(start, end)
        usage_metrics = await business_analytics.calculate_usage_metrics(start, end)

        # 趋势分析
        trends = await self._analyze_monthly_trends(start, end)

        return {
            "data": {
                "revenue": asdict(revenue_metrics),
                "users": asdict(user_metrics),
                "usage": asdict(usage_metrics),
                "trends": trends
            },
            "metrics_summary": {
                "monthly_revenue": float(revenue_metrics.monthly_revenue),
                "total_users": user_metrics.total_users,
                "avg_daily_usage": usage_metrics.daily_api_calls,
                "retention_rate": user_metrics.user_retention_rate
            },
            "insights": [
                f"月度收入增长 {revenue_metrics.revenue_growth_rate:.1%}",
                f"用户留存率 {user_metrics.user_retention_rate:.1%}",
                f"平均响应时间 {usage_metrics.average_response_time:.2f}s"
            ],
            "recommendations": [
                "继续优化高使用量模型的服务质量",
                "关注用户留存率变化趋势",
                "监控系统性能指标"
            ]
        }

    async def _generate_user_behavior_report(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """生成用户行为报告"""
        behavior_metrics = await user_behavior_analytics.calculate_behavior_metrics(start, end)
        personas = await user_behavior_analytics.generate_user_personas()
        anomalies = await user_behavior_analytics.detect_behavior_anomalies()

        return {
            "data": {
                "behavior_metrics": asdict(behavior_metrics),
                "personas": [asdict(persona) for persona in personas],
                "anomalies": [asdict(anomaly) for anomaly in anomalies]
            },
            "metrics_summary": {
                "avg_session_duration": behavior_metrics.avg_session_duration,
                "bounce_rate": behavior_metrics.bounce_rate,
                "return_user_rate": behavior_metrics.return_user_rate,
                "active_users": behavior_metrics.daily_active_users
            },
            "insights": [
                f"平均会话时长: {behavior_metrics.avg_session_duration:.1f}秒",
                f"跳出率: {behavior_metrics.bounce_rate:.1%}",
                f"回访用户率: {behavior_metrics.return_user_rate:.1%}"
            ],
            "recommendations": [
                "优化用户体验以降低跳出率",
                "提升用户参与度和留存率",
                "关注异常行为模式"
            ]
        }

    async def _generate_performance_metrics(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """生成性能指标报告"""
        usage_metrics = await business_analytics.calculate_usage_metrics(start, end)

        return {
            "data": {
                "usage": asdict(usage_metrics),
                "performance": {
                    "avg_response_time": usage_metrics.average_response_time,
                    "error_rate": usage_metrics.error_rate,
                    "throughput": usage_metrics.daily_api_calls
                }
            },
            "metrics_summary": {
                "response_time": usage_metrics.average_response_time,
                "error_rate": usage_metrics.error_rate,
                "throughput": usage_metrics.daily_api_calls,
                "availability": 1 - usage_metrics.error_rate
            },
            "insights": [
                f"平均响应时间: {usage_metrics.average_response_time:.2f}秒",
                f"系统可用性: {(1-usage_metrics.error_rate):.2%}",
                f"日处理请求: {usage_metrics.daily_api_calls} 次"
            ],
            "recommendations": [
                "监控系统响应时间变化",
                "优化错误处理机制",
                "提升系统吞吐量"
            ]
        }

    async def _generate_anomaly_detection(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """生成异常检测报告"""
        anomalies = await user_behavior_analytics.detect_behavior_anomalies()

        # 按严重程度分组
        anomaly_counts = {}
        for anomaly in anomalies:
            severity = anomaly.severity
            if severity not in anomaly_counts:
                anomaly_counts[severity] = 0
            anomaly_counts[severity] += 1

        return {
            "data": {
                "anomalies": [asdict(anomaly) for anomaly in anomalies],
                "summary": anomaly_counts
            },
            "metrics_summary": {
                "total_anomalies": len(anomalies),
                "critical_anomalies": anomaly_counts.get("critical", 0),
                "high_anomalies": anomaly_counts.get("high", 0),
                "medium_anomalies": anomaly_counts.get("medium", 0)
            },
            "insights": [
                f"检测到 {len(anomalies)} 个异常行为",
                f"严重异常: {anomaly_counts.get('critical', 0)} 个",
                f"高级异常: {anomaly_counts.get('high', 0)} 个"
            ],
            "recommendations": [
                "立即处理严重和高级异常",
                "定期审查中等异常",
                "优化异常检测规则"
            ]
        }

    async def _analyze_monthly_trends(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """分析月度趋势"""
        # TODO: 实现趋势分析逻辑
        return {
            "revenue_trend": "increasing",
            "user_trend": "stable",
            "usage_trend": "increasing",
            "performance_trend": "stable"
        }

    async def _export_report(self, report: GeneratedReport, format: ReportFormat) -> str:
        """导出报告到文件"""
        file_path = self.reports_path / f"{report.report_id}.{format.value}"

        try:
            if format == ReportFormat.PDF:
                # TODO: 实现PDF导出
                await self._export_to_pdf(report, file_path)
            elif format == ReportFormat.EXCEL:
                # TODO: 实现Excel导出
                await self._export_to_excel(report, file_path)
            elif format == ReportFormat.HTML:
                # TODO: 实现HTML导出
                await self._export_to_html(report, file_path)

            return str(file_path)

        except Exception as e:
            logger.error(f"Error exporting report to {format.value}: {e}")
            raise

    async def _export_to_pdf(self, report: GeneratedReport, file_path: Path):
        """导出为PDF"""
        # TODO: 实现PDF导出逻辑
        logger.info(f"PDF export not implemented yet: {file_path}")

    async def _export_to_excel(self, report: GeneratedReport, file_path: Path):
        """导出为Excel"""
        # TODO: 实现Excel导出逻辑
        logger.info(f"Excel export not implemented yet: {file_path}")

    async def _export_to_html(self, report: GeneratedReport, file_path: Path):
        """导出为HTML"""
        # TODO: 实现HTML导出逻辑
        logger.info(f"HTML export not implemented yet: {file_path}")

    def _calculate_next_run(self, frequency: str) -> datetime:
        """计算下次运行时间"""
        now = datetime.now()

        if frequency == "daily":
            return now + timedelta(days=1)
        elif frequency == "weekly":
            return now + timedelta(weeks=1)
        elif frequency == "monthly":
            return now + timedelta(days=30)
        else:
            return now + timedelta(days=1)

    async def _save_report(self, report: GeneratedReport):
        """保存报告到文件"""
        try:
            report_file = self.reports_path / f"{report.report_id}.json"

            # 转换为可序列化格式
            report_data = asdict(report)
            report_data["report_type"] = report.report_type.value
            report_data["file_format"] = report.file_format.value
            report_data["generated_at"] = report.generated_at.isoformat()
            report_data["period_start"] = report.period_start.isoformat()
            report_data["period_end"] = report.period_end.isoformat()

            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error saving report: {e}")

    async def _save_template(self, template: ReportTemplate):
        """保存模板到文件"""
        try:
            templates = {}

            # 读取现有模板
            if self.templates_path.exists():
                with open(self.templates_path, 'r') as f:
                    templates = json.load(f)

            # 添加新模板
            template_data = asdict(template)
            template_data["report_type"] = template.report_type.value
            template_data["created_at"] = template.created_at.isoformat()
            template_data["updated_at"] = template.updated_at.isoformat()

            templates[template.template_id] = template_data

            # 保存模板
            with open(self.templates_path, 'w') as f:
                json.dump(templates, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error saving template: {e}")

    async def _save_schedule(self, schedule: ReportSchedule):
        """保存计划到文件"""
        try:
            schedules = []

            # 读取现有计划
            if self.schedules_path.exists():
                with open(self.schedules_path, 'r') as f:
                    schedules = json.load(f)

            # 添加新计划
            schedule_data = asdict(schedule)
            schedule_data["next_run"] = schedule.next_run.isoformat()
            if schedule.last_run:
                schedule_data["last_run"] = schedule.last_run.isoformat()
            schedule_data["created_at"] = schedule.created_at.isoformat()

            schedules.append(schedule_data)

            # 保存计划
            with open(self.schedules_path, 'w') as f:
                json.dump(schedules, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error saving schedule: {e}")


# 全局实例
report_generator = ReportGenerator()