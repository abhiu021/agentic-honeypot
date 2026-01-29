from typing import Dict, Any, Optional
import json
import logging

from .detection_agent import DetectionAgent

logger = logging.getLogger(__name__)


class EnhancedDetectionAgent(DetectionAgent):
    """Hybrid scam detector: rule-based with LLM fallback for low-confidence cases.

    Uses parent DetectionAgent for keyword-based scoring, then:
    - If scamScore >= 0.60: Trust rule-based (high confidence)
    - If scamScore < 0.60: Call LLM for semantic analysis (low confidence)

    Maintains backward compatibility: all existing fields preserved.
    """

    # Confidence threshold: above this, skip LLM
    HIGH_CONFIDENCE_THRESHOLD: float = 0.60

    def __init__(self, llm_client: Optional[Any] = None) -> None:
        """Initialize with optional LLM client.

        Args:
            llm_client: Instance of BaseLLMClient (Gemini/Mock).
                If None, falls back to pure rule-based detection.
        """
        super().__init__()
        self.llm_client = llm_client

    def analyze(self, message: str, channel: str = "SMS") -> Dict[str, Any]:
        """Analyze message with hybrid rule-based + LLM approach.

        Args:
            message: Text to analyze
            channel: Communication channel (SMS/Email/WhatsApp/Call)

        Returns:
            Dict with DetectionAgent fields + confidence/detectionMethod/reasoning
        """
        # Step 1: Always run rule-based detection first
        rule_result = super().analyze(message, channel)
        rule_score = rule_result["scamScore"]

        # Step 2: High confidence? Return immediately with rule-based result
        if rule_score >= self.HIGH_CONFIDENCE_THRESHOLD:
            return {
                **rule_result,
                "confidence": "HIGH",
                "detectionMethod": "RULE_BASED",
                "reasoning": self._generate_rule_reasoning(rule_result),
            }

        # Step 3: Low confidence - try LLM if available
        if self.llm_client:
            try:
                llm_result = self._call_llm(message, channel, rule_result)
                return {
                    **llm_result,
                    "confidence": "MEDIUM",
                    "detectionMethod": "LLM_ENHANCED",
                    "ruleBasedScore": rule_score,
                    "reasoning": llm_result.get("reasoning", ""),
                }
            except Exception as e:
                logger.warning(f"LLM call failed: {e}. Falling back to rule-based.")
                return {
                    **rule_result,
                    "confidence": "LOW",
                    "detectionMethod": "RULE_BASED_FALLBACK",
                    "reasoning": f"LLM unavailable: {str(e)}",
                }

        # Step 4: No LLM available - return rule-based with low confidence
        return {
            **rule_result,
            "confidence": "LOW",
            "detectionMethod": "RULE_BASED",
            "reasoning": self._generate_rule_reasoning(rule_result),
        }

    def _call_llm(self, message: str, channel: str, rule_result: Dict[str, Any]) -> Dict[str, Any]:
        """Call LLM for semantic scam analysis.

        Args:
            message: Original message text
            channel: Communication channel
            rule_result: Rule-based detection output (for context)

        Returns:
            Dict matching DetectionAgent output format with LLM scores
        """
        prompt = f"""You are a scam detection expert. Analyze this message for scam patterns that rule-based systems might miss.

MESSAGE: "{message}"
CHANNEL: {channel}
RULE-BASED SCORE: {rule_result['scamScore']} (threshold: {self.SCAM_THRESHOLD})

Focus on detecting:
1. **Urgency tactics**: Implicit deadlines, time pressure, "act now" language
2. **Authority impersonation**: Claims to be bank/government/official without explicit naming
3. **Threat patterns**: Implied consequences (account closure, legal action, missed opportunity)
4. **Credential harvesting**: Requests for OTP, password, UPI ID, card details
5. **Financial lures**: Guaranteed returns, prizes, lottery wins, urgent refunds
6. **Novel phrasing**: New scam tactics not in keyword lists

SCAM TYPES (choose most relevant):
- UPI_FRAUD: Payment app scams, fake UPI requests
- ACCOUNT_TAKEOVER: Banking credential theft, KYC verification scams
- FAKE_CUSTOMER_SUPPORT: Impersonating service providers, fake helplines
- PHISHING: Malicious links, credential harvesting sites
- INVESTMENT_SCAM: Fake trading platforms, guaranteed returns
- FAKE_OFFER: Prize/lottery scams, free gift claims

Return ONLY valid JSON (no markdown, no explanation):
{{
    "scamDetected": true or false,
    "scamScore": 0.0 to 1.0,
    "scamType": "TYPE" or null,
    "reasoning": "Brief 1-sentence explanation of detection logic"
}}"""

        response = self.llm_client.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=200,
        )

        llm_data = json.loads(response.strip())

        return {
            "scamDetected": llm_data.get("scamDetected", False),
            "scamScore": round(llm_data.get("scamScore", 0.0), 2),
            "scamType": llm_data.get("scamType"),
            "componentScores": rule_result["componentScores"],
            "reasoning": llm_data.get("reasoning", ""),
        }

    def _generate_rule_reasoning(self, rule_result: Dict[str, Any]) -> str:
        """Generate human-readable reasoning from rule-based scores.

        Args:
            rule_result: Output from parent DetectionAgent

        Returns:
            Brief explanation string
        """
        components = rule_result["componentScores"]
        high_components = [
            name for name, score in components.items()
            if score >= 0.6 and name != "channel"
        ]

        if not high_components:
            return "Low risk indicators detected"

        return f"High {', '.join(high_components)} indicators detected"

