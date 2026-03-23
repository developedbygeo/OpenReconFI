"""Reporter service — timeframe resolution, PDF + Excel report generation."""

import io
from datetime import date
from decimal import Decimal
from typing import Optional

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    BillingCycle,
    InvoiceStatus,
    ReportFormat,
    TimeframeType,
    TransactionStatus,
)
from app.models.invoice import Invoice
from app.models.match import Match
from app.models.transaction import Transaction
from app.models.vendor import Vendor


# ---------------------------------------------------------------------------
# Timeframe resolution
# ---------------------------------------------------------------------------


def resolve_periods(
    timeframe: TimeframeType,
    period: Optional[str] = None,
    quarter: Optional[int] = None,
    year: Optional[int] = None,
    from_period: Optional[str] = None,
    to_period: Optional[str] = None,
) -> list[str]:
    """Convert a timeframe selection into a sorted list of YYYY-MM period strings."""
    if timeframe == TimeframeType.single_month:
        if not period:
            raise ValueError("period is required for single_month timeframe")
        return [period]

    if timeframe == TimeframeType.quarter:
        if quarter is None or year is None:
            raise ValueError("quarter and year are required for quarter timeframe")
        if quarter not in (1, 2, 3, 4):
            raise ValueError("quarter must be 1–4")
        start_month = (quarter - 1) * 3 + 1
        return [f"{year}-{m:02d}" for m in range(start_month, start_month + 3)]

    if timeframe == TimeframeType.ytd:
        if year is None:
            year = date.today().year
        current_month = date.today().month if year == date.today().year else 12
        return [f"{year}-{m:02d}" for m in range(1, current_month + 1)]

    if timeframe == TimeframeType.full_year:
        if year is None:
            raise ValueError("year is required for full_year timeframe")
        return [f"{year}-{m:02d}" for m in range(1, 13)]

    if timeframe == TimeframeType.custom:
        if not from_period or not to_period:
            raise ValueError("from_period and to_period are required for custom timeframe")
        periods: list[str] = []
        fy, fm = int(from_period[:4]), int(from_period[5:7])
        ty, tm = int(to_period[:4]), int(to_period[5:7])
        cy, cm = fy, fm
        while (cy, cm) <= (ty, tm):
            periods.append(f"{cy}-{cm:02d}")
            cm += 1
            if cm > 12:
                cm = 1
                cy += 1
        return periods

    raise ValueError(f"Unknown timeframe: {timeframe}")


def timeframe_label(
    timeframe: TimeframeType,
    periods: list[str],
    quarter: Optional[int] = None,
    year: Optional[int] = None,
) -> str:
    """Human-readable label for the timeframe."""
    if timeframe == TimeframeType.single_month:
        return periods[0]
    if timeframe == TimeframeType.quarter:
        return f"Q{quarter} {year}"
    if timeframe == TimeframeType.ytd:
        return f"Year to date {year or date.today().year}"
    if timeframe == TimeframeType.full_year:
        return f"Full year {year}"
    if timeframe == TimeframeType.custom:
        return f"{periods[0]} – {periods[-1]}"
    return "Report"


# ---------------------------------------------------------------------------
# Data aggregation
# ---------------------------------------------------------------------------


