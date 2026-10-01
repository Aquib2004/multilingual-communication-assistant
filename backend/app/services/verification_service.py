"""Verification service: assemble the durable verification record.

The report answers the three questions the project is required to answer: what
was checked, what was revised, and what still needs a human.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import AIProvider, AIRequest, BackTranslationOutput, ToneOutput
from app.ai.prompts.translation import (
    BACK_TRANSLATION_SYSTEM,
    BACK_TRANSLATION_USER,
    TONE_SYSTEM,
    TONE_USER,
)
from app.core.errors import TranslationNotFoundError
from app.core.languages import get_language, resolve_locale
from app.core.logging import get_logger
from app.models.message import Message, MessageState
from app.models.protected_item import ProtectedItem
from app.models.translation import Translation
from app.models.verification import (
    BackTranslationPair,
    FactCheck,
    Issue,
    ToneAssessment,
    VerificationReport,
    VerificationStatus,
)
from app.services.escalation_service import EscalationService
from app.verification.fact_comparator import (
    CheckStatus,
    FactCheckResult,
    build_fact_map,
    check_completeness,
    overall_status,
    requires_human_review,
    summarise,
)
from app.verification.fact_extractor import ExtractedItem

logger = get_logger(__name__)

#: Item types whose sentence is worth back-translating.
CRITICAL_ITEM_TYPES = frozenset({"deadline", "action", "condition", "contact"})


class VerificationService:
    """Produce and persist verification reports for a translation."""

    def __init__(self, provider: AIProvider) -> None:
        """Bind the AI provider.

        Args:
            provider: The configured :class:`AIProvider`.
        """
        self._provider = provider

    async def get(self, session: AsyncSession, report_id: str) -> VerificationReport:
        """Fetch a report or raise.

        Args:
            session: Active database session.
            report_id: The report identifier.

        Returns:
            The :class:`VerificationReport`.

        Raises:
            TranslationNotFoundError: If no such report exists.
        """
        report = await session.get(VerificationReport, report_id)
        if report is None:
            raise TranslationNotFoundError("Verification report not found.")
        return report

    async def verify(self, session: AsyncSession, translation: Translation) -> VerificationReport:
        """Run every verification layer and persist the report.

        Layers, in order: the deterministic fact map, completeness and link
        usability, back-translation of critical lines, tone and terminology, and
        risk escalation.

        Args:
            session: Active database session.
            translation: The translation to verify.

        Returns:
            The persisted :class:`VerificationReport`.
        """
        message = await session.get(Message, translation.message_id)
        if message is None:
            raise TranslationNotFoundError("Parent message not found.")

        source_text = message.approved_message or message.source_message
        language = get_language(translation.target_language)
        locale = resolve_locale(translation.locale, translation.target_language)
        items = self._items_from(message.protected_items)

        # --- Deterministic layers -------------------------------------------
        fact_checks = build_fact_map(items, source_text, translation.translated_message, locale)
        fact_checks += check_completeness(source_text, translation.translated_message, items)

        # --- Back-translation of critical lines -------------------------------
        pairs = await self._back_translate_items(translation, items, source_text, language.name)

        # --- Tone and terminology ---------------------------------------------
        tone = await self._assess_tone(translation, source_text, language.code, language.name)

        # --- Risk and escalation ----------------------------------------------
        risk = EscalationService().assess(source_text, message.risk_level.value)
        escalated = risk.level.value == "high"

        all_checks = fact_checks + [
            FactCheckResult(
                item_type="back_translation",
                source_value=pair.source_sentence,
                translated_value=pair.back_translated,
                status=CheckStatus(pair.status),
                detail=pair.detail or "",
            )
            for pair in pairs
        ]

        status = overall_status(all_checks, escalated=escalated)
        report = VerificationReport(
            message_id=message.id,
            translation_id=translation.id,
            target_language=translation.target_language,
            overall_status=status.value,
            human_review_required=requires_human_review(all_checks, escalated),
            summary=summarise(all_checks),
            risk_level=risk.level.value,
            risk_evidence=[item.to_dict() for item in risk.evidence],
            risk_declared_by_user=risk.declared_by_user.value if risk.declared_by_user else None,
            escalation_note=risk.escalation_note,
            review_requirements=risk.review_requirements,
            provider=translation.provider,
            model=translation.model,
        )

        for check in fact_checks:
            report.checks.append(
                FactCheck(
                    item_type=check.item_type,
                    source_value=check.source_value,
                    translated_value=check.translated_value,
                    status=check.status.value,
                    detail=check.detail,
                )
            )

        report.back_translation_pairs = list(pairs)
        report.tone = ToneAssessment(
            tone=tone.tone,
            mechanical_phrases=tone.mechanical_phrases,
            cultural_awkwardness=tone.cultural_awkwardness,
            terminology_notes=tone.terminology_notes,
            status=VerificationStatus.REVIEW_REQUIRED.value,
        )

        self._attach_issues(report, all_checks, translation.uncertainties, escalated)
        session.add(report)
        message.state = MessageState.ESCALATED if escalated else MessageState.VERIFIED
        await session.flush()

        logger.info(
            "verification complete",
            translation_id=translation.id,
            status=status.value,
            failures=summarise(all_checks)["failures"],
            escalated=escalated,
        )
        return report

    # --- Layers -------------------------------------------------------------

    async def _back_translate_items(
        self,
        translation: Translation,
        items: list[ExtractedItem],
        source_text: str,
        language_name: str,
    ) -> list[BackTranslationPair]:
        """Back-translate the sentences that carry critical items.

        The action, deadline, condition, and contact instructions are where
        meaning is most often lost, so those sentences are isolated from the
        translation and brought back to English for comparison.

        Args:
            translation: The translation under review.
            items: The protected items.
            source_text: The approved English source.
            language_name: The target language's display name.

        Returns:
            One :class:`BackTranslationPair` per distinct critical sentence.
        """
        pairs: list[BackTranslationPair] = []
        seen: set[str] = set()

        for item in items:
            if item.item_type not in CRITICAL_ITEM_TYPES:
                continue
            source_sentence = (item.context_sentence or "").strip()
            if not source_sentence or source_sentence in seen:
                continue
            seen.add(source_sentence)

            translated_sentence = self._find_translated_sentence(
                translation.translated_message, source_sentence
            )

            request = AIRequest(
                task="back_translate",
                system_prompt=BACK_TRANSLATION_SYSTEM.format(
                    target_language=language_name, source_language="English"
                ),
                user_prompt=BACK_TRANSLATION_USER.format(
                    source_language="English",
                    target_language=language_name,
                    source_sentence=source_sentence,
                    translated_sentence=translated_sentence,
                ),
                response_model=BackTranslationOutput,
                temperature=0.0,
                metadata={
                    "target_language": translation.target_language,
                    "source_sentence": source_sentence,
                    "translated_sentence": translated_sentence,
                },
            )

            response = await self._provider.complete(request)
            output = BackTranslationOutput.model_validate(response.data)

            status = CheckStatus.PASS if output.meaning_preserved else CheckStatus.FAIL
            detail = (
                "The action, deadline, and condition came back unchanged."
                if output.meaning_preserved
                else "; ".join(output.issues)
            )

            pairs.append(
                BackTranslationPair(
                    source_sentence=source_sentence,
                    back_translated=output.back_translated,
                    status=status.value,
                    detail=detail,
                )
            )

        translation.back_translation = "\n".join(pair.back_translated or "" for pair in pairs)
        return pairs

    @staticmethod
    def _find_translated_sentence(translated: str, source_sentence: str) -> str:
        """Locate the sentence in the translation that mirrors a source sentence.

        A positional match is the best available signal once placeholders are
        restored: the sentences are in the same order, and the protected values
        are identical on both sides.
        """
        source_fragments = [s.strip() for s in source_sentence.split(".") if s.strip()]
        target_sentences = [s.strip() for s in translated.split(".") if s.strip()]

        for position, fragment in enumerate(source_fragments):
            if position < len(target_sentences) and len(fragment.split()) >= 4:
                return target_sentences[position]

        return target_sentences[0] if target_sentences else translated

    async def _assess_tone(
        self,
        translation: Translation,
        source_text: str,
        language_code: str,
        language_name: str,
    ) -> ToneOutput:
        """Review tone, cultural naturalness, and terminology."""
        request = AIRequest(
            task="tone",
            system_prompt=TONE_SYSTEM,
            user_prompt=TONE_USER.format(
                source_language="English",
                target_language=language_name,
                source_text=source_text,
                translated_text=translation.translated_message,
            ),
            response_model=ToneOutput,
            temperature=0.0,
            metadata={
                "target_language": language_code,
                "source_text": source_text,
                "translated_text": translation.translated_message,
            },
        )
        response = await self._provider.complete(request)
        return ToneOutput.model_validate(response.data)

    @staticmethod
    def _attach_issues(
        report: VerificationReport,
        checks: list[FactCheckResult],
        uncertainties: list[str],
        escalated: bool,
    ) -> None:
        """Turn check results and model uncertainties into report issues."""
        for check in checks:
            if check.status is CheckStatus.FAIL:
                report.issues.append(
                    Issue(
                        severity="error",
                        code="FACT_MISMATCH",
                        message=f"{check.item_type}: {check.detail}",
                    )
                )
            elif check.status is CheckStatus.WARNING:
                report.issues.append(
                    Issue(
                        severity="warning",
                        code="DIFFERENT_FORM",
                        message=f"{check.item_type}: {check.detail}",
                    )
                )

        for note in uncertainties:
            report.issues.append(Issue(severity="warning", code="MODEL_UNCERTAINTY", message=note))

        if escalated:
            report.issues.append(
                Issue(
                    severity="error",
                    code="ESCALATED_HIGH_RISK",
                    message=str(report.escalation_note),
                )
            )

    @staticmethod
    def _items_from(rows: list[ProtectedItem]) -> list[ExtractedItem]:
        """Convert stored protected items into extractor objects."""
        return [
            ExtractedItem(
                item_type=row.item_type.value,
                value=row.value,
                must_match_exactly=row.must_match_exactly,
                start_offset=row.start_offset,
                end_offset=row.end_offset,
                context_sentence=row.context_sentence,
                source=row.source,
                placeholder=row.placeholder,
            )
            for row in rows
        ]


# Re-exported so the API layer can import the status enum from one place.
__all__ = ["VerificationService", "VerificationStatus"]
