from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.chat import (
    ChatClearResponse,
    ChatHistory,
    ChatMessageRead,
    ChatMessageSend,
)
from app.services.chat import chat_stream, clear_chat_history, get_chat_history

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/message",
)
async def send_message(
    body: ChatMessageSend,
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    """Send a message and receive a streaming response.

    Uses Server-Sent Events (SSE) to stream the assistant's response.
    """

    async def event_generator():
        async for chunk in chat_stream(db, body.message):
            yield {"data": chunk}

    return EventSourceResponse(event_generator())


@router.get(
    "/history",
    response_model=ChatHistory,
)
async def get_history(
    db: AsyncSession = Depends(get_db),
) -> ChatHistory:
    messages = await get_chat_history(db)
    return ChatHistory(
        items=[ChatMessageRead.model_validate(m) for m in messages],
        total=len(messages),
    )


@router.delete(
    "/history",
    response_model=ChatClearResponse,
)
async def clear_history(
    db: AsyncSession = Depends(get_db),
) -> ChatClearResponse:
    deleted = await clear_chat_history(db)
    return ChatClearResponse(deleted=deleted)
