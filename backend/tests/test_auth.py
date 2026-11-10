"""Registro, login, sesiones y bloqueo de cuenta (amenazas T-01, T-02, T-03, T-07, T-09, T-17)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import app.main as main
from conftest import PASSWORD, login, make_user, needs_database, register, transfer

pytestmark = needs_database


def test_register_ok_and_password_is_argon2id(api, engine):
    response = register(api, "alice")
    assert response.status_code == 201
    assert response.json()["role"] == "cliente"
    assert "password" not in response.text
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT password_hash FROM users WHERE username = 'alice'")).scalar_one()
    assert stored.startswith("$argon2id$")
    assert PASSWORD not in stored


def test_register_duplicate_is_rejected(api):
    assert register(api, "alice").status_code == 201
    assert register(api, "alice").status_code == 409


def test_register_username_is_case_insensitive(api):
    assert register(api, "Alice").status_code == 201
    assert register(api, "ALICE").status_code == 409


@pytest.mark.parametrize("password", ["corta", "a" * 11, "x" * 129])
def test_register_rejects_bad_password_without_echoing_it(api, password):
    response = register(api, "alice", password)
    assert response.status_code == 422
    assert password not in response.text


@pytest.mark.parametrize("username", ["ab", "con espacio", "<script>", "a" * 33, "nombre;drop"])
def test_register_rejects_bad_username(api, username):
    assert register(api, username).status_code == 422


@pytest.mark.parametrize("extra", [{"role": "administrador"}, {"balance_cents": 10**9}, {"id": "x"}])
def test_register_rejects_extra_fields_mass_assignment(api, extra):
    response = api.post("/api/auth/register", json={"username": "mallory", "password": PASSWORD, **extra})
    assert response.status_code == 422


def test_new_accounts_start_with_initial_balance_and_client_role(api):
    client = make_user(api, "alice")
    assert client.get("/api/me").json()["role"] == "cliente"
    assert client.get("/api/account").json()["balance_cents"] == 100_000


def test_login_cookie_flags(api):
    register(api, "alice")
    response = login(api, "alice")
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie


def test_login_failures_are_indistinguishable(api):
    register(api, "alice")
    wrong_password = login(api, "alice", "otra-clave-larga-999")
    unknown_user = login(api, "nadie", PASSWORD)
    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()


def test_account_locks_after_repeated_failures_even_with_right_password(api):
    register(api, "alice")
    for _ in range(5):
        assert login(api, "alice", "otra-clave-larga-999").status_code == 401
    assert login(api, "alice", PASSWORD).status_code == 401  # bloqueada: ni la clave correcta entra


def test_successful_login_resets_failed_attempts(api):
    register(api, "alice")
    for _ in range(4):
        login(api, "alice", "otra-clave-larga-999")
    assert login(api, "alice", PASSWORD).status_code == 200
    for _ in range(4):
        login(api, "alice", "otra-clave-larga-999")
    assert login(api, "alice", PASSWORD).status_code == 200


def test_endpoints_require_authentication(api):
    for path in ["/api/me", "/api/account", "/api/transfers"]:
        assert api.get(path).status_code == 401


def test_tampered_or_random_session_cookie_is_rejected(api):
    register(api, "alice")
    api.cookies.set("session", "no-es-un-token-valido")
    assert api.get("/api/me").status_code == 401


def test_logout_invalidates_session_on_the_server(api):
    client = make_user(api, "alice")
    stolen_cookie = client.cookies.get("session")
    assert client.post("/api/auth/logout").status_code == 204
    attacker = TestClient(main.app, raise_server_exceptions=False)
    attacker.cookies.set("session", stolen_cookie)
    assert attacker.get("/api/me").status_code == 401


def test_session_expires(api, engine):
    client = make_user(api, "alice")
    with engine.begin() as conn:
        conn.execute(text("UPDATE sessions SET expires_at = now() - interval '1 minute'"))
    assert client.get("/api/me").status_code == 401


def test_state_changing_requests_need_csrf_token(api):
    alice = make_user(api, "alice")
    make_user(api, "bob")
    no_header = TestClient(main.app, raise_server_exceptions=False)
    no_header.cookies.set("session", alice.cookies.get("session"))
    assert transfer(no_header, "bob", 100).status_code == 403
    no_header.headers["X-CSRF-Token"] = "token-equivocado"
    assert transfer(no_header, "bob", 100).status_code == 403
    assert transfer(alice, "bob", 100).status_code == 201


def test_audit_log_records_security_events(api, engine):
    register(api, "alice")
    login(api, "alice", "otra-clave-larga-999")
    login(api, "alice")
    with engine.connect() as conn:
        actions = [r.action for r in conn.execute(text("SELECT action FROM audit_log ORDER BY id"))]
    assert actions == ["register", "login_failed", "login_ok"]


def test_audit_log_never_contains_passwords(api, engine):
    register(api, "alice")
    login(api, "alice", "otra-clave-larga-999")
    with engine.connect() as conn:
        dump = " ".join(str(v) for row in conn.execute(text("SELECT * FROM audit_log")) for v in row)
    assert "otra-clave-larga-999" not in dump and PASSWORD not in dump


def test_unhandled_errors_return_generic_500(api, monkeypatch):
    def boom():
        raise RuntimeError("password=super-secreto host=db")

    monkeypatch.setattr("app.db.get_engine", boom)
    response = api.post("/api/auth/login", json={"username": "alice", "password": PASSWORD})
    assert response.status_code == 500
    assert response.json() == {"detail": "Error interno"}
    assert "super-secreto" not in response.text
