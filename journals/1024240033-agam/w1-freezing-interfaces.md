# Week 1 : Freezing shared interfaces so three people can build in parallel

## Context
Our project splits into three parts with one owner each: the trimmer (me), the
semantic cache (Devansh), and the autopilot (Furmaan). All three plug into one
FastAPI gateway. The risk in a 3-person build is that everyone waits on everyone
else, and small changes to one module keep breaking the others.

## Problem
If we start writing logic before agreeing on how the modules talk to each other,
every integration becomes a merge conflict, and no one can test their part alone.

## Key Observation
We do not need each other's *code* to start — we only need each other's
*interface* (what goes in, what comes out). If the interfaces are fixed first,
each person can build against a mock of the others.

## Solution
We defined the three contracts as Python `Protocol` types in
`code/gateway/interfaces.py` and agreed not to change them without all three
approving:

```python
class Trimmer(Protocol):
    def trim(self, messages, token_budget, ctx) -> tuple[list, dict]: ...

class Cache(Protocol):
    def lookup(self, request) -> dict | None: ...
    def store(self, request, response) -> None: ...

class Autopilot(Protocol):
    def decide(self, request, signals) -> dict: ...
```

Each folder (`trimmer/`, `cache/`, `autopilot/`) now owns a separate directory,
so we rarely touch the same file. With the contracts frozen, I can develop and
unit-test the trimmer using fake message lists, before the cache or autopilot are
even finished.

## Takeaway
Agree on interfaces before logic. It converted a blocking dependency into three
independent workstreams.
