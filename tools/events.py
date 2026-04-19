"""
tools/events.py — Google Calendar MCP tool implementations.

Each function is a standalone, testable unit.
The @mcp.tool() decorators are applied in server.py.

    - get_events(days, calendar_id)
    - create_event(title, start, end, attendees, description)
    - update_event(event_id, ...)
    - delete_event(event_id)
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Any

import structlog
from googleapiclient.errors import HttpError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from cache import cache_delete_pattern, cache_get, cache_set
from models import (
    CalendarEvent,
)
from tools.auth import get_calendar_service

log = structlog.get_logger(__name__)


# ─── Retry decorator — handles Google's 429 / 503 ─────────────────────────────

def google_retry(func):
    """Wrap any Google API call with exponential backoff retry."""
    return retry(
        retry=retry_if_exception_type(HttpError),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )(func)


# ─── Tool implementations ──────────────────────────────────────────────────────

def get_events(days: int = 7, calendar_id: str = "primary") -> list[dict] | str:
    """
    Fetch upcoming calendar events for the next N days.
    Results are cached for 5 minutes.

    Returns a list of CalendarEvent dicts or an error string.
    """
    try:
        cache_key = f"events:{calendar_id}:{days}d"
        cached = cache_get(cache_key)
        if cached:
            return cached

        service = get_calendar_service()

        now = datetime.now(timezone.utc)
        time_max = now + timedelta(days=days)

        log.info("fetching_events", days=days, calendar_id=calendar_id)

        @google_retry
        def _call():
            return (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=now.isoformat(),
                    timeMax=time_max.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=50,
                )
                .execute()
            )

        response = _call()
        items = response.get("items", [])

        events = []
        for item in items:
            start = item.get("start", {})
            end = item.get("end", {})
            event = CalendarEvent(
                event_id=item["id"],
                title=item.get("summary", "No Title"),
                start=start.get("dateTime", start.get("date", "")),
                end=end.get("dateTime", end.get("date", "")),
                attendees=[
                    a["email"] for a in item.get("attendees", [])
                ],
                description=item.get("description", ""),
                html_link=item.get("htmlLink", ""),
            )
            events.append(event.model_dump())

        cache_set(cache_key, events)
        log.info("events_fetched", count=len(events))
        return events
    except Exception as e:
        log.error("get_events_failed", error=str(e))
        return f"Error fetching events: {str(e)}"


def create_event(
    title: str,
    start_datetime: str,
    end_datetime: str,
    attendees: list[str],
    description: str = "",
    send_invites: bool = True,
) -> dict | str:
    """
    Create a Google Calendar event and optionally send invites.

    Returns the created CalendarEvent dict with the new event_id or an error string.
    """
    try:
        service = get_calendar_service()

        event_body = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_datetime},
            "end": {"dateTime": end_datetime},
            "attendees": [{"email": email} for email in attendees],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 1440},  # 24h before
                    {"method": "popup", "minutes": 15},
                ],
            },
        }

        send_updates = "all" if send_invites else "none"
        log.info("creating_event", title=title, attendees=attendees)

        @google_retry
        def _call():
            return (
                service.events()
                .insert(
                    calendarId="primary",
                    body=event_body,
                    sendUpdates=send_updates,
                )
                .execute()
            )

        created = _call()

        # Invalidate cached events so next fetch is fresh
        cache_delete_pattern("events:*")

        result = CalendarEvent(
            event_id=created["id"],
            title=created.get("summary", title),
            start=created["start"]["dateTime"],
            end=created["end"]["dateTime"],
            attendees=[a["email"] for a in created.get("attendees", [])],
            description=created.get("description", ""),
            html_link=created.get("htmlLink", ""),
        )

        log.info("event_created", event_id=result.event_id, title=title)
        return result.model_dump()
    except Exception as e:
        log.error("create_event_failed", error=str(e))
        return f"Error creating event: {str(e)}"


def update_event(
    event_id: str,
    title: str | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    description: str | None = None,
    attendees: list[str] | None = None,
) -> dict | str:
    """
    Patch (partial update) an existing calendar event.
    Only fields you pass will be changed.
    """
    try:
        service = get_calendar_service()

        # Build only the fields we want to update
        patch_body: dict[str, Any] = {}
        if title:
            patch_body["summary"] = title
        if description is not None:
            patch_body["description"] = description
        if start_datetime:
            patch_body["start"] = {"dateTime": start_datetime}
        if end_datetime:
            patch_body["end"] = {"dateTime": end_datetime}
        if attendees is not None:
            patch_body["attendees"] = [{"email": email} for email in attendees]

        log.info("updating_event", event_id=event_id, fields=list(patch_body.keys()))

        @google_retry
        def _call():
            return (
                service.events()
                .patch(
                    calendarId="primary",
                    eventId=event_id,
                    body=patch_body,
                    sendUpdates="all",
                )
                .execute()
            )

        updated = _call()
        cache_delete_pattern("events:*")

        log.info("event_updated", event_id=event_id)
        return {
            "event_id": updated["id"],
            "title": updated.get("summary", ""),
            "start": updated["start"].get("dateTime", ""),
            "end": updated["end"].get("dateTime", ""),
            "html_link": updated.get("htmlLink", ""),
        }
    except Exception as e:
        log.error("update_event_failed", error=str(e))
        return f"Error updating event: {str(e)}"


def delete_event(event_id: str) -> dict | str:
    """
    Cancel and delete a calendar event.
    Google sends cancellation emails to attendees.
    """
    try:
        service = get_calendar_service()
        log.info("deleting_event", event_id=event_id)

        @google_retry
        def _call():
            service.events().delete(
                calendarId="primary",
                eventId=event_id,
                sendUpdates="all",
            ).execute()

        _call()
        cache_delete_pattern("events:*")

        log.info("event_deleted", event_id=event_id)
        return {"success": True, "event_id": event_id}
    except Exception as e:
        log.error("delete_event_failed", error=str(e))
        return f"Error deleting event: {str(e)}"