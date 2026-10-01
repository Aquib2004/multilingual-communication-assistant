"""Request-scoped security helpers: request ids and PII screening.

The privacy goal is simple: a user pasting a draft into the workspace should not
accidentally ship a child's name or a phone number to a model provider. These
helpers detect that and warn, and the UI surfaces the warning.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

#: Bracketed placeholders such as [FAMILY NAME] or [PHONE]. These are safe.
PLACEHOLDER_PATTERN = re.compile(r"\[[A-Z0-9][A-Z0-9 _./-]*\]")

#: A likely real email address (example.org is the reserved documentation domain).
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@(?!example\.(?:org|com|net)\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

#: North-American style phone numbers, excluding the reserved 555-01xx block.
PHONE_PATTERN = re.compile(r"\b(?:\+1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")

#: Student / employee identifiers.
STUDENT_ID_PATTERN = re.compile(
    r"\b(?:student|emp|employee|pupil)[ _-]?(?:id|no|num|number)[:# ]*\S+", re.I
)

#: Common given names. Deliberately short and conservative: this is a prompt
#: for a human, not a verdict. It exists to catch "Call Maria about Juan" when
#: someone forgets to replace a name.
FIRST_NAME_PATTERN = re.compile(
    r"\b(?:Mr|Mrs|Ms|Miss|Dr)\.?\s+[A-Z][a-z]{2,15}\b"
    r"|\b(?:call|email|contact|ask)\s+[A-Z][a-z]{2,15}\s+(?:at|on|about|regarding)\b"
)

PRIVACY_WARNING = (
    "Use placeholders instead of real names, phone numbers, email addresses, or "
    "student IDs - for example [FAMILY NAME] or [PHONE]."
)


@dataclass(frozen=True, slots=True)
class PIIFinding:
    """A single suspected personal-data occurrence."""

    category: str
    """One of ``email``, ``phone``, ``student_id``, ``person_name``."""

    excerpt: str
    """The matched text, truncated. Used to warn the user, never to store."""

    @property
    def severity(self) -> str:
        """Advisory severity. Nothing here blocks the request on its own."""
        return "warning"


def new_request_id() -> str:
    """Generate a short, unique request identifier."""
    return uuid.uuid4().hex[:16]


def screen_for_pii(text: str) -> list[PIIFinding]:
    """Scan ``text`` for patterns that look like real personal data.

    Bracketed placeholders are removed first so ``[PHONE]`` is never flagged.

    Args:
        text: The user's draft.

    Returns:
        A list of findings. Empty means nothing suspicious was detected.
    """
    if not text:
        return []

    scrubbed = PLACEHOLDER_PATTERN.sub(" ", text)
    findings: list[PIIFinding] = []

    for match in EMAIL_PATTERN.finditer(scrubbed):
        findings.append(PIIFinding("email", _truncate(match.group(0))))

    for match in PHONE_PATTERN.finditer(scrubbed):
        digits = re.sub(r"\D", "", match.group(0))
        if _is_reserved_fictional(digits):
            continue
        findings.append(PIIFinding("phone", _truncate(match.group(0))))

    for match in STUDENT_ID_PATTERN.finditer(scrubbed):
        findings.append(PIIFinding("student_id", _truncate(match.group(0))))

    for match in FIRST_NAME_PATTERN.finditer(scrubbed):
        findings.append(PIIFinding("person_name", _truncate(match.group(0))))

    return findings


def _is_reserved_fictional(digits: str) -> bool:
    """True when the number falls in the reserved 555-01xx fictional block."""
    if len(digits) != 10:
        return False
    return digits[3:7] == "5550" or digits[3:7] == "5551"


def _truncate(value: str, limit: int = 40) -> str:
    """Shorten an excerpt so a warning never reproduces a full identifier."""
    return value if len(value) <= limit else f"{value[:limit]}..."
