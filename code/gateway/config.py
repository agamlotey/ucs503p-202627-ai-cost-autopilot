import os

PROVIDER_BASE_URL = os.getenv("PROVIDER_BASE_URL", "https://api.openai.com/v1")
PROVIDER_API_KEY = os.getenv("PROVIDER_API_KEY", "")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "8000"))

# Cache bounds so the store can't grow without limit. CACHE_TTL_SECONDS="" (the
# default) disables expiry; set e.g. "3600" to drop entries unused for an hour.
CACHE_MAX_ENTRIES = int(os.getenv("CACHE_MAX_ENTRIES", "10000"))
_ttl = os.getenv("CACHE_TTL_SECONDS", "").strip()
CACHE_TTL_SECONDS = float(_ttl) if _ttl else None

# When true (or when no API key is set), the gateway returns a canned reply
# instead of calling a real provider. Lets teammates run and test the full
# pipeline offline, with no API key and no cost.
MOCK_PROVIDER = os.getenv("MOCK_PROVIDER", "").lower() in ("1", "true", "yes")
