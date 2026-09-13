# Eval dataset loading + validation.

import json
from pathlib import Path

from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "eval"
DATASET_PATH = DATA_DIR / "qa_dataset.json"
# Expanded-corpus question set (21 docs); loaded via load_dataset(path=...) or --set jsonl.
JSONL_DATASET_PATH = DATA_DIR / "rag_eval_questions_new.jsonl"

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
    target = path or DATASET_PATH
    if target.suffix == ".jsonl":
        items = [
            json.loads(line)
            for line in target.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        items = json.loads(target.read_text(encoding="utf-8"))
    return [EvalQuestion.model_validate(item) for item in items]