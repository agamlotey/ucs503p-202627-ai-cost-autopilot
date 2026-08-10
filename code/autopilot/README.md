# Autopilot (Furmaan)

Decides the cheapest safe path per request. See docstring in `policy.py`.

## First tasks
- [ ] Implement the decision tree: safety -> cache -> trim -> passthrough.
- [ ] Use signals (token count, has_code) to decide when trimming is worth it.
- [ ] Add a conservative rule so a "close-enough" cache hit is NOT reused.
- [ ] Log tokens saved / cache hit-rate for measurement.

## Contract (do not change alone)
`decide(request, signals) -> plan`  (e.g. `{"use_cache": bool, "trim": bool}`)
