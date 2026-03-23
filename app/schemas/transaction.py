from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import TransactionStatus


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tx_date: date
    amount: Decimal
    description: str
    counterparty: str
    counterparty_iban: Optional[str] = None
    period: str
    status: TransactionStatus


class TransactionList(BaseModel):
    items: list[TransactionRead]
    total: int
