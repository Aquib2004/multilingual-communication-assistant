"""Date and time value parsing and normalisation.

This is where the "September 8 became September 9" class of bug is caught. A
value is parsed into a structured form so it can be compared *structurally*
rather than by string equality, which is what allows ``8:30 a.m.``, ``08:30``
and ``8:30 AM`` to be recognised as the same instant while ``8:00`` is not.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

MONTH_OF: dict[int, str] = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

# --- Month names -------------------------------------------------------------

MONTHS: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

#: Common abbreviated month forms used in Spanish, French and Portuguese.
FOREIGN_MONTHS: dict[str, int] = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "mar": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

_MONTH_ALTERNATION = "|".join(sorted(set(MONTHS) | set(FOREIGN_MONTHS), key=len, reverse=True))

#: Devanagari and Arabic-Indic digits, so non-Latin numerals still parse.
_DIGIT_MAP: dict[str, str] = {}
for _base in (0x0966, 0x0660, 0x06F0):
    for _i in range(10):
        _DIGIT_MAP[chr(_base + _i)] = str(_i)
DIGIT_TABLE = str.maketrans(_DIGIT_MAP)

#: "October 3", "3 October", "Oct. 3rd", "3 de octubre"
NAMED_DATE_PATTERN = re.compile(
    rf"\b(?P<month>{_MONTH_ALTERNATION})\.?\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?\b"
    rf"|\b(?P<day2>\d{{1,2}})(?:st|nd|rd|th)?\s+(?:de\s+|of\s+)?(?P<month2>{_MONTH_ALTERNATION})\b",
    re.IGNORECASE,
)

#: "10/03/2026" or "10-03-2026"
NUMERIC_DATE_PATTERN = re.compile(
    r"\b(?P<a>\d{1,4})\s*[/.\-]\s*(?P<b>\d{1,2})\s*[/.\-]\s*(?P<c>\d{1,4})\b"
)

#: "8:30 a.m.", "08:30", "6:00-7:00 p.m.", "8:30am"
TIME_PATTERN = re.compile(
    r"(?P<h>\d{1,2})\s*[:.]\s*(?P<m>\d{2})"
    r"(?:\s*(?P<start_meridiem>a\.?m\.?|p\.?m\.?))?"
    r"(?:\s*(?:[-–—]|to)\s*(?P<h2>\d{1,2})\s*[:.]\s*(?P<m2>\d{2})"
    r"(?:\s*(?P<end_meridiem>a\.?m\.?|p\.?m\.?))?)?",
    re.IGNORECASE,
)


class DateOrder(StrEnum):
    """How a locale orders the parts of a numeric date."""

    MDY = "MDY"
    DMY = "DMY"
    YMD = "YMD"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class DateValue:
    """A parsed date.

    ``year`` is ``None`` when the source omitted it. ``ambiguous`` marks a
    numeric date that could be read two ways; the comparator escalates those to
    human review instead of guessing.
    """

    raw: str
    month: int
    day: int
    year: int | None = None
    order: DateOrder = DateOrder.UNKNOWN
    ambiguous: bool = False

    def same_day(self, other: DateValue) -> bool:
        """True when both values fall on the same day and month."""
        return self.month == other.month and self.day == other.day

    def label(self) -> str:
        """A human-readable rendering for the fact map."""
        base = f"{MONTH_OF[self.month]} {self.day}"
        return f"{base}, {self.year}" if self.year else base


@dataclass(frozen=True, slots=True)
class TimeValue:
    """A parsed time, stored as minutes since midnight.

    Normalising to minutes is what makes ``8:30 a.m.`` and ``08:30`` compare
    equal, and what makes ``8:00 a.m.`` compare unequal to ``8:30 a.m.``.
    """

    raw: str
    hour: int
    minute: int
    end_hour: int | None = None
    end_minute: int | None = None

    @property
    def start_minutes(self) -> int:
        """Minutes since midnight for the start of the time."""
        return self.hour * 60 + self.minute

    @property
    def end_minutes(self) -> int | None:
        """Minutes since midnight for the end of a range, if there is one."""
        if self.end_hour is None or self.end_minute is None:
            return None
        return self.end_hour * 60 + self.end_minute

    def is_range(self) -> bool:
        """True when this value describes a span such as ``6:00-7:00 p.m.``"""
        return self.end_hour is not None


def normalize_digits(text: str) -> str:
    """Convert non-ASCII numerals to ASCII so parsing works across scripts."""
    return text.translate(DIGIT_TABLE)


def strip_accents(text: str) -> str:
    """Remove combining marks, so ``setiembre`` and ``septiembre`` compare."""
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC", "".join(c for c in decomposed if not unicodedata.combining(c))
    )


def to_int(value: str) -> int:
    """Parse digits written in any common script into an ``int``."""
    return int(normalize_digits(value))


def parse_named_date(text: str) -> DateValue | None:
    """Parse a date that names its month, in English or a common translation.

    Handles ``October 3``, ``Oct. 3rd``, ``3 October`` and ``3 de octubre``.
    Such a date is locale-independent: the month name itself identifies the
    month, so no day/month order question arises.
    """
    normalized = strip_accents(normalize_digits(text)).lower()
    match = NAMED_DATE_PATTERN.search(normalized)
    if not match:
        return None

    groups = match.groupdict()
    month_token = groups.get("month") or groups.get("month2") or ""
    day_token = groups.get("day") or groups.get("day2") or ""
    month = MONTHS.get(month_token) or FOREIGN_MONTHS.get(month_token)
    if month is None:
        return None

    day = to_int(day_token)
    if not 1 <= day <= 31:
        return None

    return DateValue(raw=match.group(0).strip(), month=month, day=day)


def parse_numeric_date(text: str, order: DateOrder = DateOrder.UNKNOWN) -> DateValue | None:
    """Parse ``10/03/2026`` style dates.

    A four-digit first component is a year, so the order is unambiguous.
    Otherwise the locale's ``order`` decides; when the order is unknown the
    result is returned marked ``ambiguous`` and the comparator escalates rather
    than guessing.
    """
    normalized = normalize_digits(text)
    match = NUMERIC_DATE_PATTERN.search(normalized)
    if not match:
        return None

    a, b, c = (to_int(match.group(key)) for key in ("a", "b", "c"))

    if len(match.group("a")) == 4:
        year, month, day, resolved = a, b, c, DateOrder.YMD
    elif len(match.group("c")) == 4:
        year, resolved = c, DateOrder.UNKNOWN
        if order == DateOrder.MDY:
            month, day = a, b
        elif order == DateOrder.DMY:
            month, day = b, a
        else:
            return DateValue(
                raw=match.group(0),
                month=a,
                day=b,
                year=c,
                order=DateOrder.UNKNOWN,
                ambiguous=True,
            )
    else:
        return None

    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return None

    return DateValue(raw=match.group(0), month=month, day=day, year=year, order=resolved)


def _meridiem_offset(token: str | None) -> int:
    """Convert a meridiem marker into an hour offset."""
    if not token:
        return 0
    return 12 if token.replace(".", "").lower().startswith("p") else 0


def _normalise_hour(hour: int, meridiem: str | None, fallback_offset: int = 0) -> int:
    """Fold a meridiem into a 24-hour value.

    ``12:00 a.m.`` is hour 0 and ``12:00 p.m.`` is hour 12. Without this,
    midnight and noon are routinely off by twelve.
    """
    if meridiem:
        offset = 12 if meridiem.replace(".", "").lower().startswith("p") else 0
        if hour == 12:
            return 0 if offset == 0 else 12
        return (hour % 12) + offset
    return (hour + fallback_offset) % 24


def parse_time(text: str) -> TimeValue | None:
    """Parse a time or time range such as ``6:00-7:00 p.m.``"""
    normalized = normalize_digits(text)
    match = TIME_PATTERN.search(normalized)
    if not match:
        return None

    minute = to_int(match.group("m"))
    if minute > 59:
        return None

    start_meridiem = match.group("start_meridiem")
    end_meridiem_token = match.group("end_meridiem")
    is_range = match.group("h2") is not None

    # In "6:00-7:00 p.m." the marker binds to the end of the range, so it
    # governs the whole range. Using only the start's marker would read the
    # range as 6 a.m. to 7 p.m.
    governing = start_meridiem or (end_meridiem_token if is_range else None)
    resolved_hour = _normalise_hour(to_int(match.group("h")), governing)

    end_hour: int | None = None
    end_minute: int | None = None
    if is_range:
        end_hour = _normalise_hour(
            to_int(match.group("h2")),
            end_meridiem_token or start_meridiem,
            _meridiem_offset(governing),
        )
        end_minute = to_int(match.group("m2"))
        if end_hour < resolved_hour:
            # A range that wraps midnight, e.g. 11:00 p.m. - 1:00 a.m.
            end_hour += 24

    return TimeValue(
        raw=match.group(0).strip(),
        hour=resolved_hour,
        minute=minute,
        end_hour=end_hour,
        end_minute=end_minute,
    )


def all_dates(text: str, order: DateOrder = DateOrder.UNKNOWN) -> list[DateValue]:
    """Every parseable date in ``text``.

    Named dates are matched first and their spans recorded, so a numeric regex
    cannot mis-read part of ``October 3`` as a bare number.
    """
    normalized = normalize_digits(text)
    lowered = strip_accents(normalized).lower()
    found: list[DateValue] = []
    spans: list[tuple[int, int]] = []

    for match in NAMED_DATE_PATTERN.finditer(lowered):
        parsed = parse_named_date(match.group(0))
        if parsed is not None:
            found.append(parsed)
            spans.append(match.span())

    for match in NUMERIC_DATE_PATTERN.finditer(normalized):
        if any(match.start() >= start and match.end() <= end for start, end in spans):
            continue
        parsed = parse_numeric_date(match.group(0), order)
        if parsed is not None:
            found.append(parsed)

    return found


def all_times(text: str) -> list[TimeValue]:
    """Every parseable time in ``text``."""
    results: list[TimeValue] = []
    for match in TIME_PATTERN.finditer(normalize_digits(text)):
        parsed = parse_time(match.group(0))
        if parsed is not None:
            results.append(parsed)
    return results


def parse_any_date(text: str, order: DateOrder = DateOrder.UNKNOWN) -> DateValue | None:
    """Parse a date in either named or numeric form."""
    return parse_named_date(text) or parse_numeric_date(text, order)
