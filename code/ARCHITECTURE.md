# Architecture

## Request flow
```
Coding agent (Cursor / Claude Code / Codex)
      |  POST /v1/chat/completions
      v
+-------------------- GATEWAY (FastAPI) --------------------+
| 1. compute signals (token count, has_code?)              |
| 2. autopilot.decide(request, signals) -> plan            |
| 3. if plan.use_cache -> cache.lookup() --hit--> return   |
| 4. if plan.trim      -> trimmer.trim()                   |
| 5. provider.forward() -> real LLM                        |
| 6. cache.store(request, response)                        |
| 7. return response                                       |
+----------------------------------------------------------+
```

## The contracts (gateway/interfaces.py)
| Component | Owner | Method |
|-----------|-------|--------|
| Trimmer   | Agam    | `trim(messages, token_budget, ctx) -> (messages, stats)` |
| Cache     | Devansh | `lookup(request) -> response \| None` ; `store(request, response)` |
| Autopilot | Furmaan | `decide(request, signals) -> plan` |

Each component is developed and tested on its own, using mock data for the
others. The gateway is the only place they meet.

## Milestones
- **M1** Gateway passthrough works + interfaces frozen.
- **M2** Each component v1 working solo (with mocks).
- **M3** Integrate all three + measure token savings on a test.
- **M4** Polish + demo.
