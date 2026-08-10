from cache.cache import SemanticCache


def test_lookup_miss_then_store_ok():
    c = SemanticCache()
    assert c.lookup({"messages": []}) is None
    c.store({"messages": []}, {"ok": True})  # should not raise
