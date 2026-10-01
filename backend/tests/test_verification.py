"""Verification: the fact map, mismatch detection, and completeness checks."""

from __future__ import annotations

import pytest

from app.core.languages import get_locale
from app.verification.fact_comparator import (
    CheckStatus,
    build_fact_map,
    check_completeness,
    compare_fact,
    overall_status,
    requires_human_review,
    summarise,
)
from app.verification.fact_extractor import ExtractedItem, extract_protected_items

LOCALE_ES = get_locale("es-US")

SOURCE = "Please bring the permission form on September 8 at 8:30 a.m."


def _checks(source: str, translation: str) -> list:
    """Extract items from ``source`` and compare them against ``translation``."""
    items = extract_protected_items(source, LOCALE_ES).items
    return build_fact_map(items, source, translation, LOCALE_ES)


def _by_type(checks: list, item_type: str) -> list:
    """All checks of one item type."""
    return [check for check in checks if check.item_type == item_type]


class TestDateMismatch:
    """A shifted deadline must be caught, not glossed over."""

    def test_day_shift_fails(self) -> None:
        """September 8 rendered as 9 de septiembre is a FAIL."""
        checks = _checks(SOURCE, "Por favor, traiga el formulario el 9 de septiembre.")
        dates = _by_type(checks, "date")
        assert dates
        assert dates[0].status is CheckStatus.FAIL

    def test_correct_date_passes(self) -> None:
        """The same date in the target locale's format is a PASS."""
        checks = _checks(SOURCE, "Por favor, traiga el formulario el 8 de septiembre.")
        assert _by_type(checks, "date")[0].status is CheckStatus.PASS

    def test_dropped_date_fails(self) -> None:
        """A translation with no date at all is a FAIL, not a pass."""
        checks = _checks("RSVP by October 3.", "Confirme su asistencia.")
        assert _by_type(checks, "date")[0].status is CheckStatus.FAIL

    def test_ambiguous_numeric_date_requires_review(self) -> None:
        """A date with no known day/month order escalates instead of guessing."""
        item = ExtractedItem("date", "10/03/2026")
        result = compare_fact(item, "Meet on 10/03/2026.", "Reunión el 10/03/2026.", None)
        assert result.status is CheckStatus.REVIEW_REQUIRED


class TestTimeMismatch:
    """A shifted start time must be caught."""

    def test_thirty_minute_shift_fails(self) -> None:
        """8:30 a.m. rendered as 8:00 is a FAIL."""
        checks = _checks(SOURCE, "Por favor, traiga el formulario a las 8:00.")
        assert _by_type(checks, "time")[0].status is CheckStatus.FAIL

    def test_twenty_four_hour_form_passes(self) -> None:
        """08:30 is the same instant as 8:30 a.m. and must pass."""
        checks = _checks(SOURCE, "Por favor, traiga el formulario a las 08:30.")
        assert _by_type(checks, "time")[0].status is CheckStatus.PASS

    def test_both_mismatches_reported_independently(self) -> None:
        """A green check must never mask a red one."""
        translation = "Por favor, traiga el formulario el 9 de septiembre a las 8:00."
        checks = _checks(SOURCE, translation)
        assert _by_type(checks, "date")[0].status is CheckStatus.FAIL
        assert _by_type(checks, "time")[0].status is CheckStatus.FAIL
        assert overall_status(checks) is CheckStatus.FAIL

    def test_correct_translation_has_no_hard_failures(self) -> None:
        """A faithful translation produces no date or time failures."""
        translation = "Por favor, traiga el formulario el 8 de septiembre a las 8:30."
        checks = _checks(SOURCE, translation)
        assert [c for c in checks if c.status is CheckStatus.FAIL] == []


class TestLiteralItems:
    """URLs, emails, and phone numbers must survive character for character."""

    def test_url_must_be_present(self) -> None:
        """A dropped link is a FAIL."""
        item = ExtractedItem("url", "https://example.org/rsvp", must_match_exactly=True)
        result = compare_fact(item, "RSVP at https://example.org/rsvp", "Confirme.", None)
        assert result.status is CheckStatus.FAIL

    def test_url_preserved_passes(self) -> None:
        """An intact link passes."""
        item = ExtractedItem("url", "https://example.org/rsvp", must_match_exactly=True)
        result = compare_fact(
            item,
            "RSVP at https://example.org/rsvp",
            "Confirme en https://example.org/rsvp",
            None,
        )
        assert result.status is CheckStatus.PASS

    def test_phone_digits_compared(self) -> None:
        """Phone comparison is digit-wise, so formatting may change."""
        item = ExtractedItem("phone", "+1-555-0100", must_match_exactly=True)
        result = compare_fact(item, "Call +1-555-0100.", "Llame al +1 555 0100.", None)
        assert result.status is CheckStatus.PASS

    def test_number_must_match(self) -> None:
        """A changed number is a FAIL."""
        item = ExtractedItem("number", "24")
        result = compare_fact(item, "We need 24 volunteers.", "Necesitamos 20 voluntarios.", None)
        assert result.status is CheckStatus.FAIL


