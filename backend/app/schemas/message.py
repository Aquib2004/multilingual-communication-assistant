"""Request/response schemas for the Communication Workspace (messages)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.common import (
    ApiModel,
    MessageStateEnum,
    PIIFindingSchema,
    ProtectedItemTypeEnum,
    ReadingLevelSchema,
    RiskLevelEnum,
)
from app.schemas.translation import TranslationResponse
from app.schemas.verification import VerificationReportResponse

#: Longest accepted source message, in characters.
MAX_MESSAGE_CHARS = 5000


class ProtectedItemInput(ApiModel):
    """A fact the user has explicitly declared must not change."""

    item_type: ProtectedItemTypeEnum
    value: str = Field(min_length=1, max_length=500)
    must_match_exactly: bool = False


class ProtectedItemResponse(ApiModel):
    """An extracted protected item."""

    id: str
    item_type: ProtectedItemTypeEnum
    value: str
    placeholder: str
    must_match_exactly: bool
    start_offset: int | None = None
    end_offset: int | None = None
    context_sentence: str | None = None
    source: str = "auto"


class MessageCreateRequest(ApiModel):
    """Create a workspace: BRIDGE step B plus the source text."""

    source_message: str = Field(
        min_length=1,
        max_length=MAX_MESSAGE_CHARS,
        description="The original message. Use fictional or de-identified content only.",
    )
    audience: str = Field(default="", max_length=255)
    purpose: str = Field(default="", max_length=500)
    action: str = Field(default="", max_length=500)
    deadline: str = Field(default="", max_length=255)
    contact_path: str = Field(default="", max_length=500)
    tone: str = Field(default="warm, respectful, direct", max_length=255)
    risk_level: RiskLevelEnum = RiskLevelEnum.ROUTINE
    target_languages: list[str] = Field(default_factory=list, max_length=10)
    locale: str = Field(default="en-US", max_length=35)
    protected_items: list[ProtectedItemInput] = Field(default_factory=list, max_length=100)

    @field_validator("source_message")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            msg = "source_message must not be blank"
            raise ValueError(msg)
        return value.strip()


class RewriteRequest(ApiModel):
    """Run the plain-language engine, standalone or against a saved message."""

    message_id: str | None = Field(
        default=None, description="Existing workspace to revise. Omit for a one-off rewrite."
    )
    source_message: str | None = Field(
        default=None, max_length=MAX_MESSAGE_CHARS, description="One-off source text."
    )

    def resolved_text(self, existing: str | None = None) -> str:
        """Return the text to revise.

        Args:
            existing: The saved source, when ``message_id`` was supplied.

        Returns:
            The source text to rewrite.

        Raises:
            ValueError: If neither a message id nor source text was provided.
        """
        if self.source_message and self.source_message.strip():
            return self.source_message.strip()
        if existing:
            return existing
        msg = "Provide either 'message_id' or 'source_message'."
        raise ValueError(msg)


class ChangeSummary(ApiModel):
    """One 'what changed / why' entry from the plain-language engine."""

    original: str = Field(description="The wording before the change.")
    revised: str = Field(description="The wording after the change.")
    reason: str = Field(description="Why the change improves clarity without altering meaning.")


class RewriteResponse(ApiModel):
    """The plain-language revision, for the user's approval."""

    message_id: str | None = None
    rewritten_message: str
    changes: list[ChangeSummary] = Field(default_factory=list)
    open_questions: list[str] = Field(
        default_factory=list,
        description="Ambiguities the engine could not resolve. These must be answered "
        "before translating, not guessed at.",
    )
    reading_level: ReadingLevelSchema = Field(default_factory=ReadingLevelSchema)
    pii_warnings: list[PIIFindingSchema] = Field(default_factory=list)
    state: MessageStateEnum = MessageStateEnum.REVISED
    provider: str = "mock"
    model: str = "mock-rule-engine-1.0"


class ApproveRequest(ApiModel):
    """The human approval decision. The gate between revision and translation."""

    approved: bool = Field(description="True to approve the revised source for translation.")
    reviewer: str | None = Field(
        default=None,
        max_length=120,
        description="Initials or a name. Optional. Do not enter personal contact details.",
    )
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("notes")
    @classmethod
    def _notes_required_when_rejecting(cls, value: str | None, info: Any) -> str | None:
        if info.data.get("approved") is False and not (value and value.strip()):
            msg = "notes are required when rejecting a revision so the next pass can improve it"
            raise ValueError(msg)
        return value


class RejectRequest(ApiModel):
    """Send a revision back with feedback."""

    notes: str = Field(min_length=3, max_length=2000)


class MessageResponse(ApiModel):
    """A full workspace, including every downstream stage."""

    id: str
    state: MessageStateEnum
    audience: str
    purpose: str
    action: str
    deadline: str
    contact_path: str
    tone: str
    locale: str
    risk_level: RiskLevelEnum

    source_message: str
    revised_message: str | None = None
    changes: list[dict[str, Any]] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    reading_level: dict[str, Any] | None = None

    approved_message: str | None = None
    approved_at: datetime | None = None
    approved_by: str | None = None
    reviewer_feedback: str | None = None

    target_languages: list[str] = Field(default_factory=list)
    pii_warnings: list[dict[str, Any]] = Field(default_factory=list)

    protected_items: list[ProtectedItemResponse] = Field(default_factory=list)
    translations: list[TranslationResponse] = Field(default_factory=list)
    verification_reports: list[VerificationReportResponse] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime


class MessageListResponse(ApiModel):
    """A page of workspaces."""

    items: list[MessageResponse]
    total: int
    limit: int
    offset: int
