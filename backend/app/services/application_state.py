# Application status state machine — no arbitrary transitions.
# Every change is recorded in application_status_history.

import uuid

from sqlalchemy.orm import Session

from app.db.models import Application, ApplicationStatusHistory

STATUSES = (
    "applied",
    "shortlisted",
    "interview",
    "offer",
    "selected",
    "rejected",
    "withdrawn",
)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "applied": {"shortlisted", "rejected", "withdrawn"},
    "shortlisted": {"interview", "offer", "rejected", "withdrawn"},
    "interview": {"offer", "selected", "rejected", "withdrawn"},
    "offer": {"selected", "rejected", "withdrawn"},
    "selected": set(),
    "rejected": set(),
    "withdrawn": set(),
}


class InvalidTransition(Exception):
    pass


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())


def transition(
    session: Session,
    application: Application,
    to_status: str,
    changed_by: uuid.UUID | None,
    reason: str | None = None,
) -> Application:
    """Apply a validated status transition and append a history row. Commits."""
    if to_status not in STATUSES:
        raise InvalidTransition(f"unknown status: {to_status}")
    old = application.status
    if to_status == old:
        return application
    if not can_transition(old, to_status):
        raise InvalidTransition(f"cannot move application from '{old}' to '{to_status}'")

    application.status = to_status
    session.add(
        ApplicationStatusHistory(
            application_id=application.id,
            from_status=old,
            to_status=to_status,
            changed_by=changed_by,
            reason=reason,
        )
    )
    session.commit()
    return application