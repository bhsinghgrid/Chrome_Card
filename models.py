"""
models.py — Pydantic v2 schemas for every tool's input and output.

Why separate models?
- LangChain uses these for input validation before calling the tool.
- FastMCP auto-generates JSON schema from these for the LLM to see.
- Makes unit testing super easy — just construct the model.
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ─── Calendar tool inputs ──────────────────────────────────────────────────────

class GetEventsInput(BaseModel):
    days: int = Field(default=7, ge=1, le=90, description="How many days ahead to fetch")
    calendar_id: str = Field(default="primary", description="Google calendar ID")


class CheckFreeSlotsInput(BaseModel):
    attendees: list[str] = Field(..., description="List of attendee email addresses")
    duration_minutes: int = Field(..., ge=15, le=480, description="Meeting length in minutes")
    days_ahead: int = Field(default=7, ge=1, le=30, description="How many days to search")
    working_hours_start: int = Field(default=9, description="Working hours start (24h)")
    working_hours_end: int = Field(default=18, description="Working hours end (24h)")
    timezone: str = Field(default="Asia/Kolkata", description="IANA timezone string")


class CreateEventInput(BaseModel):
    title: str = Field(..., description="Meeting title")
    start_datetime: str = Field(..., description="ISO 8601 datetime e.g. 2025-04-20T14:00:00+05:30")
    end_datetime: str = Field(..., description="ISO 8601 datetime e.g. 2025-04-20T15:00:00+05:30")
    attendees: list[str] = Field(..., description="List of attendee email addresses")
    description: str = Field(default="", description="Meeting description / agenda")
    send_invites: bool = Field(default=True, description="Send Google Calendar invites to attendees")


class UpdateEventInput(BaseModel):
    event_id: str = Field(..., description="Google Calendar event ID")
    title: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    description: Optional[str] = None
    attendees: Optional[list[str]] = Field(default=None, description="New list of attendee emails")


class DeleteEventInput(BaseModel):
    event_id: str = Field(..., description="Google Calendar event ID to delete")


# ─── Gmail tool inputs ─────────────────────────────────────────────────────────

class SendEmailInput(BaseModel):
    to: list[str] = Field(..., description="Recipient email addresses")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Plain text email body")
    thread_id: Optional[str] = Field(default=None, description="Thread ID to reply into")


class CheckReplyInput(BaseModel):
    thread_id: str = Field(..., description="Gmail thread ID to check for replies")
    sent_at: str = Field(..., description="ISO datetime when the original email was sent")


class UpdatePendingEmailInput(BaseModel):
    queue_id: str = Field(..., description="The queue ID of the pending email")
    to: Optional[list[str]] = Field(default=None, description="New list of recipients")
    subject: Optional[str] = Field(default=None, description="New subject")
    body: Optional[str] = Field(default=None, description="New email body")


class UndoInput(BaseModel):
    confirm: bool = Field(default=True, description="Confirm you want to revert the last action")


# ─── Tool outputs ──────────────────────────────────────────────────────────────

class CalendarEvent(BaseModel):
    event_id: str
    title: str
    start: str
    end: str
    attendees: list[str]
    description: str = ""
    html_link: str = ""


class FreeSlot(BaseModel):
    start: str
    end: str
    duration_minutes: int


class EmailResult(BaseModel):
    message_id: str
    thread_id: str
    sent_at: str


class ReplyStatus(BaseModel):
    thread_id: str
    has_reply: bool
    reply_count: int
    last_reply_at: Optional[str] = None
    is_overdue: bool = False  # True if no reply after 24h


class LastAction(BaseModel):
    action_type: str  # "create_event", "send_email", "delete_event"
    action_id: str    # event_id or thread_id
    payload: Optional[dict[str, Any]] = None


class PendingEmail(BaseModel):
    queue_id: str
    to: list[str]
    subject: str
    body: str
    thread_id: Optional[str] = None
    scheduled_send_at: str