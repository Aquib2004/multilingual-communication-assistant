"""Structural comparison of protected items between source and translation.

This module assigns every status in the fact map. It is deterministic: the same
source and translation always produce the same verdict, regardless of which
model produced the translation.

Status meanings:

* ``PASS`` - the fact is present and equivalent.
* ``WARNING`` - present but expressed differently (a locale convention changed
  the surface form without changing the fact).
* ``FAIL`` - missing, or contradicted (a different day, time, or number).
* ``REVIEW_REQUIRED`` - cannot be decided automatically. Never guessed.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from app.core.languages import Locale
from app.verification.fact_extractor import ExtractedItem
from app.verification.normalisation import (
    DateOrder,
    DateValue,
    TimeValue,
    all_dates,
    all_times,
    normalize_digits,
    parse_any_date,
    parse_time,
    strip_accents,
)


class CheckStatus(StrEnum):
    """The status of one fact-map row."""

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW"
    ESCALATED = "ESCALATED"

    @property
    def severity(self) -> int:
        """Ranking used to roll a report up to a single overall status."""
        order = {
            CheckStatus.PASS: 0,
            CheckStatus.WARNING: 1,
            CheckStatus.REVIEW_REQUIRED: 2,
            CheckStatus.FAIL: 3,
            CheckStatus.ESCALATED: 4,
        }
        return order[self]


@dataclass(slots=True)
class FactCheckResult:
    """One row of the fact map."""

    item_type: str
    source_value: str
    translated_value: str | None
    status: CheckStatus
    detail: str = ""

    @property
    def is_problem(self) -> bool:
        """True when this row needs a human to look at it."""
        return self.status in (CheckStatus.FAIL, CheckStatus.REVIEW_REQUIRED)

    def to_dict(self) -> dict[str, str | None]:
        """JSON-serialisable form for the API."""
        return {
            "item_type": self.item_type,
            "source": self.source_value,
            "translated": self.translated_value,
            "status": self.status.value,
            "detail": self.detail,
        }


def _fold(text: str) -> str:
    """Normalise text for tolerant string comparison.

    Lowercases, strips accents, and collapses whitespace and punctuation, so
    ``Family Curriculum Night.`` and ``family curriculum night`` compare equal
    while a genuinely different phrase still differs.
    """
    decomposed = unicodedata.normalize("NFD", strip_accents(text).lower())
    without_punctuation = re.sub(r"[^\w\s]", " ", decomposed)
    return re.sub(r"\s+", " ", without_punctuation).strip()


def _digits(text: str) -> str:
    """Every digit in the text, in order, for numeric comparison."""
    return "".join(ch for ch in normalize_digits(text) if ch.isdigit())


def _date_order(locale: Locale | None) -> DateOrder:
    """Map a locale's date order onto the parser's enum."""
    if locale is None:
        return DateOrder.UNKNOWN
    return {"MDY": DateOrder.MDY, "DMY": DateOrder.DMY, "YMD": DateOrder.YMD}.get(
        locale.date_order, DateOrder.UNKNOWN
    )


def _signature_word(sentence: str) -> str:
    """The most distinctive word in a sentence, for locating its translation."""
    words = list(re.findall(r"[A-Za-z]{4,}", sentence.lower()))
    skip = {"please", "thank", "will", "have", "your", "with", "from", "should"}
    for candidate in words:
        if candidate not in skip:
            return candidate
    return words[0] if words else ""


def _describe_window(text: str, value: DateValue | TimeValue) -> str:
    """A short excerpt of ``text`` around ``value``, for the fact map.

    Showing surrounding context makes a verdict reviewable: a reviewer can see
    that ``8:00`` appears in a sentence about arrival, not about something else.
    """
    index = text.find(value.raw)
    if index == -1:
        return value.raw
    start = max(0, index - 25)
    end = min(len(text), index + len(value.raw) + 25)
    return text[start:end].strip()


def _find_translation_candidate(item: ExtractedItem, translation: str) -> tuple[str | None, str]:
    """Locate the translated counterpart of a source item.

    Items carrying an exact literal (URL, email) are searched for literally.
    Dates and times are located with the parser rather than by substring, so a
    locale's date ordering is handled correctly. Everything else is located by
    the digits or distinctive words of the sentence it came from.

    Args:
        item: The source item.
        translation: The translated text.

    Returns:
        A ``(candidate_text, detail)`` pair. ``candidate_text`` is ``None`` when
        nothing plausible was located.
    """
    value = item.value.strip()

    if item.item_type in {"url", "email"}:
        if value.lower() in translation.lower():
            return value, "Found verbatim in the translation."
        return None, "The literal value does not appear in the translation."

    if item.item_type == "phone":
        source_digits = _digits(value)
        if source_digits and source_digits in _digits(translation):
            return value, "Found in the translation."
        return None, "The phone number's digits do not appear in the translation."

    if item.item_type in {"date", "datetime"}:
        if parse_any_date(value, DateOrder.UNKNOWN) is not None:
            for candidate in all_dates(translation, DateOrder.UNKNOWN):
                return (
                    _describe_window(translation, candidate),
                    "Located a date in the translation.",
                )
        return None, "No date was found in the translation."

    if item.item_type == "time":
        if parse_time(value) is not None:
            for candidate in all_times(translation):
                return (
                    _describe_window(translation, candidate),
                    "Located a time in the translation.",
                )
        return None, "No time was found in the translation."

    if item.item_type == "number":
        source_digits = _digits(value)
        if not source_digits or source_digits not in _digits(translation):
            return None, "The number does not appear in the translation."
        return value, "Found in the translation."

    # Semantic items: locate the sentence that carried the item in the source.
    sentence = item.context_sentence or value
    signature = _digits(sentence) or _signature_word(sentence)
    if signature and signature.lower() in strip_accents(translation).lower():
        return sentence, "Located the sentence containing this item."
    return None, "The corresponding text was not located in the translation."


def _compare_date(
    source_value: str, translation: str, locale: Locale | None
) -> tuple[CheckStatus, str]:
    """Compare a source date against every date in the translation.

    The verdict is ``FAIL`` when the translation contains a date that does not
    match, and ``PASS`` when a matching date is present. A translation that
    contains no date at all is a ``FAIL`` - a dropped deadline is exactly the
    failure this project exists to catch.
    """
    order = _date_order(locale)
    source_date = parse_any_date(source_value, order)
    if source_date is None:
        return CheckStatus.REVIEW_REQUIRED, "The source date could not be parsed."

    if source_date.ambiguous:
        return CheckStatus.REVIEW_REQUIRED, (
            f"'{source_value}' is ambiguous without a locale convention. A fluent reviewer "
            f"must confirm the intended date."
        )

    candidates = all_dates(translation, order)
    if not candidates:
        return CheckStatus.FAIL, "No date appears in the translation."

    for candidate in candidates:
        if candidate.ambiguous:
            continue
        if source_date.same_day(candidate) and (
            source_date.year is None or candidate.year is None or source_date.year == candidate.year
        ):
            detail = "The same calendar date is present."
            if candidate.raw != source_date.raw:
                detail = (
                    f"'{candidate.raw}' is the same date written in the target locale's format."
                )
            return CheckStatus.PASS, detail

    found = ", ".join(candidate.raw for candidate in candidates)
    return CheckStatus.FAIL, (
        f"The translation states {found}, which is not {source_date.label()}. "
        f"The deadline has changed."
    )


def _compare_time(source_value: str, translation: str) -> tuple[CheckStatus, str]:
    """Compare a source time against every time in the translation.

    ``8:30 a.m.`` and ``08:30`` are the same instant and pass. ``8:00`` does not
    match ``8:30`` and fails.
    """
    source_time = parse_time(source_value)
    if source_time is None:
        return CheckStatus.REVIEW_REQUIRED, "The source time could not be parsed."

    candidates = all_times(translation)
    if not candidates:
        return CheckStatus.FAIL, "No time appears in the translation."

    for candidate in candidates:
        same_start = candidate.start_minutes == source_time.start_minutes
        if not same_start:
            continue
        if source_time.is_range():
            if candidate.end_minutes == source_time.end_minutes:
                return CheckStatus.PASS, "The same start and end times are present."
            return CheckStatus.FAIL, (
                f"The range ends at a different time ({candidate.raw}). "
                f"The source range is {source_value}."
            )
        return CheckStatus.PASS, "The same time is present."

    found = ", ".join(candidate.raw for candidate in candidates)
    return CheckStatus.FAIL, (
        f"The translation states {found}, which is not the same time as {source_value}."
    )


URL_LABEL_IN_SOURCE = re.compile(
    r"\b(click|use the link|at the link|register|rsvp|sign up)\b", re.I
)
URL_LABEL_IN_TRANSLATION = re.compile(
    r"\b(click|haga clic|use el enlace|enlace|registr|confirme|inscr)\b", re.I
)


def compare_fact(
    item: ExtractedItem, source_text: str, translation: str, locale: Locale | None = None
) -> FactCheckResult:
    """Compare one protected item between the source and the translation.

    The check is chosen by item type. Literal values are compared exactly, dates
    and times structurally, and semantic items (actions, conditions, contacts,
    proper nouns) by structural presence plus a mandatory human look.

    Args:
        item: The protected item extracted from the source.
        source_text: The full approved source.
        translation: The translated text.
        locale: Locale hint for numeric date disambiguation.

    Returns:
        A :class:`FactCheckResult`. Semantic items never return ``PASS``
        automatically: a fluent reader, not a script, decides whether
        "may attend" became "must attend".
    """
    if not translation or not translation.strip():
        return FactCheckResult(
            item.item_type, item.value, None, CheckStatus.FAIL, "The translation is empty."
        )

    if item.item_type in {"date", "datetime"}:
        status, detail = _compare_date(item.value, translation, locale)
        return FactCheckResult(item.item_type, item.value, translation, status, detail)

    if item.item_type == "time":
        status, detail = _compare_time(item.value, translation)
        return FactCheckResult(item.item_type, item.value, translation, status, detail)

    if item.must_match_exactly or item.item_type in {"url", "email", "phone", "address", "code"}:
        candidate, detail = _find_translation_candidate(item, translation)
        if candidate is None:
            return FactCheckResult(item.item_type, item.value, None, CheckStatus.FAIL, detail)
        exact = _fold(candidate) == _fold(item.value) or item.value in translation
        return FactCheckResult(
            item.item_type,
            item.value,
            candidate,
            CheckStatus.PASS if exact else CheckStatus.WARNING,
            detail,
        )

    if item.item_type == "number":
        source_digits = _digits(item.value)
        if not source_digits:
            return FactCheckResult(
                item.item_type,
                item.value,
                None,
                CheckStatus.REVIEW_REQUIRED,
                "The number could not be read.",
            )
        present = source_digits in _digits(translation)
        return FactCheckResult(
            item.item_type,
            item.value,
            item.value if present else None,
            CheckStatus.PASS if present else CheckStatus.FAIL,
            (
                "The number is present in the translation."
                if present
                else f"The number {item.value} does not appear in the translation."
            ),
        )

    # --- Semantic items: presence is checkable, meaning is not ---------------
    # A word-level search cannot establish semantics across languages: the verb
    # for "bring" in the target language will never contain the letters of
    # "bring". So an unlocatable semantic item is ALWAYS REVIEW_REQUIRED, never
    # FAIL. Asserting a drop here would manufacture false alarms and train
    # reviewers to ignore the table.
    #
    # Genuine semantic failures come from the two checks that can reason about
    # meaning: the completeness check (sentence loss) and back-translation.
    candidate, detail = _find_translation_candidate(item, translation)
    if candidate is None:
        return FactCheckResult(
            item.item_type,
            item.value,
            None,
            CheckStatus.REVIEW_REQUIRED,
            f"{detail} This could not be checked automatically - meaning must be "
            f"confirmed by a fluent reviewer, not asserted from word matching.",
        )
    return FactCheckResult(
        item.item_type,
        item.value,
        candidate,
        CheckStatus.REVIEW_REQUIRED,
        f"{detail} A fluent reviewer must confirm the meaning was preserved.",
    )


def build_fact_map(
    items: list[ExtractedItem],
    source_text: str,
    translation: str,
    locale: Locale | None = None,
) -> list[FactCheckResult]:
    """Compare every protected item, producing the fact map."""
    return [compare_fact(item, source_text, translation, locale) for item in items]


def check_completeness(
    source_text: str, translation: str, items: list[ExtractedItem]
) -> list[FactCheckResult]:
    """Functional-layer checks: sentence count and link usability.

    A translation much shorter than its source has probably dropped content,
    even when every individual fact passed. A link whose describing
    instruction disappeared is unusable, however intact the URL itself is.
    """
    results: list[FactCheckResult] = []

    source_sentences = [s for s in re.split(r"(?<=[.!?])\s+", source_text) if s.strip()]
    target_sentences = [s for s in re.split(r"(?<=[.!?])\s+", translation) if s.strip()]

    if len(target_sentences) < len(source_sentences):
        results.append(
            FactCheckResult(
                "completeness",
                f"{len(source_sentences)} sentences",
                f"{len(target_sentences)} sentences",
                CheckStatus.FAIL,
                "The translation has fewer sentences than the source. "
                "Content may have been dropped.",
            )
        )
    else:
        results.append(
            FactCheckResult(
                "completeness",
                f"{len(source_sentences)} sentences",
                f"{len(target_sentences)} sentences",
                CheckStatus.PASS,
                "No sentences were lost in translation.",
            )
        )

    source_has_label = bool(URL_LABEL_IN_SOURCE.search(source_text))
    target_has_label = bool(URL_LABEL_IN_TRANSLATION.search(translation))

    for item in items:
        if item.item_type != "url":
            continue
        url_present = item.value in translation
        label_ok = not source_has_label or target_has_label
        ok = url_present and label_ok
        results.append(
            FactCheckResult(
                "functional",
                item.value,
                item.value if url_present else None,
                CheckStatus.PASS if ok else CheckStatus.FAIL,
                (
                    "The link and the instruction describing it are both present."
                    if ok
                    else "The link is missing, or the instruction that describes it was dropped."
                ),
            )
        )

    return results


def overall_status(checks: list[FactCheckResult], escalated: bool = False) -> CheckStatus:
    """Roll a list of checks into a single status.

    The worst status wins. A high-risk message is reported as ``ESCALATED``
    regardless of how clean its fact map is, because "all facts passed" is not
    the same as "this is safe to send".
    """
    if escalated:
        return CheckStatus.ESCALATED
    if not checks:
        return CheckStatus.REVIEW_REQUIRED
    return max((check.status for check in checks), key=lambda status: status.severity)


def summarise(checks: list[FactCheckResult]) -> dict[str, int]:
    """Counts by status, for the report header."""
    counts = {
        "total": len(checks),
        "passed": 0,
        "warnings": 0,
        "failures": 0,
        "review_required": 0,
    }
    for check in checks:
        if check.status is CheckStatus.PASS:
            counts["passed"] += 1
        elif check.status is CheckStatus.WARNING:
            counts["warnings"] += 1
        elif check.status is CheckStatus.FAIL:
            counts["failures"] += 1
        else:
            counts["review_required"] += 1
    return counts


def requires_human_review(checks: list[FactCheckResult], escalated: bool = False) -> bool:
    """True when a human must look at this before the message is sent.

    Semantic items always require review, so this is almost always true. That is
    the honest answer rather than a defect.
    """
    return escalated or any(check.is_problem for check in checks)
