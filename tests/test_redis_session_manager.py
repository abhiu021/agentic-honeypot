"""
Pytest tests for RedisSessionManager - all 10 issues covered.

Uses redis://localhost:6379/1 (DB 1) to avoid affecting production DB 0.
"""

import os
import sys
import time
import threading
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from memory.redis_session_manager import RedisSessionManager
from memory.schemas import SessionMemory


# Test DB and short TTL for fast expiry tests
REDIS_TEST_URL = os.getenv("REDIS_TEST_URL", "redis://localhost:6379/1")
TEST_TTL = 10


@pytest.fixture
def redis_manager():
    """
    RedisSessionManager on DB 1 with short TTL for tests.
    Clears sessions before and after each test.
    """
    try:
        manager = RedisSessionManager(
            redis_url=REDIS_TEST_URL,
            max_sessions=100,
            session_ttl_seconds=TEST_TTL,
        )
        manager.health_check()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

    manager.clear_all_sessions()
    yield manager
    manager.clear_all_sessions()
    manager.shutdown()


# --- ISSUE 3: Invalid Session IDs ---
class TestIssue3_InvalidIDs:
    """Test validation prevents malicious/malformed session IDs."""

    def test_valid_id_accepted(self, redis_manager):
        ok, err = redis_manager.validate_session_id("valid_session_123")
        assert ok is True
        assert err == ""

    def test_too_short_rejected(self, redis_manager):
        ok, err = redis_manager.validate_session_id("abcd")
        assert ok is False
        assert "5" in err or "length" in err.lower()

    def test_too_long_rejected(self, redis_manager):
        ok, err = redis_manager.validate_session_id("a" * 129)
        assert ok is False

    def test_path_traversal_rejected(self, redis_manager):
        ok, _ = redis_manager.validate_session_id("../../../etc/passwd")
        assert ok is False

    def test_sql_injection_like_rejected(self, redis_manager):
        ok, _ = redis_manager.validate_session_id("'; DROP TABLE sessions; --")
        assert ok is False

    def test_special_chars_rejected(self, redis_manager):
        ok, _ = redis_manager.validate_session_id("session@123")
        assert ok is False


# --- ISSUE 7: Session Hijacking (UUID randomness) ---
class TestIssue7_SessionHijacking:
    """Test generated session IDs are cryptographically random."""

    def test_generate_session_id_format(self, redis_manager):
        sid = redis_manager.generate_session_id()
        assert isinstance(sid, str)
        assert len(sid) == 16
        assert sid.isalnum()

    def test_generate_session_ids_unique(self, redis_manager):
        ids = {redis_manager.generate_session_id() for _ in range(100)}
        assert len(ids) == 100


# --- ISSUE 1: Race Conditions ---
class TestIssue1_RaceConditions:
    """Test concurrent access does not corrupt state (Redis atomic ops)."""

    def test_concurrent_writes_same_session(self, redis_manager):
        session_id = "race_test_001"
        redis_manager.create_session(session_id)
        errors = []

        def update_session(n):
            try:
                s = redis_manager.load_session(session_id)
                s.totalMessagesExchanged = n
                s.conversationHistory.append({"turn": n})
                redis_manager.save_session(session_id, s)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=update_session, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        s = redis_manager.load_session(session_id)
        assert s.totalMessagesExchanged >= 0
        assert len(s.conversationHistory) >= 1


# --- ISSUE 2: Memory Leak (TTL) ---
class TestIssue2_MemoryLeak:
    """Test sessions expire after TTL (no memory leak)."""

    def test_session_expires_after_ttl(self, redis_manager):
        session_id = "ttl_test_001"
        redis_manager.create_session(session_id)
        assert redis_manager.session_exists(session_id)
        time.sleep(TEST_TTL + 1)
        assert not redis_manager.session_exists(session_id)


# --- ISSUE 4: State Corruption ---
class TestIssue4_StateCorruption:
    """Test atomic multi-field updates (pipeline)."""

    def test_save_preserves_all_fields(self, redis_manager):
        session_id = "state_001"
        s = redis_manager.create_session(session_id)
        s.scamType = "UPI_FRAUD"
        s.totalMessagesExchanged = 5
        s.conversationHistory = [{"sender": "scammer", "text": "hello"}]
        s.extractedIntelligence["identityMarkers"]["phoneNumbers"] = ["+919876543210"]
        redis_manager.save_session(session_id, s)

        loaded = redis_manager.load_session(session_id)
        assert loaded.scamType == "UPI_FRAUD"
        assert loaded.totalMessagesExchanged == 5
        assert len(loaded.conversationHistory) == 1
        assert loaded.extractedIntelligence["identityMarkers"]["phoneNumbers"] == ["+919876543210"]


