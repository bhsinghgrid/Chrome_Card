"""
tools/availability.py — Google Calendar availability and listing tools.

Each function is a standalone, testable unit.
The @mcp.tool() decorators are applied in server.py.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import structlog

from cache import cache_get, cache_set
from models import FreeSlot
from config import settings
from tools.auth import get_calendar_service
from tools.events import google_retry

log = structlog.get_logger(__name__)


def check_free_slots(
    attendees: list[str],
    duration_minutes: int,
    days_ahead: int = 7,
    working_hours_start: int = 9,
    working_hours_end: int = 18,
    timezone: str = settings.default_timezone,
) -> list[dict] | str:
    """
    Find time slots when ALL attendees are free.

    Uses Google Calendar FreeBusy API — the most efficient way
    to find availability without reading each person's calendar.

    Returns a list of FreeSlot dicts or an error string.
    """
    try:
        service = get_calendar_service()
        tz = ZoneInfo(timezone)

        now = datetime.now(tz)
        # Start from next 30-min boundary
        minutes_to_add = 30 - (now.minute % 30)
        search_start = now + timedelta(minutes=minutes_to_add)
        
        # FIX: Ensure search_end is always after search_start
        search_end = now + timedelta(days=max(1, days_ahead))
        if search_end <= search_start:
            search_end = search_start + timedelta(hours=24)

        log.info(
            "checking_free_slots",
            attendees=attendees,
            duration_minutes=duration_minutes,
            days_ahead=days_ahead,
            start=search_start.isoformat(),
            end=search_end.isoformat(),
        )

        @google_retry
        def _call():
            return (
                service.freebusy()
                .query(
                    body={
                        "timeMin": search_start.isoformat(),
                        "timeMax": search_end.isoformat(),
                        "timeZone": timezone,
                        "items": [{"id": email} for email in attendees],
                    }
                )
                .execute()
            )

        response = _call()
        calendars = response.get("calendars", {})

        # Collect all busy periods across all attendees
        all_busy: list[tuple[datetime, datetime]] = []
        for email in attendees:
            busy_list = calendars.get(email, {}).get("busy", [])
            for period in busy_list:
                start = datetime.fromisoformat(period["start"]).astimezone(tz)
                end = datetime.fromisoformat(period["end"]).astimezone(tz)
                all_busy.append((start, end))

        # Sort busy periods
        all_busy.sort(key=lambda x: x[0])

        # Walk through each day and find free windows
        free_slots: list[dict] = []
        current = search_start

        while current < search_end and len(free_slots) < 10:
            # Skip to working hours start
            day_start = current.replace(
                hour=working_hours_start, minute=0, second=0, microsecond=0
            )
            day_end = current.replace(
                hour=working_hours_end, minute=0, second=0, microsecond=0
            )

            # Don't go backwards
            window_start = max(current, day_start)

            while window_start + timedelta(minutes=duration_minutes) <= day_end:
                window_end = window_start + timedelta(minutes=duration_minutes)

                # Check if this slot overlaps with any busy period
                conflict = any(
                    not (window_end <= busy_start or window_start >= busy_end)
                    for busy_start, busy_end in all_busy
                )

                if not conflict:
                    slot = FreeSlot(
                        start=window_start.isoformat(),
                        end=window_end.isoformat(),
                        duration_minutes=duration_minutes,
                    )
                    free_slots.append(slot.model_dump())
                    # Jump to after this slot to avoid overlapping suggestions
                    window_start = window_end
                else:
                    # Move to next 30-min boundary
                    window_start += timedelta(minutes=30)

            # Move to next day
            current = (current + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        log.info("free_slots_found", count=len(free_slots))
        return free_slots
    except Exception as e:
        log.error("check_free_slots_failed", error=str(e))
        return f"Error checking free slots: {str(e)}"


def list_calendars() -> list[dict]:
    """
    List all calendars the user has access to.
    Cached for 10 minutes — this rarely changes.
    """
    cache_key = "calendars:list"
    cached = cache_get(cache_key)
    if cached:
        return cached

    service = get_calendar_service()

    @google_retry
    def _call():
        return service.calendarList().list().execute()

    response = _call()
    items = response.get("items", [])

    calendars = [
        {
            "id": item["id"],
            "name": item.get("summary", ""),
            "description": item.get("description", ""),
            "timezone": item.get("timeZone", ""),
            "primary": item.get("primary", False),
        }
        for item in items
    ]

    cache_set(cache_key, calendars, ttl=600)
    log.info("calendars_listed", count=len(calendars))
    return calendars
