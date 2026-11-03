"""Alert queue for analysts and compliance officers."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.deps import require_roles
from app.models import ROLE_ADMIN, ROLE_ANALYST, ROLE_COMPLIANCE, Alert, User
from app.schemas import AlertOut, AlertStatusUpdate

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

STAFF_ROLES = (ROLE_ANALYST, ROLE_COMPLIANCE, ROLE_ADMIN)


@router.get("", response_model=list[AlertOut])
def list_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*STAFF_ROLES)),
    status_filter: str | None = Query(None, alias="status"),
    level: str | None = Query(None, description="LOW, MEDIUM or HIGH"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Alerts sorted by risk score, highest first."""
    query = db.query(Alert)
    if status_filter:
        query = query.filter(Alert.status == status_filter.upper())
    if level:
        query = query.filter(Alert.risk_level == level.upper())
    return (
        query.order_by(Alert.final_risk_score.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{alert_id}", response_model=AlertOut)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*STAFF_ROLES)),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return alert


@router.patch("/{alert_id}/status", response_model=AlertOut)
def update_alert_status(
    alert_id: int,
    payload: AlertStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ANALYST, ROLE_ADMIN)),
):
    """Move an alert through OPEN -> IN_REVIEW -> CLOSED."""
    allowed = [Alert.ALERT_OPEN, Alert.ALERT_IN_REVIEW, Alert.ALERT_CLOSED]
    new_status = payload.status.upper()
    if new_status not in allowed:
        raise HTTPException(
            status_code=400, detail=f"Status must be one of {', '.join(allowed)}."
        )

    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")

    old_status = alert.status
    alert.status = new_status
    db.commit()
    db.refresh(alert)

    write_audit(
        db,
        action="ALERT_STATUS_CHANGED",
        user=current_user,
        entity_type="Alert",
        entity_id=alert.id,
        details={"from": old_status, "to": new_status},
        ip_address=request.client.host if request.client else None,
    )
    return alert
