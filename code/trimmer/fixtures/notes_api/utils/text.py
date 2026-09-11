"""Small text helpers."""
import re

_NON_WORD = re.compile(r"[^a-z0-9]+")
_TAG = re.compile(r"<[^>]+>")


def slugify(value):
    """Turn a title into a URL-safe slug."""
    lowered = value.strip().lower()
    slug = _NON_WORD.sub("-", lowered)
    return slug.strip("-")


def truncate(value, limit=80):
    """Shorten text to `limit` characters, adding an ellipsis."""
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def strip_html(value):
    """Remove any HTML tags from the text."""
    return _TAG.sub("", value)


def word_count(value):
    """Count whitespace-separated words."""
    return len(value.split())


def excerpt(value, words=25):
    """First `words` words of the text, as a single line."""
    parts = strip_html(value).split()
    return " ".join(parts[:words])
