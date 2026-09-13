"""The dashboard's endpoints: metering, measured results, and the example request."""
import pytest
from fastapi.testclient import TestClient

import gateway.app as gw
from cache.cache import SemanticCache
from gateway import config
from gateway.metrics import metrics


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "MOCK_PROVIDER", True)
    # a fresh cache per test, with a stub embedder so no model is ever loaded
    monkeypatch.setattr(gw, "cache", SemanticCache(embed_fn=lambda text: [1.0, 0.0]))
    metrics.reset()
    return TestClient(gw.app)


def _send(client, messages):
    r = client.post("/v1/chat/completions", json={"model": "gpt-4o-mini", "messages": messages})
    assert r.status_code == 200
    return client.get("/stats").json()["recent"][0]


def test_empty_or_blank_message_does_not_crash(client):
    for content in ("", "   \n  "):
        last = _send(client, [{"role": "user", "content": content}])
        assert last["preview"] == ""


def test_realistic_coding_request_is_trimmed_and_recorded(client):
    messages = client.get("/demo/example-request").json()["messages"]
    last = _send(client, messages)
    assert last["outcome"] == "trim"
    assert 0 < last["sent"] < last["baseline"]
    assert last["saved"] == last["baseline"] - last["sent"]
    assert last["preview"] == "fix create_note"   # the task, not the last file


def test_repeating_it_is_a_cache_hit_that_sends_nothing(client):
    messages = client.get("/demo/example-request").json()["messages"]
    _send(client, messages)
    last = _send(client, messages)
    assert last["outcome"] == "cache"
    assert last["sent"] == 0
    stats = client.get("/stats").json()
    assert stats["requests"] == 2 and stats["cache_hits"] == 1 and stats["trimmed"] == 1


def test_plain_prompt_is_forwarded_untouched(client):
    last = _send(client, [{"role": "user", "content": "What is a good commit message style?"}])
    assert last["outcome"] == "forward"
    assert last["saved"] == 0


def test_stats_reset(client):
    _send(client, [{"role": "user", "content": "hello"}])
    client.post("/stats/reset")
    assert client.get("/stats").json()["requests"] == 0


def test_example_request_has_the_task_and_every_file(client):
    body = client.get("/demo/example-request").json()
    assert body["messages"][0]["content"] == body["task"]
    assert len(body["messages"]) == body["files"] + 1 == 11


def test_benchmarks_report_the_measured_results(client):
    b = client.get("/benchmarks").json()
    rows = {r["variant"].split(" (")[0]: r for r in b["trimmer"]["rows"]}
    assert rows["trimmer"]["valid"]
    assert not rows["strip indentation + blank lines"]["valid"]
    assert rows["trimmer"]["saved_pct"] > rows["strip comments + docstrings"]["saved_pct"]
    curve = {p["repeat_rate_pct"]: p["reduction_pct"] for p in b["cache"]["points"]}
    assert curve[0] == 0.0 and curve[80] > curve[20]
    assert b["secrets"]["missed"] == 0
