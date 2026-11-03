"""Reproduce the 10 PaySim test vectors with the saved backend models.

Run from code/:
    python -u ml/tests/test_paysim_scenarios.py

LOW / REVIEW / HIGH are scenario labels from the supplied document, not
ground-truth labels. Model outputs are captured as-is and compared with the
provided actual-results report at its four-decimal display precision.
"""
import csv
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = CODE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.ml_service import FEATURE_ORDER, MLService, build_features


MODELS = ("logistic_regression", "random_forest", "xgboost")
EXPECTED = {
    "PAY_01": (0.0000, 0.0000, 0.0000),
    "PAY_02": (0.4256, 0.0000, 0.0000),
    "PAY_03": (0.7651, 0.0000, 0.0000),
    "PAY_04": (0.0000, 0.0000, 0.0000),
    "PAY_05": (0.8899, 0.0000, 0.0000),
    "PAY_06": (0.9561, 0.0000, 0.0000),
    "PAY_07": (0.9991, 0.8500, 0.9990),
    "PAY_08": (0.0000, 0.0000, 0.0000),
    "PAY_09": (1.0000, 0.8100, 0.9844),
    "PAY_10": (1.0000, 0.8500, 0.9999),
}

CASES = [
    ("PAY_01", "Normal small payment", "LOW", {"step": 100, "type": "PAYMENT", "amount": 500, "oldbalanceOrg": 10000, "newbalanceOrig": 9500, "oldbalanceDest": 5000, "newbalanceDest": 5500, "isFlaggedFraud": 0}),
    ("PAY_02", "Normal cash withdrawal", "LOW", {"step": 120, "type": "CASH_OUT", "amount": 2000, "oldbalanceOrg": 15000, "newbalanceOrig": 13000, "oldbalanceDest": 0, "newbalanceDest": 0, "isFlaggedFraud": 0}),
    ("PAY_03", "Normal money transfer", "LOW", {"step": 150, "type": "TRANSFER", "amount": 5000, "oldbalanceOrg": 20000, "newbalanceOrig": 15000, "oldbalanceDest": 10000, "newbalanceDest": 15000, "isFlaggedFraud": 0}),
    ("PAY_04", "Cash deposit (inconsistent destination)", "LOW (provisional)", {"step": 180, "type": "CASH_IN", "amount": 3000, "oldbalanceOrg": 5000, "newbalanceOrig": 8000, "oldbalanceDest": 10000, "newbalanceDest": 7000, "isFlaggedFraud": 0}),
    ("PAY_05", "Large transfer with sufficient balance", "REVIEW", {"step": 250, "type": "TRANSFER", "amount": 75000, "oldbalanceOrg": 100000, "newbalanceOrig": 25000, "oldbalanceDest": 50000, "newbalanceDest": 125000, "isFlaggedFraud": 0}),
    ("PAY_06", "Large cash withdrawal", "REVIEW", {"step": 300, "type": "CASH_OUT", "amount": 90000, "oldbalanceOrg": 100000, "newbalanceOrig": 10000, "oldbalanceDest": 0, "newbalanceDest": 0, "isFlaggedFraud": 0}),
    ("PAY_07", "Entire sender balance transferred", "HIGH", {"step": 350, "type": "TRANSFER", "amount": 500000, "oldbalanceOrg": 500000, "newbalanceOrig": 0, "oldbalanceDest": 10000, "newbalanceDest": 510000, "isFlaggedFraud": 0}),
    ("PAY_08", "Transfer exceeds sender balance", "HIGH", {"step": 400, "type": "TRANSFER", "amount": 900000, "oldbalanceOrg": 300000, "newbalanceOrig": 0, "oldbalanceDest": 10000, "newbalanceDest": 910000, "isFlaggedFraud": 0}),
    ("PAY_09", "Flagged large transfer", "HIGH", {"step": 450, "type": "TRANSFER", "amount": 200000, "oldbalanceOrg": 200000, "newbalanceOrig": 0, "oldbalanceDest": 5000, "newbalanceDest": 205000, "isFlaggedFraud": 1}),
    ("PAY_10", "Very large account-draining transfer", "HIGH", {"step": 500, "type": "TRANSFER", "amount": 900000, "oldbalanceOrg": 900000, "newbalanceOrig": 0, "oldbalanceDest": 10000, "newbalanceDest": 910000, "isFlaggedFraud": 0}),
]


def main():
    service = MLService()
    if not service.is_ready:
        print(f"FAIL: models unavailable: {service.load_error or 'no models loaded'}")
        return 1
    unavailable = [name for name in MODELS if name not in service.models]
    if unavailable:
        print(f"FAIL: required saved models unavailable: {', '.join(unavailable)}")
        return 1

    rows = []
    all_match = True
    print("Case   Scenario                                      Logistic Reg.   Random Forest   XGBoost   Report match")
    for case_id, name, expected_category, transaction in CASES:
        probabilities = []
        predictions = []
        for model_name in MODELS:
            with redirect_stdout(io.StringIO()):
                result = service.predict(transaction, model_name)
            probabilities.append(result["fraud_score"])
            predictions.append(result["prediction"])

        case_match = all(round(p, 4) == expected for p, expected in zip(probabilities, EXPECTED[case_id]))
        all_match &= case_match
        print(f"{case_id:<6} {name:<46} " + "   ".join(f"{p:.4f} / {pred}" for p, pred in zip(probabilities, predictions)) + f"   {'MATCH' if case_match else 'DIFF'}")

        features = build_features(transaction)
        feature_values = {key: float(features.iloc[0][key]) for key in FEATURE_ORDER}
        for index, model_name in enumerate(MODELS):
            probability = probabilities[index]
            prediction = predictions[index]
            rows.append({
                "case": case_id,
                "scenario": name,
                "expected_scenario_category": expected_category,
                "model": model_name,
                "fraud_probability": probability,
                "probability_percent": round(probability * 100, 6),
                "prediction": prediction,
                "prediction_label": "FRAUD" if prediction else "NON-FRAUD",
                "matches_report_at_4dp": round(probability, 4) == EXPECTED[case_id][index],
                **transaction,
                **feature_values,
            })

    report_path = CODE_DIR / "ml" / "reports" / "paysim_scenario_results.csv"
    report_path.parent.mkdir(exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    matches = sum(row["matches_report_at_4dp"] for row in rows)
    print(f"\nPredictions: {len(rows)}; match supplied report: {matches}/{len(rows)} at four decimals.")
    print(f"Threshold: >= 0.50 is FRAUD; below 0.50 is NON-FRAUD.")
    print(f"CSV with raw outputs and engineered features: {report_path}")
    if not all_match:
        print("One or more outputs differ from the supplied report; see the CSV for actual model outputs.")
        return 1
    print("All saved-model predictions match the supplied report at four decimals.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
