import os
import joblib
import pandas as pd
import numpy as np

from features import create_features

from pathlib import Path

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent  # points to .../finshield_ai/code/ml/src
MODELS_DIR = BASE_DIR.parent / "models"     # points to .../finshield_ai/code/ml/models

MODEL_PATH = MODELS_DIR / "paysim_xgboost.pkl"
FEATURE_PATH = MODELS_DIR / "paysim_features.txt"
SCALER_PATH = MODELS_DIR / "paysim_scaler.pkl"

# (If your scaler is also loaded here, update it similarly):
# SCALER_PATH = BASE_DIR.parent / "models" / "paysim_scaler.pkl"


# --------------------------------------------------
# Paths
# --------------------------------------------------

# MODEL_PATH = "../models/paysim_xgboost.pkl"
# FEATURE_PATH = "../models/paysim_features.txt"


# --------------------------------------------------
# Load model
# --------------------------------------------------

def load_model():
    """
    Load the trained XGBoost model.
    """

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}"
        )

    return joblib.load(MODEL_PATH)


# --------------------------------------------------
# Load feature names
# --------------------------------------------------

def load_features():
    """
    Load the exact feature order used during training.
    """

    if not os.path.exists(FEATURE_PATH):
        raise FileNotFoundError(
            f"Feature file not found: {FEATURE_PATH}"
        )

    with open(FEATURE_PATH, "r") as file:
        features = [
            line.strip()
            for line in file
            if line.strip()
        ]

    return features


# --------------------------------------------------
# Prepare transaction
# --------------------------------------------------

def prepare_transaction(transaction):
    """
    Convert a transaction dictionary into
    model-ready features.
    """

    df = pd.DataFrame([transaction])

    # Create engineered features
    df = create_features(df)

    # One-hot encode transaction type
    df = pd.get_dummies(
        df,
        columns=["type"],
        prefix="type",
        dtype="int8"
    )

    return df


# --------------------------------------------------
# Align features
# --------------------------------------------------

def align_features(df, feature_names):
    """
    Make sure the prediction data has exactly
    the same features and order as training.
    """

    df = df.copy()

    # Add missing features
    for feature in feature_names:

        if feature not in df.columns:
            df[feature] = 0

    # Keep only training features
    df = df[feature_names]

    return df


# --------------------------------------------------
# Predict
# --------------------------------------------------

def predict_transaction(transaction):

    model = load_model()
    
    feature_names = load_features()


    print("=============================\n")    
    """
    Predict whether a transaction is fraudulent.

    Returns:
        fraud_probability
        risk_score
        prediction
        risk_level
    """

    # Prepare transaction
    df = prepare_transaction(
        transaction
    )

    # Align features
    df = align_features(
        df,
        feature_names
    )

    # Get fraud probability
    fraud_probability = model.predict_proba(
        df
    )[0][1]

    # Convert probability to risk score
    risk_score = round(
        fraud_probability * 100,
        2
    )

    # Classification
    prediction = int(
        fraud_probability >= 0.5
    )

    # Risk level
    if risk_score >= 70:
        risk_level = "HIGH"

    elif risk_score >= 40:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    print("\n===== DEBUG INFORMATION =====")
    
    print("Features expected by model:")
    print(feature_names)
    
    print("\nFeatures generated for transaction:")
    print(df.columns.tolist())
    
    print("\nInput values:")
    print(df)
    
    print("\nPrediction probabilities:")
    print(model.predict_proba(df))

    return {
        "fraud_probability": round(
            float(fraud_probability),
            4
        ),
        "risk_score": risk_score,
        "prediction": prediction,
        "risk_level": risk_level
    }
    


# --------------------------------------------------
# Example
# --------------------------------------------------

if __name__ == "__main__":

    transaction = {
    "step": 500,
    "type": "TRANSFER",
    "amount": 90000,
    "nameOrig": "C123456789",
    "oldbalanceOrg": 900000,
    "newbalanceOrig": 0,
    "nameDest": "C987654321",
    "oldbalanceDest": 0,
    "newbalanceDest": 0,
    "isFlaggedFraud": 1
}

    result = predict_transaction(
        transaction
    )

    print(
        "================================="
    )

    print(
        "       FINSHIELD AI"
    )

    print(
        "   FRAUD DETECTION SYSTEM"
    )

    print(
        "================================="
    )

    print(
        f"Fraud Probability: "
        f"{result['fraud_probability']}"
    )

    print(
        f"Risk Score: "
        f"{result['risk_score']}/100"
    )

    print(
        f"Prediction: "
        f"{'FRAUD' if result['prediction'] else 'NON-FRAUD'}"
    )

    print(
        f"Risk Level: "
        f"{result['risk_level']}"
    )