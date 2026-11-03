"""
Transaction endpoints.

This is where the three members meet: a transaction is stored, sent to
Member 2's ML model, sent to Member 4's AML module, combined into a hybrid
score, and turned into an alert when the risk is not LOW.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models import (
    ROLE_ADMIN,
    ROLE_ANALYST,
    ROLE_COMPLIANCE,
    Alert,
    RiskResult,
    Transaction,
    User,
)
from app.risk import combine_scores, risk_level
from app.schemas import (
    ExplanationOut,
    TransactionAnalysisOut,
    TransactionCreate,
    TransactionOut,
)
from app.services import aml_service
from app.services.ml_service import ml_service
from app import risk

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])

STAFF_ROLES = (ROLE_ANALYST, ROLE_COMPLIANCE, ROLE_ADMIN)
VALID_TYPES = ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]


def _to_ml_dict(transaction: Transaction) -> dict:
    """Transaction row -> the PaySim field names Member 2's model expects."""
    return {
        "step": transaction.step,
        "type": transaction.txn_type,
        "amount": transaction.amount,
        "oldbalanceOrg": transaction.oldbalance_org,
        "newbalanceOrig": transaction.newbalance_orig,
        "oldbalanceDest": transaction.oldbalance_dest,
        "newbalanceDest": transaction.newbalance_dest,
        "isFlaggedFraud": transaction.is_flagged_fraud,
    }


def run_analysis(
    db: Session,
    transaction: Transaction,
    commit: bool = True,
) -> tuple[RiskResult, dict | None]:
    """Run ML + AML on a transaction, save the result and create an alert."""
    ml_result = ml_service.predict(_to_ml_dict(transaction))
    aml_result = aml_service.analyze(db, transaction)

    ml_score = ml_result.get("fraud_score") if ml_result.get("available") else None
    aml_score = aml_result.get("aml_score") if aml_result.get("available") else None

    final_score = combine_scores(ml_score, aml_score)
    level = risk_level(final_score)

    # SHAP explanation, stored so the frontend can show it without recomputing.
    explanation = ml_service.explain(_to_ml_dict(transaction))

    risk = RiskResult(
        transaction_id=transaction.id,
        ml_model_used=ml_result.get("model_used"),
        ml_fraud_score=ml_score,
        ml_prediction=ml_result.get("prediction"),
        shap_available=bool(explanation.get("available")),
        shap_base_value=explanation.get("base_value"),
        shap_top_features=explanation.get("top_features"),
        aml_score=aml_score,
        aml_risk_level=aml_result.get("risk_level"),
        rule_score=aml_result.get("rule_score"),
        behavior_score=aml_result.get("behavior_score"),
        network_score=aml_result.get("network_score"),
        triggered_rules=aml_result.get("triggered_rules"),
        reasons=aml_result.get("reasons"),
        investigation_summary=aml_result.get("investigation_summary"),
        final_risk_score=final_score,
        risk_level=level,
    )
    db.add(risk)

    notification = aml_result.get("notification")
    existing_alert = (
        db.query(Alert)
        .filter(Alert.transaction_id == transaction.id)
        .first()
    )
    if level != "LOW":
        reasons = aml_result.get("reasons") or []
        message = (
            f"{level} risk transaction {transaction.txn_ref} "
            f"(score {final_score:.2f}). " + " ".join(reasons[:2])
        ).strip()
        if existing_alert is None:
            db.add(
                Alert(
                    transaction_id=transaction.id,
                    risk_level=level,
                    final_risk_score=final_score,
                    message=message,
                )
            )
        else:
            # Preserve the alert and its investigation/case relationship.
            existing_alert.risk_level = level
            existing_alert.final_risk_score = final_score
            existing_alert.message = message
    elif existing_alert is not None and existing_alert.case is None:
        # Remove stale, unlinked alerts if a re-analysis lowers risk to LOW.
        db.delete(existing_alert)

    if commit:
        db.commit()
    else:
        db.flush()

    db.refresh(risk)

    return risk, {
        "notification": notification,
        "aml_explanation": aml_result.get("detailed_explanation"),
        "aml_explanation_details": aml_result.get("explanation_details"),
    }


