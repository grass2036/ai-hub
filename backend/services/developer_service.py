"""
Developer Service for API Commercialization
Week 4 Day 22: Developer Portal and Authentication System
"""

import secrets
import hashlib
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.models.developer import Developer, DeveloperSession, DeveloperType, DeveloperStatus
from backend.models.developer import DeveloperAPIKey
from backend.config.settings import get_settings

settings = get_settings()


class DeveloperService:
    """开发者服务类"""

    def __init__(self, db: Session):
        self.db = db
        self.jwt_secret_key = settings.jwt_secret_key
        self.jwt_algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24 * 7  # 7天
        self.refresh_token_expire_days = 30

    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        import bcrypt
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def _verify_password(self, password: str, hashed: str) -> bool:
        """验证密码"""
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def _generate_tokens(self, developer_id: str) -> Tuple[str, str]:
        """生成JWT令牌"""
        # 访问令牌
        access_token_payload = {
            "sub": str(developer_id),
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes),
            "iat": datetime.utcnow()
        }
        access_token = jwt.encode(access_token_payload, self.jwt_secret_key, algorithm=self.jwt_algorithm)

        # 刷新令牌
        refresh_token_payload = {
            "sub": str(developer_id),
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=self.refresh_token_expire_days),
            "iat": datetime.utcnow()
        }
        refresh_token = jwt.encode(refresh_token_payload, self.jwt_secret_key, algorithm=self.jwt_algorithm)

        return access_token, refresh_token

    async def register_developer(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        company_name: Optional[str] = None,
        developer_type: str = DeveloperType.INDIVIDUAL
    ) -> Tuple[Developer, str]:
        """注册新开发者"""

        # 检查邮箱是否已存在
        existing_developer = await self.db.query(Developer).filter(
            Developer.email == email
        ).first()

        if existing_developer:
            raise ValueError("邮箱已被注册")

        # 创建新开发者
        password_hash = self._hash_password(password)
        email_verification_token = secrets.token_urlsafe(32)

        developer = Developer(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            company_name=company_name,
            developer_type=developer_type,
            email_verification_token=email_verification_token,
            email_verification_expires=datetime.utcnow() + timedelta(hours=24),
            status=DeveloperStatus.PENDING
        )

        await self.db.save(developer)

        # 生成访问令牌
        access_token, refresh_token = self._generate_tokens(str(developer.id))

        # 创建会话记录
        session = DeveloperSession(
            developer_id=developer.id,
            session_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        )
        await self.db.save(session)

        return developer, access_token

    async def login_developer(
        self,
        email: str,
        password: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[Developer, str]:
        """开发者登录"""

        # 查找开发者
        developer = await self.db.query(Developer).filter(
            Developer.email == email
        ).first()

        if not developer:
            raise ValueError("邮箱或密码错误")

        if not developer.is_active:
            raise ValueError("账户已被禁用")

        # 验证密码
        if not self._verify_password(password, developer.password_hash):
            raise ValueError("邮箱或密码错误")

        # 生成令牌
        access_token, refresh_token = self._generate_tokens(str(developer.id))

        # 创建新会话
        session = DeveloperSession(
            developer_id=developer.id,
            session_token=access_token,
            refresh_token=refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        )
        await self.db.save(session)

        # 更新最后登录时间
        developer.last_login_at = datetime.utcnow()
        await self.db.save(developer)

        return developer, access_token

    async def refresh_token(self, refresh_token: str) -> Tuple[Developer, str]:
        """刷新访问令牌"""

        try:
            # 验证刷新令牌
            payload = jwt.decode(refresh_token, self.jwt_secret_key, algorithms=[self.jwt_algorithm])

            if payload.get("type") != "refresh":
                raise ValueError("无效的刷新令牌")

            developer_id = payload["sub"]

            # 查找开发者
            developer = await self.db.query(Developer).filter(
                Developer.id == developer_id
            ).first()

            if not developer or not developer.is_active:
                raise ValueError("开发者账户不存在或已被禁用")

            # 查找会话
            session = await self.db.query(DeveloperSession).filter(
                and_(
                    DeveloperSession.developer_id == developer_id,
                    DeveloperSession.refresh_token == refresh_token,
                    DeveloperSession.is_active == True,
                    DeveloperSession.expires_at > datetime.utcnow()
                )
            ).first()

            if not session:
                raise ValueError("会话已过期或无效")

            # 生成新令牌
            new_access_token, new_refresh_token = self._generate_tokens(developer_id)

            # 更新会话
            session.session_token = new_access_token
            session.refresh_token = new_refresh_token
            session.expires_at = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
            await self.db.save(session)

            return developer, new_access_token

        except jwt.ExpiredSignatureError:
            raise ValueError("刷新令牌已过期")
        except jwt.InvalidTokenError:
            raise ValueError("无效的刷新令牌")

    async def verify_email(self, token: str) -> bool:
        """验证邮箱"""

        developer = await self.db.query(Developer).filter(
            and_(
                Developer.email_verification_token == token,
                Developer.email_verification_expires > datetime.utcnow(),
                Developer.email_verified == False
            )
        ).first()

        if not developer:
            return False

        # 更新验证状态
        developer.email_verified = True
        developer.email_verification_token = None
        developer.email_verification_expires = None

        # 如果是待验证状态，更新为活跃状态
        if developer.status == DeveloperStatus.PENDING:
            developer.status = DeveloperStatus.ACTIVE

        await self.db.save(developer)
        return True

    async def request_password_reset(self, email: str) -> bool:
        """请求密码重置"""

        developer = await self.db.query(Developer).filter(
            Developer.email == email
        ).first()

        if not developer:
            return False  # 为了安全，不透露邮箱是否存在

        # 生成重置令牌
        reset_token = secrets.token_urlsafe(32)
        developer.password_reset_token = reset_token
        developer.password_reset_expires = datetime.utcnow() + timedelta(hours=2)
        await self.db.save(developer)

        # TODO: 发送重置邮件
        # await email_service.send_password_reset_email(developer.email, reset_token)

        return True

    async def reset_password(self, token: str, new_password: str) -> bool:
        """重置密码"""

        developer = await self.db.query(Developer).filter(
            and_(
                Developer.password_reset_token == token,
                Developer.password_reset_expires > datetime.utcnow()
            )
        ).first()

        if not developer:
            return False

        # 更新密码
        developer.password_hash = self._hash_password(new_password)
        developer.password_reset_token = None
        developer.password_reset_expires = None

        # 使所有现有会话失效
        await self.db.query(DeveloperSession).filter(
            DeveloperSession.developer_id == developer.id
        ).update({"is_active": False})

        await self.db.save(developer)
        return True

    async def logout_developer(self, access_token: str) -> bool:
        """开发者登出"""

        try:
            payload = jwt.decode(access_token, self.jwt_secret_key, algorithms=[self.jwt_algorithm])
            developer_id = payload["sub"]

            # 使会话失效
            session = await self.db.query(DeveloperSession).filter(
                and_(
                    DeveloperSession.developer_id == developer_id,
                    DeveloperSession.session_token == access_token,
                    DeveloperSession.is_active == True
                )
            ).first()

            if session:
                session.is_active = False
                await self.db.save(session)

            return True

        except jwt.InvalidTokenError:
            return False

    async def get_current_developer(self, access_token: str) -> Optional[Developer]:
        """根据访问令牌获取当前开发者"""

        try:
            payload = jwt.decode(access_token, self.jwt_secret_key, algorithms=[self.jwt_algorithm])

            if payload.get("type") != "access":
                return None

            developer_id = payload["sub"]

            # 检查会话是否有效
            session = await self.db.query(DeveloperSession).filter(
                and_(
                    DeveloperSession.developer_id == developer_id,
                    DeveloperSession.session_token == access_token,
                    DeveloperSession.is_active == True,
                    DeveloperSession.expires_at > datetime.utcnow()
                )
            ).first()

            if not session:
                return None

            # 获取开发者信息
            developer = await self.db.query(Developer).filter(
                and_(
                    Developer.id == developer_id,
                    Developer.is_active == True
                )
            ).first()

            return developer

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    async def update_developer_profile(
        self,
        developer_id: str,
        full_name: Optional[str] = None,
        company_name: Optional[str] = None,
        timezone: Optional[str] = None,
        language: Optional[str] = None,
        preferences: Optional[Dict] = None
    ) -> Developer:
        """更新开发者资料"""

        developer = await self.db.query(Developer).filter(
            Developer.id == developer_id
        ).first()

        if not developer:
            raise ValueError("开发者不存在")

        if full_name is not None:
            developer.full_name = full_name
        if company_name is not None:
            developer.company_name = company_name
        if timezone is not None:
            developer.timezone = timezone
        if language is not None:
            developer.language = language
        if preferences is not None:
            developer.preferences = preferences

        await self.db.save(developer)
        return developer

    async def change_password(
        self,
        developer_id: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """修改密码"""

        developer = await self.db.query(Developer).filter(
            Developer.id == developer_id
        ).first()

        if not developer:
            return False

        # 验证当前密码
        if not self._verify_password(current_password, developer.password_hash):
            return False

        # 更新密码
        developer.password_hash = self._hash_password(new_password)

        # 使所有现有会话失效
        await self.db.query(DeveloperSession).filter(
            DeveloperSession.developer_id == developer_id
        ).update({"is_active": False})

        await self.db.save(developer)
        return True

    async def get_developer_stats(self, developer_id: str) -> Dict:
        """获取开发者统计信息"""

        from backend.models.developer import APIUsageRecord, DeveloperAPIKey

        # 获取API密钥数量
        api_keys_count = await self.db.query(DeveloperAPIKey).filter(
            and_(
                DeveloperAPIKey.developer_id == developer_id,
                DeveloperAPIKey.is_active == True
            )
        ).count()

        # 获取本月使用统计
        current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        monthly_usage = await self.db.query(APIUsageRecord).filter(
            and_(
                APIUsageRecord.developer_id == developer_id,
                APIUsageRecord.created_at >= current_month_start
            )
        ).all()

        total_tokens = sum(record.tokens_used for record in monthly_usage)
        total_requests = len(monthly_usage)
        total_cost = sum(float(record.cost) for record in monthly_usage)

        return {
            "api_keys_count": api_keys_count,
            "monthly_tokens": total_tokens,
            "monthly_requests": total_requests,
            "monthly_cost": total_cost,
            "last_updated": datetime.utcnow().isoformat()
        }