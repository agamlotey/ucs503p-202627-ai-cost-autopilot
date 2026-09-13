# Prototype demo

A one-command, end-to-end demo of the whole gateway — caching + trimming —
against a mock provider, so it needs **no API key and costs nothing**.

```bash
cd code
python demo.py
```

It replays a short coding session through the real gateway and prints, per
request, whether it hit the cache, got trimmed, or was forwarded, then the token
reduction **on this scripted session**:

```
tokens the app would have sent : 19824
tokens the gateway actually sent: 7309
  saved by cache (reuse)       : 9916
  saved by trimmer (bulk code) : 2599
SAVED on this scripted session : 12515  (63% less)
```

**Read the headline honestly:** the 63% is specific to this script's mix — most
of it is one repeated 9.9k-token file hitting the cache, so the number reflects
how repetitive the session is, not a universal figure. The cache/trimmer split
is shown above so the two contributions are separate. For the real relationship,
see `cache/benchmark/SAVINGS.md` (reduction vs. repeat rate) and `LATENCY.md`.

The trimmed code stays **valid Python** (function bodies collapse to `...` at
syntactic boundaries), so the model still receives runnable source — verified in
the trimmer's tests and by parsing the demo's trimmed output.
