"""
Pytest configuration file for backend tests.

This file defines fixtures that are available to all tests in this directory and subdirectories.
"""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from backend.models.base import Base

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture(scope="function")
async def db() -> AsyncSession:
    """
    Pytest fixture to provide a database session for each test function.
    
    Creates an in-memory SQLite database and tables for each test, and drops them afterwards.
    """
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create a new session for the test
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    # Drop all tables after the test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
