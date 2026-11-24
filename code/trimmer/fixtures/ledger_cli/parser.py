"""Read CSV lines into entry dicts."""

from categories import normalise
from dates import parse_date
from errors import ParseError
from money import parse_amount

HEADER = ("date", "category", "amount", "note")


def parse_rows(lines):
    """Parse every data row, skipping a header line if there is one."""
    entries = []
    for number, line in enumerate(lines, start=1):
        if number == 1 and _is_header(line):
            continue
        if not str(line).strip():
            continue
        entries.append(parse_row(line, number))
    return entries


def _is_header(line):
    return split_row(line)[:1] == ["date"]


def split_row(line):
    """Split one CSV line into trimmed, lower-cased-where-it-matters cells."""
    return [cell.strip() for cell in str(line).split(",")]


def parse_row(line, row=None):
    """Turn one CSV line into an entry."""
    cells = split_row(line)
    if len(cells) < 3:
        raise ParseError("row", line, row)
    return {
        "date": parse_date(cells[0], row),
        "category": normalise(cells[1], row),
        "amount": parse_amount(cells[2], row),
        "note": cells[3] if len(cells) > 3 else "",
    }
