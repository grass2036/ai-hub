"""
数据合规性处理模块
Data Compliance Processing Module

处理GDPR、CCPA、PIPEDA、LGPD等数据保护法规
Handles GDPR, CCPA, PIPEDA, LGPD and other data protection regulations
"""

import logging
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, asdict
from pydantic import BaseModel
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)

class ComplianceRegion(Enum):
    """合规区域枚举"""
    EU_GDPR = "eu_gdpr"
    US_CCPA = "us_ccpa"
    CA_PIPEDA = "ca_pipeda"
    BR_LGPD = "br_lgpd"
    SG_PDPA = "sg_pdpa"
    JP_APPI = "jp_appi"
    KR_PIPA = "kr_pipa"

class DataCategory(BaseModel):
    """数据类别"""
    category_id: str
    name: str
    sensitivity_level: str  # low, medium, high, critical
    retention_period_days: int
    requires_consent: bool
    encryption_required: bool
    audit_trail_required: bool

class ConsentRecord(BaseModel):
    """同意记录"""
    consent_id: str
    user_id: str
    data_categories: List[str]
    purposes: List[str]
    granted_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    legal_basis: str
    region: ComplianceRegion
    metadata: Dict[str, Any]

class DataProcessingRecord(BaseModel):
    """数据处理记录"""
    record_id: str
    user_id: str
    data_category: str
    operation: str  # create, read, update, delete, export
    purpose: str
    timestamp: datetime
    processor: str
    legal_basis: str
    region: ComplianceRegion
    ip_address: str
    user_agent: str

class SubjectRightsRequest(BaseModel):
    """数据主体权利请求"""
    request_id: str
    user_id: str
    request_type: str  # access, portability, erasure, rectification, objection
    region: ComplianceRegion
    status: str  # pending, processing, completed, rejected
    created_at: datetime
    processed_at: Optional[datetime]
    completed_at: Optional[datetime]
    reason: Optional[str]
    processor_notes: Optional[str]
    evidence: Dict[str, Any]

@dataclass
class ComplianceRule:
    """合规规则"""
    rule_id: str
    region: ComplianceRegion
    data_category: str
    requirement: str
    description: str
    implementation: str
    enabled: bool = True

