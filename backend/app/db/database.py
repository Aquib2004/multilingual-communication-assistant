"""Async engine and session factory.

The engine is created once per process. SQLite needs a few opt-ins enabled to
behave like the PostgreSQL configuration used in production.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _engine_kwargs(settings: Settings) -> dict[str, Any]:
    """Dialect-appropriate engine options.

    SQLite does not support connection-pool sizing, so those options are only
    applied for server-based engines.
    """
    kwargs: dict[str, Any] = {"echo": settings.database_echo, "future": True}

    if settings.is_sqlite:
        # aiosqlite hands objects between threads; this check keeps the
        # cross-thread access legal.
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = settings.db_pool_size
        kwargs["max_overflow"] = settings.db_max_overflow
        kwargs["pool_pre_ping"] = True

    return kwargs


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""
    global _engine
    if _engine is None:
        active = settings or get_settings()
        _engine = create_async_engine(active.database_url, **_engine_kwargs(active))
        logger.info(
            "database engine created",
            dialect=_engine.dialect.name,
            sqlite=active.is_sqlite,
        )
    return _engine


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(settings),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a transactional session.

    The session is rolled back on any exception and always closed.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Close every pooled connection. Called on application shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        logger.info("database engine disposed")
    _engine = None
    _session_factory = None


async def create_all() -> None:
    """Create the schema directly.

    Used for local development and tests. Production deployments should use
    ``alembic upgrade head`` instead.
    """
    from app.db.base import Base
    from app.models import message, protected_item, translation, verification  # noqa: F401

    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    logger.info("database schema created")


async def database_is_ready() -> bool:
    """True when a trivial query succeeds. Used by the health endpoint."""
    from sqlalchemy import text

    try:
        engine = get_engine()
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001 - health must never raise
        logger.warning("database health check failed", error_type=type(exc).__name__)
        return False
