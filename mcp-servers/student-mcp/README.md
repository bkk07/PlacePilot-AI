# student-mcp

MCP server for student-data tools (Phase 4): `get_student_profile`, `check_eligibility`, `get_application_status`.

Authorization rule: a student token can never access another student's data; every tool re-checks authz independently.
