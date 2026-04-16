import io
from typing import Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from app.config import settings

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def _get_drive_service() -> Any:
    """Build an authenticated Google Drive API service."""
    creds = Credentials(
        token=None,
        refresh_token=settings.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("drive", "v3", credentials=creds)


async def ensure_folder(
    parent_id: str, folder_name: str
) -> str:
    """Get or create a subfolder under parent_id. Returns the folder ID."""
    service = _get_drive_service()

    query = (
        f"'{parent_id}' in parents "
        f"and name = '{folder_name}' "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


async def upload_pdf(
    pdf_bytes: bytes,
    filename: str,
    year: str,
    month: str,
) -> dict[str, str]:
    """Upload a PDF to /Invoices/YYYY/Month/ and return file_id + web_url."""
    root_folder_id = settings.drive_invoices_folder_id
    year_folder_id = await ensure_folder(root_folder_id, year)
    month_folder_id = await ensure_folder(year_folder_id, month)

    service = _get_drive_service()

    metadata = {
        "name": filename,
        "parents": [month_folder_id],
    }
    media = MediaIoBaseUpload(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
    )
    file = (
        service.files()
        .create(body=metadata, media_body=media, fields="id,webViewLink")
        .execute()
    )

    return {
        "file_id": file["id"],
        "url": file["webViewLink"],
    }


async def copy_file_to_folder(
    file_id: str,
    folder_id: str,
    new_name: str | None = None,
) -> dict[str, str]:
    """Copy a file into a folder. Returns the new file's id + web link."""
    service = _get_drive_service()

    body: dict[str, Any] = {"parents": [folder_id]}
    if new_name:
        body["name"] = new_name

    copied = (
        service.files()
        .copy(fileId=file_id, body=body, fields="id,webViewLink")
        .execute()
    )
    return {
        "file_id": copied["id"],
        "url": copied["webViewLink"],
    }


async def create_period_summary_folder(
    period: str,
    invoice_file_ids: list[dict[str, str]],
) -> str:
    """Create a <period>-summary folder and copy invoice PDFs into it.

    invoice_file_ids: list of {"drive_file_id": ..., "filename": ...}
    Returns the web URL of the created folder.
    """
    root_folder_id = settings.drive_invoices_folder_id
    monthly_summaries_id = await ensure_folder(root_folder_id, "Monthly summaries")
    summary_folder_id = await ensure_folder(monthly_summaries_id, period)

    # List existing files in the summary folder to avoid duplicates
    service = _get_drive_service()
    existing = service.files().list(
        q=f"'{summary_folder_id}' in parents and trashed = false",
        fields="files(name)",
    ).execute()
    existing_names = {f["name"] for f in existing.get("files", [])}

    copied = 0
    for item in invoice_file_ids:
        file_id = item["drive_file_id"]
        filename = item["filename"]
        if filename in existing_names:
            continue
        await copy_file_to_folder(file_id, summary_folder_id, filename)
        copied += 1

    # Get folder web link
    folder_meta = service.files().get(
        fileId=summary_folder_id, fields="webViewLink"
    ).execute()

    return folder_meta["webViewLink"]


async def upload_report(
    file_bytes: bytes,
    filename: str,
    month: str,
    mimetype: str = "application/pdf",
) -> dict[str, str]:
    """Upload a report to /Reports/<Month>/ and return file_id + web_url."""
    root_folder_id = settings.drive_invoices_folder_id
    reports_folder_id = await ensure_folder(root_folder_id, "Reports")
    month_folder_id = await ensure_folder(reports_folder_id, month)

    service = _get_drive_service()

    metadata = {
        "name": filename,
        "parents": [month_folder_id],
    }
    media = MediaIoBaseUpload(
        io.BytesIO(file_bytes),
        mimetype=mimetype,
    )
    file = (
        service.files()
        .create(body=metadata, media_body=media, fields="id,webViewLink")
        .execute()
    )

    return {
        "file_id": file["id"],
        "url": file["webViewLink"],
    }
