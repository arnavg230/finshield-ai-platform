"""Preprocessing for the supplied AMLSim laundering-attempt text."""
def parse_transaction_line(line):
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 10:
        return None
    try:
        amount = float(parts[5])
        converted = float(parts[7]) if parts[7] else amount
    except (ValueError, TypeError):
        return None
    return {
        "timestamp": parts[0], "sender_id": parts[1], "sender_account": parts[2],
        "receiver_id": parts[3], "receiver_account": parts[4],
        "amount": amount, "currency": parts[6], "converted_amount": converted,
        "converted_currency": parts[8], "payment_type": parts[9],
        "label": int(parts[10]) if len(parts) > 10 and parts[10].isdigit() else 1,
    }

def parse_laundering_attempts(text):
    rows, pattern = [], None
    for raw in text.splitlines():
        line = raw.strip().strip("`")
        if not line:
            continue
        if line.startswith("BEGIN "):
            pattern = line[6:].strip()
            continue
        if line.startswith("END "):
            pattern = None
            continue
        tx = parse_transaction_line(line)
        if tx:
            tx["laundering_pattern"] = pattern or "UNKNOWN"
            rows.append(tx)
    return rows

def normalize_transaction(transaction):
    t = dict(transaction)
    aliases = {
        "sender": "sender_id", "receiver": "receiver_id",
        "from_account": "sender_account", "to_account": "receiver_account",
        "amount_usd": "amount", "type": "payment_type"
    }
    for old, new in aliases.items():
        if new not in t and old in t:
            t[new] = t[old]
    t.setdefault("amount", 0.0)
    t["amount"] = float(t["amount"])
    for k in ["timestamp","sender_id","receiver_id","sender_account","receiver_account","currency","payment_type"]:
        t.setdefault(k, "")
    return t

def map_dataset_row(row):
    return normalize_transaction(row)
