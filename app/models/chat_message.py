"""ChatMessage model — stores conversation history for expense chat."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import ChatRole


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    role: Mapped[ChatRole] = mapped_column(
        Enum(ChatRole, name="chat_role", native_enum=True),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_invoice_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=True,
    )
    retrieved_tx_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
