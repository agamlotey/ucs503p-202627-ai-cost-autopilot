"""
The gateway. Wires the three components together.

Flow:  request -> signals -> autopilot.decide -> (cache.lookup) ->
       (trimmer.trim) -> provider.forward -> cache.store -> response
"""
import copy

from fastapi import FastAPI, Request

from . import provider, config
from trimmer.trimmer import CodeTrimmer
from cache.cache import SemanticCache
from autopilot.policy import Autopilot

app = FastAPI(title="AI Cost Autopilot")

trimmer = CodeTrimmer()      # Agam
cache = SemanticCache()      # Devansh
autopilot = Autopilot()      # Furmaan


def compute_signals(body: dict) -> dict:
    """Cheap signals the autopilot uses to decide."""
    text = " ".join(
        m.get("content", "")
        for m in body.get("messages", [])
        if isinstance(m.get("content"), str)
    )
    return {
        "num_tokens_est": len(text) // 4,
        "has_code": ("```" in text) or ("def " in text) or ("import " in text),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(req: Request):
    body = await req.json()

    # Snapshot the request BEFORE trimming mutates it. The cache must key on the
    # *original* request for both lookup and store — otherwise the response gets
    # stored under the trimmed key and the next identical request never hits.
    original = copy.deepcopy(body)

    signals = compute_signals(original)
    plan = autopilot.decide(original, signals)

    if plan.get("use_cache"):
        hit = cache.lookup(original)
        if hit is not None:
            return hit

    if plan.get("trim"):
        body["messages"], _stats = trimmer.trim(
            body.get("messages", []), config.TOKEN_BUDGET, ctx={}
        )

    response = await provider.forward(body)

    if plan.get("use_cache"):
        cache.store(original, response)
    return response
