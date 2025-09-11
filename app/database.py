"""
Database connection and session management for PostgreSQL.
Handles async database operations with SQLAlchemy.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db() -> AsyncSession:
    """
    Dependency to get database session.
    Yields an async database session and ensures it's closed after use.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def test_database_connection() -> bool:
    """
    Test database connectivity.
    Returns True if connection is successful, False otherwise.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


async def create_tables():
    """
    Create all database tables.
    This will be used during application startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def close_db_connection():
    """
    Close database connection.
    This should be called during application shutdown.
    """
    await engine.dispose()
    logger.info("Database connection closed")