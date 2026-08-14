import os

from trimmer.trimmer import CodeTrimmer, collapse_python

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures", "sample_project")


def _load(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return f.read()


def test_trim_returns_messages_and_stats():
    t = CodeTrimmer()
    msgs = [{"role": "user", "content": "hello"}]
    out, stats = t.trim(msgs, token_budget=1000, ctx={})
    assert isinstance(out, list)
    assert "tokens_saved" in stats


def test_collapse_keeps_signatures_and_drops_bodies():
    src = _load("utils.py")
    out = collapse_python(src)
    # signatures survive
    assert "def parse_config(path):" in out
    assert "def validate(cfg):" in out
    # docstrings survive
    assert "Load and parse a JSON config file." in out
    # bodies are gone
    assert "json.loads" not in out
    assert "required = " not in out
    # collapsed placeholder present
    assert "..." in out
    # result is still valid Python
    compile(out, "collapsed.py", "exec")


def test_trim_reduces_tokens_when_over_budget():
    src = _load("utils.py") + "\n" + _load("main.py")
    msgs = [{"role": "user", "content": src}]
    out, stats = CodeTrimmer().trim(msgs, token_budget=10, ctx={})
    assert stats["trimmed"] is True
    assert stats["tokens_saved"] > 0
    assert stats["tokens_after"] < stats["tokens_before"]


def test_under_budget_is_noop():
    msgs = [{"role": "user", "content": _load("utils.py")}]
    out, stats = CodeTrimmer().trim(msgs, token_budget=100000, ctx={})
    assert stats["trimmed"] is False
    assert stats["tokens_saved"] == 0


def test_keep_list_preserves_named_function():
    src = _load("utils.py")
    out = collapse_python(src, keep={"parse_config"})
    # kept function retains its body
    assert "json.loads" in out
    # others still collapsed
    assert "required = " not in out
