"""
Day 5 Engineer 2: Full 5-agent orchestration pipeline.

REQUEST → [1.Detect] → [2.KillChain] → [3.Strategy] → [4.Engage] → [5.Ethics] → RESPONSE
           ↓ session       ↓ session      ↓ persona     ↓ LLM       ↓ safety check
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from api.schemas import (
    HoneypotRequest,
    HoneypotResponse,
    EngagementMetrics,
    AgentResponse,
    ExtractedIntelligence,
    KillChainAnalysis,
    IdentityMarkers,
    Infrastructure,
    PsychologicalTactics,
)
from memory.session_manager import load_session, save_session
from memory.schemas import SessionMemory
from utils.intelligence_accumulator import IntelligenceAccumulator

logger = logging.getLogger(__name__)


def _request_history_to_dict_list(request: HoneypotRequest) -> List[Dict[str, Any]]:
    """Convert request.conversationHistory (List[Message]) to list of {sender, text, timestamp}."""
    out = []
    for m in request.conversationHistory:
        ts = getattr(m, "timestamp", None) or datetime.now()
        out.append({"sender": m.sender, "text": m.text, "timestamp": ts})
    return out


def _session_to_strategy_dict(session: SessionMemory) -> Dict[str, Any]:
    """Build session_memory dict for StrategicAgent.process()."""
    return {
        "conversationHistory": list(session.conversationHistory),
        "extractedIntelligence": session.extractedIntelligence,
        "scamType": session.scamType,
        "totalMessagesExchanged": session.totalMessagesExchanged,
        "lastPersona": (session.scammerProfile or {}).get("lastPersona"),
        "killChainState": session.killChainState,
    }


def should_terminate_session(session: SessionMemory, killchain_result: Dict[str, Any]) -> bool:
    """4 termination triggers - protects honeypot integrity."""
    if not session.conversationHistory:
        return False
    last_text = (session.conversationHistory[-1].get("text") or "").lower()
    return any([
        session.totalMessagesExchanged >= 20,
        int(killchain_result.get("currentStage", 0)) >= 6,
        "are you a bot" in last_text or "are you bot" in last_text,
        float(killchain_result.get("killChainCompletion", 0)) >= 95.0,
    ])


def _dict_to_extracted_intelligence(d: Dict[str, Any]) -> ExtractedIntelligence:
    """Build Pydantic ExtractedIntelligence from merged dict."""
    im = d.get("identityMarkers") or {}
    inf = d.get("infrastructure") or {}
    pt = d.get("psychologicalTactics") or {}
    return ExtractedIntelligence(
        identityMarkers=IdentityMarkers(
            phoneNumbers=im.get("phoneNumbers", []),
            emailAddresses=im.get("emailAddresses", []),
            bankAccounts=im.get("bankAccounts", []),
            upiIds=im.get("upiIds", []),
            deviceFingerprints=im.get("deviceFingerprints", []),
        ),
        infrastructure=Infrastructure(
            phishingDomains=inf.get("phishingDomains", []),
            phishingUrls=inf.get("phishingUrls", []),
            suspiciousGateways=inf.get("suspiciousGateways", []),
        ),
        psychologicalTactics=PsychologicalTactics(
            urgencyExploitation=pt.get("urgencyExploitation", []),
            authorityMimicry=pt.get("authorityMimicry", []),
            threatPatterns=pt.get("threatPatterns", []),
            scarcityTactics=pt.get("scarcityTactics", []),
        ),
        suspiciousKeywords=d.get("suspiciousKeywords", []),
    )


def _kill_result_to_analysis(killchain_result: Dict[str, Any], scam_type: str) -> KillChainAnalysis:
    """Map kill chain analyze_message output to KillChainAnalysis schema."""
    return KillChainAnalysis(
        detectedScamType=scam_type or "UPI_FRAUD",
        estimatedKillChainStep=int(killchain_result.get("currentStage", 1)),
        stageName=killchain_result.get("stageName", ""),
        stageObjective=killchain_result.get("stageObjective", ""),
        nextPredictedStep=int(killchain_result.get("nextPredictedStage", 2)),
        killChainCompletion=float(killchain_result.get("killChainCompletion", 0.0)),
    )


def _strategy_to_engagement_metrics(strategy: Dict[str, Any], session: SessionMemory) -> EngagementMetrics:
    """Map strategy output to EngagementMetrics schema."""
    action = strategy.get("recommendedNextAction", "CONTINUE_ENGAGEMENT")
    if action not in ("CONTINUE_ENGAGEMENT", "TERMINATE", "HUMAN_REVIEW"):
        action = "CONTINUE_ENGAGEMENT"
    return EngagementMetrics(
        engagementDurationSeconds=int(strategy.get("engagementDurationSeconds", 0)),
        totalMessagesExchanged=session.totalMessagesExchanged,
        userEngagementPhase=strategy.get("userEngagementPhase", "CREDIBILITY_ESTABLISHMENT"),
        intelligenceValueRemaining=float(strategy.get("intelligenceValueRemaining", 0.75)),
        recommendedNextAction=action,
    )


def create_non_scam_response(request: HoneypotRequest, detection_result: Dict[str, Any]) -> HoneypotResponse:
    """When scam not detected, return minimal success response."""
    return HoneypotResponse(
        status="success",
        scamDetected=False,
        scamConfidenceScore=float(detection_result.get("scamScore", 0.0)),
        engagementMetrics=EngagementMetrics(
            engagementDurationSeconds=0,
            totalMessagesExchanged=0,
            userEngagementPhase="CREDIBILITY_ESTABLISHMENT",
            intelligenceValueRemaining=1.0,
            recommendedNextAction="CONTINUE_ENGAGEMENT",
        ),
        extractedIntelligence=ExtractedIntelligence(),
        agentResponse=AgentResponse(
            message="Thanks for your message. I'll get back to you.",
            responseGeneratedBy="DETECTION_AGENT",
            personaUsed="NONE",
            intentionBehindResponse="Non-scam; minimal response",
        ),
        agentNotes="No scam detected. Minimal response sent.",
    )


def create_termination_response(
    session: SessionMemory,
    strategy: Dict[str, Any],
    final_message: str,
    response_generated_by: str,
    persona_used: str,
    intention: str,
    killchain_analysis: KillChainAnalysis,
    extracted_intel: ExtractedIntelligence,
) -> HoneypotResponse:
    """Build response when session is terminating."""
    action = strategy.get("recommendedNextAction", "TERMINATE")
    if action not in ("CONTINUE_ENGAGEMENT", "TERMINATE", "HUMAN_REVIEW"):
        action = "TERMINATE"
    return HoneypotResponse(
        status="success",
        scamDetected=True,
        scamConfidenceScore=0.85,
        engagementMetrics=EngagementMetrics(
            engagementDurationSeconds=int(strategy.get("engagementDurationSeconds", 0)),
            totalMessagesExchanged=session.totalMessagesExchanged,
            userEngagementPhase=strategy.get("userEngagementPhase", "TERMINATION_PHASE"),
            intelligenceValueRemaining=float(strategy.get("intelligenceValueRemaining", 0.0)),
            recommendedNextAction=action,
        ),
        killChainAnalysis=killchain_analysis,
        extractedIntelligence=extracted_intel,
        agentResponse=AgentResponse(
            message=final_message,
            responseGeneratedBy=response_generated_by,
            personaUsed=persona_used,
            intentionBehindResponse=intention,
        ),
        agentNotes="Session terminated. Intelligence extracted.",
    )


def process_message(request: HoneypotRequest, agents: Dict[str, Any]) -> HoneypotResponse:
    """
    Day 5 Engineer 2: 5-agent orchestration - Detection → KillChain → Strategy → Engagement → Ethics.
    Extraction and intelligence merge; session load/save; termination check.
    """
    session_id = request.sessionId
    scammer_text = request.message.text.strip()
    channel = (request.metadata.channel if request.metadata else None) or "SMS"
    history_list = _request_history_to_dict_list(request)

    # STEP 0: Load session
    session = load_session(session_id)
    if not session.scammerProfile:
        session.scammerProfile = {}

    # STEP 1: Detection
    detection_agent = agents.get("detection")
    detection_result = detection_agent.analyze(scammer_text, channel) if detection_agent else {
        "scamDetected": True, "scamScore": 0.85, "scamType": "UPI_FRAUD",
    }
    if not detection_result.get("scamDetected"):
        return create_non_scam_response(request, detection_result)

    scam_type = detection_result.get("scamType") or "UPI_FRAUD"
    scam_confidence = float(detection_result.get("scamScore", 0.85))

    # STEP 2: Kill chain
    get_kill_chain = agents.get("get_kill_chain")
    if not get_kill_chain:
        from kill_chains import get_kill_chain as _get_kc
        get_kill_chain = _get_kc
    llm_client = agents.get("llm_client")
    kc = get_kill_chain(scam_type, llm_client=llm_client)
    # Restore state from session
    if session.killChainState and isinstance(session.killChainState, dict):
        kc.current_stage = session.killChainState.get("currentStage", 1)
        kc.stage_history = list(session.killChainState.get("stageHistory", [1]))
    killchain_result = kc.analyze_message(scammer_text, conversation_history=history_list)
    session.killChainState = killchain_result

    # STEP 3: Strategy
    strategy_agent = agents.get("strategy")
    session_dict = _session_to_strategy_dict(session)
    strategy = strategy_agent.process(
        killchain_result,
        session_memory=session_dict,
        scam_confidence=scam_confidence,
        scam_type=scam_type,
        scammer_message=scammer_text,
    ) if strategy_agent else {
        "personaUsed": "AVERAGE_USER",
        "recommendedNextAction": "CONTINUE_ENGAGEMENT",
        "userEngagementPhase": "CREDIBILITY_ESTABLISHMENT",
        "engagementDurationSeconds": 0,
        "intelligenceValueRemaining": 0.75,
        "intentionBehindResponse": "Engage naturally",
    }
    session.scammerProfile["lastPersona"] = strategy.get("personaUsed")

    # STEP 4: Engagement
    engagement_agent = agents.get("engagement")
    engagement_result = engagement_agent.generate_response(
        scammer_message=scammer_text,
        strategy=strategy,
        conversation_history=history_list,
    ) if engagement_agent else {"response": "I'm concerned about this. Can you provide more details?", "method": "FALLBACK"}
    planned_response = engagement_result.get("response", "I need to think about this. Let me check.")

    # STEP 5: Ethics
    ethics_agent = agents.get("ethics")
    is_valid, reason, details = ethics_agent.validate(planned_response) if ethics_agent else (True, "APPROVED", {})
    if not is_valid:
        logger.warning("Ethics violation: %s - %s", reason, planned_response[:50])
        planned_response = details.get("safeAlternative", "I need to think about this. Let me check.")
        response_generated_by = "ETHICS_AGENT_FALLBACK"
        persona_used = "SAFE_USER"
        intention = f"Ethics violation prevented: {reason}"
    else:
        response_generated_by = engagement_result.get("method", "ENGAGEMENT_AGENT").replace("LLM_VALIDATED", "ENGAGEMENT_AGENT").replace("EMERGENCY_FALLBACK", "ENGAGEMENT_AGENT")
        persona_used = strategy.get("personaUsed", "AVERAGE_USER")
        intention = strategy.get("intentionBehindResponse", "Engage naturally")

    # STEP 6: Extraction + merge intelligence
    extraction_agent = agents.get("extraction")
    new_intel = extraction_agent.extract_intelligence(scammer_text, scam_type=scam_type) if extraction_agent else session.extractedIntelligence
    merged_intel = IntelligenceAccumulator.merge_intelligence(
        session.extractedIntelligence,
        new_intel,
    )
    session.extractedIntelligence = merged_intel

    # STEP 7: Update session
    session.conversationHistory.append({"sender": "scammer", "text": scammer_text, "timestamp": datetime.now()})
    session.conversationHistory.append({"sender": "user", "text": planned_response, "timestamp": datetime.now()})
    session.totalMessagesExchanged += 1
    session.scamType = scam_type
    save_session(session_id, session)

    # STEP 8: Termination check
    if should_terminate_session(session, killchain_result):
        killchain_analysis = _kill_result_to_analysis(killchain_result, scam_type)
        extracted_pydantic = _dict_to_extracted_intelligence(merged_intel)
        return create_termination_response(
            session, strategy, planned_response, response_generated_by, persona_used, intention,
            killchain_analysis, extracted_pydantic,
        )

    # STEP 9: Build GUVI-compliant response
    killchain_analysis = _kill_result_to_analysis(killchain_result, scam_type)
    extracted_pydantic = _dict_to_extracted_intelligence(merged_intel)
    engagement_metrics = _strategy_to_engagement_metrics(strategy, session)
    notes = "Scam detected. Continuing engagement to extract intelligence."
    if response_generated_by == "ETHICS_AGENT_FALLBACK":
        notes = f"Ethics gate applied ({reason}). Safe fallback sent."

    return HoneypotResponse(
        status="success",
        scamDetected=True,
        scamConfidenceScore=scam_confidence,
        engagementMetrics=engagement_metrics,
        killChainAnalysis=killchain_analysis,
        extractedIntelligence=extracted_pydantic,
        agentResponse=AgentResponse(
            message=planned_response,
            responseGeneratedBy=response_generated_by,
            personaUsed=persona_used,
            intentionBehindResponse=intention,
        ),
        agentNotes=notes,
    )
