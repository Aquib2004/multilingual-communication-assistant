"""Verification reports: the durable record of what was checked.

A report is the artefact the project is required to produce - it answers
"what did we check, what did we change, and what still needs a human".
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:  # pragma: no cover
    from app.models.message import Message
    from app.models.translation import Translation


def _child_id() -> str:
    """Primary key generator for child rows of a report."""
    return uuid.uuid4().hex


class VerificationStatus(StrEnum):
    """Status of a single check, or of a whole report."""

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW"
    ESCALATED = "ESCALATED"

    @property
    def severity(self) -> int:
        """Numeric severity, used to roll several checks up into one status.

        ``ESCALATED`` outranks ``FAIL`` so a high-risk message is never
        presented as merely "failed" and quietly archived.
        """
        order: dict[VerificationStatus, int] = {
            VerificationStatus.PASS: 0,
            VerificationStatus.WARNING: 1,
            VerificationStatus.REVIEW_REQUIRED: 2,
            VerificationStatus.FAIL: 3,
            VerificationStatus.ESCALATED: 4,
        }
        return order[self]


class FactCheck(Base):
    """One row of the fact map: an item, its source, its translation, a verdict."""

    __tablename__ = "fact_checks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_child_id)
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("verification_reports.id", ondelete="CASCADE"), index=True
    )
    item_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_value: Mapped[str] = mapped_column(Text, nullable=False)
    translated_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable form for the API."""
        return {
            "item_type": self.item_type,
            "source": self.source_value,
            "translated": self.translated_value,
            "status": self.status,
            "detail": self.detail,
        }


class BackTranslationPair(Base):
    """A source sentence, its back-translation, and the verdict on the pair."""

    __tablename__ = "back_translation_pairs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_child_id)
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("verification_reports.id", ondelete="CASCADE"), index=True
    )
    source_sentence: Mapped[str] = mapped_column(Text, nullable=False)
    back_translated: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable form for the API."""
        return {
            "source_sentence": self.source_sentence,
            "back_translated": self.back_translated,
            "status": self.status,
            "detail": self.detail,
        }


class ToneAssessment(Base):
    """Pragmatic and terminological review. Always advisory, never blocking."""

    __tablename__ = "tone_assessments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_child_id)
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("verification_reports.id", ondelete="CASCADE"), unique=True
    )
    tone: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    mechanical_phrases: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    cultural_awkwardness: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    terminology_notes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=VerificationStatus.REVIEW_REQUIRED.value
    )

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable form for the API."""
        return {
            "tone": self.tone,
            "mechanical_phrases": self.mechanical_phrases,
            "cultural_awkwardness": self.cultural_awkwardness,
            "terminology_notes": self.terminology_notes,
            "status": self.status,
        }



class VerificationReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The full verification record for one translation."""

    __tablename__ = "verification_reports"

    message_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    translation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("translations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    target_language: Mapped[str] = mapped_column(String(12), nullable=False)
    overall_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=VerificationStatus.REVIEW_REQUIRED.value, index=True
    )
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    summary: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)

    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="routine")
    risk_evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    risk_declared_by_user: Mapped[str | None] = mapped_column(String(16), nullable=True)

    escalation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_requirements: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    message: Mapped[Message] = relationship(back_populates="verification_reports")
    translation: Mapped[Translation] = relationship(back_populates="verification_reports")

    checks: Mapped[list[FactCheck]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    back_translation_pairs: Mapped[list[BackTranslationPair]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    tone: Mapped[ToneAssessment | None] = relationship(
        cascade="all, delete-orphan", lazy="selectin", uselist=False
    )
    issues: Mapped[list[Issue]] = relationship(cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<VerificationReport {self.target_language} {self.overall_status}>"


class Issue(Base):
    """A problem found during verification, with a severity."""

    __tablename__ = "verification_issues"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_child_id)
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("verification_reports.id", ondelete="CASCADE"), index=True
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable form for the API."""
        return {"severity": self.severity, "code": self.code, "message": self.message}
