"""
tools/undo.py — Logic to revert the last successful calendar/email action.
"""

import structlog
from typing import Any

from cache import get_last_action, remove_pending_email
from tools.events import delete_event
from config import settings

log = structlog.get_logger(__name__)


def undo_last_action(confirm: bool = True) -> str:
    """
    Revert the most recent high-level action (e.g., delete a created meeting 
    or cancel a pending email before it sends).
    """
    if not confirm:
        return "Undo cancelled."

    # In this implementation, we use a single global session ID 'session_1'
    # matching what is used in agent.py
    session_id = "session_1"
    
    last_action = get_last_action(session_id)
    if not last_action:
        return "Nothing to undo — no recent actions found in this session."

    action_type = last_action.get("action_type")
    action_id = last_action.get("action_id")
    
    log.info("undoing_action", type=action_type, id=action_id)

    try:
        if action_type == "create_event":
            # Revert calendar event creation by deleting it
            result = delete_event(event_id=action_id)
            if isinstance(result, str) and "Error" in result:
                return f"Failed to undo meeting creation: {result}"
            return f"Successfully reverted: The meeting (ID: {action_id}) has been removed from your calendar."

        elif action_type == "send_email":
            # Revert queued email by removing it from Redis
            # In our current logic, action_id for email is the queue_id
            remove_pending_email(queue_id=action_id)
            return "Successfully reverted: The pending email has been cancelled and will not be sent."

        elif action_type == "delete_event":
            # Reverting a delete is harder (requires restoring), so we just inform the user
            return f"Cannot automatically undo a deletion. The event {action_id} was already removed from Google."

        else:
            return f"Undo is not supported for action type: {action_type}"

    except Exception as e:
        log.error("undo_failed", error=str(e))
        return f"Error during undo: {str(e)}"
