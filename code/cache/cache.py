"""
Semantic Cache  —  OWNER: Devansh

Goal: reuse a past answer when a new question MEANS the same thing, even if
worded differently.

v2 (THIS FILE): SEMANTIC cache.
  - HARD key (must match exactly): model + params + message structure. Same
    safety as v1 — a different model or temperature can have a different right
    answer, so those never share an entry.
  - SEMANTIC match (fuzzy): the natural-language text of the messages, compared
    with an embedding + cosine similarity. Two differently-worded questions with
    the same meaning reuse the same answer — but ONLY within the same hard key.
  - A conservative similarity THRESHOLD gates reuse: a wrong-but-free answer is
    worse than paying, so we only reuse when we're really sure.

The lookup()/store() contract is unchanged from v1, so the gateway keeps working
untouched.

Design notes:
  - The embedder is injectable (embed_fn). The default lazily loads
    sentence-transformers ("all-MiniLM-L6-v2", 384-dim); tests pass a tiny fake
    so they run fast and don't need PyTorch. Mirrors the trimmer's optional
    tree-sitter: the component degrades/stubs gracefully.
  - An identical request still hits (its text embeds to the same vector,
    cosine == 1.0 >= threshold), so semantic subsumes v1's exact match.

TODO (later): never cache secrets/PII; add a TTL/eviction (the store below grows
without bound); persist to a real vector store for the shared cloud cache.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Callable, Optional

from gateway.interfaces import Request, Response

# Fields that provably DON'T change the answer (see v1 review): requests that
# differ only here may share an entry. Keep tiny — anything not listed stays in
# the hard key, so an unknown param fails toward a MISS, never a wrong HIT.
_IGNORED_FIELDS = frozenset({"user"})

# Conservative default. all-MiniLM cosine: identical ~1.0, close paraphrase
# ~0.9+, loosely related ~0.6-0.8. Start high to avoid wrong answers; tune DOWN
# later with real benchmark numbers (that measurement is the ML deliverable).
DEFAULT_THRESHOLD = 0.90

# Sentinel type for an embedding vector: a list[float] (kept plain so the module
# imports even when numpy isn't installed; numpy is only needed for the default
# embedder and the cosine math, which are guarded).
Vector = list


def _hard_key(request: Request) -> str:
    """Fingerprint of everything that must match EXACTLY: all fields except the
    denylist AND except the message *content text* (that's matched semantically
    instead). Message roles/structure ARE included, so a system+user pair can't
    match a bare user message."""
    scaffold = {
        k: v for k, v in request.items()
        if k not in _IGNORED_FIELDS and k != "messages"
    }
    scaffold["_roles"] = [m.get("role") for m in request.get("messages", [])]
    blob = json.dumps(scaffold, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _semantic_text(request: Request) -> str:
    """The natural-language text we compare by meaning: all string message
    contents joined in order."""
    parts = []
    for m in request.get("messages", []):
        c = m.get("content")
        if isinstance(c, str):
            parts.append(c)
        elif isinstance(c, list):  # OpenAI multipart content
            parts.extend(p.get("text", "") for p in c
                         if isinstance(p, dict) and p.get("type") == "text")
    return "\n".join(parts)


def _default_embedder() -> Callable[[str], Vector]:
    """Lazily build the real sentence-transformers embedder. Imported here so
    the module (and the whole gateway) still loads if the library is absent."""
    from sentence_transformers import SentenceTransformer  # heavy import
    model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed(text: str) -> Vector:
        return model.encode(text, normalize_embeddings=True).tolist()

    return embed


def _cosine(a: Vector, b: Vector) -> float:
    """Cosine similarity of two vectors, no numpy required."""
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class SemanticCache:
    def __init__(
        self,
        embed_fn: Optional[Callable[[str], Vector]] = None,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        # buckets: hard_key -> list of (vector, stored_response). We only ever
        # compare within one bucket, preserving v1's exact-match-on-settings
        # safety while matching meaning on the text.
        # bucket entry = (semantic_text, vector, response). Text is kept so a
        # re-store of the SAME request overwrites instead of appending.
        self._buckets: dict[str, list[tuple[str, Vector, Response]]] = {}
        self._threshold = threshold
        self._embedder: Optional[Callable[[str], Vector]] = embed_fn
        # If the embedding library is missing we can't do semantic matching, so
        # the cache turns into a safe no-op (every lookup misses, store is
        # dropped) and the gateway keeps running — same graceful degradation as
        # the trimmer without tree-sitter.
        self._disabled = False

    def _embed(self, text: str) -> Optional[Vector]:
        # Build the real embedder on first use (so importing the module is cheap
        # and never triggers the PyTorch download until a request actually needs
        # semantic matching).
        if self._disabled:
            return None
        if self._embedder is None:
            try:
                self._embedder = _default_embedder()
            except Exception:  # sentence-transformers not installed
                self._disabled = True
                return None
        return self._embedder(text)

    def lookup(self, request: Request) -> Optional[Response]:
        """Return a saved answer whose request has the same hard key AND whose
        text is semantically close enough (cosine >= threshold), else None.

        Returns a copy so a caller mutating the response can't corrupt the cache.
        """
        bucket = self._buckets.get(_hard_key(request))
        if not bucket:
            return None
        query = self._embed(_semantic_text(request))
        if query is None:            # embedder unavailable -> safe miss
            return None
        best_score, best_resp = -1.0, None
        for _text, vec, resp in bucket:
            score = _cosine(query, vec)
            if score >= best_score:   # >= so the newest entry wins on a tie
                best_score, best_resp = score, resp
        if best_resp is not None and best_score >= self._threshold:
            return copy.deepcopy(best_resp)
        return None

    def store(self, request: Request, response: Response) -> None:
        """Remember this request -> response so a future same-meaning request
        (same hard key) is free. Stores a copy so later mutation of the caller's
        object doesn't change what's cached."""
        text = _semantic_text(request)
        vec = self._embed(text)
        if vec is None:              # embedder unavailable -> don't cache
            return
        bucket = self._buckets.setdefault(_hard_key(request), [])
        snapshot = copy.deepcopy(response)
        for i, (etext, _vec, _resp) in enumerate(bucket):
            if etext == text:        # same request -> refresh in place, don't append
                bucket[i] = (text, vec, snapshot)
                return
        bucket.append((text, vec, snapshot))
