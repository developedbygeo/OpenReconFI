"""Tests for Gmail service — mocked Google API calls."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from app.services.gmail import EmailAttachment, fetch_unread_invoices


@pytest.mark.asyncio
async def test_fetch_unread_invoices_empty():
    """Test when no unread messages with PDF attachments."""
    mock_service = MagicMock()
    mock_service.users().messages().list().execute.return_value = {"messages": []}

    with patch("app.services.gmail._get_gmail_service", return_value=mock_service):
        result = await fetch_unread_invoices()

    assert result == []


@pytest.mark.asyncio
async def test_fetch_unread_invoices_with_attachment():
    """Test fetching an email with a PDF attachment."""
    pdf_content = b"fake-pdf-content"
    encoded = base64.urlsafe_b64encode(pdf_content).decode()

    mock_service = MagicMock()

    # List returns one message
    mock_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "msg-123"}]
    }

    # Get message details
    mock_service.users().messages().get().execute.return_value = {
        "payload": {
            "headers": [
                {"name": "Subject", "value": "March Invoice"},
                {"name": "From", "value": "billing@vercel.com"},
            ],
            "parts": [
                {
                    "filename": "invoice.pdf",
                    "body": {"attachmentId": "att-456"},
                }
            ],
        }
    }

    # Get attachment data
    mock_service.users().messages().attachments().get().execute.return_value = {
        "data": encoded
    }

    with patch("app.services.gmail._get_gmail_service", return_value=mock_service):
        result = await fetch_unread_invoices()

    assert len(result) == 1
    assert isinstance(result[0], EmailAttachment)
    assert result[0].filename == "invoice.pdf"
    assert result[0].data == pdf_content
    assert result[0].subject == "March Invoice"
    assert result[0].sender == "billing@vercel.com"
