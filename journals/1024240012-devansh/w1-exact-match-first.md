# Week 1 : Why we start the cache with exact-match before semantic search

## Context
My component reuses past answers so the gateway does not pay the LLM twice for
the same question. The eventual goal is a *semantic* cache that matches questions
that mean the same thing, using embeddings.

## Problem
Jumping straight to embeddings adds several moving parts at once: an embedding
model, a vector store, and a similarity threshold. If a bug appears, it is hard
to tell whether the cache logic is wrong or the threshold is just badly tuned.

## Key Observation
The two hardest risks in a semantic cache are (a) returning a *wrong* answer
because two questions were only loosely similar, and (b) not knowing if the
plumbing (store / lookup / return) even works. Exact-match caching removes risk
(a) entirely and lets me verify the plumbing first.

## Solution
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

## Takeaway
Build the safe, boring version first to prove the pipeline, then add the smart
(and riskier) semantic layer with a measurable threshold.
