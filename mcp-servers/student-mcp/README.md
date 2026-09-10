# student-mcp

Served from `backend/app/mcp/servers.py` — run with `python -m app.mcp.run student` (port 8102).

Tools: `get_student_profile`, `check_eligibility`, `get_application_status`, `get_recommendations`.

Authorization rule: the token is the only identity source, and `student_id` arguments must match the
caller — a student can never read another student's data. Eligibility is decided by the deterministic
engine in `backend/app/services/eligibility.py`; the LLM only explains it.