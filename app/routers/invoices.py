from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate, InvoiceList, InvoiceRead, InvoiceUpdate

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=InvoiceList, tags=["invoices"])
async def list_invoices(
    period: Optional[str] = Query(None, description="Filter by period e.g. 2026-03"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> InvoiceList:
    query = select(Invoice)
    count_query = select(func.count(Invoice.id))

    if period:
        query = query.where(Invoice.period == period)
        count_query = count_query.where(Invoice.period == period)
    if status:
        query = query.where(Invoice.status == status)
        count_query = count_query.where(Invoice.status == status)

    query = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    invoices = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    return InvoiceList(
        items=[InvoiceRead.model_validate(inv) for inv in invoices],
        total=total,
    )


@router.get("/{invoice_id}", response_model=InvoiceRead, tags=["invoices"])
async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> InvoiceRead:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return InvoiceRead.model_validate(invoice)


@router.post("", response_model=InvoiceRead, status_code=201, tags=["invoices"])
async def create_invoice(
    body: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
) -> InvoiceRead:
    invoice = Invoice(**body.model_dump())
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return InvoiceRead.model_validate(invoice)


@router.patch("/{invoice_id}", response_model=InvoiceRead, tags=["invoices"])
async def update_invoice(
    invoice_id: UUID,
    body: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
) -> InvoiceRead:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(invoice, field, value)

    await db.commit()
    await db.refresh(invoice)
    return InvoiceRead.model_validate(invoice)


@router.post("/upload", response_model=InvoiceRead, status_code=201, tags=["invoices"])
async def upload_invoice(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> InvoiceRead:
    """Manual PDF upload — extracts via LLM, stores invoice."""
    from app.services.llm import extract_invoice_from_pdf

    pdf_bytes = await file.read()
    extracted = await extract_invoice_from_pdf(pdf_bytes)

    invoice = Invoice(
        vendor=extracted["vendor"],
        amount_excl=extracted["amount_excl"],
        amount_incl=extracted["amount_incl"],
        vat_amount=extracted["vat_amount"],
        vat_rate=extracted["vat_rate"],
        invoice_date=extracted["invoice_date"],
        invoice_number=extracted["invoice_number"],
        source="manual",
        status="pending",
        period=extracted["invoice_date"].strftime("%Y-%m"),
        raw_extraction=extracted.get("raw"),
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return InvoiceRead.model_validate(invoice)
