"""Tests for dashboard — missing invoice detection + spending summaries."""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helper: seed invoices for spending tests
# ---------------------------------------------------------------------------


async def _seed_invoices(client: AsyncClient) -> None:
    """Create a mix of invoices across vendors, categories, periods, VAT rates."""
    invoices = [
        {
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
        {
            "vendor": "Hetzner",
            "amount_excl": "10.00",
            "amount_incl": "12.10",
            "vat_amount": "2.10",
            "vat_rate": "21.00",
            "invoice_date": "2026-01-20",
            "invoice_number": "HZ-001",
            "source": "manual",
            "period": "2026-01",
            "category": "Infrastructure",
        },
        {
            "vendor": "Vercel",
            "amount_excl": "40.50",
            "amount_incl": "49.00",
            "vat_amount": "8.50",
            "vat_rate": "21.00",
            "invoice_date": "2026-02-15",
            "invoice_number": "V-002",
            "source": "manual",
            "period": "2026-02",
            "category": "SaaS",
        },
        {
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
    ]
    for inv in invoices:
        resp = await client.post("/invoices", json=inv)
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Missing invoice alert tests (Phase 3 — unchanged)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_invoices_no_vendors(client: AsyncClient):
    resp = await client.get("/dashboard/missing-invoices")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_missing_invoice_vendor_never_invoiced(client: AsyncClient):
    """Vendor with monthly cycle but zero invoices should be flagged."""
    await client.post(
        "/vendors",
        json={"name": "Ghost Vendor", "billing_cycle": "monthly"},
    )

    resp = await client.get("/dashboard/missing-invoices", params={"as_of": "2026-03"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["vendor_name"] == "Ghost Vendor"
    assert data["items"][0]["expected_period"] == "2026-03"
    assert data["items"][0]["last_invoice_period"] is None


@pytest.mark.asyncio
async def test_missing_invoice_monthly_vendor(client: AsyncClient):
    """Monthly vendor with Jan invoice should flag Feb as missing when checked in March."""
    await client.post(
        "/vendors",
        json={"name": "Vercel", "billing_cycle": "monthly"},
    )
    await client.post(
        "/invoices",
        json={
            "vendor": "Vercel",
            "amount_excl": "40.50",
            "amount_incl": "49.00",
            "vat_amount": "8.50",
            "vat_rate": "21.00",
            "invoice_date": "2026-01-15",
            "invoice_number": "INV-001",
            "source": "manual",
            "period": "2026-01",
        },
    )

    resp = await client.get("/dashboard/missing-invoices", params={"as_of": "2026-03"})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["vendor_name"] == "Vercel"
    assert data["items"][0]["expected_period"] == "2026-02"
    assert data["items"][0]["last_invoice_period"] == "2026-01"


@pytest.mark.asyncio
async def test_no_missing_invoice_when_up_to_date(client: AsyncClient):
    """Monthly vendor with Feb invoice should not be flagged when checked in Feb."""
    await client.post(
        "/vendors",
        json={"name": "Hetzner", "billing_cycle": "monthly"},
    )
    await client.post(
        "/invoices",
        json={
            "vendor": "Hetzner",
            "amount_excl": "10.00",
            "amount_incl": "12.10",
            "vat_amount": "2.10",
            "vat_rate": "21.00",
            "invoice_date": "2026-02-15",
            "invoice_number": "HZ-002",
            "source": "manual",
            "period": "2026-02",
        },
    )

    resp = await client.get("/dashboard/missing-invoices", params={"as_of": "2026-02"})
    data = resp.json()
    flagged_names = [a["vendor_name"] for a in data["items"]]
    assert "Hetzner" not in flagged_names


@pytest.mark.asyncio
async def test_missing_invoice_quarterly_vendor(client: AsyncClient):
    """Quarterly vendor: Q1 invoice exists, checked in Q2 — should flag Q2."""
    await client.post(
        "/vendors",
        json={"name": "AWS", "billing_cycle": "quarterly"},
    )
    await client.post(
        "/invoices",
        json={
            "vendor": "AWS",
            "amount_excl": "200.00",
            "amount_incl": "242.00",
            "vat_amount": "42.00",
            "vat_rate": "21.00",
            "invoice_date": "2026-01-10",
            "invoice_number": "AWS-Q1",
            "source": "manual",
            "period": "2026-01",
        },
    )

    resp = await client.get("/dashboard/missing-invoices", params={"as_of": "2026-04"})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["vendor_name"] == "AWS"
    assert data["items"][0]["expected_period"] == "2026-04"


@pytest.mark.asyncio
async def test_irregular_vendor_not_flagged(client: AsyncClient):
    """Vendors with irregular billing cycle should never be flagged."""
    await client.post(
        "/vendors",
        json={"name": "One-off Supplier", "billing_cycle": "irregular"},
    )

    resp = await client.get("/dashboard/missing-invoices", params={"as_of": "2026-12"})
    data = resp.json()
    flagged_names = [a["vendor_name"] for a in data["items"]]
    assert "One-off Supplier" not in flagged_names


# ---------------------------------------------------------------------------
# Spend summary tests (Phase 4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spend_summary_empty(client: AsyncClient):
    resp = await client.get("/dashboard/spend-summary", params={"period": "2026-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["total_spend_excl"]) == 0
    assert data["invoice_count"] == 0


@pytest.mark.asyncio
async def test_spend_summary(client: AsyncClient):
    await _seed_invoices(client)

    resp = await client.get("/dashboard/spend-summary", params={"period": "2026-01"})
    assert resp.status_code == 200
    data = resp.json()
    # Jan: Vercel 40.50 + Hetzner 10.00 = 50.50 excl
    assert float(data["total_spend_excl"]) == 50.50
    assert float(data["total_vat"]) == 10.60  # 8.50 + 2.10
    assert float(data["total_spend_incl"]) == 61.10  # 49.00 + 12.10
    assert data["invoice_count"] == 2


@pytest.mark.asyncio
async def test_spend_by_category(client: AsyncClient):
    await _seed_invoices(client)

    resp = await client.get("/dashboard/spend-by-category", params={"period": "2026-01"})
    assert resp.status_code == 200
    data = resp.json()
    categories = {item["category"]: item for item in data["items"]}
    assert "SaaS" in categories
    assert "Infrastructure" in categories
    assert float(categories["SaaS"]["total_excl"]) == 40.50
    assert float(categories["Infrastructure"]["total_excl"]) == 10.00


@pytest.mark.asyncio
async def test_spend_by_vendor(client: AsyncClient):
    await _seed_invoices(client)

    resp = await client.get("/dashboard/spend-by-vendor", params={"period": "2026-02"})
    assert resp.status_code == 200
    data = resp.json()
    vendors = {item["vendor"]: item for item in data["items"]}
    assert "Vercel" in vendors
    assert "AWS" in vendors
    assert float(vendors["AWS"]["total_excl"]) == 100.00
    assert vendors["Vercel"]["invoice_count"] == 1


@pytest.mark.asyncio
async def test_vat_summary(client: AsyncClient):
    await _seed_invoices(client)

    # Feb has two different VAT rates: 21% (Vercel) and 9% (AWS)
    resp = await client.get("/dashboard/vat-summary", params={"period": "2026-02"})
    assert resp.status_code == 200
    data = resp.json()
    rates = {float(item["vat_rate"]): item for item in data["items"]}
    assert 21.0 in rates
    assert 9.0 in rates
    assert float(rates[21.0]["total_vat"]) == 8.50
    assert float(rates[9.0]["total_vat"]) == 9.00


@pytest.mark.asyncio
async def test_mom_comparison(client: AsyncClient):
    await _seed_invoices(client)

    resp = await client.get("/dashboard/mom-comparison", params={"year": 2026})
    assert resp.status_code == 200
    data = resp.json()
    periods = {item["period"]: item for item in data["items"]}
    assert "2026-01" in periods
    assert "2026-02" in periods
    assert periods["2026-01"]["invoice_count"] == 2
    assert periods["2026-02"]["invoice_count"] == 2
    # Feb total: 40.50 + 100.00 = 140.50
    assert float(periods["2026-02"]["total_excl"]) == 140.50


@pytest.mark.asyncio
async def test_mom_comparison_empty_year(client: AsyncClient):
    resp = await client.get("/dashboard/mom-comparison", params={"year": 2020})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
