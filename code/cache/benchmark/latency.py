"""Measure the latency the cache ADDS per request — the overhead you pay for the
chance to skip a provider call.

Cases (median over many runs):
  * HIT, exact repeat / code — exact-match path, no embedding.
  * HIT, semantic paraphrase — embeds the query once to compare.
  * MISS, prose — in the real gateway a miss embeds TWICE: lookup() embeds to
    compare against the bucket, then store() embeds again after the provider
    replies. We time lookup()+store() together to reflect that.
  * cold start — the one-time model load the first prose request pays.

The provider round-trip is taken as an ASSUMED ~500 ms only to put the overheads
in perspective; the real figure varies by model, network and load.

Run:  python -m cache.benchmark.latency
"""
from __future__ import annotations

import sys
import time

try:
    import sentence_transformers  # noqa: F401
except Exception:
    sys.exit("sentence-transformers is not installed, so the embedding latency "
             "(the whole point of this benchmark) can't be measured. "
             "Install it and re-run: pip install sentence-transformers")

from cache.cache import SemanticCache, _default_embedder

ASSUMED_PROVIDER_MS = 500.0   # assumption, for perspective only


def _median_ms(fn, n=200) -> float:
    xs = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        xs.append((time.perf_counter() - t) * 1000)
    xs.sort()
    return xs[len(xs) // 2]


def _msg(text):
    return {"model": "m", "messages": [{"role": "user", "content": text}]}


def main():
    # --- cold start: the one-time model load the first prose request pays ---
    t = time.perf_counter()
    embed = _default_embedder()
    embed("warm up the model")          # first encode triggers the full load
    cold_ms = (time.perf_counter() - t) * 1000

    # share the loaded embedder so nothing below re-pays the load
    def cache():
        return SemanticCache(embed_fn=embed)

    prose = _msg("What is the capital of France, and why?")
    code = _msg("def parse(x):\n    return int(x) + 1")
    para = _msg("Which city is the capital of France, and why?")

    warm = cache()
    warm.store(prose, {"a": "Paris"})
    warm.store(code, {"a": "code"})

    # correctness assertions — fail loudly rather than silently mis-measure
    assert warm.lookup(prose) is not None, "exact repeat should HIT"
    assert warm.lookup(code) is not None, "code exact should HIT"
    assert warm.lookup(para) is not None, "semantic paraphrase should HIT"

    hit_exact = _median_ms(lambda: warm.lookup(prose))
    hit_code = _median_ms(lambda: warm.lookup(code))
    hit_semantic = _median_ms(lambda: warm.lookup(para))

    # MISS = lookup() + store(), on a bucket that already exists (same model), so
    # both embeds happen — the realistic gateway cost. Fresh cache each run keeps
    # the bucket from growing and skewing the scan.
    seed = _msg("An unrelated seeded question about apples.")
    counter = {"i": 0}

    def miss_full():
        counter["i"] += 1
        c = cache()
        c.store(seed, {"a": 0})                      # bucket now exists (setup)
        q = _msg(f"A brand new distinct question number {counter['i']}?")
        t0 = time.perf_counter()
        assert c.lookup(q) is None                   # embeds (bucket non-empty)
        c.store(q, {"a": 1})                         # embeds again
        return t0

    def _timed_miss():
        t0 = miss_full()
        # subtract nothing; the setup store() ran before t0
        _timed_miss.last = (time.perf_counter() - t0) * 1000
    misses = []
    for _ in range(100):
        _timed_miss(); misses.append(_timed_miss.last)
    misses.sort(); miss_ms = misses[len(misses) // 2]

    print("Latency the cache adds per request\n")
    print(f"  {'case':<34}{'ms':>8}")
    print(f"  {'HIT exact repeat (no embed)':<34}{hit_exact:>8.3f}")
    print(f"  {'HIT code exact (no embed)':<34}{hit_code:>8.3f}")
    print(f"  {'HIT semantic paraphrase (1 embed)':<34}{hit_semantic:>8.2f}")
    print(f"  {'MISS prose (lookup+store, 2 embeds)':<34}{miss_ms:>8.2f}")
    print(f"  {'cold start (one-time model load)':<34}{cold_ms:>8.1f}")
    print()
    print(f"Assuming a provider call is ~{ASSUMED_PROVIDER_MS:.0f} ms (varies a lot):")
    print(f"  A HIT replaces that call -> saves ~{ASSUMED_PROVIDER_MS:.0f} ms.")
    print(f"  A MISS adds {miss_ms:.1f} ms "
          f"(~{100*miss_ms/ASSUMED_PROVIDER_MS:.1f}% of one call) before forwarding.")
    print(f"  Exact repeats / code add ~0 ms. Cold start is paid once at startup.")


if __name__ == "__main__":
    main()
