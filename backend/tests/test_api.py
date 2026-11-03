"""
Basic API tests for the FinShield backend.

These run against a temporary SQLite database so the PostgreSQL data is not
touched. Run them with:

    pytest -v
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_api.db"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.models import ROLE_ADMIN, ROLE_ANALYST, ROLE_CUSTOMER, User
from app.security import hash_password

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_database():
    """Start every test with empty tables and three known users."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    from app.database import SessionLocal

    db = SessionLocal()
    for username, role in [
        ("admin", ROLE_ADMIN),
        ("analyst", ROLE_ANALYST),
        ("customer", ROLE_CUSTOMER),
    ]:
        db.add(
            User(
                username=username,
                email=f"{username}@test.com",
                hashed_password=hash_password("Test@123"),
                role=role,
            )
        )
    db.commit()
    db.close()
    yield


def auth_header(username: str) -> dict:
    response = client.post(
        "/api/auth/login", data={"username": username, "password": "Test@123"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


FRAUD_TXN = {
    "step": 1,
    "type": "TRANSFER",
    "amount": 181000.0,
    "nameOrig": "C1231006815",
    "oldbalanceOrg": 181000.0,
    "newbalanceOrig": 0.0,
    "nameDest": "C1666544295",
    "oldbalanceDest": 0.0,
    "newbalanceDest": 0.0,
}

NORMAL_TXN = {
    "step": 1,
    "type": "PAYMENT",
    "amount": 4800.0,
    "nameOrig": "C9999999999",
    "oldbalanceOrg": 50000.0,
    "newbalanceOrig": 45200.0,
    "nameDest": "M1979787155",
    "oldbalanceDest": 0.0,
    "newbalanceDest": 0.0,
}


# --- Authentication ---------------------------------------------------------
def test_register_and_login():
    response = client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "Secret@123",
            "role": "CUSTOMER",
        },
    )
    assert response.status_code == 201

    login = client.post(
        "/api/auth/login", data={"username": "newuser", "password": "Secret@123"}
    )
    assert login.status_code == 200
    assert login.json()["role"] == "CUSTOMER"


def test_login_with_wrong_password_fails():
    response = client.post(
        "/api/auth/login", data={"username": "admin", "password": "wrong"}
    )
    assert response.status_code == 401


def test_endpoint_requires_token():
    assert client.get("/api/transactions").status_code == 401


def test_cannot_self_register_as_admin():
    response = client.post(
        "/api/auth/register",
        json={
            "username": "sneaky",
            "email": "sneaky@test.com",
            "password": "Secret@123",
            "role": "ADMIN",
        },
    )
    assert response.status_code == 403


# --- RBAC -------------------------------------------------------------------
def test_customer_cannot_view_alerts():
    assert client.get("/api/alerts", headers=auth_header("customer")).status_code == 403


def test_analyst_can_view_alerts():
    assert client.get("/api/alerts", headers=auth_header("analyst")).status_code == 200


def test_analyst_cannot_manage_users():
    response = client.get("/api/admin/users", headers=auth_header("analyst"))
    assert response.status_code == 403


def test_admin_can_manage_users():
    response = client.get("/api/admin/users", headers=auth_header("admin"))
    assert response.status_code == 200


# --- Transactions and scoring ----------------------------------------------
def test_fraud_transaction_gets_high_ml_score():
    response = client.post(
        "/api/transactions", headers=auth_header("customer"), json=FRAUD_TXN
    )
    assert response.status_code == 201
    risk = response.json()["risk"]
    assert risk["ml_fraud_score"] > 0.9
    assert risk["ml_prediction"] == 1
    assert risk["risk_level"] == "HIGH"
    assert response.json()["alert_id"] is not None


def test_normal_transaction_is_low_risk():
    response = client.post(
        "/api/transactions", headers=auth_header("customer"), json=NORMAL_TXN
    )
    assert response.status_code == 201
    body = response.json()
    assert body["risk"]["risk_level"] == "LOW"
    assert body["alert_id"] is None


def test_invalid_transaction_type_is_rejected():
    bad = dict(NORMAL_TXN, type="UPI")
    response = client.post(
        "/api/transactions", headers=auth_header("customer"), json=bad
    )
    assert response.status_code == 400


def test_aml_module_returns_scores():
    response = client.post(
        "/api/transactions", headers=auth_header("customer"), json=FRAUD_TXN
    )
    risk = response.json()["risk"]
    assert risk["aml_score"] is not None
    assert risk["aml_risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert "HIGH_AMOUNT" in risk["triggered_rules"]


def test_shap_explanation_is_returned():
    created = client.post(
        "/api/transactions", headers=auth_header("customer"), json=FRAUD_TXN
    ).json()
    response = client.get(
        f"/api/transactions/{created['transaction']['id']}/explanation",
        headers=auth_header("analyst"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert len(body["top_features"]) > 0


def test_customer_sees_only_own_transactions():
    client.post("/api/transactions", headers=auth_header("customer"), json=NORMAL_TXN)
    client.post("/api/transactions", headers=auth_header("analyst"), json=FRAUD_TXN)

    customer_list = client.get(
        "/api/transactions", headers=auth_header("customer")
    ).json()
    analyst_list = client.get(
        "/api/transactions", headers=auth_header("analyst")
    ).json()
    assert len(customer_list) == 1
    assert len(analyst_list) == 2


# --- Cases ------------------------------------------------------------------
def test_case_can_be_created_and_closed():
    created = client.post(
        "/api/transactions", headers=auth_header("customer"), json=FRAUD_TXN
    ).json()
    headers = auth_header("analyst")

    case = client.post(
        "/api/cases",
        headers=headers,
        json={
            "transaction_id": created["transaction"]["id"],
            "title": "Review large transfer",
            "priority": "HIGH",
        },
    )
    assert case.status_code == 201
    case_id = case.json()["id"]

    note = client.post(
        f"/api/cases/{case_id}/notes", headers=headers, json={"note": "Checked history."}
    )
    assert note.status_code == 201

    closed = client.patch(
        f"/api/cases/{case_id}",
        headers=headers,
        json={"status": "CLOSED", "resolution": "Confirmed fraud."},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"

    detail = client.get(f"/api/cases/{case_id}", headers=headers).json()
    assert len(detail["notes"]) == 1


def test_customer_cannot_create_case():
    created = client.post(
        "/api/transactions", headers=auth_header("customer"), json=FRAUD_TXN
    ).json()
    response = client.post(
        "/api/cases",
        headers=auth_header("customer"),
        json={"transaction_id": created["transaction"]["id"], "title": "Test"},
    )
    assert response.status_code == 403


# --- Audit trail ------------------------------------------------------------
def test_audit_log_records_actions():
    client.post("/api/transactions", headers=auth_header("customer"), json=FRAUD_TXN)
    logs = client.get("/api/admin/audit-logs", headers=auth_header("admin")).json()
    actions = [log["action"] for log in logs]
    assert "LOGIN_SUCCESS" in actions
    assert "TRANSACTION_ANALYSED" in actions


# --- System -----------------------------------------------------------------
def test_health_shows_models_loaded():
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "xgboost" in body["ml_models_loaded"]
    assert body["aml_module_available"] is True
