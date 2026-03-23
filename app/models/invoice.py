import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, DateTime, Enum, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import InvoiceSource, InvoiceStatus


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    vendor: Mapped[str] = mapped_column(Text, nullable=False)
    amount_excl: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    amount_incl: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    vat_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    vat_rate: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    invoice_number: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    drive_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    drive_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[InvoiceSource] = mapped_column(
        Enum(InvoiceSource, name="invoice_source", native_enum=True),
        nullable=False,
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status", native_enum=True),
        nullable=False,
        default=InvoiceStatus.pending,
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    raw_extraction: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    embedding: Mapped[list | None] = mapped_column(Vector(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
