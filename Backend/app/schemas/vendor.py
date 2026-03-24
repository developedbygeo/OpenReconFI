from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import BillingCycle


class VendorCreate(BaseModel):
    name: str
    aliases: Optional[list[str]] = None
    default_category: Optional[str] = None
    default_vat_rate: Optional[Decimal] = None
    billing_cycle: BillingCycle = BillingCycle.monthly


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    aliases: Optional[list[str]] = None
    default_category: Optional[str] = None
    default_vat_rate: Optional[Decimal] = None
    billing_cycle: Optional[BillingCycle] = None


class VendorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    aliases: Optional[list[str]] = None
    default_category: Optional[str] = None
    default_vat_rate: Optional[Decimal] = None
    billing_cycle: BillingCycle


class VendorList(BaseModel):
    items: list[VendorRead]
    total: int
