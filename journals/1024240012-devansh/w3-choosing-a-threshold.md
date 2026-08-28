# Week 3 : Choosing a similarity threshold with real numbers, not a guess

## Context
v2 of the cache is **semantic**: instead of only matching identical requests, it
should reuse an answer when a new question *means* the same thing. I embed the
question text (`all-MiniLM-L6-v2`) and compare it to stored questions with cosine
similarity, reusing an answer only when similarity is above a threshold. The
model/parameter safety from Week 2 is preserved by first bucketing on a "hard
key" (model + params + message roles) and only comparing meaning *within* a
bucket.

## Problem
Everything hinges on the threshold. Too **low** and loosely-related questions
match, so I serve wrong answers — the exact failure I guarded against in Week 2.
Too **high** and real paraphrases miss, so the cache saves nothing. I did not
want to pick a number by vibes.

## Key Observation
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

## Solution
I set the default threshold to **0.90**, which sits in that gap: it accepts both
paraphrases and rejects "capital of Japan?" (0.474) with large margin — that
France-vs-Japan case is precisely the wrong-answer risk, and it is rejected. The
threshold is configurable so it can be tuned on a larger benchmark set later, and
I locked the behaviour in with a test using the real model.

## Takeaway
A threshold is a claim about your data, so measure the data before setting it.
The gap between paraphrases (~0.92) and different questions (~0.47) is what makes
0.90 defensible — and it is a number I can show in the report, not a guess I have
to defend.
