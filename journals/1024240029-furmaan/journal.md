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

## Retrospective for Weeks 2–8

I reconstructed these notes from my commits and reviews on 25 November. The
dates below are the dates of the work. I still need to confirm which course
week each entry belongs to.

### 31 August — First autopilot module

I added the first standalone module. It put the trimmer, cache and autopilot in
one file. The later gateway integration used the shared component interfaces.
[Initial module](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/commit/ba65dd2)

### 12 September — Routing large code requests

The policy used two signals to decide when to trim: the request contained code
and its estimated size exceeded 1,000 tokens. I added counters so we could see
which decision the policy made. [Routing policy](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/commit/b20c84d)

### 12 September — Missing secret signal

The gateway could supply a token estimate without a secret flag. I wired the
detector into the policy so the request text still got checked before cache
lookup. [Policy integration](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/commit/c530ecf)

### 13 September — Trimming a request that contains a secret

Originally a detected secret disabled both caching and trimming. I split the
decisions. A large code request can still be trimmed while its response stays
out of the cache. [Policy correction](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/commit/7f6af8c)

### 13 September — Multipart messages and false alarms

I added a case with a key in a text part beside an image part. The opposite
case mattered too: an ordinary assignment like `password = payload.get("password")`
should still be eligible for caching. [Detector cases](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/commit/7f6af8c)

### 13 September — Hyphens inside a key

A separate test used an OpenAI project key with a hyphen inside its body. I
updated the pattern and checked the actual routing decision in the test:
`use_cache` must be false. [Key-pattern fix](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/commit/68c7301)

### 13 September — Project overview and diagram review

I replaced the template README with the project overview and approved the
revised request-flow diagram. [README](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/pull/35) · [Diagram review](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/pull/36)
