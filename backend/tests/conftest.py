"""Shared pytest fixtures.

The entire suite runs on the **mock** provider and a temporary SQLite file:
no API key, no network, no database server. A test that needs credentials is a
bug in the test.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.ai.factory import build_provider
from app.core.config import Settings
from app.db.base import Base

#: Fictional, de-identified source used across the suite. The phone number is in
#: the reserved 555-01xx fictional range and the domain is example.org.
SAMPLE_SOURCE = (
    "Students are expected to return the field trip permission form in a timely manner. "
    "The form should be signed by a parent and returned to your child's teacher by "
    "Friday, September 18. Contact the undersigned with inquiries. Your cooperation "
    "is appreciated. If you need an interpreter, please call the program office at "
    "+1-555-0100."
)

#: A short message used where the wording under test is the point.
SHORT_SOURCE = "Please bring the permission form on September 8 at 8:30 a.m."


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings pointed at a throwaway SQLite database and the mock provider."""
    return Settings(
        app_env="test",
        ai_provider="mock",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        log_message_content=False,
        log_level="WARNING",
        cors_origins="http://localhost:5173",
    )


@pytest.fixture
def provider(settings: Settings) -> Any:
    """The offline mock provider."""
    return build_provider(settings)


@pytest_asyncio.fixture
async def engine(settings: Settings) -> AsyncIterator[Any]:
    """A fresh in-memory-style engine with the schema created."""
    engine = create_async_engine(settings.database_url, future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine: Any) -> AsyncIterator[AsyncSession]:
    """A transactional session that is rolled back after each test."""
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db_session:
        try:
            yield db_session
        finally:
            await db_session.rollback()


@pytest_asyncio.fixture
async def client(settings: Settings) -> AsyncIterator[AsyncClient]:
    """An HTTP client bound to the ASGI app, using the test database.

    The app builds its engine from settings, so the module-level engine cache is
    reset before and after each test to keep isolation.
    """
    from app.main import create_app

    await _reset_database_module()
    app = create_app(settings)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client

    await _reset_database_module()


async def _reset_database_module() -> None:
    """Dispose of and forget the process-wide engine so tests stay isolated."""
    import app.db.database as database_module

    if database_module._engine is not None:
        await database_module.dispose_engine()
    database_module._engine = None
    database_module._session_factory = None
