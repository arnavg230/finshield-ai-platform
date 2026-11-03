
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap


ML_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ML_DIR / "models" / "paysim_xgboost.pkl"
FEATURE_PATH = ML_DIR / "models" / "paysim_features.txt"


def load_shap_explainer():
    """Load the trained PaySim model and its SHAP explainer."""

    model = joblib.load(MODEL_PATH)

    with open(FEATURE_PATH, "r") as file:
        feature_names = [
            line.strip()
            for line in file
            if line.strip()
        ]

    explainer = shap.TreeExplainer(model)

    return model, explainer, feature_names


def explain_transaction(model, explainer, feature_names, transaction_df):
    """Explain one transaction already prepared for the model."""

    if len(transaction_df) != 1:
        raise ValueError("Provide exactly one transaction.")

    missing = [
        feature for feature in feature_names
        if feature not in transaction_df.columns
    ]

    if missing:
        raise ValueError(f"Missing features: {missing}")

    X = transaction_df[feature_names].copy()
    X = X.replace([np.inf, -np.inf], np.nan)

    if X.isna().any().any():
        raise ValueError("Input contains missing or infinite values.")

    probability = float(model.predict_proba(X)[0, 1])
    explanation = explainer(X)

    contributions = pd.DataFrame({
        "feature": feature_names,
        "feature_value": X.iloc[0].values,
        "shap_value": explanation.values[0]
    })

    contributions["absolute_impact"] = (
        contributions["shap_value"].abs()
    )

    contributions["direction"] = np.where(
        contributions["shap_value"] > 0,
        "Pushes toward fraud",
        np.where(
            contributions["shap_value"] < 0,
            "Pushes away from fraud",
            "No contribution"
        )
    )

    contributions = contributions.sort_values(
        "absolute_impact",
        ascending=False
    )

    return {
        "fraud_probability": round(probability, 6),
        "risk_score": round(probability * 100, 2),
        "top_features": contributions.head(10).to_dict(
            orient="records"
        ),
        "shap_values": explanation
    }


def print_text_explanation(result):
    """Print a readable SHAP explanation for a transaction."""

    descriptions = {
        "amount": "Transaction amount",
        "oldbalanceOrg": "Sender balance before transaction",
        "newbalanceOrig": "Sender balance after transaction",
        "oldbalanceDest": "Receiver balance before transaction",
        "newbalanceDest": "Receiver balance after transaction",
        "isFlaggedFraud": "Existing fraud flag",
        "origin_balance_change": "Change in sender balance",
        "destination_balance_change": "Change in receiver balance",
        "origin_error": "Sender balance difference",
        "destination_error": "Receiver balance difference",
        "amount_to_origin_balance": "Amount relative to sender balance",
        "amount_to_destination_balance": "Amount relative to receiver balance",
        "type_TRANSFER": "Transfer transaction type",
        "type_CASH_IN": "Cash-in transaction type",
        "type_CASH_OUT": "Cash-out transaction type",
        "type_DEBIT": "Debit transaction type",
        "type_PAYMENT": "Payment transaction type",
        "step": "Transaction time step"
    }

    print("\nFINSHIELD AI - TRANSACTION EXPLANATION")
    print("=" * 48)
    print(f"Fraud probability: {result['fraud_probability']:.2%}")
    print(f"Risk score: {result['risk_score']}/100")
    print("\nTop contributing features:")

    for item in result["top_features"][:5]:
        name = descriptions.get(item["feature"], item["feature"])
        value = item["shap_value"]

        if value > 0:
            direction = "pushed the prediction toward fraud"
        elif value < 0:
            direction = "pushed the prediction away from fraud"
        else:
            direction = "had negligible influence"

        print(f"- {name}: {direction} (SHAP value: {value:.4f})")
