"""Gmail API service — OAuth setup, on-demand fetch of emails with PDF attachments."""

import base64
from dataclasses import dataclass
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


@dataclass
class EmailAttachment:
    filename: str
    data: bytes
    message_id: str
    subject: str
    sender: str


def _get_gmail_service() -> Any:
    """Build an authenticated Gmail API service."""
    creds = Credentials(
        token=None,
        refresh_token=settings.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


async def fetch_unread_invoices() -> list[EmailAttachment]:
    """Fetch all unread emails with PDF attachments from Gmail inbox.

    This is an on-demand trigger — no cron.
    """
    service = _get_gmail_service()

    results = (
        service.users()
        .messages()
        .list(userId="me", q="is:unread has:attachment filename:pdf")
        .execute()
    )

    messages = results.get("messages", [])
    attachments: list[EmailAttachment] = []

    for msg_ref in messages:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=msg_ref["id"])
            .execute()
        )

        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        subject = headers.get("Subject", "")
        sender = headers.get("From", "")

        parts = msg["payload"].get("parts", [])
        for part in parts:
            filename = part.get("filename", "")
            if not filename.lower().endswith(".pdf"):
                continue

            attachment_id = part["body"].get("attachmentId")
            if not attachment_id:
                continue

            att = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=msg_ref["id"], id=attachment_id)
                .execute()
            )

            data = base64.urlsafe_b64decode(att["data"])
            attachments.append(
                EmailAttachment(
                    filename=filename,
                    data=data,
                    message_id=msg_ref["id"],
                    subject=subject,
                    sender=sender,
                )
            )

    # Mark processed emails as read so they aren't fetched again
    for msg_ref in messages:
        service.users().messages().modify(
            userId="me",
            id=msg_ref["id"],
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()

    return attachments
