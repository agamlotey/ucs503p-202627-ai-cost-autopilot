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

## Safety

- **Never cache secrets or personal data** — a filter rejects them.
- **Per-user isolation** — one user's cache is never served to another.
- **Time-to-live** — entries expire so stale answers are not reused forever.

## Build order

Version 1 is **exact-match** (key = hash of the messages). That proves the
store/lookup/return plumbing works with zero risk of a wrong match. The semantic
layer is then added on top.

## Status and next steps

- [ ] Exact-match cache (hash key)
- [ ] Embeddings + cosine similarity search
- [ ] Threshold tuning with measured precision / hit-rate
- [ ] Secrets filter, per-user isolation, TTL