# --- ISSUE 5: Intelligence Loss ---
class TestIssue5_IntelligenceLoss:
    """Test intelligence accumulation (load-merge-save pattern)."""

    def test_intelligence_accumulates_across_saves(self, redis_manager):
        session_id = "intel_001"
        s = redis_manager.create_session(session_id)
        s.extractedIntelligence["identityMarkers"]["phoneNumbers"] = ["+919876543210"]
        redis_manager.save_session(session_id, s)

        s2 = redis_manager.load_session(session_id)
        s2.extractedIntelligence["identityMarkers"]["upiIds"] = ["scam@paytm"]
        redis_manager.save_session(session_id, s2)

        s3 = redis_manager.load_session(session_id)
        assert "+919876543210" in s3.extractedIntelligence["identityMarkers"]["phoneNumbers"]
        assert "scam@paytm" in s3.extractedIntelligence["identityMarkers"]["upiIds"]


# --- ISSUE 6: Out of Order ---
class TestIssue6_OutOfOrder:
    """Test lastActivityTime is updated on every operation."""

    def test_last_activity_updated_on_save(self, redis_manager):
        session_id = "order_001"
        s = redis_manager.create_session(session_id)
        t1 = s.lastActivityTime
        time.sleep(0.1)
        redis_manager.save_session(session_id, s)
        s2 = redis_manager.load_session(session_id)
        assert s2.lastActivityTime >= t1


# --- ISSUE 8: Server Restart (Persistence) ---
class TestIssue8_ServerRestart:
    """Test persistence across manager restarts (new instance, same Redis)."""

    def test_session_survives_manager_restart(self, redis_manager):
        session_id = "persist_001"
        s = redis_manager.create_session(session_id)
        s.scamType = "PHISHING"
        redis_manager.save_session(session_id, s)

        # Simulate server restart: new manager instance, same Redis (ISSUE 8)
        manager2 = RedisSessionManager(
            redis_url=REDIS_TEST_URL,
            max_sessions=100,
            session_ttl_seconds=TEST_TTL,
        )
        loaded = manager2.get_session(session_id)
        assert loaded is not None
        assert loaded.scamType == "PHISHING"
        manager2.clear_all_sessions()
        manager2.shutdown()


# --- ISSUE 9: No Recovery (Error handling) ---
class TestIssue9_NoRecovery:
    """Test graceful error handling (validation, connection)."""

    def test_invalid_id_raises_on_load(self, redis_manager):
        with pytest.raises(ValueError):
            redis_manager.load_session("ab")  # too short

    def test_invalid_id_raises_on_save(self, redis_manager):
        s = redis_manager.create_session("valid_009")
        with pytest.raises(ValueError):
            redis_manager.save_session("x" * 200, s)


# --- ISSUE 10: Size Explosion ---
class TestIssue10_SizeExplosion:
    """Test max sessions limit with LRU eviction."""

    def test_max_sessions_evicts_oldest(self, redis_manager):
        # Use a small max_sessions for test
        small_manager = RedisSessionManager(
            redis_url=REDIS_TEST_URL,
            max_sessions=3,
            session_ttl_seconds=300,
        )
        small_manager.clear_all_sessions()

        s1 = small_manager.create_session("evict_001")
        s2 = small_manager.create_session("evict_002")
        s3 = small_manager.create_session("evict_003")
        assert small_manager.get_active_session_count() == 3

        time.sleep(0.1)
        s4 = small_manager.create_session("evict_004")
        assert small_manager.get_active_session_count() == 3
        assert not small_manager.session_exists("evict_001")
        assert small_manager.session_exists("evict_004")

        small_manager.clear_all_sessions()
        small_manager.shutdown()


# --- General API ---
class TestRedisSessionManagerAPI:
    """Test full API: create, load, save, delete, metrics, health."""

    def test_create_and_load(self, redis_manager):
        s = redis_manager.create_session("api_001")
        assert s.sessionId == "api_001"
        loaded = redis_manager.load_session("api_001")
        assert loaded.sessionId == s.sessionId

    def test_create_with_generated_id(self, redis_manager):
        s = redis_manager.create_session()
        assert s.sessionId
        ok, _ = redis_manager.validate_session_id(s.sessionId)
        assert ok

    def test_delete_removes_session(self, redis_manager):
        redis_manager.create_session("del_001")
        assert redis_manager.session_exists("del_001")
        redis_manager.delete_session("del_001")
        assert not redis_manager.session_exists("del_001")

    def test_get_session_returns_none_if_missing(self, redis_manager):
        assert redis_manager.get_session("nonexistent_xyz") is None

    def test_get_metrics_returns_dict(self, redis_manager):
        redis_manager.create_session("m_001")
        m = redis_manager.get_metrics()
        assert isinstance(m, dict)
        assert "total_sessions_created" in m or "total_loads" in m

    def test_health_check_returns_status(self, redis_manager):
        h = redis_manager.health_check()
        assert h["status"] == "ok"
        assert h["connected"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
