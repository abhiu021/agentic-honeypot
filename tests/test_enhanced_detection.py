import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
from agents.enhanced_detection_agent import EnhancedDetectionAgent
from utils.llm_client import MockLLMClient


class TestEnhancedDetectionAgent:
    """Test hybrid rule-based + LLM detection logic."""
    
    def test_high_confidence_skips_llm(self):
        """High confidence (≥0.60) should NOT call LLM."""
        # No LLM client provided
        agent = EnhancedDetectionAgent(llm_client=None)
        
        # Message that scores high (urgency + threat + info_request + authority)
        message = "URGENT ACTION REQUIRED: Your bank account will be BLOCKED. Submit your OTP and password IMMEDIATELY or face legal consequences from RBI authorities."
        result = agent.analyze(message, "SMS")
        
        # Assertions
        assert result["scamDetected"] is True
        assert result["scamScore"] >= 0.60
        assert result["confidence"] == "HIGH"
        assert result["detectionMethod"] == "RULE_BASED"
        assert "reasoning" in result
        
        # Verify backward compatibility
        assert "componentScores" in result
        assert "scamType" in result
    
    def test_low_confidence_calls_llm(self):
        """Low confidence (<0.60) should call LLM."""
        # Mock LLM that returns scam detection
        llm_response = json.dumps({
            "scamDetected": True,
            "scamScore": 0.75,
            "scamType": "UPI_FRAUD",
            "reasoning": "Implicit urgency with payment verification request"
        })
        
        mock_llm = MockLLMClient(
            predefined_responses={"analyze": llm_response}
        )
        
        agent = EnhancedDetectionAgent(llm_client=mock_llm)
        
        # Borderline message (low keyword matches, but contextually suspicious)
        message = "Hi, there's an important update regarding your payment. Please verify your details."
        result = agent.analyze(message, "SMS")
        
        # LLM should have been called
        assert mock_llm.call_count > 0
        assert result["detectionMethod"] == "LLM_ENHANCED"
        assert result["confidence"] == "MEDIUM"
        assert result["scamDetected"] is True
        assert "reasoning" in result
        assert result["scamScore"] == 0.75
    
    def test_llm_failure_fallback(self):
        """If LLM fails, should fallback to rule-based."""
        # Mock LLM that raises error
        class FailingLLM:
            def generate(self, *args, **kwargs):
                raise Exception("API timeout")
        
        agent = EnhancedDetectionAgent(llm_client=FailingLLM())
        
        # Low confidence message
        message = "Click this link to update your account information."
        result = agent.analyze(message, "SMS")
        
        # Should fallback gracefully
        assert result["detectionMethod"] == "RULE_BASED_FALLBACK"
        assert result["confidence"] == "LOW"
        assert "LLM unavailable" in result["reasoning"]
        
        # Core fields still present
        assert "scamDetected" in result
        assert "scamScore" in result
        assert "componentScores" in result
    
    def test_no_llm_client_provided(self):
        """Without LLM client, should use pure rule-based."""
        agent = EnhancedDetectionAgent(llm_client=None)
        
        # Legitimate message (low score)
        message = "Hi, how are you doing today?"
        result = agent.analyze(message, "SMS")
        
        assert result["detectionMethod"] == "RULE_BASED"
        assert result["scamDetected"] is False
        assert result["confidence"] == "LOW"
    
    def test_output_format_compatibility(self):
        """Output must be compatible with existing DetectionAgent format."""
        agent = EnhancedDetectionAgent(llm_client=None)
        
        message = "Urgent: Verify your UPI account to avoid suspension"
        result = agent.analyze(message, "SMS")
        
        # Required fields from DetectionAgent
        required_fields = ["scamDetected", "scamType", "scamScore", "componentScores"]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # New optional fields
        assert "confidence" in result
        assert "detectionMethod" in result
        assert "reasoning" in result
        
        # componentScores structure
        assert isinstance(result["componentScores"], dict)
        assert "urgency" in result["componentScores"]
        assert "authority" in result["componentScores"]
    
    def test_threshold_boundary(self):
        """Test behavior at exact threshold boundary."""
        agent = EnhancedDetectionAgent(llm_client=None)
        
        # Message with moderate indicators
        message = "Important update about your account"
        result = agent.analyze(message, "SMS")
        
        # Should have a detectionMethod
        assert result["detectionMethod"] in [
            "RULE_BASED", "LLM_ENHANCED", "RULE_BASED_FALLBACK"
        ]
        
        # Should have confidence level
        assert result["confidence"] in ["HIGH", "MEDIUM", "LOW"]
