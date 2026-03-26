"""Tests for LLM service — extraction, statement parsing, matching (all mocked)."""

import json
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_extract_invoice_from_pdf():
    """Test LLM extraction with mocked Claude API and pdfplumber."""
    from app.services.llm import extract_invoice_from_pdf

    mock_response = {
        "vendor": "Vercel Inc.",
        "invoice_number": "INV-2026-0312",
        "invoice_date": "2026-03-01",
        "amount_excl": 40.50,
        "amount_incl": 49.00,
        "vat_amount": 8.50,
        "vat_rate": 21.0,
        "currency": "EUR",
        "iban": "NL02ABNA0123456789",
    }

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(mock_response))]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Invoice #INV-2026-0312\nVercel Inc.\nTotal: €49.00"

    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with (
        patch("app.services.llm._get_client", return_value=mock_client),
        patch("app.services.llm.pdfplumber.open", return_value=mock_pdf),
    ):
        result = await extract_invoice_from_pdf(b"fake-pdf-bytes")

    assert result["vendor"] == "Vercel Inc."
    assert result["invoice_number"] == "INV-2026-0312"
    assert result["invoice_date"] == date(2026, 3, 1)
    assert result["amount_excl"] == Decimal("40.50")
    assert result["amount_incl"] == Decimal("49.00")
    assert result["vat_amount"] == Decimal("8.50")
    assert result["vat_rate"] == Decimal("21.0")
    assert result["raw"]["iban"] == "NL02ABNA0123456789"


@pytest.mark.asyncio
async def test_extract_invoice_empty_pdf():
    """Test that extraction raises ValueError for empty PDF."""
    from app.services.llm import extract_invoice_from_pdf

    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""

    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch("app.services.llm.pdfplumber.open", return_value=mock_pdf):
        with pytest.raises(ValueError, match="Could not extract text"):
            await extract_invoice_from_pdf(b"empty-pdf")


# ---------------------------------------------------------------------------
# Statement parsing tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_bank_statement():
    """Test statement parsing with mocked Claude API."""
    from app.services.llm import parse_bank_statement

    mock_response = [
        {
            "tx_date": "2026-03-04",
            "amount": -49.00,
            "description": "VERCEL INC SUBSCRIPTION",
            "counterparty": "Vercel Inc",
            "counterparty_iban": "NL02ABNA0123456789",
        },
        {
            "tx_date": "2026-03-05",
            "amount": -10.00,
            "description": "HETZNER CLOUD",
            "counterparty": "Hetzner",
            "counterparty_iban": None,
        },
    ]

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(mock_response))]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("app.services.llm._get_client", return_value=mock_client):
        result = await parse_bank_statement("Date,Amount,Desc\n2026-03-04,-49,VERCEL")

    assert len(result) == 2
    assert result[0]["tx_date"] == date(2026, 3, 4)
    assert result[0]["amount"] == Decimal("-49.00")
    assert result[0]["counterparty"] == "Vercel Inc"
    assert result[0]["counterparty_iban"] == "NL02ABNA0123456789"
    assert result[1]["tx_date"] == date(2026, 3, 5)
    assert result[1]["counterparty_iban"] is None


@pytest.mark.asyncio
async def test_parse_bank_statement_empty():
    """Empty statement text raises ValueError."""
    from app.services.llm import parse_bank_statement

    with pytest.raises(ValueError, match="Empty statement text"):
        await parse_bank_statement("")


@pytest.mark.asyncio
async def test_parse_bank_statement_validation_error():
    """Invalid transaction data raises ValueError."""
    from app.services.llm import parse_bank_statement

    mock_response = [{"tx_date": "2026-03-04", "amount": "not-a-number"}]

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(mock_response))]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("app.services.llm._get_client", return_value=mock_client):
        with pytest.raises(ValueError, match="Missing required field"):
            await parse_bank_statement("some bank statement text")


# ---------------------------------------------------------------------------
# Matching tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_match_single_invoice():
    """Test single-invoice matching with mocked Claude API."""
    from app.services.llm import match_single_invoice

    inv_id = str(uuid.uuid4())
    tx_id = str(uuid.uuid4())

    mock_response = [
        {
            "transaction_id": tx_id,
            "confidence": 0.97,
            "rationale": "Amount matches exactly. Vendor name matches.",
        }
    ]

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(mock_response))]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    invoice = {"id": inv_id, "vendor": "Vercel", "amount_incl": "49.00", "currency": "EUR", "invoice_date": "2026-03-01"}
    transactions = [{"id": tx_id, "tx_date": "2026-03-04", "amount": "-49.00", "counterparty": "Vercel Inc", "description": "VERCEL INC SUBSCRIPTION"}]

    with patch("app.services.llm._get_client", return_value=mock_client):
        result = await match_single_invoice(invoice, transactions)

    assert result is not None
    assert result["invoice_id"] == uuid.UUID(inv_id)
    assert result["transaction_id"] == uuid.UUID(tx_id)
    assert result["confidence"] == Decimal("0.97")
    assert "matches" in result["rationale"].lower()


@pytest.mark.asyncio
async def test_match_single_invoice_no_match():
    """LLM returns empty array → None."""
    from app.services.llm import match_single_invoice

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="[]")]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    invoice = {"id": str(uuid.uuid4()), "vendor": "Vercel", "amount_incl": "49.00", "currency": "EUR", "invoice_date": "2026-03-01"}
    transactions = [{"id": str(uuid.uuid4()), "tx_date": "2026-03-04", "amount": "-10.00", "counterparty": "Hetzner", "description": "HETZNER CLOUD"}]

    with patch("app.services.llm._get_client", return_value=mock_client):
        result = await match_single_invoice(invoice, transactions)

    assert result is None


@pytest.mark.asyncio
async def test_match_single_invoice_empty_transactions():
    """Empty transaction list returns None without calling LLM."""
    from app.services.llm import match_single_invoice

    invoice = {"id": str(uuid.uuid4()), "vendor": "Vercel", "amount_incl": "49.00"}
    result = await match_single_invoice(invoice, [])
    assert result is None
