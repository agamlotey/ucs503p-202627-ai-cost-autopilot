"""Money amounts, held as whole paise so arithmetic stays exact."""

from errors import ParseError


def parse_amount(text, row=None):
    """Turn '12.50' into 1250 paise."""
    cleaned = str(text).strip().replace(",", "")
    if not cleaned:
        raise ParseError("amount", text, row)
    negative = cleaned.startswith("-")
    if negative:
        cleaned = cleaned[1:]
    if not _is_decimal(cleaned):
        raise ParseError("amount", text, row)
    whole, _dot, frac = cleaned.partition(".")
    paise = int(whole or 0) * 100 + _frac_to_paise(frac)
    return -paise if negative else paise


def _is_decimal(text):
    """True for '12', '12.5' and '12.50', false for '1.2.3' and 'abc'."""
    parts = text.split(".")
    if len(parts) > 2 or not text:
        return False
    return all(part.isdigit() for part in parts if part != "")


def _frac_to_paise(frac):
    if not frac:
        return 0
    return int((frac + "00")[:2])


def format_amount(paise):
    """Render paise back as a decimal string."""
    sign = "-" if paise < 0 else ""
    paise = abs(paise)
    return f"{sign}{paise // 100}.{paise % 100:02d}"


def add_amounts(values):
    """Sum any iterable of paise."""
    total = 0
    for value in values:
        total += value
    return total
