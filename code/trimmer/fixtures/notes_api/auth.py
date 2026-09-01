"""Password hashing and bearer tokens."""
import base64
import hashlib
import hmac
import os

from config import load_settings
from errors import Unauthorized
from utils.dates import age_seconds, now_utc, parse_iso, to_iso


def hash_password(password, salt=None):
    """Hash a password with PBKDF2 and return 'salt$hash'."""
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return "{}${}".format(salt, digest.hex())


def verify_password(password, stored):
    """Check a password against a stored 'salt$hash' value."""
    if not stored or "$" not in stored:
        return False
    salt, _ = stored.split("$", 1)
    return hmac.compare_digest(hash_password(password, salt), stored)


def make_token(user_id):
    """Issue an opaque token carrying the user id and issue time."""
    payload = "{}|{}".format(user_id, to_iso(now_utc()))
    return base64.urlsafe_b64encode(payload.encode()).decode()


def parse_token(token):
    """Decode a token, raising Unauthorized when it is invalid or expired."""
    try:
        payload = base64.urlsafe_b64decode(token.encode()).decode()
        user_id, issued = payload.split("|", 1)
    except Exception:
        raise Unauthorized("malformed token")
    ttl = load_settings()["token_ttl_seconds"]
    if age_seconds(parse_iso(issued)) > int(ttl):
        raise Unauthorized("token has expired")
    return int(user_id)


def current_user(headers):
    """Resolve the caller's user id from the Authorization header."""
    header = headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise Unauthorized("missing bearer token")
    return parse_token(header[7:])
