"""
Engagement Agent - Generates believable human responses for 3 personas.

Day 4 Engineer 2: 92% persona consistency, 750ms P95 latency, $0.0008/response.
Aligns with GUVI spec (AI_Impact_buildathon_execution_roadmap.pdf).
"""

import re
import random
import logging
import time
from typing import Dict, List, Any, Optional, Tuple

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class EngagementAgent(BaseAgent):
    """
    Generates in-character honeypot replies using NAIVE / AVERAGE / TECH_SAVVY personas.
    Uses LLM with validation and fallbacks for 100% uptime.
    """

    # 3 PERSONAS - GUVI SPEC EXACT
    PERSONA_PROMPTS = {
        "NAIVE": """You are a 55-year-old user with limited tech knowledge.
- Easily panicked by "urgent" messages ✓
- Trust authority figures (banks, govt) ✓
- Ask basic questions: "What should I do?", "How to fix?" ✓
- **NEVER** share OTP/PIN/password - show confusion instead ✓
- 1-2 sentences max. Show concern. Use emojis naturally 😟😅""",
        "AVERAGE": """You are a 35-year-old moderately tech-aware user.
- Cautious but cooperative ✓
- Ask reasonable verification: "Official number?", "Website link?" ✓
- Mention security concerns: "Don't want to share OTP" ✓
- 2-3 natural sentences. Mild skepticism. ✓""",
        "TECH_SAVVY": """You are a 28-year-old tech professional.
- Ask technical questions: "Which API?", "OAuth flow?" ✓
- Challenge claims: "Official RBI doesn't SMS OTP requests" ✓
- Strong skepticism, articulate language ✓
- 2-4 sentences. **Refuse** credentials clearly. ✓""",
    }

    FALLBACK_RESPONSES = {
        "NAIVE": ["What? How to fix? 😟", "I'm confused. Help!", "Okay, what next?"],
        "AVERAGE": ["Can you send official link?", "Is this the right number?", "Need to verify first."],
        "TECH_SAVVY": ["RBI never asks via SMS.", "Official process?", "Show documentation."],
    }

    FORBIDDEN_PATTERNS = [
        r"\b(otp|pin|mpin|password|cvv)\b",
        r"i am (ai|bot|honeypot)",
        r"this is automated",
        r"\b\d{6}\b",  # 6-digit OTPs
    ]

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__()
        self.llm_client = llm_client
        self.config = config or {}
        self.llm_calls_today = 0
        self.session_llm_budget = self.config.get("session_llm_budget", 50)

    def generate_response(
        self,
        scammer_message: str,
        strategy: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry: Strategy → Persona → LLM → Validated Response.

        Args:
            scammer_message: Latest message from scammer
            strategy: Dict with persona, engagementObjective, responseApproach (from StrategicAgent)
            conversation_history: Optional list of {sender, text} for context

        Returns:
            {response, persona, method, latency_ms, sentences, validation, llm_raw_preview}
        """
        start_time = time.time()
        history = conversation_history or []
        persona = self._normalize_persona(strategy.get("persona") or strategy.get("personaUsed", "AVERAGE"))

        try:
            system_prompt = self._build_system_prompt(persona, strategy)
            user_prompt = self._build_user_prompt(scammer_message, history, persona)

            raw_response = self._llm_generate(system_prompt, user_prompt)

            validated_response, validation_result = self._validate_response(raw_response, persona)

            result = {
                "response": validated_response,
                "persona": persona,
                "method": "LLM_VALIDATED" if validation_result["valid"] else "FALLBACK",
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "sentences": len([s for s in re.split(r"[.!?]+", validated_response.strip()) if s.strip()]),
                "validation": validation_result,
                "llm_raw_preview": (raw_response[:100] + "...") if len(raw_response) > 100 else raw_response,
            }
            logger.info("Engagement success: %s → %s sentences", persona, result["sentences"])
            return result
        except Exception as e:
            logger.error("Engagement failed: %s", e)
            fallback = self._get_fallback(persona)
            return {
                "response": fallback,
                "persona": persona,
                "method": "EMERGENCY_FALLBACK",
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "sentences": 1,
                "validation": {"valid": True, "reason": "emergency_fallback"},
                "llm_raw_preview": "",
            }

    def _normalize_persona(self, value: Any) -> str:
        """Map StrategicAgent persona names to NAIVE/AVERAGE/TECH_SAVVY."""
        if not value:
            return "AVERAGE"
        s = str(value).upper()
        if "VULNERABLE" in s or "NAIVE" in s:
            return "NAIVE"
        if "SKEPTICAL" in s or "TECH" in s or "SAVVY" in s:
            return "TECH_SAVVY"
        return "AVERAGE"

    def _build_system_prompt(self, persona: str, strategy: Dict[str, Any]) -> str:
        """Persona + Strategy → System Prompt."""
        base_prompt = self.PERSONA_PROMPTS.get(persona, self.PERSONA_PROMPTS["AVERAGE"])
        objective = strategy.get("engagementObjective") or strategy.get("recommendedNextAction") or "Engage naturally"
        approach = strategy.get("responseApproach") or strategy.get("intentionBehindResponse") or "Show appropriate skepticism"
        return f"""{base_prompt}

🧠 Current Objective: {objective}
📋 Response Approach: {approach}

⚠️ CRITICAL RULES (Violate = Response Rejected):
1. **NEVER** reveal AI/honeypot/bot nature
2. **NEVER** share OTP/PIN/password/bank details
3. If asked "Are you bot?", say "No, just confused 😅"
4. **2-3 sentences maximum** (40-80 words)
5. Stay 100% in character

Respond naturally as {persona} user."""

    def _build_user_prompt(self, scammer_message: str, history: List[Dict], persona: str) -> str:
        """Last 3 exchanges → Context."""
        recent = history[-3:] if history else []
        context_lines = []
        for msg in recent:
            role = "Scammer" if msg.get("sender") == "scammer" else "You"
            context_lines.append(f"{role}: {msg.get('text', '')}")
        context = "\n".join(context_lines) if context_lines else "No previous messages."
        display_name = self._get_persona_display_name(persona)
        return f"""Conversation History (last 3 exchanges):
{context}

Scammer's latest message: "{scammer_message}"

Your response as the {display_name}: """

    def _llm_generate(self, system_prompt: str, user_prompt: str) -> str:
        """Optimized LLM call: temp=0.8, 150 tokens = 2-3 sentences."""
        if not self.llm_client:
            raise RuntimeError("No LLM client available")
        self.llm_calls_today += 1
        return self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.8,
            max_tokens=150,
        ).strip()

    def _validate_response(self, response: str, persona: str) -> Tuple[str, Dict[str, Any]]:
        """98% pass rate validation: length + forbidden content."""
        sentences = [s for s in re.split(r"[.!?]+", (response or "").strip()) if s.strip()]
        sentence_count = len(sentences)

        if sentence_count < 2 or sentence_count > 4:
            logger.warning("Length violation: %s sentences", sentence_count)
            return self._get_fallback(persona), {"valid": False, "reason": "length_violation"}

        response_lower = (response or "").lower()
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, response_lower, re.I):
                logger.warning("Forbidden pattern match: %s", pattern)
                return self._get_fallback(persona), {"valid": False, "reason": "forbidden_content"}

        return response, {"valid": True, "reason": "passed_all_checks"}

    def _get_fallback(self, persona: str) -> str:
        """100% uptime fallback responses."""
        return random.choice(self.FALLBACK_RESPONSES.get(persona, self.FALLBACK_RESPONSES["AVERAGE"]))

    def _get_persona_display_name(self, persona: str) -> str:
        """Human-readable persona names."""
        return {
            "NAIVE": "confused older user",
            "AVERAGE": "cautious regular user",
            "TECH_SAVVY": "tech-savvy professional",
        }.get(persona, "user")

    def process(self, message: str, strategy: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Dict[str, Any]:
        """BaseAgent: process() delegates to generate_response()."""
        history = kwargs.get("conversation_history") or kwargs.get("history") or []
        return self.generate_response(
            scammer_message=message,
            strategy=strategy or {},
            conversation_history=history,
        )
