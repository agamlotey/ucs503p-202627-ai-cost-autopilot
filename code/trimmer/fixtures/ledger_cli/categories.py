"""The allowed spending categories and their aliases."""

from errors import UnknownCategory

DEFAULT_CATEGORIES = ("food", "travel", "rent", "misc")

_ALIASES = {
    "groceries": "food",
    "dining": "food",
    "cab": "travel",
    "flight": "travel",
}


def normalise(name, row=None):
    """Map an alias onto a known category."""
    key = str(name).strip().lower()
    if not key:
        return "misc"
    key = _ALIASES.get(key, key)
    if key not in DEFAULT_CATEGORIES:
        raise UnknownCategory(key, DEFAULT_CATEGORIES, row)
    return key


def is_known(name):
    return str(name).strip().lower() in DEFAULT_CATEGORIES


def aliases_for(category):
    """Every alias that maps onto this category."""
    return sorted(a for a, target in _ALIASES.items() if target == category)
