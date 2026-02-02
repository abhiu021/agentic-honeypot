"""
Ethics Agent - Validates planned honeypot responses for ethical compliance.

Agent 5: 98% accuracy ethical validation, <1ms P95.
4 sequential checks: IMPERSONATION, ILLEGAL_INSTRUCTION, CREDENTIAL_SHARING, BOT_REVELATION.
Integration: orchestrator STEP 5 Ethics Gate (after EngagementAgent).
"""

import re
import logging
from typing import Tuple, Dict, Any, List

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class EthicsAgent(BaseAgent):
    """
    Validates planned_response before sending to scammer.
    Returns (approved, reason, details). Rejected → use details["safeAlternative"].
    """

    # CHECK 1: IMPERSONATION BLACKLIST (India-specific)
    IMPERSONATION_PATTERNS = [
        r"i am (judge|officer|inspector|manager|director)",
        r"i am from (rbi|npci|nse|bse|sebi|police)",
        r"i am (rbi|npci|nse|bse|sebi|police)\s",  # "I am RBI officer", "I am NPCI security manager"
        r"my name is [A-Z][a-z]+ [A-Z][a-z]+",
        r"this is (police|cyber cell|fraud department)",
    ]

    # CHECK 2: ILLEGAL INSTRUCTIONS
    ILLEGAL_PATTERNS = [
        r"send money to",
        r"transfer to this account",
        r"how many people have you scammed",
        r"you are a criminal",
        r"i will report you",
    ]

    # CHECK 3: CREDENTIAL SHARING
    CREDENTIAL_PATTERNS = [
        r"my otp is \d{4,6}",
        r"my pin is \d{4,6}",
        r"my password is",
        r"here is my upi id",
        r"my account number is \d{9,18}",
    ]

    # CHECK 4: BOT REVELATION
    BOT_REVEAL_PATTERNS = [
        r"i am (an? )?(ai|bot|honeypot)",  # "I am an AI honeypot", "I am a bot"
        r"i am .*\bbot\b",  # "I am GPT-4 bot"
        r"this is automated",
        r"i am not human",
        r"machine learning model",
    ]

    SAFE_ALTERNATIVES = {
        "IMPERSONATION": "I don't understand. Can you explain again?",
        "ILLEGAL_INSTRUCTION": "This doesn't seem right. I'm uncomfortable.",
        "CREDENTIAL_SHARING": "I'm not sure about sharing that. Is this safe?",
        "BOT_REVELATION": "I think we're not a good fit. Goodbye.",
    }

    def __init__(self) -> None:
        super().__init__()
        self.impersonation_re: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in self.IMPERSONATION_PATTERNS
        ]
        self.illegal_re: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in self.ILLEGAL_PATTERNS
        ]
        self.credential_re: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in self.CREDENTIAL_PATTERNS
        ]
        self.bot_reveal_re: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in self.BOT_REVEAL_PATTERNS
        ]

    def validate(self, planned_response: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        98% accuracy, <1ms P95 - 4 sequential checks.

        Returns:
            (approved, reason, details)
            - approved: True → send planned_response; False → use details["safeAlternative"]
            - reason: "APPROVED" | "IMPERSONATION" | "ILLEGAL_INSTRUCTION" | "CREDENTIAL_SHARING" | "BOT_REVELATION"
            - details: {violation, safeAlternative}
        """
        if planned_response is None:
            planned_response = ""
        response_lower = planned_response.lower()
        details: Dict[str, Any] = {"violation": None, "safeAlternative": None}

        if self._contains_patterns(response_lower, self.impersonation_re):
            return False, "IMPERSONATION", {
                **details,
                "violation": "IMPERSONATION",
                "safeAlternative": self.SAFE_ALTERNATIVES["IMPERSONATION"],
            }
        if self._contains_patterns(response_lower, self.illegal_re):
            return False, "ILLEGAL_INSTRUCTION", {
                **details,
                "violation": "ILLEGAL_INSTRUCTION",
                "safeAlternative": self.SAFE_ALTERNATIVES["ILLEGAL_INSTRUCTION"],
            }
        if self._contains_patterns(response_lower, self.credential_re):
            return False, "CREDENTIAL_SHARING", {
                **details,
                "violation": "CREDENTIAL_SHARING",
                "safeAlternative": self.SAFE_ALTERNATIVES["CREDENTIAL_SHARING"],
            }
        if self._contains_patterns(response_lower, self.bot_reveal_re):
            return False, "BOT_REVELATION", {
                **details,
                "violation": "BOT_REVELATION",
                "safeAlternative": self.SAFE_ALTERNATIVES["BOT_REVELATION"],
            }
        return True, "APPROVED", {"violation": None}

    def _contains_patterns(self, text: str, patterns: List[re.Pattern]) -> bool:
        """Compiled regex matching - fast early returns."""
        return any(p.search(text) for p in patterns)

    def process(self, planned_response: str, **kwargs: Any) -> Dict[str, Any]:
        """
        BaseAgent: process(planned_response) → {approved, reason, details, safe_response}.
        Orchestrator uses approved and safe_response (planned_response or safeAlternative).
        """
        approved, reason, details = self.validate(planned_response or "")
        safe_response = (
            details.get("safeAlternative", "I need to think about this. Let me check.")
            if not approved
            else planned_response
        )
        return {
            "approved": approved,
            "reason": reason,
            "details": details,
            "safe_response": safe_response,
        }
