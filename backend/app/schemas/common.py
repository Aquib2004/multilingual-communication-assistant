"""Shared schema primitives: the standard error envelope and enums."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Base for every request/response model.

    ``extra="forbid"`` makes a typo in a request body a loud 422 rather than a
    silently ignored field - important when a typo could mean a deadline was
    not set.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ErrorDetail(ApiModel):
    """The user-safe error payload."""

    code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="A message safe to show an end user.")
    details: dict[str, Any] | None = None


class ErrorResponse(ApiModel):
    """The envelope every non-2xx response uses."""

    error: ErrorDetail
    request_id: str | None = Field(default=None, description="Correlates with server logs.")


class RiskLevelEnum(StrEnum):
    """Risk levels, mirrored from the ORM enum for the API contract."""

    ROUTINE = "routine"
    MODERATE = "moderate"
    HIGH = "high"


class MessageStateEnum(StrEnum):
    """Message states, mirrored from the ORM enum for the API contract."""

    DRAFT = "draft"
    REVISED = "revised"
    APPROVED = "approved"
    TRANSLATED = "translated"
    VERIFIED = "verified"
    ESCALATED = "escalated"


class VerificationStatusEnum(StrEnum):
    """Check and report statuses."""

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW"
    ESCALATED = "ESCALATED"


class SeverityEnum(StrEnum):
    """Issue severity."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ProtectedItemTypeEnum(StrEnum):
    """Categories of protected information."""

    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    NUMBER = "number"
    MONEY = "money"
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"
    NAME = "name"
    PROGRAM = "program"
    PLACE = "place"
    DEADLINE = "deadline"
    ACTION = "action"
    CONDITION = "condition"
    CONTACT = "contact"
    ADDRESS = "address"
    CODE = "code"


class PIIFindingSchema(ApiModel):
    """A PII warning surfaced to the user."""

    category: str
    excerpt: str
    severity: str = "warning"


class ReadingLevelSchema(ApiModel):
    """Basic readability signals for the revised source.

    Deliberately permissive: the provider may compute additional indicators
    (total_words, Flesch score, and so on) and those must not be rejected just
    because this model does not name them. Use ``extra="allow"`` so a richer
    provider response still serialises instead of failing the request.
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    avg_sentence_length: float | None = None
    longest_sentence_words: int | None = None
    passive_voice_detected: bool = False
    nominalisations_detected: list[str] = Field(default_factory=list)
    note: str = "Indicative only. Readability scores are not a substitute for human review."
