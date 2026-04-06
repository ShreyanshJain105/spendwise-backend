import pytest
from unittest.mock import patch
from app import create_app
from models import db as _db


@pytest.fixture()
def app():
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "test-secret"
        }
    )
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user_token(client):
    """Fixture to create a test user and return their JWT token."""
    r = client.post("/api/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    })
    return r.get_json()["data"]["token"]


@pytest.fixture()
def auth_header(user_token):
    return {"Authorization": f"Bearer {user_token}"}


# ── helpers ───────────────────────────────────────────────────────────────────

def make_account(client, headers, name="Checking"):
    r = client.post("/api/accounts", json={"name": name}, headers=headers)
    assert r.status_code == 201
    return r.get_json()["data"]


def make_tx(client, headers, account_id, **overrides):
    payload = {
        "amount": "50.00",
        "type": "expense",
        "category": "food",
        "description": "Lunch",
        "date": "2024-03-15",
        **overrides,
    }
    r = client.post(f"/api/accounts/{account_id}/transactions", json=payload, headers=headers)
    return r


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_register(client):
    r = client.post("/api/auth/register", json={
        "name": "New User",
        "email": "new@example.com",
        "password": "password123"
    })
    assert r.status_code == 201
    data = r.get_json()["data"]
    assert "token" in data
    assert data["user"]["email"] == "new@example.com"


def test_login(client):
    client.post("/api/auth/register", json={
        "name": "User",
        "email": "u@e.com",
        "password": "password123"
    })
    r = client.post("/api/auth/login", json={
        "email": "u@e.com",
        "password": "password123"
    })
    assert r.status_code == 200
    assert "token" in r.get_json()["data"]


def test_login_invalid(client):
    r = client.post("/api/auth/login", json={
        "email": "nonexistent@e.com",
        "password": "wrong"
    })
    assert r.status_code == 401


def test_auth_me(client, auth_header):
    r = client.get("/api/auth/me", headers=auth_header)
    assert r.status_code == 200
    assert r.get_json()["data"]["email"] == "test@example.com"


def test_unauthorized(client):
    r = client.get("/api/accounts")
    assert r.status_code == 401


# ── isolation ─────────────────────────────────────────────────────────────────

def test_multi_user_isolation(client, auth_header):
    # User 1 (from fixture) creates an account
    acc1 = make_account(client, auth_header, "User 1 Account")
    
    # User 2 registers
    r2 = client.post("/api/auth/register", json={
        "name": "User 2",
        "email": "user2@example.com",
        "password": "password123"
    })
    token2 = r2.get_json()["data"]["token"]
    header2 = {"Authorization": f"Bearer {token2}"}
    
    # User 2 should see 0 accounts
    r = client.get("/api/accounts", headers=header2)
    assert len(r.get_json()["data"]) == 0
    
    # User 2 should not be able to access User 1's account
    r = client.get(f"/api/accounts/{acc1['id']}/transactions", headers=header2)
    assert r.status_code == 401
    assert "permission" in r.get_json()["error"].lower()


# ── health ────────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


# ── accounts ──────────────────────────────────────────────────────────────────

def test_create_account(client, auth_header):
    r = client.post("/api/accounts", json={"name": "Savings"}, headers=auth_header)
    assert r.status_code == 201
    data = r.get_json()["data"]
    assert data["name"] == "Savings"
    assert "id" in data


def test_create_account_blank_name(client, auth_header):
    r = client.post("/api/accounts", json={"name": "  "}, headers=auth_header)
    assert r.status_code == 422


def test_list_accounts(client, auth_header):
    make_account(client, auth_header, "A")
    make_account(client, auth_header, "B")
    r = client.get("/api/accounts", headers=auth_header)
    assert r.status_code == 200
    assert len(r.get_json()["data"]) == 2


def test_delete_account(client, auth_header):
    acc = make_account(client, auth_header)
    r = client.delete(f"/api/accounts/{acc['id']}", headers=auth_header)
    assert r.status_code == 200
    r2 = client.get("/api/accounts", headers=auth_header)
    assert r2.get_json()["data"] == []


# ── transactions ──────────────────────────────────────────────────────────────

def test_create_transaction(client, auth_header):
    acc = make_account(client, auth_header)
    r = make_tx(client, auth_header, acc["id"])
    assert r.status_code == 201
    data = r.get_json()["data"]
    assert data["amount"] == "50.00"


def test_create_transaction_invalid_amount(client, auth_header):
    acc = make_account(client, auth_header)
    r = make_tx(client, auth_header, acc["id"], amount="-10")
    assert r.status_code == 422


def test_list_transactions(client, auth_header):
    acc = make_account(client, auth_header)
    make_tx(client, auth_header, acc["id"])
    make_tx(client, auth_header, acc["id"], description="Dinner")
    r = client.get(f"/api/accounts/{acc['id']}/transactions", headers=auth_header)
    assert r.status_code == 200
    assert len(r.get_json()["data"]) == 2


def test_update_transaction(client, auth_header):
    acc = make_account(client, auth_header)
    tx = make_tx(client, auth_header, acc["id"]).get_json()["data"]
    r = client.patch(
        f"/api/accounts/{acc['id']}/transactions/{tx['id']}",
        json={"amount": "99.99", "description": "Updated"},
        headers=auth_header
    )
    assert r.status_code == 200


def test_delete_transaction(client, auth_header):
    acc = make_account(client, auth_header)
    tx = make_tx(client, auth_header, acc["id"]).get_json()["data"]
    r = client.delete(f"/api/accounts/{acc['id']}/transactions/{tx['id']}", headers=auth_header)
    assert r.status_code == 200


# ── summary ───────────────────────────────────────────────────────────────────

def test_summary_balance(client, auth_header):
    acc = make_account(client, auth_header)
    make_tx(client, auth_header, acc["id"], type="income", category="income", description="Pay", amount="1000")
    make_tx(client, auth_header, acc["id"], amount="200")
    r = client.get(f"/api/accounts/{acc['id']}/summary", headers=auth_header)
    s = r.get_json()["data"]
    assert s["balance"] == "800.00"


# ── budgets ───────────────────────────────────────────────────────────────────

def test_set_budget(client, auth_header):
    acc = make_account(client, auth_header)
    r = client.put(
        f"/api/accounts/{acc['id']}/budgets",
        json={"category": "food", "monthly_limit": "5000"},
        headers=auth_header
    )
    assert r.status_code == 201


# ── recurring ─────────────────────────────────────────────────────────────────

def test_create_recurring(client, auth_header):
    acc = make_account(client, auth_header)
    r = client.post(f"/api/accounts/{acc['id']}/recurring", json={
        "amount": "500",
        "type": "expense",
        "category": "utilities",
        "description": "Electricity bill",
        "frequency": "monthly",
        "next_date": "2024-04-01",
    }, headers=auth_header)
    assert r.status_code == 201


# ── AI chat ───────────────────────────────────────────────────────────────────

@patch("services.ai_service.get_financial_advice")
def test_chat_with_context(mock_advice, client, auth_header):
    mock_advice.return_value = "You should save more on food."
    acc = make_account(client, auth_header)
    r = client.post(f"/api/accounts/{acc['id']}/chat", json={"message": "How to save?"}, headers=auth_header)
    assert r.status_code == 200
