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

---

## Week 4: A prose-tuned threshold is unsafe for code — so code gets exact match

### Context
In Week 3 I set the semantic threshold to 0.90 from prose pairs. A reviewer
pointed out the obvious thing I had skipped: our real payload is *code*, and the
embedding model (`all-MiniLM-L6-v2`) is trained on prose. I built a benchmark
(`cache/benchmark/`) of labelled code pairs — `same` (whitespace, renames, added
docstrings: should reuse) and `different` (single-token semantic flips: must not
reuse) — and measured cosine similarity for each.

### Problem
The two groups overlap. Same-meaning code scored 0.881–1.000; different-meaning
code scored 0.609–0.985. Opposite-meaning pairs sat at the very top:
`a and b` vs `a or b` = 0.985, an off-by-one slice = 0.972, `True` vs `False` =
0.970, `>` vs `>=` = 0.956. The only threshold with zero wrong reuses was 0.99,
which then missed 4 of 5 genuine reuses — the cache would save nothing.

### Key Observation
A one-operator change is textually almost identical, so a prose model reads the
two snippets as near-synonyms even though they compute opposite things. Prose
does not have this property — the prose pairs in the same benchmark separated
cleanly (same 0.978 vs different 0.609). The failure is the payload type, not the
approach. No amount of threshold tuning fixes it, because there is no gap to put
the threshold in.

### Solution
Route on payload type. `lookup()` first tries an exact text match (always safe),
then: if the request looks like code (`def `, `import `, or a code fence) it
**stops** — code never reuses on similarity; only prose goes on to the embedding
comparison. A reviewer stress-tested this with an adversarial embedder that
returns cosine 1.0 for every pair, and opposite-meaning code was still blocked.

### Takeaway
This turned the safety from a *numeric* guarantee ("the threshold is tuned
right") into a *structural* one ("code cannot be reused on similarity at all").
The benchmark's negative result belongs in the report as-is: a general-purpose
embedding cannot tell `>` from `>=`, so a code cache must not rely on it.

---

## Week 5: Measuring savings honestly — a curve and its limits, not a headline

### Context
With the cache complete, I measured what it actually saves. My first version
replayed a scripted session through the gateway logic and reported "56% fewer
tokens".

### Problem
The reviewer showed that the saving tracked the workload's repeat rate almost
1:1 (0%→0, 20%→21, 50%→50, 60%→63). The 56% was not a property of the cache; it
was a property of how I had written the script. Quoting it as a result would
have been misleading. Two more things were wrong: the benchmark claimed the
semantic layer caught paraphrases, but every generated request was code with
exact repeats, so the semantic path never ran; and the workload was all
single-message requests, while a real conversation re-asks questions with
history attached.

### Key Observation
Caching can only save on requests that repeat, so the honest output is a curve
over the repeat rate, not a number. And limitations have to be stated, not
implied away. Two mattered: (1) multi-turn conversations barely benefit, because
the cache keys on the full message history, so the same question on turn 3 has a
different key than on turn 1 — I verified it misses; keying on only the last
user turn is *not* a safe fix, since two different chats ending in "fix it"
would collide. (2) Latency: exact repeats and code cost ~0 ms, but a prose miss
embeds twice in the real gateway (lookup, then store), ~8 ms — about 1.7% of an
assumed 500 ms provider call — and the first request after startup pays a
one-time ~7 s model load.

### Solution
I rewrote the measurement to sweep repeat rates (avg of 25 sessions each):
0%→0, 20%→21%, 40%→39%, 50%→49%, 60%→53%, 80%→74%. I dropped the paraphrase
claim the benchmark could not back, wrote the limitations into `SAVINGS.md`, and
made the latency benchmark assert every hit/miss and exit loudly if the embedding
library is missing (it had silently reported 0 ms). Alongside this I made
exact-match reuse work with no embedding library at all, and bounded the store
with a size cap (LRU) and an optional sliding TTL so a long-running gateway
cannot grow without limit.

### Takeaway
Three reviews in a row caught me stating a number as if it were absolute when it
depended on the setup. The fix each time was the same: show the curve, show the
split, and state what the measurement does *not* cover. A result that survives
that is worth more than a bigger one that does not.

---

## Week 6: Tuning the threshold from live use, and building the instrument

### Context
The team needed a frontend, and Furmaan was unwell, so I took it on: a live
savings dashboard served by the gateway (per-request metering, a `/stats`
endpoint, a "Try it" prompt box, KPI cards, a per-request chart and an activity
feed), then ported onto the Dabang React/MUI template the team chose. Using it
against a real provider was the first time I exercised the cache by hand rather
than through tests.

### Problem
It felt like an exact-match cache. "what is the capital of france?" followed by
"which city is the capital of france" was forwarded twice. The embedder was
loaded and the comparison ran; the pair simply scored 0.867, just under the 0.90
bar from Week 3. The Week 3 pair ("Which city is France's capital?") had scored
0.935 — a slightly different wording, three hundredths lower, and a miss.

### Key Observation
0.90 was validated on a handful of pairs and was too strict for natural
rephrasings. The data still justified a lower bar: for prose, genuine paraphrases
score ~0.87–0.94 and genuinely different questions score ≤ 0.61 ("capital of
Japan" = 0.47), so 0.85 sits in that gap with ~0.25 of margin below it. And
because code is exact-match only (Week 4), the threshold never touches code
reuse — lowering it only loosens prose, where the gap is clean.

### Solution
Lowered the default to 0.85, exposed it as `CACHE_THRESHOLD` in the gateway
config so it can be tuned without a code change, and added a real-model test
that the motivating pair hits while "capital of japan?" still misses. On the
dashboard, the same paraphrase now shows as a cache hit with the tokens saved and
a ~50 ms round trip, next to the ~13 s first request that loaded the model.

### Takeaway
A threshold validated on five pairs is a hypothesis, not a fact; live use is the
next dataset. Building the dashboard was worth it for a second reason: it made
the cache's behaviour *visible*, which is what surfaced the miss in the first
place — and what will let an audience see, rather than take on trust, that the
gateway reuses by meaning.
