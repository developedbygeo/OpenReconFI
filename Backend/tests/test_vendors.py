"""Tests for vendor CRUD, billing cycle, invoice history."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_vendors_empty(client: AsyncClient):
    resp = await client.get("/vendors")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_vendor(client: AsyncClient):
    resp = await client.post(
        "/vendors",
        json={
            "name": "Vercel",
            "billing_cycle": "monthly",
            "default_category": "SaaS",
            "default_vat_rate": "21.00",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Vercel"
    assert data["billing_cycle"] == "monthly"
    assert data["default_category"] == "SaaS"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_vendor(client: AsyncClient):
    create = await client.post("/vendors", json={"name": "Hetzner"})
    vendor_id = create.json()["id"]

    resp = await client.get(f"/vendors/{vendor_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Hetzner"


@pytest.mark.asyncio
async def test_get_vendor_not_found(client: AsyncClient):
    resp = await client.get(f"/vendors/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_vendor(client: AsyncClient):
    create = await client.post("/vendors", json={"name": "DigitalOcean"})
    vendor_id = create.json()["id"]

    resp = await client.patch(
        f"/vendors/{vendor_id}",
        json={"billing_cycle": "annual", "aliases": ["DO", "DIGITALOCEAN"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["billing_cycle"] == "annual"
    assert data["aliases"] == ["DO", "DIGITALOCEAN"]


@pytest.mark.asyncio
async def test_delete_vendor(client: AsyncClient):
    create = await client.post("/vendors", json={"name": "Temp Vendor"})
    vendor_id = create.json()["id"]

    resp = await client.delete(f"/vendors/{vendor_id}")
    assert resp.status_code == 200

    get_resp = await client.get(f"/vendors/{vendor_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_vendor_invoice_history(client: AsyncClient):
    # Create vendor
    create = await client.post("/vendors", json={"name": "Vercel Inc."})
    vendor_id = create.json()["id"]

    # Create invoices for this vendor
    for period in ["2026-01", "2026-02"]:
        await client.post(
            "/invoices",
            json={
                "vendor": "Vercel Inc.",
                "amount_excl": "40.50",
                "amount_incl": "49.00",
                "vat_amount": "8.50",
                "vat_rate": "21.00",
                "invoice_date": f"{period}-01",
                "invoice_number": f"INV-{period}",
                "source": "manual",
                "period": period,
            },
        )

    resp = await client.get(f"/vendors/{vendor_id}/invoices")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2

    # Filter by period
    resp = await client.get(f"/vendors/{vendor_id}/invoices", params={"period": "2026-01"})
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_vendor_invoice_history_not_found(client: AsyncClient):
    resp = await client.get(f"/vendors/{uuid.uuid4()}/invoices")
    assert resp.status_code == 404
