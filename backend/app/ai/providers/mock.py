"""A fully offline provider, so the project runs with no API key.

This is a rule engine, not a model. It exists so a contributor can clone the
repository and exercise the entire pipeline - rewrite, translate, verify,
back-translate - with no credentials, no network, and no cost.

It is deliberately honest about its limits: anything it cannot handle is
returned as an explicit uncertainty rather than a confident guess.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from app.ai.base import (
    AIProvider,
    AIRequest,
    AIResponse,
    BackTranslationOutput,
    RewriteChanges,
    RewriteOutput,
    ToneOutput,
    TranslationOutput,
)
from app.ai.mock_glossary import back_translate_offline, translate_offline
from app.ai.mock_rules import ALL_REWRITE_RULES, tidy_sentences
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

#: Phrases that mean the source has no usable deadline.
VAGUE_DEADLINE = re.compile(
    r"\b(soon|shortly|asap|as soon as possible|in a timely manner|promptly"
    r"|at your earliest convenience|right away)\b",
    re.IGNORECASE,
)

#: Phrases that mean the source never says how to respond.
MISSING_CONTACT = re.compile(
    r"\b(contact the undersigned|reach out|get in touch|let us know)\b", re.IGNORECASE
)

#: Surface phrases that read as though translated word-for-word.
MECHANICAL_PHRASES: dict[str, list[str]] = {
    "es": ["en orden a", "a fin de", "en relación con", "por el presente"],
    "hi": ["ताकि", "इस संबंध में", "के संदर्भ में"],
    "ur": ["تاکہ", "کے حوالے سے", "اس سلسلے میں"],
}

#: Formal constructions in the source that usually survive translation intact.
FORMAL_PHRASES = [
    "be advised that",
    "pursuant to",
    "heretofore",
    "in the event that",
    "notwithstanding",
]


class MockProvider(AIProvider):
    """Deterministic offline provider.

    Attributes:
        name: Always ``mock``.
        model: Identifies the rule-engine version. It is stored on every record
            so an offline result is never mistaken for a model result.
    """

    name = "mock"
    model = "mock-rule-engine-1.0"

    def __init__(self, settings: Settings | None = None) -> None:
        """Accept settings for interface parity with the network providers.

        Args:
            settings: Unused. The mock makes no network calls and reads no
                credentials, which is the whole point of it.
        """
        del settings

    async def health(self) -> bool:
        """Always usable: this provider makes no network calls."""
        return True

    async def complete(self, request: AIRequest) -> AIResponse:
        """Produce a structured response without any network call.

        Args:
            request: The task and its context.

        Returns:
            An :class:`AIResponse` whose payload satisfies the request's schema.
        """
        started = time.perf_counter()

        handlers = {
            "rewrite": self._rewrite,
            "translate": self._translate,
            "back_translate": self._back_translate,
            "tone": self._tone,
        }
        handler = handlers.get(request.task)
        if handler is None:
            payload: dict[str, Any] = {
                "rewritten_message": self._source_from(request),
                "changes": [],
                "open_questions": [
                    "The offline provider does not implement this task. "
                    "Set AI_PROVIDER=openai or AI_PROVIDER=local to use a model."
                ],
            }
        else:
            payload = handler(request)

        # Validate before returning: the mock must obey the same contract as a
        # real provider, so a failure here is a genuine bug, not a shortcut.
        request.response_model.model_validate(payload)

        return AIResponse(
            data=payload,
            provider=self.name,
            model=self.model,
            response_model=request.response_model,
            raw_text=json.dumps(payload, ensure_ascii=False)[:2000],
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    # --- Task handlers ------------------------------------------------------

    def _source_from(self, request: AIRequest) -> str:
        """Pull the source text out of the rendered user prompt."""
        match = re.search(
            r"##\s*(?:Source message|Message to translate|Approved source[^\n]*|Message)\s*\n+(.+)",
            request.user_prompt,
            re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        return request.user_prompt.strip()

    def _rewrite(self, request: AIRequest) -> dict[str, Any]:
        """Apply the plain-language rule table and explain every change."""
        source = self._source_from(request)
        revised = source
        changes: list[RewriteChanges] = []
        seen_codes: set[str] = set()

        for rule in ALL_REWRITE_RULES:
            matches = list(rule.pattern.finditer(revised))
            if not matches:
                continue
            before = revised
            revised = rule.pattern.sub(rule.replacement, revised)
            if revised == before or rule.reason_code in seen_codes:
                continue
            seen_codes.add(rule.reason_code)
            changes.append(
                RewriteChanges(
                    original=matches[0].group(0).strip(),
                    revised=rule.replacement.strip() or "(removed)",
                    reason=rule.reason,
                )
            )

        revised = tidy_sentences(revised)

        return RewriteOutput(
            rewritten_message=revised,
            changes=changes,
            open_questions=self._open_questions(source),
            reading_level=self._reading_level(revised),
            protected_items_preserved=self._placeholders_intact(source, revised),
        ).model_dump()

    def _translate(self, request: AIRequest) -> dict[str, Any]:
        """Glossary translation, preserving placeholders exactly."""
        source = self._source_from(request)
        language = str(request.metadata.get("target_language", "es"))

        text, missing = translate_offline(source, language)

        # The glossary operates on whole phrases, so a placeholder inside a
        # phrase could be lost. Report it rather than shipping a broken line.
        for placeholder in re.findall(r"<(P\d+)>", source):
            if placeholder not in text:
                missing.append(f"placeholder {placeholder} was not preserved")

        uncertainties = [f"No offline entry for: {phrase}" for phrase in missing]
        if uncertainties:
            uncertainties.append(
                "This is an offline glossary translation, not a model translation. "
                "A fluent reviewer must confirm the whole message before it is sent."
            )

        return TranslationOutput(
            translated_message=text,
            uncertainties=sorted(set(uncertainties)),
            terminology_notes=self._terminology_notes(source),
            tone_assessment="welcoming" if self._is_warm(source) else "neutral",
            reading_level_note="Offline glossary output; not a model translation.",
        ).model_dump()

    def _back_translate(self, request: AIRequest) -> dict[str, Any]:
        """Bring a target-language line back to English and compare it."""
        language = str(request.metadata.get("target_language", "es"))
        source_sentence = str(request.metadata.get("source_sentence", ""))
        translated = str(request.metadata.get("translated_sentence", ""))

        back = back_translate_offline(translated, language)
        issues: list[str] = []

        for token in re.findall(r"<(P\d+)>", translated):
            if token not in back:
                issues.append(f"Protected item {token} was lost in translation.")

        source_numbers = re.findall(r"\d+", source_sentence)
        back_numbers = re.findall(r"\d+", back)
        if source_numbers and source_numbers != back_numbers:
            issues.append(
                f"Numbers differ: the source has {source_numbers}, "
                f"the back-translation has {back_numbers}."
            )

        return BackTranslationOutput(
            back_translated=back,
            meaning_preserved=not issues,
            issues=issues,
        ).model_dump()

    def _tone(self, request: AIRequest) -> dict[str, Any]:
        """Flag mechanical phrasing and terminology for a human to judge."""
        language = str(request.metadata.get("target_language", "es"))
        source = str(request.metadata.get("source_text", ""))
        translated = str(request.metadata.get("translated_text", ""))

        lowered = translated.lower()
        mechanical = [
            phrase for phrase in MECHANICAL_PHRASES.get(language, []) if phrase in lowered
        ]
        mechanical += [p for p in FORMAL_PHRASES if p in source.lower()]

        return ToneOutput(
            tone=self._assess_tone(translated),
            mechanical_phrases=mechanical,
            cultural_awkwardness=[],
            terminology_notes=self._terminology_notes(source),
            requires_human_review=True,
        ).model_dump()

    # --- Helpers ------------------------------------------------------------

    @staticmethod
    def _is_warm(text: str) -> bool:
        """True when the source reads as welcoming rather than administrative."""
        lowered = text.lower()
        return any(word in lowered for word in ("thank", "please", "welcome", "invited", "glad"))

    @staticmethod
    def _assess_tone(text: str) -> str:
        """A coarse tone label from surface cues."""
        lowered = text.lower()
        if any(word in lowered for word in ("must", "required", "mandatory", "immediately")):
            return "alarming"
        if any(word in lowered for word in ("please", "thank", "welcome", "invited")):
            return "welcoming"
        return "neutral"

    @staticmethod
    def _placeholders_intact(before: str, after: str) -> bool:
        """True when every placeholder survived the rewrite."""
        return set(re.findall(r"<(P\d+)>", before)) <= set(re.findall(r"<(P\d+)>", after))

    @staticmethod
    def _open_questions(source: str) -> list[str]:
        """Ambiguities a human must resolve before translating."""
        questions: list[str] = []

        if VAGUE_DEADLINE.search(source):
            questions.append(
                "The source has no usable deadline. Add a real date so families know "
                "exactly when to respond."
            )
        if not re.search(
            r"\b(january|february|march|april|may|june|july|august|september"
            r"|october|november|december)\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            source,
            re.IGNORECASE,
        ):
            questions.append(
                "No date was found. If a response is expected by a particular date, "
                "add it so it can be verified in translation."
            )
        if not re.search(
            r"\b\d{3}[-.\s]\d{3,4}\b|\b\w+@\w+\.\w+\b|\bhttps?://|\bcall\b|\bemail\b|\blink\b",
            source,
            re.IGNORECASE,
        ):
            questions.append(
                "No clear response path was found. Add how families can ask a "
                "question or request an interpreter."
            )
        if MISSING_CONTACT.search(source):
            questions.append(
                "The source says to get in touch without saying how. Name the office, "
                "the role, and a phone number or email address."
            )
        return questions

    @staticmethod
    def _reading_level(text: str) -> dict[str, Any]:
        """Simple readability signals for the revised source."""
        sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
        lengths = [len(s.split()) for s in sentences] or [0]
        return {
            "avg_sentence_length": round(sum(lengths) / len(sentences), 1) if sentences else 0.0,
            "longest_sentence_words": max(lengths),
            "passive_voice_detected": bool(
                re.search(r"\b(is|are|was|were|be|been|being)\s+\w+ed\b", text, re.IGNORECASE)
            ),
            "total_words": len(text.split()),
        }

    @staticmethod
    def _terminology_notes(source: str) -> list[str]:
        """Flag recurring school terms whose local sense must be confirmed."""
        from app.verification.fact_extractor import AMBIGUOUS_TERMS
        from app.verification.normalisation import strip_accents

        lowered = strip_accents(source).lower()
        return [f"'{term}': {note}" for term, note in AMBIGUOUS_TERMS.items() if term in lowered]
