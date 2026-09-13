# TNPC domain APIs — all 31 entities exposed for the React wizard/pipeline.
# Every mutating route requires admin/TNPC role; reads require any authenticated user.

import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.db import get_db
from app.db.models import (
    Branch,
    Company,
    Compensation,
    Drive,
    DriveAnnouncement,
    DriveContact,
    DriveEligibleBatch,
    DriveEligibleBranch,
    DrivePolicy,
    DriveRound,
    DriveSchedule,
    EducationRequirement,
    EligibilityCriteria,
    InternshipDetails,
    JobLocation,
    JobPosition,
    JobPositionSkill,
    Skill,
    StoredFile,
    User,
)

router = APIRouter(tags=["tnpc"])

from pydantic import BaseModel, Field


class CompanyCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    legal_name: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=100)
    headquarters: str | None = Field(default=None, max_length=100)
    company_size: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=2000)


class CompanyUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    legal_name: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=500)
    industry: str | None = Field(default=None, max_length=100)
    headquarters: str | None = Field(default=None, max_length=100)
    company_size: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=2000)


class SkillCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str | None = Field(default="OTHER", max_length=50)
    description: str | None = Field(default=None, max_length=500)


def _ensure_branches_seeded(db: Session):
    """Seed default branches if table empty - idempotent, called lazily."""
    if db.scalar(select(Branch).limit(1)) is None:
        for code, name in [("CSE","Computer Science"),("IT","Information Technology"),("ECE","Electronics & Communication"),("EEE","Electrical"),("ME","Mechanical"),("CE","Civil"),("AERO","Aerospace"),("CHEM","Chemical")]:
            db.add(Branch(name=name, code=code))
        db.commit()

# ---------- Companies ----------
@router.get("/companies", tags=["companies"])
def list_companies(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Company).order_by(Company.name)).scalars().all()
    return [{"id": str(c.id), "name": c.name, "legal_name": c.legal_name, "industry": c.industry, "headquarters": c.headquarters, "website": c.website, "description": c.description, "company_size": c.company_size} for c in rows]

@router.post("/companies", status_code=201, tags=["companies"])
def create_company(payload: CompanyCreateIn, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "name is required")
    if db.scalar(select(Company).where(Company.name == name)):
        raise HTTPException(409, "company already exists")
    c = Company(
        name=name,
        legal_name=payload.legal_name,
        website=str(payload.website) if payload.website else None,
        industry=payload.industry,
        company_size=payload.company_size,
        description=payload.description,
        headquarters=payload.headquarters,
        created_by=admin.id,
    )
    db.add(c); db.commit(); db.refresh(c)
    return {"id": str(c.id), "name": c.name}


