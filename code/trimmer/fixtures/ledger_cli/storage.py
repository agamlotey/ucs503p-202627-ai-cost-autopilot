"""Reading a ledger from CSV and writing it back."""

from ledger import Ledger
from money import format_amount
from parser import parse_rows
from validators import validate_all


def load(lines, name="ledger"):
    """Build a validated ledger from CSV lines."""
    entries = parse_rows(lines)
    validate_all(entries)
    return Ledger(name, entries)


def dump(ledger):
    """Serialise the ledger back to CSV lines."""
    out = [",".join(("date", "category", "amount", "note"))]
    for entry in ledger.entries:
        out.append(_row(entry))
    return out


def _row(entry):
    year, month, day = entry["date"]
    amount = format_amount(entry["amount"])
    return f"{year:04d}-{month:02d}-{day:02d},{entry['category']},{amount},{entry['note']}"
