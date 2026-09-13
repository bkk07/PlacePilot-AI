# Phase 4 tests: MCP tool authorization through the running servers.
# These exercise the REAL servers over streamable-http — the negative test required
# by the plan (student A's token must fail when fetching student B's data).

import asyncio
import uuid

import pytest
from sqlalchemy import select

from app.agent.mcp_client import call_tool, list_tools
from app.core.security import create_token
from app.db.db import get_session_factory
from app.db.models import User

STUDENT_A_EMAIL = "asha@college.edu"
STUDENT_B_EMAIL = "rohan@college.edu"
ADMIN_EMAIL = "placement@college.edu"


def _token_for(email: str, role: str) -> str:
    session = get_session_factory()()
    try:
        user = session.scalar(select(User).where(User.email == email))
        return create_token(str(user.id), role)
    finally:
        session.close()


def _id_for(email: str) -> str:
    session = get_session_factory()()
    try:
        user = session.scalar(select(User).where(User.email == email))
        return str(user.id)
    finally:
        session.close()


def _servers_up() -> bool:
    async def check():
        tools = await list_tools("")
        return len(tools) >= 8

    try:
        return asyncio.run(asyncio.wait_for(check(), timeout=10))
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _servers_up(), reason="MCP servers not running on 8101-8103")


def test_servers_expose_expected_tools():
    tools = asyncio.run(list_tools(""))
    names = {t["name"] for t in tools}
    assert {
        "search_drives",
        "get_drive_details",
        "create_drive",
        "update_application_status",
        "get_student_profile",
        "check_eligibility",
        "get_application_status",
        "get_recommendations",
        "search_policy_docs",
    } <= names


def test_happy_path_student_reads_own_profile():
    token = _token_for(STUDENT_A_EMAIL, "student")
    result = asyncio.run(call_tool("get_student_profile", token, {"student_id": _id_for(STUDENT_A_EMAIL)}))
    assert result["name"] == "Asha Verma"


# ---- THE negative test from the plan ----

def test_student_a_cannot_read_student_b_profile():
    token_a = _token_for(STUDENT_A_EMAIL, "student")
    result = asyncio.run(call_tool("get_student_profile", token_a, {"student_id": _id_for(STUDENT_B_EMAIL)}))
    assert "error" in result
    assert "forbidden" in result["error"]


def test_student_a_cannot_check_student_b_eligibility():
    token_a = _token_for(STUDENT_A_EMAIL, "student")
    result = asyncio.run(
        call_tool("check_eligibility", token_a, {"student_id": _id_for(STUDENT_B_EMAIL), "drive": "QuantAlpha"})
    )
    assert "error" in result
    assert "forbidden" in result["error"]


def test_student_a_cannot_read_student_b_applications():
    token_a = _token_for(STUDENT_A_EMAIL, "student")
    result = asyncio.run(call_tool("get_application_status", token_a, {"student_id": _id_for(STUDENT_B_EMAIL)}))
    assert "error" in result
    assert "forbidden" in result["error"]


# ---- admin-only tools blocked for students at the MCP layer ----

def test_student_cannot_create_drive():
    token = _token_for(STUDENT_A_EMAIL, "student")
    result = asyncio.run(
        call_tool(
            "create_drive",
            token,
            {
                "title": "Fake Drive",
                "company_id": str(uuid.uuid4()),
                "role": "X",
                "location": "X",
                "application_deadline": "2026-12-01",
            },
        )
    )
    assert "error" in result
    assert "forbidden" in result["error"]


def test_student_cannot_update_application_status():
    token = _token_for(STUDENT_A_EMAIL, "student")
    result = asyncio.run(
        call_tool("update_application_status", token, {"application_id": str(uuid.uuid4()), "new_status": "selected"})
    )
    assert "error" in result
    assert "forbidden" in result["error"]


def test_admin_can_create_drive():
    token = _token_for(ADMIN_EMAIL, "admin")
    session = get_session_factory()()
    from app.db.models import Company

    company = session.scalar(select(Company).order_by(Company.created_at))
    session.close()
    if company is None:
        pytest.skip("no companies seeded in the database")
    result = asyncio.run(
        call_tool(
            "create_drive",
            token,
            {
                "title": "Admin Test Drive (delete me)",
                "company_id": str(company.id),
                "role": "Test",
                "location": "Nowhere",
                "application_deadline": "2026-12-01",
            },
        )
    )
    assert result.get("created") is True
    # cleanup: remove the test drive directly from the DB
    from sqlalchemy import text

    from app.db.db import get_engine

    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM drives WHERE title = 'Admin Test Drive (delete me)'"))


def test_garbage_token_rejected():
    result = asyncio.run(call_tool("get_student_profile", "not-a-jwt", {"student_id": _id_for(STUDENT_A_EMAIL)}))
    assert "error" in result
    assert "unauthorized" in result["error"]


def test_invalid_input_rejected_by_pydantic():
    token = _token_for(STUDENT_A_EMAIL, "student")
    # query too short for PolicyQueryInput (min_length=3)
    result = asyncio.run(call_tool("search_policy_docs", token, {"query": "ab"}))
    assert "error" in result


def test_cross_student_blocked_even_with_forged_claims():
    # A token is the ONLY identity source — args claiming another id don't help.
    token_a = _token_for(STUDENT_A_EMAIL, "student")
    result = asyncio.run(
        call_tool("get_recommendations", token_a, {"student_id": _id_for(STUDENT_B_EMAIL)})
    )
    assert "error" in result
    assert "forbidden" in result["error"]


def test_invalid_status_transition_blocked_by_state_machine():
    # The MCP path must enforce the same state machine as the HTTP API:
    # e.g. a 'selected' application can never move again (terminal state).
    token = _token_for(ADMIN_EMAIL, "admin")
    session = get_session_factory()()
    from app.db.models import Application

    app_row = session.execute(
        select(Application).where(Application.status == "selected").limit(1)
    ).scalar_one_or_none()
    if app_row is None:
        # Create a terminal-state application directly for the test.
        app_row = session.execute(select(Application).limit(1)).scalar_one_or_none()
        if app_row is None:
            pytest.skip("no applications in the database to test transitions")
        app_row.status = "selected"
        session.commit()
    session.close()

    result = asyncio.run(
        call_tool(
            "update_application_status",
            token,
            {"application_id": str(app_row.id), "new_status": "applied", "reason": "test"},
        )
    )
    assert "error" in result
    assert result.get("code") == "invalid_transition"


def test_health_tool_available():
    result = asyncio.run(call_tool("health", "", {}))
    assert result.get("status") == "ok"
