# Use-case entry points: prompt templates + structured generation, one per LLM use case.

from app.ai.llm_service import MODEL_LIGHT, MODEL_REASONING, generate_structured
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


def explain_eligibility(decision: dict, student: dict, drive: dict) -> EligibilityExplanation:
    return generate_structured(
        eligibility_explanation_prompt(decision, student, drive),
        schema=EligibilityExplanation,
        config=MODEL_REASONING,
    )


def explain_recommendation(
    student: dict, ranked_drives: list[dict]
) -> RecommendationExplanation:
    return generate_structured(
        recommendation_explanation_prompt(student, ranked_drives),
        schema=RecommendationExplanation,
        config=MODEL_REASONING,
    )


def answer_policy_question(question: str, context_chunks: list[dict]) -> PolicyAnswer:
    return generate_structured(
        policy_answer_prompt(question, context_chunks),
        schema=PolicyAnswer,
        config=MODEL_REASONING,
    )


def general_chat(user_message: str, history: list[dict] | None = None) -> ChatResponse:
    return generate_structured(
        general_chat_prompt(user_message, history),
        schema=ChatResponse,
        config=MODEL_LIGHT,
    )
