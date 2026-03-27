from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ChatRole


class ChatMessageSend(BaseModel):
    message: str


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: ChatRole
    content: str
    retrieved_invoice_ids: Optional[list[UUID]] = None
    retrieved_tx_ids: Optional[list[UUID]] = None
    created_at: datetime


class ChatHistory(BaseModel):
    items: list[ChatMessageRead]
    total: int


class ChatClearResponse(BaseModel):
    deleted: int


class ChatSuggestions(BaseModel):
    questions: list[str]
