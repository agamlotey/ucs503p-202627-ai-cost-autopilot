"""Forwards a request to the real LLM provider (OpenAI/Anthropic-compatible)."""
import httpx
from . import config


async def forward(request: dict) -> dict:
    url = f"{config.PROVIDER_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.PROVIDER_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, headers=headers, json=request)
        r.raise_for_status()
        return r.json()
