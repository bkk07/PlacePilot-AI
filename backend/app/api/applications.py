# Application APIs: submit, list, and status updates through the strict state machine.

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.db import get_db
from app.db.models import Application, Branch, Drive, DriveEligibleBatch, DriveEligibleBranch, EligibilityCriteria, StudentProfile, User
from app.schemas.api_schemas import ApplicationCreate, ApplicationOut, ApplicationStatusUpdate
from app.services.application_state import InvalidTransition, transition
from app.services.eligibility import evaluate_eligibility


def _build_extended_criteria(db, drive_id):
    crit = db.scalar(select(EligibilityCriteria).where(EligibilityCriteria.drive_id == drive_id))
    branch_rows = db.execute(select(Branch.code).join(DriveEligibleBranch, DriveEligibleBranch.branch_id == Branch.id).where(DriveEligibleBranch.drive_id == drive_id)).scalars().all()
    batch_rows = db.execute(select(DriveEligibleBatch.graduation_year).where(DriveEligibleBatch.drive_id == drive_id)).scalars().all()
    extended: dict = {}
    if crit:
        if crit.minimum_cgpa is not None:
            extended["minimum_cgpa"] = float(crit.minimum_cgpa)
        if crit.maximum_backlogs is not None:
            extended["maximum_backlogs"] = crit.maximum_backlogs
        if crit.passing_year_from is not None:
            extended["passing_year_from"] = crit.passing_year_from
        if crit.passing_year_to is not None:
            extended["passing_year_to"] = crit.passing_year_to
        if crit.minimum_10th_percentage is not None:
            extended["minimum_10th_percentage"] = float(crit.minimum_10th_percentage)
        if crit.minimum_12th_percentage is not None:
            extended["minimum_12th_percentage"] = float(crit.minimum_12th_percentage)
        if crit.minimum_diploma_percentage is not None:
            extended["minimum_diploma_percentage"] = float(crit.minimum_diploma_percentage)
        if crit.backlogs_allowed is not None:
            extended["backlogs_allowed"] = crit.backlogs_allowed
    if branch_rows:
        extended["eligible_branches"] = list(branch_rows)
    if batch_rows:
        extended["eligible_batches"] = list(batch_rows)
    return extended

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
        "tenth_percentage": float(profile.tenth_percentage) if profile.tenth_percentage is not None else None,
        "twelfth_percentage": float(profile.twelfth_percentage) if profile.twelfth_percentage is not None else None,
        "diploma_percentage": float(profile.diploma_percentage) if profile.diploma_percentage is not None else None,
    }
    extended = _build_extended_criteria(db, drive.id)
    decision = evaluate_eligibility(student, {"rules": drive.rules or {}, "extended": extended})
    if not decision.eligible:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "not eligible for this drive", "reasons": decision.reasons, "missing_requirements": decision.missing_requirements},
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
            select(Application).where(Application.idempotency_key == payload.idempotency_key, Application.student_id == user.id)
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