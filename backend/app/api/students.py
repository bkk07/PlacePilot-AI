# Student-facing APIs: own profile and eligibility checks against drives.

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.db import get_db
from app.db.models import Branch, Drive, DriveEligibleBatch, DriveEligibleBranch, EligibilityCriteria, StoredFile, StudentProfile, User
from app.schemas.api_schemas import EligibilityOut, ProfileIn, ProfileOut
from app.services.eligibility import evaluate_eligibility


def _build_extended_criteria(db: Session, drive_id: uuid.UUID) -> dict:
    """Merge normalized TNPC tables into extended criteria dict for eligibility engine."""
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

router = APIRouter(prefix="/students/me", tags=["students"])


def _num(v):
    return float(v) if v is not None else None


def _profile_dict(user: User, profile: StudentProfile) -> dict:
    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "roll_number": profile.roll_number,
        "branch": profile.branch,
        "graduation_year": profile.graduation_year,
        "cgpa": _num(profile.cgpa),
        "active_backlogs": profile.active_backlogs,
        "skills": profile.skills or [],
        "personal_email": profile.personal_email,
        "phone_number": profile.phone_number,
        "degree": profile.degree,
        "specialization": profile.specialization,
        "admission_year": profile.admission_year,
        "current_year": profile.current_year,
        "current_semester": profile.current_semester,
        "tenth_percentage": _num(profile.tenth_percentage),
        "tenth_board": profile.tenth_board,
        "twelfth_percentage": _num(profile.twelfth_percentage),
        "twelfth_board": profile.twelfth_board,
        "diploma_percentage": _num(profile.diploma_percentage),
        "history_of_backlogs": profile.history_of_backlogs,
        "year_gaps": profile.year_gaps,
        "profile_photo_id": profile.profile_photo_id,
    }


@router.get("/profile", response_model=ProfileOut)
def get_profile(
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> ProfileOut:
    profile = db.get(StudentProfile, user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile not created yet")
    return ProfileOut(**_profile_dict(user, profile))


@router.put("/profile", response_model=ProfileOut)
def upsert_profile(
    payload: ProfileIn,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> ProfileOut:
    profile = db.get(StudentProfile, user.id)
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return ProfileOut(**_profile_dict(user, profile))


@router.post("/profile/photo")
def upload_profile_photo(
    file: UploadFile = File(...),
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="only image files allowed")
    data = file.file.read()
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="file too large (max 2MB)")
    stored = StoredFile(
        file_name=file.filename or "profile.jpg",
        content_type=file.content_type or "image/jpeg",
        file_size=len(data),
        file_data=data,
        uploaded_by=user.id,
    )
    db.add(stored)
    db.flush()
    profile = db.get(StudentProfile, user.id)
    if profile is None:
        profile = StudentProfile(user_id=user.id, roll_number=f"TEMP-{str(user.id)[:8]}", branch="CSE", graduation_year=2027)
        db.add(profile)
        db.flush()
    profile.profile_photo_id = stored.id
    db.commit()
    return {"profile_photo_id": str(stored.id)}


@router.get("/profile/photo")
def get_profile_photo(
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    profile = db.get(StudentProfile, user.id)
    if not profile or not profile.profile_photo_id:
        raise HTTPException(status_code=404, detail="no profile photo")
    f = db.get(StoredFile, profile.profile_photo_id)
    if not f:
        raise HTTPException(status_code=404, detail="file not found")
    return Response(content=f.file_data, media_type=f.content_type)


@router.get("/eligibility/{drive_id}", response_model=EligibilityOut)
def check_eligibility(
    drive_id: uuid.UUID,
    user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> EligibilityOut:
    profile = db.get(StudentProfile, user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="create your student profile before checking eligibility",
        )
    drive = db.get(Drive, drive_id)
    if drive is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="drive not found")

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
    result = evaluate_eligibility(student, {"rules": drive.rules or {}, "extended": extended})
    return EligibilityOut(
        drive_id=drive.id,
        drive_title=drive.title,
        eligible=result.eligible,
        reasons=result.reasons,
        missing_requirements=result.missing_requirements,
    )