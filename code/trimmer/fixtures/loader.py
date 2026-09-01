"""Load the fixture projects as request payloads.

`sample_project` is a 2-file toy, useful for unit tests where the expected
output has to be written out by hand.

`notes_api` is a realistic small service (10 files, 45 functions). Measurement
needs it: on a toy project almost every function is reachable from any other, so
selective retention cannot show a benefit and the numbers say more about the
fixture than about the trimmer.
"""
from __future__ import annotations

import os

HERE = os.path.dirname(os.path.abspath(__file__))


def project_files(name: str = "notes_api") -> list[tuple[str, str]]:
    """Every .py file in a fixture project as (relative path, source)."""
    root = os.path.join(HERE, name)
    found: list[tuple[str, str]] = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            with open(path) as fh:
                found.append((os.path.relpath(path, root), fh.read()))
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
