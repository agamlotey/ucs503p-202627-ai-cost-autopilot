"""Measure whether a cosine-similarity threshold can safely separate
'same-meaning' from 'different-meaning' code for the semantic cache.

Run:  python -m cache.benchmark.run     (needs sentence-transformers installed)
"""
from cache.cache import _default_embedder, _cosine
from cache.benchmark.pairs import SAME, DIFFERENT


def main():
    embed = _default_embedder()

    def score(pairs):
        return [(_cosine(embed(a), embed(b)), a, b) for a, b in pairs]

    same = score(SAME)
    diff = score(DIFFERENT)

    print("\n=== SAME meaning  (cache SHOULD reuse -> want HIGH) ===")
    for c, a, _ in sorted(same):
        print(f"  {c:.3f}  {a.splitlines()[0][:48]}")
    print("\n=== DIFFERENT meaning  (cache MUST NOT reuse -> want LOW) ===")
    for c, a, b in sorted(diff, reverse=True):
        print(f"  {c:.3f}  {a.splitlines()[-1][:24]:24} vs {b.splitlines()[-1][:24]}")

    same_scores = [c for c, _, _ in same]
    diff_scores = [c for c, _, _ in diff]
    lo_same, hi_diff = min(same_scores), max(diff_scores)

    print("\n=== separation ===")
    print(f"  lowest  SAME      cosine = {lo_same:.3f}")
    print(f"  highest DIFFERENT cosine = {hi_diff:.3f}")
    if lo_same > hi_diff:
        t = (lo_same + hi_diff) / 2
        print(f"  CLEAN GAP: any threshold in ({hi_diff:.3f}, {lo_same:.3f}) works. "
              f"Suggested = {t:.3f}")
    else:
        print(f"  OVERLAP of {lo_same:.3f}..{hi_diff:.3f}: NO single threshold is safe.")
        # best-effort: sweep thresholds, report the least-bad one
        best = None
        for i in range(50, 100):
            t = i / 100
            wrong_hits = sum(c >= t for c in diff_scores)   # different but reused (BAD)
            missed = sum(c < t for c in same_scores)        # same but not reused (ok-ish)
            cost = wrong_hits * 10 + missed                 # weight wrong hits 10x
            if best is None or cost < best[0]:
                best = (cost, t, wrong_hits, missed)
        _, t, wh, ms = best
        print(f"  least-bad threshold = {t:.2f} -> {wh} wrong reuse(s), {ms} missed reuse(s)")
        print("  (wrong reuse = served a different answer; the dangerous kind)")


if __name__ == "__main__":
    main()
