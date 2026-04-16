import logging
from datetime import date, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.enums import ReportFormat, TransactionStatus
from app.models.match import Match
from app.models.transaction import Transaction
from app.schemas.report import ReportMeta, ReportRequest
from app.services.drive import create_period_summary_folder, upload_report
from app.services.reporter import (
    generate_excel,
    generate_pdf,
    resolve_periods,
    timeframe_label,
    _invoice_filename,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/generate",
    response_class=Response,
)
async def generate_report(
    body: ReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate a financial report in PDF or Excel format and upload to Drive."""
    try:
        periods = resolve_periods(
            timeframe=body.timeframe,
            period=body.period,
            quarter=body.quarter,
            year=body.year,
            from_period=body.from_period,
            to_period=body.to_period,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    label = timeframe_label(
        timeframe=body.timeframe,
        periods=periods,
        quarter=body.quarter,
        year=body.year,
    )

    slim = body.variant == "summary"
    suffix = "-summary" if slim else ""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

    if body.format == ReportFormat.pdf:
        content = await generate_pdf(db, label, periods, slim=slim)
        filename = f"openreconfi-{timestamp}-report{suffix}.pdf"
        media_type = "application/pdf"
    else:
        content = await generate_excel(db, label, periods, slim=slim)
        filename = f"openreconfi-{timestamp}-report{suffix}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # Upload to Drive in background: /Reports/<Month>/
    month_label = periods[0] if len(periods) == 1 else f"{periods[0]}_to_{periods[-1]}"
    background_tasks.add_task(_upload_report_to_drive, content, filename, month_label, media_type)

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _upload_report_to_drive(
    content: bytes, filename: str, month: str, mimetype: str
) -> None:
    """Upload report to Drive — runs as a background task."""
    try:
        result = await upload_report(content, filename, month, mimetype)
        logger.info("Report uploaded to Drive: %s", result["url"])
    except Exception:
        logger.exception("Failed to upload report to Drive")


@router.post(
    "/preview",
    response_model=ReportMeta,
)
async def preview_report(body: ReportRequest) -> ReportMeta:
    """Preview what a report would contain without generating it."""
    try:
        periods = resolve_periods(
            timeframe=body.timeframe,
            period=body.period,
            quarter=body.quarter,
            year=body.year,
            from_period=body.from_period,
            to_period=body.to_period,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    label = timeframe_label(
        timeframe=body.timeframe,
        periods=periods,
        quarter=body.quarter,
        year=body.year,
    )

    ext = "pdf" if body.format == ReportFormat.pdf else "xlsx"
    suffix = "-summary" if getattr(body, "variant", "full") == "summary" else ""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"openreconfi-{timestamp}-report{suffix}.{ext}"

    return ReportMeta(
        timeframe_label=label,
        periods=periods,
        format=body.format,
        filename=filename,
    )


class PeriodSummaryRequest(BaseModel):
    period: str  # YYYY-MM


class PeriodSummaryResponse(BaseModel):
    folder_url: str
    invoices_copied: int


@router.post(
    "/period-summary",
    response_model=PeriodSummaryResponse,
)
async def create_period_summary(
    body: PeriodSummaryRequest,
    db: AsyncSession = Depends(get_db),
) -> PeriodSummaryResponse:
    """Create a Drive folder with all matched invoices for a period."""
    from calendar import monthrange
    from sqlalchemy import or_

    # Compute boundary dates
    y, m = int(body.period[:4]), int(body.period[5:7])
    prev_m = m - 1 if m > 1 else 12
    prev_y = y if m > 1 else y - 1
    prev_last_day = date(prev_y, prev_m, monthrange(prev_y, prev_m)[1])
    next_m = m + 1 if m < 12 else 1
    next_y = y if m < 12 else y + 1
    next_first_day = date(next_y, next_m, 1)

    # Get all matched transactions for the period + boundary days
    tx_result = await db.execute(
        select(Transaction)
        .where(
            or_(
                Transaction.period == body.period,
                Transaction.tx_date == prev_last_day,
                Transaction.tx_date == next_first_day,
            )
        )
        .where(Transaction.status == TransactionStatus.matched)
    )
    matched_txs = tx_result.scalars().all()

    if not matched_txs:
        raise HTTPException(status_code=404, detail="No matched transactions for this period")

    # Get matches with invoices
    matched_ids = [tx.id for tx in matched_txs]
    match_result = await db.execute(
        select(Match)
        .where(Match.transaction_id.in_(matched_ids))
        .options(selectinload(Match.invoice))
    )
    matches = match_result.scalars().all()

    # Collect unique invoices that have Drive files
    seen_ids = set()
    invoice_files = []
    for m in matches:
        inv = m.invoice
        if inv and inv.drive_file_id and inv.id not in seen_ids:
            seen_ids.add(inv.id)
            base = _invoice_filename(inv)
            filename = base if "." in base else f"{base}{_get_ext(inv)}"
            invoice_files.append({
                "drive_file_id": inv.drive_file_id,
                "filename": filename,
            })

    if not invoice_files:
        raise HTTPException(status_code=404, detail="No invoices with Drive files found for this period")

    folder_url = await create_period_summary_folder(body.period, invoice_files)

    return PeriodSummaryResponse(
        folder_url=folder_url,
        invoices_copied=len(invoice_files),
    )


def _get_ext(inv) -> str:
    """Get file extension from raw_extraction or default to .pdf."""
    if inv.raw_extraction and isinstance(inv.raw_extraction, dict):
        fname = inv.raw_extraction.get("filename") or inv.raw_extraction.get("file_name") or ""
        if "." in fname:
            return fname[fname.rfind("."):]
    return ".pdf"
