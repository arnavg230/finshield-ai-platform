"""Summary numbers for the dashboard (Member 3 will call this)."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_roles
from app.models import (
    ROLE_ADMIN,
    ROLE_ANALYST,
    ROLE_COMPLIANCE,
    Alert,
    Case,
    RiskResult,
    Transaction,
    User,
)
from app.schemas import AnalyticsSummary

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(ROLE_ANALYST, ROLE_COMPLIANCE, ROLE_ADMIN)
    ),
):
    """Counts and averages used by the dashboard cards."""
    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0
    total_amount = db.query(func.coalesce(func.sum(Transaction.amount), 0.0)).scalar()
    average_risk = db.query(func.coalesce(func.avg(RiskResult.final_risk_score), 0.0)).scalar()

    alerts_by_level = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for level, count in db.query(Alert.risk_level, func.count(Alert.id)).group_by(
        Alert.risk_level
    ):
        alerts_by_level[level] = count

    cases_by_status = {status: 0 for status in Case.ALL_STATUSES}
    for case_status, count in db.query(Case.status, func.count(Case.id)).group_by(
        Case.status
    ):
        cases_by_status[case_status] = count

    open_alerts = (
        db.query(func.count(Alert.id)).filter(Alert.status == Alert.ALERT_OPEN).scalar()
    )
    ml_flagged = (
        db.query(func.count(RiskResult.id))
        .filter(RiskResult.ml_prediction == 1)
        .scalar()
    )

    return AnalyticsSummary(
        total_transactions=total_transactions,
        total_amount=round(float(total_amount), 2),
        alerts_by_level=alerts_by_level,
        open_alerts=open_alerts or 0,
        cases_by_status=cases_by_status,
        average_risk_score=round(float(average_risk), 4),
        ml_flagged_count=ml_flagged or 0,
    )
