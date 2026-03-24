from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ConfirmedBy


class MatchInvoiceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vendor: str
    invoice_number: str
    invoice_date: date
    amount_excl: Decimal
    amount_incl: Decimal
    category: Optional[str] = None
    drive_url: Optional[str] = None
    period: str


class MatchTransactionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tx_date: date
    value_date: Optional[date] = None
    amount: Decimal
    original_amount: Optional[Decimal] = None
    original_currency: Optional[str] = None
    description: str
    counterparty: str


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_id: UUID
    transaction_id: UUID
    confidence: Decimal
    rationale: str
    confirmed_by: ConfirmedBy
    confirmed_at: Optional[datetime] = None
    invoice: Optional[MatchInvoiceSummary] = None
    transaction: Optional[MatchTransactionSummary] = None


class MatchList(BaseModel):
    items: list[MatchRead]
    total: int


class MatchConfirm(BaseModel):
    """Confirm a match — sets confirmed_by to 'user' and confirmed_at to now."""
    pass


class MatchReassign(BaseModel):
    """Reassign a match to a different invoice or transaction."""
    invoice_id: Optional[UUID] = None
    transaction_id: Optional[UUID] = None
