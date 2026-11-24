# Weekly Progress Journal: Furmaandeep Kaur (Roll No: 1024240029)

**Project Name:** AI Cost Autopilot (a compiler-aware gateway for token-cost optimisation in LLM coding agents)  
**Component:** Autopilot Policy

---

## Week 1: Designing the autopilot decision order

### Context
My component decides, for each request, which cost-saving action to take: reuse a
cached answer, trim the request, or send it as-is. The trimmer and cache are
built by teammates; my job is to choose between them safely.

### Problem
It is tempting to always apply every trick. But trimming and caching partly
overlap — trimming rewrites the prompt, which lowers how often the cache matches.
Blindly stacking them wastes effort and can even reduce savings.

### Key Observation
The actions have a natural cost order. A cache hit is almost free, so it should be
checked first. Trimming only helps when there is a lot of code to cut. Tiny
requests should be left alone, since trimming just adds delay.

### Solution
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

### Takeaway
Pick the cheapest safe action per request instead of stacking every trick. The
decision order (safety -> cache -> trim -> passthrough) came straight from the
cost of each action.

## 12 September 2026 — Putting the policy behind the gateway

I wired the routing decision to the secret detector. The gateway could send a
code flag and a token estimate without a secret flag, so the policy needed to
scan the request itself in that case. For ordinary code requests, I used 1,000
estimated tokens as the default trimming threshold and added counters for the
decisions. [Implementation and review](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/pull/26)

## 13 September 2026 — What a secret changes

My first implementation disabled both caching and trimming when it detected a
secret. I changed that decision so a large code request can still be trimmed
while its response stays out of the cache. I added cases for text inside a
multipart message and for ordinary code that mentions an auth variable.
A separate fix covered hyphens inside OpenAI keys.
[Routing and multipart fix](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/commit/7f6af8c) · [Key-pattern fix](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/commit/68c7301)

I also replaced the template README with the project overview and reviewed the
revised request-flow diagram. [README](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/pull/35) · [Diagram review](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/pull/36)
