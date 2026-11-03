
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.fixture(scope="module")
def auth_headers():
    """Create an analyst account and obtain an access token."""

    unique_id = uuid.uuid4().hex[:10]
    username = f"integration_{unique_id}"
    password = "TestPassword@123"

    register_payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "full_name": "Integration Test Analyst",
        "role": "ANALYST"
    }

    register_response = client.post(
        "/api/auth/register",
        json=register_payload
    )

    assert register_response.status_code == 201, register_response.text

    login_response = client.post(
        "/api/auth/login",
        data={
            "username": username,
            "password": password
        }
    )

    assert login_response.status_code == 200, login_response.text

    token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def submit_test_transaction(headers):
    """Submit a transaction through the actual backend."""

    unique_id = uuid.uuid4().hex[:10]

    payload = {
        "step": 100,
        "type": "TRANSFER",
        "amount": 150000,
        "nameOrig": f"INT_SENDER_{unique_id}",
        "oldbalanceOrg": 200000,
        "newbalanceOrig": 50000,
        "nameDest": f"INT_RECEIVER_{unique_id}",
        "oldbalanceDest": 0,
        "newbalanceDest": 150000,
        "isFlaggedFraud": 0,
        "currency": "US Dollar"
    }

    response = client.post(
        "/api/transactions",
        json=payload,
        headers=headers
    )

    assert response.status_code == 201, response.text

    return response.json()



def test_transaction_saved_and_retrieved(auth_headers):
    """Verify that a submitted transaction is stored and retrievable."""

    result = submit_test_transaction(auth_headers)

    transaction_id = result["transaction"]["id"]

    response = client.get(
        f"/api/transactions/{transaction_id}",
        headers=auth_headers
    )

    assert response.status_code == 200, response.text

    saved_data = response.json()

    assert "transaction" in saved_data
    assert "risk" in saved_data

    saved_transaction = saved_data["transaction"]

    assert saved_transaction["id"] == transaction_id
    assert saved_transaction["amount"] == 150000
    assert saved_transaction["txn_type"] == "TRANSFER"

    assert saved_data["risk"]["final_risk_score"] >= 0



def test_transaction_appears_in_transaction_history(auth_headers):
    """Verify that a submitted transaction appears in transaction history."""

    result = submit_test_transaction(auth_headers)

    transaction_id = result["transaction"]["id"]

    response = client.get(
        "/api/transactions",
        headers=auth_headers
    )

    assert response.status_code == 200, response.text

    transactions = response.json()

    assert isinstance(transactions, list)

    transaction_ids = [
        transaction["id"] for transaction in transactions
    ]

    assert transaction_id in transaction_ids


def test_complete_ml_aml_integration(auth_headers):
    """Verify that ML and AML analysis are returned together."""

    result = submit_test_transaction(auth_headers)

    assert "transaction" in result
    assert "risk" in result

    risk = result["risk"]

    # ML analysis
    assert "ml_fraud_score" in risk
    assert "ml_prediction" in risk

    # AML analysis
    assert "aml_score" in risk
    assert "aml_risk_level" in risk

    # Individual AML components
    assert "rule_score" in risk
    assert "behavior_score" in risk
    assert "network_score" in risk

    # Combined risk result
    assert "final_risk_score" in risk
    assert "risk_level" in risk

    assert 0 <= risk["final_risk_score"] <= 1

    assert risk["risk_level"] in [
        "LOW",
        "MEDIUM",
        "HIGH"
    ]

    # Explanation information
    assert "aml_explanation" in result
    assert "aml_explanation_details" in result


def test_transaction_reanalysis_preserves_transaction(auth_headers):
    """Verify that reanalysis works on a previously stored transaction."""

    result = submit_test_transaction(auth_headers)

    transaction_id = result["transaction"]["id"]
    original_txn_ref = result["transaction"]["txn_ref"]

    response = client.post(
        f"/api/transactions/{transaction_id}/reanalyse",
        headers=auth_headers
    )

    assert response.status_code == 200, response.text

    reanalysed = response.json()

    assert reanalysed["transaction"]["id"] == transaction_id
    assert reanalysed["transaction"]["txn_ref"] == original_txn_ref
    assert "risk" in reanalysed

    assert 0 <= reanalysed["risk"]["final_risk_score"] <= 1


def test_invalid_transaction_is_rejected(auth_headers):
    """Verify that invalid transaction input is rejected."""

    payload = {
        "type": "TRANSFER",
        "amount": -500,
        "nameOrig": "INVALID_SENDER",
        "nameDest": "INVALID_RECEIVER"
    }

    response = client.post(
        "/api/transactions",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 422
