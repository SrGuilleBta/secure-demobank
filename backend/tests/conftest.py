import os

# Valores de prueba (no son secretos reales). Deben existir antes de importar app.main.
os.environ.setdefault("DB_APP_PASSWORD", "test-only")
os.environ.setdefault("APP_SECRET_KEY", "test-only")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

import app.main as main
from app import db

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

# Las pruebas de integración usan un PostgreSQL real con db/schema.sql ya aplicado:
# `python scripts/dev.py test` lo prepara y las corre (en el CI es un servicio de PostgreSQL).
needs_database = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL no está definida")

PASSWORD = "una-clave-larga-123"


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def api(engine, monkeypatch):
    """Cliente de la API contra una base de datos vacía en cada prueba."""
    monkeypatch.setattr(db, "get_engine", lambda: engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users, accounts, sessions, transfers, audit_log RESTART IDENTITY CASCADE"))
    # raise_server_exceptions=False: un error interno se ve como lo vería un cliente real (500 genérico).
    return TestClient(main.app, raise_server_exceptions=False)


def register(client, username, password=PASSWORD):
    return client.post("/api/auth/register", json={"username": username, "password": password})


def login(client, username, password=PASSWORD):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def make_user(app_client, username):
    """Crea un usuario y devuelve un cliente con la sesión iniciada y su cabecera CSRF lista."""
    assert register(app_client, username).status_code == 201
    client = TestClient(main.app, raise_server_exceptions=False)
    response = login(client, username)
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return client


def transfer(client, to_username, amount_cents, key=None, **extra):
    import uuid

    body = {"to_username": to_username, "amount_cents": amount_cents,
            "idempotency_key": key or str(uuid.uuid4()), **extra}
    return client.post("/api/transfers", json=body)
