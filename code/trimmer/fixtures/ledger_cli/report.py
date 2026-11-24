"""Summaries built from a ledger."""

from categories import DEFAULT_CATEGORIES
from dates import month_key
from money import format_amount


def by_category(ledger):
    """Total per category, including the ones with nothing in them."""
    totals = {name: 0 for name in DEFAULT_CATEGORIES}
    for entry in ledger.entries:
        name = entry["category"]
        totals[name] = totals.get(name, 0) + entry["amount"]
    return totals


def by_month(ledger):
    """Total per calendar month."""
    totals = {}
    for entry in ledger.entries:
        key = month_key(entry["date"])
        totals[key] = totals.get(key, 0) + entry["amount"]
    return totals


def biggest_category(ledger):
    """The category with the most spent, or None."""
    spent = {name: paise for name, paise in by_category(ledger).items() if paise}
    if not spent:
        return None
    return max(spent, key=lambda name: spent[name])


def render(ledger):
    """A short plain-text summary."""
    lines = [f"ledger: {ledger.name}"]
    for name, paise in sorted(by_category(ledger).items()):
        lines.append(f"  {name:<8} {format_amount(paise)}")
    lines.append(f"  {'total':<8} {format_amount(ledger.total())}")
    return "\n".join(lines)
