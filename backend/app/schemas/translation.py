"""Request/response schemas for the translation stage."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.common import ApiModel


class TranslateRequest(ApiModel):
    """Ask for translations of an **approved** message.

    The approval gate is enforced server-side; sending this request for an
    unapproved message returns ``409 SOURCE_NOT_APPROVED``.
    """

    message_id: str = Field(min_length=1)
    target_languages: list[str] = Field(
        min_length=1,
        max_length=10,
        description="Two or three target language codes, e.g. ['es', 'hi', 'ur'].",
    )
    locale: str | None = Field(
        default=None,
        max_length=35,
        description="BCP-47 tag such as 'es-US'. Used for date and time conventions.",
    )
    tone: str | None = Field(default=None, max_length=255)
    reading_level: str | None = Field(default=None, max_length=100, description="e.g. 'grade 6'.")

    @field_validator("target_languages")
    @classmethod
    def _dedupe(cls, value: list[str]) -> list[str]:
        seen: list[str] = []
        for code in value:
            normalized = code.strip().lower()
            if normalized and normalized not in seen:
                seen.append(normalized)
        if not seen:
            msg = "Select at least one target language."
            raise ValueError(msg)
        return seen


class TranslationResponse(ApiModel):
    """One rendered translation."""

    id: str
    message_id: str
    target_language: str
    language_name: str = ""
    locale: str | None = None
    translated_message: str
    back_translation: str | None = None
    placeholders: dict[str, Any] = Field(default_factory=dict)
    protected_items: list[dict[str, Any]] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    terminology_notes: list[str] = Field(default_factory=list)
    provider: str
    model: str
    created_at: datetime


class TranslationBatchResponse(ApiModel):
    """The result of a multi-language translation request."""

    message_id: str
    translations: list[TranslationResponse]
    provider: str
    model: str
