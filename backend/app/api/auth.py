# Auth APIs: signup, login, and current-user lookup. Passwords are bcrypt-hashed.

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_token
from app.db.db import get_db
from app.db.models import StudentProfile, User
from app.schemas.api_schemas import LoginRequest, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_token(str(user.id), user.role),
        user_id=user.id,
        role=user.role,
        full_name=user.full_name,
    )


_login_attempts: dict[str, list[float]] = {}
import time

def _check_rate_limit(key: str, max_attempts: int = 8, window_sec: int = 60):
    now = time.time()
    attempts = _login_attempts.get(key, [])
    attempts = [t for t in attempts if now - t < window_sec]
    if len(attempts) >= max_attempts:
        raise HTTPException(status_code=429, detail="too many attempts, try again later")
    attempts.append(now)
    _login_attempts[key] = attempts


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email_norm = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email_norm))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")

    user = User(
        email=email_norm,
        password_hash=pwd.hash(payload.password),
        full_name=payload.full_name.strip(),
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email_norm = payload.email.strip().lower()
    _check_rate_limit(email_norm)
    user = db.scalar(select(User).where(User.email == email_norm))
    if user is None or not pwd.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="account is inactive")
    return _token_response(user)


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    profile = db.get(StudentProfile, user.id)
    return {
        "user_id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "has_profile": profile is not None,
    }