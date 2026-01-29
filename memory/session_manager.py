"""
Session manager facade: auto-detect Redis, fall back to in-memory.

Uses Redis when available (production); otherwise uses InMemorySessionManager.
Exposes backward-compatible function API: load_session, save_session, delete_session, get_all_sessions.
"""

import os
import logging
from typing import Dict

from memory.schemas import SessionMemory
from memory.in_memory_session_manager import InMemorySessionManager

logger = logging.getLogger(__name__)

# Lazy singleton backend (Redis or InMemory)
_backend = None


def _get_backend():
    """Create or return the session backend. Tries Redis first, then in-memory."""
    global _backend
    if _backend is not None:
        return _backend

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        from memory.redis_session_manager import RedisSessionManager
        _backend = RedisSessionManager(
            redis_url=redis_url,
            max_sessions=int(os.getenv("REDIS_MAX_SESSIONS", "10000")),
            session_ttl_seconds=int(os.getenv("REDIS_SESSION_TTL", "3600")),
        )
        logger.info("Session manager using Redis: %s", redis_url)
    except Exception as e:
        logger.warning("Redis unavailable (%s), using in-memory session manager.", e)
        _backend = InMemorySessionManager()

    return _backend


def load_session(session_id: str) -> SessionMemory:
    """
    Load existing session or create new one.
    Backward-compatible with previous module API.
    """
    return _get_backend().load_session(session_id, create_if_missing=True)


def save_session(session_id: str, session: SessionMemory) -> None:
    """Save session to storage."""
    _get_backend().save_session(session_id, session, update_metrics=True)


def delete_session(session_id: str) -> None:
    """Remove session after completion."""
    _get_backend().delete_session(session_id)


def get_all_sessions() -> Dict[str, SessionMemory]:
    """Return all active sessions (for debugging)."""
    return _get_backend().get_all_sessions()
