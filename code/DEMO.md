# Prototype demo

A one-command, end-to-end demo of the whole gateway — caching + trimming —
running against a mock provider, so it needs **no API key and costs nothing**.

```bash
cd code
python demo.py
```

It replays a short coding session through the real gateway and prints, per
request, whether it hit the cache, got trimmed, or was forwarded, then the total
token reduction. Example run: **63% fewer tokens sent**, every request still
answered — from reusing repeats and trimming a whole-repo-sized request, with no
change to the coding tool.

For the measured breakdowns behind this, see `cache/benchmark/` (savings vs.
repeat rate, latency overhead, and the code-threshold study).
