import pytest


def test_app_imports():
    pytest.importorskip("fastapi")
    from gateway.app import app
    assert app is not None
