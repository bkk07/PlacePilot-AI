# CLI demo for the Phase 3 LangGraph agent — runs the four example workflows.
#
# Usage (from backend/, needs Weaviate running + GROQ_API_KEY):  python -m app.agent.cli_demo

import json
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from app.agent.runner import run_turn

WORKFLOWS = [
    ("eligibility_check", "Am I eligible for the Nimbus Software Engineer drive?"),
    ("policy_question", "How many active backlogs are allowed for placement?"),
    ("cross_company_query", "Compare the CTC offered by Nimbus and QuantAlpha"),
    ("recommendation", "Which drives should I apply to?"),
]


def main() -> None:
    student_id = "s-001"
    thread = "demo-thread"
    for expected, question in WORKFLOWS:
        print("=" * 80)
        print(f"[expected: {expected}]")
        print("Q:", question)
        out = run_turn(question, student_id=student_id, thread_id=thread)
        print("intent:", out["intent"])
        print("tools :", [t["name"] for t in out["planned_tools"]])
        print("A:", out["reply"])
        print()

    print("=" * 80)
    print("[follow-up — tests conversation persistence]")
    out = run_turn("What about the QuantAlpha one?", student_id=student_id, thread_id=thread)
    print("intent:", out["intent"])
    print("tools :", [t["name"] for t in out["planned_tools"]])
    print("A:", out["reply"])


if __name__ == "__main__":
    main()
