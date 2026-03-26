"""Dashboard router — missing invoice alerts (Phase 3), spending summaries (Phase 4)."""

from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.enums import BillingCycle, InvoiceStatus, TransactionStatus
from app.models.invoice import Invoice
from app.models.transaction import Transaction
from app.models.vendor import Vendor
from app.schemas.dashboard import (
    CategorySpend,
    CategorySpendList,
    EarningsSummary,
    EarningTransaction,
    MissingInvoiceAlert,
    MissingInvoiceAlertList,
    MoMComparison,
    MonthlySpend,
    SpendSummary,
    TaxCategoryBreakdown,
    TaxSummary,
    TaxTransaction,
    VATBreakdown,
    VATSummary,
    VendorSpend,
    VendorSpendList,
    WithholdingSummary,
    WithholdingTransaction,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _billing_cycle_months(cycle: BillingCycle) -> int | None:
    """Return the number of months between expected invoices, or None if one-off."""
    return {
        BillingCycle.monthly: 1,
        BillingCycle.annual: 12,
        BillingCycle.one_off: None,
    }[cycle]


def _next_expected_period(last_invoice_date: date, cycle: BillingCycle) -> str | None:
    """Calculate the next expected period from the last invoice date and billing cycle."""
    months = _billing_cycle_months(cycle)
    if months is None:
        return None
    next_date = last_invoice_date + relativedelta(months=months)
    return next_date.strftime("%Y-%m")


def _default_period() -> str:
    return date.today().strftime("%Y-%m")


# ---------------------------------------------------------------------------
# Missing invoices (Phase 3)
# ---------------------------------------------------------------------------


@router.get(
    "/missing-invoices",
    response_model=MissingInvoiceAlertList,
)
async def missing_invoice_alerts(
    as_of: str = Query(
        default=None,
        description="Check for missing invoices as of this period (YYYY-MM). Defaults to current month.",
    ),
    db: AsyncSession = Depends(get_db),
) -> MissingInvoiceAlertList:
    """Detect vendors with missing invoices based on billing cycle + last invoice date."""
    if as_of is None:
        as_of = _default_period()

    vendor_result = await db.execute(
        select(Vendor).where(Vendor.billing_cycle != BillingCycle.one_off)
    )
    vendors = vendor_result.scalars().all()

    alerts: list[MissingInvoiceAlert] = []

    for vendor in vendors:
        latest_result = await db.execute(
            select(Invoice.invoice_date, Invoice.period)
            .where(Invoice.vendor == vendor.name)
            .order_by(Invoice.invoice_date.desc())
            .limit(1)
        )
        latest = latest_result.first()

        if latest is None:
            alerts.append(
                MissingInvoiceAlert(
                    vendor_id=vendor.id,
                    vendor_name=vendor.name,
                    billing_cycle=vendor.billing_cycle,
                    last_invoice_period=None,
                    expected_period=as_of,
                )
            )
            continue

        last_date, last_period = latest
        expected = _next_expected_period(last_date, vendor.billing_cycle)

        if expected is None:
            continue

        if expected <= as_of:
            exists_result = await db.execute(
                select(func.count(Invoice.id)).where(
                    Invoice.vendor == vendor.name,
                    Invoice.period == expected,
                )
            )
            count = exists_result.scalar_one()

            if count == 0:
                alerts.append(
                    MissingInvoiceAlert(
                        vendor_id=vendor.id,
                        vendor_name=vendor.name,
                        billing_cycle=vendor.billing_cycle,
                        last_invoice_period=last_period,
                        expected_period=expected,
                    )
                )

    return MissingInvoiceAlertList(items=alerts, total=len(alerts))


# ---------------------------------------------------------------------------
# Spend summary (Phase 4)
# ---------------------------------------------------------------------------


@router.get(
    "/spend-summary",
    response_model=SpendSummary,
)
async def spend_summary(
    period: str = Query(
        default=None,
        description="Period filter (YYYY-MM). Defaults to current month.",
    ),
    db: AsyncSession = Depends(get_db),
) -> SpendSummary:
    """Monthly spend summary — totals, invoice count, match breakdown."""
    if period is None:
        period = _default_period()

    result = await db.execute(
        select(
            func.coalesce(func.sum(Invoice.amount_excl), 0),
            func.coalesce(func.sum(Invoice.vat_amount), 0),
            func.coalesce(func.sum(Invoice.amount_incl), 0),
            func.count(Invoice.id),
            func.count(Invoice.id).filter(Invoice.status == InvoiceStatus.matched),
            func.count(Invoice.id).filter(Invoice.status == InvoiceStatus.unmatched),
        ).where(Invoice.period == period)
    )
    row = result.one()

    return SpendSummary(
        total_spend_excl=row[0],
        total_vat=row[1],
        total_spend_incl=row[2],
        invoice_count=row[3],
        matched_count=row[4],
        unmatched_count=row[5],
    )


# ---------------------------------------------------------------------------
# Spend by category (Phase 4)
# ---------------------------------------------------------------------------


@router.get(
    "/spend-by-category",
    response_model=CategorySpendList,
)
async def spend_by_category(
    period: str = Query(
        default=None,
        description="Period filter (YYYY-MM). Defaults to current month.",
    ),
    db: AsyncSession = Depends(get_db),
) -> CategorySpendList:
    """Expenses grouped by category for the given period."""
    if period is None:
        period = _default_period()

    cat_col = func.coalesce(Invoice.category, "Uncategorized").label("cat")
    result = await db.execute(
        select(
            cat_col,
            func.sum(Invoice.amount_excl),
            func.sum(Invoice.vat_amount),
            func.sum(Invoice.amount_incl),
            func.count(Invoice.id),
        )
        .where(Invoice.period == period)
        .group_by(cat_col)
        .order_by(func.sum(Invoice.amount_excl).desc())
    )
    rows = result.all()

    return CategorySpendList(
        items=[
            CategorySpend(
                category=row[0],
                total_excl=row[1],
                total_vat=row[2],
                total_incl=row[3],
                invoice_count=row[4],
            )
            for row in rows
        ]
    )


# ---------------------------------------------------------------------------
# Spend by vendor (Phase 4)
# ---------------------------------------------------------------------------


@router.get(
    "/spend-by-vendor",
    response_model=VendorSpendList,
)
async def spend_by_vendor(
    period: str = Query(
        default=None,
        description="Period filter (YYYY-MM). Defaults to current month.",
    ),
    db: AsyncSession = Depends(get_db),
) -> VendorSpendList:
    """Expenses grouped by vendor for the given period."""
    if period is None:
        period = _default_period()

    result = await db.execute(
        select(
            Invoice.vendor,
            func.sum(Invoice.amount_excl),
            func.sum(Invoice.vat_amount),
            func.sum(Invoice.amount_incl),
            func.count(Invoice.id),
        )
        .where(Invoice.period == period)
        .group_by(Invoice.vendor)
        .order_by(func.sum(Invoice.amount_excl).desc())
    )
    rows = result.all()

    return VendorSpendList(
        items=[
            VendorSpend(
                vendor=row[0],
                total_excl=row[1],
                total_vat=row[2],
                total_incl=row[3],
                invoice_count=row[4],
            )
            for row in rows
        ]
    )


# ---------------------------------------------------------------------------
# VAT summary (Phase 4)
# ---------------------------------------------------------------------------


@router.get(
    "/vat-summary",
    response_model=VATSummary,
)
async def vat_summary(
    period: str = Query(
        default=None,
        description="Period filter (YYYY-MM). Defaults to current month.",
    ),
    db: AsyncSession = Depends(get_db),
) -> VATSummary:
    """VAT breakdown by rate for the given period."""
    if period is None:
        period = _default_period()

    result = await db.execute(
        select(
            Invoice.vat_rate,
            func.sum(Invoice.amount_excl),
            func.sum(Invoice.vat_amount),
            func.count(Invoice.id),
        )
        .where(Invoice.period == period)
        .group_by(Invoice.vat_rate)
        .order_by(Invoice.vat_rate.desc())
    )
    rows = result.all()

    return VATSummary(
        items=[
            VATBreakdown(
                vat_rate=row[0],
                total_excl=row[1],
                total_vat=row[2],
                invoice_count=row[3],
            )
            for row in rows
        ]
    )


# ---------------------------------------------------------------------------
# Month-over-month comparison (Phase 4)
# ---------------------------------------------------------------------------


@router.get(
    "/mom-comparison",
    response_model=MoMComparison,
)
async def mom_comparison(
    year: int = Query(
        default=None,
        description="Year to compare months for. Defaults to current year.",
    ),
    db: AsyncSession = Depends(get_db),
) -> MoMComparison:
    """Month-over-month spend comparison for the given year."""
    if year is None:
        year = date.today().year

    year_prefix = str(year)

    result = await db.execute(
        select(
            Invoice.period,
            func.sum(Invoice.amount_excl),
            func.sum(Invoice.vat_amount),
            func.sum(Invoice.amount_incl),
            func.count(Invoice.id),
        )
        .where(Invoice.period.like(f"{year_prefix}-%"))
        .group_by(Invoice.period)
        .order_by(Invoice.period)
    )
    rows = result.all()

    return MoMComparison(
        items=[
            MonthlySpend(
                period=row[0],
                total_excl=row[1],
                total_vat=row[2],
                total_incl=row[3],
                invoice_count=row[4],
            )
            for row in rows
        ]
    )


# ---------------------------------------------------------------------------
# Tax / no-invoice transactions (Phase 4)
# ---------------------------------------------------------------------------


@router.get(
    "/tax-summary",
    response_model=TaxSummary,
)
async def tax_summary(
    period: str = Query(
        default=None,
        description="Period filter (YYYY-MM). Defaults to current month.",
    ),
    db: AsyncSession = Depends(get_db),
) -> TaxSummary:
    """Tax and non-invoiceable transactions for the given period (bank fees, tax payments, etc.)."""
    if period is None:
        period = _default_period()

    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.period == period,
            Transaction.status == TransactionStatus.no_invoice,
            Transaction.amount < 0,
        )
        .order_by(Transaction.tx_date)
    )
    transactions = result.scalars().all()

    total = sum(tx.amount for tx in transactions)

    # Group by category
    cat_totals: dict[str, dict] = {}
    for tx in transactions:
        cat = tx.category or "Uncategorized"
        if cat not in cat_totals:
            cat_totals[cat] = {"total": Decimal(0), "count": 0}
        cat_totals[cat]["total"] += tx.amount
        cat_totals[cat]["count"] += 1

    return TaxSummary(
        period=period,
        total_amount=total,
        transaction_count=len(transactions),
        by_category=[
            TaxCategoryBreakdown(
                category=cat,
                total_amount=data["total"],
                transaction_count=data["count"],
            )
            for cat, data in sorted(cat_totals.items(), key=lambda x: x[1]["total"])
        ],
        items=[
            TaxTransaction(
                id=tx.id,
                tx_date=str(tx.tx_date),
                amount=tx.amount,
                description=tx.description,
                counterparty=tx.counterparty,
                category=tx.category,
            )
            for tx in transactions
        ],
    )


