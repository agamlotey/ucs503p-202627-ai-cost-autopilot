"""
Autopilot  —  OWNER: Furmaan

Goal: for each request, pick the cheapest SAFE path — reuse a cached answer,
trim the request, or send it as-is. Does not blindly stack techniques,
because trimming rewrites the prompt and lowers how often the cache matches.

Decision order (cheapest action first, see docs/components/autopilot.md):
  1. Safety check   -> secrets/PII present?  -> never cache, never trim
                        (trimming a message with a secret risks the trimmer
                        splitting/duplicating it across a cached boundary,
                        so the safest move is to send it through untouched).
  2. Cache lookup   -> handled by the gateway using our `use_cache` flag;
                        a hit is near-free.
  3. Code-heavy and large enough to be worth the trimmer's overhead?
                        -> trim.
  4. Otherwise      -> pass through untouched.

Everything here is self-contained inside the autopilot package — it does not
require gateway/interfaces.py or gateway/app.py to change. The secrets check
in particular does its own lightweight scan of the request, rather than
depending on the gateway to have computed a `has_secrets` signal, so the
safety guarantee holds even before the shared `compute_signals()` is
extended to cover it.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from gateway.interfaces import Request


# ----------------------------------------------------------------------
# Safety check: secrets / PII detection
# ----------------------------------------------------------------------
class SecretsDetector:
    """
    Cheap, fast, regex-based check for obvious secrets/PII in a request.
    Intentionally conservative (covers common patterns, not a full DLP
    system) — good enough to guarantee "never cache a secret" without
    adding latency to every request.
    """

    PATTERNS = [
        r"sk-(proj-|ant-api\d{2}-)?[A-Za-z0-9_-]{20,}",  # OpenAI (sk-..., sk-proj-...) and Anthropic (sk-ant-api03-...) keys
        r"AIza[0-9A-Za-z\-_]{35}",                      # Google API keys
        r"ghp_[A-Za-z0-9]{36}",                         # GitHub personal access tokens
        r"AKIA[0-9A-Z]{16}",                            # AWS access key IDs
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",          # PEM private keys
        r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",  # JWTs
        r"(?i)\b(password|passwd|pwd|api[_-]?key|secret|token)\s*[:=]\s*\S+",
        r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b",      # credit-card-shaped
        r"\b\d{3}-\d{2}-\d{4}\b",                        # SSN-shaped
    ]

    def __init__(self) -> None:
        self._compiled = [re.compile(p) for p in self.PATTERNS]

    def scan(self, text: str) -> bool:
        return any(p.search(text) for p in self._compiled)


def _extract_text(request: Request) -> str:
    """Pulls all message content out of an OpenAI-style chat request body."""
    if not isinstance(request, dict):
        return ""
    messages = request.get("messages", [])
    return " ".join(
        m.get("content", "")
        for m in messages
        if isinstance(m, dict) and isinstance(m.get("content"), str)
    )


# ----------------------------------------------------------------------
# The Autopilot
# ----------------------------------------------------------------------
class Autopilot:
    """
    Contract (frozen — see gateway/interfaces.py, do not change alone):
        decide(request: Request, signals: dict) -> dict
            e.g. {"use_cache": bool, "trim": bool}
    """

    # Trimming a small request isn't worth the compiler-aware trimmer's
    # parsing overhead — only worth it once a request is both code-heavy
    # AND reasonably large. Threshold is tunable, see `stats()` below.
    DEFAULT_TRIM_TOKEN_THRESHOLD = 1000

    def __init__(self, trim_token_threshold: int = DEFAULT_TRIM_TOKEN_THRESHOLD):
        self.trim_token_threshold = trim_token_threshold
        self._secrets = SecretsDetector()
        # Lightweight in-memory counters so we can measure/tune thresholds
        # later (per "Measurement and tuning" in the component doc), without
        # needing a separate logging system yet.
        self._decision_counts: Counter[str] = Counter()

    def decide(self, request: Request, signals: dict) -> dict:
        # --- 1. Safety check: never cache a secret ---
        has_secrets = signals.get("has_secrets")
        if has_secrets is None:
            # The shared compute_signals() in gateway/app.py doesn't compute
            # this yet, so the autopilot does its own scan as a fallback.
            # This keeps the safety guarantee independent of what the
            # gateway currently passes in.
            has_secrets = self._secrets.scan(_extract_text(request))

        if has_secrets:
            self._decision_counts["secrets_no_cache"] += 1
            return {"use_cache": False, "trim": False, "reason": "secrets_detected"}

        # --- 2 & 3. Cache is always attempted; trim only if it's worth it ---
        has_code = bool(signals.get("has_code", False))
        num_tokens_est = signals.get("num_tokens_est", 0)
        should_trim = has_code and num_tokens_est > self.trim_token_threshold

        self._decision_counts["trimmed" if should_trim else "cache_or_passthrough"] += 1
        return {
            "use_cache": True,
            "trim": should_trim,
            "reason": "trim_code_heavy" if should_trim else "no_trim_needed",
        }

    def stats(self) -> dict:
        """Decision counts so far, for measurement/threshold tuning."""
        return dict(self._decision_counts)
