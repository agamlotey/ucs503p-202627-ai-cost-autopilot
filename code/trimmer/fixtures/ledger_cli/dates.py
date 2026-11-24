"""Dates, kept as plain (year, month, day) tuples."""

from errors import ParseError


def parse_date(text, row=None):
    """Read an ISO date such as '2026-03-09'."""
    parts = str(text).strip().split("-")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ParseError("date", text, row)
    year, month, day = (int(part) for part in parts)
    if not _valid(year, month, day):
        raise ParseError("date", text, row)
    return (year, month, day)


def _valid(year, month, day):
    if not 1 <= month <= 12:
        return False
    return 1 <= day <= days_in_month(year, month)


def days_in_month(year, month):
    """How many days that month has."""
    if month == 2:
        return 29 if is_leap(year) else 28
    return 30 if month in (4, 6, 9, 11) else 31


def is_leap(year):
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    return year % 4 == 0


def month_key(date):
    """'2026-03' for grouping."""
    year, month, _day = date
    return f"{year:04d}-{month:02d}"
