"""Measured results for the dashboard's "Measured results" section.

Nothing here is hard-coded where it can be measured: the trimmer table and the
cache curve are computed by the same benchmark code that the report and the
command line use, the first time they are asked for, then kept in memory. Only
latency comes from cache/benchmark/LATENCY.md, because measuring it needs the
embedding model, which may not be installed where the gateway runs.
"""
from __future__ import annotations

import os
import random
import re
import string
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
LATENCY_MD = os.path.join(HERE, "..", "cache", "benchmark", "LATENCY.md")

REPEAT_RATES = (0.0, 0.2, 0.4, 0.5, 0.6, 0.8)


def _trimmer_table() -> dict:
    from trimmer.benchmark.baselines import run

    task, fixture = "fix create_note", "notes_api"
    rows = [
        {"variant": r.name, "tokens": r.tokens, "saved_pct": round(r.saved_pct, 1),
         "valid": r.valid, "note": r.note}
        for r in run(task, fixture)
    ]
    return {"task": task, "fixture": fixture, "rows": rows,
            "command": "python -m trimmer.benchmark.baselines"}


def _cache_curve() -> dict:
    from cache.benchmark.savings import _reduction

    points = []
    for rate in REPEAT_RATES:
        reduction, hits = _reduction(rate)
        points.append({"repeat_rate_pct": round(rate * 100),
                       "reduction_pct": round(reduction, 1),
                       "avg_hits": round(hits, 1)})
    return {"points": points, "command": "python -m cache.benchmark.savings"}


def _secret_detection(n: int = 1000) -> dict:
    from autopilot.policy import SecretsDetector

    detector = SecretsDetector()
    rng = random.Random(0)
    alphabet = string.ascii_letters + string.digits + "-_"
    missed = total = 0
    for prefix, length in (("sk-proj-", 156), ("sk-ant-api03-", 95)):
        for _ in range(n):
            total += 1
            key = prefix + "".join(rng.choice(alphabet) for _ in range(length))
            missed += not detector.scan(key)
    return {"keys_tested": total, "missed": missed}


def _latency() -> dict:
    rows = []
    try:
        with open(LATENCY_MD, encoding="utf-8") as f:
            for line in f:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) == 2 and "latency" not in cells[1].lower() and not set(cells[1]) <= {"-"}:
                    rows.append({"case": re.sub(r"\*\*", "", cells[0]), "latency": cells[1]})
    except OSError:
        pass
    return {"rows": rows, "source": "cache/benchmark/LATENCY.md",
            "note": "measured with the embedding model installed"}


@lru_cache(maxsize=1)
def all_results() -> dict:
    """Every measured result, computed once per gateway process."""
    return {
        "trimmer": _trimmer_table(),
        "cache": _cache_curve(),
        "secrets": _secret_detection(),
        "latency": _latency(),
    }
