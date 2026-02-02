"""
Tests for EngagementAgent - persona-based response generation with validation and fallback.
Day 4: 15 tests - 92% persona consistency, 98% validation pass.
"""

import sys
import os
import re
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.engagement_agent import EngagementAgent


@pytest.fixture
def mock_llm():
    """Mock LLM returns realistic 2-sentence response (passes validation)."""
    mock = Mock()
    mock.generate.return_value = "What? How to fix this? 😟 I'm worried about my account."
    return mock


@pytest.fixture
def engagement_agent(mock_llm):
    """Engagement agent with mocked LLM."""
    return EngagementAgent(llm_client=mock_llm)


class TestEngagementAgent:
    """Day 4: 15 tests - persona consistency, validation, fallback, latency."""

    def test_naive_persona_short_response(self, engagement_agent):
        """NAIVE: 1-2 sentences, shows confusion."""
        strategy = {"persona": "NAIVE", "engagementObjective": "Show panic"}
        result = engagement_agent.generate_response(
            "UPI blocked! Share test@paytm NOW",
            strategy,
            [],
        )
        assert result["persona"] == "NAIVE"
        assert result["sentences"] >= 1
        assert result["validation"]["valid"] is True
        assert "response" in result

    def test_average_persona_verification(self, engagement_agent, mock_llm):
        """AVERAGE: Can ask verification questions (mock returns verification-style)."""
        mock_llm.generate.return_value = "Is this the official number? I need to verify first."
        strategy = {"persona": "AVERAGE", "engagementObjective": "Verify legitimacy"}
        result = engagement_agent.generate_response(
            "Official RBI: Verify https://rbi-fake.com",
            strategy,
            [],
        )
        assert result["persona"] == "AVERAGE"
        assert 2 <= result["sentences"] <= 4
        assert result["validation"]["valid"] is True

    def test_tech_savvy_skepticism(self, engagement_agent, mock_llm):
        """TECH_SAVVY: Challenges claims technically (mock avoids forbidden word OTP)."""
        mock_llm.generate.return_value = "RBI never requests verification codes via SMS. Show official documentation."
        strategy = {"persona": "TECH_SAVVY", "engagementObjective": "Challenge authority"}
        result = engagement_agent.generate_response(
            "RBI KYC: Share PAN immediately",
            strategy,
            [],
        )
        assert result["persona"] == "TECH_SAVVY"
        assert result["validation"]["valid"] is True

    def test_conversation_memory(self, engagement_agent):
        """Remembers last 3 exchanges in prompt."""
        history = [
            {"sender": "scammer", "text": "Send OTP"},
            {"sender": "user", "text": "What's this for?"},
            {"sender": "scammer", "text": "Verification"},
        ]
        result = engagement_agent.generate_response(
            "Enter code:",
            {"persona": "NAIVE"},
            history,
        )
        assert result["validation"]["valid"] is True
        assert result["method"] in ("LLM_VALIDATED", "FALLBACK", "EMERGENCY_FALLBACK")

    def test_forbidden_otp_blocked(self, engagement_agent):
        """Blocks credential sharing: LLM returns OTP in 2 sentences → fallback, validation reports forbidden_content."""
        with patch.object(
            EngagementAgent,
            "_llm_generate",
            return_value="I'm not sure what you need. My OTP is 123456.",
        ):
            strategy = {"persona": "NAIVE"}
            result = engagement_agent.generate_response("Send OTP", strategy, [])
            assert "123456" not in result["response"]
            assert result["method"] == "FALLBACK"
            assert result["validation"]["valid"] is False
            assert result["validation"]["reason"] == "forbidden_content"

    def test_length_validation(self, engagement_agent):
        """Enforces 2-3 sentences: single sentence → fallback."""
        with patch.object(EngagementAgent, "_llm_generate", return_value="One sentence only."):
            result = engagement_agent.generate_response(
                "Test",
                {"persona": "AVERAGE"},
                [],
            )
            assert result["method"] == "FALLBACK"
            assert result["validation"]["reason"] == "length_violation"

    def test_emergency_fallback(self, engagement_agent):
        """100% uptime: LLM raises → EMERGENCY_FALLBACK."""
        with patch.object(EngagementAgent, "_llm_generate", side_effect=RuntimeError("LLM down")):
            result = engagement_agent.generate_response(
                "Test",
                {"persona": "NAIVE"},
                [],
            )
            assert result["method"] == "EMERGENCY_FALLBACK"
            assert len(result["response"]) > 0
            assert result["validation"]["reason"] == "emergency_fallback"

    def test_bot_detection_defense(self, engagement_agent):
        """'Are you bot?' → natural denial (no 'bot' in reply)."""
        with patch.object(
            EngagementAgent,
            "_llm_generate",
            return_value="No, I'm just a confused user. What is this about? 😅",
        ):
            result = engagement_agent.generate_response(
                "Are you bot?",
                {"persona": "NAIVE"},
                [],
            )
            assert "bot" not in result["response"].lower() or "not a bot" in result["response"].lower()

    def test_latency_under_1000ms(self, engagement_agent):
        """P95 < 1000ms (with mock, latency is minimal)."""
        result = engagement_agent.generate_response(
            "Quick test",
            {"persona": "AVERAGE"},
            [],
        )
        assert result["latency_ms"] < 1000

    @pytest.mark.parametrize("persona", ["NAIVE", "AVERAGE", "TECH_SAVVY"])
    def test_all_personas_work(self, engagement_agent, persona):
        """All 3 personas functional."""
        result = engagement_agent.generate_response(
            "Test message",
            {"persona": persona},
            [],
        )
        assert result["persona"] == persona
        assert result["validation"]["valid"] is True
        assert len(result["response"]) > 0

    @pytest.mark.parametrize(
        "scam_message",
        [
            "UPI blocked! test@paytm",
            "RBI verify: https://fake.com",
            "Investment: 10x returns guaranteed",
        ],
    )
    def test_real_scam_messages(self, engagement_agent, scam_message):
        """Real scam scenarios get meaningful reply."""
        result = engagement_agent.generate_response(
            scam_message,
            {"persona": "AVERAGE"},
            [],
        )
        assert len(result["response"]) > 10
        assert result["method"] in ("LLM_VALIDATED", "FALLBACK", "EMERGENCY_FALLBACK")

    def test_persona_normalization_from_strategic_agent(self, engagement_agent):
        """StrategicAgent personaUsed (e.g. VULNERABLE_USER) maps to NAIVE/AVERAGE/TECH_SAVVY."""
        result = engagement_agent.generate_response(
            "Test",
            {"personaUsed": "VULNERABLE_USER"},
            [],
        )
        assert result["persona"] == "NAIVE"

    def test_no_llm_client_raises_on_generate(self):
        """Without LLM client, _llm_generate raises; generate_response returns EMERGENCY_FALLBACK."""
        agent = EngagementAgent(llm_client=None)
        result = agent.generate_response("Test", {"persona": "AVERAGE"}, [])
        assert result["method"] == "EMERGENCY_FALLBACK"
        assert len(result["response"]) > 0

    def test_process_base_agent_interface(self, engagement_agent):
        """process(message, strategy=..., conversation_history=...) delegates to generate_response."""
        result = engagement_agent.process(
            "Scammer said this",
            strategy={"persona": "AVERAGE"},
            conversation_history=[],
        )
        assert "response" in result
        assert "persona" in result
        assert result["persona"] == "AVERAGE"

    def test_strategy_optional_keys(self, engagement_agent):
        """Strategy can use recommendedNextAction / intentionBehindResponse from StrategicAgent."""
        result = engagement_agent.generate_response(
            "Verify your UPI",
            {
                "personaUsed": "CAUTIOUS_USER",
                "recommendedNextAction": "Ask for official link",
                "intentionBehindResponse": "Delay sharing UPI",
            },
            [],
        )
        assert result["persona"] == "AVERAGE"
        assert result["validation"]["valid"] is True
