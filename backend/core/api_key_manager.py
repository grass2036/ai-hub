"""
API Key Management Service
"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.models.api_key import APIKey
from backend.models.user import User


class APIKeyManager:
    """API密钥管理器"""

    @staticmethod
    async def create_api_key(
        db: AsyncSession,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        expires_days: Optional[int] = None
    ) -> APIKey:
        """
        创建新的API密钥

        Args:
            db: 数据库会话
            user_id: 用户ID
            name: 密钥名称
            description: 密钥描述
            expires_days: 过期天数（None表示永不过期）

        Returns:
            创建的API密钥对象
        """
        # Generate unique API key
        api_key = APIKey.generate_key()

        # Calculate expiration date
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)

        # Create API key record
        db_api_key = APIKey(
            user_id=user_id,
            key=api_key,
            name=name,
            description=description,
            expires_at=expires_at,
            is_active=True
        )

        db.add(db_api_key)
        await db.commit()
        await db.refresh(db_api_key)

        return db_api_key

    @staticmethod
    async def validate_api_key(
        db: AsyncSession,
        api_key: str
    ) -> Optional[tuple[APIKey, User]]:
        """
        验证API密钥并返回关联的用户

        Args:
            db: 数据库会话
            api_key: API密钥字符串

        Returns:
            (APIKey, User) 元组，如果密钥无效则返回None
        """
        # Query API key with user relationship
        result = await db.execute(
            select(APIKey, User)
            .join(User, APIKey.user_id == User.id)
            .where(
                and_(
                    APIKey.key == api_key,
                    APIKey.is_active == True,
                    User.is_active == True
                )
            )
        )

        row = result.first()
        if not row:
            return None

        db_api_key, user = row

        # Check if key is expired
        if db_api_key.is_expired():
            return None

        # Update last_used_at timestamp
        db_api_key.last_used_at = datetime.utcnow()
        await db.commit()

        return db_api_key, user

    @staticmethod
    async def get_user_api_keys(
        db: AsyncSession,
        user_id: int,
        include_inactive: bool = False
    ) -> List[APIKey]:
        """
        获取用户的所有API密钥

        Args:
            db: 数据库会话
            user_id: 用户ID
            include_inactive: 是否包含已停用的密钥

        Returns:
            API密钥列表
        """
        query = select(APIKey).where(APIKey.user_id == user_id)

        if not include_inactive:
            query = query.where(APIKey.is_active == True)

        result = await db.execute(query.order_by(APIKey.created_at.desc()))
        return result.scalars().all()

    @staticmethod
    async def revoke_api_key(
        db: AsyncSession,
        api_key_id: int,
        user_id: int
    ) -> bool:
        """
        撤销API密钥

        Args:
            db: 数据库会话
            api_key_id: API密钥ID
            user_id: 用户ID（用于验证所有权）

        Returns:
            是否成功撤销
        """
        result = await db.execute(
            select(APIKey).where(
                and_(
                    APIKey.id == api_key_id,
                    APIKey.user_id == user_id
                )
            )
        )

        db_api_key = result.scalar_one_or_none()
        if not db_api_key:
            return False

        db_api_key.is_active = False
        await db.commit()

        return True

    @staticmethod
    async def delete_api_key(
        db: AsyncSession,
        api_key_id: int,
        user_id: int
    ) -> bool:
        """
        删除API密钥

        Args:
            db: 数据库会话
            api_key_id: API密钥ID
            user_id: 用户ID（用于验证所有权）

        Returns:
            是否成功删除
        """
        result = await db.execute(
            select(APIKey).where(
                and_(
                    APIKey.id == api_key_id,
                    APIKey.user_id == user_id
                )
            )
        )

        db_api_key = result.scalar_one_or_none()
        if not db_api_key:
            return False

        await db.delete(db_api_key)
        await db.commit()

        return True

    @staticmethod
    async def get_api_key_by_id(
        db: AsyncSession,
        api_key_id: int,
        user_id: int
    ) -> Optional[APIKey]:
        """
        通过ID获取API密钥

        Args:
            db: 数据库会话
            api_key_id: API密钥ID
            user_id: 用户ID（用于验证所有权）

        Returns:
            API密钥对象或None
        """
        result = await db.execute(
            select(APIKey).where(
                and_(
                    APIKey.id == api_key_id,
                    APIKey.user_id == user_id
                )
            )
        )

        return result.scalar_one_or_none()
