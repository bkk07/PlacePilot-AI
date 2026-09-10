# Prompt-template tests: each use case builds the right messages and embeds its schema.

import json

from app.ai.prompts import (
    eligibility_explanation_prompt,
    general_chat_prompt,
    policy_answer_prompt,
    recommendation_explanation_prompt,
)
from app.schemas.llm_schemas import (
    ChatResponse,
    EligibilityExplanation,
    PolicyAnswer,
    RecommendationExplanation,
)


def test_eligibility_prompt_structure_and_schema():
    msgs = eligibility_explanation_prompt(
        decision={"eligible": False},
        student={"cgpa": 6.2},
        drive={"title": "Nimbus SDE", "min_cgpa": 7.0},
    )
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert '"EligibilityExplanation"' in msgs[0]["content"]
    assert EligibilityExplanation.model_json_schema()["properties"]["eligible"]["type"] in msgs[0]["content"]
    assert "6.2" in msgs[1]["content"] and "7.0" in msgs[1]["content"]
    assert "never contradict" in msgs[0]["content"].lower()


def test_recommendation_prompt_includes_ranked_drives_and_schema():
    msgs = recommendation_explanation_prompt(
        student={"skills": ["python"]},
        ranked_drives=[{"title": "Nimbus SDE", "score": 0.9}],
    )
    assert "Nimbus SDE" in msgs[1]["content"]
    assert '"RecommendationExplanation"' in msgs[0]["content"]


def test_policy_answer_prompt_includes_chunks_and_citation_rules():
    chunks = [{"source": "policy.pdf", "page_number": 2, "text": "one backlog allowed"}]
    msgs = policy_answer_prompt("How many backlogs?", chunks)
    assert "policy.pdf p.2" in msgs[1]["content"]
    assert "grounded" in msgs[0]["content"]
    assert "don't have that information" in msgs[0]["content"]


def test_general_chat_prompt_appends_history():
    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    msgs = general_chat_prompt("What can you do?", history)
    assert msgs[0]["role"] == "system"
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "user"]
    assert "What can you do?" == msgs[-1]["content"]


def test_general_chat_prompt_no_history():
    msgs = general_chat_prompt("hello")
    assert len(msgs) == 2


def test_schema_instruction_has_valid_json():
    msgs = eligibility_explanation_prompt({}, {}, {})
    schema_part = msgs[0]["content"].split("{", 1)[1].rsplit("}", 1)[0]
    parsed = json.loads("{" + schema_part + "}")
    assert "properties" in parsed
