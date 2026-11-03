"""Run the 15 AML functional scenarios from the FinShield test specification.

Run from the repository root with:
    python code/ml/test_aml_scenarios_15.py

The histories are deliberately built from the scenario descriptions (including
timestamps outside the 24-hour window where a case is meant to isolate other
signals). Reports are written under ml/reports/.
"""
import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ML_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ML_DIR))

from src.analysis_aml import analyze_aml
from src.explanation_aml import generate_detailed_aml_explanation

BASE = datetime(2026, 10, 29, 10, 0)


def tx(sender, receiver, amount, when=BASE):
    return {
        "timestamp": when.strftime("%Y/%m/%d %H:%M"),
        "sender_id": sender,
        "receiver_id": receiver,
        "amount": amount,
        "currency": "USD",
        "payment_type": "TRANSFER",
    }


def ago(hours, sender, receiver, amount):
    return tx(sender, receiver, amount, BASE - timedelta(hours=hours))


def scenarios():
    cases = []

    def add(number, name, current, history, checks):
        cases.append({"number": number, "name": name, "transaction": current,
                      "history": history, "checks": checks})

    add(1, "Normal low-value transaction", tx("SENDER_01", "RECEIVER_01", 500), [],
        {"not_rules": ["HIGH_AMOUNT", "HIGH_FREQUENCY", "NEW_RECEIVER_LARGE_AMOUNT"], "behavior": .20, "risk": "LOW"})
    add(2, "Just below high-amount threshold", tx("SENDER_02", "RECEIVER_02", 99999), [],
        {"not_rules": ["HIGH_AMOUNT"], "risk": "LOW"})
    add(3, "At high-amount threshold", tx("SENDER_03", "RECEIVER_03", 100000), [],
        {"rules": ["HIGH_AMOUNT", "NEW_RECEIVER_LARGE_AMOUNT"]})
    add(4, "New receiver below large-transfer threshold", tx("SENDER_04", "RECEIVER_04", 49999),
        [ago(48, "SENDER_04", "OTHER_04A", 30000), ago(72, "SENDER_04", "OTHER_04B", 30000)],
        {"not_rules": ["HIGH_AMOUNT", "HIGH_FREQUENCY", "NEW_RECEIVER_LARGE_AMOUNT", "SUDDEN_ACTIVITY_SPIKE"], "behavior": 0.0})
    add(5, "Large transfer to a new receiver", tx("SENDER_05", "RECEIVER_05", 60000),
        [ago(48, "SENDER_05", "OTHER_05A", 10000), ago(72, "SENDER_05", "OTHER_05B", 10000)],
        {"rules": ["NEW_RECEIVER_LARGE_AMOUNT", "SUDDEN_ACTIVITY_SPIKE"], "behavior": .90})
    add(6, "Four transactions within 24 hours", tx("SENDER_06", "RECEIVER_06", 1000),
        [ago(2, "SENDER_06", "R06A", 1000), ago(5, "SENDER_06", "R06B", 1000), ago(8, "SENDER_06", "R06C", 1000)],
        {"not_rules": ["HIGH_FREQUENCY"]})
    add(7, "Five transactions within 24 hours", tx("SENDER_07", "RECEIVER_07", 1000),
        [ago(2, "SENDER_07", "R07A", 1000), ago(5, "SENDER_07", "R07B", 1000), ago(8, "SENDER_07", "R07C", 1000), ago(11, "SENDER_07", "R07D", 1000)],
        {"rules": ["HIGH_FREQUENCY"]})
    add(8, "Behaviour ratio 2x", tx("SENDER_08", "RECEIVER_08", 2000),
        [ago(48, "SENDER_08", "OLD_08", 1000)],
        {"not_rules": ["SUDDEN_ACTIVITY_SPIKE"], "behavior": .45})
    add(9, "Behaviour ratio 3x", tx("SENDER_09", "RECEIVER_09", 3000),
        [ago(48, "SENDER_09", "OLD_09", 1000)],
        {"rules": ["SUDDEN_ACTIVITY_SPIKE"], "behavior": .70})
    add(10, "Behaviour ratio 5x", tx("SENDER_10", "RECEIVER_10", 5000),
        [ago(48, "SENDER_10", "OLD_10", 1000)],
        {"rules": ["SUDDEN_ACTIVITY_SPIKE"], "behavior": .90})
    add(11, "Sender connected to multiple receivers", tx("SENDER_11", "RECEIVER_11_NEW", 2000),
        [ago(48 + 24*i, "SENDER_11", f"R11_{i}", 1000) for i in range(5)],
        {"not_rules": ["HIGH_FREQUENCY"], "network": .60})
    add(12, "Receiver connected to multiple senders", tx("SENDER_12", "RECEIVER_12", 2000),
        [ago(48 + 24*i, f"OTHER_12_{i}", "RECEIVER_12", 1000) for i in range(5)],
        {"not_rules": ["HIGH_FREQUENCY"], "network": .30})
    add(13, "Reciprocal transaction", tx("SENDER_13", "RECEIVER_13", 5000),
        [ago(48, "RECEIVER_13", "SENDER_13", 5000)],
        {"network": .40})
    add(14, "Combined high-risk indicators", tx("SENDER_14", "RECEIVER_14_NEW", 150000),
        [ago(2 + 2*i, "SENDER_14", f"R14_{i}", 1000) for i in range(5)],
        {"rules": ["HIGH_AMOUNT", "HIGH_FREQUENCY", "NEW_RECEIVER_LARGE_AMOUNT", "SUDDEN_ACTIVITY_SPIKE"], "risk": "HIGH"})
    add(15, "Stable customer activity", tx("SENDER_15", "RECEIVER_15", 1000),
        [ago(48 + 24*i, "SENDER_15", "RECEIVER_15", 1000) for i in range(10)],
        {"not_rules": ["HIGH_AMOUNT", "HIGH_FREQUENCY", "NEW_RECEIVER_LARGE_AMOUNT", "SUDDEN_ACTIVITY_SPIKE"], "behavior": .10, "risk": "LOW"})
    return cases


