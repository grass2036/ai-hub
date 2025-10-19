"""
Developer API Key Management Service
Week 4 Day 23: API Key Management and Permission System
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from backend.models.developer import Developer, DeveloperAPIKey, DeveloperType
from backend.models.developer import APIUsageRecord
from backend.config.settings import get_settings

settings = get_settings()


class DeveloperAPIService:
    """开发者API密钥管理服务"""

    def __init__(self, db: Session):
        self.db = db

    def _generate_api_key(self) -> Tuple[str, str]:
        """生成安全的API密钥"""
        # 生成密钥格式: ahub_dev_<random_string>
        prefix = "ahub_dev_"
        random_part = secrets.token_urlsafe(32)
        api_key = f"{prefix}{random_part}"

        # 生成密钥哈希值用于存储
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # 生成显示前缀
        key_prefix = f"{api_key[:20]}..."

        return api_key, key_hash, key_prefix

    async def create_api_key(
        self,
        developer_id: str,
        name: str,
        permissions: List[str] = None,
        rate_limit: Optional[int] = None,
        allowed_models: List[str] = None,
        expires_days: Optional[int] = None
    ) -> Tuple[DeveloperAPIKey, str]:
        """创建新的API密钥"""

        # 获取开发者信息
        developer = await self.db.query(Developer).filter(
            Developer.id == developer_id
        ).first()

        if not developer:
            raise ValueError("开发者不存在")

        if not developer.is_active:
            raise ValueError("开发者账户已被禁用")

        if not developer.email_verified:
            raise ValueError("请先验证邮箱地址")

        # 检查API密钥数量限制
        existing_keys_count = await self.db.query(DeveloperAPIKey).filter(
            and_(
                DeveloperAPIKey.developer_id == developer_id,
                DeveloperAPIKey.is_active == True
            )
        ).count()

        max_keys = self._get_max_api_keys(developer.developer_type)
        if existing_keys_count >= max_keys:
            raise ValueError(f"已达到最大API密钥数量限制 ({max_keys}个)")

        # 生成API密钥
        api_key, key_hash, key_prefix = self._generate_api_key()

        # 设置过期时间
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)

        # 设置默认权限
        default_permissions = ["chat.completions", "chat.models", "usage.view"]
        if permissions is None:
            permissions = default_permissions

        # 设置默认速率限制
        if rate_limit is None:
            rate_limit = developer.api_rate_limit

        # 创建API密钥记录
        db_api_key = DeveloperAPIKey(
            developer_id=developer_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=permissions,
            rate_limit=rate_limit,
            allowed_models=allowed_models or [],
            expires_at=expires_at
        )

        await self.db.save(db_api_key)

        return db_api_key, api_key

    def _get_max_api_keys(self, developer_type: str) -> int:
        """根据开发者类型获取最大API密钥数量"""
        limits = {
            DeveloperType.INDIVIDUAL: 5,
            DeveloperType.STARTUP: 10,
            DeveloperType.ENTERPRISE: 50,
            DeveloperType.AGENCY: 25
        }
        return limits.get(developer_type, 5)

    async def validate_api_key(self, api_key: str) -> Optional[DeveloperAPIKey]:
        """验证API密钥"""

        # 计算密钥哈希
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # 查找API密钥
        db_api_key = await self.db.query(DeveloperAPIKey).filter(
            and_(
                DeveloperAPIKey.key_hash == key_hash,
                DeveloperAPIKey.is_active == True,
                or_(
                    DeveloperAPIKey.expires_at.is_(None),
                    DeveloperAPIKey.expires_at > datetime.utcnow()
                )
            )
        ).first()

        if not db_api_key:
            return None

        # 检查关联的开发者是否活跃
        developer = await self.db.query(Developer).filter(
            Developer.id == db_api_key.developer_id
        ).first()

        if not developer or not developer.is_active:
            return None

        return db_api_key

    async def get_api_keys(
        self,
        developer_id: str,
        include_inactive: bool = False,
        page: int = 1,
        limit: int = 20
    ) -> Dict:
        """获取开发者的API密钥列表"""

        query = await self.db.query(DeveloperAPIKey).filter(
            DeveloperAPIKey.developer_id == developer_id
        )

        if not include_inactive:
            query = query.filter(DeveloperAPIKey.is_active == True)

        # 获取总数
        total = query.count()

        # 分页查询
        api_keys = query.order_by(desc(DeveloperAPIKey.created_at)).offset(
            (page - 1) * limit
        ).limit(limit).all()

        return {
            "api_keys": [api_key.to_dict(include_usage=True) for api_key in api_keys],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }

    async def get_api_key(
        self,
        api_key_id: str,
        developer_id: str
    ) -> Optional[DeveloperAPIKey]:
        """获取特定API密钥详情"""

        return await self.db.query(DeveloperAPIKey).filter(
            and_(
                DeveloperAPIKey.id == api_key_id,
                DeveloperAPIKey.developer_id == developer_id
            )
        ).first()

    async def update_api_key(
        self,
        api_key_id: str,
        developer_id: str,
        name: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        rate_limit: Optional[int] = None,
        allowed_models: Optional[List[str]] = None,
        is_active: Optional[bool] = None
    ) -> DeveloperAPIKey:
        """更新API密钥信息"""

        api_key = await self.get_api_key(api_key_id, developer_id)
        if not api_key:
            raise ValueError("API密钥不存在")

        # 更新字段
        if name is not None:
            api_key.name = name
        if permissions is not None:
            api_key.permissions = permissions
        if rate_limit is not None:
            api_key.rate_limit = rate_limit
        if allowed_models is not None:
            api_key.allowed_models = allowed_models
        if is_active is not None:
            api_key.is_active = is_active

        await self.db.save(api_key)
        return api_key

    async def regenerate_api_key(
        self,
        api_key_id: str,
        developer_id: str
    ) -> Tuple[DeveloperAPIKey, str]:
        """重新生成API密钥"""

        api_key = await self.get_api_key(api_key_id, developer_id)
        if not api_key:
            raise ValueError("API密钥不存在")

        # 生成新的API密钥
        new_api_key, new_key_hash, new_key_prefix = self._generate_api_key()

        # 更新密钥信息
        api_key.key_hash = new_key_hash
        api_key.key_prefix = new_key_prefix

        await self.db.save(api_key)
        return api_key, new_api_key

    async def delete_api_key(
        self,
        api_key_id: str,
        developer_id: str
    ) -> bool:
        """删除API密钥（软删除）"""

        api_key = await self.get_api_key(api_key_id, developer_id)
        if not api_key:
            return False

        # 软删除：设置为非活跃状态
        api_key.is_active = False
        await self.db.save(api_key)
        return True

    async def record_api_usage(
        self,
        api_key_id: str,
        endpoint: str,
        method: str,
        model: Optional[str],
        tokens_used: int,
        response_time_ms: int,
        status_code: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """记录API使用情况"""

        # 获取API密钥信息
        api_key = await self.db.query(DeveloperAPIKey).filter(
            DeveloperAPIKey.id == api_key_id
        ).first()

        if not api_key:
            return

        # 计算成本
        cost = self._calculate_cost(model, tokens_used)

        # 创建使用记录
        usage_record = APIUsageRecord(
            developer_id=api_key.developer_id,
            api_key_id=api_key_id,
            endpoint=endpoint,
            method=method,
            model=model,
            tokens_used=tokens_used,
            cost=str(cost),
            response_time_ms=response_time_ms,
            status_code=status_code,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id
        )

        await self.db.save(usage_record)

        # 更新API密钥使用统计
        api_key.usage_count += 1
        api_key.total_tokens_used += tokens_used
        api_key.last_used_at = datetime.utcnow()

        await self.db.save(api_key)

    def _calculate_cost(self, model: str, tokens: int) -> float:
        """计算API使用成本"""

        # 模型定价表（每1000 tokens的成本）
        pricing = {
            "gpt-4o": 0.015,
            "gpt-4o-mini": 0.00015,
            "claude-3.5-sonnet": 0.003,
            "llama-3.1-70b": 0.001,
            "gemini-1.5-pro": 0.0025
        }

        per_thousand_cost = pricing.get(model, 0.001)
        return (tokens / 1000) * per_thousand_cost

    async def get_api_key_usage_stats(
        self,
        api_key_id: str,
        developer_id: str,
        days: int = 30
    ) -> Dict:
        """获取API密钥使用统计"""

        # 检查权限
        api_key = await self.get_api_key(api_key_id, developer_id)
        if not api_key:
            raise ValueError("API密钥不存在")

        # 计算时间范围
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 查询使用记录
        usage_records = await self.db.query(APIUsageRecord).filter(
            and_(
                APIUsageRecord.api_key_id == api_key_id,
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
                "avg_response_time": 0,
                "success_rate": 0.0,
                "model_usage": {},
                "daily_usage": {}
            }

        # 统计数据
        total_requests = len(usage_records)
        total_tokens = sum(record.tokens_used for record in usage_records)
        total_cost = sum(float(record.cost) for record in usage_records)
        avg_response_time = sum(record.response_time_ms for record in usage_records if record.response_time_ms) / total_requests
        success_count = sum(1 for record in usage_records if 200 <= record.status_code < 300)
        success_rate = (success_count / total_requests) * 100

        # 按模型统计
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

        # 按日期统计
        daily_usage = {}
        for record in usage_records:
            date_key = record.created_at.strftime("%Y-%m-%d")
            if date_key not in daily_usage:
                daily_usage[date_key] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0.0
                }

            daily_usage[date_key]["requests"] += 1
            daily_usage[date_key]["tokens"] += record.tokens_used
            daily_usage[date_key]["cost"] += float(record.cost)

        return {
            "period_days": days,
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "avg_response_time": round(avg_response_time, 2),
            "success_rate": round(success_rate, 2),
            "model_usage": model_usage,
            "daily_usage": daily_usage
        }

    async def check_rate_limit(
        self,
        api_key_id: str,
        window_minutes: int = 1
    ) -> Tuple[bool, Dict]:
        """检查API密钥速率限制"""

        api_key = await self.db.query(DeveloperAPIKey).filter(
            DeveloperAPIKey.id == api_key_id
        ).first()

        if not api_key or not api_key.is_active:
            return False, {"error": "API密钥无效或已禁用"}

        # 计算时间窗口
        window_start = datetime.utcnow() - timedelta(minutes=window_minutes)

        # 统计窗口内的请求数
        request_count = await self.db.query(APIUsageRecord).filter(
            and_(
                APIUsageRecord.api_key_id == api_key_id,
                APIUsageRecord.created_at >= window_start
            )
        ).count()

        rate_limit = api_key.rate_limit
        remaining = max(0, rate_limit - request_count)
        is_allowed = request_count < rate_limit

        return is_allowed, {
            "limit": rate_limit,
            "used": request_count,
            "remaining": remaining,
            "window_minutes": window_minutes
        }

    async def get_developer_api_quota(
        self,
        developer_id: str
    ) -> Dict:
        """获取开发者的API配额信息"""

        developer = await self.db.query(Developer).filter(
            Developer.id == developer_id
        ).first()

        if not developer:
            raise ValueError("开发者不存在")

        # 获取本月使用统计
        current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        monthly_usage = await self.db.query(APIUsageRecord).filter(
            and_(
                APIUsageRecord.developer_id == developer_id,
                APIUsageRecord.created_at >= current_month_start
            )
        ).all()

        total_tokens_used = sum(record.tokens_used for record in monthly_usage)
        total_cost = sum(float(record.cost) for record in monthly_usage)

        # 获取活跃API密钥数量
        active_keys_count = await self.db.query(DeveloperAPIKey).filter(
            and_(
                DeveloperAPIKey.developer_id == developer_id,
                DeveloperAPIKey.is_active == True
            )
        ).count()

        return {
            "monthly_quota": developer.api_quota_limit,
            "monthly_used": total_tokens_used,
            "monthly_remaining": max(0, developer.api_quota_limit - total_tokens_used),
            "monthly_usage_percent": round((total_tokens_used / developer.api_quota_limit) * 100, 2) if developer.api_quota_limit > 0 else 0,
            "monthly_cost": total_cost,
            "active_api_keys": active_keys_count,
            "max_api_keys": self._get_max_api_keys(developer.developer_type),
            "reset_date": (current_month_start + timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d")
        }