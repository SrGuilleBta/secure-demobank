"""Transferencias, doble gasto, IDOR y autorización (amenazas T-07, T-08, T-13, T-19, T-20)."""
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import app.main as main
from conftest import make_user, needs_database, transfer

pytestmark = needs_database


def balance(client):
    return client.get("/api/account").json()["balance_cents"]


def test_transfer_moves_money_and_is_visible_to_both(api):
    alice, bob = make_user(api, "alice"), make_user(api, "bob")
    response = transfer(alice, "bob", 2_500, concept="  almuerzo ")
    assert response.status_code == 201
    assert response.json()["concept"] == "almuerzo"
    assert balance(alice) == 97_500 and balance(bob) == 102_500
    assert len(alice.get("/api/transfers").json()) == 1
    assert len(bob.get("/api/transfers").json()) == 1


@pytest.mark.parametrize("amount", [-500, 0, 10.5, "100", True, None, 1_000_001, 10**12])
def test_invalid_amounts_are_rejected_and_balances_do_not_change(api, amount):
    alice, bob = make_user(api, "alice"), make_user(api, "bob")
    assert transfer(alice, "bob", amount).status_code == 422
    assert balance(alice) == balance(bob) == 100_000


@pytest.mark.parametrize("extra", [{"from_username": "bob"}, {"from_user_id": "x"}, {"role": "administrador"}])
def test_transfer_rejects_extra_fields(api, extra):
    alice, _bob = make_user(api, "alice"), make_user(api, "bob")
    assert transfer(alice, "bob", 100, **extra).status_code == 422


def test_origin_account_always_comes_from_the_session(api):
    alice, bob, carol = make_user(api, "alice"), make_user(api, "bob"), make_user(api, "carol")
    transfer(alice, "bob", 100, from_username="carol")  # intento de gastar de otra cuenta: se rechaza
    assert balance(carol) == 100_000
    assert transfer(alice, "bob", 100).status_code == 201
    assert balance(carol) == 100_000


def test_insufficient_balance_is_rejected(api):
    alice, bob = make_user(api, "alice"), make_user(api, "bob")
    assert transfer(alice, "bob", 1_000_000).status_code == 409  # el saldo inicial es 100_000
    assert balance(alice) == 100_000 and balance(bob) == 100_000


def test_cannot_transfer_to_yourself_or_to_unknown_user(api):
    alice = make_user(api, "alice")
    assert transfer(alice, "alice", 100).status_code == 422
    assert transfer(alice, "nadie", 100).status_code == 404


def test_replayed_request_does_not_double_charge(api):
    alice, bob = make_user(api, "alice"), make_user(api, "bob")
    key = str(uuid.uuid4())
    first = transfer(alice, "bob", 1_000, key=key)
    replay = transfer(alice, "bob", 1_000, key=key)
    assert first.status_code == 201 and replay.status_code == 200
    assert first.json()["id"] == replay.json()["id"]
    assert balance(alice) == 99_000 and balance(bob) == 101_000


def test_concurrent_transfers_cannot_double_spend(api):
    """Amenaza T-08: 10 transferencias simultáneas de 30.000 con saldo de 100.000: solo caben 3."""
    alice, bob = make_user(api, "alice"), make_user(api, "bob")

    def send(_):
        client = TestClient(main.app, raise_server_exceptions=False)
        client.cookies.set("session", alice.cookies.get("session"))
        client.headers["X-CSRF-Token"] = alice.headers["X-CSRF-Token"]
        return transfer(client, "bob", 30_000).status_code

    with ThreadPoolExecutor(max_workers=10) as pool:
        statuses = list(pool.map(send, range(10)))

    assert statuses.count(201) == 3 and statuses.count(409) == 7
    assert balance(alice) == 10_000 and balance(bob) == 190_000
    assert balance(alice) + balance(bob) == 200_000  # el dinero total se conserva


def test_crossed_concurrent_transfers_do_not_deadlock(api):
    alice, bob = make_user(api, "alice"), make_user(api, "bob")

    def send(pair):
        sender, receiver = pair
        client = TestClient(main.app, raise_server_exceptions=False)
        client.cookies.set("session", sender.cookies.get("session"))
        client.headers["X-CSRF-Token"] = sender.headers["X-CSRF-Token"]
        return transfer(client, receiver, 100).status_code

    jobs = [(alice, "bob"), (bob, "alice")] * 10
    with ThreadPoolExecutor(max_workers=10) as pool:
        assert set(pool.map(send, jobs)) == {201}
    assert balance(alice) + balance(bob) == 200_000


def test_idor_other_users_transfer_returns_404(api):
    alice, bob, carol = make_user(api, "alice"), make_user(api, "bob"), make_user(api, "carol")
    transfer_id = transfer(alice, "bob", 100).json()["id"]
    assert bob.get(f"/api/transfers/{transfer_id}").status_code == 200
    assert carol.get(f"/api/transfers/{transfer_id}").status_code == 404
    assert carol.get(f"/api/transfers/{uuid.uuid4()}").status_code == 404  # igual que uno inexistente
    assert carol.get("/api/transfers").json() == []


def test_transfer_id_must_be_a_uuid(api):
    alice = make_user(api, "alice")
    assert alice.get("/api/transfers/1").status_code == 422
    assert alice.get("/api/transfers/1 OR 1=1").status_code == 422


def test_sql_injection_payloads_are_treated_as_data(api, engine):
    alice = make_user(api, "alice")
    make_user(api, "bob")
    assert transfer(alice, "bob", 100, concept="'); DROP TABLE users;--").status_code == 201
    assert transfer(alice, "bob' OR '1'='1", 100).status_code == 422
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM users")).scalar_one() == 2


def test_stored_xss_payload_is_kept_as_plain_text(api):
    alice, bob = make_user(api, "alice"), make_user(api, "bob")
    payload = "<script>alert(1)</script>"
    assert transfer(alice, "bob", 100, concept=payload).status_code == 201
    assert bob.get("/api/transfers").json()[0]["concept"] == payload  # la API es JSON; el frontend lo escapa
    assert bob.get("/api/transfers").headers["content-type"].startswith("application/json")


def test_concept_longer_than_100_is_rejected(api):
    alice, _bob = make_user(api, "alice"), make_user(api, "bob")
    assert transfer(alice, "bob", 100, concept="x" * 101).status_code == 422


@pytest.mark.parametrize("query", ["page_size=100000", "page_size=0", "page=0", "page=-1", "page_size=abc"])
def test_pagination_is_bounded(api, query):
    alice = make_user(api, "alice")
    assert alice.get(f"/api/transfers?{query}").status_code == 422
    assert alice.get("/api/transfers?page_size=50").status_code == 200


def test_clients_cannot_use_admin_endpoints_and_admins_can(api, engine):
    alice, admin = make_user(api, "alice"), make_user(api, "root")
    assert alice.get("/api/admin/users").status_code == 403
    assert alice.get("/api/admin/audit").status_code == 403
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET role = 'administrador' WHERE username = 'root'"))
    users = admin.get("/api/admin/users")
    assert users.status_code == 200 and {u["username"] for u in users.json()} == {"alice", "root"}
    assert "password_hash" not in users.text
    assert admin.get("/api/admin/audit").status_code == 200


def test_admin_endpoints_require_authentication(api):
    assert api.get("/api/admin/users").status_code == 401
