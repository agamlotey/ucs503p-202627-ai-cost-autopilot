# Week 1 : Designing the autopilot decision order

## Context
My component decides, for each request, which cost-saving action to take: reuse a
cached answer, trim the request, or send it as-is. The trimmer and cache are
built by teammates; my job is to choose between them safely.

## Problem
It is tempting to always apply every trick. But trimming and caching partly
overlap — trimming rewrites the prompt, which lowers how often the cache matches.
Blindly stacking them wastes effort and can even reduce savings.

## Key Observation
The actions have a natural cost order. A cache hit is almost free, so it should be
checked first. Trimming only helps when there is a lot of code to cut. Tiny
requests should be left alone, since trimming just adds delay.

## Solution
The policy checks the cheapest safe option first and stops as soon as one applies:

```python
def decide(request, signals):
    if signals["has_secrets"]:          # safety first
        return {"use_cache": False, "trim": False}
    return {
        "use_cache": True,              # a hit is near-free, try it first
        "trim": signals["has_code"] and signals["num_tokens_est"] > 1000,
    }
```

The gateway then does: cache lookup -> (if miss) trim -> forward. A separate
conservative rule ensures a "close-enough" cache match is **not** reused, because
a wrong-but-cheap answer is worse than paying full price.

## Takeaway
Pick the cheapest safe action per request instead of stacking every trick. The
decision order (safety -> cache -> trim -> passthrough) came straight from the
cost of each action.
