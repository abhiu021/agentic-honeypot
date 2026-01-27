import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from agents.detection_agent import DetectionAgent


class TestDetectionAgent:
    """Test suite for DetectionAgent scam detection functionality."""

    @pytest.fixture
    def agent(self):
        """Create DetectionAgent instance for testing."""
        return DetectionAgent()

    def test_upi_fraud_detection(self, agent):
        """Test detection of UPI fraud scam messages."""
        msg = "URGENT: Your UPI account will be BLOCKED. Share UPI ID and OTP now."
        result = agent.analyze(msg, "SMS")
        
        assert result["scamDetected"] == True
        assert result["scamScore"] >= 0.45
        assert result["scamType"] == "UPI_FRAUD"
        assert "componentScores" in result
        assert all(score >= 0.0 for score in result["componentScores"].values())

    def test_account_takeover(self, agent):
        """Test detection of account takeover scam messages."""
        msg = "URGENT: Account locked due to suspicious login. Immediate action required. Share your user ID and password or account will be terminated."
        result = agent.analyze(msg, "SMS")
        
        assert result["scamDetected"] == True
        assert result["scamScore"] >= 0.50
        assert result["scamType"] == "ACCOUNT_TAKEOVER"
        assert "componentScores" in result

    def test_phishing_link(self, agent):
        """Test detection of phishing scam messages with links."""
        msg = "URGENT: Click here to verify immediately: https://fake-bank.com/verify now or access will be suspended and blocked."
        result = agent.analyze(msg, "Email")
        
        assert result["scamDetected"] == True
        assert result["scamScore"] >= 0.50
        assert result["scamType"] == "PHISHING"
        assert "componentScores" in result

    def test_investment_scam(self, agent):
        """Test detection of investment scam messages."""
        msg = "URGENT: Earn guaranteed profit immediately! Limited time. Invest now before offer expires. Join our platform today."
        result = agent.analyze(msg, "WhatsApp")
        
        assert result["scamDetected"] == True
        assert result["scamScore"] >= 0.44
        assert result["scamType"] == "INVESTMENT_SCAM"
        assert "componentScores" in result

    def test_legitimate_message(self, agent):
        """Test that legitimate messages are not flagged as scams."""
        msg = "Your appointment is tomorrow at 3 PM. Please confirm."
        result = agent.analyze(msg, "SMS")
        
        assert result["scamDetected"] == False
        assert result["scamScore"] < 0.45
        assert result["scamType"] is None

    def test_component_score_transparency(self, agent):
        """Test that component scores are provided and sum correctly."""
        msg = "URGENT: Your bank account is BLOCKED. Share OTP immediately."
        result = agent.analyze(msg, "SMS")
        
        # Verify all component scores are present
        component_scores = result["componentScores"]
        assert "urgency" in component_scores
        assert "authority" in component_scores
        assert "threat" in component_scores
        assert "infoRequest" in component_scores
        assert "channel" in component_scores
        
        # Verify scores are in valid range [0, 1]
        for score_name, score_value in component_scores.items():
            assert 0.0 <= score_value <= 1.0, f"{score_name} score out of range: {score_value}"
        
        # Verify scam score is weighted sum of components
        expected_score = (
            component_scores["urgency"] * agent.URGENCY_WEIGHT
            + component_scores["authority"] * agent.AUTHORITY_WEIGHT
            + component_scores["threat"] * agent.THREAT_WEIGHT
            + component_scores["infoRequest"] * agent.INFO_REQUEST_WEIGHT
            + component_scores["channel"] * agent.CHANNEL_WEIGHT
        )
        assert abs(result["scamScore"] - round(expected_score, 2)) < 0.01

    def test_channel_weighting(self, agent):
        """Test that different channels have different risk scores."""
        msg = "Your account needs verification. Please share details."
        
        # Test different channels
        sms_result = agent.analyze(msg, "SMS")
        whatsapp_result = agent.analyze(msg, "WhatsApp")
        email_result = agent.analyze(msg, "Email")
        call_result = agent.analyze(msg, "CALL")
        other_result = agent.analyze(msg, "Other")
        
        # SMS and WhatsApp should have higher channel scores
        assert sms_result["componentScores"]["channel"] == 0.75
        assert whatsapp_result["componentScores"]["channel"] == 0.45
        
        # Email and Call should have medium channel scores
        assert email_result["componentScores"]["channel"] == 0.6
        assert call_result["componentScores"]["channel"] == 0.5
        
        # Other channels should have lower channel scores
        assert other_result["componentScores"]["channel"] == 0.5
        
        # SMS/WhatsApp should contribute more to overall score
        assert sms_result["scamScore"] >= email_result["scamScore"]
        assert whatsapp_result["scamScore"] >= other_result["scamScore"]
