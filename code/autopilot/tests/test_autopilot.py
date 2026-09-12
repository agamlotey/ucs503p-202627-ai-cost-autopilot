from autopilot.policy import Autopilot


def test_handle_passes_through_and_caches_response():
    calls = []

    def fake_llm(prompt):
        calls.append(prompt)
        return "answer"

    pilot = Autopilot()
    result = pilot.handle("What is the capital of India?", fake_llm)

    assert result["route"] == "passthrough"
    assert result["answer"] == "answer"
    assert result["cached"] is True
    assert calls == ["What is the capital of India?"]


def test_handle_returns_cached_response_without_calling_llm():
    calls = []

    def fake_llm(prompt):
        calls.append(prompt)
        return "answer"

    pilot = Autopilot()
    pilot.handle("What is the capital of India?", fake_llm)
    result = pilot.handle("What is the capital of India?", fake_llm)

    assert result["route"] == "cache_hit"
    assert result["cost_estimate"] == 0
    assert len(calls) == 1


def test_handle_trims_large_messages():
    received = []

    def fake_llm(prompt):
        received.append(prompt)
        return "trimmed answer"

    pilot = Autopilot(size_threshold_chars=20)
    result = pilot.handle("repeated line\n" * 10, fake_llm)

    assert result["route"] == "trimmed"
    assert len(received[0]) < len("repeated line\n" * 10)


def test_handle_does_not_cache_secrets():
    calls = []

    def fake_llm(prompt):
        calls.append(prompt)
        return "safe answer"

    pilot = Autopilot()
    result = pilot.handle("my api_key: sk-abc123XYZsecretvalue000000", fake_llm)

    assert result["route"] == "sensitive_no_cache"
    assert result["cached"] is False
    assert len(pilot.cache.entries) == 0
    assert len(calls) == 1
