"""Session memory: schemas, Redis/in-memory backends, and facade."""

from memory.schemas import SessionMemory
from memory.session_manager import (
    load_session,
    save_session,
    delete_session,
    get_all_sessions,
)
from memory.in_memory_session_manager import InMemorySessionManager

__all__ = [
    "SessionMemory",
    "load_session",
    "save_session",
    "delete_session",
    "get_all_sessions",
    "InMemorySessionManager",
]

try:
    from memory.redis_session_manager import RedisSessionManager
    __all__.append("RedisSessionManager")
except ImportError:
    pass
