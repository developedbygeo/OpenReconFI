import uuid
from datetime import date

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, Enum, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import TransactionStatus


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    tx_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    counterparty: Mapped[str] = mapped_column(Text, nullable=False)
    counterparty_iban: Mapped[str | None] = mapped_column(Text, nullable=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, name="transaction_status", native_enum=True),
        nullable=False,
        default=TransactionStatus.unmatched,
    )
    embedding: Mapped[list | None] = mapped_column(Vector(1024), nullable=True)
