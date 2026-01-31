"""
Tests for StrategicAgent: engagement phase, next action, persona, intention.
"""

import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.strategic_agent import StrategicAgent, ENGAGEMENT_PHASES, PERSONAS


def test_strategic_agent_early_stage():
    """Early kill-chain stage -> CREDIBILITY_ESTABLISHMENT, CONTINUE_ENGAGEMENT."""
    agent = StrategicAgent()
    kill_chain = {
        "currentStage": 1,
        "stageName": "Urgency Trigger",
        "killChainCompletion": 16.67,
        "stageObjective": "Create urgency",
    }
    out = agent.process(kill_chain, {}, scam_confidence=0.8)
    assert out["userEngagementPhase"] == "CREDIBILITY_ESTABLISHMENT"
    assert out["recommendedNextAction"] in ("CONTINUE_ENGAGEMENT", "HUMAN_REVIEW", "TERMINATE")
    assert out["personaUsed"] in PERSONAS
    assert "intentionBehindResponse" in out
    assert out["engagementDurationSeconds"] >= 0
    assert 0 <= out["intelligenceValueRemaining"] <= 1.0


def test_strategic_agent_mid_stage():
    """Mid stage -> INTELLIGENCE_GATHERING or PII_HARVEST."""
    agent = StrategicAgent()
    kill_chain = {
        "currentStage": 3,
        "stageName": "UPI ID Harvesting",
        "killChainCompletion": 50.0,
        "stageObjective": "Collect UPI ID",
    }
    out = agent.process(kill_chain, {"totalMessagesExchanged": 5}, scam_confidence=0.9)
    assert out["userEngagementPhase"] in ("INTELLIGENCE_GATHERING", "PII_HARVEST")
    assert out["personaUsed"] in PERSONAS


def test_strategic_agent_terminate():
    """Kill-chain completion >= 95 -> TERMINATE."""
    agent = StrategicAgent()
    kill_chain = {
        "currentStage": 6,
        "stageName": "Complete",
        "killChainCompletion": 100.0,
        "stageObjective": "Done",
    }
    out = agent.process(kill_chain, {}, scam_confidence=0.95)
    assert out["recommendedNextAction"] == "TERMINATE"
    assert out["userEngagementPhase"] == "TERMINATION_PHASE"
    assert "Disengage" in out["intentionBehindResponse"] or "do not share" in out["intentionBehindResponse"].lower()


def test_strategic_agent_intelligence_remaining():
    """More extracted intelligence -> lower intelligenceValueRemaining."""
    agent = StrategicAgent()
    kill_chain = {"currentStage": 1, "killChainCompletion": 10.0, "stageName": "X", "stageObjective": "Y"}
    empty_session = {}
    rich_session = {
        "extractedIntelligence": {
            "identityMarkers": {"phoneNumbers": ["1"], "emailAddresses": ["a@b.com"], "upiIds": ["x@ybl"], "bankAccounts": []},
            "infrastructure": {"phishingUrls": ["http://x.com"], "phishingDomains": ["x.com"]},
        }
    }
    out_empty = agent.process(kill_chain, empty_session, scam_confidence=0.7)
    out_rich = agent.process(kill_chain, rich_session, scam_confidence=0.7)
    assert out_rich["intelligenceValueRemaining"] <= out_empty["intelligenceValueRemaining"]


def test_strategic_agent_duration():
    """Session with sessionStartTime -> engagementDurationSeconds > 0 when in past."""
    agent = StrategicAgent()
    kill_chain = {"currentStage": 1, "killChainCompletion": 10.0, "stageName": "X", "stageObjective": "Y"}
    past = datetime.now(timezone.utc) - timedelta(seconds=120)
    session = {"sessionStartTime": past, "totalMessagesExchanged": 2}
    out = agent.process(kill_chain, session, scam_confidence=0.7)
    assert out["engagementDurationSeconds"] >= 100
    assert out["totalMessagesExchanged"] == 2




def test_strategic_agent_process_contract():
    """Output has all fields required by EngagementMetrics + PDF output structure."""
    agent = StrategicAgent()
    out = agent.process(
        {"currentStage": 2, "killChainCompletion": 33.0, "stageName": "Authority", "stageObjective": "Establish"},
        {"totalMessagesExchanged": 3},
        scam_confidence=0.85,
    )
    required = [
        "userEngagementPhase", "recommendedNextAction", "personaUsed", "intentionBehindResponse",
        "engagementDurationSeconds", "totalMessagesExchanged", "intelligenceValueRemaining",
        "sophisticationLevel", "repetitionDetected", "suspicionDetected",
        "personaDetails", "adaptiveFlags", "missingIntelligenceTargets", "priorityIntelligenceTarget",
        "intelligenceExtractionPrompts", "safetyConstraints", "confidenceScore",
    ]
    for k in required:
        assert k in out, f"Missing key: {k}"
    assert out["userEngagementPhase"] in ENGAGEMENT_PHASES
    assert out["recommendedNextAction"] in ("CONTINUE_ENGAGEMENT", "TERMINATE", "HUMAN_REVIEW")
    assert out["personaUsed"] in PERSONAS
    assert 0 <= out["confidenceScore"] <= 1.0


def test_strategic_agent_persona_consistency():
    """PDF Step 2: Persona should be consistent across turns unless suspicion."""
    agent = StrategicAgent()
    kc1 = {"currentStage": 1, "killChainCompletion": 16.67, "stageName": "Urgency", "stageObjective": "X"}
    kc2 = {"currentStage": 2, "killChainCompletion": 33.33, "stageName": "Authority", "stageObjective": "Y"}
    out1 = agent.process(kc1, {"totalMessagesExchanged": 0}, scam_confidence=0.8)
    persona1 = out1["personaUsed"]
    session_turn2 = {
        "totalMessagesExchanged": 2,
        "lastPersona": persona1,
        "conversationHistory": [
            {"sender": "scammer", "text": "Your UPI will be blocked"},
            {"sender": "user", "text": "What should I do?"},
        ],
    }
    out2 = agent.process(kc2, session_turn2, scam_confidence=0.8)
    assert out2["personaUsed"] == persona1, "Persona should be consistent when no suspicion"


def test_strategic_agent_scam_type_specific_intention():
    """Scam-type-specific objectives (Issue 3): UPI_FRAUD vs INVESTMENT_SCAM."""
    agent = StrategicAgent()
    kc = {"currentStage": 3, "killChainCompletion": 50.0, "stageName": "X", "stageObjective": "Y"}
    out_upi = agent.process(kc, {}, scam_confidence=0.8, scam_type="UPI_FRAUD")
    out_inv = agent.process(kc, {}, scam_confidence=0.8, scam_type="INVESTMENT_SCAM")
    assert "UPI" in out_upi["intentionBehindResponse"] or "verify" in out_upi["intentionBehindResponse"].lower()
    assert "invest" in out_inv["intentionBehindResponse"].lower() or "willingness" in out_inv["intentionBehindResponse"].lower() or "small" in out_inv["intentionBehindResponse"].lower()


def test_strategic_agent_sophistication_and_safety():
    """Sophistication affects persona (Issue 1); CONFIRMATION never recommends OTP (Issue 7)."""
    agent = StrategicAgent()
    kc = {"currentStage": 5, "killChainCompletion": 83.0, "stageName": "OTP", "stageObjective": "Extract OTP"}
    out = agent.process(kc, {}, scam_confidence=0.9, scammer_message="Share your OTP to verify")
    assert "OTP" not in out["intentionBehindResponse"] or "Do not share" in out["intentionBehindResponse"] or "do not" in out["intentionBehindResponse"].lower()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
