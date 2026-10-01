"""Request/response schemas for verification, escalation, and reference data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import (
    ApiModel,
    RiskLevelEnum,
    SeverityEnum,
    VerificationStatusEnum,
)


class FactCheckResponse(ApiModel):
    """One row of the fact map."""

    item_type: str
    source: str
    translated: str | None = None
    status: VerificationStatusEnum
    detail: str | None = None


class BackTranslationPairResponse(ApiModel):
    """A source sentence, its back-translation, and the verdict."""

    source_sentence: str
    back_translated: str | None = None
    status: VerificationStatusEnum
    detail: str | None = None


class ToneAssessmentResponse(ApiModel):
    """Pragmatic and terminological review. Advisory only."""

    tone: str
    mechanical_phrases: list[str] = Field(default_factory=list)
    cultural_awkwardness: list[str] = Field(default_factory=list)
    terminology_notes: list[str] = Field(default_factory=list)
    status: VerificationStatusEnum = VerificationStatusEnum.REVIEW_REQUIRED


class IssueResponse(ApiModel):
    """A problem found during verification."""

    severity: SeverityEnum
    code: str
    message: str


class RiskEvidenceResponse(ApiModel):
    """Why a risk level was assigned."""

    category: str
    matched: list[str] = Field(default_factory=list)
    excerpt: str = ""


class RiskResponse(ApiModel):
    """The assigned risk level and the evidence behind it."""

    level: RiskLevelEnum
    declared_by_user: RiskLevelEnum | None = None
    evidence: list[RiskEvidenceResponse] = Field(default_factory=list)
    review_requirements: list[str] = Field(default_factory=list)


class VerificationSummaryResponse(ApiModel):
    """Counts by status, for the report header."""

    total: int = 0
    passed: int = 0
    warnings: int = 0
    failures: int = 0
    review_required: int = 0


class VerificationRequest(ApiModel):
    """Verify one translation."""

    translation_id: str = Field(min_length=1)
    reviewer: str | None = Field(
        default=None, max_length=120, description="Initials only. Optional."
    )


class VerificationReportResponse(ApiModel):
    """The durable verification record."""

    id: str
    message_id: str
    translation_id: str
    target_language: str
    overall_status: VerificationStatusEnum
    human_review_required: bool
    summary: VerificationSummaryResponse
    checks: list[FactCheckResponse] = Field(default_factory=list)
    back_translation: list[BackTranslationPairResponse] = Field(default_factory=list)
    tone_assessment: ToneAssessmentResponse
    issues: list[IssueResponse] = Field(default_factory=list)
    risk: RiskResponse
    escalation_note: str | None = None
    review_requirements: list[str] = Field(default_factory=list)
    provider: str
    model: str
    verified_at: datetime
    created_at: datetime


# --- Escalation --------------------------------------------------------------


class EscalationRequest(ApiModel):
    """Ask whether a message needs professional human translation."""

    text: str = Field(min_length=1, max_length=5000)
    declared_risk_level: RiskLevelEnum | None = Field(
        default=None,
        description="A declared level acts as a floor. The system may raise it.",
    )


class EscalationResponse(ApiModel):
    """Risk classification plus escalation guidance."""

    level: RiskLevelEnum
    declared_by_user: RiskLevelEnum | None = None
    evidence: list[RiskEvidenceResponse] = Field(default_factory=list)
    escalation_note: str | None = None
    review_requirements: list[str] = Field(default_factory=list)
    ai_output_is_final: bool = Field(
        default=False,
        description="Always false for HIGH risk. The system never marks AI output as final.",
    )


# --- Reference data ----------------------------------------------------------


class LanguageInfo(ApiModel):
    """A supported language, as shown in the language selector."""

    code: str
    name: str
    english_name: str
    script: str
    direction: str
    reading_level_hint: str = ""
    term_support: str = "partial"


class LanguagesResponse(ApiModel):
    """The registered source and target languages."""

    source: LanguageInfo
    targets: list[LanguageInfo]
    locales: list[str] = Field(default_factory=list)


class RiskLevelInfo(ApiModel):
    """One risk tier and what it requires."""

    level: RiskLevelEnum
    label: str
    description: str
    examples: list[str] = Field(default_factory=list)
    review_requirements: list[str] = Field(default_factory=list)


class RiskLevelsResponse(ApiModel):
    """All risk tiers."""

    levels: list[RiskLevelInfo]


class ExampleMessageResponse(ApiModel):
    """A bundled fictional demo message."""

    id: str
    title: str
    risk_level: RiskLevelEnum
    category: str = "routine"
    target_languages: list[str] = Field(default_factory=list)
    locale: str = "en-US"
    tone: str = ""
    audience: str = ""
    purpose: str = ""
    action: str = ""
    deadline: str = ""
    source_message: str = ""


class ExamplesResponse(ApiModel):
    """Every bundled demo message."""

    items: list[ExampleMessageResponse]
    total: int
    disclaimer: str = (
        "All examples are fictional and de-identified. No real names, phone numbers, "
        "email addresses, or student IDs are used."
    )


class HealthResponse(ApiModel):
    """Service health, including the active AI provider."""

    status: str
    app: str
    version: str
    environment: str
    ai_provider: str
    database: str
    timestamp: datetime
    details: dict[str, Any] = Field(default_factory=dict)
