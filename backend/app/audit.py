"""Small helper so every router can write an audit log the same way."""
from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit(
    db: Session,
    action: str,
    user=None,
    entity_type: str | None = None,
    entity_id=None,
    details: dict | None = None,
    ip_address: str | None = None,
    commit: bool = True,
) -> AuditLog:
    log = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details,
        ip_address=ip_address,
    )
    db.add(log)
    if commit:
        db.commit()
    return log
