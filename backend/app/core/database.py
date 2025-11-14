"""
Database Configuration with SQLAlchemy 2.0
Async support for better performance
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Convert sync URL to async
database_url = str(settings.DATABASE_URL).replace("postgresql://", "postgresql+asyncpg://")

# Create async engine
engine = create_async_engine(
    database_url,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    poolclass=NullPool if settings.ENVIRONMENT == "test" else None,
)

# Session factory
SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    """Base class for all models"""
    pass

async def get_db() -> AsyncSession:
    """Dependency for database sessions"""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
