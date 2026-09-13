"""
The gateway. Wires the three components together.

Flow:  request -> signals -> autopilot.decide -> (cache.lookup) ->
       (trimmer.trim) -> provider.forward -> cache.store -> response
"""
import copy
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from . import provider, config
from .metrics import metrics
from trimmer.trimmer import CodeTrimmer, count_tokens
from cache.cache import SemanticCache
from autopilot.policy import Autopilot

app = FastAPI(title="AI Cost Autopilot")

trimmer = CodeTrimmer()      # Agam
cache = SemanticCache(                       # Devansh
    threshold=config.CACHE_THRESHOLD,
    max_entries=config.CACHE_MAX_ENTRIES,
    ttl_seconds=config.CACHE_TTL_SECONDS,
)
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


def _tokens(messages: list) -> int:
    """Billable tokens in a message list."""
    text = "\n".join(m["content"] for m in messages
                     if isinstance(m.get("content"), str))
    return count_tokens(text) if text else 0


def _preview(body: dict, n: int = 60) -> str:
    """First line of the latest user message that is not code, for the activity
    feed. A coding agent sends the task and then one message per file, so the
    last message is usually a file; the task is the useful label."""
    users = [m["content"] for m in body.get("messages", [])
             if m.get("role") == "user" and isinstance(m.get("content"), str)]
    if not users:
        return ""
    prose = [t for t in users if not compute_signals({"messages": [{"content": t}]})["has_code"]]
    lines = (prose or users)[-1].strip().splitlines()
    return (lines or [""])[0][:n]              # an empty message must not crash


_DASHBOARD = os.path.join(os.path.dirname(__file__), "static", "dashboard.html")


@app.get("/", response_class=HTMLResponse)
def dashboard():
    """The live savings dashboard (same origin as /stats, so no CORS)."""
    with open(_DASHBOARD, encoding="utf-8") as f:
        return f.read()


@app.get("/stats")
def stats():
    """Running totals + recent activity for the dashboard."""
    return metrics.snapshot()


@app.post("/stats/reset")
def stats_reset():
    metrics.reset()
    return {"status": "reset"}


@app.get("/benchmarks")
def benchmarks():
    """Measured results (trimmer vs baselines, cache curve, secret detection,
    latency) for the dashboard. Computed once per process, then cached."""
    from .benchmarks import all_results
    return all_results()


@app.get("/demo/example-request")
def example_request():
    """A realistic coding request: a task plus the 10 files of the notes_api
    fixture, one message per file, the way a coding agent sends them. A typed
    one-line prompt has no code to trim; this shows what the trimmer does."""
    from trimmer.fixtures.loader import as_messages
    task = "fix create_note"
    messages = as_messages(task)
    return {"task": task, "files": len(messages) - 1, "messages": messages}


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
    baseline = _tokens(original.get("messages", []))
    model = original.get("model", config.DEFAULT_MODEL)
    preview = _preview(original)

    signals = compute_signals(original)
    plan = autopilot.decide(original, signals)

    if plan.get("use_cache"):
        hit = cache.lookup(original)
        if hit is not None:
            metrics.record(baseline=baseline, sent=0, outcome="cache",
                           model=model, preview=preview)
            return hit

    if plan.get("trim"):
        body["messages"], _stats = trimmer.trim(
            body.get("messages", []), config.TOKEN_BUDGET, ctx={}
        )

    response = await provider.forward(body)

    if plan.get("use_cache"):
        cache.store(original, response)

    sent = _tokens(body.get("messages", []))
    outcome = "trim" if sent < baseline else "forward"
    metrics.record(baseline=baseline, sent=sent, outcome=outcome,
                   model=model, preview=preview)
    return response
