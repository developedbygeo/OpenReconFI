"""Tests for reports — timeframe resolution, PDF + Excel output."""

import pytest
from httpx import AsyncClient

from app.models.enums import ReportFormat, TimeframeType
from app.services.reporter import resolve_periods


# ---------------------------------------------------------------------------
# Timeframe resolution (unit tests — no DB needed)
# ---------------------------------------------------------------------------


def test_resolve_single_month():
    periods = resolve_periods(TimeframeType.single_month, period="2026-03")
    assert periods == ["2026-03"]


def test_resolve_single_month_missing_period():
    with pytest.raises(ValueError, match="period is required"):
        resolve_periods(TimeframeType.single_month)


def test_resolve_quarter_q1():
    periods = resolve_periods(TimeframeType.quarter, quarter=1, year=2026)
    assert periods == ["2026-01", "2026-02", "2026-03"]


def test_resolve_quarter_q4():
    periods = resolve_periods(TimeframeType.quarter, quarter=4, year=2026)
    assert periods == ["2026-10", "2026-11", "2026-12"]


def test_resolve_quarter_missing_params():
    with pytest.raises(ValueError, match="quarter and year are required"):
        resolve_periods(TimeframeType.quarter, quarter=1)


def test_resolve_quarter_invalid():
    with pytest.raises(ValueError, match="quarter must be"):
        resolve_periods(TimeframeType.quarter, quarter=5, year=2026)


def test_resolve_full_year():
    periods = resolve_periods(TimeframeType.full_year, year=2026)
    assert len(periods) == 12
    assert periods[0] == "2026-01"
    assert periods[-1] == "2026-12"


def test_resolve_full_year_missing():
    with pytest.raises(ValueError, match="year is required"):
        resolve_periods(TimeframeType.full_year)


def test_resolve_custom():
    periods = resolve_periods(
        TimeframeType.custom,
        from_period="2025-11",
        to_period="2026-03",
    )
    assert periods == ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03"]


def test_resolve_custom_missing():
    with pytest.raises(ValueError, match="from_period and to_period are required"):
        resolve_periods(TimeframeType.custom, from_period="2025-11")


def test_resolve_ytd():
    # YTD with explicit year — since we don't know current month, test full year fallback
    periods = resolve_periods(TimeframeType.ytd, year=2020)
    assert periods[0] == "2020-01"
    assert len(periods) == 12  # past year → all 12 months


# ---------------------------------------------------------------------------
# Report preview endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_preview_single_month(client: AsyncClient):
    resp = await client.post(
        "/reports/preview",
        json={
            "timeframe": "single_month",
            "format": "pdf",
            "period": "2026-03",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["timeframe_label"] == "2026-03"
    assert data["periods"] == ["2026-03"]
    assert data["format"] == "pdf"
    assert data["filename"] == "matchbook-report-2026-03.pdf"


@pytest.mark.asyncio
async def test_report_preview_quarter(client: AsyncClient):
    resp = await client.post(
        "/reports/preview",
        json={
            "timeframe": "quarter",
            "format": "excel",
            "quarter": 2,
            "year": 2026,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["timeframe_label"] == "Q2 2026"
    assert data["periods"] == ["2026-04", "2026-05", "2026-06"]
    assert data["filename"].endswith(".xlsx")


@pytest.mark.asyncio
async def test_report_preview_validation_error(client: AsyncClient):
    resp = await client.post(
        "/reports/preview",
        json={
            "timeframe": "single_month",
            "format": "pdf",
            # missing period
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Report generation (PDF + Excel)
# ---------------------------------------------------------------------------


async def _seed_for_report(client: AsyncClient) -> None:
    """Seed minimal data for report generation tests."""
    await client.post(
        "/invoices",
        json={
            "vendor": "Vercel",
            "amount_excl": "40.50",
            "amount_incl": "49.00",
            "vat_amount": "8.50",
            "vat_rate": "21.00",
            "invoice_date": "2026-01-15",
            "invoice_number": "V-001",
            "source": "manual",
            "period": "2026-01",
            "category": "SaaS",
        },
    )
    await client.post(
        "/invoices",
        json={
            "vendor": "AWS",
            "amount_excl": "100.00",
            "amount_incl": "109.00",
            "vat_amount": "9.00",
            "vat_rate": "9.00",
            "invoice_date": "2026-02-10",
            "invoice_number": "AWS-001",
            "source": "manual",
            "period": "2026-02",
            "category": "Infrastructure",
        },
    )


@pytest.mark.asyncio
async def test_generate_pdf_report(client: AsyncClient):
    try:
        from weasyprint import HTML  # noqa: F401
    except OSError:
        pytest.skip("WeasyPrint system libs not installed (pango/cairo)")

    await _seed_for_report(client)

    resp = await client.post(
        "/reports/generate",
        json={
            "timeframe": "single_month",
            "format": "pdf",
            "period": "2026-01",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "matchbook-report" in resp.headers["content-disposition"]
    # PDF starts with %PDF
    assert resp.content[:5] == b"%PDF-"


@pytest.mark.asyncio
async def test_generate_excel_report(client: AsyncClient):
    await _seed_for_report(client)

    resp = await client.post(
        "/reports/generate",
        json={
            "timeframe": "custom",
            "format": "excel",
            "from_period": "2026-01",
            "to_period": "2026-02",
        },
    )
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]
    # XLSX files start with PK (zip)
    assert resp.content[:2] == b"PK"


@pytest.mark.asyncio
async def test_generate_report_empty_period(client: AsyncClient):
    """Report for a period with no data should still generate successfully."""
    resp = await client.post(
        "/reports/generate",
        json={
            "timeframe": "single_month",
            "format": "excel",
            "period": "2020-01",
        },
    )
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"
