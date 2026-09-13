# Agent runner: conversation-state persistence across turns.
# Prefers the Redis-backed checkpointer (survives restarts, Phase 3.5 of the
# build plan); falls back to in-memory when Redis is unreachable so local dev
# and CI keep working.

from langgraph.checkpoint.memory import MemorySaver

from app.agent.graph import build_agent_graph
from app.core.config import settings

_graph = None


def _redis_checkpointer():
    """Return a Redis checkpointer, or None when Redis is not reachable."""
    try:
        from langgraph.checkpoint.redis import AsyncRedisSaver
    except ImportError:
        return None
    try:
        import redis as _redis

        url = settings.REDIS_URL
        host = url.split("//")[-1].split(":")[0] or "localhost"
        port = int(url.split(":")[-1].split("/")[0] or 6379)
        r = _redis.Redis(host=host, port=port, socket_connect_timeout=1)
        r.ping()
        # AsyncRedisSaver sets up its own connection from the URL
        return AsyncRedisSaver.from_conn_string(url)
    except Exception:
        return None


def get_graph():
    global _graph
    if _graph is None:
        checkpointer = _redis_checkpointer() or MemorySaver()
        _graph = build_agent_graph(checkpointer=checkpointer)
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
        "citations": events.get("citations", []),
    }
