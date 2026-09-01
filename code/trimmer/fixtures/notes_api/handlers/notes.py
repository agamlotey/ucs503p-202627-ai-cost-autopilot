"""Request handlers for the /notes resource."""
from auth import current_user
from config import load_settings
from db import delete_row, fetch_all, fetch_one, insert_row, update_row
from errors import NotFound
from serializers import paginated, serialize_note
from utils.dates import now_utc, to_iso
from utils.text import slugify
from validators import validate_note


def create_note(headers, payload):
    """Validate and store a new note for the current user."""
    user_id = current_user(headers)
    clean = validate_note(payload)
    row_id = insert_row(
        "notes",
        {
            "user_id": user_id,
            "title": clean["title"],
            "slug": slugify(clean["title"]),
            "body": clean["body"],
            "tags": ",".join(clean["tags"]),
            "created_at": to_iso(now_utc()),
        },
    )
    return serialize_note(fetch_one("SELECT * FROM notes WHERE id = ?", (row_id,)))


def get_note(headers, note_id):
    """Fetch a single note owned by the current user."""
    user_id = current_user(headers)
    row = fetch_one(
        "SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id)
    )
    if row is None:
        raise NotFound("no such note")
    return serialize_note(row)


def list_notes(headers, page=1):
    """List the current user's notes, newest first."""
    user_id = current_user(headers)
    page_size = load_settings()["page_size"]
    rows = fetch_all(
        "SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, page_size, (page - 1) * page_size),
    )
    return paginated(rows, serialize_note, page, page_size)


def update_note(headers, note_id, payload):
    """Replace the contents of an existing note."""
    user_id = current_user(headers)
    existing = fetch_one(
        "SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id)
    )
    if existing is None:
        raise NotFound("no such note")
    clean = validate_note(payload)
    update_row(
        "notes",
        note_id,
        {
            "title": clean["title"],
            "slug": slugify(clean["title"]),
            "body": clean["body"],
            "tags": ",".join(clean["tags"]),
        },
    )
    return serialize_note(fetch_one("SELECT * FROM notes WHERE id = ?", (note_id,)))


def delete_note(headers, note_id):
    """Remove a note owned by the current user."""
    user_id = current_user(headers)
    row = fetch_one(
        "SELECT id FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id)
    )
    if row is None:
        raise NotFound("no such note")
    delete_row("notes", note_id)
    return {"deleted": note_id}
