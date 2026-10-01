"""Escalation: route high-consequence content to a human process.

The specification is explicit that for safety, health, legal rights,
discipline, disability services, and emergencies, the AI output must not be
presented as final. This service is where that rule is enforced.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.verification.risk_classifier import (
    HIGH_RISK_ESCALATION_NOTE,
    RISK_LEVELS,
    RiskAssessment,
    RiskTier,
    classify_risk,
)

logger = get_logger(__name__)


class EscalationService:
    """Decide whether a message needs professional human review."""

    def assess(self, text: str, declared_level: str | RiskTier | None = None) -> RiskAssessment:
        """Classify risk and attach the required review guidance.

        Args:
            text: The message to assess.
            declared_level: The level the user selected, used as a floor.

        Returns:
            A :class:`RiskAssessment`. For ``HIGH`` it carries the escalation
            note and the professional-process requirements.
        """
        assessment = classify_risk(text, declared_level)

        if assessment.is_escalated:
            logger.info(
                "high-consequence content detected",
                level=assessment.level.value,
                categories=[item.category for item in assessment.evidence],
            )

        return assessment

    @staticmethod
    def escalation_note() -> str:
        """The exact guidance string required for high-consequence content."""
        return HIGH_RISK_ESCALATION_NOTE

    @staticmethod
    def review_requirements(level: str | RiskTier) -> list[str]:
        """The review a given risk level requires."""
        return [str(item) for item in RISK_LEVELS[RiskTier(level)]["review_requirements"]]

    @staticmethod
    def ai_output_is_final(level: str | RiskTier) -> bool:
        """Whether AI output may be treated as final for this level.

        Always ``False`` for high-consequence content. ``False`` for the other
        levels too, because this tool never certifies a translation; the UI
        still shows a human-review requirement.
        """
        return False
