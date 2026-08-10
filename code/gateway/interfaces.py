"""
THE CONTRACTS — frozen shared interfaces.

All three components plug into the gateway through these. Everyone builds
against them independently, using mocks for the others.

⚠️  Do NOT change this file without all three owners agreeing — a change here
    affects everyone.

Types are OpenAI-style dicts so any coding agent can talk to us.
"""
from typing import Protocol, Optional, Any

Message = dict[str, Any]      # {"role": "user"|"assistant"|"system", "content": str}
Request = dict[str, Any]      # a full chat-completions request body
Response = dict[str, Any]     # a full chat-completions response body
Stats = dict[str, Any]        # metrics (tokens saved, etc.)


class Trimmer(Protocol):
    """AGAM. Shrinks the request before it reaches the AI, safely."""
    def trim(self, messages: list[Message], token_budget: int, ctx: dict) -> tuple[list[Message], Stats]:
        ...


class Cache(Protocol):
    """DEVANSH. Reuses past answers for questions that mean the same thing."""
    def lookup(self, request: Request) -> Optional[Response]: ...
    def store(self, request: Request, response: Response) -> None: ...


class Autopilot(Protocol):
    """FURMAAN. Decides the cheapest safe path for each request."""
    def decide(self, request: Request, signals: dict) -> dict:
        """Return a plan, e.g. {"use_cache": True, "trim": False}."""
        ...
