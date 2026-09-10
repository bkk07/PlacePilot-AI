# One prompt template per use case — separate functions, never one giant prompt.

import json

from app.schemas.llm_schemas import (
    ChatResponse,
    EligibilityExplanation,
    PolicyAnswer,
    RecommendationExplanation,
)


def _schema_instruction(schema_name: str, schema: type) -> str:
    return (
        f'Respond with ONLY a JSON object matching this schema (schema name: "{schema_name}"): '
        f"{json.dumps(schema.model_json_schema())}"
    )


def eligibility_explanation_prompt(
    decision: dict,
    student: dict,
    drive: dict,
) -> list[dict]:
    """Explain the rule engine's decision. The LLM explains — it never determines eligibility."""
    system = (
        "You are a placement assistant. You are GIVEN the eligibility decision made by a "
        "deterministic rule engine. Your job is only to explain it clearly and empathetically. "
        "Never contradict the given decision. Never invent requirements not present in the data. "
        + _schema_instruction("EligibilityExplanation", EligibilityExplanation)
    )
    user = (
        f"Rule engine decision: {json.dumps(decision)}\n\n"
        f"Student profile: {json.dumps(student)}\n\n"
        f"Drive and its eligibility rules: {json.dumps(drive)}\n\n"
        "Explain this decision for the student."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def recommendation_explanation_prompt(
    student: dict,
    ranked_drives: list[dict],
) -> list[dict]:
    """Explain why these drives were recommended for this student."""
    system = (
        "You are a placement assistant. You are GIVEN a ranked list of recommended drives "
        "produced by a deterministic recommendation engine. Explain the ranking in student-friendly "
        "language, referencing actual skill matches from the data. Do not invent facts. "
        + _schema_instruction("RecommendationExplanation", RecommendationExplanation)
    )
    user = (
        f"Student profile: {json.dumps(student)}\n\n"
        f"Recommended drives (ranked): {json.dumps(ranked_drives)}\n\n"
        "Explain why these drives suit this student."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def policy_answer_prompt(question: str, context_chunks: list[dict]) -> list[dict]:
    """Grounded policy Q&A: answer ONLY from the given chunks, with citations, or decline."""
    system = (
        "You are a placement-cell assistant. Answer ONLY from the provided context chunks. "
        "Cite every factual claim with the chunk's source and page_number, quoting the exact "
        "supporting text. If the context does not contain the answer, set grounded=false and "
        "make the answer exactly: 'I don't have that information in the placement documents I was "
        "given.' Never invent company names, CTC figures, stipends, dates, or selection rounds. "
        + _schema_instruction("PolicyAnswer", PolicyAnswer)
    )
    parts = []
    for c in context_chunks:
        parts.append(f"[{c.get('source')} p.{c.get('page_number')}]\n{c.get('text')}")
    user = (
        f"Context chunks:\n\n{'-' * 40}\n" + f"\n{'-' * 40}\n\n".join(parts)
        + f"\n{'-' * 40}\n\nQuestion: {question}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def general_chat_prompt(user_message: str, history: list[dict] | None = None) -> list[dict]:
    """Lightweight general chat turn for the assistant."""
    system = (
        "You are a friendly campus placement assistant. Answer helpfully and concisely. "
        "For anything about specific drives, eligibility, or placement policy, say you will "
        "look it up rather than guessing. "
        + _schema_instruction("ChatResponse", ChatResponse)
    )
    messages = [{"role": "system", "content": system}]
    for turn in history or []:
        messages.append(turn)
    messages.append({"role": "user", "content": user_message})
    return messages
