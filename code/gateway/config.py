import os

PROVIDER_BASE_URL = os.getenv("PROVIDER_BASE_URL", "https://api.openai.com/v1")
PROVIDER_API_KEY = os.getenv("PROVIDER_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
# The trimmer only cuts a request larger than this many tokens. It matches the
# autopilot's trim threshold (Autopilot.DEFAULT_TRIM_TOKEN_THRESHOLD), so when
# the autopilot asks for trimming, trimming actually happens. The old default of
# 8000 meant a realistic ~3,000-token coding request was planned for trimming
# but forwarded untouched.
TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "1000"))

# Cache bounds so the store can't grow without limit. CACHE_TTL_SECONDS="" (the
# default) disables expiry; set e.g. "3600" to drop entries unused for an hour.
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
