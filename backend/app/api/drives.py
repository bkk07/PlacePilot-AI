# Drive APIs: search/filter, detail, and admin creation.

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.db import get_db
from app.db.models import Compensation, Company, Drive, JobLocation, JobPosition, JobPositionSkill, Skill, User
from app.schemas.api_schemas import DriveCreate, DriveOut

router = APIRouter(prefix="/drives", tags=["drives"])


def _aggregate_drive(drive: Drive, db: Session) -> dict:
    # Optimized: single queries batched per-drive; caller may batch further via preloading
    positions = db.execute(select(JobPosition).where(JobPosition.drive_id == drive.id)).scalars().all()
    if not positions:
        return {"roles_count": 0, "ctc_min": None, "ctc_max": None, "stipend_min": None, "stipend_max": None, "has_unpaid_roles": False, "employment_types": [], "skills_union": [], "locations_union": []}
    pos_ids = [p.id for p in positions]
    comp_rows = db.execute(select(Compensation).where(Compensation.job_position_id.in_(pos_ids))).scalars().all() if pos_ids else []
    ctc_vals = []
    stip_vals = []
    has_unpaid = False
    for c in comp_rows:
        if c.is_unpaid:
            has_unpaid = True
        for v in [c.ctc_min, c.ctc_max, c.annual_ctc, c.fixed_ctc]:
            if v is not None:
                ctc_vals.append(float(v))
        for v in [c.stipend_min, c.stipend_max, c.monthly_stipend, c.monthly_salary]:
            if v is not None and not c.is_unpaid:
                stip_vals.append(float(v))
    if not ctc_vals and drive.ctc_lpa is not None:
        ctc_vals = [float(drive.ctc_lpa)]
    if not stip_vals and drive.stipend_monthly is not None:
        stip_vals = [float(drive.stipend_monthly)]
    employment_types = sorted({p.employment_type for p in positions if p.employment_type})
    skill_names = set(drive.skills or [])
    if pos_ids:
        rows = db.execute(select(Skill.name).join(JobPositionSkill, Skill.id == JobPositionSkill.skill_id).where(JobPositionSkill.job_position_id.in_(pos_ids))).scalars().all()
        skill_names.update(rows)
    locs = set()
    if drive.location:
        locs.update([s.strip() for s in drive.location.split(",") if s.strip()])
    if pos_ids:
        loc_rows = db.execute(select(JobLocation.city).where(JobLocation.job_position_id.in_(pos_ids))).scalars().all()
        locs.update(loc_rows)
    return {
        "roles_count": len(positions),
        "ctc_min": min(ctc_vals) if ctc_vals else None,
        "ctc_max": max(ctc_vals) if ctc_vals else None,
        "stipend_min": min(stip_vals) if stip_vals else None,
        "stipend_max": max(stip_vals) if stip_vals else None,
        "has_unpaid_roles": has_unpaid,
        "employment_types": employment_types,
        "skills_union": sorted(skill_names),
        "locations_union": sorted(locs),
    }

def _drive_out(drive: Drive, company: Company, db: Session, include_rules: bool = False) -> DriveOut:
    def _dt(v):
        return v.isoformat() if v is not None else None
    agg = _aggregate_drive(drive, db)
    return DriveOut(
        id=drive.id,
        title=drive.title,
        company=company.name,
        company_id=company.id,
        role=drive.role,
        ctc_lpa=float(drive.ctc_lpa) if drive.ctc_lpa is not None else None,
        stipend_monthly=float(drive.stipend_monthly) if drive.stipend_monthly is not None else None,
        location=drive.location,
        application_deadline=drive.application_deadline,
        status=drive.status,
        skills=drive.skills or [],
        rules=drive.rules if include_rules else None,
        description=drive.description,
        drive_type=drive.drive_type,
        mode=drive.mode,
        registration_start=_dt(drive.registration_start),
        registration_end=_dt(drive.registration_end),
        venue=drive.venue,
        meeting_link=drive.meeting_link,
        roles_count=agg["roles_count"],
        ctc_min=agg["ctc_min"],
        ctc_max=agg["ctc_max"],
        stipend_min=agg["stipend_min"],
        stipend_max=agg["stipend_max"],
        has_unpaid_roles=agg["has_unpaid_roles"],
        employment_types=agg["employment_types"],
        skills_union=agg["skills_union"],
        locations_union=agg["locations_union"],
    )