async def _gather_report_data(db: AsyncSession, periods: list[str]) -> dict:
    """Query all data needed for the report across the given periods."""
    # Summary totals
    summary_result = await db.execute(
        select(
            func.coalesce(func.sum(Invoice.amount_excl), 0),
            func.coalesce(func.sum(Invoice.vat_amount), 0),
            func.coalesce(func.sum(Invoice.amount_incl), 0),
            func.count(Invoice.id),
            func.count(Invoice.id).filter(Invoice.status == InvoiceStatus.matched),
            func.count(Invoice.id).filter(Invoice.status == InvoiceStatus.unmatched),
        ).where(Invoice.period.in_(periods))
    )
    s = summary_result.one()
    summary = {
        "total_excl": s[0],
        "total_vat": s[1],
        "total_incl": s[2],
        "invoice_count": s[3],
        "matched": s[4],
        "unmatched": s[5],
    }

    # Per-month breakdown
    monthly_result = await db.execute(
        select(
            Invoice.period,
            func.sum(Invoice.amount_excl),
            func.sum(Invoice.vat_amount),
            func.sum(Invoice.amount_incl),
            func.count(Invoice.id),
        )
        .where(Invoice.period.in_(periods))
        .group_by(Invoice.period)
        .order_by(Invoice.period)
    )
    monthly = [
        {"period": r[0], "excl": r[1], "vat": r[2], "incl": r[3], "count": r[4]}
        for r in monthly_result.all()
    ]

    # By category
    cat_col = func.coalesce(Invoice.category, "Uncategorized").label("cat")
    cat_result = await db.execute(
        select(
            cat_col,
            func.sum(Invoice.amount_excl),
            func.sum(Invoice.vat_amount),
            func.sum(Invoice.amount_incl),
            func.count(Invoice.id),
        )
        .where(Invoice.period.in_(periods))
        .group_by(cat_col)
        .order_by(func.sum(Invoice.amount_excl).desc())
    )
    by_category = [
        {"category": r[0], "excl": r[1], "vat": r[2], "incl": r[3], "count": r[4]}
        for r in cat_result.all()
    ]

    # By vendor
    vendor_result = await db.execute(
        select(
            Invoice.vendor,
            func.sum(Invoice.amount_excl),
            func.sum(Invoice.vat_amount),
            func.sum(Invoice.amount_incl),
            func.count(Invoice.id),
        )
        .where(Invoice.period.in_(periods))
        .group_by(Invoice.vendor)
        .order_by(func.sum(Invoice.amount_excl).desc())
    )
    by_vendor = [
        {"vendor": r[0], "excl": r[1], "vat": r[2], "incl": r[3], "count": r[4]}
        for r in vendor_result.all()
    ]

    # Full invoice list
    inv_result = await db.execute(
        select(Invoice)
        .where(Invoice.period.in_(periods))
        .order_by(Invoice.invoice_date)
    )
    invoices = inv_result.scalars().all()

    # Unmatched transactions
    unmatched_result = await db.execute(
        select(Transaction)
        .where(
            Transaction.period.in_(periods),
            Transaction.status == TransactionStatus.unmatched,
        )
        .order_by(Transaction.tx_date)
    )
    unmatched_txs = unmatched_result.scalars().all()

    # Missing invoices (vendors with billing cycle that expected invoice in range)
    missing: list[dict] = []
    vendor_q = await db.execute(
        select(Vendor).where(Vendor.billing_cycle != BillingCycle.irregular)
    )
    for vendor in vendor_q.scalars().all():
        cycle_months = {
            BillingCycle.monthly: 1,
            BillingCycle.bimonthly: 2,
            BillingCycle.quarterly: 3,
            BillingCycle.annual: 12,
        }.get(vendor.billing_cycle)
        if cycle_months is None:
            continue
        for p in periods:
            exists = await db.execute(
                select(func.count(Invoice.id)).where(
                    Invoice.vendor == vendor.name,
                    Invoice.period == p,
                )
            )
            if exists.scalar_one() == 0:
                missing.append({"vendor": vendor.name, "period": p})

    return {
        "summary": summary,
        "monthly": monthly,
        "by_category": by_category,
        "by_vendor": by_vendor,
        "invoices": invoices,
        "unmatched_txs": unmatched_txs,
        "missing": missing,
    }


def _fmt(value) -> str:
    """Format a Decimal/float for display."""
    if isinstance(value, Decimal):
        return f"{value:,.2f}"
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return str(value)


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------


