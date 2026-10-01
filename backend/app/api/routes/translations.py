"""Translation routes. Every path here is behind the approval gate."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import (
    MessageServiceDep,
    ProviderDep,
    SessionDep,
    TranslationServiceDep,
    VerificationServiceDep,
)
from app.core.errors import TranslationNotFoundError
from app.core.languages import get_language
from app.models.translation import Translation
from app.schemas.message import MessageResponse
from app.schemas.translation import (
    TranslateRequest,
    TranslationBatchResponse,
    TranslationResponse,
)

router = APIRouter(prefix="/translations", tags=["translations"])


def to_translation_response(row: Translation) -> TranslationResponse:
    """Convert a translation ORM row into its API representation."""
    try:
        language_name = get_language(row.target_language).name
    except Exception:
        language_name = row.target_language

    return TranslationResponse(
        id=row.id,
        message_id=row.message_id,
        target_language=row.target_language,
        language_name=language_name,
        locale=row.locale,
        translated_message=row.translated_message,
        back_translation=row.back_translation,
        placeholders=row.placeholders or {},
        protected_items=row.protected_items or [],
        uncertainties=row.uncertainties or [],
        terminology_notes=row.terminology_notes or [],
        provider=row.provider,
        model=row.model,
        created_at=row.created_at,
    )


@router.post(
    "",
    response_model=TranslationBatchResponse,
    summary="Translate an approved message into two or three languages",
)
async def create_translations(
    payload: TranslateRequest,
    session: SessionDep,
    translation_service: TranslationServiceDep,
    message_service: MessageServiceDep,
    provider: ProviderDep,
) -> TranslationBatchResponse:
    """Translate an approved message.

    The message must be in state ``approved``. Any other state returns
    ``409 SOURCE_NOT_APPROVED``: the approval gate cannot be bypassed.
    """
    message = await message_service.get(session, payload.message_id)

    rows = await translation_service.translate(
        session,
        message,
        target_languages=payload.target_languages,
        locale=payload.locale,
        tone=payload.tone,
        reading_level=payload.reading_level,
    )
    await session.commit()

    return TranslationBatchResponse(
        message_id=message.id,
        translations=[to_translation_response(row) for row in rows],
        provider=provider.name,
        model=provider.model,
    )


@router.get(
    "/{translation_id}",
    response_model=TranslationResponse,
    summary="Get one translation",
)
async def get_translation(translation_id: UUID, session: SessionDep) -> TranslationResponse:
    """Return a single translation record."""
    row = await session.get(Translation, str(translation_id))
    if row is None:
        raise TranslationNotFoundError
    return to_translation_response(row)


@router.post(
    "/{translation_id}/verify",
    response_model=MessageResponse,
    summary="Verify a translation and return the updated workspace",
)
async def verify_translation(
    translation_id: UUID,
    session: SessionDep,
    verification_service: VerificationServiceDep,
    message_service: MessageServiceDep,
) -> MessageResponse:
    """Verify one translation, then return the whole workspace.

    A convenience endpoint for a single-language flow. The dedicated
    ``/api/verification`` router returns the report itself, which is what the
    main UI uses.
    """
    from app.api.routes.messages import to_response

    row = await session.get(Translation, str(translation_id))
    if row is None:
        raise TranslationNotFoundError

    await verification_service.verify(session, row)
    await session.commit()

    message = await message_service.get(session, row.message_id)
    return to_response(message)


__all__ = ["router", "to_translation_response"]
