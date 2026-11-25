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

I grouped Weeks 2–8 retrospectively in the order the policy developed. The dates below identify the commits and reviews I used to reconstruct the work. The original working weeks are approximate.

## Week 2: First autopilot module

Repository record: 31 August 2026.

I added the first standalone module. It put the trimmer, cache and autopilot in
one file. The later gateway integration used the shared component interfaces.
[Initial module](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/commit/ba65dd2)

## Week 3: Routing large code requests

Repository record: 12 September 2026.

The policy used two signals to decide when to trim: the request contained code
and its estimated size exceeded 1,000 tokens. I added counters so we could see
which decision the policy made. [Routing policy](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/commit/b20c84d)

## Week 4: Missing secret signal

Repository record: 12 September 2026.

The gateway could supply a token estimate without a secret flag. I wired the
detector into the policy so the request text still got checked before cache
lookup. [Policy integration](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/commit/c530ecf)

## Week 5: Trimming a request that contains a secret

Repository record: 13 September 2026.

Originally a detected secret disabled both caching and trimming. I split the
decisions. A large code request can still be trimmed while its response stays
out of the cache. [Policy correction](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/commit/7f6af8c)

## Week 6: Multipart messages and false alarms

Repository record: 13 September 2026.

I added a case with a key in a text part beside an image part. The opposite
case mattered too: an ordinary assignment like `password = payload.get("password")`
should still be eligible for caching. [Detector cases](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/commit/7f6af8c)

## Week 7: Hyphens inside a key

Repository record: 13 September 2026.

A separate test used an OpenAI project key with a hyphen inside its body. I
updated the pattern and checked the actual routing decision in the test:
`use_cache` must be false. [Key-pattern fix](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/commit/68c7301)

## Week 8: Project overview and diagram review

Repository record: 13 September 2026.

I replaced the template README with the project overview and approved the
revised request-flow diagram. [README](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/pull/35) · [Diagram review](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/pull/36)

### Follow-up verification, 25 November 2026

I replayed Agam’s notes_api and ledger_cli fixtures through the mock gateway.
With the trimmer budget held at 1,000, policy thresholds of 500 and 1,000
forwarded the same input on both tasks. At 4,000 each went through in full.
I kept the default. [Routing measurements](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/pull/59)

Repeating a request with a dummy credential bypassed Devansh’s cache both
times. I followed the same decision into the dashboard and changed the shared
activity preview to read “Sensitive request”. In Chrome I checked both the
visible label and its tooltip, and verified that an ordinary prompt
still had a preview. [Dashboard change](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot/pull/61)
