"""Forwards a request to the real LLM provider (OpenAI/Anthropic-compatible).

If MOCK_PROVIDER is on (or no API key is set), returns a canned response so the
whole pipeline runs offline with no key and no cost. This lets the cache and
autopilot owners develop and test end-to-end without waiting on anything else.
"""
import time
import uuid

import httpx

from . import config


def _text_of(message: dict) -> str:
    """Text of a message whose content may be a string or a list of parts.

    The OpenAI format allows `content` to be a list
    (e.g. [{"type": "text", "text": "..."}, {"type": "image_url", ...}]);
    join the text parts and ignore the rest.
    """
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return ""


def _last_user_text(request: dict) -> str:
    """Text of the last *user* message (not merely the last message)."""
    for m in reversed(request.get("messages", [])):
        if m.get("role") == "user":
            text = _text_of(m)
            if text:
                return text
    return ""


def mock_response(request: dict) -> dict:
    text = _last_user_text(request)
    # Rough estimates, so the cost/autopilot pipeline has non-zero numbers to
    # work with offline. ~4 characters per token is the usual approximation.
    prompt_tokens = len(text) // 4
    completion_tokens = 10
    return {
        # Unique per call: a static id would collide across requests, which
        # matters because this project has a cache layer.
        "id": f"mock-cmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.get("model", config.DEFAULT_MODEL),
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"[MOCK REPLY] received {len(text)} characters of input.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


async def forward(request: dict) -> dict:
    if config.MOCK_PROVIDER or not config.PROVIDER_API_KEY:
        return mock_response(request)

    url = f"{config.PROVIDER_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.PROVIDER_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, headers=headers, json=request)
        r.raise_for_status()
        return r.json()
