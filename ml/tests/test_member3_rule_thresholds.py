"""
Member 3 AML threshold tests.
Destination: code/ml/tests/test_member3_rule_thresholds.py
Run from repository root: python -m pytest -v code/ml/tests/test_member3_rule_thresholds.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

from src.rules_aml import DEFAULT_THRESHOLDS, run_aml_rules


def transaction(amount, sender="S1", receiver="R1", timestamp="2022/08/05 10:00"):
    return {"timestamp": timestamp, "sender_id": sender, "receiver_id": receiver, "amount": amount}


def test_high_amount_rule_is_inclusive_at_threshold():
    threshold = DEFAULT_THRESHOLDS["high_amount"]
    result = run_aml_rules(transaction(threshold), history=[])
    assert "HIGH_AMOUNT" in result["triggered_rules"]
    assert any("unusually high" in reason.lower() for reason in result["reasons"])


def test_high_amount_rule_does_not_trigger_just_below_threshold():
    threshold = DEFAULT_THRESHOLDS["high_amount"]
    history = [{"timestamp": "2022/08/04 10:00", "sender_id": "S1", "receiver_id": "R1", "amount": 1000}]
    result = run_aml_rules(transaction(threshold - 0.01), history=history)
    assert "HIGH_AMOUNT" not in result["triggered_rules"]


def test_new_receiver_rule_respects_threshold_and_explains_reason():
    threshold = DEFAULT_THRESHOLDS["new_receiver_amount"]
    history = [{"timestamp": "2022/08/04 10:00", "sender_id": "S1", "receiver_id": "OLD", "amount": 1000}]
    at_threshold = run_aml_rules(transaction(threshold, receiver="NEW"), history)
    below_threshold = run_aml_rules(transaction(threshold - 0.01, receiver="NEW"), history)
    assert "NEW_RECEIVER_LARGE_AMOUNT" in at_threshold["triggered_rules"]
    assert any("receiver" in reason.lower() for reason in at_threshold["reasons"])
    assert "NEW_RECEIVER_LARGE_AMOUNT" not in below_threshold["triggered_rules"]


def test_frequency_rule_triggers_at_configured_count():
    count = DEFAULT_THRESHOLDS["high_frequency_count"]
    history = [
        {"timestamp": f"2022/08/05 {hour:02d}:00", "sender_id": "S1", "receiver_id": f"R{hour}", "amount": 100}
        for hour in range(10 - (count - 1), 10)
    ]
    result = run_aml_rules(transaction(100, timestamp="2022/08/05 10:00"), history)
    assert "HIGH_FREQUENCY" in result["triggered_rules"]
    assert any("short time" in reason.lower() for reason in result["reasons"])


def test_rule_score_is_bounded_and_explanations_exist():
    result = run_aml_rules(transaction(DEFAULT_THRESHOLDS["high_amount"], receiver="NEW"), history=[])
    assert 0.0 <= result["rule_score"] <= 1.0
    assert result["triggered_rules"]
    assert result["reasons"]
    assert len(result["reasons"]) == len(result["triggered_rules"])


def test_threshold_overrides_are_respected():
    result = run_aml_rules(transaction(500), history=[], thresholds={"high_amount": 500})
    assert "HIGH_AMOUNT" in result["triggered_rules"]
