"""Deterministic extraction of protected items from a message.

Pure regex and lookup work. No model call is required, so every protected item
the system relies on is found the same way in CI as in production.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.languages import Locale
from app.verification.normalisation import (
    DateOrder,
    all_dates,
    all_times,
    normalize_digits,
    strip_accents,
)

# --- Patterns ---------------------------------------------------------------

URL_PATTERN = re.compile(r"\b(?:https?://|www\.)[^\s<>()\[\]{}\"']+", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
MONEY_PATTERN = re.compile(
    r"(?:[$€£₹₨]|USD|EUR|GBP|INR|PKR)\s?\d[\d,]*(?:\.\d+)?"
    r"|\d[\d,]*(?:\.\d+)?\s?(?:USD|EUR|GBP|INR|PKR|dollars|euros|rupees)\b",
    re.IGNORECASE,
)
URL_LABEL_PATTERN = re.compile(
    r"\b(?:click (?:here|the link)|use the link|at the link|register online"
    r"|rsvp online|sign up (?:online|here)|via the (?:website|form|link))\b",
    re.IGNORECASE,
)
CONDITION_PATTERN = re.compile(
    r"\b(if you (?:would like|wish|are|have|can|need)|when you (?:would like|wish)"
    r"|should you (?:choose|wish|like)|optional|you may|you are welcome to"
    r"|please do not feel|only if|unless)\b",
    re.IGNORECASE,
)
ACTION_PATTERN = re.compile(
    r"\b(please\s+\w+|return|submit|sign|send|bring|complete|fill (?:out|in)"
    r"|rsvp|register|call|email|contact|pick ?up|drop ?off|attend|arrive"
    r"|reply|respond|review|read|notice|pay)\b",
    re.IGNORECASE,
)
ROLE_PATTERN = re.compile(
    r"\b((?:program|school|main|front|site)\s+"
    r"(?:office|desk|coordinator|administrator|secretary|librarian|nurse|counselor"
    r"|principal|office)\b"
    r"|\b(the\s+)?(?:principal|counselor|nurse|teacher|coordinator"
    r"|administrator|front desk|main office)\b)",
    re.IGNORECASE,
)
VAGUE_DEADLINE_PATTERN = re.compile(
    r"\b(soon|shortly|as soon as possible|asap|right away|promptly"
    r"|in a timely manner|at your earliest convenience|in due time"
    r"|before long|as early as possible)\b",
    re.IGNORECASE,
)
DEADLINE_CONTEXT_PATTERN = re.compile(
    r"\b(?:by|before|due|until|no later than|deadline)\s+([^.!?\n]{3,60})", re.IGNORECASE
)
NUMBER_WITH_UNIT_PATTERN = re.compile(
    r"\b\d{1,4}(?:[- ](?:minute|hour|day|week|page|grade|year|month))\b", re.IGNORECASE
)

#: Title-cased multiword sequences are the strongest proper-noun signal
#: available without a model, so they are always REVIEW_REQUIRED.
TITLE_CASE_SEQUENCE = re.compile(r"\b(?:[A-Z][a-z]+(?:\s+|$)){2,4}")

#: Words that look like a title but are ordinary sentence starts.
TITLE_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "if",
        "please",
        "we",
        "our",
        "your",
        "you",
        "thank",
        "questions",
        "contact",
        "bring",
        "return",
        "send",
        "join",
        "meet",
        "students",
        "families",
        "parents",
        "teachers",
        "children",
        "dear",
        "hello",
        "attention",
        "important",
        "reminder",
        "notice",
        "this",
        "that",
        "these",
        "those",
        "there",
        "here",
        "when",
        "while",
        "on",
        "in",
        "at",
        "to",
        "for",
        "and",
        "or",
        "but",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "can",
        "could",
        "will",
        "would",
        "should",
        "may",
        "might",
        "must",
        "not",
        "no",
        "yes",
        "all",
        "any",
        "each",
        "every",
        "some",
        "as",
        "by",
        "from",
        "with",
        "without",
    }
)

#: Recurring school/program terms whose correct sense is context dependent.
AMBIGUOUS_TERMS: dict[str, str] = {
    "conference": "Can mean a family-teacher meeting, a professional event, or a sports grouping.",
    "office": "Can mean a physical room, an administrative team, or a government position.",
    "field trip form": "May need a locally used school term rather than a literal phrase.",
    "referral": "Can mean a teacher referral, a service referral, or a discipline referral.",
    "placement": "Can mean a class placement, a job placement, or a legal placement order.",
    "counselor": (
        "School counselor, mental health professional, and academic adviser "
        "may differ by country."
    ),
    "attendance": "May mean presence at school, participation in an activity, or grades.",
    "credit": "Academic credit, financial credit, and leave credit are different things.",
    "excursion": "Systems use different words: field trip, school trip, outing, or visit.",
    "bus": "School bus, public bus, and coach services may be distinguished locally.",
}


@dataclass(slots=True)
class ExtractedItem:
    """One protected item found in a message.

    ``placeholder`` is the token the translation model sees instead of the
    value, e.g. ``P3``.
    """

    item_type: str
    value: str
    must_match_exactly: bool = False
    start_offset: int | None = None
    end_offset: int | None = None
    context_sentence: str | None = None
    source: str = "auto"
    placeholder: str = ""
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """JSON-serialisable form for the API and the database."""
        return {
            "item_type": self.item_type,
            "value": self.value,
            "must_match_exactly": self.must_match_exactly,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "context_sentence": self.context_sentence,
            "source": self.source,
            "placeholder": self.placeholder,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class ExtractionResult:
    """Everything found in one message, plus the questions that were raised."""

    items: list[ExtractedItem] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    vague_deadlines: list[str] = field(default_factory=list)
    terminology_notes: list[str] = field(default_factory=list)

    def by_type(self, item_type: str) -> list[ExtractedItem]:
        """All items of one type."""
        return [item for item in self.items if item.item_type == item_type]

    def values_for(self, item_type: str) -> list[str]:
        """Just the values of one type, in document order."""
        return [item.value for item in self.by_type(item_type)]


def _sentence_containing(text: str, offset: int) -> str:
    """The sentence surrounding ``offset``, for critical-line isolation."""
    if offset < 0:
        return ""
    start = text.rfind(".", 0, offset)
    start = 0 if start == -1 else start + 1
    end = text.find(".", offset)
    end = len(text) if end == -1 else end + 1
    return text[start:end].strip()


def _date_order_for(locale: Locale | None) -> DateOrder:
    """Map a locale's date order onto the parser's enum."""
    if locale is None:
        return DateOrder.UNKNOWN
    mapping = {"MDY": DateOrder.MDY, "DMY": DateOrder.DMY, "YMD": DateOrder.YMD}
    return mapping.get(locale.date_order, DateOrder.UNKNOWN)


def extract_protected_items(
    text: str,
    locale: Locale | None = None,
    user_items: list[ExtractedItem] | None = None,
) -> ExtractionResult:
    """Extract every protected item from ``text``.

    User-declared items are added first, so an explicit "this must not change"
    always wins over inference.

    Args:
        text: The approved source text.
        locale: Locale hint, used only for numeric date disambiguation.
        user_items: Items the user explicitly declared.

    Returns:
        An :class:`ExtractionResult` with deduplicated, ordered items.
    """
    result = ExtractionResult()
    if not text or not text.strip():
        result.open_questions.append("The message is empty. There is nothing to verify.")
        return result

    order = _date_order_for(locale)
    seen: set[tuple[str, str]] = set()

    def _add(item: ExtractedItem) -> None:
        key = (item.item_type, item.value.strip().lower())
        if not item.value.strip() or key in seen:
            return
        seen.add(key)
        if item.context_sentence is None and item.start_offset is not None:
            item.context_sentence = _sentence_containing(text, item.start_offset)
        result.items.append(item)

    # --- 1. Explicitly declared items win -----------------------------------
    for declared in user_items or []:
        declared.source = "user"
        _add(declared)

    normalized = normalize_digits(text)

    # --- 2. Literal identifiers ---------------------------------------------
    for match in URL_PATTERN.finditer(normalized):
        _add(ExtractedItem("url", match.group(0).rstrip(".,;"), True, match.start(), match.end()))
    for match in EMAIL_PATTERN.finditer(normalized):
        _add(ExtractedItem("email", match.group(0), True, match.start(), match.end()))
    for match in MONEY_PATTERN.finditer(normalized):
        _add(ExtractedItem("money", match.group(0).strip(), False, match.start(), match.end()))
    for match in NUMBER_WITH_UNIT_PATTERN.finditer(normalized):
        _add(ExtractedItem("number", match.group(0), False, match.start(), match.end()))

    # --- 3. Dates and times ---------------------------------------------------
    for date in all_dates(text, order):
        offset = text.find(date.raw)
        if offset == -1:
            offset = text.find(strip_accents(date.raw))
        if date.ambiguous:
            result.open_questions.append(
                f"The date '{date.raw}' uses a numeric format whose day/month order is "
                f"ambiguous. Spell it out (for example 'October 3') before sending."
            )
        _add(
            ExtractedItem(
                "date",
                date.raw,
                False,
                offset if offset >= 0 else None,
                metadata={"ambiguous": date.ambiguous, "order": date.order.value},
            )
        )

    for time in all_times(text):
        offset = text.find(time.raw)
        _add(
            ExtractedItem(
                "time",
                time.raw,
                False,
                offset if offset >= 0 else None,
                metadata={
                    "start_minutes": time.start_minutes,
                    "end_minutes": time.end_minutes,
                    "is_range": time.is_range(),
                },
            )
        )

    # --- 4. Deadlines ---------------------------------------------------------
    for match in DEADLINE_CONTEXT_PATTERN.finditer(normalized):
        _add(ExtractedItem("deadline", match.group(1).strip(), False, match.start(1), match.end(1)))
    for match in VAGUE_DEADLINE_PATTERN.finditer(normalized):
        result.vague_deadlines.append(match.group(0))
        result.open_questions.append(
            f"'{match.group(0)}' is not a usable deadline. Replace it with an actual "
            f"date or time so families know exactly when to respond."
        )

    # --- 5. Actions, conditions, contact paths -------------------------------
    for match in ACTION_PATTERN.finditer(normalized):
        phrase = match.group(0).strip()
        if len(phrase) >= 3:
            _add(ExtractedItem("action", phrase, False, match.start(), match.end()))

    for match in CONDITION_PATTERN.finditer(normalized):
        _add(ExtractedItem("condition", match.group(0).strip(), False, match.start(), match.end()))

    for match in URL_LABEL_PATTERN.finditer(normalized):
        _add(ExtractedItem("action", match.group(0).strip(), False, match.start(), match.end()))

    for match in ROLE_PATTERN.finditer(normalized):
        _add(ExtractedItem("contact", match.group(0).strip(), False, match.start(), match.end()))

    # --- 6. Proper nouns and program names -----------------------------------
    ambiguous_lower = {term.lower() for term in AMBIGUOUS_TERMS}
    for match in TITLE_CASE_SEQUENCE.finditer(text):
        candidate = match.group(0).strip()
        lowered = candidate.lower()
        if lowered in TITLE_STOPWORDS or lowered in ambiguous_lower:
            continue
        if any(lowered.startswith(word) for word in ("please ", "if ", "we ", "thank ")):
            continue
        _add(ExtractedItem("name", candidate, False, match.start(), match.end()))

    # --- 7. Terminology notes ------------------------------------------------
    lowered_text = strip_accents(text).lower()
    for term, note in AMBIGUOUS_TERMS.items():
        if term in lowered_text:
            result.terminology_notes.append(f"'{term}': {note}")

    result.items.sort(key=lambda item: (item.start_offset is None, item.start_offset or 0))
    for index, item in enumerate(result.items, start=1):
        item.placeholder = f"P{index}"

    if not result.by_type("date") and not result.by_type("deadline"):
        result.open_questions.append(
            "No date or deadline was found. If a response is expected by a particular "
            "date, add it so it can be verified in translation."
        )

    return result


def mask_placeholders(text: str, items: list[ExtractedItem]) -> tuple[str, dict[str, str]]:
    """Replace every protected value with a placeholder.

    This is the safety property of the whole translation stage: a date, URL or
    phone number is never *asked to be translated*. It is removed, translated
    around, then restored verbatim.

    Args:
        text: The approved source.
        items: Items to mask.

    Returns:
        The masked text and a ``{placeholder: original_value}`` mapping.
    """
    mapping: dict[str, str] = {}
    masked = text

    ordered = sorted(
        (item for item in items if item.value and item.placeholder),
        key=lambda item: len(item.value),
        reverse=True,
    )
    for item in ordered:
        if item.value in masked:
            mapping[item.placeholder] = item.value
            masked = masked.replace(item.value, f"<{item.placeholder}>")

    return masked, mapping


def restore_placeholders(text: str, mapping: dict[str, str]) -> tuple[str, list[str]]:
    """Put the original values back after translation.

    Args:
        text: The translated text containing placeholders.
        mapping: The mapping from :func:`mask_placeholders`.

    Returns:
        The restored text, and the placeholders the model dropped or corrupted.
        Dropping a placeholder means dropping a fact, so the caller must surface
        it rather than let it pass.
    """
    restored = text
    missing: list[str] = []

    for placeholder, value in mapping.items():
        token = f"<{placeholder}>"
        if token in restored:
            restored = restored.replace(token, value)
            continue
        # Tolerate cosmetic variants such as <P1 > or ⟨P1⟩, but record it.
        loose = re.search(rf"[<⟨(]\s*{re.escape(placeholder)}\s*[>⟩)]", restored)
        if loose:
            restored = restored.replace(loose.group(0), value)
        else:
            missing.append(f"{placeholder} ({value})")

    return restored, missing
