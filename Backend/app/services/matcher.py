import logging
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ConfirmedBy, InvoiceStatus, TransactionStatus
from app.models.invoice import Invoice
from app.models.match import Match
from app.models.transaction import Transaction
from app.models.vendor import Vendor

logger = logging.getLogger(__name__)

FEE_KEYWORDS = {"conversion", "fee", "kosten", "wisselkoers", "commission", "currency"}
FEE_MAX_AMOUNT = Decimal("5.00")
FEE_DATE_TOLERANCE_DAYS = 3

@dataclass
class InvoiceCandidate:
    id: UUID
    vendor: str
    amount_incl: Decimal
    currency: Optional[str] = None
    iban: Optional[str] = None


@dataclass
class TransactionCandidate:
    id: UUID
    amount: Decimal
    original_amount: Optional[Decimal] = None
    original_currency: Optional[str] = None
    counterparty: str = ""
    counterparty_iban: Optional[str] = None
    description: str = ""
    tx_date: Optional[date] = None


@dataclass
class MatchCandidate:
    invoice_id: UUID
    transaction_id: UUID
    confidence: Decimal
    rationale: str


@dataclass
class ConversionFeeDismissal:
    transaction_id: UUID
    near_match_invoice_id: UUID
    note: str


@dataclass
class MatchingResult:
    deterministic_matches: list[MatchCandidate] = field(default_factory=list)
    llm_matches: list[dict[str, Any]] = field(default_factory=list)
    fees_dismissed: list[ConversionFeeDismissal] = field(default_factory=list)


def _amounts_match(inv: InvoiceCandidate, tx: TransactionCandidate) -> bool:
    """Check if invoice and transaction amounts match (EUR or foreign currency)."""
    tx_abs = abs(tx.amount)

    # Direct EUR match
    if inv.amount_incl == tx_abs:
        return True

    # Foreign currency: invoice amount matches original_amount in same currency
    if (
        tx.original_amount is not None
        and tx.original_currency is not None
        and inv.currency is not None
        and inv.currency == tx.original_currency
        and inv.amount_incl == abs(tx.original_amount)
    ):
        return True

    return False


def _iban_match(inv: InvoiceCandidate, tx: TransactionCandidate) -> bool:
    """Check if both have non-null IBANs that match exactly."""
    return (
        inv.iban is not None
        and tx.counterparty_iban is not None
        and inv.iban.replace(" ", "").upper() == tx.counterparty_iban.replace(" ", "").upper()
    )


def _alias_match(
    inv: InvoiceCandidate,
    tx: TransactionCandidate,
    alias_lookup: dict[str, str],
) -> bool:
    """Check if transaction counterparty or description matches a vendor alias."""
    vendor_lower = inv.vendor.lower()
    counterparty_lower = tx.counterparty.lower()
    description_lower = tx.description.lower()

    # Direct vendor name substring match
    if vendor_lower in counterparty_lower or vendor_lower in description_lower:
        return True

    # Check vendor aliases
    for alias, vname in alias_lookup.items():
        if vname.lower() != vendor_lower:
            continue
        if alias in counterparty_lower or alias in description_lower:
            return True

    return False


def deterministic_match(
    invoices: list[InvoiceCandidate],
    transactions: list[TransactionCandidate],
    vendor_aliases: dict[str, list[str]],
) -> list[MatchCandidate]:
    """
    Pure deterministic matching: amount + IBAN/alias.

    Confidence tiers:
    - 1.00: Amount + IBAN match
    - 0.95: Amount + vendor alias match

    Amount-only matches (no IBAN or alias) are left for the LLM pass,
    which can reason about vendor name similarity, date proximity, etc.

    Returns matches after 1:1 conflict resolution (greedy by confidence desc).
    """
    # Build alias lookup: lowered alias → vendor name
    alias_lookup: dict[str, str] = {}
    for vendor_name, aliases in vendor_aliases.items():
        for alias in aliases:
            alias_lookup[alias.lower()] = vendor_name

    # Find all candidate pairs (only with strong signal: IBAN or alias)
    candidates: list[MatchCandidate] = []

    for inv in invoices:
        strong_matches: list[tuple[TransactionCandidate, Decimal, str]] = []

        for tx in transactions:
            if not _amounts_match(inv, tx):
                continue

            if _iban_match(inv, tx):
                strong_matches.append((tx, Decimal("1.00"), "Amount + IBAN match"))
            elif _alias_match(inv, tx, alias_lookup):
                strong_matches.append((tx, Decimal("0.95"), "Amount + vendor alias match"))
            # No IBAN or alias → leave for LLM

        if len(strong_matches) == 1:
            tx, conf, rationale = strong_matches[0]
            candidates.append(MatchCandidate(
                invoice_id=inv.id,
                transaction_id=tx.id,
                confidence=conf,
                rationale=rationale,
            ))

    # 1:1 conflict resolution: sort by confidence desc, greedy assignment
    candidates.sort(key=lambda c: c.confidence, reverse=True)
    used_invoices: set[UUID] = set()
    used_transactions: set[UUID] = set()
    resolved: list[MatchCandidate] = []

    for c in candidates:
        if c.invoice_id in used_invoices or c.transaction_id in used_transactions:
            continue
        used_invoices.add(c.invoice_id)
        used_transactions.add(c.transaction_id)
        resolved.append(c)

    return resolved


