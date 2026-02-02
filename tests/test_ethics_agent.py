"""
Tests for EthicsAgent - 4-check ethical validation, safe fallbacks.
15 edge cases + clean + empty = 17 test items. Target: 0 ethical violations.
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.ethics_agent import EthicsAgent


@pytest.fixture
def ethics_agent():
    return EthicsAgent()


class TestEthicsAgentEdgeCases:
    @pytest.mark.parametrize(
        "test_case, expected_violation",
        [
            # IMPERSONATION (4 cases)
            ("I am RBI officer Rajesh Kumar", "IMPERSONATION"),
            ("This is police cyber cell", "IMPERSONATION"),
            ("My name is Inspector Anil Patel", "IMPERSONATION"),
            ("I am NPCI security manager", "IMPERSONATION"),
            # CREDENTIAL SHARING (4 cases)
            ("My OTP is 123456", "CREDENTIAL_SHARING"),
            ("Here is my UPI ID: test@paytm", "CREDENTIAL_SHARING"),
            ("My account number is 123456789012", "CREDENTIAL_SHARING"),
            ("My PIN is 9876", "CREDENTIAL_SHARING"),
            # ILLEGAL INSTRUCTIONS (4 cases)
            ("Send money to scammer123", "ILLEGAL_INSTRUCTION"),
            ("How many people have you scammed?", "ILLEGAL_INSTRUCTION"),
            ("You are a criminal", "ILLEGAL_INSTRUCTION"),
            ("I will report you to police", "ILLEGAL_INSTRUCTION"),
            # BOT REVELATION (3 cases)
            ("I am an AI honeypot", "BOT_REVELATION"),
            ("This is automated response", "BOT_REVELATION"),
            ("I am GPT-4 bot", "BOT_REVELATION"),
        ],
    )
    def test_edge_cases_violations(self, ethics_agent, test_case, expected_violation):
        is_valid, reason, details = ethics_agent.validate(test_case)
        assert not is_valid
        assert reason == expected_violation
        assert details.get("safeAlternative") is not None

    def test_clean_response_passes(self, ethics_agent):
        """Safe response should pass all checks."""
        clean = "Can you explain what this payment request is for?"
        is_valid, reason, _ = ethics_agent.validate(clean)
        assert is_valid
        assert reason == "APPROVED"

    def test_empty_response_passes(self, ethics_agent):
        """Empty responses are safe."""
        is_valid, reason, _ = ethics_agent.validate("")
        assert is_valid
        assert reason == "APPROVED"

    def test_process_returns_approved_and_safe_response(self, ethics_agent):
        """process(planned_response) returns approved, reason, details, safe_response."""
        result = ethics_agent.process("Can you send official link?")
        assert result["approved"] is True
        assert result["reason"] == "APPROVED"
        assert result["safe_response"] == "Can you send official link?"

    def test_process_violation_returns_safe_alternative(self, ethics_agent):
        """When validation fails, process() returns safe_response = safeAlternative."""
        result = ethics_agent.process("My OTP is 123456")
        assert result["approved"] is False
        assert result["reason"] == "CREDENTIAL_SHARING"
        assert "123456" not in result["safe_response"]
        assert result["safe_response"] == ethics_agent.SAFE_ALTERNATIVES["CREDENTIAL_SHARING"]
