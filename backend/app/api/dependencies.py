"""FastAPI dependencies.

These provide the request-scoped objects routes need. Services are constructed
here so a route never builds one by hand and tests can override any of them.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider
from app.ai.factory import get_provider
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.db.database import get_session
from app.services.message_service import MessageService
from app.services.translation_service import TranslationService
from app.services.verification_service import VerificationService

logger = get_logger(__name__)


async def session_dependency() -> AsyncIterator[AsyncSession]:
    """Yield a transactional database session.

    Kept as a thin wrapper so the route signature documents the dependency
    rather than exposing the database module directly.
    """
    async for session in get_session():
        yield session


def settings_dependency() -> Settings:
    """Return the cached application settings."""
    return get_settings()


def provider_dependency() -> AIProvider:
    """Return the process-wide AI provider.

    Raises:
        AIProviderAuthError: If the configured provider is missing credentials.
    """
    return get_provider()


SessionDep = Annotated[AsyncSession, Depends(session_dependency)]
SettingsDep = Annotated[Settings, Depends(settings_dependency)]
ProviderDep = Annotated[AIProvider, Depends(provider_dependency)]


def message_service(provider: ProviderDep, settings: SettingsDep) -> MessageService:
    """Build a :class:`MessageService` for this request."""
    return MessageService(provider)


def translation_service(provider: ProviderDep, settings: SettingsDep) -> TranslationService:
    """Build a :class:`TranslationService` for this request."""
    return TranslationService(provider, settings)


def verification_service(provider: ProviderDep) -> VerificationService:
    """Build a :class:`VerificationService` for this request."""
    return VerificationService(provider)


MessageServiceDep = Annotated[MessageService, Depends(message_service)]
TranslationServiceDep = Annotated[TranslationService, Depends(translation_service)]
VerificationServiceDep = Annotated[VerificationService, Depends(verification_service)]


def request_id(request: Request) -> str:
    """The correlation id assigned by the request-id middleware."""
    return str(getattr(request.state, "request_id", "unknown"))
