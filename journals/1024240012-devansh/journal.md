# Weekly Progress Journal: Devansh Sharma (Roll No: 1024240012)

**Project Name:** AI Cost Autopilot (a compiler-aware gateway for token-cost optimisation in LLM coding agents)  
**Component:** Semantic Cache

---

## Week 1: Why we start the cache with exact-match before semantic search

### Context
My component reuses past answers so the gateway does not pay the LLM twice for
the same question. The eventual goal is a *semantic* cache that matches questions
that mean the same thing, using embeddings.

### Problem
Jumping straight to embeddings adds several moving parts at once: an embedding
model, a vector store, and a similarity threshold. If a bug appears, it is hard
to tell whether the cache logic is wrong or the threshold is just badly tuned.

### Key Observation
The two hardest risks in a semantic cache are (a) returning a *wrong* answer
because two questions were only loosely similar, and (b) not knowing if the
plumbing (store / lookup / return) even works. Exact-match caching removes risk
(a) entirely and lets me verify the plumbing first.

### Solution
Version 1 keys the cache on a hash of the request messages, so only an identical
request hits:

```python
import hashlib, json

def key(request):
    blob = json.dumps(request["messages"], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()
```

Once store/lookup/return is proven correct end-to-end, I will add the semantic
layer on top: embed the request, find the nearest stored key, and only reuse the
answer if cosine similarity is above a **conservative** threshold. A wrong-but-
cheap answer is worse than paying, so the threshold starts high and is tuned
down carefully.

### Takeaway
Build the safe, boring version first to prove the pipeline, then add the smart
(and riskier) semantic layer with a measurable threshold.

---

## Week 2: Keying a cache on the right thing (a wrong hit is worse than a miss)

### Context
I built v1 of the semantic cache as an **exact-match** cache first (per my Week 1
plan): hash the request, store the answer, hand it back on an identical request.
The point of v1 was to prove the store → lookup → return pipeline before adding
any embeddings.

### Problem
My first key hashed only the `messages`. In review, my teammate pointed out this
serves *wrong* answers: the same question sent to a different **model**, or with
a different **temperature**, `max_tokens`, `stream`, or `response_format`, would
wrongly reuse the first answer. I reproduced it — all of those parameters
produced a false cache HIT. The nastiest was `stream: True` returning a stored
non-streaming dict, which can break the client.

### Key Observation
A cache can fail two ways, and they are not equal:
- a **miss** when it could have hit → we pay for one extra call (costs money);
- a **wrong hit** → we serve a wrong answer (costs correctness / trust).

When forced to choose, fail toward the miss. That reframes the whole key design.

### Solution
I inverted the key from an **allowlist** to a **denylist**. Instead of hashing
only two fields I trust, I hash the *whole* request except a tiny set of fields
proven not to affect the answer (currently just `user`):

```python
_IGNORED_FIELDS = frozenset({"user"})

def _make_key(request):
    fingerprint = {k: v for k, v in request.items() if k not in _IGNORED_FIELDS}
    return hashlib.sha256(
        json.dumps(fingerprint, sort_keys=True, default=str).encode()
    ).hexdigest()
```

Now any parameter I haven't explicitly cleared — including new OpenAI params that
don't exist yet — stays in the key and causes a safe miss, never a wrong hit. I
added regression tests for temperature, stream, an unknown param, and that
denylisted fields still share an entry.

### Takeaway
Design the failure direction on purpose. An allowlist quietly turns every new,
unrecognised field into a wrong-answer bug; a denylist turns it into a harmless
extra miss. "What is the safe way to be wrong?" is a better design question than
"how do I be right?".

---

## Week 3: Choosing a similarity threshold with real numbers, not a guess

### Context
v2 of the cache is **semantic**: instead of only matching identical requests, it
should reuse an answer when a new question *means* the same thing. I embed the
question text (`all-MiniLM-L6-v2`) and compare it to stored questions with cosine
similarity, reusing an answer only when similarity is above a threshold. The
model/parameter safety from Week 2 is preserved by first bucketing on a "hard
key" (model + params + message roles) and only comparing meaning *within* a
bucket.

### Problem
Everything hinges on the threshold. Too **low** and loosely-related questions
match, so I serve wrong answers — the exact failure I guarded against in Week 2.
Too **high** and real paraphrases miss, so the cache saves nothing. I did not
want to pick a number by vibes.

### Key Observation
The right threshold is wherever there is a clean *gap* between "same meaning" and
"different question". So I measured cosine similarity against a base question,
`"What is the capital of France?"`:

| Compared question | cosine |
|---|---|
| "Which city is France's capital?" (paraphrase) | 0.935 |
| "Tell me France's capital city" (paraphrase) | 0.909 |
| "What is the capital of Japan?" (different answer) | 0.474 |
| "How do I sort a list in Python?" (unrelated) | 0.112 |

Real paraphrases cluster at ~0.91–0.94; genuinely different questions sit at
≤0.47. There is a wide empty gap between them.

### Solution
I set the default threshold to **0.90**, which sits in that gap: it accepts both
paraphrases and rejects "capital of Japan?" (0.474) with large margin — that
France-vs-Japan case is precisely the wrong-answer risk, and it is rejected. The
threshold is configurable so it can be tuned on a larger benchmark set later, and
I locked the behaviour in with a test using the real model.

### Takeaway
A threshold is a claim about your data, so measure the data before setting it.
The gap between paraphrases (~0.92) and different questions (~0.47) is what makes
0.90 defensible — and it is a number I can show in the report, not a guess I have
to defend.
