# Schemas for the agent's own structured LLM outputs (intent, tool selection).

from typing import Literal

from pydantic import BaseModel, Field

IntentKind = Literal[
    "eligibility_check",
    "policy_question",
    "cross_company_query",
    "recommendation",
    "general_chat",
]

ToolName = Literal[
    "search_drives",
    "get_drive_details",
    "get_student_profile",
    "check_eligibility",
    "get_application_status",
    "search_policy_docs",
    "get_recommendations",
]


class IntentClassification(BaseModel):
    intent: IntentKind
    entities: dict[str, str] = Field(
        default_factory=dict,
        description="Extracted entities, e.g. company/drive/role names mentioned by the user",
    )


class ToolCallSpec(BaseModel):
    name: ToolName
    args: dict[str, str] = Field(
        default_factory=dict,
        description="Arguments for the tool; use the entity ids exactly as given in the catalog",
    )


class ToolSelection(BaseModel):
    calls: list[ToolCallSpec] = Field(
        default_factory=list,
        description="Tool calls needed to answer the question; empty list for pure chat",
    )
