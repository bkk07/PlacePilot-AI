# Shared implementation of placement/student tools backed by the real PostgreSQL.
# Each function is wrapped by tool_handler (authz + validation + audit) and exposed
# by one of the MCP servers in app/mcp/servers.py.

import uuid

from sqlalchemy import or_, select

from app.core.security import AuthContext
from app.db.db import get_session_factory
from app.db.models import (
    Application,
    Branch,
    Company,
    Drive,
    DriveEligibleBatch,
    DriveEligibleBranch,
    EligibilityCriteria,
    JobPosition,
    JobPositionSkill,
    Skill,
    StudentProfile,
    User,
)
from app.schemas.mcp_tool_schemas import (
    CheckEligibilityInput,
    CreateDriveInput,
    DriveIdInput,
    RecommendationsInput,
    SearchDrivesInput,
    StudentIdInput,
    UpdateApplicationStatusInput,
)
from app.services.application_state import STATUSES, InvalidTransition, transition
from app.services.eligibility import evaluate_eligibility


def _build_extended_criteria(session, drive_id) -> dict:
    """Merge the normalized TNPC tables (EligibilityCriteria / branches / batches)
    into the extended-criteria dict consumed by the eligibility engine — identical
    to the HTTP API path so the agent never contradicts /students/me/eligibility."""
    crit = session.scalar(select(EligibilityCriteria).where(EligibilityCriteria.drive_id == drive_id))
    branch_rows = session.execute(
        select(Branch.code)
        .join(DriveEligibleBranch, DriveEligibleBranch.branch_id == Branch.id)
        .where(DriveEligibleBranch.drive_id == drive_id)
    ).scalars().all()
    batch_rows = session.execute(
        select(DriveEligibleBatch.graduation_year).where(DriveEligibleBatch.drive_id == drive_id)
    ).scalars().all()
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


def _drive_dict(drive: Drive, company: Company, include_rules: bool = True) -> dict:
    d = {
        "id": str(drive.id),
        "title": drive.title,
        "company": company.name,
        "role": drive.role,
        "ctc_lpa": float(drive.ctc_lpa) if drive.ctc_lpa is not None else None,
        "stipend_monthly": float(drive.stipend_monthly) if drive.stipend_monthly is not None else None,
        "location": drive.location,
        "application_deadline": drive.application_deadline,
        "status": drive.status,
        "skills": drive.skills,
    }
    if include_rules:
        d["rules"] = drive.rules
    return d


def _resolve_student(session, student_id: str) -> dict | None:
    try:
        sid = uuid.UUID(student_id)
    except ValueError:
        return None
    row = session.execute(
        select(User, StudentProfile).join(StudentProfile, StudentProfile.user_id == User.id).where(User.id == sid)
    ).first()
    if row is None:
        return None
    user, profile = row
    return {
        "id": str(user.id),
        "name": user.full_name,
        "branch": profile.branch,
        "cgpa": float(profile.cgpa) if profile.cgpa is not None else None,
        "active_backlogs": profile.active_backlogs,
        "graduation_year": profile.graduation_year,
        "skills": profile.skills,
    }


def search_drives_impl(auth: AuthContext, inp: SearchDrivesInput) -> dict:
    session = get_session_factory()()
    try:
        stmt = (
            select(Drive, Company)
            .join(Company, Drive.company_id == Company.id)
            .where(Drive.status == "open")
        )
        if inp.company:
            stmt = stmt.where(Company.name.ilike(f"%{inp.company}%"))
        if inp.role:
            stmt = stmt.where(Drive.role.ilike(f"%{inp.role}%"))
        rows = session.execute(stmt).all()
        results = []
        for drive, company in rows:
            if inp.query:
                haystack = " ".join(
                    [drive.title, drive.role, company.name, drive.location, " ".join(drive.skills)]
                ).lower()
                if inp.query.lower() not in haystack:
                    continue
            results.append(_drive_dict(drive, company, include_rules=False))
        return {"drives": results}
    finally:
        session.close()


