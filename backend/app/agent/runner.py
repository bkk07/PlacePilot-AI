# Agent runner: conversation-state persistence across turns (in-memory checkpointer).
# Swap the checkpointer for a Redis-backed one later without touching the graph.

from langgraph.checkpoint.memory import MemorySaver

from app.agent.graph import build_agent_graph

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_agent_graph(checkpointer=MemorySaver())
    return _graph


def run_turn(user_message: str, student_id: str, thread_id: str, token: str = "") -> dict:
    """One conversational turn. History persists per thread_id across turns.
    The token is passed through to MCP tools for independent authz checks."""
    graph = get_graph()
    events = graph.invoke(
        {
            "messages": [{"role": "user", "content": user_message}],
            "student_id": student_id,
            "token": token,
        },
        config={"configurable": {"thread_id": thread_id}},
    )
    return {
        "intent": events.get("intent"),
        "planned_tools": events.get("planned_tools", []),
        "tool_results": events.get("tool_results", []),
        "reply": events.get("final_reply", ""),
    }
