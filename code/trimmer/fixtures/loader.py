"""Load the fixture projects as request payloads.

`sample_project` is a 2-file toy, useful for unit tests where the expected
output has to be written out by hand.

`notes_api` is a realistic small service (10 files, 45 functions). Measurement
needs it: on a toy project almost every function is reachable from any other, so
selective retention cannot show a benefit and the numbers say more about the
fixture than about the trimmer.

`ledger_cli` is a second realistic project, deliberately unlike the first: a
command line tool rather than a request handler, with a four-deep exception
hierarchy and a stateful class, so five classes define a constructor where
notes_api has one. One fixture cannot show whether a saving generalises, and
code shape is exactly what the trimmer keys on. It ships its own passing test
suite, so a patch written against the trimmed context can be judged by the
project's own tests rather than by eye.
"""
from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))


def _is_test(rel: str) -> bool:
    parts = rel.split(os.sep)
    return "tests" in parts[:-1] or parts[-1].startswith("test_")


def project_files(name: str = "notes_api", include_tests: bool = False) -> list[tuple[str, str]]:
    """Every .py file in a fixture project as (relative path, source).

    A project's own tests are left out by default: a coding agent is sent the
    source it has to change, and counting the test suite in the baseline would
    inflate every saving. Pass `include_tests=True` to get them, which is how
    a patch is checked against the project's own definition of correct.
    """
    root = os.path.join(HERE, name)
    found: list[tuple[str, str]] = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root)
            if not include_tests and _is_test(rel):
                continue
            with open(path) as fh:
                found.append((rel, fh.read()))
    return sorted(found)


def as_messages(task: str, name: str = "notes_api") -> list[dict]:
    """Build a request the way a coding agent would: the task, then the files.

    Each file arrives as its own message, which is what makes cross-file
    dependency resolution matter.
    """
    messages = [{"role": "user", "content": task}]
    for rel, source in project_files(name):
        messages.append({"role": "user", "content": f"# file: {rel}\n{source}"})
    return messages
