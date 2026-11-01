import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.main as main


@pytest.fixture
def client():
    return TestClient(main.app)


def test_health_ok(client, monkeypatch):
    monkeypatch.setattr(main, "get_engine", lambda: create_engine("sqlite://"))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_down_does_not_leak_details(client, monkeypatch):
    broken = create_engine("sqlite:///no/such/dir/demobank.db")
    monkeypatch.setattr(main, "get_engine", lambda: broken)
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


@pytest.mark.parametrize("path", ["/api/docs", "/api/openapi.json", "/redoc"])
def test_docs_disabled_outside_development(client, path):
    assert client.get(path).status_code == 404


def test_settings_repr_hides_secrets():
    settings = main.get_settings()
    assert "test-only" not in repr(settings)
