# The five MVP tools as plain Python functions over seeded data, plus the
# Weaviate policy retriever wired in as a tool (Phase 4 moves these into MCP servers).

from app.agent.seed_data import APPLICATIONS, COMPANIES, DRIVES, STUDENTS
from app.ai.retriever import retrieve
from app.services.eligibility import evaluate_eligibility


def search_drives(query: str = "", company: str = "", role: str = "") -> list[dict]:
    """Search drives: free text OR-matches title/company/role/location/skills;
    company and role are narrowing filters (substring match)."""
    results = []
    for drive in DRIVES.values():
        company_name = COMPANIES[drive["company_id"]]["name"]
        if company and company.lower() not in company_name.lower():
            continue
        if role and role.lower() not in drive["role"].lower():
            continue
        if query:
            haystack = " ".join(
                [drive["title"], drive["role"], company_name, drive["location"], " ".join(drive["skills"])]
            ).lower()
            if query.lower() not in haystack:
                continue
        results.append({k: v for k, v in drive.items() if k != "rules"})
    return results


def get_drive_details(drive_id: str) -> dict | None:
    """Full details for one drive, including eligibility rules."""
    return DRIVES.get(drive_id)


def get_student_profile(student_id: str) -> dict | None:
    """Fetch a student profile. Phase 4 will enforce ownership via MCP authz."""
    return STUDENTS.get(student_id)


def check_eligibility(student_id: str, drive_id: str = "", drive: str = "") -> dict:
    """Run the deterministic eligibility engine for a student against a drive.

    The drive may be given by exact id (d-001), or resolved by company/role name
    via search when only a name is known. Exactly one drive must resolve.
    """
    student = STUDENTS.get(student_id)
    if student is None:
        return {"error": "student not found", "student_id": student_id}

    target = DRIVES.get(drive_id) if drive_id else None
    if target is None:
        name = drive or drive_id
        matches = search_drives(query=name) if name else []
        if len(matches) == 1:
            target = DRIVES.get(matches[0]["id"])
        elif len(matches) > 1:
            return {
                "error": "multiple drives matched; specify the exact drive_id",
                "matched_drive_ids": [d["id"] for d in matches],
            }
    if target is None:
        return {"error": "drive not found", "student_id": student_id, "drive_id": drive_id}

    result = evaluate_eligibility(student, target)
    return {
        "student_id": student_id,
        "drive_id": target["id"],
        "drive_title": target["title"],
        "eligible": result.eligible,
        "reasons": result.reasons,
        "missing_requirements": result.missing_requirements,
    }


def get_application_status(student_id: str) -> list[dict]:
    """All applications + statuses for one student."""
    out = []
    for app in APPLICATIONS.values():
        if app["student_id"] != student_id:
            continue
        drive = DRIVES[app["drive_id"]]
        out.append(
            {
                "application_id": app["id"],
                "drive_id": app["drive_id"],
                "drive_title": drive["title"],
                "status": app["status"],
            }
        )
    return out


def search_policy_docs(query: str, top_k: int = 3) -> list[dict]:
    """RAG over placement documents via the Phase 1 Weaviate retriever."""
    chunks = retrieve(query, top_k=top_k)
    return [
        {
            "text": c.text,
            "source": c.source,
            "page_number": c.page_number,
            "company": c.company,
            "document_type": c.document_type,
        }
        for c in chunks
    ]


def get_recommendations(student_id: str) -> list[dict]:
    """Simple skill-match recommendations (the full weighted engine arrives in Phase 8)."""
    student = STUDENTS.get(student_id)
    if student is None:
        return []
    out = []
    for drive in DRIVES.values():
        if drive["status"] != "open":
            continue
        matched = [s for s in drive["skills"] if s in student["skills"]]
        result = evaluate_eligibility(student, drive)
        score = round(
            0.4 * (len(matched) / len(drive["skills"]) if drive["skills"] else 0)
            + 0.2 * result.eligible,
            2,
        )
        out.append(
            {
                "drive_id": drive["id"],
                "title": drive["title"],
                "company": COMPANIES[drive["company_id"]]["name"],
                "matched_skills": matched,
                "eligible": result.eligible,
                "score": score,
            }
        )
    return sorted(out, key=lambda d: d["score"], reverse=True)


TOOLS: dict[str, dict] = {
    "search_drives": {
        "fn": search_drives,
        "arg_names": ["query", "company", "role"],
        "description": "Search/filter placement drives by free text, company, or role.",
    },
    "get_drive_details": {
        "fn": get_drive_details,
        "arg_names": ["drive_id"],
        "description": "Get full details for one drive by its id (e.g. d-001), including eligibility rules.",
    },
    "get_student_profile": {
        "fn": get_student_profile,
        "arg_names": ["student_id"],
        "description": "Get a student's profile by id (e.g. s-001).",
    },
    "check_eligibility": {
        "fn": check_eligibility,
        "arg_names": ["student_id", "drive_id", "drive"],
        "description": "Check whether a student is eligible for a drive. Pass drive_id (e.g. d-001) if known, otherwise pass the drive/company name in 'drive' and it will be resolved.",
    },
    "get_application_status": {
        "fn": get_application_status,
        "arg_names": ["student_id"],
        "description": "Get all applications and their statuses for a student.",
    },
    "search_policy_docs": {
        "fn": search_policy_docs,
        "arg_names": ["query"],
        "description": "Search placement policy documents and job descriptions for a question.",
    },
    "get_recommendations": {
        "fn": get_recommendations,
        "arg_names": ["student_id"],
        "description": "Get recommended drives ranked by skill match and eligibility for a student.",
    },
}


def execute_tool(name: str, args: dict) -> dict:
    """Validate the tool name and args, execute, and return a JSON-serializable result."""
    spec = TOOLS.get(name)
    if spec is None:
        return {"error": f"unknown tool: {name}"}
    unknown = [a for a in args if a not in spec["arg_names"]]
    if unknown:
        return {"error": f"unknown arguments for {name}: {unknown}"}
    try:
        return spec["fn"](**args)
    except Exception as exc:  # tool failure returns a partial answer, never crashes the run
        return {"error": f"tool {name} failed: {exc}"}