@router.get("", response_model=list[DriveOut])
def list_drives(
    query: str = Query(default="", max_length=200),
    company: str = Query(default="", max_length=120),
    role: str = Query(default="", max_length=120),
    status_filter: str = Query(default="", alias="status", max_length=20),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DriveOut]:
    # Normalize status values: accept case-insensitive, map to stored values
    # Students default to open-like statuses; admins see all when no filter
    status_normalized = status_filter.strip().lower() if status_filter else ""
    # Treat "open" to include legacy "open" and new "PUBLISHED"/"REGISTRATION_OPEN"
    open_statuses = ["open", "PUBLISHED", "REGISTRATION_OPEN"]
    effective_in = None
    if status_normalized == "open":
        effective_in = open_statuses
    elif status_normalized and not status_normalized == "":
        effective_in = [status_filter]

    stmt = select(Drive, Company).join(Company, Drive.company_id == Company.id).order_by(Drive.created_at.desc())
    if not status_filter and user.role != "admin":
        stmt = stmt.where(Drive.status.in_(open_statuses))
    elif effective_in:
        stmt = stmt.where(Drive.status.in_(effective_in))
    if company:
        stmt = stmt.where(Company.name.ilike(f"%{company}%"))
    if role:
        stmt = stmt.where(Drive.role.ilike(f"%{role}%"))

    stmt = stmt.offset(skip).limit(limit)
    out: list[DriveOut] = []
    rows = db.execute(stmt).all()
    # Preload aggregates in batch to avoid N+1 - collect drive ids
    for drive, comp in rows:
        if query:
            haystack = " ".join(
                [drive.title, drive.role, comp.name, drive.location, " ".join(drive.skills or [])]
            ).lower()
            if query.lower() not in haystack:
                continue
        out.append(_drive_out(drive, comp, db))
    return out


@router.get("/{drive_id}", response_model=DriveOut)
def get_drive(
    drive_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DriveOut:
    row = db.execute(
        select(Drive, Company).join(Company, Drive.company_id == Company.id).where(Drive.id == drive_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="drive not found")
    return _drive_out(row[0], row[1], db, include_rules=True)


@router.post("", response_model=DriveOut, status_code=status.HTTP_201_CREATED)
def create_drive(
    payload: DriveCreate,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> DriveOut:
    company = db.get(Company, payload.company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company not found")
    drive = Drive(
        company_id=company.id,
        title=payload.title,
        description=payload.description,
        drive_type=payload.drive_type,
        mode=payload.mode,
        registration_start=payload.registration_start,
        registration_end=payload.registration_end,
        drive_start_date=payload.drive_start_date,
        drive_end_date=payload.drive_end_date,
        venue=payload.venue,
        meeting_link=payload.meeting_link,
        application_limit=payload.application_limit,
        instructions=payload.instructions,
        role=payload.role,
        ctc_lpa=payload.ctc_lpa,
        stipend_monthly=payload.stipend_monthly,
        location=payload.location,
        application_deadline=payload.application_deadline,
        status="open",
        skills=payload.skills,
        rules=payload.rules,
    )
    db.add(drive)
    db.commit()
    db.refresh(drive)
    return _drive_out(drive, company, db, include_rules=True)


@router.put("/{drive_id}", response_model=DriveOut)
def update_drive(
    drive_id: uuid.UUID,
    payload: dict,
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> DriveOut:
    drive = db.get(Drive, drive_id)
    if drive is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="drive not found")

    # company change
    if "company_id" in payload and payload["company_id"]:
        try:
            new_cid = uuid.UUID(str(payload["company_id"]))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid company_id")
        company = db.get(Company, new_cid)
        if company is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="company not found")
        drive.company_id = company.id

    # simple scalar fields — only update if present in payload
    for field in [
        "title",
        "description",
        "drive_type",
        "mode",
        "venue",
        "meeting_link",
        "instructions",
        "role",
        "location",
        "application_deadline",
        "status",
    ]:
        if field in payload:
            setattr(drive, field, payload[field])

    for field in ["application_limit"]:
        if field in payload:
            val = payload[field]
            setattr(drive, field, int(val) if val not in (None, "") else None)

    for field in ["ctc_lpa", "stipend_monthly"]:
        if field in payload:
            val = payload[field]
            setattr(drive, field, float(val) if val not in (None, "") else None)

    for field in ["registration_start", "registration_end", "drive_start_date", "drive_end_date"]:
        if field in payload:
            val = payload[field]
            if val in (None, ""):
                setattr(drive, field, None)
            else:
                # accept ISO string
                from datetime import datetime

                try:
                    # handle datetime-local without tz
                    dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
                    setattr(drive, field, dt)
                except Exception:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"invalid {field}")

    for field in ["skills", "rules"]:
        if field in payload:
            setattr(drive, field, payload[field] if payload[field] is not None else ([] if field == "skills" else {}))

    db.commit()
    db.refresh(drive)
    company = db.get(Company, drive.company_id)
    return _drive_out(drive, company, db, include_rules=True)