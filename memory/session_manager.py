from typing import Dict
from memory.schemas import SessionMemory
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# In-memory storage (use Redis in production)
SESSIONS: Dict[str, SessionMemory] = {}

def load_session(session_id: str) -> SessionMemory:
    """
    Load existing session or create new one.
    """
    if session_id not in SESSIONS:
        logger.info(f"Creating new session: {session_id}")
        SESSIONS[session_id] = SessionMemory(sessionId=session_id)
    else:
        logger.info(f"Loading existing session: {session_id}")
    
    return SESSIONS[session_id]

def save_session(session_id: str, session: SessionMemory) -> None:
    """
    Save session to storage.
    """
    session.lastActivityTime = datetime.now()
    SESSIONS[session_id] = session
    logger.info(f"Session saved: {session_id}, total messages: {session.totalMessagesExchanged}")

def delete_session(session_id: str) -> None:
    """
    Remove session after completion.
    """
    if session_id in SESSIONS:
        del SESSIONS[session_id]
        logger.info(f"Session deleted: {session_id}")

def get_all_sessions() -> Dict[str, SessionMemory]:
    """
    Return all active sessions (for debugging).
    """
    return SESSIONS
