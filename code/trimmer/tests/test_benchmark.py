"""The claims the prototype report makes about the trimmer, checked in CI.

These assert relationships, not exact token counts, so they hold whichever
tokenizer is available.
"""
from trimmer.benchmark.baselines import (
    _function_bodies,
    _without_header,
    run,
    strip_comments_and_docstrings,
)
from trimmer.fixtures.loader import as_messages
from trimmer.trimmer import CodeTrimmer


def _by_name(results):
    return {r.name.split(" (")[0]: r for r in results}


def test_trimmer_beats_the_simplest_safe_baseline_and_stays_valid():
    r = _by_name(run())
    assert r["trimmer"].valid
    assert r["strip comments + docstrings"].valid
    assert r["trimmer"].saved_pct > r["strip comments + docstrings"].saved_pct


def test_the_cheap_trick_breaks_the_code():
    r = _by_name(run())
    assert not r["strip indentation + blank lines"].valid


def test_collapsing_everything_saves_more_only_by_dropping_the_focus():
    r = _by_name(run())
    assert r["collapse every function body"].saved_pct > r["trimmer"].saved_pct


def test_trimmer_keeps_the_focus_and_its_cross_file_dependency():
    trimmed, _ = CodeTrimmer().trim(as_messages("fix create_note"), token_budget=0)
    full, _collapsed = _function_bodies([_without_header(m["content"]) for m in trimmed[1:]])
    assert "create_note" in full        # the focus
    assert "validate_note" in full      # its dependency, defined in another file


def test_docstring_only_body_becomes_pass_not_empty():
    src = 'def f():\n    """only a docstring"""\n'
    out = strip_comments_and_docstrings(src)
    compile(out, "<test>", "exec")      # an empty body would be a SyntaxError
    assert "pass" in out
