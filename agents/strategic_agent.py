"""
Strategic Agent - Engagement strategy based on kill-chain and session context.

Addresses all 7 critical issues from StrategicAgent PDF:
1. Multi-dimensional sophistication assessment (not just 4 keywords + caps)
2. Scam-type-aware strategy (no generic one-size-fits-all)
3. Scam-type-specific stage objectives (e.g. UPI vs investment vs phishing)
4. Context awareness (conversation history, extracted intel, persona consistency)
5. Intelligence extraction strategy (priority targets per scam type)
6. Adaptive behavior (repetition/suspicion detection, strategy pivot)
7. Safety validation (never recommend OTP/PIN/password; stage-based constraints)

Aligns with api.schemas.EngagementMetrics and AgentResponse.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Engagement phases (aligned with GUVI / honeypot evaluation)
ENGAGEMENT_PHASES = [
    "CREDIBILITY_ESTABLISHMENT",
    "INTELLIGENCE_GATHERING",
    "PII_HARVEST",
    "CONFIRMATION",
    "TERMINATION_PHASE",
]

PERSONAS = [
    "AVERAGE_USER",
    "CAUTIOUS_USER",
    "VULNERABLE_USER",
    "SKEPTICAL_USER",
]

# Persona details (PDF Section 4.3: Enhanced Persona Definition)
PERSONA_DETAILS: Dict[str, Dict[str, str]] = {
    "AVERAGE_USER": {
        "description": "Normal user, slightly curious, follows instructions with mild hesitation",
        "response_style": "Asks clarifying questions; does not share sensitive data immediately",
    },
    "CAUTIOUS_USER": {
        "description": "Hesitant, asks for proof and official channels",
        "response_style": "Requests verification; delays sharing until convinced",
    },
    "VULNERABLE_USER": {
        "description": "Anxious, less tech-savvy, may appear compliant",
        "response_style": "Shows concern; asks for step-by-step guidance; use sparingly",
    },
    "SKEPTICAL_USER": {
        "description": "Doubts legitimacy; asks for evidence",
        "response_style": "Challenges claims; asks for official link or number",
    },
}

STAGE_TO_PHASE = {
    1: "CREDIBILITY_ESTABLISHMENT",
    2: "CREDIBILITY_ESTABLISHMENT",
    3: "INTELLIGENCE_GATHERING",
    4: "PII_HARVEST",
    5: "PII_HARVEST",
    6: "CONFIRMATION",
}

COMPLETION_TERMINATE = 95.0
COMPLETION_HUMAN_REVIEW = 80.0
INTELLIGENCE_LOW = 0.3

# --- Issue 3: Scam-type-specific stage objectives (not generic) ---
SCAM_TYPE_STAGE_OBJECTIVES: Dict[str, Dict[int, str]] = {
    "UPI_FRAUD": {
        1: "Acknowledge urgency about UPI/KYC; ask who is contacting; do not share UPI ID.",
        2: "Show confusion about which bank/entity; request official link or number.",
        3: "Appear willing to verify but ask how to confirm it is NPCI/bank; do not share UPI ID yet.",
        4: "Ask what the Rs 1 request is for; delay sharing any ID until verified.",
        5: "Do not share OTP or verification code; ask for alternative verification method.",
        6: "Do not confirm transaction; disengage if they insist on OTP.",
    },
    "ACCOUNT_TAKEOVER": {
        1: "Acknowledge account concern; ask which account and from where they are contacting.",
        2: "Request official channel (app/website) to verify; do not share login details.",
        3: "Show hesitation; ask for customer care number from official site.",
        4: "Do not share OTP or password; ask for alternative verification.",
        5: "Do not share OTP; suggest visiting branch or official app.",
        6: "Do not confirm account restored; disengage if they ask for OTP.",
    },
    "PHISHING": {
        1: "Acknowledge link/message; do not click; ask what organization this is from.",
        2: "Do not enter credentials; ask for official website or phone number.",
        3: "Do not share login details; suggest verifying via official app or branch.",
    },
    "INVESTMENT_SCAM": {
        1: "Show mild interest in returns; ask which company and how to verify.",
        2: "Ask for company name, registration; do not share bank or UPI yet.",
        3: "Show willingness to invest small amount; ask about guarantees and withdrawal process.",
        4: "Ask how to withdraw and what fees; do not share OTP or payment yet.",
        5: "Do not pay upgrade or GST fee; ask for official invoice or portal.",
        6: "Do not share OTP or pay unlock fee; disengage if pressured.",
    },
    "FAKE_CUSTOMER_SUPPORT": {
        1: "Acknowledge service issue; ask for ticket number or official channel.",
        2: "Request callback from number on official website; do not share OTP.",
        3: "Do not install remote app or share screen; ask for alternative.",
        4: "Do not pay service fee; ask for official bill or portal.",
    },
    "FAKE_OFFER": {
        1: "Show curiosity about offer; ask how to verify it is from company.",
        2: "Do not share PAN/mobile yet; ask for official link or email.",
        3: "Do not pay processing fee; ask for terms and official channel.",
    },
}

# --- Issue 5: Intelligence extraction strategy (priority targets per scam type) ---
SCAM_TYPE_INTELLIGENCE_TARGETS: Dict[str, List[str]] = {
    "UPI_FRAUD": ["upiIds", "phoneNumbers", "bankAccounts", "phishingUrls"],
    "ACCOUNT_TAKEOVER": ["phoneNumbers", "phishingUrls", "phishingDomains"],
    "PHISHING": ["phishingUrls", "phishingDomains"],
    "INVESTMENT_SCAM": ["phoneNumbers", "upiIds", "phishingUrls", "bankAccounts"],
    "FAKE_CUSTOMER_SUPPORT": ["phoneNumbers", "phishingUrls"],
    "FAKE_OFFER": ["phoneNumbers", "emailAddresses", "phishingUrls"],
}

# --- Issue 7: Safety - never recommend sharing these ---
SAFETY_BLOCKED_PHRASES = [
    "share otp", "provide otp", "enter otp", "send otp", "give otp",
    "share pin", "provide pin", "enter pin", "send pin",
    "share password", "provide password", "enter password",
    "share verification code", "provide verification code",
]
CONFIRMATION_STAGE_SAFE_INTENTION = "Do not share OTP or codes; ask for alternative verification."

# --- Issue 6: Suspicion / repetition detection ---
SUSPICION_KEYWORDS = ["real?", "bot?", "human?", "fake?", "scam?", "who are you?", "legit?", "genuine?"]
REPETITION_WINDOW = 3  # last N scammer messages to check for repetition


class StrategicAgent(BaseAgent):
    """
    Plans engagement strategy from kill-chain, session context, and scam type.
    Addresses PDF issues: sophistication, scam-type specialization, context,
    intel targets, adaptive detection, safety validation.
    """

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        self.llm_client = llm_client

    def process(
        self,
        kill_chain_result: Dict[str, Any],
        session_memory: Optional[Dict[str, Any]] = None,
        scam_confidence: float = 0.0,
        scam_type: Optional[str] = None,
        scammer_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute engagement strategy. Uses conversation history and extracted
        intelligence from session_memory (Issue 4); scam_type for specialized
        objectives (Issue 2, 3) and intel targets (Issue 5); scammer_message
        for sophistication (Issue 1). Applies repetition/suspicion detection
        (Issue 6) and safety validation (Issue 7).
        """
        session_memory = session_memory or {}
        kc = kill_chain_result
        current_stage = int(kc.get("currentStage", 1))
        completion = float(kc.get("killChainCompletion", 0.0))
        stage_name = kc.get("stageName", "")
        stage_objective = kc.get("stageObjective", "")
        scam_type = (scam_type or session_memory.get("scamType") or "UPI_FRAUD").upper().replace(" ", "_")

        # --- Issue 6: Adaptive - repetition / suspicion ---
        conversation_history = session_memory.get("conversationHistory") or []
        repetition_detected = self._detect_repetition(conversation_history)
        suspicion_detected = self._detect_suspicion(conversation_history, scammer_message or "")

        # --- Issue 1: Multi-dimensional sophistication (not just 4 keywords) ---
        sophistication_level, sophistication_confidence = self._assess_sophistication(
            scammer_message or ""
        )

        # Phase from stage
        user_engagement_phase = STAGE_TO_PHASE.get(current_stage, ENGAGEMENT_PHASES[0])
        if completion >= 99.0:
            user_engagement_phase = "TERMINATION_PHASE"

        # --- Persona: use sophistication + stage + context; maintain consistency (PDF Step 2) ---
        last_persona = session_memory.get("lastPersona")
        persona_used = self._select_persona(
            current_stage, completion, session_memory, sophistication_level,
            last_persona=last_persona, suspicion_detected=suspicion_detected,
        )

        # --- Next action: add pivot on repetition/suspicion (Issue 6) ---
        recommended_next_action = self._recommend_action(
            completion, scam_confidence, session_memory, current_stage, scam_type,
            repetition_detected=repetition_detected, suspicion_detected=suspicion_detected,
        )

        # --- Issue 3 + 5: Scam-type-specific intention + intel targets ---
        intention = self._build_intention(
            scam_type=scam_type,
            current_stage=current_stage,
            user_engagement_phase=user_engagement_phase,
            stage_name=stage_name,
            stage_objective=stage_objective,
            action=recommended_next_action,
            persona=persona_used,
            session_memory=session_memory,
        )

        # --- Issue 7: Safety validation - never recommend OTP/PIN/password ---
        intention = self._validate_safety(intention, current_stage)

        total_messages = int(session_memory.get("totalMessagesExchanged", 0))
        intelligence_remaining = self._intelligence_value_remaining(session_memory, scam_type)
        duration_seconds = self._engagement_duration_seconds(session_memory)

        # --- PDF: Intelligence gap (missing targets + priority) ---
        missing_intel, priority_target = self._intelligence_gap(session_memory, scam_type)
        extraction_prompts = self._intelligence_extraction_prompts(
            scam_type, current_stage, priority_target
        )
        safety_constraints = self._safety_constraints_list(current_stage)

        # --- PDF Step 7: Confidence score (explainable) ---
        confidence_score = self._confidence_calculation(
            sophistication_confidence, persona_used, current_stage,
            repetition_detected, suspicion_detected,
        )

        return {
            "userEngagementPhase": user_engagement_phase,
            "recommendedNextAction": recommended_next_action,
            "personaUsed": persona_used,
            "personaDetails": PERSONA_DETAILS.get(persona_used, {}),
            "intentionBehindResponse": intention,
            "engagementDurationSeconds": duration_seconds,
            "totalMessagesExchanged": total_messages,
            "intelligenceValueRemaining": round(intelligence_remaining, 2),
            "currentStage": current_stage,
            "killChainCompletion": completion,
            "stageName": stage_name,
            "sophisticationLevel": sophistication_level,
            "sophisticationConfidence": round(sophistication_confidence, 2),
            "repetitionDetected": repetition_detected,
            "suspicionDetected": suspicion_detected,
            "adaptiveFlags": {
                "scammerSuspicionDetected": suspicion_detected,
                "repetitionDetected": repetition_detected,
            },
            "missingIntelligenceTargets": missing_intel,
            "priorityIntelligenceTarget": priority_target,
            "intelligenceExtractionPrompts": extraction_prompts,
            "safetyConstraints": safety_constraints,
            "confidenceScore": round(confidence_score, 2),
        }

    # --- Issue 1: Multi-dimensional sophistication assessment ---
    def _assess_sophistication(self, message: str) -> Tuple[str, float]:
        """
        Assess scammer sophistication (LOW/MEDIUM/HIGH) using grammar, caps,
        structure, length. Not just 4 keywords + caps ratio.
        """
        if not message or not message.strip():
            return "MEDIUM", 0.5
        text = message.strip().lower()
        score = 50.0
        # Grammar / informal indicators (multiple dimensions)
        grammar_indicators = [
            ("ur", -8), (" u ", -5), ("plz", -6), ("pls", -5), ("2day", -4),
            ("thru", -3), ("gr8", -4), ("r u ", -5), ("wat", -4), ("dont", -2),
            ("cant", -2), ("wont", -2), ("u will", -3), ("kindly do the needful", 5),
        ]
        for pattern, delta in grammar_indicators:
            if pattern in text:
                score += delta
        # Caps ratio
        if len(message) > 0:
            caps_ratio = sum(1 for c in message if c.isupper()) / len(message)
            if caps_ratio > 0.4:
                score -= 15
            elif caps_ratio > 0.2:
                score -= 5
        # Structure: very short or single block = often lower sophistication
        words = message.split()
        if len(words) >= 15 and "." in message:
            score += 5
        if len(words) <= 3 and not message.endswith("?"):
            score -= 5
        score = max(0, min(100, score))
        if score >= 65:
            return "HIGH", min(0.95, 0.5 + score / 200)
        if score >= 40:
            return "MEDIUM", min(0.85, 0.4 + score / 150)
        return "LOW", min(0.8, 0.3 + score / 100)

    # --- Issue 6: Repetition detection ---
    def _detect_repetition(self, conversation_history: List[Dict]) -> bool:
        """True if last N scammer messages are very similar (stalling)."""
        scammer_texts = []
        for m in conversation_history[- (REPETITION_WINDOW * 2) :]:
            if isinstance(m, dict) and m.get("sender") == "scammer":
                t = (m.get("text") or "").strip()
                if t:
                    scammer_texts.append(t)
        if len(scammer_texts) < 2:
            return False
        last = scammer_texts[-1].lower()
        for prev in scammer_texts[-REPETITION_WINDOW:-1]:
            if prev.lower() == last or (len(last) > 10 and prev.lower() in last):
                return True
        return False

    # --- Issue 6: Suspicion detection ---
    def _detect_suspicion(self, conversation_history: List[Dict], current_message: str) -> bool:
        """True if user (we) or scammer message suggests suspicion (e.g. 'are you real?')."""
        combined = current_message.lower()
        for m in conversation_history[-5:]:
            if isinstance(m, dict):
                combined += " " + (m.get("text") or "").lower()
        return any(kw in combined for kw in SUSPICION_KEYWORDS)

    def _select_persona(
        self,
        current_stage: int,
        completion: float,
        session_memory: Dict[str, Any],
        sophistication_level: str = "MEDIUM",
        last_persona: Optional[str] = None,
        suspicion_detected: bool = False,
    ) -> str:
        """Select persona; maintain consistency across turns unless suspicion (PDF Step 2)."""
        total = int(session_memory.get("totalMessagesExchanged", 0))
        # First turn or no history: choose from sophistication + stage
        if last_persona is None or total == 0:
            base = self._base_persona_for_context(current_stage, sophistication_level, total)
            return base
        # Later turns: maintain persona unless scammer shows suspicion (allow slight pivot)
        if suspicion_detected:
            return "CAUTIOUS_USER" if current_stage <= 4 else last_persona
        return last_persona

    def _base_persona_for_context(
        self, current_stage: int, sophistication_level: str, total: int
    ) -> str:
        """Base persona from stage and sophistication (used when no last_persona)."""
        if sophistication_level == "LOW":
            return "VULNERABLE_USER" if current_stage <= 2 else "AVERAGE_USER"
        if sophistication_level == "HIGH":
            return "SKEPTICAL_USER" if current_stage <= 4 else "CAUTIOUS_USER"
        if current_stage <= 2:
            return "AVERAGE_USER"
        if current_stage <= 4:
            if total % 3 == 0:
                return "CAUTIOUS_USER"
            return "SKEPTICAL_USER" if total % 2 == 0 else "AVERAGE_USER"
        return "AVERAGE_USER"

    def _recommend_action(
        self,
        completion: float,
        scam_confidence: float,
        session_memory: Dict[str, Any],
        current_stage: int,
        scam_type: str = "UPI_FRAUD",
        repetition_detected: bool = False,
        suspicion_detected: bool = False,
    ) -> str:
        """Recommend action; pivot to HUMAN_REVIEW on repetition/suspicion (Issue 6)."""
        if repetition_detected or suspicion_detected:
            return "HUMAN_REVIEW"
        if completion >= COMPLETION_TERMINATE:
            return "TERMINATE"
        if completion >= COMPLETION_HUMAN_REVIEW and scam_confidence >= 0.9:
            return "HUMAN_REVIEW"
        intelligence_remaining = self._intelligence_value_remaining(session_memory, scam_type)
        if intelligence_remaining > INTELLIGENCE_LOW and completion < 50.0:
            return "CONTINUE_ENGAGEMENT"
        if completion >= 70.0 and scam_confidence < 0.5:
            return "HUMAN_REVIEW"
        return "CONTINUE_ENGAGEMENT"

    def _build_intention(
        self,
        scam_type: str,
        current_stage: int,
        user_engagement_phase: str,
        stage_name: str,
        stage_objective: str,
        action: str,
        persona: str,
        session_memory: Dict[str, Any],
    ) -> str:
        """Scam-type and stage-specific intention + intel targets (Issue 3, 5)."""
        if action == "TERMINATE":
            return "Disengage politely; do not share further details."
        if action == "HUMAN_REVIEW":
            return "Stay neutral; avoid committing; flag for human review."
        # Scam-type-specific objective (Issue 3)
        type_map = SCAM_TYPE_STAGE_OBJECTIVES.get(scam_type) or SCAM_TYPE_STAGE_OBJECTIVES.get("UPI_FRAUD", {})
        specific = type_map.get(current_stage)
        if specific:
            return specific
        # Fallback with intel targets hint (Issue 5)
        targets = SCAM_TYPE_INTELLIGENCE_TARGETS.get(scam_type, ["phoneNumbers", "phishingUrls"])
        targets_hint = "Elicit " + ", ".join(targets[:2]) + " without sharing own. "
        if user_engagement_phase == "CREDIBILITY_ESTABLISHMENT":
            return targets_hint + "Show mild concern; ask who they are; do not share personal details."
        if user_engagement_phase == "INTELLIGENCE_GATHERING":
            return targets_hint + "Ask clarifying questions; do not share links or contact yet."
        if user_engagement_phase == "PII_HARVEST":
            return targets_hint + "Appear willing but delay; ask for proof or official link."
        if user_engagement_phase == "CONFIRMATION":
            return CONFIRMATION_STAGE_SAFE_INTENTION
        return f"Match phase {user_engagement_phase}; avoid sharing sensitive data."

    def _intelligence_gap(self, session_memory: Dict[str, Any], scam_type: str) -> Tuple[List[str], Optional[str]]:
        """PDF Step 3: Missing intelligence targets and priority (what to extract next)."""
        extracted = session_memory.get("extractedIntelligence") or {}
        identity = extracted.get("identityMarkers") or {}
        infra = extracted.get("infrastructure") or {}
        targets = SCAM_TYPE_INTELLIGENCE_TARGETS.get(scam_type, ["phoneNumbers", "phishingUrls"])
        missing = []
        for t in targets:
            count = 0
            if t == "phoneNumbers":
                count = len(identity.get("phoneNumbers", []))
            elif t == "emailAddresses":
                count = len(identity.get("emailAddresses", []))
            elif t == "upiIds":
                count = len(identity.get("upiIds", []))
            elif t == "bankAccounts":
                count = len(identity.get("bankAccounts", []))
            elif t == "phishingUrls":
                count = len(infra.get("phishingUrls", []))
            elif t == "phishingDomains":
                count = len(infra.get("phishingDomains", []))
            if count == 0:
                missing.append(t)
        priority = missing[0] if missing else None
        return missing, priority

    def _intelligence_extraction_prompts(
        self, scam_type: str, current_stage: int, priority_target: Optional[str]
    ) -> List[str]:
        """PDF Step 4: Suggested prompts to elicit priority intelligence (e.g. 'Ask: What UPI ID...')."""
        if not priority_target:
            return []
        prompts = []
        if priority_target == "upiIds":
            prompts.append("Ask: 'What UPI ID should I use to send/receive?' or 'Which UPI app do you use?'")
        elif priority_target == "phoneNumbers":
            prompts.append("Ask: 'Which number should I call to verify?' or 'What is the official helpline?'")
        elif priority_target == "phishingUrls":
            prompts.append("Ask: 'Can you send the official link?' or 'Where can I check this?'")
        elif priority_target == "phishingDomains":
            prompts.append("Ask: 'What is the official website?' or 'How do I verify the portal?'")
        elif priority_target == "emailAddresses":
            prompts.append("Ask: 'Which email should I use for verification?'")
        elif priority_target == "bankAccounts":
            prompts.append("Ask: 'Which bank account details do you need?' (do not share own)")
        return prompts[:2]

    def _safety_constraints_list(self, current_stage: int) -> List[str]:
        """PDF: Explicit safety constraints (never share OTP/PIN/password; stage-based)."""
        constraints = [
            "Never share OTP, PIN, or password.",
            "Never share real bank account or UPI ID.",
            "Do not install remote-access apps or share screen.",
        ]
        if current_stage >= 5:
            constraints.append("Do not share verification codes; ask for alternative method.")
        return constraints

    def _confidence_calculation(
        self,
        sophistication_confidence: float,
        persona: str,
        current_stage: int,
        repetition_detected: bool,
        suspicion_detected: bool,
    ) -> float:
        """PDF Step 7: Multi-factor strategy confidence (0–1)."""
        base = 0.75
        sophistication_component = sophistication_confidence * 0.15
        persona_believability = 0.95 if persona in PERSONAS else 0.7
        persona_component = persona_believability * 0.10
        late_stage_penalty = 0.0 if current_stage <= 4 else -0.05 * (current_stage - 4)
        if repetition_detected or suspicion_detected:
            base -= 0.15
        total = base + sophistication_component + persona_component + late_stage_penalty
        return max(0.0, min(1.0, total))

    # --- Issue 7: Safety validation ---
    def _validate_safety(self, intention: str, current_stage: int) -> str:
        """Never allow intention that recommends sharing OTP/PIN/password."""
        lower = intention.lower()
        for phrase in SAFETY_BLOCKED_PHRASES:
            if phrase in lower:
                return CONFIRMATION_STAGE_SAFE_INTENTION
        if current_stage >= 5:
            if any(w in lower for w in ["otp", "pin", "password", "verification code", "code"]):
                return CONFIRMATION_STAGE_SAFE_INTENTION
        return intention

    def _intelligence_value_remaining(self, session_memory: Dict[str, Any], scam_type: str) -> float:
        """Remaining intel value 0–1; considers priority targets for scam_type (Issue 5)."""
        extracted = session_memory.get("extractedIntelligence") or {}
        identity = extracted.get("identityMarkers") or {}
        infra = extracted.get("infrastructure") or {}
        targets = SCAM_TYPE_INTELLIGENCE_TARGETS.get(scam_type, ["phoneNumbers", "phishingUrls"])
        total_items = 0
        for t in targets:
            if t == "phoneNumbers":
                total_items += len(identity.get("phoneNumbers", []))
            elif t == "emailAddresses":
                total_items += len(identity.get("emailAddresses", []))
            elif t == "upiIds":
                total_items += len(identity.get("upiIds", []))
            elif t == "bankAccounts":
                total_items += len(identity.get("bankAccounts", []))
            elif t == "phishingUrls":
                total_items += len(infra.get("phishingUrls", []))
            elif t == "phishingDomains":
                total_items += len(infra.get("phishingDomains", []))
        if total_items >= 5:
            return 0.2
        if total_items >= 3:
            return 0.4
        if total_items >= 1:
            return 0.6
        return 0.8

    def _engagement_duration_seconds(self, session_memory: Dict[str, Any]) -> int:
        start = session_memory.get("sessionStartTime")
        if start is None:
            return 0
        now = datetime.now(timezone.utc)
        try:
            if isinstance(start, datetime):
                delta = now - start
            elif isinstance(start, str):
                from datetime import datetime as dt
                start_dt = dt.fromisoformat(start.replace("Z", "+00:00"))
                delta = now - start_dt
            else:
                return 0
            return max(0, int(delta.total_seconds()))
        except Exception:
            return 0
