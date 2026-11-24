import os

from trimmer.trimmer import (
    CodeTrimmer,
    collapse_python,
    build_call_graph,
    expand_focus,
    merge_call_graphs,
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


# ---- class instantiation edges ----

CLASS_SAMPLE = '''
class ConfigError(Exception):
    def __init__(self, message, path=None):
        """Raised when a config file is invalid."""
        self.message = _format(message)
        self.path = path
        super().__init__(self.message)


class UnrelatedError(Exception):
    def __init__(self, code):
        """Nothing in the task raises this."""
        self.code = code
        self.tag = "unrelated"


def _format(message):
    return message.strip().capitalize()


def load_config(path):
    """Read and validate a config file."""
    if not path:
        raise ConfigError("missing path", path)
    return {"path": path}


def untouched(x):
    return x * 99
'''


def _trim_class_sample(task="fix load_config so the error message is clearer"):
    out, _ = CodeTrimmer().trim(
        [{"role": "user", "content": task},
         {"role": "user", "content": CLASS_SAMPLE}], token_budget=0)
    return out[-1]["content"]


def test_instantiating_a_class_is_an_edge_to_its_constructor():
    g = build_call_graph(CLASS_SAMPLE)
    assert "ConfigError" in g["load_config"]          # the class is a known symbol
    assert g["ConfigError"] == {"ConfigError.__init__"}


def test_constructor_body_is_kept_when_the_task_raises_it():
    """Regression: `raise ConfigError(...)` created no edge, so the constructor
    was collapsed and the agent could not see what it did with the message."""
    code = _trim_class_sample()
    assert "self.message = _format(message)" in code


def test_constructors_own_dependency_is_kept():
    """The constructor calls _format, which the fix also needs."""
    assert "return message.strip().capitalize()" in _trim_class_sample()


def test_other_constructors_still_collapse():
    """Only the instantiated class's __init__ is kept, not every __init__."""
    code = _trim_class_sample()
    assert "self.code = code" not in code
    assert 'self.tag = "unrelated"' not in code
    assert "return x * 99" not in code                # plain functions too


def test_class_without_a_constructor_is_harmless():
    src = 'class Marker:\n    """no constructor"""\n\n\ndef go():\n    return Marker()\n'
    g = build_call_graph(src)
    assert "Marker" in g["go"]
    assert "Marker.__init__" not in g.get("Marker", set())


CLASS_FILE_A = '''
def save_note(text):
    """entry point"""
    if not text:
        raise EmptyNote("note is empty")
    return text
'''

CLASS_FILE_B = '''
class EmptyNote(Exception):
    def __init__(self, reason):
        """Raised when a note has no body."""
        self.reason = reason
        self.hint = "type something first"
'''


HIERARCHY = '''
class LedgerError(Exception):
    def __init__(self, message, row=None):
        self.message = message
        self.row = row
        super().__init__(self._describe())

    def _describe(self):
        return f"{self.message} (row {self.row})"


class ParseError(LedgerError):
    def __init__(self, field, value, row=None):
        self.field = field
        super().__init__(f"could not read {field}: {value!r}", row)


class Unrelated(LedgerError):
    def __init__(self, code):
        self.code = code
        super().__init__("unrelated")


def parse_row(line):
    raise ParseError("date", line, 2)
'''


def test_super_resolves_to_the_declared_base():
    g = build_call_graph(HIERARCHY)
    assert "LedgerError.__init__" in g["ParseError.__init__"]
    # still no false self-edge: the base's own super() goes to Exception
    assert "__init__" not in g["__init__"]


def test_base_class_constructor_is_kept():
    """A subclass constructor that defers to its base leaves the real work in
    the base, so keeping only the subclass shows the agent nothing."""
    out, _ = CodeTrimmer().trim(
        [{"role": "user", "content": "fix parse_row so the message names the column"},
         {"role": "user", "content": HIERARCHY}], token_budget=0)
    code = out[-1]["content"]
    assert "self.field = field" in code              # the subclass constructor
    assert "self.message = message" in code          # the base constructor
    assert "(row {self.row})" in code                # and what it calls


def test_an_unrelated_subclass_constructor_still_collapses():
    out, _ = CodeTrimmer().trim(
        [{"role": "user", "content": "fix parse_row so the message names the column"},
         {"role": "user", "content": HIERARCHY}], token_budget=0)
    assert "self.code = code" not in out[-1]["content"]


def test_constructor_in_another_file_is_kept():
    out, _ = CodeTrimmer().trim(
        [{"role": "user", "content": "fix save_note"},
         {"role": "user", "content": CLASS_FILE_A},
         {"role": "user", "content": CLASS_FILE_B}], token_budget=0)
    assert 'self.hint = "type something first"' in out[-1]["content"]


# ---- cross-file dependencies ----

FILE_A = '''
def run(path):
    """entry point"""
    cfg = load(path)
    return check(cfg)
'''

FILE_B = '''
def load(p):
    """read the file"""
    return open(p).read()


def check(cfg):
    """validate it"""
    return "name" in cfg


def unrelated(z):
    """nothing calls this"""
    return z * 99
'''


def test_merge_call_graphs_links_across_sources():
    graph, defined = merge_call_graphs([FILE_A, FILE_B])
    assert defined == {"run", "load", "check", "unrelated"}
    # the edge run -> load lives across a file boundary
    assert graph["run"] == {"load", "check"}


def test_dependency_in_another_message_is_kept():
    """Regression: the focus function's dependencies may live in another file.

    Building a call graph per message missed those edges, so the dependency was
    collapsed to a signature -- dropping context the task needs.
    """
    msgs = [
        {"role": "user", "content": "fix the run function"},
        {"role": "user", "content": FILE_A},
        {"role": "user", "content": FILE_B},
    ]
    out, stats = CodeTrimmer().trim(msgs, token_budget=5)
    a, b = out[1]["content"], out[2]["content"]

    assert "cfg = load(path)" in a          # focus kept
    assert "return open(p).read()" in b     # dependency, other file
    assert 'return "name" in cfg' in b      # dependency, other file
    assert "z * 99" not in b                # unrelated -> collapsed
    assert "def unrelated(z):" in b         # ...but its signature survives
    assert stats["tokens_saved"] > 0


def test_no_focus_still_collapses_everything():
    out, _ = CodeTrimmer().trim(
        [{"role": "user", "content": FILE_A}, {"role": "user", "content": FILE_B}],
        token_budget=5,
    )
    assert "cfg = load(path)" not in out[0]["content"]
    assert "return open(p).read()" not in out[1]["content"]
    assert "def run(path):" in out[0]["content"]   # signatures remain


# ---- realistic fixture ----

def test_notes_api_fixture_is_valid_python():
    """Every fixture file must compile, or measurements made on it are junk."""
    from trimmer.fixtures.loader import project_files

    files = project_files("notes_api")
    assert len(files) >= 10
    for rel, source in files:
        compile(source, rel, "exec")


def test_notes_api_fixture_is_big_enough_to_measure():
    """A toy project cannot demonstrate selective retention."""
    from trimmer.fixtures.loader import project_files
    from trimmer.trimmer import _defined_functions, count_tokens

    files = project_files("notes_api")
    functions = set()
    tokens = 0
    for _rel, source in files:
        functions |= _defined_functions(source)
        tokens += count_tokens(source)
    assert len(functions) >= 40
    assert tokens >= 2500


def test_as_messages_puts_each_file_in_its_own_message():
    from trimmer.fixtures.loader import as_messages, project_files

    msgs = as_messages("fix create_note")
    assert msgs[0]["content"] == "fix create_note"
    assert len(msgs) == len(project_files("notes_api")) + 1