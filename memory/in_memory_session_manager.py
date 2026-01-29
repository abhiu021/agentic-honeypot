"""
In-memory session storage (fallback when Redis is unavailable).
Use RedisSessionManager in production for persistence and thread-safety.
"""

from typing import Dict
from memory.schemas import SessionMemory
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class InMemorySessionManager:
    """
    In-memory session storage. Sessions are lost on process restart.
    Used as fallback when Redis is not available.
    """

    def __init__(self) -> None:
        """Initialize in-memory session store."""
        self._sessions: Dict[str, SessionMemory] = {}

    def load_session(
        self, session_id: str, create_if_missing: bool = True
    ) -> SessionMemory:
        """
        Load existing session or create new one.

        Args:
            session_id: Unique session identifier.
            create_if_missing: If True, create session when not found.

        Returns:
            SessionMemory instance.
        """
        if session_id not in self._sessions:
            if create_if_missing:
                logger.info("Creating new session: %s", session_id)
                self._sessions[session_id] = SessionMemory(sessionId=session_id)
            else:
                raise KeyError(f"Session not found: {session_id}")
        else:
            logger.info("Loading existing session: %s", session_id)

        return self._sessions[session_id]

    def save_session(
        self,
        session_id: str,
        session: SessionMemory,
        update_metrics: bool = True,
    ) -> None:
        """
        Save session to storage.

        Args:
            session_id: Unique session identifier.
            session: SessionMemory instance to save.
            update_metrics: If True, update lastActivityTime (default True).
        """
        if update_metrics:
            session.lastActivityTime = datetime.now()
        self._sessions[session_id] = session
        logger.info(
            "Session saved: %s, total messages: %s",
            session_id,
            session.totalMessagesExchanged,
        )

    def delete_session(self, session_id: str) -> bool:
        """
        Remove session from storage.

        Args:
            session_id: Unique session identifier.

        Returns:
            True if session was deleted, False if it did not exist.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("Session deleted: %s", session_id)
            return True
        return False

    def get_all_sessions(self) -> Dict[str, SessionMemory]:
        """Return all active sessions (for debugging)."""
        return self._sessions
