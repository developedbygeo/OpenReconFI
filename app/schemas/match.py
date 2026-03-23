from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ConfirmedBy


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_id: UUID
    transaction_id: UUID
    confidence: Decimal
    rationale: str
    confirmed_by: ConfirmedBy
    confirmed_at: Optional[datetime] = None


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
