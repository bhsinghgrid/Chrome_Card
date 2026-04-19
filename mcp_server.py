"""
mcp_server.py — Pure MCP Tool Provider.

This file defines the Google Calendar and Gmail tools.
It is intended to be used:
1. As a standalone MCP server.
2. Imported by api_server.py to provide tools to the agent.
"""

from mcp.server.fastmcp import FastMCP

from tools.availability import check_free_slots, list_calendars
from tools.events import (
    create_event,
    delete_event,
    get_events,
    update_event,
)
from tools.gmail import check_reply_status, send_email, update_pending_email_tool
from tools.undo import undo_last_action

# ─── Create the MCP server ────────────────────────────────────────────────────

mcp = FastMCP(
    name="GoogleCalendarGmailMCP",
    instructions="""
    You are an autonomous calendar and email assistant.
    Use these tools to help users manage their schedule and communications.
    """,
)


# ─── Register Tools ───────────────────────────────────────────────────────────

@mcp.tool()
def tool_get_events(days: int = 7, calendar_id: str = "primary") -> list[dict]:
    """Fetch upcoming calendar events for the next N days."""
    return get_events(days=days, calendar_id=calendar_id)


@mcp.tool()
def tool_check_free_slots(
    attendees: list[str],
    duration_minutes: int,
    days_ahead: int = 7,
    working_hours_start: int = 9,
    working_hours_end: int = 18,
    timezone: str = "Asia/Kolkata",
) -> list[dict]:
    """Find time slots when ALL listed people are available."""
    return check_free_slots(
        attendees=attendees,
        duration_minutes=duration_minutes,
        days_ahead=days_ahead,
        working_hours_start=working_hours_start,
        working_hours_end=working_hours_end,
        timezone=timezone,
    )


@mcp.tool()
def tool_create_event(
    title: str,
    start_datetime: str,
    end_datetime: str,
    attendees: list[str],
    description: str = "",
    send_invites: bool = True,
) -> dict:
    """Create a Google Calendar event. Sends Google invites if send_invites=True."""
    return create_event(
        title=title,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        attendees=attendees,
        description=description,
        send_invites=send_invites,
    )


@mcp.tool()
def tool_update_event(
    event_id: str,
    title: str | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    description: str | None = None,
    attendees: list[str] | None = None,
) -> dict:
    """
    Update fields of an existing calendar event.
    Useful for removing people from a meeting by passing a new attendee list.
    """
    return update_event(
        event_id=event_id,
        title=title,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        description=description,
        attendees=attendees,
    )


@mcp.tool()
def tool_delete_event(event_id: str) -> dict:
    """Delete/cancel a calendar event."""
    return delete_event(event_id=event_id)


@mcp.tool()
def tool_list_calendars() -> list[dict]:
    """List all calendars the user has."""
    return list_calendars()


@mcp.tool()
def tool_send_email(
    to: list[str],
    subject: str,
    body: str,
    thread_id: str | None = None,
) -> dict:
    """Send an email via Gmail (with 5-minute delayed outbox support)."""
    return send_email(to=to, subject=subject, body=body, thread_id=thread_id)


@mcp.tool()
def tool_check_reply_status(thread_id: str, sent_at: str) -> dict:
    """Check if the recipient replied to an email thread."""
    return check_reply_status(thread_id=thread_id, sent_at=sent_at)


@mcp.tool()
def tool_update_pending_email(
    queue_id: str,
    to: list[str] | None = None,
    subject: str | None = None,
    body: str | None = None,
) -> str:
    """
    Update an email that is waiting in the 5-minute delayed outbox.
    Use this to remove a person from a group email before it is actually sent.
    """
    return update_pending_email_tool(queue_id=queue_id, to=to, subject=subject, body=body)


@mcp.tool()
def tool_undo_last_action(confirm: bool = True) -> str:
    """
    Revert the most recent high-level action (e.g., delete a meeting you just 
    created or cancel a pending email before the 5-minute window expires).
    """
    return undo_last_action(confirm=confirm)


if __name__ == "__main__":
    # If run directly, starts as a standard MCP server
    mcp.run()
