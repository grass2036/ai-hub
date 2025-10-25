"""
GDPR合规性���理模块
GDPR Compliance Processing Module

实现欧盟通用数据保护条例(GDPR)的合规要求
Implements EU General Data Protection Regulation (GDPR) compliance requirements
"""

import logging
import json
import hashlib
import secrets
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, BinaryIO
from enum import Enum
from dataclasses import dataclass, asdict
from pydantic import BaseModel, EmailStr
from pathlib import Path
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class GDPRRightType(Enum):
    """GDPR数据主体权利类型"""
    RIGHT_TO_ACCESS = "right_to_access"
    RIGHT_TO_RECTIFICATION = "right_to_rectification"
    RIGHT_TO_ERASURE = "right_to_erasure"  # 被遗忘权
    RIGHT_TO_PORTABILITY = "right_to_portability"
    RIGHT_TO_OBJECT = "right_to_object"
    RIGHT_TO_RESTRICT_PROCESSING = "right_to_restrict_processing"
    RIGHT_TO_DATA_PROTECTION_OFFICER = "right_to_data_protection_officer"

class ConsentPurpose(Enum):
    """同意目的"""
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    PERSONALIZATION = "personalization"
    SERVICE_IMPROVEMENT = "service_improvement"
    LEGAL_REQUIREMENTS = "legal_requirements"
    SECURITY = "security"

class DataCategoryGDPR(BaseModel):
    """GDPR数据类别"""
    category_id: str
    name: str
    description: str
    special_category: bool  # 是否为特殊类别数据
    processing_purposes: List[str]
    legal_basis: str
    retention_period_months: int
    requires_consent: bool
    encryption_required: bool

class ConsentRecordGDPR(BaseModel):
    """GDPR同意记录"""
    consent_id: str
    user_id: str
    data_categories: List[str]
    purposes: List[ConsentPurpose]
    legal_basis: str
    granted_at: datetime
    expires_at: Optional[datetime]
    withdrawn_at: Optional[datetime]
    is_active: bool
    withdrawal_method: Optional[str]
    ip_address: str
    user_agent: str
    consent_version: str
    privacy_policy_version: str

class SubjectRightsRequestGDPR(BaseModel):
    """GDPR数据主体权利请求"""
    request_id: str
    user_id: str
    request_type: GDPRRightType
    description: str
    evidence_provided: List[str]
    status: str  # pending, processing, completed, rejected, requires_verification
    created_at: datetime
    processed_at: Optional[datetime]
    completed_at: Optional[datetime]
    assigned_processor: str
    response_deadline: datetime
    response_data: Optional[Dict[str, Any]]
    audit_log: List[Dict[str, Any]]

class DataBreachRecord(BaseModel):
    """数据泄露记录"""
    breach_id: str
    detected_at: datetime
    reported_at: datetime
    severity: str  # low, medium, high, critical
    affected_users: List[str]
    data_categories: List[str]
    description: str
    containment_actions: List[str]
    mitigation_actions: List[str]
    notification_required: bool
    notification_sent: bool
    supervisory_authority_notified: bool
    investigation_status: str

class DPIARecord(BaseModel):
    """数据保护影响评估记录"""
    dpia_id: str
    processing_activity: str
    controller: str
    data_types: List[str]
    purposes: List[str]
    recipients: List[str]
    risks_identified: List[str]
    mitigation_measures: List[str]
    compliance_officer_approved: bool
    date_approved: Optional[datetime]
    review_date: datetime
    status: str

