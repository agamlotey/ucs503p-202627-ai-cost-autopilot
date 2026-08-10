"""
Semantic Cache  —  OWNER: Devansh

Goal: reuse a past answer when a new question MEANS the same thing, even if
worded differently.

Pipeline to build:
  1. Turn the request into a vector (embeddings, e.g. sentence-transformers).
  2. Find the nearest stored request (cosine similarity).
  3. If similarity >= threshold -> return the stored answer.
  4. Otherwise store the new (request -> answer) after the model replies.

Safety: never cache secrets/PII; support per-user isolation and a TTL.
"""
from typing import Optional
from gateway.interfaces import Request, Response


class SemanticCache:
    def __init__(self):
        # TODO(Devansh): replace with embeddings + a vector store (sqlite+numpy or FAISS).
        self._store: dict = {}

    def lookup(self, request: Request) -> Optional[Response]:
        # TODO(Devansh): embed request, return nearest answer above threshold.
        return None

    def store(self, request: Request, response: Response) -> None:
        # TODO(Devansh): embed + store, skipping anything sensitive.
        return None
