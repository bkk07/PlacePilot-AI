# The LangGraph agent: intent -> tool selection -> tool execution -> LLM synthesis.

import json
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agent.state import AgentState
from app.ai.llm_service import MODEL_REASONING, generate_structured
from app.schemas.agent_schemas import IntentClassification, ToolSelection

INTENT_DESCRIPTIONS = """- eligibility_check: the user asks whether they/someone can apply to a drive, or why they are not eligible
- policy_question: questions about placement policy, stipends, CGPA rules, backlogs, selection process, offers
- cross_company_query: comparing companies/drives (CTC, stipend, location, deadlines)
- recommendation: the user wants suggested drives or "what should I apply to"
- general_chat: greetings or anything else"""


def _catalog_for_intent(intent: str, student_id: str, entities: dict) -> str:
    """Live tool catalog fetched from the MCP servers — user input never executes here."""
    import asyncio

    from app.agent.mcp_client import list_tools

    try:
        tools = asyncio.run(list_tools(""))
    except Exception:
        tools = []
    lines = [f"- {t['name']}: {t['description']} args={list(t['args'].keys())}" for t in tools]
    if not lines:
        lines = ["(no tools available)"]
    return "\n".join(lines)


def _last_user_text(state: AgentState) -> str:
    """Latest user message as plain text, regardless of LangGraph message wrapper."""
    msg = state["messages"][-1]
    return msg["content"] if isinstance(msg, dict) else msg.content


def _drives_catalog(token: str) -> str:
    """Live list of open drives (id + title + company) so the planner can emit
    exact drive_ids instead of inventing ids or leaving placeholders."""
    import asyncio

    from app.agent.mcp_client import call_tool

    try:
        result = asyncio.run(call_tool("search_drives", token, {}))
    except Exception:
        return "(unavailable)"
    drives = result.get("drives") if isinstance(result, dict) else None
    if not drives:
        return "(none)"
    return "\n".join(f"  {d['id']}: {d['title']} ({d['company']})" for d in drives)


def intent_node(state: AgentState) -> dict:
    messages = state["messages"]
    from app.ai.prompts import _schema_instruction

    system = (
        "Classify the user's placement-assistant question and extract entities. "
        + INTENT_DESCRIPTIONS
        + " "
        + _schema_instruction("IntentClassification", IntentClassification)
    )
    result = generate_structured(
        [{"role": "system", "content": system}, {"role": "user", "content": _last_user_text(state)}],
        schema=IntentClassification,
        config=MODEL_REASONING,
    )
    return {"intent": result.intent, "entities": result.entities}


def selection_node(state: AgentState) -> dict:
    intent = state.get("intent", "general_chat")
    student_id = state.get("student_id", "")
    entities = state.get("entities", {})
    from app.ai.prompts import _schema_instruction

    if intent == "general_chat":
        return {"planned_tools": []}

    token = state.get("token", "")
    system = (
        "You pick tools for a placement assistant. Choose the minimal set of tool calls "
        "needed to answer the question. For the student's own data, always use the "
        f"student_id '{student_id}' — never invent ids. "
        "When a specific drive is referenced, pass its exact drive_id from the list below "
        "(never invent or omit a drive_id). "
        "If no tool is needed, return an empty calls list. "
        "Available tools:\n" + _catalog_for_intent(intent, student_id, entities)
        + "\n\nOpen drives (id: title (company)):\n" + _drives_catalog(token)
    )
    user = (
        f"Intent: {intent}\nExtracted entities: {json.dumps(entities)}\n"
        f"Question: {_last_user_text(state)}"
    )
    result = generate_structured(
        [
            {
                "role": "system",
                "content": system + " " + _schema_instruction("ToolSelection", ToolSelection),
            },
            {"role": "user", "content": user},
        ],
        schema=ToolSelection,
        config=MODEL_REASONING,
    )
    return {"planned_tools": [c.model_dump() for c in result.calls]}


def _clean_drive_args(args: dict, entities: dict) -> dict:
    """Drop placeholder/empty drive identifiers and backfill a drive name hint
    from the intent entities so check_eligibility can resolve it server-side."""
    cleaned = dict(args)
    for key in ("drive_id", "drive"):
        val = cleaned.get(key)
        if isinstance(val, str) and ("{{" in val or not val.strip()):
            cleaned.pop(key, None)
    if not cleaned.get("drive_id") and not cleaned.get("drive"):
        for value in entities.values():
            if isinstance(value, str) and value.strip():
                cleaned["drive"] = value.strip()
                break
    return cleaned


def execution_node(state: AgentState) -> dict:
    import asyncio

    from app.agent.mcp_client import call_tool

    token = state.get("token", "")
    entities = state.get("entities", {}) or {}
    results = []
    for call in state.get("planned_tools", []):
        # MCP tools re-validate caller identity/role and sanitize inputs themselves;
        # failures return a partial answer, never crash the agent run.
        args = _clean_drive_args(call.get("args", {}), entities)
        try:
            result = asyncio.run(call_tool(call["name"], token, args))
        except Exception as exc:
            result = {"error": f"tool {call['name']} unavailable: {exc}"}
        results.append({"tool": call["name"], "args": args, "result": result})
    return {"tool_results": results}


def synthesis_node(state: AgentState) -> dict:
    intent = state.get("intent", "general_chat")
    question = _last_user_text(state)
    tool_results = state.get("tool_results", [])

    if intent == "policy_question" and tool_results:
        from app.ai.grounded_answer import answer_question

        answer = answer_question(question)
        return {"final_reply": answer["answer"], "messages": [{"role": "assistant", "content": answer["answer"]}]}

    if not tool_results:
        from app.ai.llm_use_cases import general_chat

        reply = general_chat(question, history=state["messages"][:-1])
        return {"final_reply": reply.reply, "messages": [{"role": "assistant", "content": reply.reply}]}

    system = (
        "You are a placement assistant. Answer the student's question using ONLY the tool "
        "results below. For eligibility, restate the engine's decision and its reasons "
        "exactly — never override or contradict them. Cite drive/company facts as they "
        "appear in the data. Be concise and friendly. Plain text, no JSON."
    )
    user = (
        f"Question: {question}\n\nTool results:\n{json.dumps(tool_results, default=str)}"
    )
    from app.ai.llm_service import call_llm

    raw = call_llm(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        config=MODEL_REASONING,
    )
    return {"final_reply": raw, "messages": [{"role": "assistant", "content": raw}]}


def route_after_intent(state: AgentState) -> Literal["selection", "synthesis"]:
    return "selection"  # selection decides tool calls (possibly zero), then synthesis


def build_agent_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("intent", intent_node)
    graph.add_node("selection", selection_node)
    graph.add_node("execution", execution_node)
    graph.add_node("synthesis", synthesis_node)
    graph.add_edge(START, "intent")
    graph.add_edge("intent", "selection")
    graph.add_edge("selection", "execution")
    graph.add_edge("execution", "synthesis")
    graph.add_edge("synthesis", END)
    compiled = graph.compile(checkpointer=checkpointer) if checkpointer else graph.compile()
    return compiled