class TestSemanticItems:
    """Meaning cannot be decided by word matching, so these are REVIEW."""

    def test_action_is_review_not_pass(self) -> None:
        """A located action still needs a fluent reviewer."""
        item = ExtractedItem("action", "Please bring")
        result = compare_fact(
            item, "Please bring the form.", "Por favor traiga el formulario.", None
        )
        assert result.status is CheckStatus.REVIEW_REQUIRED

    def test_unlocatable_semantic_item_is_review_not_fail(self) -> None:
        """Asserting a drop from word matching would manufacture false alarms."""
        item = ExtractedItem("action", "Please bring")
        result = compare_fact(
            item, "Please bring the form.", "Por favor traiga el formulario.", None
        )
        assert result.status is not CheckStatus.FAIL

    def test_empty_translation_fails(self) -> None:
        """An empty translation is unambiguously a FAIL."""
        item = ExtractedItem("action", "Please bring")
        assert compare_fact(item, "Please bring.", "", None).status is CheckStatus.FAIL


class TestCompleteness:
    """Content loss is detected even when every individual fact passed."""

    def test_fewer_sentences_fails(self) -> None:
        """A shorter translation means content may have been dropped."""
        assert check_completeness("One. Two. Three.", "Uno.", [])[0].status is CheckStatus.FAIL

    def test_equal_sentences_pass(self) -> None:
        """No sentences lost."""
        assert check_completeness("One. Two.", "Uno. Dos.", [])[0].status is CheckStatus.PASS

    def test_link_without_its_instruction_fails(self) -> None:
        """A link whose describing instruction vanished is unusable."""
        item = ExtractedItem("url", "https://example.org/rsvp")
        checks = check_completeness(
            "Please RSVP using the link at https://example.org/rsvp.",
            "https://example.org/rsvp",
            [item],
        )
        assert checks[-1].status is CheckStatus.FAIL


class TestRollup:
    """The worst status wins, and high risk outranks everything."""

    def test_worst_status_wins(self) -> None:
        """A single failure makes the report fail."""
        checks = _checks(SOURCE, "Por favor, traiga el formulario el 9 de septiembre.")
        assert overall_status(checks) is CheckStatus.FAIL

    def test_escalation_outranks_failure(self) -> None:
        """A high-risk message is ESCALATED regardless of its fact map."""
        checks = _checks(SOURCE, "Por favor, traiga el formulario el 8 de septiembre.")
        assert overall_status(checks, escalated=True) is CheckStatus.ESCALATED

    def test_empty_checks_require_review(self) -> None:
        """No checks is not the same as "all good"."""
        assert overall_status([]) is CheckStatus.REVIEW_REQUIRED

    def test_summary_counts(self) -> None:
        """The header counts add up to the total."""
        checks = _checks(SOURCE, "Por favor, traiga el formulario el 9 de septiembre.")
        summary = summarise(checks)
        assert summary["total"] == len(checks)
        assert (
            summary["passed"]
            + summary["warnings"]
            + summary["failures"]
            + summary["review_required"]
            == summary["total"]
        )

    def test_human_review_required_by_default(self) -> None:
        """Semantic items always mean a human must look."""
        checks = _checks(SOURCE, "Por favor, traiga el formulario el 8 de septiembre.")
        assert requires_human_review(checks) is True


class TestAmbiguityDetection:
    """Vague wording must be surfaced, not translated."""

    def test_vague_deadline_raises_a_question(self) -> None:
        """'Soon' cannot become a date, so it is flagged."""
        result = extract_protected_items("Return the form soon.", LOCALE_ES)
        assert result.vague_deadlines == ["soon"]
        assert any("not a usable deadline" in q for q in result.open_questions)

    def test_timely_manner_is_vague(self) -> None:
        """'In a timely manner' is the classic untranslatable deadline."""
        result = extract_protected_items("Return the form in a timely manner.", LOCALE_ES)
        assert "in a timely manner" in result.vague_deadlines

    def test_missing_date_raises_a_question(self) -> None:
        """A message with no date is flagged so a human can add one."""
        result = extract_protected_items("Please return the form.", LOCALE_ES)
        assert any("No date or deadline" in q for q in result.open_questions)


@pytest.mark.parametrize("locale_tag", ["es-US", "hi-IN", "ur-PK"])
def test_every_language_extracts_the_same_facts(locale_tag: str) -> None:
    """The fact map does not depend on the target language."""
    items = extract_protected_items(SOURCE, get_locale(locale_tag)).items
    types = {item.item_type for item in items}
    assert "date" in types
    assert "time" in types
