"""Request handlers for sign-up and sign-in."""
from auth import current_user, hash_password, make_token, verify_password
from db import fetch_one, insert_row
from errors import Unauthorized, ValidationError
from serializers import serialize_user
from utils.dates import now_utc, to_iso
from validators import validate_email, is_blank


def register(payload):
    """Create a new account and return a token."""
    email = validate_email(payload.get("email"))
    password = payload.get("password")
    if is_blank(password) or len(password) < 8:
        raise ValidationError("password must be at least 8 characters", field="password")
    if fetch_one("SELECT id FROM users WHERE email = ?", (email,)):
        raise ValidationError("that email is already registered", field="email")
    user_id = insert_row(
        "users",
        {
            "email": email,
            "password": hash_password(password),
            "created_at": to_iso(now_utc()),
        },
    )
    return {"token": make_token(user_id), "user_id": user_id}


def login(payload):
    """Exchange an email and password for a token."""
    email = validate_email(payload.get("email"))
    row = fetch_one("SELECT * FROM users WHERE email = ?", (email,))
    if row is None or not verify_password(payload.get("password") or "", row["password"]):
        raise Unauthorized("email or password is incorrect")
    return {"token": make_token(row["id"]), "user_id": row["id"]}


def get_profile(headers):
    """Return the current user's profile."""
    user_id = current_user(headers)
    row = fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if row is None:
        raise Unauthorized("account no longer exists")
    return serialize_user(row)