def validate(case, result):
    checks = case["checks"]
    errors = []
    rules = set(result["triggered_rules"])
    for name in checks.get("rules", []):
        if name not in rules:
            errors.append(f"missing rule {name}")
    for name in checks.get("not_rules", []):
        if name in rules:
            errors.append(f"unexpected rule {name}")
    for key in ("behavior", "network"):
        if key in checks and result[f"{key}_score"] != checks[key]:
            errors.append(f"{key} expected {checks[key]}, got {result[f'{key}_score']}")
    if "risk" in checks and result["risk_level"] != checks["risk"]:
        errors.append(f"risk expected {checks['risk']}, got {result['risk_level']}")
    detail = generate_detailed_aml_explanation(case["transaction"], case["history"], result)
    if detail["aml_score"] != result["aml_score"] or detail["risk_level"] != result["risk_level"]:
        errors.append("detailed explanation does not match analysis score/risk")
    expected_notify = result["risk_level"] != "LOW"
    if result["notification"]["should_notify"] != expected_notify:
        errors.append("notification expectation does not match risk level")
    return errors, detail


def main():
    rows, report = [], []
    passed = 0
    for case in scenarios():
        result = analyze_aml(case["transaction"], case["history"])
        errors, detail = validate(case, result)
        status = "PASS" if not errors else "FAIL"
        passed += status == "PASS"
        row = {"case": case["number"], "name": case["name"], "status": status,
               "aml_score": result["aml_score"], "risk_level": result["risk_level"],
               "rule_score": result["rule_score"], "behavior_score": result["behavior_score"],
               "network_score": result["network_score"],
               "triggered_rules": ";".join(result["triggered_rules"]),
               "should_notify": result["notification"]["should_notify"],
               "notification_channels": ";".join(result["notification"]["channels"]),
               "errors": "; ".join(errors)}
        rows.append(row)
        report.extend([
            f"TEST {case['number']:02d} - {case['name']} [{status}]",
            f"Sender/receiver: {case['transaction']['sender_id']} -> {case['transaction']['receiver_id']}",
            f"Amount: {case['transaction']['amount']:.2f} USD; history rows: {len(case['history'])}",
            f"AML score: {result['aml_score']:.4f}; risk: {result['risk_level']}",
            f"Rule/behavior/network: {result['rule_score']:.2f} / {result['behavior_score']:.2f} / {result['network_score']:.2f}",
            f"Triggered rules: {', '.join(result['triggered_rules']) or 'None'}",
            f"Reasons: {' | '.join(result['reasons'])}",
            f"Investigation summary: {result['investigation_summary']}",
            f"Notification: {json.dumps(result['notification'], ensure_ascii=False)}",
            detail["explanation"],
            ("Validation errors: " + "; ".join(errors)) if errors else "",
            "-" * 78,
        ])
        print(f"{status} {case['number']:02d} {case['name']}: score={result['aml_score']:.4f} {result['risk_level']} rules={','.join(result['triggered_rules']) or '-'}")
        if errors:
            print("  " + "; ".join(errors))

    report_dir = ML_DIR / "reports"
    report_dir.mkdir(exist_ok=True)
    csv_path = report_dir / "aml_scenario_results.csv"
    txt_path = report_dir / "aml_scenario_results.txt"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    report.extend(["", f"SUMMARY: {passed}/15 passed; {15-passed}/15 failed.",
                   f"CSV report: {csv_path}", f"Text report: {txt_path}"])
    txt_path.write_text("\n".join(report), encoding="utf-8")
    print(f"\nSUMMARY: {passed}/15 passed; {15-passed}/15 failed")
    print(f"Reports saved: {csv_path} and {txt_path}")
    return 0 if passed == 15 else 1


if __name__ == "__main__":
    raise SystemExit(main())
