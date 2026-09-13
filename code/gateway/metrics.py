"""Lightweight in-memory metering for the savings dashboard.

Every request records what the gateway did with it, so /stats can report the
running totals and a recent-activity feed. In-memory only (resets on restart) —
enough for a live demo and a local dashboard.
"""
import time
from collections import deque

# Illustrative input price (USD per token). gpt-4o-mini is ~$0.15 / 1M input
# tokens; used only to turn "tokens saved" into a rough dollar figure on the UI.
USD_PER_TOKEN = 0.15 / 1_000_000


class Metrics:
    def __init__(self, recent: int = 30) -> None:
        self.requests = 0
        self.cache_hits = 0
        self.trimmed = 0
        self.baseline_tokens = 0   # tokens that WOULD have been sent, no gateway
        self.sent_tokens = 0       # tokens that actually reached the provider
        self.recent = deque(maxlen=recent)

    def record(self, *, baseline: int, sent: int, outcome: str,
               model: str, preview: str) -> None:
        self.requests += 1
        self.baseline_tokens += baseline
        self.sent_tokens += sent
        if outcome == "cache":
            self.cache_hits += 1
        elif outcome == "trim":
            self.trimmed += 1
        self.recent.appendleft({
            "time": time.strftime("%H:%M:%S"),
            "model": model,
            "preview": preview,
            "baseline": baseline,
            "sent": sent,
            "saved": baseline - sent,
            "outcome": outcome,          # "cache" | "trim" | "forward"
        })

    def snapshot(self) -> dict:
        saved = self.baseline_tokens - self.sent_tokens
        return {
            "requests": self.requests,
            "cache_hits": self.cache_hits,
            "hit_rate": (self.cache_hits / self.requests) if self.requests else 0.0,
            "trimmed": self.trimmed,
            "baseline_tokens": self.baseline_tokens,
            "sent_tokens": self.sent_tokens,
            "saved_tokens": saved,
            "reduction": (saved / self.baseline_tokens) if self.baseline_tokens else 0.0,
            "saved_usd": saved * USD_PER_TOKEN,
            "recent": list(self.recent),
        }

    def reset(self) -> None:
        self.__init__(recent=self.recent.maxlen)


metrics = Metrics()
