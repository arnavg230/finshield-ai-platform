"""Deterministic investigation-assistant placeholder; no API key required."""
def generate_investigation_summary(transaction, aml_score, risk_level, triggered_rules, behavior_score, network_score, reasons):
    steps = [
        "Review the customer's recent transaction history.",
        "Verify the source and purpose of funds.",
        "Review linked accounts and counterparties."
    ]
    if "HIGH_FREQUENCY" in triggered_rules:
        steps.append("Check transaction timing for rapid movement of funds.")
    if network_score >= 0.5:
        steps.append("Inspect connected accounts for possible transaction chains.")
    return {
        "summary": f"Transaction {transaction.get('sender_id','?')} -> {transaction.get('receiver_id','?')} has AML score {aml_score:.2f} and risk level {risk_level}.",
        "investigation_steps": steps,
        "disclaimer": "This assistant supports investigation and does not determine that a crime occurred."
    }
