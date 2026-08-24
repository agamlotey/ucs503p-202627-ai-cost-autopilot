import os

from trimmer.trimmer import (
    CodeTrimmer,
    collapse_python,
    build_call_graph,
    expand_focus,
)

SAMPLE = '''
def foo(x):
    """entry"""
    return bar(x) + 1


def bar(y):
    """helper"""
    return y * 2


def baz(z):
    """unrelated"""
    return z - 3
'''

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


# ---- phase 2: focus + call graph ----

def test_build_call_graph_edges():
    g = build_call_graph(SAMPLE)
    assert "bar" in g["foo"]      # foo calls bar
    assert g["baz"] == set()      # baz calls nothing known


def test_expand_focus_follows_calls():
    g = build_call_graph(SAMPLE)
    assert expand_focus({"foo"}, g, hops=2) == {"foo", "bar"}


def test_trim_keeps_focus_and_its_callees():
    msgs = [
        {"role": "user", "content": "please fix foo"},   # plain text -> focus = foo
        {"role": "user", "content": SAMPLE},
    ]
    out, stats = CodeTrimmer().trim(msgs, token_budget=5)
    code = out[1]["content"]
    assert "return bar(x) + 1" in code   # foo kept (focus)
    assert "return y * 2" in code        # bar kept (called by foo)
    assert "z - 3" not in code           # baz collapsed
    assert "def baz(z):" in code         # baz signature still there
    assert stats["tokens_saved"] > 0


def test_trim_no_focus_collapses_all():
    out, _ = CodeTrimmer().trim([{"role": "user", "content": SAMPLE}], token_budget=5)
    code = out[0]["content"]
    assert "return bar(x) + 1" not in code
    assert "z - 3" not in code
    assert "def foo(x):" in code          # signatures remain


def test_ctx_focus_override():
    out, _ = CodeTrimmer().trim(
        [{"role": "user", "content": SAMPLE}], token_budget=5, ctx={"focus": ["baz"]}
    )
    code = out[0]["content"]
    assert "z - 3" in code                # baz kept via explicit focus
    assert "return y * 2" not in code     # bar collapsed


# ---- call-graph edge resolution ----

SUPER_SAMPLE = '''
class ConfigError(Exception):
    def __init__(self, message):
        """Raised when a config file is invalid."""
        self.message = message
        super().__init__(message)


def helper(x):
    return x


def caller(x):
    return helper(x)


def recurse(n):
    return recurse(n - 1)
'''


def test_super_call_does_not_create_false_edge():
    """super().__init__() dispatches to the base class, not to our __init__."""
    g = build_call_graph(SUPER_SAMPLE)
    assert "__init__" not in g["__init__"]


def test_no_self_edges():
    """Recursion adds nothing to focus expansion."""
    g = build_call_graph(SUPER_SAMPLE)
    assert "recurse" not in g["recurse"]


def test_real_edges_still_resolved():
    g = build_call_graph(SUPER_SAMPLE)
    assert g["caller"] == {"helper"}
