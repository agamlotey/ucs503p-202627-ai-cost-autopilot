"""Tests for the v2 semantic cache.

Most tests inject a tiny FAKE embedder (a fixed text->vector map) so we can
test the cache LOGIC — threshold, bucketing, cosine — deterministically and
without downloading PyTorch. One test at the bottom uses the REAL model and is
skipped if sentence-transformers isn't installed.
"""
import pytest

from cache.cache import SemanticCache, DEFAULT_THRESHOLD


# --- fake embedder ---------------------------------------------------------
# Hand-picked vectors so we know the cosine similarities exactly:
#   FR ~ FR2  (cosine 0.96, a "paraphrase")   |   FR vs JP (cosine 0.0)
_VECTORS = {
    "capital of France?": [1.0, 0.0, 0.0],
    "France's capital?":  [0.96, 0.28, 0.0],   # cosine with FR ~= 0.96
    "capital of Japan?":  [0.0, 1.0, 0.0],     # cosine with FR  = 0.0
}


def _fake_embed(text):
    return _VECTORS.get(text, [0.0, 0.0, 1.0])   # unknown -> a 3rd direction


def _req(text, **extra):
    return {"model": "gpt-4o", "messages": [{"role": "user", "content": text}], **extra}


def _cache(threshold=DEFAULT_THRESHOLD):
    return SemanticCache(embed_fn=_fake_embed, threshold=threshold)


# --- core behaviour --------------------------------------------------------

def test_miss_when_empty():
    assert _cache().lookup(_req("capital of France?")) is None


def test_identical_request_hits():
    c = _cache()
    c.store(_req("capital of France?"), {"a": "Paris"})
    assert c.lookup(_req("capital of France?")) == {"a": "Paris"}


def test_paraphrase_above_threshold_hits():
    """Different wording, same meaning (cosine 0.96 >= 0.90) -> reuse."""
    c = _cache()
    c.store(_req("capital of France?"), {"a": "Paris"})
    assert c.lookup(_req("France's capital?")) == {"a": "Paris"}


def test_dissimilar_question_misses():
    """A genuinely different question (cosine 0.0) must not reuse the answer."""
    c = _cache()
    c.store(_req("capital of France?"), {"a": "Paris"})
    assert c.lookup(_req("capital of Japan?")) is None


# --- v1 safety preserved (hard key) ----------------------------------------

def test_different_model_does_not_match():
    """Same text, different model -> different bucket -> no reuse."""
    c = _cache()
    c.store(_req("capital of France?", model="gpt-4o"), {"a": "Paris"})
    assert c.lookup(_req("capital of France?", model="gpt-3.5-turbo")) is None


def test_different_temperature_does_not_match():
    c = _cache()
    c.store(_req("capital of France?", temperature=0), {"a": "Paris"})
    assert c.lookup(_req("capital of France?", temperature=1.9)) is None


def test_ignored_field_still_shares_entry():
    """`user` is denylisted -> same bucket -> reuse."""
    c = _cache()
    c.store(_req("capital of France?", user="alice"), {"a": "Paris"})
    assert c.lookup(_req("capital of France?", user="bob")) == {"a": "Paris"}


# --- threshold + robustness ------------------------------------------------

def test_threshold_is_configurable():
    """Below the default a paraphrase misses; lower the bar and it hits."""
    strict = SemanticCache(embed_fn=_fake_embed, threshold=0.99)
    strict.store(_req("capital of France?"), {"a": "Paris"})
    assert strict.lookup(_req("France's capital?")) is None   # 0.96 < 0.99

    loose = SemanticCache(embed_fn=_fake_embed, threshold=0.80)
    loose.store(_req("capital of France?"), {"a": "Paris"})
    assert loose.lookup(_req("France's capital?")) == {"a": "Paris"}


def test_lookup_returns_a_copy():
    c = _cache()
    c.store(_req("capital of France?"), {"choices": [{"text": "Paris"}]})
    hit = c.lookup(_req("capital of France?"))
    hit["choices"][0]["text"] = "TAMPERED"
    assert c.lookup(_req("capital of France?"))["choices"][0]["text"] == "Paris"


def test_store_snapshots_response():
    c = _cache()
    resp = {"a": "v1"}
    c.store(_req("capital of France?"), resp)
    resp["a"] = "v2"
    assert c.lookup(_req("capital of France?")) == {"a": "v1"}


# --- real model (skipped if the library is missing) ------------------------

def test_real_embeddings_match_paraphrase_not_unrelated():
    pytest.importorskip("sentence_transformers")
    c = SemanticCache()  # real all-MiniLM embedder, default threshold
    c.store(_req("What is the capital of France?"), {"a": "Paris"})
    # a genuine paraphrase should reuse...
    assert c.lookup(_req("Which city is France's capital?")) == {"a": "Paris"}
    # ...an unrelated question should not
    assert c.lookup(_req("How do I sort a list in Python?")) is None


def test_degrades_to_noop_when_embedder_unavailable(monkeypatch):
    """If sentence-transformers isn't installed, the cache must not crash the
    gateway: every lookup misses and store is dropped (safe passthrough)."""
    import cache.cache as m

    def _boom():
        raise ImportError("sentence-transformers not installed")

    monkeypatch.setattr(m, "_default_embedder", _boom)
    c = SemanticCache()  # no embed_fn -> tries the (now failing) default
    c.store(_req("capital of France?"), {"a": "Paris"})   # dropped, no raise
    assert c.lookup(_req("capital of France?")) is None    # safe miss


def test_repeated_store_overwrites_and_does_not_duplicate():
    """Re-storing the SAME request refreshes the answer (newest wins) and keeps
    exactly one bucket entry — restored from v1, adapted to v2's buckets."""
    c = _cache()
    req = _req("capital of France?")
    c.store(req, {"a": "OLD"})
    c.store(req, {"a": "NEW"})
    assert c.lookup(req) == {"a": "NEW"}
    # only one entry in the bucket despite two stores
    bucket = next(iter(c._buckets.values()))
    assert len(bucket) == 1
