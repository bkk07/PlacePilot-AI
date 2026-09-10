# The LangGraph agent: intent -> tool selection -> tool execution -> LLM synthesis.

import json
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agent.state import AgentState
from app.agent.tools import TOOLS, execute_tool
from app.ai.llm_service import MODEL_REASONING, generate_structured
from app.schemas.agent_schemas import IntentClassification, ToolSelection

INTENT_DESCRIPTIONS = """- eligibility_check: the user asks whether they/someone can apply to a drive, or why they are not eligible
- policy_question: questions about placement policy, stipends, CGPA rules, backlogs, selection process, offers
- cross_company_query: comparing companies/drives (CTC, stipend, location, deadlines)
- recommendation: the user wants suggested drives or "what should I apply to"
- general_chat: greetings or anything else"""


def _catalog_for_intent(intent: str, student_id: str, entities: dict) -> str:
    """Tool catalog + known entity ids the selection LLM sees — user input never executes here."""
    from app.agent.seed_data import COMPANIES, DRIVES

    lines = [f"- {name}: {spec['description']} args={spec['arg_names']}" for name, spec in TOOLS.items()]
    lines.append("")
    lines.append("Known drives:")
    for d in DRIVES.values():
        company = COMPANIES[d["company_id"]]["name"]
        lines.append(f"  {d['id']}: {d['title']} ({company})")
    lines.append("Known companies: " + ", ".join(f"{c['id']} ({c['name']})" for c in COMPANIES.values()))
    return "\n".join(lines)


def _last_user_text(state: AgentState) -> str:
    """Latest user message as plain text, regardless of LangGraph message wrapper."""
    msg = state["messages"][-1]
    return msg["content"] if isinstance(msg, dict) else msg.content


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

    system = (
        "You pick tools for a placement assistant. Choose the minimal set of tool calls "
        "needed to answer the question. For the student's own data, always use the "
        f"student_id '{student_id}' — never invent ids. "
        "Prefer get_drive_details with the exact drive_id when a specific drive is "
        "referenced; resolve names like 'Nimbus' to ids via search_drives first when unsure. "
        "If no tool is needed, return an empty calls list. "
        "Available tools:\n" + _catalog_for_intent(intent, student_id, entities)
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


def execution_node(state: AgentState) -> dict:
    results = []
    for call in state.get("planned_tools", []):
        # Tools validate + sanitize their own args; user input is never treated as instruction.
        results.append({"tool": call["name"], "args": call.get("args", {}), "result": execute_tool(call["name"], call.get("args", {}))})
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