class GDPRComplianceManager:
    """GDPR合规性管理器"""

    def __init__(self, storage_path: str = "data/gdpr_compliance"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # 加密密钥
        self.encryption_key = self._load_or_create_encryption_key()

        # 初始化配置
        self.data_categories = self._initialize_data_categories()
        self.breach_response_team = self._initialize_breach_response_team()

        # 数据保护官信息
        self.dpo_info = {
            "name": "Data Protection Officer",
            "email": "dpo@ai-hub.com",
            "phone": "+1-555-0123",
            "address": "Privacy Office, AI Hub Inc.",
            "contact_hours": "Monday-Friday 9:00-17:00 CET"
        }

        logger.info("GDPR compliance manager initialized")

    def _load_or_create_encryption_key(self) -> bytes:
        """加载或创建加密密钥"""
        key_file = self.storage_path / "encryption.key"

        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # 生成新密钥
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            logger.info("New encryption key generated and saved")
            return key

    def _initialize_data_categories(self) -> Dict[str, DataCategoryGDPR]:
        """初始化GDPR数据类别"""
        categories = {
            "personal_identification": DataCategoryGDPR(
                category_id="personal_identification",
                name="Personal Identification Data",
                description="Name, address, ID numbers, contact information",
                special_category=False,
                processing_purposes=["user_identification", "communication", "legal_compliance"],
                legal_basis="contractual_necessity",
                retention_period_months=60,  # 5年
                requires_consent=True,
                encryption_required=True
            ),
            "financial_information": DataCategoryGDPR(
                category_id="financial_information",
                name="Financial Information",
                description="Payment details, billing information, credit card data",
                special_category=False,
                processing_purposes=["payment_processing", "billing", "fraud_prevention"],
                legal_basis="contractual_necessity",
                retention_period_months=84,  # 7年（税务要求）
                requires_consent=True,
                encryption_required=True
            ),
            "health_data": DataCategoryGDPR(
                category_id="health_data",
                name="Health Data",
                description="Medical information, health records, biometric data",
                special_category=True,
                processing_purposes=["health_monitoring", "personalization"],
                legal_basis="explicit_consent",
                retention_period_months=60,  # 5年
                requires_consent=True,
                encryption_required=True
            ),
            "racial_ethnic_origin": DataCategoryGDPR(
                category_id="racial_ethnic_origin",
                name="Racial or Ethnic Origin",
                description="Information about racial or ethnic origin",
                special_category=True,
                processing_purposes=["diversity_monitoring"],
                legal_basis="explicit_consent",
                retention_period_months=24,  # 2年
                requires_consent=True,
                encryption_required=True
            ),
            "political_opinions": DataCategoryGDPR(
                category_id="political_opinions",
                name="Political Opinions",
                description="Political views, affiliations, activities",
                special_category=True,
                processing_purposes=["personalization"],
                legal_basis="explicit_consent",
                retention_period_months=12,  # 1年
                requires_consent=True,
                encryption_required=True
            ),
            "religious_beliefs": DataCategoryGDPR(
                category_id="religious_beliefs",
                name="Religious or Philosophical Beliefs",
                description="Religious beliefs, philosophical views",
                special_category=True,
                processing_purposes=["personalization"],
                legal_basis="explicit_consent",
                retention_period_months=12,  # 1年
                requires_consent=True,
                encryption_required=True
            ),
            "trade_union_membership": DataCategoryGDPR(
                category_id="trade_union_membership",
                name="Trade Union Membership",
                description="Trade union membership information",
                special_category=True,
                processing_purposes=["professional_networking"],
                legal_basis="explicit_consent",
                retention_period_months=36,  # 3年
                requires_consent=True,
                encryption_required=True
            ),
            "genetic_data": DataCategoryGDPR(
                category_id="genetic_data",
                name="Genetic Data",
                description="Genetic information, DNA data",
                special_category=True,
                processing_purposes=["research", "health_analysis"],
                legal_basis="explicit_consent",
                retention_period_months=120,  # 10年
                requires_consent=True,
                encryption_required=True
            ),
            "biometric_data": DataCategoryGDPR(
                category_id="biometric_data",
                name="Biometric Data",
                description="Fingerprints, facial recognition, voice patterns",
                special_category=True,
                processing_purposes=["authentication", "security"],
                legal_basis="explicit_consent",
                retention_period_months=24,  # 2年
                requires_consent=True,
                encryption_required=True
            ),
            "usage_data": DataCategoryGDPR(
                category_id="usage_data",
                name="Usage Data",
                description="Service usage patterns, interaction data",
                special_category=False,
                processing_purposes=["service_improvement", "analytics"],
                legal_basis="legitimate_interest",
                retention_period_months=24,  # 2年
                requires_consent=False,
                encryption_required=True
            ),
            "communication_data": DataCategoryGDPR(
                category_id="communication_data",
                name="Communication Data",
                description="Emails, messages, support tickets",
                special_category=False,
                processing_purposes=["customer_support", "service_delivery"],
                legal_basis="contractual_necessity",
                retention_period_months=36,  # 3年
                requires_consent=False,
                encryption_required=True
            )
        }

        # 保存到文件
        categories_file = self.storage_path / "data_categories.json"
        with open(categories_file, 'w', encoding='utf-8') as f:
            json.dump({k: asdict(v) for k, v in categories.items()}, f, indent=2, default=str)

        return categories

    def _initialize_breach_response_team(self) -> List[Dict[str, Any]]:
        """初始化数据泄露响应团队"""
        team = [
            {
                "role": "Incident Response Manager",
                "name": "Security Lead",
                "email": "security@ai-hub.com",
                "phone": "+1-555-0111"
            },
            {
                "role": "Legal Counsel",
                "name": "Legal Team",
                "email": "legal@ai-hub.com",
                "phone": "+1-555-0222"
            },
            {
                "role": "Technical Lead",
                "name": "Engineering Lead",
                "email": "tech@ai-hub.com",
                "phone": "+1-555-0333"
            },
            {
                "role": "Communications Lead",
                "name": "PR Team",
                "email": "comms@ai-hub.com",
                "phone": "+1-555-0444"
            },
            {
                "role": "Data Protection Officer",
                "name": "DPO",
                "email": "dpo@ai-hub.com",
                "phone": "+1-555-0123"
            }
        ]

        # 保存团队信息
        team_file = self.storage_path / "breach_response_team.json"
        with open(team_file, 'w', encoding='utf-8') as f:
            json.dump(team, f, indent=2)

        return team

    async def record_consent(self, user_id: str, data_categories: List[str],
                           purposes: List[ConsentPurpose], legal_basis: str,
                           ip_address: str, user_agent: str,
                           consent_version: str = "1.0",
                           privacy_policy_version: str = "1.0") -> str:
        """记录GDPR同意"""
        try:
            consent_id = secrets.token_urlsafe(16)

            consent = ConsentRecordGDPR(
                consent_id=consent_id,
                user_id=user_id,
                data_categories=data_categories,
                purposes=purposes,
                legal_basis=legal_basis,
                granted_at=datetime.now(),
                expires_at=None,  # 持续有效直到撤销
                withdrawn_at=None,
                is_active=True,
                withdrawal_method=None,
                ip_address=ip_address,
                user_agent=user_agent,
                consent_version=consent_version,
                privacy_policy_version=privacy_policy_version
            )

            # 保存同意记录
            consent_dir = self.storage_path / "consents"
            consent_dir.mkdir(exist_ok=True)

            consent_file = consent_dir / f"{user_id}.json"
            existing_consents = []

            if consent_file.exists():
                with open(consent_file, 'r', encoding='utf-8') as f:
                    existing_consents = json.load(f)

            # 检查是否已存在相同的同意
            for existing_consent in existing_consents:
                if (existing_consent["data_categories"] == data_categories and
                    existing_consent["purposes"] == [p.value for p in purposes] and
                    existing_consent["is_active"]):
                    # 更新现有同意
                    existing_consent["granted_at"] = consent.granted_at.isoformat()
                    existing_consent["ip_address"] = ip_address
                    existing_consent["user_agent"] = user_agent
                    break
            else:
                # 添加新同意
                existing_consents.append(consent.dict())

            with open(consent_file, 'w', encoding='utf-8') as f:
                json.dump(existing_consents, f, indent=2, default=str)

            logger.info(f"GDPR consent recorded for user {user_id}: {consent_id}")
            return consent_id

        except Exception as e:
            logger.error(f"Failed to record GDPR consent: {e}")
            raise

    async def withdraw_consent(self, user_id: str, consent_id: str,
                             withdrawal_method: str = "user_request") -> bool:
        """撤销GDPR同意"""
        try:
            consent_file = self.storage_path / "consents" / f"{user_id}.json"
            if not consent_file.exists():
                return False

            with open(consent_file, 'r', encoding='utf-8') as f:
                consents = json.load(f)

            for consent in consents:
                if consent["consent_id"] == consent_id:
                    consent["is_active"] = False
                    consent["withdrawn_at"] = datetime.now().isoformat()
                    consent["withdrawal_method"] = withdrawal_method
                    break

            with open(consent_file, 'w', encoding='utf-8') as f:
                json.dump(consents, f, indent=2, default=str)

            logger.info(f"GDPR consent withdrawn for user {user_id}: {consent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to withdraw GDPR consent: {e}")
            return False

    async def check_consent(self, user_id: str, data_category: str,
                          purpose: ConsentPurpose) -> bool:
        """检查GDPR同意"""
        try:
            consent_file = self.storage_path / "consents" / f"{user_id}.json"
            if not consent_file.exists():
                return False

            with open(consent_file, 'r', encoding='utf-8') as f:
                consents = json.load(f)

            for consent in consents:
                if (consent["is_active"] and
                    data_category in consent["data_categories"] and
                    purpose.value in consent["purposes"]):

                    # 检查是否过期
                    if consent.get("expires_at"):
                        expires_at = datetime.fromisoformat(consent["expires_at"])
                        if datetime.now() > expires_at:
                            continue

                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to check GDPR consent: {e}")
            return False

    async def create_subject_rights_request(self, user_id: str,
                                         request_type: GDPRRightType,
                                         description: str,
                                         evidence_provided: List[str] = None) -> str:
        """创建GDPR数据主体权利请求"""
        try:
            request_id = secrets.token_urlsafe(16)

            # GDPR要求在特定时间内响应
            response_deadline = datetime.now() + timedelta(days=30)
            if request_type == GDPRRightType.RIGHT_TO_ACCESS:
                response_deadline = datetime.now() + timedelta(days=30)
            elif request_type == GDPRRightType.RIGHT_TO_ERASURE:
                response_deadline = datetime.now() + timedelta(days=30)

            request = SubjectRightsRequestGDPR(
                request_id=request_id,
                user_id=user_id,
                request_type=request_type,
                description=description,
                evidence_provided=evidence_provided or [],
                status="pending",
                created_at=datetime.now(),
                processed_at=None,
                completed_at=None,
                assigned_processor="system",
                response_deadline=response_deadline,
                response_data=None,
                audit_log=[
                    {
                        "action": "request_created",
                        "timestamp": datetime.now().isoformat(),
                        "user": "system",
                        "details": "GDPR subject rights request created"
                    }
                ]
            )

            # 保存请求记录
            requests_dir = self.storage_path / "subject_rights_requests"
            requests_dir.mkdir(exist_ok=True)

            request_file = requests_dir / f"{request_id}.json"
            with open(request_file, 'w', encoding='utf-8') as f:
                json.dump(request.dict(), f, indent=2, default=str)

            logger.info(f"GDPR subject rights request created: {request_id}")
            return request_id

        except Exception as e:
            logger.error(f"Failed to create GDPR subject rights request: {e}")
            raise

    async def process_access_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """处理数据访问请求"""
        try:
            request_file = self.storage_path / "subject_rights_requests" / f"{request_id}.json"
            if not request_file.exists():
                return None

            with open(request_file, 'r', encoding='utf-8') as f:
                request = json.load(f)

            # 收集用户所有数据
            user_data = await self._collect_user_data(request["user_id"])

            # 加密敏感数据
            encrypted_data = await self._encrypt_sensitive_data(user_data)

            response_data = {
                "request_id": request_id,
                "user_id": request["user_id"],
                "data_collected": encrypted_data,
                "collection_purposes": await self._get_data_purposes(request["user_id"]),
                "data_recipients": await self._get_data_recipients(request["user_id"]),
                "retention_periods": await self._get_retention_periods(request["user_id"]),
                "data_rights": await self._get_data_rights_info(),
                "generated_at": datetime.now().isoformat(),
                "format": "json"
            }

            # 更新请求状态
            request["status"] = "completed"
            request["completed_at"] = datetime.now().isoformat()
            request["response_data"] = response_data
            request["audit_log"].append({
                "action": "access_request_completed",
                "timestamp": datetime.now().isoformat(),
                "user": "system",
                "details": "User data access request processed"
            })

            with open(request_file, 'w', encoding='utf-8') as f:
                json.dump(request, f, indent=2, default=str)

            logger.info(f"GDPR access request completed: {request_id}")
            return response_data

        except Exception as e:
            logger.error(f"Failed to process GDPR access request: {e}")
            return None

    async def process_erasure_request(self, request_id: str) -> bool:
        """处理数据删除请求（被遗忘权）"""
        try:
            request_file = self.storage_path / "subject_rights_requests" / f"{request_id}.json"
            if not request_file.exists():
                return False

            with open(request_file, 'r', encoding='utf-8') as f:
                request = json.load(f)

            user_id = request["user_id"]
            deletion_log = []

            # 删除用户各类数据
            data_types_to_delete = [
                "personal_information",
                "usage_data",
                "communication_history",
                "preferences",
                "analytics_data"
            ]

            for data_type in data_types_to_delete:
                try:
                    # 这里应该调用实际的数据删除接口
                    # await self._delete_user_data(user_id, data_type)
                    deletion_log.append({
                        "data_type": data_type,
                        "status": "deleted",
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    deletion_log.append({
                        "data_type": data_type,
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })

            # 撤销所有同意
            await self._withdraw_all_consents(user_id)

            # 更新请求状态
            request["status"] = "completed"
            request["completed_at"] = datetime.now().isoformat()
            request["response_data"] = {
                "deletion_log": deletion_log,
                "confirmation": "User data has been deleted in accordance with GDPR right to erasure"
            }
            request["audit_log"].append({
                "action": "erasure_request_completed",
                "timestamp": datetime.now().isoformat(),
                "user": "system",
                "details": "User data erasure request processed"
            })

            with open(request_file, 'w', encoding='utf-8') as f:
                json.dump(request, f, indent=2, default=str)

            logger.info(f"GDPR erasure request completed: {request_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to process GDPR erasure request: {e}")
            return False

    async def _collect_user_data(self, user_id: str) -> Dict[str, Any]:
        """收集用户数据"""
        # 这里应该从各个数据源收集用户数据
        user_data = {
            "personal_information": {
                "name": "John Doe",  # 示例数据
                "email": "john.doe@example.com",
                "registration_date": "2024-01-01T00:00:00Z"
            },
            "usage_data": {
                "last_login": "2024-12-01T10:00:00Z",
                "total_requests": 100,
                "active_features": ["chat", "api"]
            },
            "preferences": {
                "language": "en-US",
                "theme": "dark",
                "notifications": True
            }
        }

        return user_data

    async def _encrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """加密敏感数据"""
        try:
            fernet = Fernet(self.encryption_key)
            data_json = json.dumps(data, default=str)
            encrypted_data = fernet.encrypt(data_json.encode())

            return {
                "encrypted": True,
                "data": base64.b64encode(encrypted_data).decode(),
                "encryption_method": "Fernet",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to encrypt sensitive data: {e}")
            return {"encrypted": False, "error": str(e)}

    async def record_data_breach(self, severity: str, affected_users: List[str],
                               data_categories: List[str], description: str) -> str:
        """记录数据泄露事件"""
        try:
            breach_id = secrets.token_urlsafe(16)

            breach = DataBreachRecord(
                breach_id=breach_id,
                detected_at=datetime.now(),
                reported_at=datetime.now(),
                severity=severity,
                affected_users=affected_users,
                data_categories=data_categories,
                description=description,
                containment_actions=[],
                mitigation_actions=[],
                notification_required=severity in ["medium", "high", "critical"],
                notification_sent=False,
                supervisory_authority_notified=severity in ["high", "critical"],
                investigation_status="investigating"
            )

            # 保存泄露记录
            breaches_dir = self.storage_path / "data_breaches"
            breaches_dir.mkdir(exist_ok=True)

            breach_file = breaches_dir / f"{breach_id}.json"
            with open(breach_file, 'w', encoding='utf-8') as f:
                json.dump(breach.dict(), f, indent=2, default=str)

            # 如果需要通知，启动通知流程
            if breach.notification_required:
                asyncio.create_task(self._handle_breach_notification(breach_id))

            logger.info(f"Data breach recorded: {breach_id}")
            return breach_id

        except Exception as e:
            logger.error(f"Failed to record data breach: {e}")
            raise

    async def _handle_breach_notification(self, breach_id: str):
        """处理数据泄露通知"""
        try:
            # GDPR要求在72小时内通知监管机构
            breach_file = self.storage_path / "data_breaches" / f"{breach_id}.json"
            with open(breach_file, 'r', encoding='utf-8') as f:
                breach = json.load(f)

            # 这里应该实现实际的通知逻辑
            # 包括通知受影响用户和监管机构

            breach["notification_sent"] = True
            if breach["supervisory_authority_notified"]:
                breach["supervisory_authority_notified"] = True

            with open(breach_file, 'w', encoding='utf-8') as f:
                json.dump(breach, f, indent=2, default=str)

            logger.info(f"Breach notifications sent for: {breach_id}")

        except Exception as e:
            logger.error(f"Failed to handle breach notification: {e}")

    async def create_dpia(self, processing_activity: str, controller: str,
                         data_types: List[str], purposes: List[str],
                         risks_identified: List[str]) -> str:
        """创建数据保护影响评估(DPIA)"""
        try:
            dpia_id = secrets.token_urlsafe(16)

            dpia = DPIARecord(
                dpia_id=dpia_id,
                processing_activity=processing_activity,
                controller=controller,
                data_types=data_types,
                purposes=purposes,
                recipients=["internal_team"],
                risks_identified=risks_identified,
                mitigation_measures=[
                    "Data encryption at rest and in transit",
                    "Access control and authentication",
                    "Regular security audits",
                    "Data minimization principles"
                ],
                compliance_officer_approved=False,
                date_approved=None,
                review_date=datetime.now() + timedelta(days=365),
                status="pending_review"
            )

            # 保存DPIA记录
            dpia_dir = self.storage_path / "dpia_records"
            dpia_dir.mkdir(exist_ok=True)

            dpia_file = dpia_dir / f"{dpia_id}.json"
            with open(dpia_file, 'w', encoding='utf-8') as f:
                json.dump(dpia.dict(), f, indent=2, default=str)

            logger.info(f"DPIA created: {dpia_id}")
            return dpia_id

        except Exception as e:
            logger.error(f"Failed to create DPIA: {e}")
            raise

    async def get_compliance_report(self, start_date: datetime = None,
                                  end_date: datetime = None) -> Dict[str, Any]:
        """获取GDPR合规报告"""
        try:
            report = {
                "generated_at": datetime.now().isoformat(),
                "report_period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                },
                "consent_management": await self._get_consent_statistics(),
                "subject_rights_requests": await self._get_rights_request_statistics(),
                "data_breaches": await self._get_breach_statistics(),
                "dpia_records": await self._get_dpia_statistics(),
                "data_processing_activities": await self._get_processing_activities(),
                "compliance_score": await self._calculate_compliance_score()
            }

            return report

        except Exception as e:
            logger.error(f"Failed to generate GDPR compliance report: {e}")
            raise

    async def _get_consent_statistics(self) -> Dict[str, Any]:
        """获取同意统计"""
        consents_dir = self.storage_path / "consents"
        if not consents_dir.exists():
            return {"total_consents": 0, "active_consents": 0, "withdrawn_consents": 0}

        total_consents = 0
        active_consents = 0
        withdrawn_consents = 0

        for consent_file in consents_dir.glob("*.json"):
            try:
                with open(consent_file, 'r', encoding='utf-8') as f:
                    consents = json.load(f)
                    for consent in consents:
                        total_consents += 1
                        if consent.get("is_active", False):
                            active_consents += 1
                        if consent.get("withdrawn_at"):
                            withdrawn_consents += 1
            except Exception:
                continue

        return {
            "total_consents": total_consents,
            "active_consents": active_consents,
            "withdrawn_consents": withdrawn_consents
        }

    async def _get_rights_request_statistics(self) -> Dict[str, Any]:
        """获取权利请求统计"""
        # 实现权利请求统计逻辑
        return {
            "total_requests": 0,
            "pending_requests": 0,
            "completed_requests": 0,
            "average_response_time_days": 0
        }

    async def _get_breach_statistics(self) -> Dict[str, Any]:
        """获取数据泄露统计"""
        # 实现数据泄露统计逻辑
        return {
            "total_breaches": 0,
            "breaches_by_severity": {"low": 0, "medium": 0, "high": 0, "critical": 0},
            "average_notification_time_hours": 0
        }

    async def _get_dpia_statistics(self) -> Dict[str, Any]:
        """获取DPIA统计"""
        # 实现DPIA统计逻辑
        return {
            "total_dpias": 0,
            "approved_dpias": 0,
            "pending_dpias": 0
        }

    async def _get_processing_activities(self) -> List[Dict[str, Any]]:
        """获取数据处理活动列表"""
        return [
            {
                "activity": "User Registration",
                "purpose": "Service Provision",
                "legal_basis": "Contractual Necessity",
                "data_categories": ["personal_identification", "contact_information"]
            },
            {
                "activity": "Analytics Processing",
                "purpose": "Service Improvement",
                "legal_basis": "Legitimate Interest",
                "data_categories": ["usage_data"]
            }
        ]

    async def _calculate_compliance_score(self) -> float:
        """计算合规评分"""
        # 实现合规评分计算逻辑
        return 85.5  # 示例分数

    async def _withdraw_all_consents(self, user_id: str):
        """撤销用户所有同意"""
        try:
            consent_file = self.storage_path / "consents" / f"{user_id}.json"
            if consent_file.exists():
                with open(consent_file, 'r', encoding='utf-8') as f:
                    consents = json.load(f)

                for consent in consents:
                    if consent.get("is_active", False):
                        consent["is_active"] = False
                        consent["withdrawn_at"] = datetime.now().isoformat()
                        consent["withdrawal_method"] = "right_to_erasure"

                with open(consent_file, 'w', encoding='utf-8') as f:
                    json.dump(consents, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Failed to withdraw all consents: {e}")

# 全局GDPR合规管理器实例
gdpr_compliance_manager = GDPRComplianceManager()

async def get_gdpr_compliance_manager() -> GDPRComplianceManager:
    """获取GDPR合规管理器实例"""
    return gdpr_compliance_manager