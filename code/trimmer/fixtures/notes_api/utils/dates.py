"""Date and time helpers, all in UTC."""
from datetime import datetime, timezone


def now_utc():
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_iso(value):
    """Format a datetime as an ISO-8601 string."""
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def parse_iso(value):
    """Parse an ISO-8601 string back into a datetime."""
    if not value:
        return None
    return datetime.fromisoformat(value)


def age_seconds(value):
    """Seconds elapsed since the given datetime."""
    if value is None:
        return 0
    return int((now_utc() - value).total_seconds())


def humanize(value):
    """Render a datetime as a rough human-readable age."""
    seconds = age_seconds(value)
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return "{} minutes ago".format(seconds // 60)
    if seconds < 86400:
        return "{} hours ago".format(seconds // 3600)
    return "{} days ago".format(seconds // 86400)
