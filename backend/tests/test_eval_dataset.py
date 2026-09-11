# Offline validation of the eval dataset and metric helpers — runs in CI without services.

from app.eval.dataset import QUESTION_TYPES, load_dataset
from app.eval.metrics import (
    citation_accuracy,
    correctness,
    hallucination,
    is_declined,
    retrieval_recall,
)


def test_dataset_loads_and_has_enough_questions():
    questions = load_dataset()
    assert 20 <= len(questions) <= 30


def test_dataset_covers_all_question_types():
    types = {q.type for q in load_dataset()}
    assert types == QUESTION_TYPES


def test_dataset_ids_unique():
    ids = [q.id for q in load_dataset()]
    assert len(ids) == len(set(ids))


def test_questions_have_expected_criteria():
    for q in load_dataset():
        if q.expect_decline:
            assert not q.expected_contains
        else:
            assert q.expected_contains, f"{q.id} needs expected_contains"


def test_eligibility_questions_carry_a_student():
    for q in load_dataset():
        if q.type in {"am_i_eligible", "why_not_eligible", "recommendation"}:
            assert q.student_id, f"{q.id} needs a student_id"


# ---- metric helpers ----

def test_is_declined_detects_standard_refusal():
    assert is_declined("I don't have that information in the placement documents I was given.")
    assert not is_declined("The stipend is 35,000 rupees per month.")


def test_correctness_requires_all_keywords():
    assert correctness("CTC is 12 LPA", ["12"])
    assert not correctness("CTC is 12 LPA", ["12", "9.5"])
    assert correctness("anything", [])


def test_correctness_supports_or_alternatives():
    assert correctness("at most one backlog", [["one", "1"]])
    assert correctness("max 1 backlog", [["one", "1"]])
    assert not correctness("two backlogs", [["one", "1"]])
    assert correctness("12 LPA and 9.5 LPA", ["12", ["9.5", "nine point five"]])


def test_correctness_requires_decline_for_out_of_corpus():
    decline = "I don't have that information in the placement documents I was given."
    assert correctness(decline, [], expect_decline=True)
    assert not correctness("The capital of France is Paris.", [], expect_decline=True)


def test_correctness_fails_when_in_corpus_question_is_declined():
    assert not correctness("I don't have that information.", ["12"], expect_decline=False)
    assert correctness("The CTC is 12 LPA.", ["12"], expect_decline=False)


def test_citation_accuracy_handles_dicts_and_strings():
    assert citation_accuracy(["placement_policy_2026.pdf p.1"], "placement_policy_2026.pdf") is True
    assert citation_accuracy([{"source": "jd_nimbus.txt", "page_number": 1}], "jd_nimbus.txt") is True
    assert citation_accuracy([], "x.pdf") is False
    assert citation_accuracy(["a"], None) is None


def test_retrieval_recall():
    assert retrieval_recall(["placement_policy_2026.pdf"], "placement_policy_2026.pdf") is True
    assert retrieval_recall(["other.txt"], "placement_policy_2026.pdf") is False
    assert retrieval_recall([], None) is None


def test_hallucination_flags_answered_out_of_corpus():
    assert hallucination(True, "The capital of France is Paris.", []) is True
    assert hallucination(True, "I don't have that information.", []) is False
    assert hallucination(False, "I don't have that information.", ["12"]) is True
    assert hallucination(False, "Nimbus is 12 LPA.", ["12"]) is False