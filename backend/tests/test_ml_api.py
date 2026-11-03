
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.fixture(scope="module")
def auth_headers():
    """
    Register a test user, log in, and return authentication headers.
    A unique username avoids conflicts with previous test runs.
    """

    unique_id = uuid.uuid4().hex[:10]

    username = f"ml_test_{unique_id}"
    password = "TestPassword@123"

    register_payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "full_name": "ML API Test User",
        "role": "ANALYST"
    }

    register_response = client.post(
        "/api/auth/register",
        json=register_payload
    )

    assert register_response.status_code == 201, (
        f"Registration failed: {register_response.text}"
    )

    login_response = client.post(
        "/api/auth/login",
        data={
            "username": username,
            "password": password
        }
    )

    assert login_response.status_code == 200, (
        f"Login failed: {login_response.text}"
    )

    token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def create_transaction(headers, amount, sender, receiver):
    """Submit a transaction and return its API response."""

    payload = {
        "step": 100,
        "type": "TRANSFER",
        "amount": amount,
        "nameOrig": sender,
        "oldbalanceOrg": amount + 1000,
        "newbalanceOrig": 1000,
        "nameDest": receiver,
        "oldbalanceDest": 0,
        "newbalanceDest": amount,
        "isFlaggedFraud": 0,
        "currency": "US Dollar"
    }

    return client.post(
        "/api/transactions",
        json=payload,
        headers=headers
    )


def validate_risk_response(response):
    """Validate the structure and basic values of the risk analysis."""

    assert response.status_code == 201, response.text

    data = response.json()

    assert "transaction" in data
    assert "risk" in data

    risk = data["risk"]

    assert "final_risk_score" in risk
    assert "risk_level" in risk

    assert isinstance(risk["final_risk_score"], (int, float))

    assert risk["risk_level"] in [
        "LOW",
        "MEDIUM",
        "HIGH"
    ]

    assert risk["shap_available"] in [True, False]

    # AML component scores should be between 0 and 1 when available.
    for field in [
        "aml_score",
        "rule_score",
        "behavior_score",
        "network_score"
    ]:
        if risk[field] is not None:
            assert 0 <= risk[field] <= 1, (
                f"{field} is outside the expected range"
            )

    return data


def test_normal_transaction_analysis(auth_headers):
    """Test ML/AML analysis of a normal transaction."""

    response = create_transaction(
        auth_headers,
        amount=500,
        sender="NORMAL_SENDER_001",
        receiver="NORMAL_RECEIVER_001"
    )

    data = validate_risk_response(response)

    assert data["transaction"]["amount"] == 500


def test_suspicious_transaction_analysis(auth_headers):
    """Test ML/AML analysis of a high-value transaction."""

    response = create_transaction(
        auth_headers,
        amount=181000,
        sender="SUSPICIOUS_SENDER_001",
        receiver="SUSPICIOUS_RECEIVER_001"
    )

    data = validate_risk_response(response)

    risk = data["risk"]

    assert risk["aml_score"] is not None
    assert risk["triggered_rules"] is not None


def test_risk_score_fields(auth_headers):
    """Check that the API returns the expected ML and AML fields."""

    response = create_transaction(
        auth_headers,
        amount=2500,
        sender="RISK_TEST_SENDER_001",
        receiver="RISK_TEST_RECEIVER_001"
    )

    data = validate_risk_response(response)
    risk = data["risk"]

    expected_fields = [
        "ml_model_used",
        "ml_fraud_score",
        "ml_prediction",
        "aml_score",
        "aml_risk_level",
        "rule_score",
        "behavior_score",
        "network_score",
        "triggered_rules",
        "reasons",
        "final_risk_score",
        "risk_level",
        "shap_available"
    ]

    for field in expected_fields:
        assert field in risk, f"Missing risk field: {field}"

    if risk["ml_prediction"] is not None:
        assert risk["ml_prediction"] in [0, 1]


def test_aml_explanation(auth_headers):
    """Check whether the transaction response contains AML explanations."""

    response = create_transaction(
        auth_headers,
        amount=150000,
        sender="EXPLANATION_SENDER_001",
        receiver="EXPLANATION_RECEIVER_001"
    )

    data = validate_risk_response(response)

    assert "aml_explanation" in data
    assert "aml_explanation_details" in data


def test_transaction_reanalysis(auth_headers):
    """Test reanalysis of an existing transaction."""

    response = create_transaction(
        auth_headers,
        amount=75000,
        sender="REANALYSIS_SENDER_001",
        receiver="REANALYSIS_RECEIVER_001"
    )

    data = validate_risk_response(response)

    transaction_id = data["transaction"]["id"]

    reanalysis_response = client.post(
        f"/api/transactions/{transaction_id}/reanalyse",
        headers=auth_headers
    )

    assert reanalysis_response.status_code == 200, (
        f"Reanalysis failed: {reanalysis_response.text}"
    )

    reanalysis_data = reanalysis_response.json()

    assert "transaction" in reanalysis_data
    assert "risk" in reanalysis_data

    assert "final_risk_score" in reanalysis_data["risk"]
    assert "risk_level" in reanalysis_data["risk"]


def test_transaction_explanation_endpoint(auth_headers):
    """Test the dedicated transaction explanation endpoint."""

    response = create_transaction(
        auth_headers,
        amount=120000,
        sender="DETAIL_SENDER_001",
        receiver="DETAIL_RECEIVER_001"
    )

    data = validate_risk_response(response)

    transaction_id = data["transaction"]["id"]

    explanation_response = client.get(
        f"/api/transactions/{transaction_id}/explanation",
        headers=auth_headers
    )

    assert explanation_response.status_code == 200, (
        f"Explanation request failed: {explanation_response.text}"
    )


def test_unauthenticated_transaction():
    """Verify that transaction submission requires authentication."""

    response = client.post(
        "/api/transactions",
        json={
            "type": "TRANSFER",
            "amount": 500,
            "nameOrig": "UNAUTH_SENDER",
            "nameDest": "UNAUTH_RECEIVER"
        }
    )

    assert response.status_code in [401, 403]
