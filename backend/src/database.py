from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings
from .models.base import Base

_db_engine = None
_db_session_factory = None


def get_engine():
    """Return the singleton async SQLAlchemy engine, creating it on first call."""
    global _db_engine
    if _db_engine is None:
        settings = get_settings()
        _db_engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
    return _db_engine


def get_session_factory():
    """Return the singleton session factory, creating it on first call."""
    global _db_session_factory
    if _db_session_factory is None:
        _db_session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _db_session_factory


async def init_db():
    """Create all tables. Call once at startup."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield a session, commit on success, rollback on error."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
