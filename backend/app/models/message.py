"""The Message aggregate root: source, revision, and approval record."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.protected_item import ProtectedItem
    from app.models.translation import Translation
    from app.models.verification import VerificationReport


class MessageState(StrEnum):
    """Where a message sits in the BRIDGE pipeline.

    The state machine is the mechanism behind the approval gate: only
    ``APPROVED`` messages may be translated.
    """

    DRAFT = "draft"
    REVISED = "revised"
    APPROVED = "approved"
    TRANSLATED = "translated"
    VERIFIED = "verified"
    ESCALATED = "escalated"


class RiskLevel(StrEnum):
    """Consequence tier. See ``app.verification.risk_classifier``."""

    ROUTINE = "routine"
    MODERATE = "moderate"
    HIGH = "high"


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A communication workspace.

    Holds the BRIDGE context (audience, purpose, action, deadline, tone), the
    original source, the AI revision, the human approval decision, and the
    frozen approved text that is actually translated.
    """

    __tablename__ = "messages"

    # --- B: Begin with purpose ------------------------------------------------
    audience: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    purpose: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    action: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    deadline: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    contact_path: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    tone: Mapped[str] = mapped_column(
        String(255), default="warm, respectful, direct", nullable=False
    )
    locale: Mapped[str] = mapped_column(String(35), default="en-US", nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, native_enum=False, length=16),
        default=RiskLevel.ROUTINE,
        nullable=False,
        index=True,
    )

    # --- R: Rewrite plainly ---------------------------------------------------
    source_message: Mapped[str] = mapped_column(Text, nullable=False)
    revised_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    open_questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    reading_level: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # --- Approval gate --------------------------------------------------------
    state: Mapped[MessageState] = mapped_column(
        Enum(MessageState, native_enum=False, length=16),
        default=MessageState.DRAFT,
        nullable=False,
        index=True,
    )
    approved_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    approval_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    target_languages: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    # --- PII screening --------------------------------------------------------
    pii_warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # --- Relationships --------------------------------------------------------
    protected_items: Mapped[list[ProtectedItem]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ProtectedItem.start_offset",
    )
    translations: Mapped[list[Translation]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    verification_reports: Mapped[list[VerificationReport]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Message {self.id[:8]} state={self.state}>"