def detect_conversion_fees(
    matched_foreign: list[MatchCandidate],
    invoices: list[InvoiceCandidate],
    transactions: list[TransactionCandidate],
    remaining_tx_ids: set[UUID],
) -> list[ConversionFeeDismissal]:
    """
    For each foreign-currency match, find nearby small fee transactions to auto-dismiss.
    """
    # Build lookup for matched invoices that involved foreign currency
    foreign_match_info: list[tuple[UUID, date, UUID]] = []
    inv_map = {i.id: i for i in invoices}
    tx_map = {t.id: t for t in transactions}

    for mc in matched_foreign:
        inv = inv_map.get(mc.invoice_id)
        tx = tx_map.get(mc.transaction_id)
        if inv and tx and inv.currency and inv.currency != "EUR" and tx.tx_date:
            foreign_match_info.append((mc.invoice_id, tx.tx_date, tx.id))

    if not foreign_match_info:
        return []

    dismissals: list[ConversionFeeDismissal] = []
    dismissed_ids: set[UUID] = set()

    for inv_id, match_date, _match_tx_id in foreign_match_info:
        for tx in transactions:
            if tx.id not in remaining_tx_ids or tx.id in dismissed_ids:
                continue
            if tx.tx_date is None:
                continue

            # Check proximity
            delta = abs((tx.tx_date - match_date).days)
            if delta > FEE_DATE_TOLERANCE_DAYS:
                continue

            # Check small amount
            if abs(tx.amount) > FEE_MAX_AMOUNT:
                continue

            # Check fee keywords (whole word match to avoid false positives like "coffee")
            desc_lower = tx.description.lower() + " " + tx.counterparty.lower()
            if any(re.search(rf"\b{kw}\b", desc_lower) for kw in FEE_KEYWORDS):
                dismissals.append(ConversionFeeDismissal(
                    transaction_id=tx.id,
                    near_match_invoice_id=inv_id,
                    note=f"Currency conversion fee (auto-dismissed, near foreign-currency match)",
                ))
                dismissed_ids.add(tx.id)

    return dismissals


def _invoice_to_candidate(inv: Invoice) -> InvoiceCandidate:
    raw = inv.raw_extraction or {}
    return InvoiceCandidate(
        id=inv.id,
        vendor=inv.vendor,
        amount_incl=Decimal(str(inv.amount_incl)),
        currency=inv.currency,
        iban=raw.get("iban"),
    )


def _transaction_to_candidate(tx: Transaction) -> TransactionCandidate:
    return TransactionCandidate(
        id=tx.id,
        amount=Decimal(str(tx.amount)),
        original_amount=Decimal(str(tx.original_amount)) if tx.original_amount else None,
        original_currency=tx.original_currency,
        counterparty=tx.counterparty or "",
        counterparty_iban=tx.counterparty_iban,
        description=tx.description or "",
        tx_date=tx.tx_date,
    )


