import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from app import create_app  # noqa: E402


@pytest.fixture()
def app(tmp_path):
    """Fresh app + empty temp database per test. No network providers, no API key."""
    return create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.db"),
        "SECRET_KEY": "test",
        "ENABLE_WIKIPEDIA": False,
        "BRAVE_API_KEY": None,
        "ANTHROPIC_API_KEY": None,
    })


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def logged_in(client):
    r = client.post("/api/register", json={"username": "amrinder", "password": "secret123"})
    assert r.status_code == 201
    return client
