# CLI demo for the agent — now running tools through the three MCP servers (Phase 4).
#
# Prereqs: Postgres seeded (python -m app.db.seed), Weaviate ingested, and the three
# MCP servers running (placement 8101, student 8102, knowledge 8103).
#
# Usage (from backend/):  python -m app.agent.cli_demo

import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select

from app.agent.runner import run_turn
from app.core.security import create_token
from app.db.db import get_session_factory
from app.db.models import User

WORKFLOWS = [
    ("eligibility_check", "Am I eligible for the Nimbus Software Engineer drive?"),
    ("policy_question", "How many active backlogs are allowed for placement?"),
    ("cross_company_query", "Compare the CTC offered by Nimbus and QuantAlpha"),
    ("recommendation", "Which drives should I apply to?"),
]


def _dev_token(email: str) -> tuple[str, str]:
    session = get_session_factory()()
    try:
        user = session.scalar(select(User).where(User.email == email))
        return str(user.id), create_token(str(user.id), user.role)
    finally:
        session.close()


def main() -> None:
    student_id, token = _dev_token("asha@college.edu")
    other_id, _ = _dev_token("rohan@college.edu")
    print(f"student: {student_id} (asha) | other student: {other_id} (rohan)\n")

    thread = "demo-thread"
    for expected, question in WORKFLOWS:
        print("=" * 80)
        print(f"[expected: {expected}]")
        print("Q:", question)
        out = run_turn(question, student_id=student_id, thread_id=thread, token=token)
        print("intent:", out["intent"])
        print("tools :", [t["name"] for t in out["planned_tools"]])
        print("A:", out["reply"])
        print()

    print("=" * 80)
    print("[NEGATIVE AUTHZ TEST — student A token, student B's id]")
    from app.agent.mcp_client import call_tool

    result = call_tool_sync("get_student_profile", token, {"student_id": other_id})
    print("get_student_profile(rohan) with asha's token ->", result)
    print()

    print("=" * 80)
    print("[follow-up — tests conversation persistence]")
    out = run_turn("What about the QuantAlpha one?", student_id=student_id, thread_id=thread, token=token)
    print("intent:", out["intent"])
    print("tools :", [t["name"] for t in out["planned_tools"]])
    print("A:", out["reply"])


def call_tool_sync(tool_name: str, token: str, args: dict) -> dict:
    import asyncio

    from app.agent.mcp_client import call_tool

    return asyncio.run(call_tool(tool_name, token, args))


if __name__ == "__main__":
    main()
