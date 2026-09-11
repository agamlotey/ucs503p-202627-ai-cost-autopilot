"""Application settings loaded from the environment."""
import os

DEFAULTS = {
    "db_path": "notes.sqlite",
    "page_size": 20,
    "token_ttl_seconds": 3600,
    "max_title_length": 120,
}


def get_env(name, fallback=None):
    """Read an environment variable, falling back to the defaults table."""
    if name in os.environ:
        return os.environ[name]
    if fallback is not None:
        return fallback
    return DEFAULTS.get(name)


def load_settings():
    """Build the settings mapping used by the rest of the application."""
    settings = dict(DEFAULTS)
    for key in DEFAULTS:
        value = get_env(key.upper())
        if value is not None:
            settings[key] = value
    settings["page_size"] = int(settings["page_size"])
    return settings


def is_debug():
    """True when the service is running in debug mode."""
    return str(get_env("DEBUG", "0")).lower() in ("1", "true", "yes")
