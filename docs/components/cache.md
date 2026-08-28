# Semantic Cache

**Owner:** Devansh (1024240012) · **Code:** `code/cache/`

Reuses a past answer when a new request **means the same thing** — so the same
question is never paid for twice.

## Why semantic, not exact

Ordinary caching only helps when two requests are byte-for-byte identical. In
practice developers ask the same thing in different words:

- *"What does `parse_config` do?"*
- *"Explain the parse_config function"*

A semantic cache recognises these as equivalent and returns the stored answer at
near-zero cost.

## How it works

1. **Embed** the request into a vector (`sentence-transformers`).
2. **Search** the stored requests for the nearest neighbour (cosine similarity).
3. **Reuse** the stored answer if similarity is above a tuned threshold.
4. **Store** the new question/answer pair after the model replies.

``` python
hit = cache.lookup(request)      # -> response | None
if hit is None:
    response = call_model(request)
    cache.store(request, response)
```

## The threshold is the hard part

The similarity threshold decides correctness:

- Too **low** → loosely related questions match, and the cache serves a *wrong*
  answer.
- Too **high** → almost nothing matches, and the cache saves nothing.

A wrong-but-cheap answer is worse than paying, so the threshold starts
deliberately conservative and is tuned with measurements.

### Prose threshold vs. code payloads

The 0.90 default was validated on natural-language questions (paraphrases score
~0.91–0.94, unrelated questions ≤0.47 — a clean gap). But our real payload is
**code**, and the embedding model (`all-MiniLM-L6-v2`) is trained on prose. On
near-identical but *opposite-meaning* code it scores dangerously high:

| Code pair | cosine |
|---|---|
| `if a > b` vs `if a >= b` | 0.96 |
| `return True` vs `return False` | 0.90 |
| `x + 1` vs `x - 1` | 0.88 |

At 0.90 these would be wrongly reused. So the threshold must be **re-measured on
code pairs** before the semantic path is trusted on real code traffic — that
measurement is the component's core ML task, tracked next.

## Safety

- **Never cache secrets or personal data** — a filter rejects them.
- **Per-user isolation** — one user's cache is never served to another.
- **Time-to-live** — entries expire so stale answers are not reused forever.

## Build order

Version 1 is **exact-match** (key = hash of the messages). That proves the
store/lookup/return plumbing works with zero risk of a wrong match. The semantic
layer is then added on top.

## Status and next steps

- [x] Exact-match cache (hash key) — *merged (#9)*
- [x] Embeddings + cosine similarity search — *merged (#11)*
- [ ] Threshold tuning on **code** with measured precision / hit-rate *(in progress)*
- [ ] Secrets filter, per-user isolation, TTL
