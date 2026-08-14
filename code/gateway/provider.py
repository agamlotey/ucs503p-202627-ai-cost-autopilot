"""Forwards a request to the real LLM provider (OpenAI/Anthropic-compatible).

If MOCK_PROVIDER is on (or no API key is set), returns a canned response so the
whole pipeline runs offline with no key and no cost. This lets the cache and
autopilot owners develop and test end-to-end without waiting on anything else.
"""
import httpx

from . import config


def _last_user_text(request: dict) -> str:
    for m in reversed(request.get("messages", [])):
        if isinstance(m.get("content"), str):
            return m["content"]
    return ""


def mock_response(request: dict) -> dict:
    text = _last_user_text(request)
    return {
        "id": "mock-cmpl-1",
        "object": "chat.completion",
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
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
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
