"""Turn database rows into API responses."""
from utils.dates import humanize, parse_iso, to_iso
from utils.text import excerpt


def serialize_note(row):
    """Render one note row for the API."""
    created = parse_iso(row.get("created_at"))
    return {
        "id": row["id"],
        "title": row["title"],
        "slug": row.get("slug"),
        "excerpt": excerpt(row.get("body", "")),
        "tags": (row.get("tags") or "").split(",") if row.get("tags") else [],
        "created_at": to_iso(created),
        "created_ago": humanize(created),
    }


def serialize_user(row):
    """Render one user row, never including the password hash."""
    return {
        "id": row["id"],
        "email": row["email"],
        "joined_at": to_iso(parse_iso(row.get("created_at"))),
    }


def serialize_many(rows, serializer):
    """Apply a serializer across a list of rows."""
    return [serializer(row) for row in rows]


def paginated(rows, serializer, page, page_size):
    """Wrap serialized rows in a pagination envelope."""
    return {
        "page": page,
        "page_size": page_size,
        "count": len(rows),
        "items": serialize_many(rows, serializer),
    }
