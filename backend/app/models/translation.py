"""A translation of an approved message into one target language."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.message import Message
    from app.models.verification import VerificationReport


class Translation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One target-language rendering of the approved source.

    ``uncertainties`` records anything the model was unsure about. That list is
    shown to the user; it is never silently dropped.
    """

    __tablename__ = "translations"

    message_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )

    target_language: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    locale: Mapped[str | None] = mapped_column(String(35), nullable=True)

    translated_message: Mapped[str] = mapped_column(Text, nullable=False)

    #: Full target-language text of the critical lines, joined by newlines.
    back_translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    back_translation_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)

    #: ``{placeholder: original_value}`` used for this translation.
    placeholders: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    #: Items flagged by the extractor, for display in the UI.
    protected_items: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    #: Things the model flagged as uncertain or ambiguous.
    uncertainties: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    #: Terminology decisions worth a human glance, e.g. "conference" -> ?
    terminology_notes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)

    message: Mapped[Message] = relationship(back_populates="translations")
    verification_reports: Mapped[list[VerificationReport]] = relationship(
        back_populates="translation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Translation {self.target_language} {self.id[:8]}>"
