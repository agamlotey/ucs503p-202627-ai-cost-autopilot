# Savings measurement — how much does the cache cut, and when?

`savings.py` replays synthetic coding sessions at several **repeat rates**
through the same logic as `gateway/app.py` (autopilot → cache → trimmer) and
counts the tokens that reach the paid provider versus sending every request
untouched. Tokens are counted with `tiktoken`; each point averages 25 random
sessions of 20 requests.

Run: `python -m cache.benchmark.savings`

## Result: savings track the repeat rate

| Workload repeat rate | Token reduction |
|---|---|
| 0%  | 0.0% |
| 20% | 21% |
| 40% | 39% |
| 50% | 49% |
| 60% | 53% |
| 80% | 74% |

Caching can only save on requests that **repeat**, so the reduction is a
function of the workload, not a single headline number: it is ~0 when nothing
repeats and rises roughly 1:1 with the repeat rate. (This workload is code with
exact repeats, so every hit is an exact match; the semantic layer is exercised
separately in the cache tests and the threshold benchmark, not here.)

## Limitations (important, honest)

- **The number is entirely workload-dependent.** Quote the *curve*, never a
  single percentage — a "56% saving" only means "this trace happened to repeat
  ~56% of the time".
- **Multi-turn conversations barely benefit.** The cache key includes the whole
  message history, so the *same question asked on turn 3* of a conversation has
  a different key than on turn 1 and does **not** hit. Caching helps most for
  independent, single-shot requests (or the first turn); reuse within a growing
  conversation is largely missed. Keying on only the last user turn is **not** a
  safe fix — two different conversations that both end in "fix it" would then
  collide and return each other's answers. A safer direction is prefix caching
  (reuse the shared leading turns) or the provider's own prompt caching — a
  future change, not done here.
- **These payloads sit under the 8000-token trim budget**, so the trimmer never
  fires; every saving here is cache-driven. The trimmer's contribution needs
  large whole-repo requests, best measured on the `notes_api` fixture (PR #19)
  as a full ablation (baseline → +trim → +cache).
- Requires the exact-match-without-embedder fix (PR #22); without it the cache
  is a no-op on machines with no `sentence-transformers` (CI included) and this
  reports 0%.
