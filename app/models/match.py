import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import ConfirmedBy


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id"),
        nullable=False,
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id"),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed_by: Mapped[ConfirmedBy] = mapped_column(
        Enum(ConfirmedBy, name="confirmed_by", native_enum=True),
        nullable=False,
        default=ConfirmedBy.llm,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
