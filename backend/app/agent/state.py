# LangGraph agent state object.

from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages

IntentKind = Literal[
    "eligibility_check",
    "policy_question",
    "cross_company_query",
    "recommendation",
    "general_chat",
]


class AgentState(TypedDict, total=False):
    # Who is asking — MCP tools re-check authorization against this (Phase 4).
    student_id: str
    # Caller's JWT — passed through to MCP tools for independent authz checks.
    token: str
    # Conversation history (LangGraph message reducer appends across turns).
    messages: Annotated[list, add_messages]
    # Set by the intent node.
    intent: IntentKind
    entities: dict
    # Set by the tool-selection node.
    planned_tools: list
    # Filled by the tool-execution node.
    tool_results: list
    # Final reply for this turn.
    final_reply: str
