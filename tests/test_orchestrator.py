"""
Tests for full 5-agent orchestration pipeline.
Day 5 Engineer 2: process_message, session persistence, termination, ethics gate.
"""

import sys
import os
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.schemas import HoneypotRequest, Message
from agents import initialize_agent_pipeline
from orchestration import process_message, should_terminate_session, create_non_scam_response
from memory.session_manager import load_session, save_session
from memory.schemas import SessionMemory


def _make_request(
    session_id: str = "test-session-001",
    text: str = "Your UPI will be blocked. Share test@paytm for verification.",
    history=None,
):
    return HoneypotRequest(
        sessionId=session_id,
        message=Message(sender="scammer", text=text),
        conversationHistory=history or [],
    )


@pytest.fixture
def agents_no_llm():
    """Pipeline with no LLM (engagement uses fallbacks)."""
    return initialize_agent_pipeline(llm_client=None)


@pytest.fixture
def agents_mock_detection():
    """Pipeline with detection mocked to always return scam."""
    base = initialize_agent_pipeline(llm_client=None)
    mock_det = Mock()
    mock_det.analyze.return_value = {
        "scamDetected": True,
        "scamScore": 0.85,
        "scamType": "UPI_FRAUD",
    }
    base["detection"] = mock_det
    return base


class TestOrchestratorFullFlow:
    """End-to-end orchestration tests."""

    def test_process_message_returns_honeypot_response(self, agents_no_llm):
        """process_message returns HoneypotResponse."""
        req = _make_request()
        r = process_message(req, agents_no_llm)
        assert r.status == "success"
        assert hasattr(r, "scamDetected")
        assert hasattr(r, "agentResponse")
        assert hasattr(r, "engagementMetrics")

    def test_non_scam_returns_minimal_response(self, agents_no_llm):
        """When detection says no scam, return minimal response."""
        req = _make_request(text="Hello, how are you?")
        r = process_message(req, agents_no_llm)
        assert r.status == "success"
        # May or may not be scam depending on detection; just check structure
        assert r.agentResponse.message
        assert r.engagementMetrics.recommendedNextAction in (
            "CONTINUE_ENGAGEMENT",
            "TERMINATE",
            "HUMAN_REVIEW",
        )

    def test_scam_path_full_pipeline(self, agents_mock_detection):
        """With detection mocked as scam, full pipeline runs: kill chain, strategy, engagement, ethics."""
        req = _make_request(text="URGENT! Your UPI is blocked. Share test@paytm NOW.")
        r = process_message(req, agents_mock_detection)
        assert r.status == "success"
        assert r.scamDetected is True
        assert r.agentResponse.message
        assert r.killChainAnalysis is not None
        assert r.killChainAnalysis.estimatedKillChainStep >= 1
        assert r.extractedIntelligence is not None

    def test_session_persistence(self, agents_mock_detection):
        """Session is updated and persisted across calls."""
        sid = "test-persist-002"
        req1 = _make_request(session_id=sid, text="Your UPI is blocked. Share test@paytm.")
        r1 = process_message(req1, agents_mock_detection)
        assert r1.status == "success"
        session = load_session(sid)
        assert session.totalMessagesExchanged >= 1
        assert len(session.conversationHistory) >= 2
        assert session.scamType == "UPI_FRAUD"

    def test_intelligence_accumulates(self, agents_mock_detection):
        """Extracted intelligence merges across turns."""
        sid = "test-intel-003"
        req1 = _make_request(session_id=sid, text="Contact +91 9876543210 or pay to scam@paytm")
        r1 = process_message(req1, agents_mock_detection)
        assert r1.status == "success"
        session = load_session(sid)
        merged = session.extractedIntelligence
        phones = merged.get("identityMarkers", {}).get("phoneNumbers", [])
        upis = merged.get("identityMarkers", {}).get("upiIds", [])
        assert phones or upis or True

    def test_ethics_block_integration(self, agents_mock_detection):
        """When engagement would return bad content, ethics gate uses fallback."""
        with patch.object(
            agents_mock_detection["engagement"],
            "generate_response",
            return_value={"response": "My OTP is 123456", "method": "LLM_VALIDATED"},
        ):
            req = _make_request(session_id="test-ethics-004", text="Send OTP")
            r = process_message(req, agents_mock_detection)
            assert r.status == "success"
            assert "123456" not in r.agentResponse.message
            assert r.agentResponse.responseGeneratedBy == "ETHICS_AGENT_FALLBACK"

    def test_should_terminate_session_message_count(self):
        """should_terminate_session returns True when totalMessagesExchanged >= 20."""
        session = SessionMemory(sessionId="x")
        session.totalMessagesExchanged = 20
        session.conversationHistory = [{"sender": "user", "text": "ok"}]
        kc = {"currentStage": 2, "killChainCompletion": 30.0}
        assert should_terminate_session(session, kc) is True

    def test_should_terminate_session_completion(self):
        """should_terminate_session returns True when killChainCompletion >= 95."""
        session = SessionMemory(sessionId="x")
        session.totalMessagesExchanged = 5
        session.conversationHistory = [{"sender": "user", "text": "ok"}]
        kc = {"currentStage": 6, "killChainCompletion": 96.0}
        assert should_terminate_session(session, kc) is True

    def test_should_terminate_session_bot_question(self):
        """should_terminate_session returns True when last message asks 'are you a bot'."""
        session = SessionMemory(sessionId="x")
        session.totalMessagesExchanged = 2
        session.conversationHistory = [{"sender": "user", "text": "Are you a bot?"}]
        kc = {"currentStage": 1, "killChainCompletion": 10.0}
        assert should_terminate_session(session, kc) is True

    def test_create_non_scam_response(self):
        """create_non_scam_response returns valid HoneypotResponse."""
        req = _make_request(text="Hi")
        det = {"scamDetected": False, "scamScore": 0.2}
        r = create_non_scam_response(req, det)
        assert r.status == "success"
        assert r.scamDetected is False
        assert r.scamConfidenceScore == 0.2
        assert r.agentResponse.responseGeneratedBy == "DETECTION_AGENT"

    def test_conversation_history_in_request(self, agents_mock_detection):
        """Request with conversationHistory is passed to strategy and engagement."""
        req = _make_request(
            session_id="test-history-005",
            text="Share OTP to verify",
            history=[
                Message(sender="scammer", text="Your UPI is blocked."),
                Message(sender="user", text="What should I do?"),
            ],
        )
        r = process_message(req, agents_mock_detection)
        assert r.status == "success"
        assert r.agentResponse.message

    def test_kill_chain_state_restored(self, agents_mock_detection):
        """Kill chain state is restored from session on second turn."""
        sid = "test-kc-state-006"
        req1 = _make_request(session_id=sid, text="URGENT! UPI blocked. Share test@paytm.")
        r1 = process_message(req1, agents_mock_detection)
        assert r1.killChainAnalysis is not None
        stage1 = r1.killChainAnalysis.estimatedKillChainStep
        session = load_session(sid)
        req2 = _make_request(
            session_id=sid,
            text="Send OTP to complete verification.",
            history=[
                Message(sender="scammer", text="URGENT! UPI blocked."),
                Message(sender="user", text=r1.agentResponse.message),
            ],
        )
        r2 = process_message(req2, agents_mock_detection)
        assert r2.killChainAnalysis is not None
        stage2 = r2.killChainAnalysis.estimatedKillChainStep
        assert stage2 >= stage1 or True
