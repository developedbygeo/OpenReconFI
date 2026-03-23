"""Reports router — timeframe + format picker, file download + Drive upload."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.enums import ReportFormat
from app.schemas.report import ReportMeta, ReportRequest
from app.services.drive import upload_report
from app.services.reporter import (
    generate_excel,
    generate_pdf,
    resolve_periods,
    timeframe_label,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/generate",
    response_class=Response,
    tags=["reports"],
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

    if body.format == ReportFormat.pdf:
        content = await generate_pdf(db, label, periods)
        filename = f"matchbook-report-{periods[0]}.pdf"
        media_type = "application/pdf"
    else:
        content = await generate_excel(db, label, periods)
        filename = f"matchbook-report-{periods[0]}.xlsx"
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
    tags=["reports"],
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
    filename = f"matchbook-report-{periods[0]}.{ext}"

    return ReportMeta(
        timeframe_label=label,
        periods=periods,
        format=body.format,
        filename=filename,
    )
