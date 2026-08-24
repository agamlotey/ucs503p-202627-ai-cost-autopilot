"""
Semantic Cache  —  OWNER: Devansh

Goal: reuse a past answer when a new question MEANS the same thing, even if
worded differently.

Build order (see cache/README.md):
  v1 (THIS FILE): EXACT-MATCH cache. Key = a hash of the request messages.
      Only an identical request hits. No ML yet — this proves the plumbing
      (store -> lookup -> return) works with ZERO risk of a wrong answer.
  v2 (next):      SEMANTIC. Replace the hash key with an embedding + cosine
      similarity, reusing an answer only when similarity >= a conservative
      threshold. The lookup()/store() contract below does NOT change, so the
      gateway keeps working untouched.

Safety (added in a later version): never cache secrets/PII; support a TTL.
"""
import hashlib
import json
from typing import Optional

from gateway.interfaces import Request, Response


def _make_key(request: Request) -> str:
    """Turn a request into a stable fingerprint string.

    Two requests with the same messages produce the same key; any difference
    (even word order inside the text) produces a different key. `sort_keys`
    makes the JSON deterministic so {"a":1,"b":2} and {"b":2,"a":1} match.
    """
    messages = request.get("messages", [])
    blob = json.dumps(messages, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class SemanticCache:
    def __init__(self) -> None:
        # v1 store: {key -> saved response}. An in-memory dict is enough to
        # prove the pipeline. v2 swaps this for embeddings + a vector store.
        self._store: dict[str, Response] = {}

    def lookup(self, request: Request) -> Optional[Response]:
        """Return a saved answer for this exact request, or None if we've
        never seen it before."""
        return self._store.get(_make_key(request))

    def store(self, request: Request, response: Response) -> None:
        """Remember this request -> response so the next identical request is
        free."""
        self._store[_make_key(request)] = response
