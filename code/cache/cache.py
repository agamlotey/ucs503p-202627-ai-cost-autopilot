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

Bounds: a size cap (LRU eviction) and an optional TTL keep the store from
growing without limit. The TTL is *sliding* — a hit refreshes an entry's timer —
so it bounds memory but does not guarantee freshness (a hot entry can outlive
`ttl_seconds`).

TODO (later): never cache secrets/PII; persist to a real vector store for the
shared cloud cache.
"""
from __future__ import annotations

import copy
import hashlib
import json
import time
from typing import Callable, Optional

from gateway.interfaces import Request, Response

# Fields that provably DON'T change the answer (see v1 review): requests that
# differ only here may share an entry. Keep tiny — anything not listed stays in
# the hard key, so an unknown param fails toward a MISS, never a wrong HIT.
_IGNORED_FIELDS = frozenset({"user"})

# Prose threshold. Measured with all-MiniLM on natural-language pairs:
# genuine paraphrases score ~0.87-0.94 ("what is the capital of france?" vs
# "which city is the capital of france" = 0.867), while genuinely different
# questions score <= 0.61 ("capital of Japan" = 0.47). 0.85 sits in that gap
# with ~0.25 of margin below it. Only prose uses this — code is exact-match
# (benchmark/FINDINGS.md), so the value never affects code reuse. Tunable via
# CACHE_THRESHOLD in the gateway config.
DEFAULT_THRESHOLD = 0.85

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


def _looks_like_code(text: str) -> bool:
    """Same cheap heuristic the gateway uses for its `has_code` signal."""
    return ("```" in text) or ("def " in text) or ("import " in text)


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
        max_entries: Optional[int] = 10_000,
        ttl_seconds: Optional[float] = None,
        _now: Callable[[], float] = time.time,
    ) -> None:
        # buckets: hard_key -> list of entries. Each entry is a mutable list
        # [semantic_text, vector, response, last_used_ts]. We only compare within
        # one bucket, preserving exact-match-on-settings safety while matching
        # meaning on the text. `last_used_ts` is set on store and refreshed on a
        # hit; it drives TTL expiry and LRU eviction so a long-running gateway
        # can't grow without limit.
        self._buckets: dict[str, list[list]] = {}
        self._threshold = threshold
        self._embedder: Optional[Callable[[str], Vector]] = embed_fn
        self._disabled = False
        # Bounds (both optional):
        #   max_entries : hard cap on total cached answers; least-recently-used
        #                 entries are evicted once the cap is exceeded.
        #   ttl_seconds : an entry not used within this many seconds is dropped.
        self._max_entries = max_entries
        self._ttl = ttl_seconds
        self._now = _now

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

    # ---- expiry / eviction ------------------------------------------------

    def _drop_expired(self, bucket: list) -> None:
        if self._ttl is None:
            return
        cutoff = self._now() - self._ttl
        bucket[:] = [e for e in bucket if e[3] >= cutoff]

    def _total(self) -> int:
        return sum(len(b) for b in self._buckets.values())

    def _evict(self) -> None:
        # First expire stale entries everywhere, then evict least-recently-used
        # entries until we are back under the size cap.
        if self._ttl is not None:
            for key in list(self._buckets):
                self._drop_expired(self._buckets[key])
                if not self._buckets[key]:
                    del self._buckets[key]
        if self._max_entries is None:
            return
        while self._total() > self._max_entries:
            oldest_key = oldest_i = None
            oldest_ts = None
            for key, b in self._buckets.items():
                for i, e in enumerate(b):
                    if oldest_ts is None or e[3] < oldest_ts:
                        oldest_key, oldest_i, oldest_ts = key, i, e[3]
            if oldest_key is None:
                break
            del self._buckets[oldest_key][oldest_i]
            if not self._buckets[oldest_key]:
                del self._buckets[oldest_key]

    # ---- contract ---------------------------------------------------------

    def lookup(self, request: Request) -> Optional[Response]:
        """Return a saved answer whose request has the same hard key AND whose
        text matches (exact for code, semantic >= threshold for prose), else
        None. Expired entries are skipped. Returns a copy so a caller mutating
        the response can't corrupt the cache."""
        key = _hard_key(request)
        bucket = self._buckets.get(key)
        if not bucket:
            return None
        self._drop_expired(bucket)
        if not bucket:
            del self._buckets[key]
            return None
        text = _semantic_text(request)
        now = self._now()

        # 1) EXACT text match — always available, needs no embedder. Covers code
        #    (exact-only) AND identical prose, so the cache still saves money
        #    when sentence-transformers isn't installed.
        for entry in bucket:
            if entry[0] == text:
                entry[3] = now          # LRU touch
                return copy.deepcopy(entry[2])

        # 2) CODE never reuses on similarity: a one-operator change (`>` vs `>=`,
        #    `and` vs `or`) is textually near-identical, so cosine cannot tell
        #    opposite-meaning code apart (benchmark/FINDINGS.md: 0.92-0.99).
        if _looks_like_code(text):
            return None

        # 3) NATURAL-LANGUAGE: semantic reuse above the threshold.
        query = self._embed(text)
        if query is None:               # embedder unavailable -> no fuzzy match
            return None
        best_score, best = -1.0, None
        for entry in bucket:
            if entry[1] is None:        # entry stored without an embedding
                continue
            score = _cosine(query, entry[1])
            if score >= best_score:     # >= so the newest entry wins on a tie
                best_score, best = score, entry
        if best is not None and best_score >= self._threshold:
            best[3] = now               # LRU touch
            return copy.deepcopy(best[2])
        return None

    def store(self, request: Request, response: Response) -> None:
        """Remember this request -> response so a future same-meaning request
        (same hard key) is free. Stores a copy, then enforces the TTL and
        size cap."""
        text = _semantic_text(request)
        # Embed ONLY for prose: code reuses by exact text, so its vector is never
        # consulted. If the embedder is unavailable, vec stays None and the entry
        # is still stored, so exact-match reuse works without the ML dependency.
        vec = None if _looks_like_code(text) else self._embed(text)
        bucket = self._buckets.setdefault(_hard_key(request), [])
        snapshot = copy.deepcopy(response)
        now = self._now()
        for entry in bucket:
            if entry[0] == text:        # same request -> refresh in place
                entry[1], entry[2], entry[3] = vec, snapshot, now
                return
        bucket.append([text, vec, snapshot, now])
        self._evict()
