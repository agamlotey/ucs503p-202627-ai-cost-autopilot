import pytest


def test_app_imports():
    pytest.importorskip("fastapi")
    from gateway.app import app
    assert app is not None


def test_pipeline_runs_offline_with_mock_provider(monkeypatch):
    """The full gateway pipeline should work with no API key and no network."""
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from gateway import config
    from gateway.app import app

    # force mock mode (no key, no outbound call)
    monkeypatch.setattr(config, "MOCK_PROVIDER", True)

    client = TestClient(app)
    resp = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "def f():\n    return 1"}],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["choices"][0]["message"]["role"] == "assistant"


def test_health_endpoint():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from gateway.app import app

    assert TestClient(app).get("/health").json() == {"status": "ok"}
