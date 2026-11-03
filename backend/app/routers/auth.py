"""Registration, login and profile endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.deps import get_current_user
from app.models import ALL_ROLES, ROLE_ADMIN, User
from app.schemas import Token, UserCreate, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Create a new account. Only an admin can hand out the ADMIN role."""
    if payload.role not in ALL_ROLES:
        raise HTTPException(
            status_code=400, detail=f"Role must be one of {', '.join(ALL_ROLES)}."
        )
    if payload.role == ROLE_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="The ADMIN role can only be given by an existing admin.",
        )
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username is already taken.")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email is already registered.")

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    write_audit(
        db,
        action="USER_REGISTERED",
        user=user,
        entity_type="User",
        entity_id=user.id,
        details={"role": user.role},
        ip_address=request.client.host if request.client else None,
    )
    return user


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Exchange username and password for a JWT access token."""
    user = db.query(User).filter(User.username == form_data.username).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        write_audit(
            db,
            action="LOGIN_FAILED",
            details={"username": form_data.username},
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=401, detail="Incorrect username or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is disabled.")

    write_audit(
        db,
        action="LOGIN_SUCCESS",
        user=user,
        entity_type="User",
        entity_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    return Token(
        access_token=create_access_token(user.username, user.role),
        role=user.role,
        username=user.username,
    )


@router.get("/me", response_model=UserOut)
def read_profile(current_user: User = Depends(get_current_user)):
    """Details of the logged-in user."""
    return current_user
