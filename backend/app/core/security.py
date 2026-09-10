# Security: JWT creation/verification and role extraction.
# Every MCP tool re-checks authorization from these helpers — never from request text.

import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings

# This dev-only key material is fine for the seeded local environment; production
# rotates GROQ/JWT secrets via env (Phase 10).
ALGORITHM = settings.JWT_ALGORITHM
EXPIRE_MINUTES = settings.JWT_EXPIRE_MINUTES


def create_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


class AuthContext:
    """Identity extracted from the caller's verified JWT."""

    def __init__(self, user_id: str, role: str):
        self.user_id = user_id
        self.role = role

    @property
    def is_student(self) -> bool:
        return self.role == "student"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class AuthError(Exception):
    pass


def verify_token(token: str) -> AuthContext:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise AuthError("invalid or expired token") from exc
    user_id = payload.get("sub")
    role = payload.get("role")
    if not user_id or not role:
        raise AuthError("token missing identity claims")
    return AuthContext(user_id=str(user_id), role=str(role))
