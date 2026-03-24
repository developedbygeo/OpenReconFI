import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_invoices_empty(client: AsyncClient):
    resp = await client.get("/invoices")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_invoice(client: AsyncClient):
    payload = {
        "vendor": "Vercel Inc.",
        "amount_excl": "40.50",
        "amount_incl": "49.00",
        "vat_amount": "8.50",
        "vat_rate": "21.00",
        "invoice_date": "2026-03-01",
        "invoice_number": "INV-2026-0312",
        "source": "manual",
        "period": "2026-03",
    }
    resp = await client.post("/invoices", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["vendor"] == "Vercel Inc."
    assert data["amount_excl"] == "40.50"
    assert data["status"] == "pending"
    assert data["period"] == "2026-03"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_invoice(client: AsyncClient):
    # Create first
    payload = {
        "vendor": "Hetzner",
        "amount_excl": "10.00",
        "amount_incl": "12.10",
        "vat_amount": "2.10",
        "vat_rate": "21.00",
        "invoice_date": "2026-02-15",
        "invoice_number": "HZ-001",
        "source": "manual",
        "period": "2026-02",
    }
    create_resp = await client.post("/invoices", json=payload)
    invoice_id = create_resp.json()["id"]

    # Get by ID
    resp = await client.get(f"/invoices/{invoice_id}")
    assert resp.status_code == 200
    assert resp.json()["vendor"] == "Hetzner"


@pytest.mark.asyncio
async def test_get_invoice_not_found(client: AsyncClient):
    resp = await client.get("/invoices/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_invoice(client: AsyncClient):
    # Create
    payload = {
        "vendor": "DigitalOcean",
        "amount_excl": "5.00",
        "amount_incl": "6.05",
        "vat_amount": "1.05",
        "vat_rate": "21.00",
        "invoice_date": "2026-01-10",
        "invoice_number": "DO-999",
        "source": "manual",
        "period": "2026-01",
    }
    create_resp = await client.post("/invoices", json=payload)
    invoice_id = create_resp.json()["id"]

    # Update category
    resp = await client.patch(
        f"/invoices/{invoice_id}",
        json={"category": "SaaS"},
    )
    assert resp.status_code == 200
    assert resp.json()["category"] == "SaaS"


@pytest.mark.asyncio
async def test_list_invoices_filter_by_period(client: AsyncClient):
    # Create two invoices with different periods
    for period, vendor in [("2026-01", "Vendor A"), ("2026-02", "Vendor B")]:
        await client.post(
            "/invoices",
            json={
                "vendor": vendor,
                "amount_excl": "10.00",
                "amount_incl": "12.10",
                "vat_amount": "2.10",
                "vat_rate": "21.00",
                "invoice_date": f"{period}-15",
                "invoice_number": f"INV-{vendor}",
                "source": "manual",
                "period": period,
            },
        )

    resp = await client.get("/invoices", params={"period": "2026-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(inv["period"] == "2026-01" for inv in data["items"])
