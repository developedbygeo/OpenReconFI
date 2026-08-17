import calendar
import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.models.vendor import Vendor
from app.services.dedup import find_duplicate_invoice
from app.services.drive import upload_pdf
from app.services.gmail import fetch_unread_invoices
from app.services.llm import extract_invoice_from_pdf

logger = logging.getLogger(__name__)


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
    skipped_details: list[str] = []
    errors: list[str] = []

    for att in attachments:
        try:
            extracted = await extract_invoice_from_pdf(
                att.data, sender=att.sender, subject=att.subject
            )

            # Deduplicate by normalized invoice number + date + amount. Amount
            # replaces vendor as the collision guard: different vendors do reuse
            # short sequential numbers (e.g. "1") on the same date, but rarely
            # for the same amount. Vendor itself is unusable as a key — a newer
            # extraction prompt rewords it and every invoice looks new.
            duplicate = await find_duplicate_invoice(
                db,
                invoice_number=extracted["invoice_number"],
                invoice_date=extracted["invoice_date"],
                amount_incl=extracted["amount_incl"],
            )
            if duplicate is not None:
                # Skipping a genuinely new invoice is worse than storing a
                # duplicate, so record both sides of every collision rather than
                # just incrementing a counter.
                detail = (
                    f"{att.filename}: {extracted['vendor']} "
                    f"{extracted['invoice_number']} {extracted['invoice_date']} "
                    f"{extracted['amount_incl']} — matched existing "
                    f"{duplicate.vendor} {duplicate.invoice_number} "
                    f"{duplicate.invoice_date} {duplicate.amount_incl} "
                    f"({duplicate.id})"
                )
                logger.warning("Skipped as duplicate — %s", detail)
                skipped_details.append(detail)
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
        "skipped_details": skipped_details,
        "errors": errors,
    }
