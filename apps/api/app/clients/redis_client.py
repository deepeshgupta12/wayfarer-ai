"""
Lazy-initialised Redis client.

The connection is only established on the first actual use, so the API can
start up even when Redis is unavailable (it will degrade gracefully).
"""
import json
import logging
from typing import Any

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def _get_client() -> redis.Redis | None:
    """Return the shared Redis client, initialising it on first call."""
    global _redis_client  # noqa: PLW0603
    if _redis_client is None:
        try:
            settings = get_settings()
            _redis_client = redis.Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("Redis client initialisation failed: %s", exc)
    return _redis_client


def check_redis_connection() -> bool:
    client = _get_client()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Generic cache helpers (JSON-serialisable values only)
# ---------------------------------------------------------------------------

def cache_get(key: str) -> Any | None:
    """Return the cached value for *key*, or None on miss/error."""
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception as exc:
        logger.debug("Redis cache_get failed for key=%s: %s", key, exc)
        return None


def cache_set(key: str, value: Any, ttl_seconds: int = 900) -> bool:
    """Store *value* under *key* with the given TTL. Returns True on success."""
    client = _get_client()
    if client is None:
        return False
    try:
        client.setex(key, ttl_seconds, json.dumps(value))
        return True
    except Exception as exc:
        logger.debug("Redis cache_set failed for key=%s: %s", key, exc)
        return False


def cache_delete(key: str) -> bool:
    """Remove *key* from the cache. Returns True if the key existed."""
    client = _get_client()
    if client is None:
        return False
    try:
        return bool(client.delete(key))
    except Exception as exc:
        logger.debug("Redis cache_delete failed for key=%s: %s", key, exc)
        return False
