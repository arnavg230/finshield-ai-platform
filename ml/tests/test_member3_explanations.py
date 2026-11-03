# Member 3 tests for detailed AML explanations.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

from src.explanation_aml import generate_detailed_aml_explanation


def test_explanation_names_triggered_high_amount_rule():
    transaction = {"timestamp": "2022/08/05 10:00", "sender_id": "S1", "receiver_id": "R1", "amount": 150000}
    result = generate_detailed_aml_explanation(transaction)
    assert "HIGH_AMOUNT" in result["triggered_rules"]
    assert "High transaction amount" in result["explanation"]
    assert "configured high-amount threshold" in result["explanation"]


def test_explanation_includes_historical_average_and_ratio():
    transaction = {"timestamp": "2022/08/05 10:00", "sender_id": "S1", "receiver_id": "R2", "amount": 3000}
    history = [
        {"timestamp": "2022/08/04 10:00", "sender_id": "S1", "receiver_id": "R1", "amount": 1000},
        {"timestamp": "2022/08/03 10:00", "sender_id": "S1", "receiver_id": "R3", "amount": 2000},
    ]
    result = generate_detailed_aml_explanation(transaction, history)
    assert "Historical average transaction amount: 1,500.00" in result["explanation"]
    assert "Current amount / historical average: 2.00x" in result["explanation"]


def test_explanation_handles_missing_history_and_contains_disclaimer():
    transaction = {"timestamp": "2022/08/05 10:00", "sender_id": "S1", "receiver_id": "R1", "amount": 1000}
    result = generate_detailed_aml_explanation(transaction, [])
    assert "No previous transactions for this sender were supplied" in result["explanation"]
    assert "not proof of money laundering" in result["explanation"]


def test_supplied_analysis_score_and_level_are_used():
    transaction = {"timestamp": "2022/08/05 10:00", "sender_id": "S1", "receiver_id": "R1", "amount": 1000}
    result = generate_detailed_aml_explanation(
        transaction, analysis_result={"aml_score": 0.82, "risk_level": "HIGH"}
    )
    assert result["aml_score"] == 0.82
    assert result["risk_level"] == "HIGH"
    assert "AML risk score: 0.8200 (82.00%)" in result["explanation"]
