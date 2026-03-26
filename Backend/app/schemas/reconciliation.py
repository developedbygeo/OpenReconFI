from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StatementUploadResponse(BaseModel):
    transactions_parsed: int
    period: str


class MatchTriggerRequest(BaseModel):
    period: Optional[str] = None


class MatchTriggerResponse(BaseModel):
    matches_suggested: int
    period: Optional[str] = None
    deterministic_matches: int = 0
    llm_matches: int = 0
    fees_dismissed: int = 0

class UnmatchedInvoiceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vendor: str
    invoice_number: str
    amount_incl: Decimal
    invoice_date: str
    category: Optional[str] = None


class UnmatchedTransactionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    counterparty: str
    description: str
    amount: Decimal
    tx_date: str
    category: Optional[str] = None


class PeriodReconciliation(BaseModel):
    period: str
    is_complete: bool

    # Invoices
    total_invoices: int
    matched_invoices: int
    unmatched_invoices: int
    total_invoiced_incl: Decimal

    # Bank transactions (expenses only, excludes earnings/withholdings)
    total_transactions: int
    matched_transactions: int
    unmatched_transactions: int
    total_bank_debits: Decimal

    # No-invoice expenses (taxes, fees etc.)
    no_invoice_count: int
    no_invoice_total: Decimal

    # Withholdings
    withholding_count: int
    withholding_total: Decimal

    # Earnings
    earnings_count: int
    earnings_total: Decimal

    # Gap
    gap: Decimal  # bank debits - invoiced amount (0 = fully reconciled)

    # Detail
    unmatched_invoice_list: list[UnmatchedInvoiceSummary]
    unmatched_transaction_list: list[UnmatchedTransactionSummary]
