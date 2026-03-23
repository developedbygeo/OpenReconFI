"""Tests for embeddings service — text formatting + API mocking."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.embeddings import (
    format_invoice_text,
    format_transaction_text,
    embed_text,
    embed_texts,
)


# ---------------------------------------------------------------------------
# Text format tests (no mocking needed)
# ---------------------------------------------------------------------------


class FakeInvoice:
    vendor = "Vercel"
    category = "SaaS"
    amount_incl = 49.00
    invoice_date = "2026-01-15"
    period = "2026-01"


class FakeInvoiceNoCategory:
    vendor = "AWS"
    category = None
    amount_incl = 109.00
    invoice_date = "2026-02-10"
    period = "2026-02"


class FakeTransaction:
    counterparty = "Vercel Inc"
    description = "Monthly subscription"
    amount = -49.00
    tx_date = "2026-01-20"


def test_format_invoice_text():
    text = format_invoice_text(FakeInvoice())
    assert "Vercel" in text
    assert "SaaS" in text
    assert "49.00" in text or "49.0" in text
    assert "2026-01-15" in text
    assert "2026-01" in text


def test_format_invoice_text_no_category():
    text = format_invoice_text(FakeInvoiceNoCategory())
    assert "AWS" in text
    assert "Uncategorized" in text


def test_format_transaction_text():
    text = format_transaction_text(FakeTransaction())
    assert "Vercel Inc" in text
    assert "Monthly subscription" in text
    assert "49.0" in text or "-49.00" in text
    assert "2026-01-20" in text


# ---------------------------------------------------------------------------
# API call tests (mocked)
# ---------------------------------------------------------------------------


FAKE_EMBEDDING = [0.1] * 1024


@pytest.mark.asyncio
@patch("app.services.embeddings.httpx.AsyncClient")
async def test_embed_text(mock_client_cls):
    # httpx.Response.json() and raise_for_status() are sync methods
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [{"embedding": FAKE_EMBEDDING}],
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    result = await embed_text("test text")
    assert len(result) == 1024
    assert result[0] == 0.1

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert "embeddings" in str(call_kwargs)


@pytest.mark.asyncio
@patch("app.services.embeddings.httpx.AsyncClient")
async def test_embed_texts_batch(mock_client_cls):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"embedding": FAKE_EMBEDDING},
            {"embedding": [0.2] * 1024},
        ],
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client

    result = await embed_texts(["text one", "text two"])
    assert len(result) == 2
    assert len(result[0]) == 1024
    assert result[1][0] == 0.2


# ---------------------------------------------------------------------------
# Embed + store (integration via HTTP client)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_invoice_via_api(client):
    """Create an invoice via API — embedding happens in background, not at creation."""
    resp = await client.post(
        "/invoices",
        json={
            "vendor": "Vercel",
            "amount_excl": "40.50",
            "amount_incl": "49.00",
            "vat_amount": "8.50",
            "vat_rate": "21.00",
            "invoice_date": "2026-01-15",
            "invoice_number": "EMB-001",
            "source": "manual",
            "period": "2026-01",
            "category": "SaaS",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["vendor"] == "Vercel"
