"""
Hybrid risk scoring (Member 1).

Member 2 returns a fraud probability from the PaySim model.
Member 4 returns an AML score that already blends its rule, behaviour and
network sub-scores. This module combines those two numbers into the single
score the dashboard and the alert queue are sorted by.

    final = ML_WEIGHT * ml_score + AML_WEIGHT * aml_score

If one side is missing (for example the ML models were not loaded), the other
side is used on its own instead of silently scoring the transaction as zero.
"""
from app.config import (
    AML_WEIGHT,
    HIGH_RISK_THRESHOLD,
    MEDIUM_RISK_THRESHOLD,
    ML_WEIGHT,
)


def combine_scores(ml_score: float | None, aml_score: float | None) -> float:
    if ml_score is None and aml_score is None:
        return 0.0
    if ml_score is None:
        return round(float(aml_score), 4)
    if aml_score is None:
        return round(float(ml_score), 4)

    total_weight = ML_WEIGHT + AML_WEIGHT
    score = (ml_score * ML_WEIGHT + aml_score * AML_WEIGHT) / total_weight
    return round(max(0.0, min(1.0, score)), 4)


def risk_level(score: float) -> str:
    if score >= HIGH_RISK_THRESHOLD:
        return "HIGH"
    if score >= MEDIUM_RISK_THRESHOLD:
        return "MEDIUM"
    return "LOW"
