from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.enums import ConfirmedBy, InvoiceStatus, TransactionStatus
from app.models.invoice import Invoice
from app.models.match import Match
from app.models.transaction import Transaction
from app.models.vendor import Vendor
from app.schemas.match import MatchConfirm, MatchList, MatchRead, MatchReassign
from app.schemas.reconciliation import (
    MatchTriggerRequest,
    MatchTriggerResponse,
    StatementUploadResponse,
)
from app.schemas.transaction import TransactionList, TransactionRead

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


# ---------------------------------------------------------------------------
# Statement upload
# ---------------------------------------------------------------------------


@router.post(
    "/upload",
    response_model=StatementUploadResponse,
    status_code=201,
    tags=["reconciliation"],
)
async def upload_statement(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> StatementUploadResponse:
    """Upload a bank statement file, parse via LLM, store transactions."""
    from app.services.ingester import ingest
    from app.services.llm import parse_bank_statement

    file_bytes = await file.read()
    filename = file.filename or "statement.csv"

    # Convert file to clean text
    statement_text = ingest(file_bytes, filename)

    # LLM parses the text into structured transactions
    parsed = await parse_bank_statement(statement_text)

    if not parsed:
        raise HTTPException(status_code=422, detail="No transactions found in statement")

    # Derive period from first transaction date
    period = parsed[0]["tx_date"].strftime("%Y-%m")

    # Store transactions
    for tx_data in parsed:
        status = TransactionStatus.no_invoice if tx_data.get("no_invoice") else TransactionStatus.unmatched
        tx = Transaction(
            tx_date=tx_data["tx_date"],
            value_date=tx_data.get("value_date"),
            amount=tx_data["amount"],
            original_amount=tx_data.get("original_amount"),
            original_currency=tx_data.get("original_currency"),
            description=tx_data["description"],
            counterparty=tx_data["counterparty"],
            counterparty_iban=tx_data.get("counterparty_iban"),
            period=tx_data["tx_date"].strftime("%Y-%m"),
            status=status,
        )
        db.add(tx)

    await db.commit()

    return StatementUploadResponse(
        transactions_parsed=len(parsed),
        period=period,
    )


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


@router.get("/transactions", response_model=TransactionList, tags=["reconciliation"])
async def list_transactions(
    period: Optional[str] = Query(None),
    status: Optional[TransactionStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> TransactionList:
    query = select(Transaction)
    count_query = select(func.count(Transaction.id))

    if period:
        query = query.where(Transaction.period == period)
        count_query = count_query.where(Transaction.period == period)
    if status:
        query = query.where(Transaction.status == status)
        count_query = count_query.where(Transaction.status == status)

    query = query.order_by(Transaction.tx_date.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    transactions = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    return TransactionList(
        items=[TransactionRead.model_validate(tx) for tx in transactions],
        total=total,
    )


# ---------------------------------------------------------------------------
# Match trigger
# ---------------------------------------------------------------------------


@router.post("/match", response_model=MatchTriggerResponse, tags=["reconciliation"])
async def trigger_matching(
    body: MatchTriggerRequest,
    db: AsyncSession = Depends(get_db),
) -> MatchTriggerResponse:
    """Trigger LLM matching for a given period."""
    from app.services.llm import match_invoices_transactions

    # Fetch unmatched invoices for the period
    inv_result = await db.execute(
        select(Invoice).where(
            Invoice.period == body.period,
            Invoice.status.in_([InvoiceStatus.pending, InvoiceStatus.unmatched]),
        )
    )
    invoices = inv_result.scalars().all()

    # Fetch unmatched transactions for the period
    tx_result = await db.execute(
        select(Transaction).where(
            Transaction.period == body.period,
            Transaction.status == TransactionStatus.unmatched,
        )
    )
    transactions = tx_result.scalars().all()

    if not invoices or not transactions:
        return MatchTriggerResponse(matches_suggested=0, period=body.period)

    # Fetch vendor aliases
    vendor_result = await db.execute(select(Vendor))
    vendors = vendor_result.scalars().all()
    aliases = [
        {"name": v.name, "aliases": v.aliases or []}
        for v in vendors
    ]

    # Prepare data for LLM
    invoices_data = [
        {
            "id": str(inv.id),
            "vendor": inv.vendor,
            "amount_incl": str(inv.amount_incl),
            "amount_excl": str(inv.amount_excl),
            "invoice_date": str(inv.invoice_date),
            "invoice_number": inv.invoice_number,
        }
        for inv in invoices
    ]
    transactions_data = [
        {
            "id": str(tx.id),
            "tx_date": str(tx.tx_date),
            "value_date": str(tx.value_date) if tx.value_date else None,
            "amount": str(tx.amount),
            "original_amount": str(tx.original_amount) if tx.original_amount else None,
            "original_currency": tx.original_currency,
            "description": tx.description,
            "counterparty": tx.counterparty,
            "counterparty_iban": tx.counterparty_iban,
        }
        for tx in transactions
    ]

    # LLM matching
    suggestions = await match_invoices_transactions(
        invoices_data, transactions_data, aliases
    )

    # Store matches
    for s in suggestions:
        match = Match(
            invoice_id=s["invoice_id"],
            transaction_id=s["transaction_id"],
            confidence=s["confidence"],
            rationale=s["rationale"],
            confirmed_by=ConfirmedBy.llm,
        )
        db.add(match)

    await db.commit()

    return MatchTriggerResponse(
        matches_suggested=len(suggestions),
        period=body.period,
    )


# ---------------------------------------------------------------------------
# Match CRUD
# ---------------------------------------------------------------------------


@router.get("/matches", response_model=MatchList, tags=["reconciliation"])
async def list_matches(
    period: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> MatchList:
    query = select(Match)
    count_query = select(func.count(Match.id))

    if period:
        query = query.join(Invoice, Match.invoice_id == Invoice.id).where(
            Invoice.period == period
        )
        count_query = count_query.join(Invoice, Match.invoice_id == Invoice.id).where(
            Invoice.period == period
        )

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    matches = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    return MatchList(
        items=[MatchRead.model_validate(m) for m in matches],
        total=total,
    )


@router.get("/matches/{match_id}", response_model=MatchRead, tags=["reconciliation"])
async def get_match(
    match_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> MatchRead:
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return MatchRead.model_validate(match)


@router.post(
    "/matches/{match_id}/confirm",
    response_model=MatchRead,
    tags=["reconciliation"],
)
async def confirm_match(
    match_id: UUID,
    body: MatchConfirm,
    db: AsyncSession = Depends(get_db),
) -> MatchRead:
    """Confirm a match — updates invoice and transaction status."""
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.confirmed_by = ConfirmedBy.user
    match.confirmed_at = datetime.now(timezone.utc)

    # Update invoice status
    inv_result = await db.execute(
        select(Invoice).where(Invoice.id == match.invoice_id)
    )
    invoice = inv_result.scalar_one_or_none()
    if invoice:
        invoice.status = InvoiceStatus.matched

    # Update transaction status
    tx_result = await db.execute(
        select(Transaction).where(Transaction.id == match.transaction_id)
    )
    transaction = tx_result.scalar_one_or_none()
    if transaction:
        transaction.status = TransactionStatus.matched

        # Vendor alias learning
        await _learn_vendor_alias(db, invoice, transaction)

    await db.commit()
    await db.refresh(match)
    return MatchRead.model_validate(match)


@router.delete(
    "/matches/{match_id}",
    response_model=MatchRead,
    tags=["reconciliation"],
)
async def reject_match(
    match_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> MatchRead:
    """Reject (delete) a match — resets invoice and transaction to unmatched."""
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Reset invoice status if it was matched by this match
    inv_result = await db.execute(
        select(Invoice).where(Invoice.id == match.invoice_id)
    )
    invoice = inv_result.scalar_one_or_none()
    if invoice and invoice.status == InvoiceStatus.matched:
        invoice.status = InvoiceStatus.unmatched

    # Reset transaction status
    tx_result = await db.execute(
        select(Transaction).where(Transaction.id == match.transaction_id)
    )
    transaction = tx_result.scalar_one_or_none()
    if transaction and transaction.status == TransactionStatus.matched:
        transaction.status = TransactionStatus.unmatched

    response = MatchRead.model_validate(match)
    await db.delete(match)
    await db.commit()
    return response


@router.patch(
    "/matches/{match_id}/reassign",
    response_model=MatchRead,
    tags=["reconciliation"],
)
async def reassign_match(
    match_id: UUID,
    body: MatchReassign,
    db: AsyncSession = Depends(get_db),
) -> MatchRead:
    """Reassign a match to a different invoice and/or transaction."""
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if body.invoice_id is not None:
        # Verify new invoice exists
        inv_check = await db.execute(
            select(Invoice).where(Invoice.id == body.invoice_id)
        )
        if not inv_check.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Invoice not found")
        match.invoice_id = body.invoice_id

    if body.transaction_id is not None:
        # Verify new transaction exists
        tx_check = await db.execute(
            select(Transaction).where(Transaction.id == body.transaction_id)
        )
        if not tx_check.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Transaction not found")
        match.transaction_id = body.transaction_id

    match.confirmed_by = ConfirmedBy.user
    match.confirmed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(match)
    return MatchRead.model_validate(match)


# ---------------------------------------------------------------------------
# Vendor alias learning (internal)
# ---------------------------------------------------------------------------


async def _learn_vendor_alias(
    db: AsyncSession,
    invoice: Optional[Invoice],
    transaction: Optional[Transaction],
) -> None:
    """On confirmed match, save bank description variant to vendor aliases."""
    if not invoice or not transaction:
        return

    # Find vendor by invoice vendor name
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.name == invoice.vendor)
    )
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        return

    description = transaction.description.strip()
    if not description:
        return

    # Add to aliases if not already present
    current_aliases = vendor.aliases or []
    if description not in current_aliases:
        vendor.aliases = current_aliases + [description]
