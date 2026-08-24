from cache.cache import SemanticCache


def _req(text):
    return {"messages": [{"role": "user", "content": text}]}


def test_lookup_miss_then_store_ok():
    c = SemanticCache()
    assert c.lookup({"messages": []}) is None
    c.store({"messages": []}, {"ok": True})  # should not raise


def test_store_then_lookup_hits():
    """The core promise: store an answer, get it back for the same request."""
    c = SemanticCache()
    req = _req("what is the capital of France?")
    answer = {"choices": [{"message": {"content": "Paris"}}]}
    assert c.lookup(req) is None          # not seen yet -> miss
    c.store(req, answer)
    assert c.lookup(req) == answer        # identical request -> hit


def test_different_requests_do_not_collide():
    """A stored answer must not leak to a different question."""
    c = SemanticCache()
    c.store(_req("capital of France?"), {"a": "Paris"})
    assert c.lookup(_req("capital of Japan?")) is None


def test_key_is_order_independent_within_message():
    """Same messages but keys written in a different order still match,
    because we hash with sort_keys=True."""
    c = SemanticCache()
    c.store({"messages": [{"role": "user", "content": "hi"}]}, {"a": 1})
    # same message, dict keys built in the opposite order
    reordered = {"messages": [{"content": "hi", "role": "user"}]}
    assert c.lookup(reordered) == {"a": 1}


def test_repeated_store_overwrites():
    """Storing the same request twice keeps the latest answer."""
    c = SemanticCache()
    req = _req("q")
    c.store(req, {"v": 1})
    c.store(req, {"v": 2})
    assert c.lookup(req) == {"v": 2}
