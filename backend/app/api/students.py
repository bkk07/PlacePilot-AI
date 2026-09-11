# Student-facing APIs: own profile and eligibility checks against drives.

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.db import get_db
from app.db.models import Drive, StudentProfile, User
from app.schemas.api_schemas import EligibilityOut, ProfileIn, ProfileOut
from app.services.eligibility import evaluate_eligibility

router = APIRouter(prefix="/students/me", tags=["students"])


def _profile_dict(user: User, profile: StudentProfile) -> dict:
    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "roll_number": profile.roll_number,
        "branch": profile.branch,
        "graduation_year": profile.graduation_year,
        "cgpa": float(profile.cgpa) if profile.cgpa is not None else None,
        "active_backlogs": profile.active_backlogs,
        "skills": profile.skills or [],
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
    }
    result = evaluate_eligibility(student, {"rules": drive.rules or {}})
    return EligibilityOut(
        drive_id=drive.id,
        drive_title=drive.title,
        eligible=result.eligible,
        reasons=result.reasons,
        missing_requirements=result.missing_requirements,
    )