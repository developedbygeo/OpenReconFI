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
from app.schemas.match import MatchConfirm, MatchCreate, MatchList, MatchRead, MatchReassign
from app.schemas.reconciliation import (
    MatchTriggerRequest,
    MatchTriggerResponse,
    PeriodReconciliation,
    StatementUploadResponse,
    UnmatchedInvoiceSummary,
    UnmatchedTransactionSummary,
)
from app.schemas.transaction import TransactionDismiss, TransactionList, TransactionRead, TransactionUpdate

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])

@router.post(
    "/upload",
    response_model=StatementUploadResponse,
    status_code=201,
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
        # Detect withholdings by description as fallback
        desc_upper = tx_data["description"].upper()
        is_withholding = tx_data.get("withholding") or "ΕΝΑΝΤΙ ΚΕΡΔ" in desc_upper or "ENANTI KERD" in desc_upper

        if is_withholding:
            status = TransactionStatus.withholding
        elif tx_data.get("no_invoice"):
            status = TransactionStatus.no_invoice
        else:
            status = TransactionStatus.unmatched
        tx = Transaction(
            tx_date=tx_data["tx_date"],
            value_date=tx_data.get("value_date"),
            amount=tx_data["amount"],
            original_amount=tx_data.get("original_amount"),
            original_currency=tx_data.get("original_currency"),
            description=tx_data["description"],
            counterparty=tx_data["counterparty"],
            counterparty_iban=tx_data.get("counterparty_iban"),
            category=tx_data.get("category"),
            period=tx_data["tx_date"].strftime("%Y-%m"),
            status=status,
        )
        db.add(tx)

    await db.commit()

    return StatementUploadResponse(
        transactions_parsed=len(parsed),
        period=period,
    )


@router.get(
    "/overview",
    response_model=PeriodReconciliation,
)
async def period_overview(
    period: str = Query(description="Period to reconcile (YYYY-MM)"),
    db: AsyncSession = Depends(get_db),
) -> PeriodReconciliation:
    """Full reconciliation overview for a period — shows whether the month is complete."""
    from decimal import Decimal

    # Invoices
    inv_result = await db.execute(
        select(Invoice).where(Invoice.period == period)
    )
    invoices = inv_result.scalars().all()

    total_invoices = len(invoices)
    matched_invoices = sum(1 for i in invoices if i.status == InvoiceStatus.matched)
    unmatched_invoices_list = [i for i in invoices if i.status != InvoiceStatus.matched]
    total_invoiced_incl = sum(i.amount_incl for i in invoices)

    # All transactions for the period
    tx_result = await db.execute(
        select(Transaction).where(Transaction.period == period)
    )
    transactions = tx_result.scalars().all()

    # Split by type
    expense_txs = [t for t in transactions if t.amount < 0 and t.status not in (TransactionStatus.withholding,)]
    no_invoice_txs = [t for t in expense_txs if t.status == TransactionStatus.no_invoice]
    matchable_txs = [t for t in expense_txs if t.status != TransactionStatus.no_invoice]
    withholding_txs = [t for t in transactions if t.status == TransactionStatus.withholding]
    earning_txs = [t for t in transactions if t.amount > 0]

    matched_txs = [t for t in matchable_txs if t.status == TransactionStatus.matched]
    unmatched_txs = [t for t in matchable_txs if t.status == TransactionStatus.unmatched]

    total_bank_debits = abs(sum(t.amount for t in expense_txs))
    no_invoice_total = abs(sum(t.amount for t in no_invoice_txs))
    withholding_total = abs(sum(t.amount for t in withholding_txs))
    earnings_total = sum(t.amount for t in earning_txs)

    # Gap: bank debits (excluding no_invoice + withholdings) vs invoiced amount
    matchable_debits = abs(sum(t.amount for t in matchable_txs))
    gap = matchable_debits - total_invoiced_incl

    is_complete = (
        len(unmatched_txs) == 0
        and len(matchable_txs) > 0
    )

    return PeriodReconciliation(
        period=period,
        is_complete=is_complete,
        total_invoices=total_invoices,
        matched_invoices=matched_invoices,
        unmatched_invoices=len(unmatched_invoices_list),
        total_invoiced_incl=total_invoiced_incl,
        total_transactions=len(matchable_txs),
        matched_transactions=len(matched_txs),
        unmatched_transactions=len(unmatched_txs),
        total_bank_debits=total_bank_debits,
        no_invoice_count=len(no_invoice_txs),
        no_invoice_total=no_invoice_total,
        withholding_count=len(withholding_txs),
        withholding_total=withholding_total,
        earnings_count=len(earning_txs),
        earnings_total=earnings_total,
        gap=gap,
        unmatched_invoice_list=[
            UnmatchedInvoiceSummary(
                id=i.id,
                vendor=i.vendor,
                invoice_number=i.invoice_number,
                amount_incl=i.amount_incl,
                invoice_date=str(i.invoice_date),
                currency=i.currency,
                category=i.category,
            )
            for i in unmatched_invoices_list
        ],
        unmatched_transaction_list=[
            UnmatchedTransactionSummary(
                id=t.id,
                counterparty=t.counterparty,
                description=t.description,
                amount=t.amount,
                tx_date=str(t.tx_date),
                category=t.category,
            )
            for t in unmatched_txs
        ],
    )


@router.delete("/transactions")
async def delete_all_transactions(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete all transactions (and their matches), reset linked invoice statuses."""
    from sqlalchemy import text, update

    # Reset invoices that were matched via now-deleted matches back to unmatched
    await db.execute(
        update(Invoice)
        .where(Invoice.status == InvoiceStatus.matched)
        .values(status=InvoiceStatus.unmatched)
    )
    await db.execute(text("DELETE FROM matches"))
    result = await db.execute(select(func.count(Transaction.id)))
    count = result.scalar_one()
    await db.execute(text("DELETE FROM transactions"))
    await db.commit()
    return {"deleted": count}


@router.post(
    "/transactions/{transaction_id}/dismiss",
    response_model=TransactionRead,
)
async def dismiss_transaction(
    transaction_id: UUID,
    body: TransactionDismiss,
    db: AsyncSession = Depends(get_db),
) -> TransactionRead:
    """Dismiss a transaction — mark as no_invoice with an optional note (e.g. 'currency conversion fee')."""
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    tx.status = TransactionStatus.no_invoice
    if body.note:
        tx.note = body.note
    await db.commit()
    await db.refresh(tx)
    return TransactionRead.model_validate(tx)


@router.patch(
    "/transactions/{transaction_id}",
    response_model=TransactionRead,
)
async def update_transaction(
    transaction_id: UUID,
    body: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
) -> TransactionRead:
    """Update a transaction's category or note."""
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tx, field, value)

    await db.commit()
    await db.refresh(tx)
    return TransactionRead.model_validate(tx)


@router.get("/transactions", response_model=TransactionList)
async def list_transactions(
    period: Optional[str] = Query(None),
    status: Optional[TransactionStatus] = Query(None),
    category: Optional[str] = Query(None),
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
    if category:
        query = query.where(Transaction.category == category)
        count_query = count_query.where(Transaction.category == category)

    query = query.order_by(Transaction.tx_date.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    transactions = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    return TransactionList(
        items=[TransactionRead.model_validate(tx) for tx in transactions],
        total=total,
    )


@router.post("/match", response_model=MatchTriggerResponse)
async def trigger_matching(
    body: MatchTriggerRequest,
    db: AsyncSession = Depends(get_db),
) -> MatchTriggerResponse:
    """Trigger hybrid matching: deterministic first, then LLM for leftovers."""
    from app.services.matcher import run_matching

    result = await run_matching(db, period=body.period)

    total = len(result.deterministic_matches) + len(result.llm_matches)
    return MatchTriggerResponse(
        matches_suggested=total,
        period=body.period,
        deterministic_matches=len(result.deterministic_matches),
        llm_matches=len(result.llm_matches),
        fees_dismissed=len(result.fees_dismissed),
    )

@router.post("/matches", response_model=MatchRead, status_code=201)
async def create_match(
    body: MatchCreate,
    db: AsyncSession = Depends(get_db),
) -> MatchRead:
    """Manually create a match between an unmatched invoice and transaction."""
    # Validate invoice exists and is unmatched
    inv_result = await db.execute(
        select(Invoice).where(Invoice.id == body.invoice_id)
    )
    invoice = inv_result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == InvoiceStatus.matched:
        raise HTTPException(status_code=409, detail="Invoice is already matched")

    # Validate transaction exists and is unmatched
    tx_result = await db.execute(
        select(Transaction).where(Transaction.id == body.transaction_id)
    )
    transaction = tx_result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if transaction.status == TransactionStatus.matched:
        raise HTTPException(status_code=409, detail="Transaction is already matched")

    # Create the match
    match = Match(
        invoice_id=body.invoice_id,
        transaction_id=body.transaction_id,
        confidence=1.00,
        rationale="Manual match by user",
        confirmed_by=ConfirmedBy.user,
        confirmed_at=datetime.now(timezone.utc),
    )
    db.add(match)

    # Update statuses
    invoice.status = InvoiceStatus.matched
    transaction.status = TransactionStatus.matched

    # Learn vendor alias
    await _learn_vendor_alias(db, invoice, transaction)

    await db.commit()
    await db.refresh(match)
    return MatchRead.model_validate(match)


@router.get("/matches", response_model=MatchList)
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


@router.get("/matches/{match_id}", response_model=MatchRead)
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
