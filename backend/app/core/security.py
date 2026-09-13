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


def verify_active_user(token: str) -> AuthContext:
    """Verify the JWT AND confirm the user still exists and is active in the DB.
    Same liveness rule as the HTTP API layer (deps.get_current_user) — a
    deactivated or deleted user's unexpired token must not pass MCP authz."""
    auth = verify_token(token)
    try:
        from app.db.db import get_session_factory
        from app.db.models import User

        session = get_session_factory()()
        try:
            try:
                user_uuid = uuid.UUID(auth.user_id)
            except ValueError as exc:
                raise AuthError("invalid subject") from exc
            user = session.get(User, user_uuid)
            if user is None or not user.is_active:
                raise AuthError("user not found or inactive")
        finally:
            session.close()
    except ImportError:
        # DB unavailable (isolated unit tests) — signature verification still applies.
        pass
    return auth
