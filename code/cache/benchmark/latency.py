"""Measure the latency the cache ADDS per request — the overhead you pay for the
chance to skip a provider call.

Three cases:
  * cache HIT   — we return a stored answer and skip the provider entirely.
  * cache MISS  — we still embed the request (prose) before forwarding, so this
                  is pure added overhead on top of the provider call.
  * exact repeat (code) — exact-match path, no embedding.

The question is whether the added time is small relative to a real provider
call (hundreds of ms to seconds), i.e. whether caching is "free" latency-wise.

Run:  python -m cache.benchmark.latency
"""
from __future__ import annotations

import time

from cache.cache import SemanticCache

# A rough, widely-quoted floor for a hosted chat completion round-trip. Used
# only to put the measured overheads in perspective, not as a precise figure.
TYPICAL_PROVIDER_MS = 500.0


def _median_ms(fn, n=200) -> float:
    xs = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        xs.append((time.perf_counter() - t) * 1000)
    xs.sort()
    return xs[len(xs) // 2]


def main():
    cache = SemanticCache()
    prose = {"model": "m", "messages": [{"role": "user",
             "content": "What is the capital of France, and why?"}]}
    code = {"model": "m", "messages": [{"role": "user",
            "content": "def parse(x):\n    return int(x) + 1"}]}

    # warm the embedder + seed the cache so hits/misses are meaningful
    cache.store(prose, {"a": "Paris"})
    cache.store(code, {"a": "code"})

    hit_exact = _median_ms(lambda: cache.lookup(prose))     # exact repeat, no embed
    hit_code = _median_ms(lambda: cache.lookup(code))       # code exact, no embed
    # a semantic (paraphrase) hit DOES embed the query before matching
    para = {"model": "m", "messages": [{"role": "user",
            "content": "Which city is the capital of France, and why?"}]}
    hit_semantic = _median_ms(lambda: cache.lookup(para))

    # a genuine miss: a new prose question each time (still embeds → overhead)
    counter = {"i": 0}
    def miss():
        counter["i"] += 1
        cache.lookup({"model": "m", "messages": [{"role": "user",
                     "content": f"unique question number {counter['i']}?"}]})
    miss_prose = _median_ms(miss)

    print("Latency the cache adds per request (median over 200 runs)\n")
    print(f"  {'case':<30}{'ms':>8}")
    print(f"  {'HIT exact repeat (no embed)':<30}{hit_exact:>8.3f}")
    print(f"  {'HIT code exact (no embed)':<30}{hit_code:>8.3f}")
    print(f"  {'HIT semantic paraphrase (embeds)':<30}{hit_semantic:>8.2f}")
    print(f"  {'MISS prose (embeds)':<30}{miss_prose:>8.2f}")
    print()
    print(f"For perspective, a real provider call is ~{TYPICAL_PROVIDER_MS:.0f} ms.")
    print(f"  A HIT replaces that call, so it SAVES ~{TYPICAL_PROVIDER_MS:.0f} ms.")
    print(f"  A MISS adds {miss_prose:.1f} ms "
          f"({100*miss_prose/TYPICAL_PROVIDER_MS:.1f}% of one call) before forwarding.")
    print("  Code / exact repeats add no embedding cost at all.")


if __name__ == "__main__":
    main()
