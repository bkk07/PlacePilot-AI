# Eval dataset loading + validation.

import json
from pathlib import Path

from pydantic import BaseModel, Field

DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "eval" / "qa_dataset.json"

QUESTION_TYPES = {
    "stipend_lookup",
    "eligible_branches",
    "am_i_eligible",
    "why_not_eligible",
    "cross_company_ctc",
    "policy_question",
    "selection_process",
    "interview_experience",
    "recommendation",
    "out_of_corpus",
}


class EvalQuestion(BaseModel):
    id: str
    type: str
    question: str
    expected_contains: list[str | list[str]] = Field(default_factory=list)
    expected_source: str | None = None
    student_id: str | None = None
    expected_decision: bool | None = None
    expect_decline: bool = False
    note: str | None = None


def load_dataset(path: Path | None = None) -> list[EvalQuestion]:
    raw = json.loads((path or DATASET_PATH).read_text(encoding="utf-8"))
    return [EvalQuestion.model_validate(item) for item in raw]