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


def test_different_models_do_not_share_an_answer():
    """Same question, different model -> different cache entry.

    Serving one model's answer for another is a wrong-answer bug: the whole
    point of the cache is 'reuse when it's genuinely the same request'.
    """
    c = SemanticCache()
    q = [{"role": "user", "content": "2+2?"}]
    c.store({"model": "gpt-4o", "messages": q}, {"a": "from gpt-4o"})
    assert c.lookup({"model": "gpt-3.5-turbo", "messages": q}) is None
    assert c.lookup({"model": "gpt-4o", "messages": q}) == {"a": "from gpt-4o"}


def test_lookup_returns_a_copy_not_the_stored_object():
    """Mutating a looked-up response must not corrupt the cache."""
    c = SemanticCache()
    req = _req("q")
    c.store(req, {"choices": [{"text": "original"}]})
    hit = c.lookup(req)
    hit["choices"][0]["text"] = "TAMPERED"     # caller mutates their copy
    assert c.lookup(req)["choices"][0]["text"] == "original"  # cache intact


def test_store_snapshots_the_response():
    """Mutating the caller's object AFTER store() must not change the cache."""
    c = SemanticCache()
    req = _req("q")
    resp = {"answer": "v1"}
    c.store(req, resp)
    resp["answer"] = "v2"                       # caller changes it later
    assert c.lookup(req) == {"answer": "v1"}    # cache kept the snapshot


def test_different_temperature_does_not_share_an_answer():
    """temperature changes the answer, so it must be part of the key."""
    c = SemanticCache()
    q = [{"role": "user", "content": "write a poem"}]
    c.store({"model": "gpt-4o", "messages": q, "temperature": 0}, {"a": "deterministic"})
    assert c.lookup({"model": "gpt-4o", "messages": q, "temperature": 1.9}) is None


def test_stream_flag_is_part_of_key():
    """A streaming client must not be served a stored non-streaming dict."""
    c = SemanticCache()
    q = [{"role": "user", "content": "hi"}]
    c.store({"model": "gpt-4o", "messages": q}, {"non": "stream dict"})
    assert c.lookup({"model": "gpt-4o", "messages": q, "stream": True}) is None


def test_unknown_param_misses_rather_than_wrong_hit():
    """Design guarantee: a param we've never seen fails toward a MISS (safe),
    never a wrong reuse. This is why the key is a denylist, not an allowlist."""
    c = SemanticCache()
    q = [{"role": "user", "content": "hi"}]
    c.store({"model": "gpt-4o", "messages": q}, {"a": 1})
    # some future OpenAI field we don't special-case
    assert c.lookup({"model": "gpt-4o", "messages": q, "some_new_2027_param": 5}) is None


def test_ignored_field_does_not_change_key():
    """Fields in the denylist (e.g. `user`) don't affect the answer, so
    requests differing only there SHARE a cache entry."""
    c = SemanticCache()
    q = [{"role": "user", "content": "hi"}]
    c.store({"model": "gpt-4o", "messages": q, "user": "alice"}, {"a": 1})
    assert c.lookup({"model": "gpt-4o", "messages": q, "user": "bob"}) == {"a": 1}
