"""Measure how the gateway's token savings depend on how repetitive the
workload is.

Caching can only save on requests that repeat, so the saving is a function of
the workload's repeat rate, not a single headline number. This replays
synthetic sessions at several repeat rates through the same logic as
gateway/app.py (autopilot -> cache -> trimmer) and reports the curve.

Run:  python -m cache.benchmark.savings
"""
from __future__ import annotations

import random

from autopilot.policy import Autopilot
from cache.cache import SemanticCache
from gateway.app import compute_signals
from gateway import config
from trimmer.trimmer import CodeTrimmer, count_tokens

MODEL = "gpt-4o-mini"


def _tok(messages) -> int:
    text = "\n".join(m["content"] for m in messages
                     if isinstance(m.get("content"), str))
    return count_tokens(text)


def _distinct_request(k: int):
    """A distinct, code-bearing request (so each is a different cache key)."""
    code = f"def func{k}(x):\n    \"\"\"do thing {k}\"\"\"\n    return x + {k}\n"
    return [{"role": "user", "content": f"Explain func{k} in this file:\n{code}"}]


def _session(repeat_rate: float, n: int = 20, seed: int = 0):
    """A sequence of n requests where ~repeat_rate of them re-ask an earlier
    request verbatim (what an agent's retries / re-reads look like)."""
    rng = random.Random(seed)
    seq, nxt = [], 0
    for _ in range(n):
        if seq and rng.random() < repeat_rate:
            seq.append(rng.choice(seq))          # exact repeat of an earlier one
        else:
            seq.append(_distinct_request(nxt)); nxt += 1
    return seq


def _reduction_once(repeat_rate: float, seed: int) -> tuple[float, int]:
    cache = SemanticCache()
    autopilot = Autopilot()
    trimmer = CodeTrimmer()
    baseline = gateway = hits = 0
    for messages in _session(repeat_rate, seed=seed):
        body = {"model": MODEL, "messages": messages}
        baseline += _tok(messages)
        plan = autopilot.decide(body, compute_signals(body))
        if plan.get("use_cache") and cache.lookup(body) is not None:
            hits += 1
            continue                              # served free
        msgs = messages
        if plan.get("trim"):
            msgs, _ = trimmer.trim(messages, config.TOKEN_BUDGET, ctx={})
        gateway += _tok(msgs)
        cache.store(body, {"choices": [{"message": {"content": "..."}}]})
    saved = baseline - gateway
    return 100 * saved / baseline, hits


def _reduction(repeat_rate: float, seeds: int = 25) -> tuple[float, float]:
    """Average reduction and hit count over several random sessions."""
    rs = [_reduction_once(repeat_rate, s) for s in range(seeds)]
    red = sum(r for r, _ in rs) / seeds
    hits = sum(h for _, h in rs) / seeds
    return red, hits


def main():
    print("Token reduction vs. workload repeat rate (20 requests each)\n")
    print(f"  {'repeat rate':>12}  {'avg hits':>9}  {'reduction':>9}")
    for r in (0.0, 0.2, 0.4, 0.5, 0.6, 0.8):
        red, hits = _reduction(r)
        bar = "#" * round(red / 5)
        print(f"  {int(r*100):>10}%   {hits:>8.1f}   {red:>7.1f}%  {bar}")
    print("\nCaching saves in proportion to how often requests repeat, and adds")
    print("nothing on a workload with no repeats. This workload is code with")
    print("exact repeats, so every hit is an exact match; the semantic layer is")
    print("exercised separately in the cache tests and the threshold benchmark.")


if __name__ == "__main__":
    main()
