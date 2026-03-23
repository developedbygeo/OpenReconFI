"""Tests for the reconciliation router."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_transactions_empty(client: AsyncClient):
    resp = await client.get("/reconciliation/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_matches_empty(client: AsyncClient):
    resp = await client.get("/reconciliation/matches")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_match_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/reconciliation/matches/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_confirm_match_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await client.post(f"/reconciliation/matches/{fake_id}/confirm", json={})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reject_match_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/reconciliation/matches/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_match_trigger_no_data(client: AsyncClient):
    """Triggering match with no invoices/transactions returns 0 matches."""
    resp = await client.post(
        "/reconciliation/match",
        json={"period": "2026-03"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["matches_suggested"] == 0
    assert data["period"] == "2026-03"
