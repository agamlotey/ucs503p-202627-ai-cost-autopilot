"""Checks run on an entry before it joins the ledger."""

from categories import is_known
from errors import AmountError, LedgerError

REQUIRED_FIELDS = ("date", "category", "amount")


def validate(entry, row=None):
    """Raise if the entry cannot go in the ledger."""
    check_fields(entry, row)
    check_category(entry, row)
    if entry["amount"] <= 0:
        raise AmountError(entry["amount"], row)
    return True


def check_fields(entry, row=None):
    missing = [field for field in REQUIRED_FIELDS if field not in entry]
    if missing:
        raise LedgerError(f"missing fields: {', '.join(missing)}", row)
    return True


def check_category(entry, row=None):
    if not is_known(entry["category"]):
        raise LedgerError(f"category not allowed: {entry['category']}", row)
    return True


def validate_all(entries):
    """Validate a whole batch, numbering rows from one."""
    for number, entry in enumerate(entries, start=1):
        validate(entry, number)
    return len(entries)