def get_drive_details_impl(auth: AuthContext, inp: DriveIdInput) -> dict:
    session = get_session_factory()()
    try:
        try:
            did = uuid.UUID(inp.drive_id)
        except ValueError:
            return {"error": "drive not found"}
        row = session.execute(
            select(Drive, Company).join(Company, Drive.company_id == Company.id).where(Drive.id == did)
        ).first()
        if row is None:
            return {"error": "drive not found"}
        return _drive_dict(row[0], row[1], include_rules=True)
    finally:
        session.close()


def get_student_profile_impl(auth: AuthContext, inp: StudentIdInput) -> dict:
    from app.mcp.tool_guard import require_owner

    require_owner(auth, inp.student_id)
    session = get_session_factory()()
    try:
        student = _resolve_student(session, inp.student_id)
        if student is None:
            return {"error": "student not found"}
        return student
    finally:
        session.close()


def check_eligibility_impl(auth: AuthContext, inp: CheckEligibilityInput) -> dict:
    from app.mcp.tool_guard import require_owner

    require_owner(auth, inp.student_id)
    session = get_session_factory()()
    try:
        student = _resolve_student(session, inp.student_id)
        if student is None:
            return {"error": "student not found"}

        target = None
        if inp.drive_id:
            try:
                did = uuid.UUID(inp.drive_id)
            except ValueError:
                did = None
            if did is not None:
                target = session.get(Drive, did)
        if target is None:
            name = inp.drive or inp.drive_id
            if name:
                rows = session.execute(
                    select(Drive, Company)
                    .join(Company, Drive.company_id == Company.id)
                    .where(or_(Drive.title.ilike(f"%{name}%"), Company.name.ilike(f"%{name}%"), Drive.role.ilike(f"%{name}%")))
                ).all()
                if len(rows) == 1:
                    target = rows[0][0]
                elif len(rows) > 1:
                    return {"error": "multiple drives matched", "matched": [str(r[0].id) for r in rows]}
        if target is None:
            return {"error": "drive not found"}

        drive_dict = _drive_dict(target, target.company)
        extended = _build_extended_criteria(session, target.id)
        result = evaluate_eligibility(student, {"rules": drive_dict.get("rules") or {}, "extended": extended})
        return {
            "student_id": inp.student_id,
            "drive_id": str(target.id),
            "drive_title": target.title,
            "eligible": result.eligible,
            "reasons": result.reasons,
            "missing_requirements": result.missing_requirements,
        }
    finally:
        session.close()


def get_application_status_impl(auth: AuthContext, inp: StudentIdInput) -> dict:
    from app.mcp.tool_guard import require_owner

    require_owner(auth, inp.student_id)
    session = get_session_factory()()
    try:
        try:
            sid = uuid.UUID(inp.student_id)
        except ValueError:
            return {"error": "student not found"}
        rows = session.execute(select(Application, Drive).join(Drive, Application.drive_id == Drive.id).where(Application.student_id == sid)).all()
        return {
            "applications": [
                {
                    "application_id": str(app.id),
                    "drive_id": str(app.drive_id),
                    "drive_title": drive.title,
                    "status": app.status,
                }
                for app, drive in rows
            ]
        }
    finally:
        session.close()


