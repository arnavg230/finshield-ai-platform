"""Configurable prototype AML rules."""
from datetime import datetime, timedelta

DEFAULT_THRESHOLDS = {
    "high_amount": 100000.0,
    "high_frequency_count": 5,
    "frequency_window_hours": 24,
    "new_receiver_amount": 50000.0,
    "activity_spike_ratio": 3.0,
}

def _dt(x):
    if isinstance(x, datetime): return x
    try: return datetime.strptime(str(x), "%Y/%m/%d %H:%M")
    except Exception: return None

def run_aml_rules(transaction, history=None, thresholds=None):
    history = history or []
    cfg = dict(DEFAULT_THRESHOLDS)
    if thresholds: cfg.update(thresholds)
    score, triggered, reasons = 0.0, [], []
    amount = float(transaction.get("amount", 0))
    if amount >= cfg["high_amount"]:
        triggered.append("HIGH_AMOUNT")
        reasons.append("Transaction amount is unusually high.")
        score += 0.30

    sender = transaction.get("sender_id", "")
    receiver = transaction.get("receiver_id", "")
    t0 = _dt(transaction.get("timestamp"))
    recent = []
    for h in history:
        ht = _dt(h.get("timestamp"))
        if h.get("sender_id") == sender and t0 and ht and timedelta(0) <= t0-ht <= timedelta(hours=cfg["frequency_window_hours"]):
            recent.append(h)
    if len(recent) + 1 >= cfg["high_frequency_count"]:
        triggered.append("HIGH_FREQUENCY")
        reasons.append("Too many transactions were made in a short time window.")
        score += 0.25

    seen = {h.get("receiver_id") for h in history if h.get("sender_id") == sender}
    if receiver not in seen and amount >= cfg["new_receiver_amount"]:
        triggered.append("NEW_RECEIVER_LARGE_AMOUNT")
        reasons.append("Large transfer to a receiver not previously seen in the history.")
        score += 0.20

    amounts = [float(h.get("amount",0)) for h in history if h.get("sender_id") == sender]
    if amounts:
        avg = sum(amounts)/len(amounts)
        if avg > 0 and amount/avg >= cfg["activity_spike_ratio"]:
            triggered.append("SUDDEN_ACTIVITY_SPIKE")
            reasons.append("Current transaction is much larger than the sender's historical average.")
            score += 0.15
    return {"rule_score": min(score,1.0), "triggered_rules": triggered, "reasons": reasons}
