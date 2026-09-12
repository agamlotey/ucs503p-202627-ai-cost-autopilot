from autopilot.policy import Autopilot


def test_decide_returns_plan_shape():
    a = Autopilot()
    plan = a.decide({}, {"has_code": True, "num_tokens_est": 2000})
    assert "use_cache" in plan
    assert "trim" in plan


def test_trims_when_code_heavy_and_large():
    a = Autopilot()
    plan = a.decide({}, {"has_code": True, "num_tokens_est": 5000})
    assert plan["trim"] is True
    assert plan["use_cache"] is True


def test_does_not_trim_small_code_request():
    # Below the token threshold: trimming overhead isn't worth it.
    a = Autopilot()
    plan = a.decide({}, {"has_code": True, "num_tokens_est": 50})
    assert plan["trim"] is False
    assert plan["use_cache"] is True


def test_does_not_trim_non_code_request():
    a = Autopilot()
    plan = a.decide({}, {"has_code": False, "num_tokens_est": 5000})
    assert plan["trim"] is False
    assert plan["use_cache"] is True


def test_secrets_in_signals_block_cache_and_trim():
    a = Autopilot()
    request = {"messages": [{"role": "user", "content": "hello"}]}
    plan = a.decide(request, {"has_code": True, "num_tokens_est": 5000, "has_secrets": True})
    assert plan["use_cache"] is False
    assert plan["trim"] is False


def test_own_secrets_scan_used_when_signal_missing():
    # Gateway hasn't computed has_secrets yet -> autopilot must catch it itself.
    a = Autopilot()
    request = {
        "messages": [
            {"role": "user", "content": "my api_key: sk-abc123XYZsecretvalue000000"}
        ]
    }
    plan = a.decide(request, {"has_code": False, "num_tokens_est": 10})
    assert plan["use_cache"] is False
    assert plan["trim"] is False


def test_detects_openai_project_key_format():
    # sk-proj-... is the current OpenAI key format, not just legacy sk-...
    a = Autopilot()
    request = {
        "messages": [
            {"role": "user", "content": "key: sk-proj-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"}
        ]
    }
    plan = a.decide(request, {"has_code": False, "num_tokens_est": 10})
    assert plan["use_cache"] is False
    assert plan["trim"] is False


def test_detects_anthropic_key_format():
    a = Autopilot()
    request = {
        "messages": [
            {"role": "user", "content": "ANTHROPIC_API_KEY=sk-ant-api03-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-AbCdEfGh"}
        ]
    }
    plan = a.decide(request, {"has_code": False, "num_tokens_est": 10})
    assert plan["use_cache"] is False
    assert plan["trim"] is False


def test_stats_tracks_decisions():
    a = Autopilot()
    a.decide({}, {"has_code": True, "num_tokens_est": 5000})
    a.decide({}, {"has_code": False, "num_tokens_est": 5000})
    stats = a.stats()
    assert stats.get("trimmed", 0) == 1
    assert stats.get("cache_or_passthrough", 0) == 1
