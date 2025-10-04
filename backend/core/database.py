"""
Database Connection Manager
"""

from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

from backend.config.settings import get_settings
from backend.models.base import Base

settings = get_settings()


# Synchronous engine for migrations and initial setup
def get_sync_engine():
    """获取同步数据库引擎"""
    database_url = settings.get_database_url()

    # Convert async URL to sync URL if needed
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    return create_engine(
        database_url,
        echo=settings.show_sql_queries,
        pool_pre_ping=True,
    )


# Asynchronous engine for FastAPI endpoints
def get_async_engine():
    """获取异步数据库引擎"""
    database_url = settings.get_database_url()

    # Convert to async URL if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    elif database_url.startswith("sqlite:///"):
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

    return create_async_engine(
        database_url,
        echo=settings.show_sql_queries,
        pool_pre_ping=True,
    )


# Session factories
def get_sync_session_factory():
    """获取同步会话工厂"""
    engine = get_sync_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_async_session_factory():
    """获取异步会话工厂"""
    engine = get_async_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# Dependency for FastAPI endpoints
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    数据库会话依赖
    用于FastAPI依赖注入
    """
    SessionLocal = get_async_session_factory()
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def init_db():
    """初始化数据库 - 创建所有表"""
    engine = get_sync_engine()
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def drop_db():
    """删除所有数据库表 - 仅用于开发/测试"""
    engine = get_sync_engine()
    Base.metadata.drop_all(bind=engine)
    print("⚠️  All database tables dropped")


if __name__ == "__main__":
    # Test database connection
    print("Testing database connection...")
    init_db()
