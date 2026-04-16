import calendar
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.models.vendor import Vendor
from app.services.drive import upload_pdf
from app.services.gmail import fetch_unread_invoices
from app.services.llm import extract_invoice_from_pdf


def _build_filename(
    invoice_date: Any, vendor: str, amount_incl: Decimal, invoice_number: str
) -> str:
    """Build structured filename: 2026-03_Vercel_EUR49.00_INV-1234.pdf"""
    period = invoice_date.strftime("%Y-%m")
    amount_str = f"EUR{amount_incl:.2f}"
    safe_vendor = vendor.replace(" ", "-").replace("/", "-")
    safe_inv_num = invoice_number.replace(" ", "-").replace("/", "-")
    return f"{period}_{safe_vendor}_{amount_str}_{safe_inv_num}.pdf"


async def _ensure_vendor(
    db: AsyncSession, vendor_name: str, category: str | None
) -> Vendor:
    """Get or create a Vendor record. Returns the vendor."""
    result = await db.execute(
        select(Vendor).where(Vendor.name == vendor_name)
    )
    vendor = result.scalar_one_or_none()
    if vendor is not None:
        return vendor

    vendor = Vendor(
        name=vendor_name,
        default_category=category,
    )
    db.add(vendor)
    await db.flush()
    return vendor


async def run_collection(db: AsyncSession) -> dict[str, Any]:
    """Run the full collection pipeline. Returns a summary dict."""
    attachments = await fetch_unread_invoices()

    processed = 0
    skipped = 0
    errors: list[str] = []

    for att in attachments:
        try:
            extracted = await extract_invoice_from_pdf(att.data)

            # Deduplicate by invoice number + date
            existing = await db.execute(
                select(Invoice.id).where(
                    Invoice.invoice_number == extracted["invoice_number"],
                    Invoice.invoice_date == extracted["invoice_date"],
                )
            )
            if existing.scalar_one_or_none() is not None:
                skipped += 1
                continue

            # Auto-create vendor if new
            category = extracted.get("category")
            vendor = await _ensure_vendor(db, extracted["vendor"], category)

            # Use vendor's default category if LLM didn't assign one
            if not category and vendor.default_category:
                category = vendor.default_category

            filename = _build_filename(
                extracted["invoice_date"],
                extracted["vendor"],
                extracted["amount_incl"],
                extracted["invoice_number"],
            )

            year = str(extracted["invoice_date"].year)
            month = calendar.month_name[extracted["invoice_date"].month]

            drive_result = await upload_pdf(att.data, filename, year, month)

            period = extracted["invoice_date"].strftime("%Y-%m")

            invoice = Invoice(
                vendor=extracted["vendor"],
                amount_excl=extracted["amount_excl"],
                amount_incl=extracted["amount_incl"],
                vat_amount=extracted["vat_amount"],
                vat_rate=extracted["vat_rate"],
                invoice_date=extracted["invoice_date"],
                invoice_number=extracted["invoice_number"],
                currency=extracted.get("currency", "EUR"),
                category=category,
                source="gmail",
                status="pending",
                period=period,
                drive_url=drive_result["url"],
                drive_file_id=drive_result["file_id"],
                raw_extraction=extracted.get("raw"),
            )
            db.add(invoice)
            processed += 1

        except Exception as exc:
            errors.append(f"{att.filename}: {exc}")

    await db.commit()

    return {
        "emails_found": len(attachments),
        "invoices_processed": processed,
        "skipped_duplicates": skipped,
        "errors": errors,
    }
