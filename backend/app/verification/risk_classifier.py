"""Risk classification and escalation guidance.

The greater the consequences of an error, the more thorough the verification
must be. This module decides which tier a message falls into and what review it
therefore requires.

A user-declared level acts as a **floor**, never a ceiling: declaring a
suspension letter "routine" still returns ``HIGH``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypedDict


class RiskLevelInfo(TypedDict):
    """Static metadata for one risk tier.

    A TypedDict rather than ``dict[str, object]``: the latter erases the field
    types, so every consumer needs a cast and mypy cannot check any of it.
    """

    label: str
    description: str
    examples: list[str]
    review_requirements: list[str]


class RiskTier(StrEnum):
    """Consequence tiers."""

    ROUTINE = "routine"
    MODERATE = "moderate"
    HIGH = "high"

    @property
    def severity(self) -> int:
        """Ordering, so the highest triggered category wins."""
        order = {RiskTier.ROUTINE: 0, RiskTier.MODERATE: 1, RiskTier.HIGH: 2}
        return order[self]


#: The exact guidance string the specification requires for high risk.
HIGH_RISK_ESCALATION_NOTE = (
    "Professional human translation or interpretation is recommended for this "
    "high-consequence message."
)

#: Categories that always make a message high consequence.
HIGH_RISK_CATEGORIES: dict[str, list[str]] = {
    "safety": [
        "emergency",
        "evacuate",
        "evacuation",
        "fire drill",
        "lockdown",
        "active shooter",
        "shelter in place",
        "threat",
        "weapon",
        "armed",
        "danger",
        "hazardous",
        "chemical spill",
        "gas leak",
        "injury",
    ],
    "health": [
        "medication",
        "prescription",
        "dose",
        "allergy",
        "allergic",
        "asthma",
        "diabetes",
        "epilepsy",
        "seizure",
        "infection",
        "contagious",
        "quarantine",
        "medical",
        "health plan",
        "immunization",
    ],
    "legal_rights": [
        "appeal",
        "due process",
        "your rights",
        "legal",
        "attorney",
        "lawyer",
        "custody",
        "court",
        "hearing",
        "grievance",
        "entitled to",
        "entitled",
        "eligible for",
        "under the law",
    ],
    "discipline": [
        "suspended",
        "suspension",
        "expelled",
        "expulsion",
        "detention",
        "discipline",
        "disciplinary",
        "misconduct",
        "violation of",
        "behavior plan",
        "behaviour plan",
        "restriction on participation",
    ],
    "disability_services": [
        "individualized education program",
        "iep",
        "504 plan",
        "accommodation",
        "disability",
        "disabled student",
        "special education",
        "related service",
        "speech therapy",
        "occupational therapy",
        "assistive technology",
    ],
    "child_safety": [
        "custody",
        "abuse",
        "neglect",
        "safeguarding",
        "mandated reporter",
        "child protection",
        "safe haven",
        "runaway",
        "missing student",
    ],
}

#: Categories that make a message moderate consequence.
MODERATE_RISK_CATEGORIES: dict[str, list[str]] = {
    "permission_and_consent": [
        "permission",
        "consent",
        "authorize",
        "authorise",
        "opt in",
        "opt-in",
        "opt out",
        "opt-out",
        "release form",
        "media release",
        "photo",
        "photograph",
        "video",
        "field trip",
        "excursion",
        "off campus",
        "off-campus",
    ],
    "schedule_change": [
        "schedule change",
        "start time",
        "end time",
        "dismissal",
        "early release",
        "late start",
        "will start",
        "start at",
        "starts at",
        "instead of",
        "delayed",
        "rescheduled",
        "moved to",
        "cancelled",
        "canceled",
        "closed",
        "snow day",
        "remote learning",
        "distance learning",
        "half day",
    ],
    "participation": [
        "participation",
        "participate",
        "required to",
        "mandatory",
        "sign up",
        "register",
        "enroll",
        "enrolment",
        "enrollment",
        "volunteer",
        "requirement",
        "must bring",
        "must wear",
        "uniform",
    ],
    "response_path": [
        "reply by",
        "respond by",
        "return the form",
        "sign and return",
        "submit the",
        "provide consent",
        "confirm your",
    ],
}

#: Phrases that look high-risk but are routine, so a false alarm is avoided.
NEGATIVE_CONTEXT = [
    "first aid",
    "first-aid training",
    "health curriculum",
    "health education",
    "safety drill practice",
    "sample",
    "example",
    "test message",
    "hypothetical",
    "for a training exercise",
]

RISK_LEVELS: dict[RiskTier, RiskLevelInfo] = {
    RiskTier.ROUTINE: {
        "label": "Routine",
        "description": "A welcome note, event reminder, or classroom update.",
        "examples": ["welcome note", "event reminder", "classroom update", "newsletter"],
        "review_requirements": [
            "AI draft and fact check are sufficient as a first pass.",
            "Bilingual review by a fluent reviewer when one is available.",
        ],
    },
    RiskTier.MODERATE: {
        "label": "Moderate consequence",
        "description": "Instructions tied to participation, permission, or a schedule change.",
        "examples": [
            "permission request",
            "schedule change",
            "participation instructions",
            "consent form",
        ],
        "review_requirements": [
            "Use the organisation's approved workflow.",
            "A fluent reviewer must sign off before sending.",
            "Confirm the response path actually works in every target language.",
        ],
    },
    RiskTier.HIGH: {
        "label": "High consequence",
        "description": (
            "Safety, health, legal rights, discipline, disability services, or emergencies."
        ),
        "examples": [
            "safety notice",
            "health instruction",
            "disability services",
            "legal rights",
            "discipline",
            "emergency",
        ],
        "review_requirements": [
            "Do not rely on AI output alone for this content.",
            "Use the organisation's approved professional translation or "
            "interpretation process.",
            "Confirm any legal or rights language with the responsible office.",
            "Offer an interpretation option in the response path.",
            HIGH_RISK_ESCALATION_NOTE,
        ],
    },
}


@dataclass(slots=True)
class RiskEvidence:
    """Why a category was triggered, so the user can check the reasoning."""

    category: str
    matched: list[str] = field(default_factory=list)
    excerpt: str = ""

    def to_dict(self) -> dict[str, object]:
        """JSON-serialisable form for the API."""
        return {"category": self.category, "matched": self.matched, "excerpt": self.excerpt}


@dataclass(slots=True)
class RiskAssessment:
    """The assigned level plus everything that led to it."""

    level: RiskTier
    evidence: list[RiskEvidence] = field(default_factory=list)
    declared_by_user: RiskTier | None = None
    escalation_note: str | None = None

    @property
    def is_escalated(self) -> bool:
        """True when the message must go to a professional process."""
        return self.level is RiskTier.HIGH

    @property
    def review_requirements(self) -> list[str]:
        """The review this level requires."""
        return list(RISK_LEVELS[self.level]["review_requirements"])

    def to_dict(self) -> dict[str, object]:
        """JSON-serialisable form for the API.

        The API layer calls this when building an escalation response, so its
        absence would be a runtime error rather than a typing nit.
        """
        return {
            "level": self.level.value,
            "declared_by_user": self.declared_by_user.value if self.declared_by_user else None,
            "evidence": [item.to_dict() for item in self.evidence],
            "escalation_note": self.escalation_note,
            "review_requirements": self.review_requirements,
        }


def _normalise(text: str) -> str:
    """Lowercase and collapse whitespace for phrase matching."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _matches_for(text: str, phrases: list[str]) -> tuple[list[str], str]:
    """Which phrases occur in ``text``, plus a short excerpt around the first."""
    hits: list[str] = []
    first_index = -1

    for phrase in phrases:
        index = text.find(phrase)
        if index == -1:
            continue
        hits.append(phrase)
        if first_index == -1 or index < first_index:
            first_index = index

    if first_index == -1:
        return hits, ""

    start = max(0, first_index - 30)
    end = min(len(text), first_index + 60)
    return hits, f"...{text[start:end].strip()}..."


