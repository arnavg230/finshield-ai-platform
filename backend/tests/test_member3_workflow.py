"""
Member 3 end-to-end tests: suspicious transaction -> alert -> investigation case.
Destination: code/backend/tests/test_member3_workflow.py
Run from code/backend: python -m pytest -v tests/test_member3_workflow.py
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from test_api import client, auth_header, FRAUD_TXN, NORMAL_TXN, fresh_database


@pytest.mark.usefixtures("fresh_database")
def test_suspicious_transaction_creates_open_alert():
    response = client.post("/api/transactions", headers=auth_header("customer"), json=FRAUD_TXN)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["alert_id"] is not None
    assert body["risk"]["risk_level"] in ("MEDIUM", "HIGH")

    alerts = client.get("/api/alerts", headers=auth_header("analyst"))
    assert alerts.status_code == 200, alerts.text
    matching = [a for a in alerts.json() if a["transaction_id"] == body["transaction"]["id"]]
    assert len(matching) == 1
    assert matching[0]["status"] == "OPEN"
    assert matching[0]["risk_level"] == body["risk"]["risk_level"]
    assert 0.0 <= matching[0]["final_risk_score"] <= 1.0


@pytest.mark.usefixtures("fresh_database")
def test_low_risk_transaction_does_not_create_alert():
    response = client.post("/api/transactions", headers=auth_header("customer"), json=NORMAL_TXN)
    assert response.status_code == 201, response.text
    assert response.json()["alert_id"] is None


@pytest.mark.usefixtures("fresh_database")
def test_alert_to_case_notes_and_status_workflow():
    created = client.post("/api/transactions", headers=auth_header("customer"), json=FRAUD_TXN)
    assert created.status_code == 201, created.text
    transaction_id = created.json()["transaction"]["id"]
    alert_id = created.json()["alert_id"]
    assert alert_id is not None
    analyst = auth_header("analyst")

    case_response = client.post("/api/cases", headers=analyst, json={
        "transaction_id": transaction_id,
        "title": "Member 3 suspicious transfer review",
        "description": "Review triggered risk indicators and transaction history.",
        "priority": "HIGH",
    })
    assert case_response.status_code == 201, case_response.text
    case = case_response.json()
    assert case["transaction_id"] == transaction_id
    assert case["alert_id"] == alert_id

    alert = client.get(f"/api/alerts/{alert_id}", headers=analyst)
    assert alert.status_code == 200, alert.text
    assert alert.json()["status"] == "IN_REVIEW"

    note_response = client.post(
        f"/api/cases/{case['id']}/notes", headers=analyst,
        json={"note": "Reviewed transaction details; follow up with account history."},
    )
    assert note_response.status_code == 201, note_response.text

    detail = client.get(f"/api/cases/{case['id']}", headers=analyst)
    assert detail.status_code == 200, detail.text
    assert len(detail.json()["notes"]) == 1
    assert "Reviewed transaction details" in detail.json()["notes"][0]["note"]

    closed = client.patch(f"/api/cases/{case['id']}", headers=analyst, json={
        "status": "CLOSED", "resolution": "Reviewed; no further action in test."
    })
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "CLOSED"
    closed_alert = client.get(f"/api/alerts/{alert_id}", headers=analyst)
    assert closed_alert.status_code == 200, closed_alert.text
    assert closed_alert.json()["status"] == "CLOSED"


@pytest.mark.usefixtures("fresh_database")
def test_alert_status_rejects_unknown_value():
    created = client.post("/api/transactions", headers=auth_header("customer"), json=FRAUD_TXN)
    alert_id = created.json()["alert_id"]
    assert alert_id is not None
    response = client.patch(
        f"/api/alerts/{alert_id}/status", headers=auth_header("analyst"),
        json={"status": "NOT_A_REAL_STATUS"},
    )
    assert response.status_code == 400


@pytest.mark.usefixtures("fresh_database")
def test_case_creation_requires_staff_role():
    created = client.post("/api/transactions", headers=auth_header("customer"), json=FRAUD_TXN)
    response = client.post("/api/cases", headers=auth_header("customer"), json={
        "transaction_id": created.json()["transaction"]["id"],
        "title": "Customer must not open an investigation case",
    })
    assert response.status_code == 403

@pytest.mark.usefixtures("fresh_database")
def test_reanalysis_preserves_case_linked_alert_and_in_review_status():
    created = client.post("/api/transactions", headers=auth_header("customer"), json=FRAUD_TXN)
    assert created.status_code == 201, created.text
    transaction_id = created.json()["transaction"]["id"]
    original_alert_id = created.json()["alert_id"]
    assert original_alert_id is not None
    analyst = auth_header("analyst")

    case_response = client.post(
        "/api/cases", headers=analyst,
        json={"transaction_id": transaction_id, "title": "Re-analysis preservation test", "priority": "HIGH"},
    )
    assert case_response.status_code == 201, case_response.text

    reanalysed = client.post(f"/api/transactions/{transaction_id}/reanalyse", headers=analyst)
    assert reanalysed.status_code == 200, reanalysed.text
    assert reanalysed.json()["alert_id"] == original_alert_id

    alert = client.get(f"/api/alerts/{original_alert_id}", headers=analyst)
    assert alert.status_code == 200, alert.text
    assert alert.json()["status"] == "IN_REVIEW"

    alerts = client.get("/api/alerts", headers=analyst)
    matching = [item for item in alerts.json() if item["transaction_id"] == transaction_id]
    assert len(matching) == 1


@pytest.mark.usefixtures("fresh_database")
def test_reanalysis_does_not_create_duplicate_unlinked_alert():
    created = client.post("/api/transactions", headers=auth_header("customer"), json=FRAUD_TXN)
    assert created.status_code == 201, created.text
    transaction_id = created.json()["transaction"]["id"]
    analyst = auth_header("analyst")

    reanalysed = client.post(f"/api/transactions/{transaction_id}/reanalyse", headers=analyst)
    assert reanalysed.status_code == 200, reanalysed.text
    assert reanalysed.json()["alert_id"] is not None

    alerts = client.get("/api/alerts", headers=analyst)
    matching = [item for item in alerts.json() if item["transaction_id"] == transaction_id]
    assert len(matching) == 1

