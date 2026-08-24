# Autopilot

**Owner:** Furmaan (1024240029) · **Code:** `code/autopilot/`

Decides, for every request, which cost-saving action to take — the "brain" that
ties the trimmer and the cache together.

## Why a decision layer is needed

It is tempting to apply every trick to every request, but the techniques
**overlap**. Trimming rewrites the prompt, which lowers how often the cache
matches. Blindly stacking them wastes effort and can reduce total savings.

The autopilot therefore picks the cheapest **safe** action per request, rather
than doing everything at once.

## Signals

Before deciding, it reads a few cheap signals:

| Signal | Why it matters |
|---|---|
| Estimated token count | Trimming a tiny request is not worth the delay |
| Contains code? | Selects the compiler-aware path |
| Contains secrets / PII? | Must not be cached |
| Cache similarity score | A hit is near-free |

## Decision order

The order follows the cost of each action — cheapest first:

```
1. Safety check      -> secrets present? do not cache
2. Cache lookup      -> hit? return the stored answer   (near-free)
3. Code-heavy?       -> trim the request
4. Otherwise         -> pass through untouched
```

``` python
def decide(request, signals):
    if signals["has_secrets"]:
        return {"use_cache": False, "trim": False}
    return {
        "use_cache": True,
        "trim": signals["has_code"] and signals["num_tokens_est"] > 1000,
    }
```

## Guardrails

- A **close-enough** cache match is not reused — correctness beats cost.
- Sensitive requests are never stored.
- Trimming is skipped when the context is too small to benefit.

## Measurement and tuning

The autopilot logs tokens saved, cache hit-rate, and cost per request. Those
measurements feed back into its thresholds — which is what makes it an
*autopilot* rather than a fixed rulebook.

## Status and next steps

- [ ] Full decision tree with safety checks
- [ ] Signal extraction (token count, code detection, secret detection)
- [ ] Conservative cache-reuse rule
- [ ] Metrics logging and threshold tuning
