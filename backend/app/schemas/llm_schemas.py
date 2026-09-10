# Pydantic schemas for every structured LLM output in the system.
# Malformed LLM output is rejected against these — never passed downstream as-is.

from pydantic import BaseModel, Field


class Citation(BaseModel):
    source: str = Field(description="Document source identifier or filename")
    page_number: int = Field(ge=1, description="1-indexed page the cited text came from")
    quote: str = Field(description="Short supporting quote from the source")


class EligibilityExplanation(BaseModel):
    eligible: bool
    summary: str = Field(description="One-line restatement of the engine's decision")
    reasons: list[str] = Field(description="Why the student is or is not eligible")
    missing_requirements: list[str] = Field(
        default_factory=list,
        description="Unmet criteria, empty if eligible",
    )


class RecommendationExplanation(BaseModel):
    summary: str = Field(description="Why these drives were recommended for this student")
    skill_matches: list[str] = Field(default_factory=list)
    advice: str = Field(description="One actionable improvement suggestion")


class PolicyAnswer(BaseModel):
    answer: str = Field(description="Answer grounded ONLY in the provided context chunks")
    citations: list[Citation] = Field(default_factory=list)
    grounded: bool = Field(
        description="False when the context does not contain the answer; answer must then be the decline message"
    )


class ChatResponse(BaseModel):
    reply: str
    used_tool: bool = Field(default=False, description="Whether a data/RAG tool was invoked")
    tool_names: list[str] = Field(default_factory=list)
