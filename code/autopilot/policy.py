"""
Autopilot  —  OWNER: Furmaan

Goal: for each request, pick the cheapest SAFE path — reuse a cached answer,
trim the request, or send it as-is. Does not blindly stack techniques.

Policy to build:
  1. Safety check: contains secrets/PII? -> don't cache.
  2. Cache check first (near-free on a hit).
  3. Code-heavy? -> trim.  Small/simple? -> send as-is.
  4. Measure tokens saved and tune thresholds over time.
"""
from gateway.interfaces import Request


class Autopilot:
    def decide(self, request: Request, signals: dict) -> dict:
        # TODO(Furmaan): real policy + safety checks + threshold tuning.
        return {
            "use_cache": True,
            "trim": bool(signals.get("has_code", False)),
        }
