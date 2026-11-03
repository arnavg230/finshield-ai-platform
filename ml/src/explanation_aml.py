
"""Generate detailed, human-readable AML risk explanations."""

from .preprocessing_aml import normalize_transaction
from .rules_aml import run_aml_rules
from .behavior_aml import analyze_behavior
from .network_aml import analyze_network
from .scoring_aml import calculate_aml_score, risk_level


# Explain each AML rule in simple language.
RULE_EXPLANATIONS = {
    "HIGH_AMOUNT": (
        "High transaction amount",
        "The transaction amount crossed the configured high-amount threshold."
    ),
    "HIGH_FREQUENCY": (
        "High transaction frequency",
        "The sender made several transactions within the configured time window."
    ),
    "NEW_RECEIVER_LARGE_AMOUNT": (
        "Large transfer to a new receiver",
        "The sender transferred a large amount to a receiver not found "
        "in the supplied transaction history."
    ),
    "SUDDEN_ACTIVITY_SPIKE": (
        "Sudden increase in transaction amount",
        "The current transaction is significantly larger than the "
        "sender's historical average transaction amount."
    ),
}


def _format_amount(amount):
    """Format a numeric amount for readable output."""
    try:
        return f"{float(amount):,.2f}"
    except (TypeError, ValueError):
        return str(amount)


def _explain_rules(rule_result):
    """Create a detailed explanation of triggered rules."""
    triggered = rule_result.get("triggered_rules", [])
    reasons = rule_result.get("reasons", [])

    lines = [
        "RULE-BASED ANALYSIS",
        f"Rule score: {rule_result.get('rule_score', 0):.2f}",
    ]

    if not triggered:
        lines.append("No configured AML rules were triggered.")
    else:
        lines.append("Triggered rules:")

        for rule in triggered:
            title, description = RULE_EXPLANATIONS.get(
                rule,
                (rule.replace("_", " ").title(),
                 "This rule was triggered by the transaction.")
            )
            lines.append(f"- {title} ({rule}): {description}")

    if reasons:
        lines.append("Rule observations:")
        for reason in reasons:
            lines.append(f"- {reason}")

    return lines


def _explain_behavior(transaction, history, behavior_result):
    """Explain the sender's transaction behavior."""
    sender = transaction.get("sender_id", "")
    amount = float(transaction.get("amount", 0) or 0)

    sender_history = [
        item for item in history
        if item.get("sender_id") == sender
    ]

    lines = [
        "",
        "BEHAVIOR ANALYSIS",
        f"Behavior score: {behavior_result.get('behavior_score', 0):.2f}",
        f"Historical transactions for sender: {len(sender_history)}",
        f"Current transaction amount: {_format_amount(amount)}",
    ]

    if sender_history:
        historical_amounts = [
            float(item.get("amount", 0) or 0)
            for item in sender_history
        ]
        average = sum(historical_amounts) / len(historical_amounts)

        lines.append(
            f"Historical average transaction amount: "
            f"{_format_amount(average)}"
        )

        if average > 0:
            ratio = amount / average
            lines.append(
                f"Current amount / historical average: {ratio:.2f}x"
            )
        else:
            lines.append(
                "The historical average is zero, so a transaction-size "
                "ratio cannot be calculated."
            )
    else:
        lines.append(
            "No previous transactions for this sender were supplied. "
            "The behavior assessment is therefore limited."
        )

    lines.append("Behavior observations:")
    for reason in behavior_result.get("reasons", []):
        lines.append(f"- {reason}")

    return lines


def _explain_network(transaction, history, network_result):
    """Explain observed transaction relationships."""
    sender = transaction.get("sender_id", "")
    receiver = transaction.get("receiver_id", "")

    lines = [
        "",
        "NETWORK ANALYSIS",
        f"Network score: {network_result.get('network_score', 0):.2f}",
        f"Sender: {sender}",
        f"Receiver: {receiver}",
        "Network observations:",
    ]

    for reason in network_result.get("reasons", []):
        lines.append(f"- {reason}")

    if not history:
        lines.append(
            "Network analysis is based only on the current transaction "
            "because no transaction history was supplied."
        )

    return lines


def generate_detailed_aml_explanation(
    transaction_data,
    transaction_history=None,
    analysis_result=None,
):
    """
    Generate a detailed AML explanation.

    Args:
        transaction_data (dict): The transaction being investigated.
        transaction_history (list[dict], optional): Previous transactions.
        analysis_result (dict, optional): Existing output from analyze_aml().
            If supplied, its overall score and risk level are used.

    Returns:
        dict: Structured explanation containing scores, observations,
              and a human-readable report.
    """
    transaction = normalize_transaction(transaction_data)
    history = [
        normalize_transaction(item)
        for item in (transaction_history or [])
    ]

    # Reuse the existing analysis functions to get component-level details.
    rule_result = run_aml_rules(transaction, history)
    behavior_result = analyze_behavior(transaction, history)
    network_result = analyze_network(transaction, history)

    calculated_score = calculate_aml_score(
        rule_result["rule_score"],
        behavior_result["behavior_score"],
        network_result["network_score"],
    )

    # Use an existing analysis result when provided, keeping its final
    # risk score consistent with the application's main analysis.
    if analysis_result is not None:
        score = float(
            analysis_result.get("aml_score", calculated_score)
        )
        level = analysis_result.get("risk_level", risk_level(score))
    else:
        score = calculated_score
        level = risk_level(score)

    lines = [
        "DETAILED AML TRANSACTION EXPLANATION",
        "=" * 42,
        f"Transaction ID: {transaction.get('transaction_id', 'Not provided')}",
        f"Sender ID: {transaction.get('sender_id', 'Not provided')}",
        f"Receiver ID: {transaction.get('receiver_id', 'Not provided')}",
        f"Transaction amount: {_format_amount(transaction.get('amount', 0))}",
        f"Timestamp: {transaction.get('timestamp', 'Not provided')}",
        "",
        "OVERALL RISK ASSESSMENT",
        f"AML risk score: {score:.4f} ({score * 100:.2f}%)",
        f"Risk level: {level}",
        "",
    ]

    lines.extend(_explain_rules(rule_result))
    lines.extend(
        _explain_behavior(transaction, history, behavior_result)
    )
    lines.extend(
        _explain_network(transaction, history, network_result)
    )

    lines.extend([
        "",
        "FINAL INTERPRETATION",
    ])

    if level == "HIGH":
        lines.append(
            "The transaction has a high AML risk score under the "
            "current prototype. It should be prioritized for human review."
        )
    elif level == "MEDIUM":
        lines.append(
            "The transaction has a medium AML risk score. Review the "
            "listed observations and gather additional context if needed."
        )
    else:
        lines.append(
            "The transaction has a low AML risk score under the current "
            "prototype. This does not guarantee that the transaction is safe."
        )

    lines.append(
        "Important: This is a rule-based prototype assessment, not proof "
        "of money laundering. A qualified investigator should review "
        "the available evidence before making a decision."
    )

    report = "\n".join(lines)

    return {
        "transaction_id": transaction.get("transaction_id"),
        "aml_score": score,
        "risk_level": level,
        "rule_score": rule_result["rule_score"],
        "triggered_rules": rule_result["triggered_rules"],
        "behavior_score": behavior_result["behavior_score"],
        "network_score": network_result["network_score"],
        "rule_reasons": rule_result["reasons"],
        "behavior_reasons": behavior_result["reasons"],
        "network_reasons": network_result["reasons"],
        "explanation": report,
    }
