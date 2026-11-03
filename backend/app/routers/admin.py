"""Admin endpoints: users, audit trail and the AML rule thresholds."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.deps import require_roles
from app.models import ALL_ROLES, ROLE_ADMIN, ROLE_COMPLIANCE, AuditLog, User
from app.schemas import AuditLogOut, RoleUpdate, UserOut
from app.services import aml_service
from app.services.ml_service import ML_MODEL_NAME, ml_service

router = APIRouter(prefix="/api/admin", tags=["Administration"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    return db.query(User).order_by(User.id).all()


@router.patch("/users/{user_id}/role", response_model=UserOut)
def change_user_role(
    user_id: int,
    payload: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
):
    """Change a user's role. Used to demonstrate RBAC during the viva."""
    new_role = payload.role.upper()
    if new_role not in ALL_ROLES:
        raise HTTPException(
            status_code=400, detail=f"Role must be one of {', '.join(ALL_ROLES)}."
        )
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    old_role = user.role
    user.role = new_role
    db.commit()
    db.refresh(user)

    write_audit(
        db,
        action="USER_ROLE_CHANGED",
        user=current_user,
        entity_type="User",
        entity_id=user.id,
        details={"from": old_role, "to": new_role},
        ip_address=request.client.host if request.client else None,
    )
    return user


@router.get("/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_ADMIN, ROLE_COMPLIANCE)),
    action: str | None = Query(None, description="Filter by action name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """The audit trail, newest entry first."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action.upper())
    return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/aml-rules")
def get_aml_rules(current_user: User = Depends(require_roles(ROLE_ADMIN, ROLE_COMPLIANCE))):
    """Thresholds currently used by Member 4's rule engine."""
    return {
        "aml_module_available": aml_service.AML_AVAILABLE,
        "thresholds": aml_service.get_thresholds(),
        "note": "Thresholds are defined in Member 4's aml/rules.py (DEFAULT_THRESHOLDS).",
    }


@router.get("/ml-models")
def get_ml_models(current_user: User = Depends(require_roles(ROLE_ADMIN, ROLE_COMPLIANCE))):
    """Which of Member 2's models are loaded and which one is in use."""
    return {
        "models_loaded": ml_service.available_models(),
        "active_model": ML_MODEL_NAME,
        "scaler_loaded": ml_service.scaler is not None,
        "load_error": ml_service.load_error,
    }