class DataComplianceManager:
    """数据合规性管理器"""

    def __init__(self, storage_path: str = "data/compliance"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # 初始化数据类别
        self.data_categories = self._load_data_categories()

        # 初始化合规规则
        self.compliance_rules = self._load_compliance_rules()

        # 初始化区域配置
        self.region_configs = self._load_region_configs()

        logger.info("Data compliance manager initialized")

    def _load_data_categories(self) -> Dict[str, DataCategory]:
        """加载数据类别配置"""
        categories = {
            "personal_identification": DataCategory(
                category_id="personal_identification",
                name="Personal Identification",
                sensitivity_level="critical",
                retention_period_days=2555,  # 7 years
                requires_consent=True,
                encryption_required=True,
                audit_trail_required=True
            ),
            "contact_information": DataCategory(
                category_id="contact_information",
                name="Contact Information",
                sensitivity_level="high",
                retention_period_days=1825,  # 5 years
                requires_consent=True,
                encryption_required=True,
                audit_trail_required=True
            ),
            "financial_information": DataCategory(
                category_id="financial_information",
                name="Financial Information",
                sensitivity_level="critical",
                retention_period_days=2555,  # 7 years
                requires_consent=True,
                encryption_required=True,
                audit_trail_required=True
            ),
            "health_information": DataCategory(
                category_id="health_information",
                name="Health Information",
                sensitivity_level="critical",
                retention_period_days=2555,  # 7 years (HIPAA)
                requires_consent=True,
                encryption_required=True,
                audit_trail_required=True
            ),
            "usage_data": DataCategory(
                category_id="usage_data",
                name="Usage Data",
                sensitivity_level="medium",
                retention_period_days=365,  # 1 year
                requires_consent=False,
                encryption_required=True,
                audit_trail_required=True
            ),
            "preferences": DataCategory(
                category_id="preferences",
                name="User Preferences",
                sensitivity_level="low",
                retention_period_days=1825,  # 5 years
                requires_consent=False,
                encryption_required=False,
                audit_trail_required=False
            )
        }

        # 保存到文件
        categories_file = self.storage_path / "data_categories.json"
        with open(categories_file, 'w', encoding='utf-8') as f:
            json.dump({k: asdict(v) for k, v in categories.items()}, f, indent=2, default=str)

        return categories

    def _load_compliance_rules(self) -> List[ComplianceRule]:
        """加载合规规则"""
        rules = [
            # GDPR规则
            ComplianceRule(
                rule_id="gdpr_consent",
                region=ComplianceRegion.EU_GDPR,
                data_category="personal_identification",
                requirement="explicit_consent",
                description="GDPR requires explicit consent for processing personal data",
                implementation="User consent must be obtained before data collection"
            ),
            ComplianceRule(
                rule_id="gdpr_right_to_erasure",
                region=ComplianceRegion.EU_GDPR,
                data_category="personal_identification",
                requirement="right_to_erasure",
                description="GDPR provides right to erasure ('right to be forgotten')",
                implementation="Implement secure data deletion mechanisms"
            ),
            ComplianceRule(
                rule_id="gdpr_data_portability",
                region=ComplianceRegion.EU_GDPR,
                data_category="personal_identification",
                requirement="data_portability",
                description="GDPR provides right to data portability",
                implementation="Export data in machine-readable format"
            ),

            # CCPA规则
            ComplianceRule(
                rule_id="ccpa_opt_out",
                region=ComplianceRegion.US_CCPA,
                data_category="personal_identification",
                requirement="opt_out_sale",
                description="CCPA allows consumers to opt out of sale of personal information",
                implementation="Implement 'Do Not Sell My Personal Information' mechanism"
            ),
            ComplianceRule(
                rule_id="ccpa_delete",
                region=ComplianceRegion.US_CCPA,
                data_category="personal_identification",
                requirement="right_to_delete",
                description="CCPA provides right to delete personal information",
                implementation="Implement 45-day response window for deletion requests"
            ),

            # LGPD规则
            ComplianceRule(
                rule_id="lgpd_consent",
                region=ComplianceRegion.BR_LGPD,
                data_category="personal_identification",
                requirement="explicit_consent",
                description="LGPD requires explicit consent for processing personal data",
                implementation="Obtain clear and specific consent from Brazilian users"
            ),

            # PIPEDA规则
            ComplianceRule(
                rule_id="pipeda_consent",
                region=ComplianceRegion.CA_PIPEDA,
                data_category="personal_identification",
                requirement="meaningful_consent",
                description="PIPEDA requires meaningful consent for data collection",
                implementation="Ensure consent is informed and voluntarily given"
            )
        ]

        # 保存到文件
        rules_file = self.storage_path / "compliance_rules.json"
        with open(rules_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(rule) for rule in rules], f, indent=2, default=str)

        return rules

    def _load_region_configs(self) -> Dict[str, Dict[str, Any]]:
        """加载区域配置"""
        configs = {
            "eu_gdpr": {
                "max_retention_days": 2555,
                "consent_required": True,
                "data_portability": True,
                "right_to_erasure": True,
                "breach_notification_hours": 72,
                "dpo_required": True,
                "privacy_policy_required": True,
                "consent_management": "granular"
            },
            "us_ccpa": {
                "max_retention_days": 365,
                "consent_required": False,
                "data_portability": True,
                "right_to_erasure": True,
                "breach_notification_hours": 72,
                "dpo_required": False,
                "privacy_policy_required": True,
                "consent_management": "opt_out"
            },
            "ca_pipeda": {
                "max_retention_days": 2555,
                "consent_required": True,
                "data_portability": True,
                "right_to_erasure": True,
                "breach_notification_hours": "reasonable",
                "dpo_required": False,
                "privacy_policy_required": True,
                "consent_management": "meaningful"
            },
            "br_lgpd": {
                "max_retention_days": 2555,
                "consent_required": True,
                "data_portability": True,
                "right_to_erasure": True,
                "breach_notification_hours": 72,
                "dpo_required": True,
                "privacy_policy_required": True,
                "consent_management": "explicit"
            }
        }

        # 保存到文件
        configs_file = self.storage_path / "region_configs.json"
        with open(configs_file, 'w', encoding='utf-8') as f:
            json.dump(configs, f, indent=2)

        return configs

    async def check_compliance(self, user_id: str, data_category: str,
                             operation: str, region: ComplianceRegion,
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """检查操作合规性"""
        try:
            compliance_result = {
                "compliant": True,
                "violations": [],
                "requirements": [],
                "recommendations": []
            }

            # 检查数据类别
            if data_category not in self.data_categories:
                compliance_result["compliant"] = False
                compliance_result["violations"].append(f"Unknown data category: {data_category}")
                return compliance_result

            category = self.data_categories[data_category]

            # 检查同意要求
            if category.requires_consent:
                has_consent = await self._check_user_consent(user_id, data_category, region)
                if not has_consent:
                    compliance_result["compliant"] = False
                    compliance_result["violations"].append("Missing required consent")
                    compliance_result["requirements"].append("Obtain user consent before processing")

            # 检查区域特定规则
            for rule in self.compliance_rules:
                if rule.region == region and rule.data_category == data_category and rule.enabled:
                    rule_compliance = await self._check_rule_compliance(rule, context)
                    if not rule_compliance["compliant"]:
                        compliance_result["compliant"] = False
                        compliance_result["violations"].extend(rule_compliance["violations"])

            # 检查数据保留期限
            retention_check = await self._check_retention_period(user_id, data_category, region)
            if not retention_check["compliant"]:
                compliance_result["compliant"] = False
                compliance_result["violations"].extend(retention_check["violations"])
                compliance_result["requirements"].append("Delete expired data")

            logger.info(f"Compliance check for user {user_id}, category {data_category}: {compliance_result['compliant']}")
            return compliance_result

        except Exception as e:
            logger.error(f"Compliance check failed: {e}")
            return {
                "compliant": False,
                "violations": [f"Compliance check error: {str(e)}"],
                "requirements": [],
                "recommendations": ["Review compliance implementation"]
            }

    async def _check_user_consent(self, user_id: str, data_category: str,
                                region: ComplianceRegion) -> bool:
        """检查用户同意"""
        try:
            consent_file = self.storage_path / "consents" / f"{user_id}.json"
            if not consent_file.exists():
                return False

            with open(consent_file, 'r', encoding='utf-8') as f:
                consents = json.load(f)

            for consent in consents:
                if (consent["is_active"] and
                    data_category in consent["data_categories"] and
                    consent["region"] == region.value and
                    consent.get("expires_at") and
                    datetime.fromisoformat(consent["expires_at"]) > datetime.now()):
                    return True

            return False

        except Exception as e:
            logger.error(f"Consent check failed: {e}")
            return False

    async def _check_rule_compliance(self, rule: ComplianceRule,
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """检查特定规则合规性"""
        result = {"compliant": True, "violations": []}

        if rule.requirement == "explicit_consent":
            if not context.get("has_explicit_consent", False):
                result["compliant"] = False
                result["violations"].append(f"Explicit consent required for {rule.rule_id}")

        elif rule.requirement == "right_to_erasure":
            if not context.get("erasure_mechanism_available", False):
                result["compliant"] = False
                result["violations"].append(f"Erasure mechanism required for {rule.rule_id}")

        elif rule.requirement == "data_portability":
            if not context.get("portability_format_available", False):
                result["compliant"] = False
                result["violations"].append(f"Data portability required for {rule.rule_id}")

        elif rule.requirement == "opt_out_sale":
            if not context.get("opt_out_mechanism_available", False):
                result["compliant"] = False
                result["violations"].append(f"Opt-out mechanism required for {rule.rule_id}")

        return result

    async def _check_retention_period(self, user_id: str, data_category: str,
                                    region: ComplianceRegion) -> Dict[str, Any]:
        """检查数据保留期限"""
        result = {"compliant": True, "violations": []}

        category = self.data_categories[data_category]
        region_config = self.region_configs.get(region.value, {})
        max_retention = min(
            category.retention_period_days,
            region_config.get("max_retention_days", category.retention_period_days)
        )

        # 这里应该检查实际的数据时间戳
        # 实现需要根据具体的数据存储方式

        return result

    async def record_consent(self, user_id: str, data_categories: List[str],
                           purposes: List[str], region: ComplianceRegion,
                           legal_basis: str, expires_days: int = 365) -> str:
        """记录用户同意"""
        try:
            consent_id = secrets.token_urlsafe(16)
            consent = ConsentRecord(
                consent_id=consent_id,
                user_id=user_id,
                data_categories=data_categories,
                purposes=purposes,
                granted_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=expires_days),
                is_active=True,
                legal_basis=legal_basis,
                region=region,
                metadata={"ip_address": "", "user_agent": ""}
            )

            # 保存同意记录
            consent_dir = self.storage_path / "consents"
            consent_dir.mkdir(exist_ok=True)

            consent_file = consent_dir / f"{user_id}.json"
            existing_consents = []

            if consent_file.exists():
                with open(consent_file, 'r', encoding='utf-8') as f:
                    existing_consents = json.load(f)

            existing_consents.append(consent.dict())

            with open(consent_file, 'w', encoding='utf-8') as f:
                json.dump(existing_consents, f, indent=2, default=str)

            logger.info(f"Consent recorded for user {user_id}: {consent_id}")
            return consent_id

        except Exception as e:
            logger.error(f"Failed to record consent: {e}")
            raise

    async def revoke_consent(self, user_id: str, consent_id: str) -> bool:
        """撤销用户同意"""
        try:
            consent_file = self.storage_path / "consents" / f"{user_id}.json"
            if not consent_file.exists():
                return False

            with open(consent_file, 'r', encoding='utf-8') as f:
                consents = json.load(f)

            for consent in consents:
                if consent["consent_id"] == consent_id:
                    consent["is_active"] = False
                    consent["revoked_at"] = datetime.now().isoformat()
                    break

            with open(consent_file, 'w', encoding='utf-8') as f:
                json.dump(consents, f, indent=2, default=str)

            logger.info(f"Consent revoked for user {user_id}: {consent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke consent: {e}")
            return False

    async def create_subject_rights_request(self, user_id: str, request_type: str,
                                         region: ComplianceRegion, reason: str = None) -> str:
        """创建数据主体权利请求"""
        try:
            request_id = secrets.token_urlsafe(16)
            request = SubjectRightsRequest(
                request_id=request_id,
                user_id=user_id,
                request_type=request_type,
                region=region,
                status="pending",
                created_at=datetime.now(),
                reason=reason,
                evidence={}
            )

            # 保存请求记录
            requests_dir = self.storage_path / "subject_rights_requests"
            requests_dir.mkdir(exist_ok=True)

            request_file = requests_dir / f"{request_id}.json"
            with open(request_file, 'w', encoding='utf-8') as f:
                json.dump(request.dict(), f, indent=2, default=str)

            logger.info(f"Subject rights request created: {request_id}")
            return request_id

        except Exception as e:
            logger.error(f"Failed to create subject rights request: {e}")
            raise

    async def get_compliance_report(self, region: ComplianceRegion = None,
                                  start_date: datetime = None,
                                  end_date: datetime = None) -> Dict[str, Any]:
        """获取合规报告"""
        try:
            report = {
                "generated_at": datetime.now().isoformat(),
                "region": region.value if region else "all",
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                },
                "summary": {},
                "details": {}
            }

            # 统计同意记录
            consents_count = await self._count_consents(region, start_date, end_date)
            report["summary"]["total_consents"] = consents_count

            # 统计权利请求
            requests_count = await self._count_subject_rights_requests(region, start_date, end_date)
            report["summary"]["total_requests"] = requests_count

            # 统计违规事件
            violations_count = await self._count_violations(region, start_date, end_date)
            report["summary"]["total_violations"] = violations_count

            return report

        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            raise

    async def _count_consents(self, region: ComplianceRegion = None,
                            start_date: datetime = None,
                            end_date: datetime = None) -> int:
        """统计同意记录数量"""
        # 实现统计逻辑
        return 0

    async def _count_subject_rights_requests(self, region: ComplianceRegion = None,
                                           start_date: datetime = None,
                                           end_date: datetime = None) -> int:
        """统计权利请求数量"""
        # 实现统计逻辑
        return 0

    async def _count_violations(self, region: ComplianceRegion = None,
                              start_date: datetime = None,
                              end_date: datetime = None) -> int:
        """统计违规事件数量"""
        # 实现统计逻辑
        return 0

# 全局合规管理器实例
compliance_manager = DataComplianceManager()

async def get_compliance_manager() -> DataComplianceManager:
    """获取合规管理器实例"""
    return compliance_manager