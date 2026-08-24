"""
Semantic Cache  —  OWNER: Devansh

Goal: reuse a past answer when a new question MEANS the same thing, even if
worded differently.

Build order (see cache/README.md):
  v1 (THIS FILE): EXACT-MATCH cache. Key = a hash of the request messages
      (plus the model). Only an identical request hits. No ML yet — this proves
      the plumbing (store -> lookup -> return) works with ZERO risk of a wrong
      answer.
  v2 (next):      SEMANTIC. Replace the hash key with an embedding + cosine
      similarity, reusing an answer only when similarity >= a conservative
      threshold. The lookup()/store() contract below does NOT change, so the
      gateway keeps working untouched.

Safety (added in a later version): never cache secrets/PII; support a TTL.
"""
import copy
import hashlib
import json
from typing import Optional

from gateway.interfaces import Request, Response


def _make_key(request: Request) -> str:
    """Turn a request into a stable fingerprint string.

    The key covers BOTH the messages AND the model: the same question sent to
    two different models can have two different right answers, so they must not
    share a cache entry. `sort_keys` makes the JSON deterministic so
    {"a":1,"b":2} and {"b":2,"a":1} produce the same key.
    """
    fingerprint = {
        "model": request.get("model"),
        "messages": request.get("messages", []),
    }
    blob = json.dumps(fingerprint, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class SemanticCache:
    def __init__(self) -> None:
        # v1 store: {key -> saved response}. An in-memory dict is enough to
        # prove the pipeline. v2 swaps this for embeddings + a vector store.
        self._store: dict[str, Response] = {}

    def lookup(self, request: Request) -> Optional[Response]:
        """Return a saved answer for this exact request, or None if we've
        never seen it before.

        Returns a *copy* so a caller that mutates the response can't corrupt
        the cached original (which would poison every later hit).
        """
        hit = self._store.get(_make_key(request))
        return copy.deepcopy(hit) if hit is not None else None

    def store(self, request: Request, response: Response) -> None:
        """Remember this request -> response so the next identical request is
        free.

        Stores a *copy* so later mutation of the caller's object doesn't
        silently change what's cached.
        """
        self._store[_make_key(request)] = copy.deepcopy(response)
