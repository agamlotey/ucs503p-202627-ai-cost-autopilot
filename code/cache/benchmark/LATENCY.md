# Latency measurement — does the cache slow requests down?

`latency.py` measures the time the cache **adds** per request (median over many
runs), for the proposal's "added latency" metric. A provider call is taken as an
**assumed ~500 ms** only for perspective — the real figure varies a lot by model,
network and load. Requires `sentence-transformers` (the benchmark exits with a
message if it is absent, rather than silently mis-measuring).

Run: `python -m cache.benchmark.latency`

## Result

| Case | Added latency |
|---|---|
| HIT, exact repeat (no embed) | ~0.003 ms |
| HIT, code exact (no embed) | ~0.003 ms |
| HIT, semantic paraphrase (1 embed) | ~4.6 ms |
| MISS, prose (lookup + store, **2 embeds**) | ~8.4 ms |
| Cold start (one-time model load at startup) | ~7.5 s |

## Reading it

- **Per-request overhead is small.** Exact repeats and all code requests skip
  embedding entirely (~0 ms). A semantic hit embeds once (~4.6 ms). A prose
  **miss embeds twice** — `lookup()` embeds to compare, then `store()` embeds
  again after the provider replies — so ~8.4 ms, about **1.7% of an assumed
  500 ms call**.
- **A hit *saves* the whole call** (~500 ms here), so it is a net win, not a cost.
- **Cold start is the one real latency to plan for:** the first prose request
  after startup pays ~7.5 s to load the embedding model. It is paid **once**;
  every request after is warm. Worth pre-warming the model at boot in a real
  deployment.

## Notes

- The double-embed on a miss could be halved by reusing the embedding computed
  in `lookup()` inside `store()` — a possible future optimisation (not done here,
  to keep this measurement independent of the cache internals).
- Absolute numbers are machine-specific (measured on CPU); treat the ratios to an
  assumed provider call as indicative, not exact.
