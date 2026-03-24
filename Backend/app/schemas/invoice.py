from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import InvoiceSource, InvoiceStatus


class InvoiceCreate(BaseModel):
    vendor: str
    amount_excl: Decimal
    amount_incl: Decimal
    vat_amount: Decimal
    vat_rate: Decimal
    invoice_date: date
    invoice_number: str
    category: Optional[str] = None
    source: InvoiceSource = InvoiceSource.manual
    period: str
    raw_extraction: Optional[dict[str, Any]] = None


class InvoiceUpdate(BaseModel):
    vendor: Optional[str] = None
    category: Optional[str] = None
    status: Optional[InvoiceStatus] = None


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vendor: str
    amount_excl: Decimal
    amount_incl: Decimal
    vat_amount: Decimal
    vat_rate: Decimal
    invoice_date: date
    invoice_number: str
    category: Optional[str] = None
    drive_url: Optional[str] = None
    drive_file_id: Optional[str] = None
    source: InvoiceSource
    status: InvoiceStatus
    period: str
    raw_extraction: Optional[dict[str, Any]] = None
    created_at: datetime


class InvoiceList(BaseModel):
    items: list[InvoiceRead]
    total: int
