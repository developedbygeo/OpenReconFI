from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.invoice import Invoice
from app.models.vendor import Vendor
from app.schemas.invoice import InvoiceList, InvoiceRead
from app.schemas.vendor import VendorCreate, VendorList, VendorRead, VendorUpdate

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("", response_model=VendorList)
async def list_vendors(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> VendorList:
    query = select(Vendor).order_by(Vendor.name).offset(skip).limit(limit)
    count_query = select(func.count(Vendor.id))

    result = await db.execute(query)
    vendors = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    return VendorList(
        items=[VendorRead.model_validate(v) for v in vendors],
        total=total,
    )


@router.get("/{vendor_id}", response_model=VendorRead)
async def get_vendor(
    vendor_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> VendorRead:
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return VendorRead.model_validate(vendor)


@router.post("", response_model=VendorRead, status_code=201)
async def create_vendor(
    body: VendorCreate,
    db: AsyncSession = Depends(get_db),
) -> VendorRead:
    vendor = Vendor(**body.model_dump())
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)
    return VendorRead.model_validate(vendor)


@router.patch("/{vendor_id}", response_model=VendorRead)
async def update_vendor(
    vendor_id: UUID,
    body: VendorUpdate,
    db: AsyncSession = Depends(get_db),
) -> VendorRead:
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vendor, field, value)

    await db.commit()
    await db.refresh(vendor)
    return VendorRead.model_validate(vendor)


@router.delete("/{vendor_id}", response_model=VendorRead)
async def delete_vendor(
    vendor_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> VendorRead:
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    response = VendorRead.model_validate(vendor)
    await db.delete(vendor)
    await db.commit()
    return response


@router.get(
    "/{vendor_id}/invoices",
    response_model=InvoiceList,
)
async def get_vendor_invoices(
    vendor_id: UUID,
    period: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> InvoiceList:
    """Get invoice history for a vendor."""
    # Verify vendor exists
    vendor_result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    query = select(Invoice).where(Invoice.vendor == vendor.name)
    count_query = select(func.count(Invoice.id)).where(Invoice.vendor == vendor.name)

    if period:
        query = query.where(Invoice.period == period)
        count_query = count_query.where(Invoice.period == period)

    query = query.order_by(Invoice.invoice_date.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    invoices = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    return InvoiceList(
        items=[InvoiceRead.model_validate(inv) for inv in invoices],
        total=total,
    )