@router.post("", response_model=TransactionAnalysisOut, status_code=status.HTTP_201_CREATED)
def submit_transaction(
    payload: TransactionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a transaction and get its fraud score, AML score and risk level.

    Any logged-in user may submit. The response contains everything the
    investigation screen needs.
    """
    if payload.type.upper() not in VALID_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"type must be one of {', '.join(VALID_TYPES)}.",
        )

    transaction = Transaction(
        txn_ref=f"TXN-{uuid.uuid4().hex[:10].upper()}",
        step=payload.step,
        txn_type=payload.type.upper(),
        amount=payload.amount,
        name_orig=payload.nameOrig,
        oldbalance_org=payload.oldbalanceOrg,
        newbalance_orig=payload.newbalanceOrig,
        name_dest=payload.nameDest,
        oldbalance_dest=payload.oldbalanceDest,
        newbalance_dest=payload.newbalanceDest,
        is_flagged_fraud=payload.isFlaggedFraud,
        currency=payload.currency,
        timestamp=payload.timestamp or datetime.utcnow(),
        submitted_by_id=current_user.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    risk, analysis_extras = run_analysis(db, transaction)
    notification = analysis_extras["notification"]

    write_audit(
        db,
        action="TRANSACTION_ANALYSED",
        user=current_user,
        entity_type="Transaction",
        entity_id=transaction.id,
        details={
            "txn_ref": transaction.txn_ref,
            "amount": transaction.amount,
            "risk_level": risk.risk_level,
            "final_risk_score": risk.final_risk_score,
        },
        ip_address=request.client.host if request.client else None,
    )

    alert = db.query(Alert).filter(Alert.transaction_id == transaction.id).first()
    return TransactionAnalysisOut(
    transaction=transaction,
    risk=risk,
    alert_id=alert.id if alert else None,
    notification=notification,
    aml_explanation=analysis_extras["aml_explanation"],
    aml_explanation_details=analysis_extras["aml_explanation_details"],
)


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    risk_level_filter: str | None = Query(
        None, alias="risk_level", description="LOW, MEDIUM or HIGH"
    ),
):
    """
    List transactions.

    A CUSTOMER only sees the transactions they submitted. Analysts, compliance
    officers and admins see everything.
    """
    query = db.query(Transaction)
    if current_user.role not in STAFF_ROLES:
        query = query.filter(Transaction.submitted_by_id == current_user.id)
    if risk_level_filter:
        query = query.join(RiskResult).filter(
            RiskResult.risk_level == risk_level_filter.upper()
        )
    return (
        query.order_by(Transaction.created_at.desc()).offset(skip).limit(limit).all()
    )


@router.get("/{transaction_id}", response_model=TransactionAnalysisOut)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full detail of one transaction, including its risk breakdown."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    if (
        current_user.role not in STAFF_ROLES
        and transaction.submitted_by_id != current_user.id
    ):
        raise HTTPException(
            status_code=403, detail="You can only view your own transactions."
        )
    if transaction.risk_result is None:
        raise HTTPException(
            status_code=404, detail="This transaction has not been analysed yet."
        )

    alert = db.query(Alert).filter(Alert.transaction_id == transaction.id).first()
    return TransactionAnalysisOut(
        transaction=transaction,
        risk=transaction.risk_result,
        alert_id=alert.id if alert else None,
    )


@router.get("/{transaction_id}/explanation", response_model=ExplanationOut)
def get_explanation(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*STAFF_ROLES)),
):
    """
    SHAP explanation for the ML prediction.

    The stored explanation is returned when it exists, otherwise it is
    calculated again from Member 2's model.
    """
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    risk = transaction.risk_result
    if risk and risk.shap_available and risk.shap_top_features:
        return ExplanationOut(
            transaction_id=transaction.id,
            available=True,
            explainer_model="xgboost",
            base_value=risk.shap_base_value,
            top_features=risk.shap_top_features,
        )

    explanation = ml_service.explain(_to_ml_dict(transaction))
    return ExplanationOut(
        transaction_id=transaction.id,
        available=explanation.get("available", False),
        explainer_model=explanation.get("explainer_model"),
        base_value=explanation.get("base_value"),
        top_features=explanation.get("top_features", []),
        error=explanation.get("error"),
    )


@router.post("/{transaction_id}/reanalyse", response_model=TransactionAnalysisOut)
def reanalyse_transaction(
    transaction_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ANALYST, ROLE_ADMIN)),
):
    """Run the ML and AML analysis again, for example after new history arrives."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    if transaction.risk_result:
        db.delete(transaction.risk_result)
    existing_alert = db.query(Alert).filter(Alert.transaction_id == transaction.id).first()
    if existing_alert and existing_alert.case is None:
        db.delete(existing_alert)
    db.commit()

    risk, analysis_extras = run_analysis(db, transaction)
    notification = analysis_extras["notification"]
    write_audit(
        db,
        action="TRANSACTION_REANALYSED",
        user=current_user,
        entity_type="Transaction",
        entity_id=transaction.id,
        details={"risk_level": risk.risk_level},
        ip_address=request.client.host if request.client else None,
    )
    alert = db.query(Alert).filter(Alert.transaction_id == transaction.id).first()
    return TransactionAnalysisOut(
    transaction=transaction,
    risk=risk,
    alert_id=alert.id if alert else None,
    notification=notification,
    aml_explanation=analysis_extras["aml_explanation"],
    aml_explanation_details=analysis_extras["aml_explanation_details"],
)
