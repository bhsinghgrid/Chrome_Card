"""
tools/auth.py — Google OAuth 2.0 credential management.

Handles:
- First-time OAuth flow (opens browser, saves token.json)
- Automatic token refresh when access token expires
- Building the Google API service clients

Usage:
    from tools.auth import get_calendar_service, get_gmail_service
    service = get_calendar_service()
"""

import json
import os
from pathlib import Path

import structlog
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import settings

log = structlog.get_logger(__name__)


def _load_or_refresh_credentials() -> Credentials:
    """
    Load credentials from token.json.
    If expired, refresh automatically.
    If missing, run the OAuth browser flow.
    """
    creds = None
    token_path = Path(settings.token_path)

    # Load existing token if it exists
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(
            str(token_path), settings.google_scopes
        )
        log.info("credentials_loaded", token_path=str(token_path))

    # Refresh or re-authorize
    if creds and creds.expired and creds.refresh_token:
        log.info("refreshing_access_token")
        creds.refresh(Request())
        _save_credentials(creds)

    elif not creds or not creds.valid:
        log.info("starting_oauth_flow")
        creds = _run_oauth_flow()

    return creds


def _run_oauth_flow() -> Credentials:
    """
    Opens a browser for the user to authorize the app.
    Only runs once — token.json is saved afterwards.
    """
    # Build the client config dict from our settings
    client_config = {
        "installed": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uris": [settings.google_redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, settings.google_scopes)
    # run_local_server opens the browser and waits for the callback
    creds = flow.run_local_server(port=8080)
    _save_credentials(creds)
    log.info("oauth_flow_complete")
    return creds


def _save_credentials(creds: Credentials) -> None:
    """Save token to disk so we don't need to re-auth every run."""
    token_path = Path(settings.token_path)
    token_path.write_text(creds.to_json())
    log.info("credentials_saved", path=str(token_path))


def get_calendar_service():
    """
    Returns an authorized Google Calendar API v3 client.

    Usage:
        service = get_calendar_service()
        events = service.events().list(calendarId="primary").execute()
    """
    creds = _load_or_refresh_credentials()
    service = build("calendar", "v3", credentials=creds)
    log.info("calendar_service_built")
    return service


def get_gmail_service():
    """
    Returns an authorized Gmail API v1 client.

    Usage:
        service = get_gmail_service()
        result = service.users().messages().list(userId="me").execute()
    """
    creds = _load_or_refresh_credentials()
    service = build("gmail", "v1", credentials=creds)
    log.info("gmail_service_built")
    return service