@router.put("/companies/{company_id}", tags=["companies"])
def update_company(company_id: uuid.UUID, payload: CompanyUpdateIn, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    c = db.get(Company, company_id)
    if not c:
        raise HTTPException(404, "company not found")
    if payload.name is not None:
        new_name = payload.name.strip()
        if not new_name:
            raise HTTPException(400, "name is required")
        if new_name != c.name and db.scalar(select(Company).where(Company.name == new_name)):
            raise HTTPException(409, "company already exists")
        c.name = new_name
    for field in ["legal_name", "website", "industry", "headquarters", "company_size", "description"]:
        val = getattr(payload, field)
        if val is not None:
            setattr(c, field, (val.strip() if isinstance(val, str) else val) or None)
    c.updated_by = admin.id
    db.commit()
    db.refresh(c)
    return {"id": str(c.id), "name": c.name, "legal_name": c.legal_name, "website": c.website, "industry": c.industry, "headquarters": c.headquarters, "company_size": c.company_size, "description": c.description}

# ---------- Skills & Branches ----------
@router.get("/skills")
def list_skills(q: str = Query(default="", max_length=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Skill).order_by(Skill.name)
    if q:
        like = f"%{q.strip()}%"
        # search both name and category
        from sqlalchemy import or_
        stmt = stmt.where(or_(Skill.name.ilike(like), Skill.category.ilike(like)))
    stmt = stmt.limit(80)
    return [{"id": str(s.id), "name": s.name, "category": s.category} for s in db.execute(stmt).scalars().all()]

@router.post("/skills", status_code=201)
def create_skill(payload: SkillCreateIn, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "name required")
    if db.scalar(select(Skill).where(Skill.name == name)):
        raise HTTPException(409, "skill already exists")
    s = Skill(name=name, category=payload.category or "OTHER", description=payload.description)
    db.add(s); db.commit(); db.refresh(s)
    return {"id": str(s.id), "name": s.name, "category": s.category}

@router.get("/branches")
def list_branches(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_branches_seeded(db)
    rows = db.execute(select(Branch).order_by(Branch.code)).scalars().all()
    return [{"id": str(b.id), "name": b.name, "code": b.code} for b in rows]

# ---------- Job Positions ----------
def _comp_to_dict(c: Compensation | None) -> dict | None:
    if not c:
        return None
    def f(v):
        return float(v) if v is not None else None
    return {
        "annual_ctc": f(c.annual_ctc),
        "fixed_ctc": f(c.fixed_ctc),
        "variable_ctc": f(c.variable_ctc),
        "monthly_salary": f(c.monthly_salary),
        "monthly_stipend": f(c.monthly_stipend),
        "ctc_min": f(c.ctc_min),
        "ctc_max": f(c.ctc_max),
        "stipend_min": f(c.stipend_min),
        "stipend_max": f(c.stipend_max),
        "is_unpaid": bool(c.is_unpaid),
        "stipend_type": c.stipend_type,
        "currency": c.currency,
        "joining_bonus": f(c.joining_bonus),
        "retention_bonus": f(c.retention_bonus),
    }

def _position_out(p: JobPosition, db: Session) -> dict:
    comp = db.scalar(select(Compensation).where(Compensation.job_position_id == p.id))
    intern = db.scalar(select(InternshipDetails).where(InternshipDetails.job_position_id == p.id))
    skills = db.execute(select(JobPositionSkill, Skill).join(Skill, JobPositionSkill.skill_id == Skill.id).where(JobPositionSkill.job_position_id == p.id)).all()
    locs = db.execute(select(JobLocation).where(JobLocation.job_position_id == p.id)).scalars().all()
    return {
        "id": str(p.id),
        "drive_id": str(p.drive_id),
        "title": p.title,
        "role": p.role,
        "department": p.department,
        "employment_type": p.employment_type,
        "openings": p.openings,
        "work_mode": p.work_mode,
        "job_description": p.job_description,
        "bond_required": bool(p.bond_required),
        "bond_duration_months": p.bond_duration_months,
        "bond_amount": float(p.bond_amount) if p.bond_amount is not None else None,
        "bond_description": p.bond_description,
        "compensation": _comp_to_dict(comp),
        "internship": {
            "duration_months": intern.duration_months,
            "paid": bool(intern.paid),
            "stipend": float(intern.stipend) if intern.stipend is not None else None,
            "stipend_min": float(intern.stipend_min) if intern.stipend_min is not None else None,
            "stipend_max": float(intern.stipend_max) if intern.stipend_max is not None else None,
            "ppo_available": bool(intern.ppo_available),
            "ppo_criteria": intern.ppo_criteria,
        } if intern else None,
        "skills": [
            {"skill_id": str(skill.id), "name": skill.name, "category": skill.category, "mandatory": bool(jps.mandatory), "skill_level": jps.skill_level}
            for jps, skill in skills
        ],
        "locations": [
            {"id": str(l.id), "city": l.city, "state": l.state, "country": l.country, "work_mode": l.work_mode}
            for l in locs
        ],
    }

@router.get("/drives/{drive_id}/positions")
def list_positions(drive_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    drive = db.get(Drive, drive_id)
    if not drive:
        raise HTTPException(404, "drive not found")
    positions = db.execute(select(JobPosition).where(JobPosition.drive_id == drive_id).order_by(JobPosition.created_at)).scalars().all()
    return [_position_out(p, db) for p in positions]

@router.post("/drives/{drive_id}/positions", status_code=201)
def create_position(drive_id: uuid.UUID, payload: dict, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    # Validate compensation ranges early
    _comp = payload.get("compensation") or {}
    if _comp.get("ctc_min") is not None and _comp.get("ctc_max") is not None:
        try:
            if float(_comp["ctc_min"]) > float(_comp["ctc_max"]):
                raise HTTPException(400, "ctc_min cannot exceed ctc_max")
        except ValueError:
            pass
    if _comp.get("stipend_min") is not None and _comp.get("stipend_max") is not None:
        try:
            if float(_comp["stipend_min"]) > float(_comp["stipend_max"]):
                raise HTTPException(400, "stipend_min cannot exceed stipend_max")
        except ValueError:
            pass
    drive = db.get(Drive, drive_id)
    if not drive:
        raise HTTPException(404, "drive not found")
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(400, "title required")
    pos = JobPosition(
        drive_id=drive_id,
        title=title,
        role=payload.get("role") or title,
        employment_type=payload.get("employment_type") or "FULL_TIME",
        openings=payload.get("openings"),
        work_mode=payload.get("work_mode"),
        job_description=payload.get("job_description"),
        department=payload.get("department"),
        bond_required=bool(payload.get("bond_required", False)),
        bond_duration_months=payload.get("bond_duration_months"),
        bond_amount=payload.get("bond_amount"),
        bond_description=payload.get("bond_description"),
    )
    db.add(pos); db.flush()  # get pos.id before commit

    # Compensation: support ranges + is_unpaid
    comp_payload = payload.get("compensation") or {}
    # also allow flat fields for backward compat
    for k in ["annual_ctc","monthly_stipend","fixed_ctc","variable_ctc","monthly_salary","ctc_min","ctc_max","stipend_min","stipend_max","currency","is_unpaid","stipend_type","joining_bonus","retention_bonus"]:
        if k in payload and k not in comp_payload:
            comp_payload[k] = payload[k]
    has_comp = any(comp_payload.get(k) is not None for k in ["annual_ctc","fixed_ctc","variable_ctc","monthly_salary","monthly_stipend","ctc_min","ctc_max","stipend_min","stipend_max","joining_bonus","retention_bonus"]) or comp_payload.get("is_unpaid")
    if has_comp:
        comp = Compensation(
            job_position_id=pos.id,
            annual_ctc=comp_payload.get("annual_ctc"),
            fixed_ctc=comp_payload.get("fixed_ctc"),
            variable_ctc=comp_payload.get("variable_ctc"),
            monthly_salary=comp_payload.get("monthly_salary"),
            monthly_stipend=comp_payload.get("monthly_stipend"),
            ctc_min=comp_payload.get("ctc_min"),
            ctc_max=comp_payload.get("ctc_max"),
            stipend_min=comp_payload.get("stipend_min"),
            stipend_max=comp_payload.get("stipend_max"),
            is_unpaid=bool(comp_payload.get("is_unpaid", False)),
            stipend_type=comp_payload.get("stipend_type"),
            currency=comp_payload.get("currency") or "INR",
            joining_bonus=comp_payload.get("joining_bonus"),
            retention_bonus=comp_payload.get("retention_bonus"),
        )
        db.add(comp)

    # Internship details if provided
    intern_payload = payload.get("internship")
    if intern_payload or payload.get("employment_type") == "INTERNSHIP":
        if intern_payload is None:
            intern_payload = {}
        # allow flat stipend fields
        if "stipend" not in intern_payload and comp_payload.get("stipend_min") is not None:
            intern_payload["stipend"] = comp_payload.get("stipend_min")
        intern = InternshipDetails(
            job_position_id=pos.id,
            duration_months=intern_payload.get("duration_months"),
            paid=not bool(comp_payload.get("is_unpaid", False)) if "paid" not in intern_payload else bool(intern_payload.get("paid")),
            stipend=intern_payload.get("stipend"),
            stipend_min=intern_payload.get("stipend_min") or comp_payload.get("stipend_min"),
            stipend_max=intern_payload.get("stipend_max") or comp_payload.get("stipend_max"),
            ppo_available=bool(intern_payload.get("ppo_available", False)),
            ppo_criteria=intern_payload.get("ppo_criteria"),
        )
        db.add(intern)

    # Skills
    for s in (payload.get("skills") or []):
        # s can be {skill_id} or {skill_name}
        skill = None
        if s.get("skill_id"):
            try:
                skill = db.get(Skill, uuid.UUID(s["skill_id"]))
            except ValueError:
                continue
        elif s.get("name"):
            skill = db.scalar(select(Skill).where(Skill.name == s["name"]))
        elif s.get("skill_name"):
            skill = db.scalar(select(Skill).where(Skill.name == s["skill_name"]))
        if not skill:
            continue
        # avoid duplicate
        exists = db.scalar(select(JobPositionSkill).where(JobPositionSkill.job_position_id == pos.id, JobPositionSkill.skill_id == skill.id))
        if exists:
            continue
        jps = JobPositionSkill(job_position_id=pos.id, skill_id=skill.id, mandatory=bool(s.get("mandatory", True)), skill_level=s.get("skill_level"), minimum_experience_months=s.get("minimum_experience_months"))
        db.add(jps)

    # Locations
    for loc in (payload.get("locations") or []):
        city = (loc.get("city") or "").strip()
        if not city:
            continue
        jl = JobLocation(job_position_id=pos.id, city=city, state=loc.get("state"), country=loc.get("country") or "India", work_mode=loc.get("work_mode"))
        db.add(jl)
    # legacy single location support (payload.location string)
    if payload.get("location") and not payload.get("locations"):
        # split by comma
        for city in [c.strip() for c in str(payload.get("location")).split(",") if c.strip()]:
            db.add(JobLocation(job_position_id=pos.id, city=city, country="India"))

    db.commit(); db.refresh(pos)
    return _position_out(pos, db)

# ---------- Eligibility ----------
@router.get("/drives/{drive_id}/eligibility-criteria")
def get_eligibility(drive_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    drive = db.get(Drive, drive_id)
    if not drive:
        raise HTTPException(404, "drive not found")
    crit = db.scalar(select(EligibilityCriteria).where(EligibilityCriteria.drive_id == drive_id))
    if not crit:
        return {}
    return {c.name: getattr(crit, c.name) for c in EligibilityCriteria.__table__.columns if c.name not in ("id","drive_id")}

@router.put("/drives/{drive_id}/eligibility-criteria")
def save_eligibility(drive_id: uuid.UUID, payload: dict, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    drive = db.get(Drive, drive_id)
    if not drive:
        raise HTTPException(404, "drive not found")
    crit = db.scalar(select(EligibilityCriteria).where(EligibilityCriteria.drive_id == drive_id))
    if not crit:
        crit = EligibilityCriteria(drive_id=drive_id); db.add(crit)
    for k, v in payload.items():
        if hasattr(crit, k):
            setattr(crit, k, v)
    db.commit(); db.refresh(crit)
    return {"ok": True}

# ---------- Branches / Batches ----------
@router.get("/drives/{drive_id}/branches")
def get_drive_branches(drive_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(DriveEligibleBranch).where(DriveEligibleBranch.drive_id == drive_id)).scalars().all()
    return [{"branch_id": str(r.branch_id)} for r in rows]

@router.put("/drives/{drive_id}/branches")
def save_drive_branches(drive_id: uuid.UUID, payload: dict, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    drive = db.get(Drive, drive_id)
    if not drive:
        raise HTTPException(404, "drive not found")
    ids = payload.get("branch_ids") or []
    db.query(DriveEligibleBranch).filter(DriveEligibleBranch.drive_id == drive_id).delete()
    for bid in ids:
        try:
            db.add(DriveEligibleBranch(drive_id=drive_id, branch_id=uuid.UUID(bid)))
        except ValueError:
            continue
    db.commit()
    return {"ok": True, "count": len(ids)}

@router.get("/drives/{drive_id}/batches")
def get_drive_batches(drive_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(DriveEligibleBatch).where(DriveEligibleBatch.drive_id == drive_id)).scalars().all()
    return [{"graduation_year": r.graduation_year} for r in rows]

@router.put("/drives/{drive_id}/batches")
def save_drive_batches(drive_id: uuid.UUID, payload: dict, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    drive = db.get(Drive, drive_id)
    if not drive:
        raise HTTPException(404, "drive not found")
    years = payload.get("years") or []
    db.query(DriveEligibleBatch).filter(DriveEligibleBatch.drive_id == drive_id).delete()
    for y in years:
        db.add(DriveEligibleBatch(drive_id=drive_id, graduation_year=int(y)))
    db.commit()
    return {"ok": True, "count": len(years)}

# ---------- Rounds & Schedules ----------
@router.get("/drives/{drive_id}/rounds")
def list_rounds(drive_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(DriveRound).where(DriveRound.drive_id == drive_id).order_by(DriveRound.sequence)).scalars().all()
    return [{"id": str(r.id), "name": r.name, "type": r.type, "sequence": r.sequence, "status": r.status} for r in rows]

@router.post("/drives/{drive_id}/rounds", status_code=201)
def create_round(drive_id: uuid.UUID, payload: dict, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    drive = db.get(Drive, drive_id)
    if not drive:
        raise HTTPException(404, "drive not found")
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "name required")
    seq = payload.get("sequence") or (len(drive.rounds) + 1 if hasattr(drive, 'rounds') else 1)
    r = DriveRound(drive_id=drive_id, sequence=int(seq), name=name, type=payload.get("type") or "OTHER", description=payload.get("description"), eliminatory=payload.get("eliminatory", True))
    db.add(r); db.commit(); db.refresh(r)
    return {"id": str(r.id), "name": r.name}

@router.get("/drives/{drive_id}/schedules")
def list_schedules(drive_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(DriveSchedule).where(DriveSchedule.drive_id == drive_id).order_by(DriveSchedule.start_time)).scalars().all()
    return [{"id": str(s.id), "event_name": s.event_name, "start_time": s.start_time.isoformat() if s.start_time else None} for s in rows]

@router.post("/drives/{drive_id}/schedules", status_code=201)
def create_schedule(drive_id: uuid.UUID, payload: dict, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    drive = db.get(Drive, drive_id)
    if not drive:
        raise HTTPException(404, "drive not found")
    s = DriveSchedule(drive_id=drive_id, event_name=payload.get("event_name") or "Event", start_time=payload.get("start_time") or datetime.utcnow(), end_time=payload.get("end_time") or datetime.utcnow(), venue=payload.get("venue"), meeting_link=payload.get("meeting_link"))
    db.add(s); db.commit(); db.refresh(s)
    return {"id": str(s.id)}

# ---------- Announcements / Policy / Publish / Pipeline ----------
@router.get("/drives/{drive_id}/announcements")
def list_announcements(drive_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(DriveAnnouncement).where(DriveAnnouncement.drive_id == drive_id).order_by(DriveAnnouncement.published_at.desc())).scalars().all()
    return [{"id": str(a.id), "title": a.title, "message": a.message, "announcement_type": a.announcement_type} for a in rows]

@router.post("/drives/{drive_id}/announcements", status_code=201)
def create_announcement(drive_id: uuid.UUID, payload: dict, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    drive = db.get(Drive, drive_id)
    if not drive:
        raise HTTPException(404, "drive not found")
    a = DriveAnnouncement(drive_id=drive_id, title=payload.get("title") or "Announcement", message=payload.get("message") or "", announcement_type=payload.get("announcement_type") or "GENERAL", published_by=admin.id)
    db.add(a); db.commit(); db.refresh(a)
    return {"id": str(a.id)}

@router.post("/drives/{drive_id}/publish")
def publish_drive(drive_id: uuid.UUID, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    drive = db.get(Drive, drive_id)
    if not drive:
        raise HTTPException(404, "drive not found")
    pos_exists = db.execute(select(JobPosition.id).where(JobPosition.drive_id == drive_id).limit(1)).first() is not None
    if not pos_exists:
        raise HTTPException(status_code=400, detail="at least one job position required before publishing")
    # Optional hardening: warn if no eligibility/batches set - still allow publish but inform
    crit = db.scalar(select(EligibilityCriteria).where(EligibilityCriteria.drive_id == drive_id))
    batches = db.execute(select(DriveEligibleBatch.id).where(DriveEligibleBatch.drive_id == drive_id).limit(1)).first() is not None
    if not crit and not batches:
        # allow but could require in future - log for admin awareness
        pass
    drive.status = "open"
    drive.published_at = datetime.utcnow()
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="failed to publish drive")
    return {"ok": True, "status": drive.status}


@router.get("/drives/{drive_id}/applications", tags=["applications"])
def list_drive_applications(
    drive_id: uuid.UUID, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)
):
    from app.db.models import Application, JobPosition, StudentProfile, User as UserModel

    drive = db.get(Drive, drive_id)
    if not drive:
        raise HTTPException(404, "drive not found")
    rows = db.execute(
        select(Application, UserModel, StudentProfile, JobPosition)
        .join(UserModel, Application.student_id == UserModel.id)
        .outerjoin(StudentProfile, StudentProfile.user_id == UserModel.id)
        .outerjoin(JobPosition, JobPosition.id == Application.job_position_id)
        .where(Application.drive_id == drive_id)
        .order_by(Application.created_at.desc())
    ).all()
    out = []
    for app_row, user_row, profile, job in rows:
        out.append(
            {
                "id": str(app_row.id),
                "drive_id": str(app_row.drive_id),
                "job_position_id": str(app_row.job_position_id) if app_row.job_position_id else None,
                "job_title": job.title if job else None,
                "job_role": job.role if job else None,
                "student_id": str(app_row.student_id),
                "student_name": user_row.full_name,
                "student_email": user_row.email,
                "branch": profile.branch if profile else None,
                "cgpa": float(profile.cgpa) if profile and profile.cgpa is not None else None,
                "graduation_year": profile.graduation_year if profile else None,
                "status": app_row.status,
                "created_at": app_row.created_at.isoformat() if app_row.created_at else None,
            }
        )
    return out

@router.get("/drives/{drive_id}/pipeline")
def get_pipeline(drive_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    drive = db.get(Drive, drive_id)
    if not drive:
        raise HTTPException(404, "drive not found")
    # aggregate counts for analytics / pipeline view
    from app.db.models import Application, DriveOffer, DriveSelection, PlacementOutcome, RoundResult
    from sqlalchemy import func as sa_func
    apps = db.scalar(select(sa_func.count()).select_from(Application).where(Application.drive_id == drive_id)) or 0
    return {
        "drive_id": str(drive_id),
        "title": drive.title,
        "status": drive.status,
        "applications": apps,
        "rounds": len(drive.rounds) if hasattr(drive, 'rounds') else 0,
        "message": "Pipeline data — extend with shortlist/selection counts as needed",
    }
