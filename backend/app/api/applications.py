# Application APIs: submit, list, and status updates through the strict state machine.

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.db import get_db
from app.db.models import Application, Drive, StudentProfile, User
from app.schemas.api_schemas import ApplicationCreate, ApplicationOut, ApplicationStatusUpdate
from app.services.application_state import InvalidTransition, transition
from app.services.eligibility import evaluate_eligibility

router = APIRouter(prefix="/applications", tags=["applications"])


def _app_out(app_row: Application, drive: Drive) -> ApplicationOut:
    return ApplicationOut(
        id=app_row.id,
        drive_id=app_row.drive_id,
        job_position_id=app_row.job_position_id,
        drive_title=drive.title,
        student_id=app_row.student_id,
        status=app_row.status,
        created_at=app_row.created_at.isoformat(),
    )


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def apply(
    payload: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationOut:
    if user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="only students can apply")

    drive = db.get(Drive, payload.drive_id)
    if drive is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="drive not found")
    if drive.status != "open":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="drive is not open")

    profile = db.get(StudentProfile, user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="create your student profile before applying",
        )

    student = {
        "branch": profile.branch,
        "cgpa": float(profile.cgpa) if profile.cgpa is not None else None,
        "active_backlogs": profile.active_backlogs,
        "graduation_year": profile.graduation_year,
        "skills": profile.skills or [],
    }
    decision = evaluate_eligibility(student, {"rules": drive.rules or {}})
    if not decision.eligible:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "not eligible for this drive", "reasons": decision.reasons},
        )

    # support per-role application: if job_position_id supplied, check that combo
    jid = payload.job_position_id
    if jid is not None:
        # verify position belongs to drive
        from app.db.models import JobPosition
        pos = db.get(JobPosition, jid)
        if pos is None or pos.drive_id != drive.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid job_position for this drive")
    existing_q = select(Application).where(Application.drive_id == drive.id, Application.student_id == user.id)
    if jid is not None:
        existing_q = existing_q.where(Application.job_position_id == jid)
    existing = db.scalar(existing_q)
    if existing is not None:
        return _app_out(existing, drive)

    if payload.idempotency_key:
        dup = db.scalar(
            select(Application).where(Application.idempotency_key == payload.idempotency_key)
        )
        if dup is not None:
            return _app_out(dup, db.get(Drive, dup.drive_id))

    app_row = Application(
        drive_id=drive.id,
        job_position_id=jid,
        student_id=user.id,
        status="applied",
        idempotency_key=payload.idempotency_key,
    )
    db.add(app_row)
    db.commit()
    db.refresh(app_row)
    return _app_out(app_row, drive)


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApplicationOut]:
    stmt = select(Application, Drive).join(Drive, Application.drive_id == Drive.id)
    if user.role != "admin":
        stmt = stmt.where(Application.student_id == user.id)
    return [_app_out(app_row, drive) for app_row, drive in db.execute(stmt).all()]


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_status(
    application_id: uuid.UUID,
    payload: ApplicationStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationOut:
    app_row = db.get(Application, application_id)
    if app_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")

    if user.role == "student":
        if app_row.student_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not your application")
        if payload.status != "withdrawn":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="students may only withdraw their own application",
            )
    elif user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")

    try:
        transition(db, app_row, payload.status, changed_by=user.id, reason=payload.reason)
    except InvalidTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    drive = db.get(Drive, app_row.drive_id)
    return _app_out(app_row, drive)