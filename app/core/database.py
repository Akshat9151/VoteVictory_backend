import logging
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

logger = logging.getLogger("app.database")

# Declarative Base for all SQLAlchemy models
Base = declarative_base()

# Async Engine for FastAPI endpoints (Exclusively PostgreSQL with asyncpg)
async_engine_kwargs = {
    "echo": settings.DEBUG and settings.ENVIRONMENT == "development",
    "future": True,
}
if "sqlite" not in settings.DATABASE_URL:
    async_engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_pre_ping": True,
        "connect_args": {"prepared_statement_cache_size": 0},
    })

async_engine = create_async_engine(settings.DATABASE_URL, **async_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync Engine for Background Workers, Celery, and Migrations (Exclusively PostgreSQL with psycopg2)
sync_engine_kwargs = {
    "echo": False,
    "future": True,
}
if "sqlite" not in settings.DATABASE_SYNC_URL:
    sync_engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": True,
    })

sync_engine = create_engine(settings.DATABASE_SYNC_URL, **sync_engine_kwargs)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async PostgreSQL database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
