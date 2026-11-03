"""
Demo script for the viva.

Starts from an empty-ish database, logs in as the seeded users and walks
through the whole flow: build some history, submit a suspicious transaction,
show the ML score, the AML breakdown, the SHAP features, open a case and
print the audit trail.

Run the server first, then:
    python demo.py
"""
import json

import httpx

BASE_URL = "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE_URL, timeout=60.0)


def login(username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login", data={"username": username, "password": password}
    )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def heading(text: str):
    print(f"\n{'=' * 62}\n{text}\n{'=' * 62}")


def main():
    customer = login("customer", "Customer@123")
    analyst = login("analyst", "Analyst@123")
    admin = login("admin", "Admin@123")

    heading("1. Build some normal history for the sender")
    for i in range(6):
        client.post(
            "/api/transactions",
            headers=customer,
            json={
                "step": i + 1,
                "type": "PAYMENT",
                "amount": 5000.0 + i * 100,
                "nameOrig": "C1231006815",
                "oldbalanceOrg": 200000.0,
                "newbalanceOrig": 195000.0 - i * 100,
                "nameDest": f"M100{i}",
                "oldbalanceDest": 0.0,
                "newbalanceDest": 0.0,
                "timestamp": f"2026-09-10T0{i}:00:00",
            },
        )
    print("Submitted 6 routine payments.")

    heading("2. Submit a suspicious transaction")
    response = client.post(
        "/api/transactions",
        headers=customer,
        json={
            "step": 7,
            "type": "TRANSFER",
            "amount": 181000.0,
            "nameOrig": "C1231006815",
            "oldbalanceOrg": 181000.0,
            "newbalanceOrig": 0.0,
            "nameDest": "C1666544295",
            "oldbalanceDest": 0.0,
            "newbalanceDest": 0.0,
            "timestamp": "2026-09-10T07:00:00",
        },
    )
    body = response.json()
    risk = body["risk"]
    transaction_id = body["transaction"]["id"]

    print(f"Reference     : {body['transaction']['txn_ref']}")
    print(f"ML fraud score: {risk['ml_fraud_score']} (model: {risk['ml_model_used']})")
    print(f"AML score     : {risk['aml_score']} ({risk['aml_risk_level']})")
    print(
        f"  rule={risk['rule_score']}  behaviour={risk['behavior_score']}"
        f"  network={risk['network_score']}"
    )
    print(f"Rules fired   : {', '.join(risk['triggered_rules'])}")
    print(f"FINAL SCORE   : {risk['final_risk_score']}  ->  {risk['risk_level']}")
    print(f"Alert created : {body['alert_id']}")
    for reason in risk["reasons"]:
        print(f"  - {reason}")

    heading("3. SHAP explanation (why the model said fraud)")
    explanation = client.get(
        f"/api/transactions/{transaction_id}/explanation", headers=analyst
    ).json()
    for feature in explanation["top_features"][:6]:
        print(
            f"  {feature['feature']:30s} value={feature['value']:>14}"
            f"  shap={feature['shap_value']:+.4f}"
        )

    heading("4. Analyst opens and closes a case")
    case = client.post(
        "/api/cases",
        headers=analyst,
        json={
            "transaction_id": transaction_id,
            "title": "Full balance transfer to a new account",
            "priority": "HIGH",
        },
    ).json()
    print(f"Case opened: {case['case_ref']} ({case['status']})")

    client.post(
        f"/api/cases/{case['id']}/notes",
        headers=analyst,
        json={"note": "Customer could not explain the source of funds."},
    )
    closed = client.patch(
        f"/api/cases/{case['id']}",
        headers=analyst,
        json={"status": "CLOSED", "resolution": "Confirmed fraud, account frozen."},
    ).json()
    print(f"Case closed: {closed['status']}")

    heading("5. Dashboard summary")
    print(json.dumps(client.get("/api/analytics/summary", headers=analyst).json(), indent=2))

    heading("6. Audit trail (most recent entries)")
    for log in client.get("/api/admin/audit-logs", headers=admin).json()[:8]:
        print(f"  {log['username'] or '-':10s} {log['action']:24s} {log['entity_type']}")


if __name__ == "__main__":
    main()
