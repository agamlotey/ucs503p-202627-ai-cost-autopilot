from fastapi.testclient import TestClient

from gateway import config
from gateway.app import app
from gateway.provider import mock_response

# The fastapi guard lives in conftest.py so it is declared once for the
# whole tests/ directory.


def test_app_imports():
    assert app is not None


def test_health_endpoint():
    assert TestClient(app).get("/health").json() == {"status": "ok"}


def test_pipeline_runs_offline_with_mock_provider(monkeypatch):
    """The full gateway pipeline works with no network access.

    PROVIDER_API_KEY is set to a fake value so the mock is chosen because of the
    MOCK_PROVIDER flag, not merely because the key happens to be empty in the
    test environment.
    """
    monkeypatch.setattr(config, "PROVIDER_API_KEY", "sk-fake")
    monkeypatch.setattr(config, "MOCK_PROVIDER", True)

    resp = TestClient(app).post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "def f():\n    return 1"}],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["choices"][0]["message"]["role"] == "assistant"
    # Prove the mock actually produced this response.
    assert "[MOCK REPLY]" in body["choices"][0]["message"]["content"]
    assert body["usage"]["total_tokens"] > 0
    assert body["created"] > 0


def test_mock_ids_are_unique():
    """A static id would collide across calls, which matters for the cache."""
    req = {"messages": [{"role": "user", "content": "hi"}]}
    assert mock_response(req)["id"] != mock_response(req)["id"]


def test_mock_uses_last_user_message_not_last_message():
    """An assistant turn at the end must not be mistaken for the user's text."""
    body = mock_response(
        {
            "messages": [
                {"role": "user", "content": "12345"},
                {"role": "assistant", "content": "a much longer assistant reply"},
            ]
        }
    )
    assert "received 5 characters" in body["choices"][0]["message"]["content"]


def test_mock_handles_multipart_content():
    """content may be a list of parts; the text parts should be joined."""
    body = mock_response(
        {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "abc"},
                        {"type": "image_url", "image_url": {"url": "http://x/y.png"}},
                    ],
                }
            ]
        }
    )
    assert "received 3 characters" in body["choices"][0]["message"]["content"]
