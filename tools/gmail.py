"""
tools/gmail.py — Gmail MCP tool implementations with delayed sending support.
"""

import base64
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import structlog
from googleapiclient.errors import HttpError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from cache import queue_pending_email, list_pending_emails, remove_pending_email, update_pending_email
from models import EmailResult, ReplyStatus, PendingEmail
from tools.auth import get_gmail_service

log = structlog.get_logger(__name__)


# ─── Retry decorator — same pattern as events.py ─────────────────────────────

def google_retry(func):
    return retry(
        retry=retry_if_exception_type(HttpError),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )(func)


# ─── Internal Send Logic ──────────────────────────────────────────────────────

def _do_send_email(
    to: list[str],
    subject: str,
    body: str,
    thread_id: str | None = None,
) -> dict:
    """Internal function that performs the actual Gmail API call."""
    service = get_gmail_service()

    mime = MIMEText(body, "plain")
    mime["to"] = ", ".join(to)
    mime["subject"] = subject

    raw_bytes = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    message_body: dict = {"raw": raw_bytes}
    if thread_id:
        message_body["threadId"] = thread_id

    @google_retry
    def _call():
        return (
            service.users()
            .messages()
            .send(userId="me", body=message_body)
            .execute()
        )

    result = _call()
    sent_at = datetime.now(timezone.utc).isoformat()
    
    return {
        "message_id": result["id"],
        "thread_id": result["threadId"],
        "sent_at": sent_at,
    }


# ─── Tool implementations ──────────────────────────────────────────────────────

def send_email(
    to: list[str],
    subject: str,
    body: str,
    thread_id: str | None = None,
) -> dict | str:
    """
    Queue an email to be sent via Gmail API after a delay.
    Returns the queue status.
    """
    try:
        delay_min = settings.email_delay_minutes
        
        if delay_min <= 0:
            # Send immediately if no delay configured
            result = _do_send_email(to, subject, body, thread_id)
            return EmailResult(**result).model_dump()

        # Generate a unique queue ID
        queue_id = str(uuid.uuid4())
        scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=delay_min)
        
        pending = PendingEmail(
            queue_id=queue_id,
            to=to,
            subject=subject,
            body=body,
            thread_id=thread_id,
            scheduled_send_at=scheduled_at.isoformat()
        )
        
        # Store in Redis queue
        queue_pending_email(queue_id, pending.model_dump(), ttl=delay_min * 60 + 300)
        
        log.info(
            "email_queued",
            queue_id=queue_id,
            scheduled_at=pending.scheduled_send_at,
            to=to
        )
        
        return {
            "status": "QUEUED",
            "queue_id": queue_id,
            "scheduled_send_at": pending.scheduled_send_at,
            "message": f"Email queued successfully. It will be sent in {delay_min} minutes. You can undo this by saying 'undo'."
        }

    except Exception as e:
        log.error("send_email_queue_failed", error=str(e))
        return f"Error queuing email: {str(e)}"


def check_reply_status(thread_id: str, sent_at: str) -> dict | str:
    """Check if anyone replied to a thread."""
    try:
        service = get_gmail_service()
        log.info("checking_reply_status", thread_id=thread_id)

        @google_retry
        def _call():
            return (
                service.users()
                .threads()
                .get(userId="me", id=thread_id, format="metadata")
                .execute()
            )

        thread = _call()
        messages = thread.get("messages", [])
        reply_count = max(0, len(messages) - 1)
        has_reply = reply_count > 0

        last_reply_at = None
        if has_reply:
            last_msg = messages[-1]
            internal_date_ms = int(last_msg.get("internalDate", 0))
            if internal_date_ms:
                last_reply_dt = datetime.fromtimestamp(
                    internal_date_ms / 1000, tz=timezone.utc
                )
                last_reply_at = last_reply_dt.isoformat()

        sent_dt = datetime.fromisoformat(sent_at)
        overdue_threshold = sent_dt + timedelta(hours=24)
        is_overdue = not has_reply and datetime.now(timezone.utc) > overdue_threshold

        status = ReplyStatus(
            thread_id=thread_id,
            has_reply=has_reply,
            reply_count=reply_count,
            last_reply_at=last_reply_at,
            is_overdue=is_overdue,
        )

        return status.model_dump()
    except Exception as e:
        log.error("check_reply_status_failed", error=str(e))
        return f"Error checking reply status: {str(e)}"


def update_pending_email_tool(
    queue_id: str,
    to: list[str] | None = None,
    subject: str | None = None,
    body: str | None = None,
) -> str:
    """Update fields of an unsent email while it is still in the queue."""
    updates = {}
    if to is not None: updates["to"] = to
    if subject is not None: updates["subject"] = subject
    if body is not None: updates["body"] = body
    
    if not updates:
        return "No updates provided."

    success = update_pending_email(queue_id, **updates)
    if success:
        return f"Successfully updated pending email {queue_id}. The changes will be applied when it sends."
    else:
        return f"Could not update email. It may have already been sent or the ID {queue_id} is invalid."


# ─── Background Processor ─────────────────────────────────────────────────────

async def process_pending_emails():
    """
    Periodically called to process the email queue.
    Checks for emails whose scheduled_send_at has passed.
    """
    pending_list = list_pending_emails()
    if not pending_list:
        return

    now = datetime.now(timezone.utc)
    for p_dict in pending_list:
        try:
            p = PendingEmail(**p_dict)
            scheduled_at = datetime.fromisoformat(p.scheduled_send_at)
            
            if now >= scheduled_at:
                log.info("processing_delayed_email", queue_id=p.queue_id)
                # Perform actual send
                _do_send_email(
                    to=p.to,
                    subject=p.subject,
                    body=p.body,
                    thread_id=p.thread_id
                )
                # Remove from queue
                remove_pending_email(p.queue_id)
                log.info("delayed_email_sent_successfully", queue_id=p.queue_id)
        except Exception as e:
            log.error("failed_to_process_pending_email", queue_id=p_dict.get('queue_id'), error=str(e))