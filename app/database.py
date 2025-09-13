"""
Database connection and session management for PostgreSQL.
Handles async database operations with SQLAlchemy and connection pooling.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import text, DateTime, UUID, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from app.config import settings
import logging
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Create async engine with optimized connection pooling for containerized environment
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    # Connection pool settings optimized for Docker containers
    pool_size=10,  # Number of connections to maintain in the pool
    max_overflow=20,  # Additional connections that can be created on demand
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_timeout=30,  # Timeout for getting connection from pool
    # Connection arguments for PostgreSQL
    connect_args={
        "server_settings": {
            "application_name": "property_listing_api",
        }
    }
)

# Create test engine for testing environment
test_engine = None
if settings.is_testing:
    test_engine = create_async_engine(
        settings.test_database_url,
        echo=settings.debug,
        pool_size=5,  # Smaller pool for testing
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={
            "server_settings": {
                "application_name": "property_listing_api_test",
            }
        }
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Test session factory
TestAsyncSessionLocal = None
if test_engine:
    TestAsyncSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


class Base(DeclarativeBase):
    """
    Base class for all database models.
    Includes common fields: id, created_at, updated_at.
    """
    
    # Primary key with UUID
    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    # Timestamp fields with automatic management
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True
    )
    
    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"


async def get_db() -> AsyncSession:
    """
    Dependency to get database session.
    Yields an async database session and ensures it's closed after use.
    """
    session_factory = TestAsyncSessionLocal if settings.is_testing and TestAsyncSessionLocal else AsyncSessionLocal
    
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_test_db() -> AsyncSession:
    """
    Dependency to get test database session.
    Used specifically for testing to ensure test isolation.
    """
    if not TestAsyncSessionLocal:
        raise RuntimeError("Test database not configured")
    
    async with TestAsyncSessionLocal() as session:
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
        session_factory = TestAsyncSessionLocal if settings.is_testing and TestAsyncSessionLocal else AsyncSessionLocal
        async with session_factory() as session:
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
    target_engine = test_engine if settings.is_testing and test_engine else engine
    
    async with target_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def drop_tables():
    """
    Drop all database tables.
    This should only be used in testing or development.
    """
    if not settings.is_testing and not settings.is_development:
        raise RuntimeError("Cannot drop tables in production environment")
    
    target_engine = test_engine if settings.is_testing and test_engine else engine
    
    async with target_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")


async def close_db_connection():
    """
    Close database connection.
    This should be called during application shutdown.
    """
    await engine.dispose()
    if test_engine:
        await test_engine.dispose()
    logger.info("Database connections closed")


async def get_database_info() -> dict:
    """
    Get database connection information for monitoring.
    Returns connection pool status and database version.
    """
    try:
        session_factory = TestAsyncSessionLocal if settings.is_testing and TestAsyncSessionLocal else AsyncSessionLocal
        async with session_factory() as session:
            # Get PostgreSQL version
            version_result = await session.execute(text("SELECT version()"))
            version = version_result.scalar()
            
            # Get connection pool info
            target_engine = test_engine if settings.is_testing and test_engine else engine
            pool = target_engine.pool
            
            return {
                "database_version": version,
                "pool_size": pool.size(),
                "checked_in_connections": pool.checkedin(),
                "checked_out_connections": pool.checkedout(),
                "overflow_connections": pool.overflow(),
                "invalid_connections": pool.invalidated(),
            }
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {"error": str(e)}