def classify_risk(text: str, declared_level: str | RiskTier | None = None) -> RiskAssessment:
    """Classify the consequence tier of a message.

    Keyword hits are grouped by category. The highest tier triggered wins, and
    a user-declared tier can only raise the result, never lower it.

    Args:
        text: The message to classify.
        declared_level: The level the user selected in the UI, if any.

    Returns:
        A :class:`RiskAssessment` with the level and the evidence behind it.
    """
    normalized = _normalise(text)
    evidence: list[RiskEvidence] = []
    detected = RiskTier.ROUTINE

    for category, phrases in HIGH_RISK_CATEGORIES.items():
        hits, excerpt = _matches_for(normalized, phrases)
        if hits:
            evidence.append(RiskEvidence(category, hits, excerpt))
            detected = RiskTier.HIGH

    for category, phrases in MODERATE_RISK_CATEGORIES.items():
        hits, excerpt = _matches_for(normalized, phrases)
        if hits:
            evidence.append(RiskEvidence(category, hits, excerpt))
            if detected is RiskTier.ROUTINE:
                detected = RiskTier.MODERATE

    # Suppress false alarms when the text is explicitly about a sample or a
    # training exercise rather than about a real family.
    if detected is RiskTier.HIGH and any(m in normalized for m in NEGATIVE_CONTEXT):
        hits, excerpt = _matches_for(normalized, NEGATIVE_CONTEXT)
        evidence.append(RiskEvidence("de-escalation-context", hits, excerpt))
        detected = RiskTier.MODERATE

    declared = RiskTier(declared_level) if declared_level else None
    candidates = [detected, *([declared] if declared else [])]
    final = max(candidates, key=lambda tier: tier.severity)

    return RiskAssessment(
        level=final,
        evidence=evidence,
        declared_by_user=declared,
        escalation_note=HIGH_RISK_ESCALATION_NOTE if final is RiskTier.HIGH else None,
    )
