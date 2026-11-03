"""Shared FastAPI dependencies: current user and role checks (RBAC)."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token

# tokenUrl makes the "Authorize" button in Swagger work.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_error

    user = db.query(User).filter(User.username == payload["sub"]).first()
    if user is None:
        raise credentials_error
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is disabled.")
    return user


def require_roles(*allowed_roles: str):
    """
    Dependency factory for role based access control.

    Example:
        @router.get("/", dependencies=[Depends(require_roles(ROLE_ADMIN))])
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{current_user.role}' is not allowed to use this endpoint. "
                    f"Allowed roles: {', '.join(allowed_roles)}."
                ),
            )
        return current_user

    return role_checker
