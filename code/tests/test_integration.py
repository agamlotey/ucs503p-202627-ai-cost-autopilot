import pytest


def test_app_imports():
    pytest.importorskip("fastapi")
    from gateway.app import app
    assert app is not None


def test_cache_uses_original_request_not_trimmed(monkeypatch):
    """Regression: cache lookup AND store must key on the original request.

    The trimmer mutates body["messages"]; if store() ran on the trimmed body,
    the response would be cached under a key no future request could match, so
    the cache would never hit. This test locks in the fix.
    """
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from gateway import app as gw

    seen = {}

    class SpyCache:
        def lookup(self, request):
            seen["lookup"] = request
            return None

        def store(self, request, response):
            seen["store"] = request

    class MutatingTrimmer:
        def trim(self, messages, token_budget, ctx=None):
            return [{"role": "user", "content": "TRIMMED"}], {}

    class YesAutopilot:
        def decide(self, request, signals):
            return {"use_cache": True, "trim": True}

    async def fake_forward(body):
        return {"ok": True, "sent": body["messages"][0]["content"]}

    monkeypatch.setattr(gw, "cache", SpyCache())
    monkeypatch.setattr(gw, "trimmer", MutatingTrimmer())
    monkeypatch.setattr(gw, "autopilot", YesAutopilot())
    monkeypatch.setattr(gw.provider, "forward", fake_forward)

    resp = TestClient(gw.app).post(
        "/v1/chat/completions",
        json={"model": "m", "messages": [{"role": "user", "content": "ORIGINAL"}]},
    )
    assert resp.status_code == 200
    # trimming still happens -> provider receives the trimmed body
    assert resp.json()["sent"] == "TRIMMED"
    # but the cache used the ORIGINAL request for both lookup and store
    assert seen["lookup"]["messages"][0]["content"] == "ORIGINAL"
    assert seen["store"]["messages"][0]["content"] == "ORIGINAL"
    assert seen["lookup"] == seen["store"]