# ---------------------------------------------------------------------------
# Earnings (credits / incoming payments)
# ---------------------------------------------------------------------------


@router.get(
    "/earnings",
    response_model=EarningsSummary,
)
async def earnings(
    period: str = Query(
        default=None,
        description="Period filter (YYYY-MM). Defaults to current month.",
    ),
    db: AsyncSession = Depends(get_db),
) -> EarningsSummary:
    """Incoming payments (credits) for the given period."""
    if period is None:
        period = _default_period()

    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.period == period,
            Transaction.amount > 0,
        )
        .order_by(Transaction.tx_date)
    )
    transactions = result.scalars().all()

    total = sum(tx.amount for tx in transactions)

    return EarningsSummary(
        period=period,
        total_earnings=total,
        transaction_count=len(transactions),
        items=[
            EarningTransaction(
                id=tx.id,
                tx_date=str(tx.tx_date),
                amount=tx.amount,
                description=tx.description,
                counterparty=tx.counterparty,
                category=tx.category,
            )
            for tx in transactions
        ],
    )


# ---------------------------------------------------------------------------
# Withholdings (owner drawings against earnings)
# ---------------------------------------------------------------------------


@router.get(
    "/withholdings",
    response_model=WithholdingSummary,
)
async def withholdings(
    period: str = Query(
        default=None,
        description="Period filter (YYYY-MM). Defaults to current month.",
    ),
    db: AsyncSession = Depends(get_db),
) -> WithholdingSummary:
    """Owner withdrawals against earnings for the given period."""
    if period is None:
        period = _default_period()

    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.period == period,
            Transaction.status == TransactionStatus.withholding,
        )
        .order_by(Transaction.tx_date)
    )
    transactions = result.scalars().all()

    total = sum(tx.amount for tx in transactions)

    return WithholdingSummary(
        period=period,
        total_amount=total,
        transaction_count=len(transactions),
        items=[
            WithholdingTransaction(
                id=tx.id,
                tx_date=str(tx.tx_date),
                amount=tx.amount,
                description=tx.description,
                counterparty=tx.counterparty,
            )
            for tx in transactions
        ],
    )