def _render_html(label: str, data: dict) -> str:
    """Build the HTML string for the PDF report."""
    today = date.today().strftime("%Y-%m-%d")
    s = data["summary"]

    html_parts = [
        f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; margin: 40px; color: #333; font-size: 11px; }}
  h1 {{ color: #1a1a2e; border-bottom: 2px solid #1a1a2e; padding-bottom: 8px; }}
  h2 {{ color: #16213e; margin-top: 30px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 10px 0 20px; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; }}
  th {{ background: #f4f4f8; font-weight: 600; }}
  td.num {{ text-align: right; }}
  .cover {{ text-align: center; margin-top: 120px; }}
  .cover h1 {{ font-size: 28px; border: none; }}
  .cover p {{ font-size: 14px; color: #666; }}
  .page-break {{ page-break-before: always; }}
</style>
</head><body>

<div class="cover">
  <h1>Matchbook — Financial Report</h1>
  <p><strong>{label}</strong></p>
  <p>Generated {today}</p>
</div>

<div class="page-break"></div>

<h2>Summary</h2>
<table>
  <tr><th>Metric</th><th>Value</th></tr>
  <tr><td>Total spend (ex VAT)</td><td class="num">&euro;{_fmt(s['total_excl'])}</td></tr>
  <tr><td>Total VAT</td><td class="num">&euro;{_fmt(s['total_vat'])}</td></tr>
  <tr><td>Total spend (incl VAT)</td><td class="num">&euro;{_fmt(s['total_incl'])}</td></tr>
  <tr><td>Invoice count</td><td class="num">{s['invoice_count']}</td></tr>
  <tr><td>Matched</td><td class="num">{s['matched']}</td></tr>
  <tr><td>Unmatched</td><td class="num">{s['unmatched']}</td></tr>
</table>""",
    ]

    # Per-month breakdown (if multi-period)
    if len(data["monthly"]) > 1:
        html_parts.append("""
<h2>Monthly Breakdown</h2>
<table>
  <tr><th>Period</th><th>Ex VAT</th><th>VAT</th><th>Incl VAT</th><th>Invoices</th></tr>""")
        for m in data["monthly"]:
            html_parts.append(
                f'  <tr><td>{m["period"]}</td>'
                f'<td class="num">&euro;{_fmt(m["excl"])}</td>'
                f'<td class="num">&euro;{_fmt(m["vat"])}</td>'
                f'<td class="num">&euro;{_fmt(m["incl"])}</td>'
                f'<td class="num">{m["count"]}</td></tr>'
            )
        html_parts.append("</table>")

    # By category
    html_parts.append("""
<h2>Expenses by Category</h2>
<table>
  <tr><th>Category</th><th>Ex VAT</th><th>VAT</th><th>Incl VAT</th><th>Invoices</th></tr>""")
    for c in data["by_category"]:
        html_parts.append(
            f'  <tr><td>{c["category"]}</td>'
            f'<td class="num">&euro;{_fmt(c["excl"])}</td>'
            f'<td class="num">&euro;{_fmt(c["vat"])}</td>'
            f'<td class="num">&euro;{_fmt(c["incl"])}</td>'
            f'<td class="num">{c["count"]}</td></tr>'
        )
    html_parts.append("</table>")

    # By vendor
    html_parts.append("""
<h2>Expenses by Vendor</h2>
<table>
  <tr><th>Vendor</th><th>Ex VAT</th><th>VAT</th><th>Incl VAT</th><th>Invoices</th></tr>""")
    for v in data["by_vendor"]:
        html_parts.append(
            f'  <tr><td>{v["vendor"]}</td>'
            f'<td class="num">&euro;{_fmt(v["excl"])}</td>'
            f'<td class="num">&euro;{_fmt(v["vat"])}</td>'
            f'<td class="num">&euro;{_fmt(v["incl"])}</td>'
            f'<td class="num">{v["count"]}</td></tr>'
        )
    html_parts.append("</table>")

    # Invoice list
    html_parts.append("""
<div class="page-break"></div>
<h2>Invoice List</h2>
<table>
  <tr><th>Vendor</th><th>Invoice #</th><th>Date</th><th>Ex VAT</th><th>VAT</th><th>Incl VAT</th><th>Status</th></tr>""")
    for inv in data["invoices"]:
        html_parts.append(
            f"  <tr><td>{inv.vendor}</td>"
            f"<td>{inv.invoice_number}</td>"
            f"<td>{inv.invoice_date}</td>"
            f'<td class="num">&euro;{_fmt(inv.amount_excl)}</td>'
            f'<td class="num">&euro;{_fmt(inv.vat_amount)}</td>'
            f'<td class="num">&euro;{_fmt(inv.amount_incl)}</td>'
            f"<td>{inv.status.value}</td></tr>"
        )
    html_parts.append("</table>")

    # Unmatched transactions
    if data["unmatched_txs"]:
        html_parts.append("""
<h2>Unmatched Transactions</h2>
<table>
  <tr><th>Date</th><th>Description</th><th>Counterparty</th><th>Amount</th></tr>""")
        for tx in data["unmatched_txs"]:
            html_parts.append(
                f"  <tr><td>{tx.tx_date}</td>"
                f"<td>{tx.description}</td>"
                f"<td>{tx.counterparty}</td>"
                f'<td class="num">&euro;{_fmt(tx.amount)}</td></tr>'
            )
        html_parts.append("</table>")

    # Missing invoices
    if data["missing"]:
        html_parts.append("""
<h2>Missing Invoices</h2>
<table>
  <tr><th>Vendor</th><th>Expected Period</th></tr>""")
        for mi in data["missing"]:
            html_parts.append(
                f'  <tr><td>{mi["vendor"]}</td><td>{mi["period"]}</td></tr>'
            )
        html_parts.append("</table>")

    html_parts.append("</body></html>")
    return "\n".join(html_parts)


async def generate_pdf(db: AsyncSession, label: str, periods: list[str]) -> bytes:
    """Generate a PDF report for the given periods."""
    data = await _gather_report_data(db, periods)
    html_str = _render_html(label, data)
    from weasyprint import HTML  # lazy import — requires system libs (pango, cairo)

    pdf_bytes = HTML(string=html_str).write_pdf()
    return pdf_bytes


# ---------------------------------------------------------------------------
# Excel generation
# ---------------------------------------------------------------------------


def _write_header(ws, headers: list[str]) -> None:
    """Write a styled header row."""
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1a1a2e", end_color="1a1a2e", fill_type="solid")
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")


async def generate_excel(db: AsyncSession, label: str, periods: list[str]) -> bytes:
    """Generate an Excel report for the given periods."""
    data = await _gather_report_data(db, periods)
    wb = openpyxl.Workbook()

    # --- Summary sheet ---
    ws = wb.active
    ws.title = "Summary"
    _write_header(ws, ["Metric", "Value"])
    s = data["summary"]
    rows = [
        ("Total spend (ex VAT)", float(s["total_excl"])),
        ("Total VAT", float(s["total_vat"])),
        ("Total spend (incl VAT)", float(s["total_incl"])),
        ("Invoice count", s["invoice_count"]),
        ("Matched", s["matched"]),
        ("Unmatched", s["unmatched"]),
    ]
    for i, (metric, val) in enumerate(rows, 2):
        ws.cell(row=i, column=1, value=metric)
        ws.cell(row=i, column=2, value=val)
    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 18

    # --- Monthly breakdown sheet ---
    if len(data["monthly"]) > 1:
        ws_m = wb.create_sheet("Monthly Breakdown")
        _write_header(ws_m, ["Period", "Ex VAT", "VAT", "Incl VAT", "Invoices"])
        for i, m in enumerate(data["monthly"], 2):
            ws_m.cell(row=i, column=1, value=m["period"])
            ws_m.cell(row=i, column=2, value=float(m["excl"]))
            ws_m.cell(row=i, column=3, value=float(m["vat"]))
            ws_m.cell(row=i, column=4, value=float(m["incl"]))
            ws_m.cell(row=i, column=5, value=m["count"])

    # --- By category sheet ---
    ws_c = wb.create_sheet("By Category")
    _write_header(ws_c, ["Category", "Ex VAT", "VAT", "Incl VAT", "Invoices"])
    for i, c in enumerate(data["by_category"], 2):
        ws_c.cell(row=i, column=1, value=c["category"])
        ws_c.cell(row=i, column=2, value=float(c["excl"]))
        ws_c.cell(row=i, column=3, value=float(c["vat"]))
        ws_c.cell(row=i, column=4, value=float(c["incl"]))
        ws_c.cell(row=i, column=5, value=c["count"])

    # --- By vendor sheet ---
    ws_v = wb.create_sheet("By Vendor")
    _write_header(ws_v, ["Vendor", "Ex VAT", "VAT", "Incl VAT", "Invoices"])
    for i, v in enumerate(data["by_vendor"], 2):
        ws_v.cell(row=i, column=1, value=v["vendor"])
        ws_v.cell(row=i, column=2, value=float(v["excl"]))
        ws_v.cell(row=i, column=3, value=float(v["vat"]))
        ws_v.cell(row=i, column=4, value=float(v["incl"]))
        ws_v.cell(row=i, column=5, value=v["count"])

    # --- Invoice list sheet ---
    ws_i = wb.create_sheet("Invoices")
    _write_header(ws_i, ["Vendor", "Invoice #", "Date", "Ex VAT", "VAT", "Incl VAT", "Status"])
    for i, inv in enumerate(data["invoices"], 2):
        ws_i.cell(row=i, column=1, value=inv.vendor)
        ws_i.cell(row=i, column=2, value=inv.invoice_number)
        ws_i.cell(row=i, column=3, value=str(inv.invoice_date))
        ws_i.cell(row=i, column=4, value=float(inv.amount_excl))
        ws_i.cell(row=i, column=5, value=float(inv.vat_amount))
        ws_i.cell(row=i, column=6, value=float(inv.amount_incl))
        ws_i.cell(row=i, column=7, value=inv.status.value)

    # --- Unmatched transactions sheet ---
    if data["unmatched_txs"]:
        ws_u = wb.create_sheet("Unmatched Transactions")
        _write_header(ws_u, ["Date", "Description", "Counterparty", "Amount"])
        for i, tx in enumerate(data["unmatched_txs"], 2):
            ws_u.cell(row=i, column=1, value=str(tx.tx_date))
            ws_u.cell(row=i, column=2, value=tx.description)
            ws_u.cell(row=i, column=3, value=tx.counterparty)
            ws_u.cell(row=i, column=4, value=float(tx.amount))

    # --- Missing invoices sheet ---
    if data["missing"]:
        ws_mi = wb.create_sheet("Missing Invoices")
        _write_header(ws_mi, ["Vendor", "Expected Period"])
        for i, mi in enumerate(data["missing"], 2):
            ws_mi.cell(row=i, column=1, value=mi["vendor"])
            ws_mi.cell(row=i, column=2, value=mi["period"])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
