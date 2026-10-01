"""Date and time parsing, which is what catches a shifted deadline."""

from __future__ import annotations

import pytest

from app.verification.normalisation import (
    DateOrder,
    all_dates,
    all_times,
    parse_any_date,
    parse_named_date,
    parse_numeric_date,
    parse_time,
)


class TestNamedDates:
    """A month name identifies the month, so no order question arises."""

    @pytest.mark.parametrize(
        ("text", "month", "day"),
        [
            ("September 8", 9, 8),
            ("October 3", 10, 3),
            ("Sept. 18th", 9, 18),
            ("3 October", 10, 3),
            ("December 31", 12, 31),
            ("9 de septiembre", 9, 9),
            ("18 de octubre", 10, 18),
        ],
    )
    def test_parses_named_dates(self, text: str, month: int, day: int) -> None:
        """English and Spanish month names both parse to the right day."""
        parsed = parse_named_date(text)
        assert parsed is not None
        assert (parsed.month, parsed.day) == (month, day)

    def test_invalid_day_is_rejected(self) -> None:
        """A day outside the month is not silently accepted."""
        assert parse_named_date("September 45") is None


class TestNumericDates:
    """Numeric dates depend on locale order, and must escalate when unknown."""

    def test_year_first_is_unambiguous(self) -> None:
        """``2026-10-03`` cannot be misread, so no ambiguity flag is set."""
        parsed = parse_numeric_date("2026-10-03")
        assert parsed is not None
        assert (parsed.year, parsed.month, parsed.day) == (2026, 10, 3)
        assert parsed.ambiguous is False

    def test_unknown_order_is_flagged_ambiguous(self) -> None:
        """``10/03/2026`` with no locale must not be guessed."""
        parsed = parse_numeric_date("10/03/2026")
        assert parsed is not None
        assert parsed.ambiguous is True

    @pytest.mark.parametrize(
        ("order", "month", "day"),
        [(DateOrder.MDY, 10, 3), (DateOrder.DMY, 3, 10)],
    )
    def test_locale_order_resolves_ambiguity(self, order: DateOrder, month: int, day: int) -> None:
        """A known locale order resolves the date and clears the flag."""
        parsed = parse_numeric_date("10/03/2026", order)
        assert parsed is not None
        assert (parsed.month, parsed.day) == (month, day)
        assert parsed.ambiguous is False


class TestTimes:
    """Times are normalised to minutes since midnight, not compared as strings."""

    @pytest.mark.parametrize(
        ("text", "minutes"),
        [
            ("8:30 a.m.", 510),
            ("08:30", 510),
            ("8:30 AM", 510),
            ("8:30am", 510),
        ],
    )
    def test_equivalent_forms_match(self, text: str, minutes: int) -> None:
        """``8:30 a.m.`` and ``08:30`` are the same instant."""
        parsed = parse_time(text)
        assert parsed is not None
        assert parsed.start_minutes == minutes

    def test_different_time_does_not_match(self) -> None:
        """8:00 is not 8:30. This is the check the specification requires."""
        assert parse_time("8:30 a.m.").start_minutes != parse_time("8:00 a.m.").start_minutes

    def test_pm_conversion(self) -> None:
        """A 12-hour clock is folded into 24 hours."""
        assert parse_time("6:00 p.m.").hour == 18
        assert parse_time("6:00 a.m.").hour == 6

    def test_midnight_and_noon(self) -> None:
        """The 12-hour edges are where naive conversion goes wrong."""
        assert parse_time("12:00 a.m.").hour == 0
        assert parse_time("12:00 p.m.").hour == 12

    def test_range(self) -> None:
        """``6:00-7:00 p.m.`` is a range, and the trailing meridiem applies to both ends."""
        parsed = parse_time("6:00-7:00 p.m.")
        assert parsed is not None
        assert parsed.is_range()
        assert (parsed.hour, parsed.end_hour) == (18, 19)

    def test_minutes_above_fifty_nine_rejected(self) -> None:
        """An impossible minute value is not parsed."""
        assert parse_time("8:75 a.m.") is None


class TestScanning:
    """Multiple values in one message are all found."""

    def test_finds_multiple_dates(self) -> None:
        """Both the event date and the RSVP deadline are extracted."""
        text = "Join us on October 8. Please RSVP by October 3."
        found = {(d.month, d.day) for d in all_dates(text)}
        assert (10, 8) in found
        assert (10, 3) in found

    def test_named_date_not_double_counted_as_numeric(self) -> None:
        """``October 3`` must not also be read as a bare number."""
        found = all_dates("by October 3")
        assert len(found) == 1

    def test_finds_multiple_times(self) -> None:
        """All three shift times in a volunteer message are found."""
        text = "Shifts start at 8:00 a.m., 10:00 a.m., or 1:00 p.m."
        assert len(all_times(text)) == 3

    def test_parse_any_date_falls_back(self) -> None:
        """``parse_any_date`` tries named then numeric."""
        assert parse_any_date("September 8") is not None
        assert parse_any_date("2026-09-08") is not None
        assert parse_any_date("not a date") is None
