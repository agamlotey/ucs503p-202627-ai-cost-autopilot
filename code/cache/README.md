# Cache (Devansh)

Semantic (meaning-based) cache. See docstring in `cache.py`.

## First tasks
- [x] Start with exact-match caching (key = hash of messages).  *(v1, merged #9)*
- [x] Add embeddings (sentence-transformers) + cosine similarity.  *(v2)*
- [ ] Tune the similarity threshold (too low = wrong answers).
- [x] Add a TTL + size-cap eviction (store no longer grows unbounded).
- [ ] Skip caching for secrets/PII.

## Contract (do not change alone)
`lookup(request) -> response | None`  ·  `store(request, response) -> None`
