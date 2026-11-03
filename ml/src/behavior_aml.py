"""Customer/account behaviour analysis."""
def analyze_behavior(transaction, history=None):
    history = history or []
    sender = transaction.get("sender_id","")
    amount = float(transaction.get("amount",0))
    own = [h for h in history if h.get("sender_id")==sender]
    if not own:
        return {"behavior_score":0.20, "reasons":["No historical activity was supplied for comparison."]}
    amounts = [float(h.get("amount",0)) for h in own]
    avg = sum(amounts)/len(amounts)
    score, reasons = 0.0, []
    if avg > 0:
        ratio = amount/avg
        if ratio >= 5: score, reasons = 0.90, ["Transaction is at least five times the historical average."]
        elif ratio >= 3: score, reasons = 0.70, ["Transaction is at least three times the historical average."]
        elif ratio >= 2: score, reasons = 0.45, ["Transaction is at least twice the historical average."]
    if len(own) >= 10:
        score = min(1.0, score+0.10)
        reasons.append("Account has high recent transaction activity.")
    if not reasons:
        reasons.append("Transaction is broadly consistent with the supplied history.")
    return {"behavior_score":score, "reasons":reasons}
