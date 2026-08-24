"""
Semantic Cache  —  OWNER: Devansh

Goal: reuse a past answer when a new question MEANS the same thing, even if
worded differently.

Build order (see cache/README.md):
  v1 (THIS FILE): EXACT-MATCH cache. Key = a hash of the whole request (minus a
      tiny denylist of fields that don't affect the answer). Only an identical
      request hits. No ML yet — this proves the plumbing (store -> lookup ->
      return) works with ZERO risk of a wrong answer.
  v2 (next):      SEMANTIC. Replace the hash key with an embedding + cosine
      similarity, reusing an answer only when similarity >= a conservative
      threshold. The lookup()/store() contract below does NOT change, so the
      gateway keeps working untouched.

Safety (added in a later version): never cache secrets/PII; support a TTL
(the in-memory store below grows without bound until then).
"""
import copy
import hashlib
import json
from typing import Optional

from gateway.interfaces import Request, Response

# Fields that provably DON'T change the model's answer, so two requests that
# differ only here may safely share a cache entry.
#
# This is a DENYLIST on purpose. The key hashes the whole request *except*
# these — so any field we haven't explicitly cleared (temperature, max_tokens,
# stream, tools, response_format, and any future OpenAI param) stays in the key.
# That means an unknown field causes an extra cache MISS (costs a little money),
# never a wrong HIT (costs correctness). Keep this set tiny and only add a field
# once you're sure it can't change the answer.
_IGNORED_FIELDS = frozenset({
    "user",  # OpenAI end-user id for abuse monitoring; doesn't affect output
})


def _make_key(request: Request) -> str:
    """Turn a request into a stable fingerprint string.

    Hashes every field of the request except `_IGNORED_FIELDS`, so anything
    that can change the answer — model, messages, temperature, max_tokens,
    stream, tools, response_format, ... — is part of the key. `sort_keys` makes
    the JSON deterministic; `default=str` keeps it from crashing on any exotic
    value.
    """
    fingerprint = {k: v for k, v in request.items() if k not in _IGNORED_FIELDS}
    blob = json.dumps(fingerprint, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class SemanticCache:
    def __init__(self) -> None:
        # v1 store: {key -> saved response}. An in-memory dict is enough to
        # prove the pipeline. v2 swaps this for embeddings + a vector store,
        # and adds a TTL so it stops growing forever.
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
