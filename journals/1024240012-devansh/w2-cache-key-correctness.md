# Week 2 : Keying a cache on the right thing (a wrong hit is worse than a miss)

## Context
I built v1 of the semantic cache as an **exact-match** cache first (per my Week 1
plan): hash the request, store the answer, hand it back on an identical request.
The point of v1 was to prove the store → lookup → return pipeline before adding
any embeddings.

## Problem
My first key hashed only the `messages`. In review, my teammate pointed out this
serves *wrong* answers: the same question sent to a different **model**, or with
a different **temperature**, `max_tokens`, `stream`, or `response_format`, would
wrongly reuse the first answer. I reproduced it — all of those parameters
produced a false cache HIT. The nastiest was `stream: True` returning a stored
non-streaming dict, which can break the client.

## Key Observation
A cache can fail two ways, and they are not equal:
- a **miss** when it could have hit → we pay for one extra call (costs money);
- a **wrong hit** → we serve a wrong answer (costs correctness / trust).

When forced to choose, fail toward the miss. That reframes the whole key design.

## Solution
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

## Takeaway
Design the failure direction on purpose. An allowlist quietly turns every new,
unrecognised field into a wrong-answer bug; a denylist turns it into a harmless
extra miss. "What is the safe way to be wrong?" is a better design question than
"how do I be right?".
