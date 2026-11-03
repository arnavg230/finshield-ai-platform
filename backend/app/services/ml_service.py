"""
Wrapper around Member 2's trained PaySim models.

Member 2 supplied four pickle files and no code, so this module only does what
is needed to call those files correctly:

  * builds the 18 features the models were trained on, in the exact order
    stored in the scaler's `feature_names_in_`
  * sends raw (unscaled) features to Random Forest and XGBoost, because their
    tree split thresholds are in rupee/amount units, not standard-deviation units
  * sends scaled features to Logistic Regression, which needs the scaler
  * uses SHAP's TreeExplainer on the XGBoost model for explanations

Nothing here retrains or replaces Member 2's work.
"""
from pyexpat import features
import warnings
from xml.parsers.expat import model

import joblib
import pandas as pd

from app.config import ML_MODEL_NAME, ML_MODELS_DIR

warnings.filterwarnings("ignore")

# Exact training order taken from paysim_scaler.feature_names_in_
FEATURE_ORDER = [
    "step",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "isFlaggedFraud",
    "origin_balance_change",
    "destination_balance_change",
    "origin_error",
    "destination_error",
    "amount_to_origin_balance",
    "amount_to_destination_balance",
    "type_CASH_IN",
    "type_CASH_OUT",
    "type_DEBIT",
    "type_PAYMENT",
    "type_TRANSFER",
]

TRANSACTION_TYPES = ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]

MODEL_FILES = {
    "logistic_regression": "paysim_logistic_regression.pkl",
    "random_forest": "paysim_random_forest.pkl",
    "xgboost": "paysim_xgboost.pkl",
}

# Only Logistic Regression was trained on scaled inputs.
NEEDS_SCALING = {"logistic_regression"}


def build_features(transaction: dict) -> pd.DataFrame:
    """
    Turn one transaction into the single-row feature frame the models expect.

    `transaction` uses the PaySim column names:
    step, type, amount, oldbalanceOrg, newbalanceOrig, oldbalanceDest,
    newbalanceDest, isFlaggedFraud.
    """
    amount = float(transaction.get("amount", 0.0))
    old_org = float(transaction.get("oldbalanceOrg", 0.0))
    new_org = float(transaction.get("newbalanceOrig", 0.0))
    old_dest = float(transaction.get("oldbalanceDest", 0.0))
    new_dest = float(transaction.get("newbalanceDest", 0.0))

    row = {
        "step": float(transaction.get("step", 1)),
        "amount": amount,
        "oldbalanceOrg": old_org,
        "newbalanceOrig": new_org,
        "oldbalanceDest": old_dest,
        "newbalanceDest": new_dest,
        "isFlaggedFraud": float(transaction.get("isFlaggedFraud", 0)),
        # Derived features (formulas confirmed against the scaler's stored means)
        "origin_balance_change": old_org - new_org,
        "destination_balance_change": new_dest - old_dest,
        "origin_error": new_org + amount - old_org,
        "destination_error": old_dest + amount - new_dest,
        "amount_to_origin_balance": amount / (old_org + 1.0),
        "amount_to_destination_balance": amount / (old_dest + 1.0),
    }

    txn_type = str(transaction.get("type", "")).upper()
    for name in TRANSACTION_TYPES:
        row[f"type_{name}"] = 1.0 if txn_type == name else 0.0

    return pd.DataFrame([[row[col] for col in FEATURE_ORDER]], columns=FEATURE_ORDER)


class MLService:
    """Loads Member 2's pickles once and serves predictions."""

    def __init__(self):
        self.models = {}
        self.scaler = None
        self.explainer = None
        self.load_error = None
        self._load()

    def _load(self):
        try:
            self.scaler = joblib.load(ML_MODELS_DIR / "paysim_scaler.pkl")
            for name, filename in MODEL_FILES.items():
                path = ML_MODELS_DIR / filename
                if path.exists():
                    self.models[name] = joblib.load(path)
        except Exception as exc:                      # noqa: BLE001
            self.load_error = f"{type(exc).__name__}: {exc}"

    @property
    def is_ready(self) -> bool:
        return bool(self.models) and self.scaler is not None

    def available_models(self) -> list[str]:
        return sorted(self.models.keys())

    def predict(self, transaction: dict, model_name: str | None = None) -> dict:
        """Return the fraud probability for one transaction."""
        model_name = model_name or ML_MODEL_NAME
        if not self.is_ready:
            return {
                "available": False,
                "error": self.load_error or "ML models are not loaded.",
            }
        if model_name not in self.models:
            return {"available": False, "error": f"Unknown model '{model_name}'."}

        features = build_features(transaction)
        if model_name in NEEDS_SCALING:
            features = pd.DataFrame(
                self.scaler.transform(features), columns=FEATURE_ORDER
            )

        model = self.models[model_name]
        print("MODEL CLASSES:", model.classes_, flush=True)

        raw_probabilities = model.predict_proba(features)
        print("RAW PROBABILITIES:", raw_probabilities, flush=True)

        probability = float(raw_probabilities[0][1])
        return {
            "available": True,
            "model_used": model_name,
            "fraud_score": round(probability, 8),
            "prediction": int(probability >= 0.5),
        }

    def explain(self, transaction: dict, top_n: int = 8) -> dict:
        """
        SHAP explanation for one transaction.

        XGBoost is always used here because SHAP's TreeExplainer is fast on it,
        and it is one of the models Member 2 trained.
        """
        if "xgboost" not in self.models:
            return {"available": False, "error": "XGBoost model is not loaded."}
        try:
            import shap
        except ImportError:
            return {"available": False, "error": "shap package is not installed."}

        try:
            if self.explainer is None:
                self.explainer = shap.TreeExplainer(self.models["xgboost"])

            features = build_features(transaction)
            shap_values = self.explainer.shap_values(features)[0]
            base_value = float(self.explainer.expected_value)

            contributions = []
            for index, feature_name in enumerate(FEATURE_ORDER):
                contributions.append(
                    {
                        "feature": feature_name,
                        "value": round(float(features.iloc[0, index]), 4),
                        "shap_value": round(float(shap_values[index]), 4),
                        "direction": "increases_risk"
                        if shap_values[index] > 0
                        else "decreases_risk",
                    }
                )
            contributions.sort(key=lambda item: abs(item["shap_value"]), reverse=True)

            return {
                "available": True,
                "explainer_model": "xgboost",
                "base_value": round(base_value, 4),
                "top_features": contributions[:top_n],
            }
        except Exception as exc:                      # noqa: BLE001
            return {"available": False, "error": f"{type(exc).__name__}: {exc}"}


# One shared instance for the whole application.
ml_service = MLService()
