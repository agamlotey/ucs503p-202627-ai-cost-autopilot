# Threshold benchmark — can cosine similarity safely gate a code cache?

**Question.** The semantic cache reuses a stored answer when a new request is
"similar enough" (cosine of `all-MiniLM-L6-v2` embeddings >= threshold). Earlier
tuning on *prose* found a clean gap at 0.90. But our real payload is **code**.
Is any threshold safe for code?

**Method.** `run.py` scores labeled pairs (`pairs.py`): `same` = should reuse
(want high), `different` = must not reuse (want low). A safe threshold needs
every `same` above it and every `different` below it.

## Result: no safe threshold for code

| Group | cosine range |
|---|---|
| SAME meaning (should reuse) | 0.881 - 1.000 |
| DIFFERENT meaning (must NOT reuse) | 0.609 - 0.985 |

The ranges **overlap** (0.881-0.985), so no single threshold separates them.
Worse, opposite-meaning *code* scores at the very top:

| Different-meaning code pair | cosine |
|---|---|
| `return a and b` vs `return a or b` | 0.985 |
| `xs[:n]` vs `xs[:n-1]` (off-by-one) | 0.972 |
| `return True` vs `return False` | 0.970 |
| `a > b` vs `a >= b` | 0.956 |
| `x + 1` vs `x - 1` | 0.937 |

The only threshold with **zero** wrong reuses is 0.99, which then misses 4 of 5
genuine reuses - i.e. the cache stops saving anything.

## Why

`all-MiniLM-L6-v2` is trained on natural-language prose. A one-operator change
(`>`->`>=`, `and`->`or`) is textually almost identical, so the model reads the
two snippets as near-synonyms - even though they compute opposite things. Prose
does not have this property, which is why the prose pairs *do* separate cleanly
(same = 0.978, different = 0.609).

## Recommendation

1. **Gate semantic caching to natural-language requests**; use exact-match (v1)
   for code payloads. The gateway already computes a `has_code` signal.
2. Longer term, evaluate a **code-aware embedding** (e.g. a CodeBERT/StarCoder
   embedder) and re-run this benchmark before trusting semantic reuse on code.

A wrong reuse serves a wrong answer, so on code the safe default is: **don't
reuse semantically - require an exact match.**
