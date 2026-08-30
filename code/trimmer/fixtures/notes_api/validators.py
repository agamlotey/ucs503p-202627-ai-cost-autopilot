"""Validation for incoming request bodies."""
from config import load_settings
from errors import ValidationError


def is_blank(value):
    """True when the value is missing or only whitespace."""
    return value is None or not str(value).strip()


def validate_title(title):
    """A title must be present and within the configured length."""
    if is_blank(title):
        raise ValidationError("title is required", field="title")
    limit = load_settings()["max_title_length"]
    if len(title) > limit:
        raise ValidationError("title is too long", field="title")
    return title.strip()


def validate_body(body):
    """A note body must be present."""
    if is_blank(body):
        raise ValidationError("body is required", field="body")
    return body.strip()


def validate_tags(tags):
    """Tags must be a list of short non-empty strings."""
    if tags is None:
        return []
    if not isinstance(tags, list):
        raise ValidationError("tags must be a list", field="tags")
    cleaned = []
    for tag in tags:
        if is_blank(tag):
            continue
        cleaned.append(str(tag).strip().lower())
    return cleaned


def validate_note(payload):
    """Validate a whole note payload and return the cleaned version."""
    return {
        "title": validate_title(payload.get("title")),
        "body": validate_body(payload.get("body")),
        "tags": validate_tags(payload.get("tags")),
    }


def validate_email(email):
    """A crude email check, good enough for the sign-up form."""
    if is_blank(email) or "@" not in email:
        raise ValidationError("a valid email is required", field="email")
    return email.strip().lower()
