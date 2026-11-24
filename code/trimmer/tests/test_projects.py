"""The second-project claims, checked in CI.

The point of a second fixture is that one codebase cannot show whether a
saving generalises. These assert the shape of the result rather than exact
token counts, so they hold whichever tokenizer is installed.
"""
import subprocess
import sys
from pathlib import Path

import pytest

from trimmer.benchmark.projects import TASKS, measure, run
from trimmer.fixtures.loader import project_files
from trimmer.trimmer import _defined_classes

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "ledger_cli"


def test_every_task_keeps_the_context_its_fix_needs():
    """The claim that matters: nothing a correct patch must read is collapsed."""
    missing = {(r.fixture, r.task): r.missing for r in run() if r.missing}
    assert not missing


def test_every_task_still_compiles():
    assert all(r.valid for r in run())


def test_the_trimmer_saves_on_both_projects():
    results = run()
    for fixture in {r.fixture for r in results}:
        rows = [r for r in results if r.fixture == fixture]
        assert all(r.saved_pct > 20 for r in rows), fixture


def test_the_second_project_has_a_different_shape():
    """A second fixture only adds evidence if it is not the first again.

    The difference that matters to the trimmer is constructors: notes_api has
    one class with a real `__init__`, ledger_cli has several, so it exercises
    the class-instantiation edges that notes_api barely touches.
    """
    def constructors(name):
        return [cls for _rel, src in project_files(name)
                for cls, methods in _defined_classes(src).items()
                if "__init__" in methods]

    notes, ledger = constructors("notes_api"), constructors("ledger_cli")
    assert len(ledger) > len(notes)
    assert len(ledger) >= 4

    notes_files = {rel for rel, _ in project_files("notes_api")}
    ledger_files = {rel for rel, _ in project_files("ledger_cli")}
    # an incidental shared name such as errors.py is fine; near-identical
    # layouts are not
    assert len(notes_files & ledger_files) <= 2
    assert len(ledger_files) >= 8


def test_something_is_always_collapsed():
    """Guards against a regression where the trimmer keeps everything and the
    context check passes for the wrong reason."""
    for r in run():
        assert r.kept < r.total


def test_tests_are_not_sent_as_context():
    """A coding agent is sent the source, not the project's test suite;
    counting the tests would inflate every saving."""
    sent = {rel for rel, _ in project_files("ledger_cli")}
    with_tests = {rel for rel, _ in project_files("ledger_cli", include_tests=True)}
    assert with_tests - sent
    assert not any("test" in rel for rel in sent)


@pytest.mark.parametrize("task", [t for t in TASKS if t.fixture == "ledger_cli"],
                         ids=lambda t: t.task)
def test_each_ledger_task_keeps_its_focus(task):
    assert not measure(task).missing


def test_the_fixtures_own_test_suite_passes():
    """The patch-correctness check is only meaningful if the suite is green to
    begin with. Run out-of-process: the fixture uses flat imports and is not
    part of the gateway package."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(FIXTURE / "tests")],
        capture_output=True, text=True, cwd=str(FIXTURE),
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(FIXTURE)},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
