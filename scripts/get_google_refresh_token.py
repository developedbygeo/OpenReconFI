"""One-time script to get a Google OAuth refresh token.

Usage:
    uv run python scripts/get_google_refresh_token.py

Prerequisites:
    1. Go to Google Cloud Console → APIs & Credentials
    2. Create an OAuth 2.0 Client ID (type: Desktop app)
    3. Enable Gmail API and Google Drive API
    4. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env

This will open a browser for consent, then print the refresh token.
Paste it into .env as GOOGLE_REFRESH_TOKEN.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_auth_oauthlib.flow import InstalledAppFlow

from app.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.file",
]


def main():
    if not settings.google_client_id or not settings.google_client_secret:
        print("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env first.")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        },
        scopes=SCOPES,
    )

    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    print("\n" + "=" * 60)
    print("GOOGLE_REFRESH_TOKEN=" + creds.refresh_token)
    print("=" * 60)
    print("\nPaste the line above into your .env file.")


if __name__ == "__main__":
    main()
