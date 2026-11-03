from .preprocessing_aml import normalize_transaction
from .rules_aml import run_aml_rules
from .behavior_aml import analyze_behavior
from .network_aml import analyze_network
from .scoring_aml import calculate_aml_score, risk_level
from .llm_assistant_aml import generate_investigation_summary
from .notifications_aml import build_notification

def analyze_aml(transaction_data, transaction_history=None):
    transaction = normalize_transaction(transaction_data)
    history = [normalize_transaction(x) for x in (transaction_history or [])]
    rule = run_aml_rules(transaction, history)
    behavior = analyze_behavior(transaction, history)
    network = analyze_network(transaction, history)
    score = calculate_aml_score(rule["rule_score"], behavior["behavior_score"], network["network_score"])
    level = risk_level(score)
    reasons = list(dict.fromkeys(rule["reasons"] + behavior["reasons"] + network["reasons"]))
    investigation = generate_investigation_summary(
        transaction, score, level, rule["triggered_rules"],
        behavior["behavior_score"], network["network_score"], reasons
    )
    notification = build_notification(transaction, score, level, reasons)
    return {
        "aml_score":score, "risk_level":level,
        "triggered_rules":rule["triggered_rules"], "rule_score":rule["rule_score"],
        "behavior_score":behavior["behavior_score"], "network_score":network["network_score"],
        "reasons":reasons, "investigation_summary":investigation, "notification":notification
    }
