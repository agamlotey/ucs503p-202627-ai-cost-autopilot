import os

PROVIDER_BASE_URL = os.getenv("PROVIDER_BASE_URL", "https://api.openai.com/v1")
PROVIDER_API_KEY = os.getenv("PROVIDER_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "8000"))

# Cache bounds so the store can't grow without limit. CACHE_TTL_SECONDS="" (the
# default) disables expiry; set e.g. "3600" to drop entries unused for an hour.
# Prose similarity threshold for semantic reuse (see cache.py). Lower = looser.
_thr = os.getenv("CACHE_THRESHOLD", "").strip()
CACHE_THRESHOLD = float(_thr) if _thr else 0.85
_max = os.getenv("CACHE_MAX_ENTRIES", "").strip()
CACHE_MAX_ENTRIES = int(_max) if _max else 10000
_ttl = os.getenv("CACHE_TTL_SECONDS", "").strip()
# NOTE: the TTL is *sliding* — a hit refreshes an entry's timer (see cache.py),
# so a frequently used answer never expires. It bounds memory, but it is not a
# freshness guarantee: a hot entry can outlive `ttl_seconds`.
CACHE_TTL_SECONDS = float(_ttl) if _ttl else None

# When true (or when no API key is set), the gateway returns a canned reply
# instead of calling a real provider. Lets teammates run and test the full
# pipeline offline, with no API key and no cost.
MOCK_PROVIDER = os.getenv("MOCK_PROVIDER", "").lower() in ("1", "true", "yes")
