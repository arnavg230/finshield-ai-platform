"""Notification payload builder. It does not send real SMS/email."""
def build_notification(transaction, aml_score, risk_level, reasons):
    if risk_level == "LOW":
        return {"should_notify":False,"channels":[],"message":"No alert notification required."}
    msg = f"FinShield AML Alert: {risk_level} risk transaction. AML score={aml_score:.2f}. " + " ".join(reasons[:3])
    return {"should_notify":True,"channels":["dashboard","email"],"message":msg}
