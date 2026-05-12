"""Period helpers for month-level YYYY-MM source period fields."""

from __future__ import annotations

import re

_MONTH_RE = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])$")

_MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def _tuple_le(a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Compare two (year, month) tuples: a <= b."""
    return a[0] < b[0] or (a[0] == b[0] and a[1] <= b[1])


def validate_month(value: str, field_name: str = "period") -> str:
    """Validate a YYYY-MM string. Returns it stripped if valid, raises ValueError otherwise."""
    if not value or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty YYYY-MM string")
    value = value.strip()
    if not _MONTH_RE.match(value):
        raise ValueError(f"{field_name} '{value}' is not a valid YYYY-MM format")
    return value


def parse_month(value: str) -> tuple[int, int]:
    """Parse a YYYY-MM string into (year, month) tuple."""
    parts = value.split("-")
    return int(parts[0]), int(parts[1])


def validate_period_range(start_month: str, end_month: str) -> None:
    """Validate that start_month <= end_month. Raises ValueError if not."""
    s_year, s_mon = parse_month(start_month)
    e_year, e_mon = parse_month(end_month)
    if (s_year, s_mon) > (e_year, e_mon):
        raise ValueError(
            f"period_start_month ({start_month}) must be <= period_end_month ({end_month})"
        )


def derive_period_label(start_month: str | None, end_month: str | None) -> str | None:
    """Derive a human-readable period label from start/end month strings.

    Returns None if both are None. Returns single-month label if only one is set.
    """
    if not start_month and not end_month:
        return None

    # If only one is provided, use it for both
    start = start_month or end_month  # type: ignore[assignment]
    end = end_month or start_month  # type: ignore[assignment]
    assert start is not None and end is not None  # guaranteed by the None check above

    if start == end:
        year, month = parse_month(start)
        return f"{_MONTH_NAMES[month]} {year}"

    s_year, s_mon = parse_month(start)
    e_year, e_mon = parse_month(end)

    if s_year == e_year:
        return f"{_MONTH_NAMES[s_mon]} – {_MONTH_NAMES[e_mon]} {s_year}"

    return f"{_MONTH_NAMES[s_mon]} {s_year} – {_MONTH_NAMES[e_mon]} {e_year}"


def ranges_overlap(
    start_a: str | None,
    end_a: str | None,
    start_b: str | None,
    end_b: str | None,
) -> bool:
    """Check whether two month-level ranges overlap.

    None values are treated as unbounded on that side.
    """
    # If either range is completely unbounded, they overlap
    if start_a is None and end_a is None:
        return True
    if start_b is None and end_b is None:
        return True

    # Normalize: if start is None, treat as before everything; if end is None, after everything
    a_start: tuple[int, int] = parse_month(start_a) if start_a else (0, 1)
    a_end: tuple[int, int] = parse_month(end_a) if end_a else (9999, 12)
    b_start: tuple[int, int] = parse_month(start_b) if start_b else (0, 1)
    b_end: tuple[int, int] = parse_month(end_b) if end_b else (9999, 12)

    # Ranges overlap if a_start <= b_end and b_start <= a_end
    return _tuple_le(a_start, b_end) and _tuple_le(b_start, a_end)
