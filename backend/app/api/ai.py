# AI chat endpoint: authenticate, then hand off to the LangGraph agent (MCP + Groq + Weaviate).

from fastapi import APIRouter, Depends

from app.agent.runner import run_turn
from app.api.deps import get_bearer_token, get_current_user
from app.db.models import User
from app.schemas.api_schemas import ChatRequest, ChatResponseOut

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponseOut)
def chat(
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    token: str = Depends(get_bearer_token),
) -> ChatResponseOut:
    thread_id = payload.thread_id or f"user-{user.id}"
    result = run_turn(
        payload.message,
        student_id=str(user.id),
        thread_id=thread_id,
        token=token,
    )
    return ChatResponseOut(
        reply=result.get("reply", ""),
        intent=result.get("intent"),
        thread_id=thread_id,
        tools=[t["name"] for t in result.get("planned_tools", [])],
    )