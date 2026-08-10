# Cache (Devansh)

Semantic (meaning-based) cache. See docstring in `cache.py`.

## First tasks
- [ ] Start with exact-match caching (key = hash of messages).
- [ ] Add embeddings (sentence-transformers) + cosine similarity.
- [ ] Tune the similarity threshold (too low = wrong answers).
- [ ] Skip caching for secrets/PII; add a TTL.

## Contract (do not change alone)
`lookup(request) -> response | None`  ·  `store(request, response) -> None`
