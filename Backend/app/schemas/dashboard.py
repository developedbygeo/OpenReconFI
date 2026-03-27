from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import BillingCycle


# --- Missing invoice alerts (Phase 3) ---


class MissingInvoiceAlert(BaseModel):
    vendor_id: UUID
    vendor_name: str
    billing_cycle: BillingCycle
    last_invoice_period: Optional[str] = None
    expected_period: str


class MissingInvoiceAlertList(BaseModel):
    items: list[MissingInvoiceAlert]
    total: int


# --- Spending summaries (Phase 4) ---


class SpendSummary(BaseModel):
    total_spend_excl: Decimal
    total_vat: Decimal
    total_spend_incl: Decimal
    invoice_count: int
    matched_count: int
    unmatched_count: int


class CategorySpend(BaseModel):
    category: str
    total_excl: Decimal
    total_vat: Decimal
    total_incl: Decimal
    invoice_count: int


class CategorySpendList(BaseModel):
    items: list[CategorySpend]


class VendorSpend(BaseModel):
    vendor: str
    total_excl: Decimal
    total_vat: Decimal
    total_incl: Decimal
    invoice_count: int


class VendorSpendList(BaseModel):
    items: list[VendorSpend]


class VATBreakdown(BaseModel):
    vat_rate: Decimal
    total_excl: Decimal
    total_vat: Decimal
    invoice_count: int


class VATSummary(BaseModel):
    items: list[VATBreakdown]


class MonthlySpend(BaseModel):
    period: str
    total_excl: Decimal
    total_vat: Decimal
    total_incl: Decimal
    invoice_count: int


class MoMComparison(BaseModel):
    items: list[MonthlySpend]


# --- Tax / no-invoice transaction summaries ---


# --- Earnings ---


class EarningTransaction(BaseModel):
    id: UUID
    tx_date: str
    amount: Decimal
    description: str
    counterparty: str
    category: Optional[str] = None


class EarningsSummary(BaseModel):
    period: str
    total_earnings: Decimal
    transaction_count: int
    items: list[EarningTransaction]


# --- Withholdings (deductions against earnings) ---


class WithholdingTransaction(BaseModel):
    id: UUID
    tx_date: str
    amount: Decimal
    description: str
    counterparty: str


class WithholdingSummary(BaseModel):
    period: str
    total_amount: Decimal
    transaction_count: int
    items: list[WithholdingTransaction]


# --- Tax / no-invoice transactions ---


class TaxTransaction(BaseModel):
    id: UUID
    tx_date: str
    amount: Decimal
    description: str
    counterparty: str
    category: Optional[str] = None


class TaxCategoryBreakdown(BaseModel):
    category: str
    total_amount: Decimal
    transaction_count: int


class TaxSummary(BaseModel):
    period: str
    total_amount: Decimal
    transaction_count: int
    by_category: list[TaxCategoryBreakdown]
    items: list[TaxTransaction]
