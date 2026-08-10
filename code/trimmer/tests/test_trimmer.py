from trimmer.trimmer import CodeTrimmer


def test_trim_returns_messages_and_stats():
    t = CodeTrimmer()
    msgs = [{"role": "user", "content": "hello"}]
    out, stats = t.trim(msgs, token_budget=1000, ctx={})
    assert isinstance(out, list)
    assert "tokens_saved" in stats