def get_recommendations_impl(auth: AuthContext, inp: RecommendationsInput) -> dict:
    from app.mcp.tool_guard import require_owner

    require_owner(auth, inp.student_id)
    session = get_session_factory()()
    try:
        student = _resolve_student(session, inp.student_id)
        if student is None:
            return {"error": "student not found"}
        rows = session.execute(
            select(Drive, Company).join(Company, Drive.company_id == Company.id).where(Drive.status == "open")
        ).all()
        out = []
        for drive, company in rows:
            drive_dict = _drive_dict(drive, company)
            extended = _build_extended_criteria(session, drive.id)
            # Per-role skills union (TNPC wizard) preferred over legacy drive.skills
            role_skills = set(
                session.execute(
                    select(Skill.name).where(
                        JobPositionSkill.job_position_id.in_(
                            select(JobPosition.id).where(JobPosition.drive_id == drive.id)
                        )
                    )
                ).scalars().all()
            ) or set(drive.skills or [])

            # — Weighted score: Skill 40% / Eligibility 20% / Role 20% / CTC 10% / Location 10% —
            matched = [s for s in role_skills if s in student["skills"]]
            skill_score = (len(matched) / len(role_skills)) if role_skills else 0.0

            result = evaluate_eligibility(student, {"rules": drive_dict.get("rules") or {}, "extended": extended})
            elig_score = 1.0 if result.eligible else 0.0

            role_score = 0.0
            student_role = (student.get("skills") or [])
            if drive.role:
                role_words = {w.lower() for w in str(drive.role).replace("-", " ").split() if len(w) > 2}
                student_text = " ".join(student_role).lower()
                role_score = min(1.0, sum(1 for w in role_words if w in student_text) / len(role_words)) if role_words else 0.0

            ctc = drive_dict.get("ctc_lpa")
            # normalize CTC against a 20 LPA ceiling for the 10% weight
            ctc_score = min(1.0, (float(ctc) / 20.0)) if ctc is not None else 0.0

            location_score = 0.0
            if drive.location:
                # remote/hybrid drives match everyone; else neutral 0.5
                location_score = 1.0 if "remote" in str(drive.location).lower() else 0.5

            score = round(
                0.4 * skill_score
                + 0.2 * elig_score
                + 0.2 * role_score
                + 0.1 * ctc_score
                + 0.1 * location_score,
                3,
            )
            out.append(
                {
                    "drive_id": drive_dict["id"],
                    "title": drive_dict["title"],
                    "company": drive_dict["company"],
                    "matched_skills": matched,
                    "eligible": result.eligible,
                    "score": score,
                    "score_breakdown": {
                        "skill": round(skill_score, 2),
                        "eligibility": elig_score,
                        "role": round(role_score, 2),
                        "ctc": round(ctc_score, 2),
                        "location": location_score,
                    },
                }
            )
        return {"recommendations": sorted(out, key=lambda d: d["score"], reverse=True)}
    finally:
        session.close()


def create_drive_impl(auth: AuthContext, inp: CreateDriveInput) -> dict:
    from app.mcp.tool_guard import require_admin

    require_admin(auth)
    session = get_session_factory()()
    try:
        try:
            cid = uuid.UUID(inp.company_id)
        except ValueError:
            return {"error": "company not found"}
        company = session.get(Company, cid)
        if company is None:
            return {"error": "company not found"}
        drive = Drive(
            company_id=cid,
            title=inp.title,
            role=inp.role,
            ctc_lpa=inp.ctc_lpa,
            stipend_monthly=inp.stipend_monthly,
            location=inp.location,
            application_deadline=inp.application_deadline,
            status="open",
            skills=inp.skills,
            rules=inp.rules,
        )
        session.add(drive)
        session.commit()
        return {"created": True, "drive_id": str(drive.id), "title": drive.title}
    finally:
        session.close()


def update_application_status_impl(auth: AuthContext, inp: UpdateApplicationStatusInput) -> dict:
    from uuid import UUID

    from app.mcp.tool_guard import require_admin

    require_admin(auth)
    if inp.new_status not in STATUSES:
        return {"error": f"invalid status; must be one of {sorted(STATUSES)}", "code": "invalid_input"}
    session = get_session_factory()()
    try:
        try:
            aid = UUID(inp.application_id)
        except ValueError:
            return {"error": "application not found"}
        app_row = session.get(Application, aid)
        if app_row is None:
            return {"error": "application not found"}
        old = app_row.status
        try:
            transition(
                session,
                app_row,
                inp.new_status,
                changed_by=UUID(auth.user_id),
                reason=inp.reason or None,
            )
        except InvalidTransition as exc:
            # Same state machine as the HTTP API — the MCP path must not bypass it.
            from app.services.application_state import ALLOWED_TRANSITIONS

            return {
                "error": f"invalid transition: {exc}",
                "code": "invalid_transition",
                "allowed_next": sorted(ALLOWED_TRANSITIONS.get(old, set())),
            }
        return {"updated": True, "application_id": str(aid), "from": old, "to": inp.new_status}
    finally:
        session.close()
