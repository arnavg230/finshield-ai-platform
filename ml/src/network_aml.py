
"""Basic relationship/network analysis without external graph packages."""

from collections import Counter


def analyze_network(transaction, history=None):

    history = history or []

    sender = transaction.get("sender_id", "")
    receiver = transaction.get("receiver_id", "")

    # Create transaction relationships
    edges = [
        (h.get("sender_id"), h.get("receiver_id"))
        for h in history
    ]

    edges.append((sender, receiver))

    # Count outgoing and incoming transactions
    outgoing = Counter(a for a, b in edges if a)
    incoming = Counter(b for a, b in edges if b)

    score = 0.0
    reasons = []

    # Check frequent outgoing transactions
    if outgoing[sender] >= 5:
        score += 0.30
        reasons.append(
            "Sender is connected to many transactions."
        )

    # Check frequent incoming transactions
    if incoming[receiver] >= 5:
        score += 0.30
        reasons.append(
            "Receiver is connected to many incoming transactions."
        )

    # Check transfers to multiple different receivers
    distinct_receivers = {
        b for a, b in edges
        if a == sender and b
    }

    if len(distinct_receivers) >= 5:
        score += 0.30
        reasons.append(
            "Sender has transferred money to multiple different receivers."
        )

    # Check reciprocal transfer relationships
    if (receiver, sender) in edges:
        score += 0.40
        reasons.append(
            "A reciprocal transfer relationship was observed."
        )

    if not reasons:
        reasons.append(
            "No strong relationship anomaly was found in the supplied history."
        )

    return {
        "network_score": min(score, 1.0),
        "reasons": reasons
    }
