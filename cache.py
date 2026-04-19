"""
cache.py — Simple Redis cache wrapper.

Why cache?
The LLM calls get_events() multiple times per ReAct loop.
Without cache we'd burn Google API quota very fast.

Usage:
    from cache import cache_get, cache_set, cache_delete

    # Store JSON-serializable value
    cache_set("events:user123:7d", events_list, ttl=300)

    # Retrieve — returns None on miss
    cached = cache_get("events:user123:7d")
"""

import json
from typing import Any, Optional

import redis
import structlog

from config import settings

log = structlog.get_logger(__name__)

# One global connection pool — thread safe
_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        log.info("redis_connected", url=settings.redis_url)
    return _redis_client


def cache_get(key: str) -> Optional[Any]:
    """Return cached value or None if not found / Redis is down."""
    try:
        raw = get_redis().get(key)
        if raw is None:
            log.debug("cache_miss", key=key)
            return None
        log.debug("cache_hit", key=key)
        return json.loads(raw)
    except Exception as e:
        # Never crash the app because Redis is down — just bypass cache
        log.warning("cache_get_error", key=key, error=str(e))
        return None


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """Store value as JSON with optional TTL in seconds."""
    try:
        ttl = ttl or settings.cache_ttl_seconds
        get_redis().setex(key, ttl, json.dumps(value))
        log.debug("cache_set", key=key, ttl=ttl)
    except Exception as e:
        log.warning("cache_set_error", key=key, error=str(e))


def cache_delete(key: str) -> None:
    """Invalidate a cache key (call after create/update/delete operations)."""
    try:
        get_redis().delete(key)
        log.debug("cache_deleted", key=key)
    except Exception as e:
        log.warning("cache_delete_error", key=key, error=str(e))


def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a pattern e.g. 'events:user123:*'"""
    try:
        keys = get_redis().keys(pattern)
        if keys:
            get_redis().delete(*keys)
            log.info("cache_pattern_deleted", pattern=pattern, count=len(keys))
    except Exception as e:
        log.warning("cache_pattern_delete_error", pattern=pattern, error=str(e))


# ─── Session State & Queue Helpers ──────────────────────────────────────────

def set_last_action(session_id: str, action: dict) -> None:
    """Store the last successful write action for undo operations."""
    cache_set(f"last_action:{session_id}", action, ttl=86400) # 24h


def get_last_action(session_id: str) -> Optional[dict]:
    return cache_get(f"last_action:{session_id}")


def queue_pending_email(queue_id: str, email_data: dict, ttl: int = 600) -> None:
    """Store an email in the pending queue."""
    cache_set(f"pending_email:{queue_id}", email_data, ttl=ttl)


def list_pending_emails() -> list[dict]:
    """Retrieve all pending emails from the queue."""
    try:
        keys = get_redis().keys("pending_email:*")
        emails = []
        for k in keys:
            val = cache_get(k)
            if val:
                emails.append(val)
        return emails
    except Exception:
        return []


def remove_pending_email(queue_id: str) -> None:
    cache_delete(f"pending_email:{queue_id}")


def update_pending_email(queue_id: str, **updates) -> bool:
    """Update specific fields of a pending email while keeping its send time."""
    data = cache_get(f"pending_email:{queue_id}")
    if not data:
        return False
    
    data.update(updates)
    # Re-store with current TTL
    ttl = get_redis().ttl(f"pending_email:{queue_id}")
    if ttl <= 0: ttl = 600
    cache_set(f"pending_email:{queue_id}", data, ttl=ttl)
    return True