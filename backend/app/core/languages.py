"""Supported-language registry.

Adding a language means adding one entry here. The API, the verification engine
and the UI all read this registry, so no other change is required.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import UnsupportedLanguageError


@dataclass(frozen=True, slots=True)
class Language:
    """Metadata for one language the assistant can translate into."""

    code: str
    """ISO 639-1 code, e.g. ``es``."""

    name: str
    """Endonym, e.g. ``Español``."""

    english_name: str
    script: str
    direction: str = "ltr"
    reading_level_hint: str = ""
    term_support: str = "partial"
    """``full``, ``partial`` or ``none`` - how well the offline mock provider
    can handle this language without a network call."""

    @property
    def is_rtl(self) -> bool:
        """True for right-to-left scripts such as Arabic."""
        return self.direction == "rtl"

    def to_dict(self) -> dict[str, str]:
        """A JSON-serialisable representation for the API."""
        return {
            "code": self.code,
            "name": self.name,
            "english_name": self.english_name,
            "script": self.script,
            "direction": self.direction,
            "reading_level_hint": self.reading_level_hint,
            "term_support": self.term_support,
        }


#: The source language. All pipeline stages operate English -> target.
SOURCE_LANGUAGE = Language(
    code="en",
    name="English",
    english_name="English",
    script="Latin",
    direction="ltr",
    reading_level_hint="Aim for a grade 6-8 reading level.",
    term_support="full",
)

LANGUAGES: tuple[Language, ...] = (
    Language(
        code="es",
        name="Español",
        english_name="Spanish",
        script="Latin",
        reading_level_hint=(
            "Use 'usted' unless the school writes to families informally. "
            "Avoid Latin America / Spain mixing."
        ),
        term_support="full",
    ),
    Language(
        code="hi",
        name="हिन्दी",
        english_name="Hindi",
        script="Devanagari",
        reading_level_hint="Use natural everyday Hindi, not translated English word order.",
        term_support="full",
    ),
    Language(
        code="ur",
        name="اردو",
        english_name="Urdu",
        script="Arabic",
        direction="rtl",
        reading_level_hint=(
            "Urdu is right-to-left. Use vocabulary a family would recognise; "
            "borrow an English term rather than inventing one when unsure."
        ),
        term_support="partial",
    ),
)

_LANGUAGES_BY_CODE: dict[str, Language] = {lang.code: lang for lang in LANGUAGES}


@dataclass(frozen=True, slots=True)
class Locale:
    """A specific regional variant of a language."""

    tag: str
    language_code: str
    region: str
    date_order: str = "MDY"
    """``MDY`` (US), ``DMY`` (Europe/LatAm), ``YMD`` (East Asia).

    Used by the fact comparator to decide whether a numeric date is ambiguous.
    """

    time_format: str = "12h"
    currency: str = "$"
    notes: str = ""


LOCALES: tuple[Locale, ...] = (
    Locale("en-US", "en", "US", "MDY", "12h", "$"),
    Locale("es-US", "es", "US", "MDY", "12h", "$", "Spanish in the United States."),
    Locale("es-MX", "es", "MX", "DMY", "24h", "$", "Spanish in Mexico."),
    Locale("hi-IN", "hi", "IN", "DMY", "24h", "₹", "Hindi in India."),
    Locale("ur-PK", "ur", "PK", "DMY", "12h", "₨", "Urdu in Pakistan."),
)

_LOCALES_BY_TAG: dict[str, Locale] = {loc.tag: loc for loc in LOCALES}


def get_language(code: str) -> Language:
    """Look up a target language by code.

    Args:
        code: ISO 639-1 code, case-insensitive.

    Returns:
        The matching :class:`Language`.

    Raises:
        UnsupportedLanguageError: If the code is not registered.
    """
    normalized = code.strip().lower()
    if normalized not in _LANGUAGES_BY_CODE:
        supported = ", ".join(sorted(_LANGUAGES_BY_CODE))
        raise UnsupportedLanguageError(
            f"Language {code!r} is not supported. Supported languages: {supported}.",
            details={"supported": sorted(_LANGUAGES_BY_CODE)},
        )
    return _LANGUAGES_BY_CODE[normalized]


def is_supported(code: str) -> bool:
    """True when ``code`` names a registered target language."""
    return code.strip().lower() in _LANGUAGES_BY_CODE


def get_locale(tag: str) -> Locale | None:
    """Look up a locale by BCP-47 tag, returning ``None`` when unknown.

    An unknown locale is not an error: the pipeline still works, but ambiguous
    numeric dates get escalated to human review rather than guessed.
    """
    return _LOCALES_BY_TAG.get(tag.strip())


def resolve_locale(tag: str | None, language_code: str) -> Locale | None:
    """Resolve a locale, falling back to the language's first known locale."""
    if tag:
        found = get_locale(tag)
        if found is not None:
            return found
    for locale in LOCALES:
        if locale.language_code == language_code.lower():
            return locale
    return None


def list_languages() -> tuple[Language, ...]:
    """All registered target languages."""
    return LANGUAGES
