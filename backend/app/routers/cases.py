"""Investigation case management."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.deps import require_roles
from app.models import (
    ROLE_ADMIN,
    ROLE_ANALYST,
    ROLE_COMPLIANCE,
    Alert,
    Case,
    CaseNote,
    Transaction,
    User,
)
from app.schemas import (
    CaseCreate,
    CaseDetailOut,
    CaseNoteCreate,
    CaseNoteOut,
    CaseOut,
    CaseUpdate,
)

router = APIRouter(prefix="/api/cases", tags=["Cases"])

STAFF_ROLES = (ROLE_ANALYST, ROLE_COMPLIANCE, ROLE_ADMIN)


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ANALYST, ROLE_ADMIN)),
):
    """Open an investigation case for a transaction."""
    transaction = (
        db.query(Transaction).filter(Transaction.id == payload.transaction_id).first()
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    if payload.assigned_to_id is not None:
        assignee = db.query(User).filter(User.id == payload.assigned_to_id).first()
        if assignee is None:
            raise HTTPException(status_code=404, detail="Assigned user not found.")

    alert = db.query(Alert).filter(Alert.transaction_id == transaction.id).first()

    case = Case(
        case_ref=f"CASE-{uuid.uuid4().hex[:8].upper()}",
        title=payload.title,
        description=payload.description,
        transaction_id=transaction.id,
        alert_id=alert.id if alert else None,
        priority=payload.priority.upper(),
        created_by_id=current_user.id,
        assigned_to_id=payload.assigned_to_id or current_user.id,
    )
    db.add(case)

    if alert and alert.status == Alert.ALERT_OPEN:
        alert.status = Alert.ALERT_IN_REVIEW

    db.commit()
    db.refresh(case)

    write_audit(
        db,
        action="CASE_CREATED",
        user=current_user,
        entity_type="Case",
        entity_id=case.id,
        details={"case_ref": case.case_ref, "transaction_id": transaction.id},
        ip_address=request.client.host if request.client else None,
    )
    return case


@router.get("", response_model=list[CaseOut])
def list_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*STAFF_ROLES)),
    status_filter: str | None = Query(None, alias="status"),
    assigned_to_me: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    query = db.query(Case)
    if status_filter:
        query = query.filter(Case.status == status_filter.upper())
    if assigned_to_me:
        query = query.filter(Case.assigned_to_id == current_user.id)
    return query.order_by(Case.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{case_id}", response_model=CaseDetailOut)
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*STAFF_ROLES)),
):
    """One case with all its investigation notes."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


@router.patch("/{case_id}", response_model=CaseOut)
def update_case(
    case_id: int,
    payload: CaseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ANALYST, ROLE_ADMIN)),
):
    """Change the status, priority, assignee or resolution of a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    changes = {}
    if payload.status is not None:
        new_status = payload.status.upper()
        if new_status not in Case.ALL_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Status must be one of {', '.join(Case.ALL_STATUSES)}.",
            )
        changes["status"] = {"from": case.status, "to": new_status}
        case.status = new_status
        if new_status == Case.STATUS_CLOSED:
            case.closed_at = datetime.utcnow()
            if case.alert:
                case.alert.status = Alert.ALERT_CLOSED

    if payload.priority is not None:
        case.priority = payload.priority.upper()
        changes["priority"] = case.priority

    if payload.assigned_to_id is not None:
        assignee = db.query(User).filter(User.id == payload.assigned_to_id).first()
        if assignee is None:
            raise HTTPException(status_code=404, detail="Assigned user not found.")
        case.assigned_to_id = payload.assigned_to_id
        changes["assigned_to_id"] = payload.assigned_to_id

    if payload.resolution is not None:
        case.resolution = payload.resolution
        changes["resolution_updated"] = True

    db.commit()
    db.refresh(case)

    write_audit(
        db,
        action="CASE_UPDATED",
        user=current_user,
        entity_type="Case",
        entity_id=case.id,
        details=changes,
        ip_address=request.client.host if request.client else None,
    )
    return case


@router.post(
    "/{case_id}/notes", response_model=CaseNoteOut, status_code=status.HTTP_201_CREATED
)
def add_case_note(
    case_id: int,
    payload: CaseNoteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ANALYST, ROLE_ADMIN)),
):
    """Add an investigation note to a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    note = CaseNote(case_id=case.id, author_id=current_user.id, note=payload.note)
    db.add(note)
    db.commit()
    db.refresh(note)

    write_audit(
        db,
        action="CASE_NOTE_ADDED",
        user=current_user,
        entity_type="Case",
        entity_id=case.id,
        ip_address=request.client.host if request.client else None,
    )
    return note
