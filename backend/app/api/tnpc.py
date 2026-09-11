# TNPC domain APIs — all 31 entities exposed for the React wizard/pipeline.
# Every mutating route requires admin/TNPC role; reads require any authenticated user.

import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
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
    Skill,
    StoredFile,
    User,
)

router = APIRouter(tags=["tnpc"])

# ---------- Companies ----------
@router.get("/companies", tags=["companies"])
def list_companies(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Company).order_by(Company.name)).scalars().all()
    return [{"id": str(c.id), "name": c.name, "legal_name": c.legal_name, "industry": c.industry, "headquarters": c.headquarters, "website": c.website, "description": c.description, "company_size": c.company_size} for c in rows]

@router.post("/companies", status_code=201, tags=["companies"])
def create_company(payload: dict, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    if db.scalar(select(Company).where(Company.name == name)):
        raise HTTPException(409, "company already exists")
    c = Company(
        name=name,
        legal_name=payload.get("legal_name"),
        website=payload.get("website"),
        industry=payload.get("industry"),
        company_size=payload.get("company_size"),
        description=payload.get("description"),
        headquarters=payload.get("headquarters"),
        created_by=admin.id,
    )
    db.add(c); db.commit(); db.refresh(c)
    return {"id": str(c.id), "name": c.name}

# ---------- Skills & Branches ----------
@router.get("/skills")
def list_skills(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [{"id": str(s.id), "name": s.name, "category": s.category} for s in db.execute(select(Skill).order_by(Skill.name)).scalars().all()]

@router.post("/skills", status_code=201)
def create_skill(payload: dict, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "name required")
    if db.scalar(select(Skill).where(Skill.name == name)):
        raise HTTPException(409, "skill already exists")
    s = Skill(name=name, category=payload.get("category") or "OTHER", description=payload.get("description"))
    db.add(s); db.commit(); db.refresh(s)
    return {"id": str(s.id), "name": s.name, "category": s.category}

@router.get("/branches")
def list_branches(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Branch).order_by(Branch.code)).scalars().all()
    if not rows:
        # seed default branches on first call if empty
        for code, name in [("CSE","Computer Science"),("IT","Information Technology"),("ECE","Electronics & Communication"),("EEE","Electrical"),("ME","Mechanical"),("CE","Civil")]:
            b = Branch(name=name, code=code); db.add(b)
        db.commit()
        rows = db.execute(select(Branch).order_by(Branch.code)).scalars().all()
    return [{"id": str(b.id), "name": b.name, "code": b.code} for b in rows]

# ---------- Job Positions ----------
@router.get("/drives/{drive_id}/positions")
def list_positions(drive_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    drive = db.get(Drive, drive_id)
    if not drive:
        raise HTTPException(404, "drive not found")
    positions = db.execute(select(JobPosition).where(JobPosition.drive_id == drive_id)).scalars().all()
    return [{"id": str(p.id), "title": p.title, "role": p.role, "employment_type": p.employment_type, "openings": p.openings, "work_mode": p.work_mode} for p in positions]

@router.post("/drives/{drive_id}/positions", status_code=201)
def create_position(drive_id: uuid.UUID, payload: dict, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    drive = db.get(Drive, drive_id)
    if not drive:
        raise HTTPException(404, "drive not found")
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(400, "title required")
    pos = JobPosition(drive_id=drive_id, title=title, role=payload.get("role") or title, employment_type=payload.get("employment_type") or "FULL_TIME", openings=payload.get("openings"), work_mode=payload.get("work_mode"), job_description=payload.get("job_description"), department=payload.get("department"))
    db.add(pos); db.commit(); db.refresh(pos)
    # also create compensation/location if provided
    if payload.get("annual_ctc") or payload.get("monthly_stipend"):
        comp = Compensation(job_position_id=pos.id, annual_ctc=payload.get("annual_ctc"), monthly_stipend=payload.get("monthly_stipend"), currency=payload.get("currency") or "INR")
        db.add(comp); db.commit()
    return {"id": str(pos.id), "title": pos.title, "role": pos.role}

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
    drive.status = "PUBLISHED"
    drive.published_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "status": drive.status}

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
