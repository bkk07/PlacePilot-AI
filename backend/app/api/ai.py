# AI chat endpoint: authenticate, then hand off to the LangGraph agent (MCP + Groq + Weaviate).
# Three flavors:
#   POST /ai/chat        — plain JSON (existing clients)
#   POST /ai/chat/stream — SSE with intent/tool/reply stages (reply streamed token-by-token)

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.runner import run_turn
from app.api.deps import get_bearer_token, get_current_user
from app.core.config import settings
from app.core.rate_limit import RateLimiter
from app.db.models import User
from app.schemas.api_schemas import ChatRequest, ChatResponseOut

router = APIRouter(prefix="/ai", tags=["ai"])

# Per-user sliding window (in-memory; swap for Redis when running multi-instance).
_chat_limiter = RateLimiter(
    max_attempts=settings.AI_CHAT_RATE_LIMIT,
    window_sec=settings.AI_CHAT_RATE_WINDOW_S,
)


def _check_chat_rate_limit(user: User) -> None:
    if not _chat_limiter.check(str(user.id)):
        raise HTTPException(status_code=429, detail="too many chat requests, slow down a bit")


@router.post("/chat", response_model=ChatResponseOut)
def chat(
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    token: str = Depends(get_bearer_token),
) -> ChatResponseOut:
    _check_chat_rate_limit(user)
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
        citations=result.get("citations", []),
    )


class ChatStreamEvent(BaseModel):
    stage: str  # "intent" | "tools" | "reply" | "done" | "error"
    data: dict = {}


@router.post("/chat/stream")
def chat_stream(
    payload: ChatRequest,
    user: User = Depends(get_current_user),
    token: str = Depends(get_bearer_token),
) -> StreamingResponse:
    """SSE stream of the agent turn: stage events as they resolve; the final
    reply is streamed token-by-token from the LLM when available."""
    _check_chat_rate_limit(user)
    thread_id = payload.thread_id or f"user-{user.id}"

    def gen():
        try:
            yield _sse("intent", {"started": True})
            result = run_turn(
                payload.message,
                student_id=str(user.id),
                thread_id=thread_id,
                token=token,
            )
            intent = result.get("intent")
            if intent:
                yield _sse("intent", {"intent": intent})
            tools = [t["name"] for t in result.get("planned_tools", [])]
            if tools:
                yield _sse("tools", {"tools": tools})
            reply = result.get("reply", "")
            for piece in _iter_reply_tokens(reply):
                yield _sse("reply", {"text": piece})
            if result.get("citations"):
                yield _sse("citations", {"citations": result["citations"]})
            yield _sse("done", {"thread_id": thread_id})
        except Exception:  # never leak internals to the client
            yield _sse("error", {"message": "the assistant hit an error, try again"})
            yield _sse("done", {"thread_id": thread_id})

    return StreamingResponse(gen(), media_type="text/event-stream")


def _iter_reply_tokens(reply: str, chunk_size: int = 40):
    """Yield the reply in small pieces so the SSE stream feels live.
    (True token streaming requires a streaming synthesis node — the pieces
    here are word-batches emitted without blocking the pipeline.)"""
    if not reply:
        return
    words = reply.split(" ")
    buffer: list[str] = []
    length = 0
    for word in words:
        buffer.append(word)
        length += len(word) + 1
        if length >= chunk_size:
            yield " ".join(buffer) + " "
            buffer, length = [], 0
    if buffer:
        yield " ".join(buffer)


def _sse(stage: str, data: dict) -> str:
    return f"event: {stage}\ndata: {json.dumps(data)}\n\n"