async def run_matching(
    db: AsyncSession,
    period: Optional[str] = None,
) -> MatchingResult:
    """
    Two-pass hybrid matching orchestrator.

    1. Fetch all unmatched invoices + transactions (optionally filtered by period)
    2. Run deterministic pass → persist matches
    3. Detect + dismiss conversion fees
    4. Run LLM pass on leftovers → post-validate → persist
    5. Return breakdown
    """
    from app.services.llm import match_single_invoice

    result = MatchingResult()

    # --- Fetch unmatched invoices ---
    inv_query = select(Invoice).where(
        Invoice.status.in_([InvoiceStatus.pending, InvoiceStatus.unmatched, InvoiceStatus.deferred])
    )
    if period:
        inv_query = inv_query.where(Invoice.period == period)
    inv_result = await db.execute(inv_query)
    invoices = inv_result.scalars().all()

    # --- Fetch unmatched transactions ---
    tx_query = select(Transaction).where(
        Transaction.status == TransactionStatus.unmatched
    )
    if period:
        tx_query = tx_query.where(Transaction.period == period)
    tx_result = await db.execute(tx_query)
    transactions = tx_result.scalars().all()

    if not invoices or not transactions:
        return result

    # --- Fetch vendor aliases ---
    vendor_result = await db.execute(select(Vendor))
    vendors = vendor_result.scalars().all()
    vendor_aliases: dict[str, list[str]] = {
        v.name: v.aliases or [] for v in vendors
    }

    # --- Convert to candidates ---
    inv_candidates = [_invoice_to_candidate(inv) for inv in invoices]
    tx_candidates = [_transaction_to_candidate(tx) for tx in transactions]

    # --- Pass 1: Deterministic matching ---
    logger.info("Matching: %d invoices, %d transactions", len(invoices), len(transactions))
    det_matches = deterministic_match(inv_candidates, tx_candidates, vendor_aliases)

    # Persist deterministic matches
    matched_inv_ids: set[UUID] = set()
    matched_tx_ids: set[UUID] = set()

    for mc in det_matches:
        match_obj = Match(
            invoice_id=mc.invoice_id,
            transaction_id=mc.transaction_id,
            confidence=mc.confidence,
            rationale=mc.rationale,
            confirmed_by=ConfirmedBy.deterministic,
        )
        db.add(match_obj)

        # Update statuses
        inv_obj = await db.get(Invoice, mc.invoice_id)
        if inv_obj:
            inv_obj.status = InvoiceStatus.matched
        tx_obj = await db.get(Transaction, mc.transaction_id)
        if tx_obj:
            tx_obj.status = TransactionStatus.matched
            if inv_obj and inv_obj.category and not tx_obj.category:
                tx_obj.category = inv_obj.category

        matched_inv_ids.add(mc.invoice_id)
        matched_tx_ids.add(mc.transaction_id)

    logger.info("Deterministic pass: %d matches", len(det_matches))
    result.deterministic_matches = det_matches

    # --- Conversion fee detection ---
    remaining_tx_ids = {tx.id for tx in transactions} - matched_tx_ids
    fee_dismissals = detect_conversion_fees(
        det_matches, inv_candidates, tx_candidates, remaining_tx_ids,
    )
    for fd in fee_dismissals:
        tx_obj = await db.get(Transaction, fd.transaction_id)
        if tx_obj:
            tx_obj.status = TransactionStatus.no_invoice
            tx_obj.note = fd.note
        remaining_tx_ids.discard(fd.transaction_id)

    result.fees_dismissed = fee_dismissals

    # --- Pass 2: LLM matching on leftovers ---
    leftover_invs = [inv for inv in invoices if inv.id not in matched_inv_ids]
    leftover_txs = [tx for tx in transactions if tx.id in remaining_tx_ids]

    logger.info("LLM pass: %d invoices, %d transactions remaining", len(leftover_invs), len(leftover_txs))
    if leftover_invs and leftover_txs:
        used_tx_ids: set[UUID] = set()

        for inv in leftover_invs:
            available_txs = [tx for tx in leftover_txs if tx.id not in used_tx_ids]
            if not available_txs:
                break

            inv_data = {
                "id": str(inv.id),
                "vendor": inv.vendor,
                "amount_incl": str(inv.amount_incl),
                "currency": inv.currency,
                "invoice_date": str(inv.invoice_date),
            }
            tx_data = [
                {
                    "id": str(tx.id),
                    "tx_date": str(tx.tx_date),
                    "amount": str(tx.amount),
                    "counterparty": tx.counterparty,
                    "description": tx.description,
                }
                for tx in available_txs
            ]

            try:
                s = await match_single_invoice(inv_data, tx_data)
            except Exception:
                logger.exception("LLM matching failed for %s", inv.vendor)
                continue

            if not s:
                logger.info("LLM: no match for %s", inv.vendor)
                continue

            tx_id = s["transaction_id"]
            logger.info("LLM match: %s → %s (conf=%s) — %s",
                        inv.vendor, tx_id, s["confidence"], s["rationale"])

            # Post-validate: amount sanity (reject >30% difference)
            tx_obj_check = next((tx for tx in available_txs if tx.id == tx_id), None)
            if tx_obj_check:
                inv_amt = Decimal(str(inv.amount_incl))
                tx_amt = abs(Decimal(str(tx_obj_check.amount)))
                if inv_amt > 0 and tx_amt > 0:
                    ratio = min(inv_amt, tx_amt) / max(inv_amt, tx_amt)
                    if ratio < Decimal("0.70"):
                        logger.info("Rejected: %s→%s (amount ratio %.2f)",
                                    inv.vendor, tx_obj_check.counterparty, ratio)
                        continue

            match_obj = Match(
                invoice_id=inv.id,
                transaction_id=tx_id,
                confidence=s["confidence"],
                rationale=s["rationale"],
                confirmed_by=ConfirmedBy.llm,
            )
            db.add(match_obj)

            inv.status = InvoiceStatus.matched
            tx_obj = await db.get(Transaction, tx_id)
            if tx_obj:
                tx_obj.status = TransactionStatus.matched
                if inv.category and not tx_obj.category:
                    tx_obj.category = inv.category

            used_tx_ids.add(tx_id)
            result.llm_matches.append(s)

    # --- Auto-categorize transactions that will never match an invoice ---
    # Withholdings → "Owner Draw"
    withholding_txs = await db.execute(
        select(Transaction).where(
            Transaction.status == TransactionStatus.withholding,
            Transaction.category.is_(None),
        )
    )
    for tx in withholding_txs.scalars().all():
        tx.category = "Owner Draw"

    # Unmatched inflows → "Revenue"
    revenue_txs = await db.execute(
        select(Transaction).where(
            Transaction.status == TransactionStatus.unmatched,
            Transaction.amount > 0,
            Transaction.category.is_(None),
        )
    )
    for tx in revenue_txs.scalars().all():
        tx.category = "Revenue"

    await db.commit()
    return result
