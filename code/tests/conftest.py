"""Shared test configuration for the integration tests.

Declares the fastapi dependency once for the whole directory, instead of
repeating `pytest.importorskip("fastapi")` inside every test.

`collect_ignore` is used rather than `pytest.importorskip` because raising
Skipped while a conftest is being imported surfaces as a collection error,
whereas this skips the affected module cleanly.
"""
import importlib.util

collect_ignore = []

if importlib.util.find_spec("fastapi") is None:
    collect_ignore.append("test_integration.py")
