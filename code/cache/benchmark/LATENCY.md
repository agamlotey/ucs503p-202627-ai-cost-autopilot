# Latency measurement — does the cache slow requests down?

`latency.py` measures the time the cache **adds** per request (median of 200
runs), to check the proposal's "added latency" metric. A hosted provider call is
used only as a ~500 ms reference point to keep the numbers in perspective.

Run: `python -m cache.benchmark.latency`

## Result

| Case | Added latency |
|---|---|
| HIT, exact repeat (no embed) | ~0.003 ms |
| HIT, code exact (no embed) | ~0.003 ms |
| HIT, semantic paraphrase (embeds the query) | ~4.3 ms |
| MISS, prose (embeds the query) | ~4.5 ms |

## Reading it

- **The embedding (~4.5 ms) is the only real cost, and it is paid only when the
  query is not an exact match** — i.e. on a semantic hit or a miss. Exact repeats
  and all code requests skip it entirely (~0 ms).
- **A hit replaces the provider call**, so it doesn't just add nothing — it
  *saves* the whole round-trip (~500 ms here).
- **A miss adds ~0.9% of one provider call** before forwarding — negligible next
  to the call it precedes.

So caching is effectively free on the latency axis: near-zero on exact hits, a
few milliseconds on prose, and a large saving whenever it hits. (Measured on
this machine's CPU; absolute numbers vary, but the ratio to a network call
does not.)
