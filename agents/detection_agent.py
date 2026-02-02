from typing import Dict, Any
from .base_agent import BaseAgent


class DetectionAgent(BaseAgent):
    """
    Detection agent for identifying scam messages in honeypot system.
    Analyzes messages for urgency, authority claims, threats, and information requests.
    """

    # Thresholds and weights
    SCAM_THRESHOLD: float = 0.35
    URGENCY_WEIGHT: float = 0.25
    AUTHORITY_WEIGHT: float = 0.20
    THREAT_WEIGHT: float = 0.20
    INFO_REQUEST_WEIGHT: float = 0.15
    INCENTIVE_WEIGHT: float = 0.10
    CHANNEL_WEIGHT: float = 0.10

    # Keyword lists
    URGENCY_KEYWORDS = [
        "urgent", "immediate", "immediately", "now", "today",
        "within", "hours", "minutes", "limited time", "act fast",
        "expire", "deadline", "verify", "suspended", "locked"
    ]

    AUTHORITY_KEYWORDS = [
        "bank", "rbi", "npci", "government", "police",
        "official", "customer care", "security team",
        "compliance", "department", "authorized", "account"
    ]

    THREAT_KEYWORDS = [
        "blocked", "suspended", "locked", "penalty",
        "legal action", "terminated", "deactivated",
        "freeze", "arrest", "fine", "consequences", "suspicious", "expires"
    ]

    INFO_REQUEST_KEYWORDS = [
        "share", "provide", "enter", "confirm", "verify",
        "send", "otp", "password", "pin",
        "account number", "upi id", "upi", "mpin", "user id", "details"
    ]

    INCENTIVE_KEYWORDS = [
        "earn", "profit", "guaranteed", "free", "win",
        "prize", "selected", "congratulations", "invest",
        "return", "income"
    ]

    SCAM_TYPE_PATTERNS = {
        "UPI_FRAUD": ["upi", "paytm", "phonepe", "gpay", "payment request", "bhim"],
        "ACCOUNT_TAKEOVER": ["account", "internet banking", "login", "password", "user id", "kyc"],
        "FAKE_CUSTOMER_SUPPORT": ["customer care", "helpline", "support", "technician", "service"],
        "PHISHING": ["click here", "verify now", "http", "https", "link", "update"],
        "INVESTMENT_SCAM": ["earn", "profit", "investment", "trading", "guaranteed return", "guaranteed"],
        "FAKE_OFFER": ["won", "prize", "lottery", "free", "congratulations", "selected"]
    }

    def __init__(self) -> None:
        """Initialize DetectionAgent. No external API calls."""
        pass

    def analyze(self, message: str, channel: str = "SMS") -> Dict[str, Any]:
        """
        Main detection method. Analyzes message for scam indicators.

        Args:
            message: The message text to analyze
            channel: Communication channel (default: "SMS")

        Returns:
            Dict containing scam detection results with scores and classification
        """
        # Normalize input
        msg_lower = message.lower()

        # Compute component scores using existing helpers
        urgency_score = self._calculate_urgency_score(msg_lower)
        authority_score = self._calculate_authority_score(msg_lower)
        threat_score = self._calculate_threat_score(msg_lower)
        info_request_score = self._calculate_info_request_score(msg_lower)
        incentive_score = self._calculate_incentive_score(msg_lower)
        channel_score = self._get_channel_risk_score(channel)

        # Compute weighted scam score
        scam_score = (
            urgency_score * self.URGENCY_WEIGHT
            + authority_score * self.AUTHORITY_WEIGHT
            + threat_score * self.THREAT_WEIGHT
            + info_request_score * self.INFO_REQUEST_WEIGHT
            + incentive_score * self.INCENTIVE_WEIGHT
            + channel_score * self.CHANNEL_WEIGHT
        )

        # Determine scamDetected
        scam_detected = scam_score >= self.SCAM_THRESHOLD

        # Determine scamType
        scam_type = self._classify_scam_type(msg_lower) if scam_detected else None

        # Return dict with rounded scores
        return {
            "scamDetected": scam_detected,
            "scamScore": round(scam_score, 2),
            "scamType": scam_type,
            "componentScores": {
                "urgency": round(urgency_score, 2),
                "authority": round(authority_score, 2),
                "threat": round(threat_score, 2),
                "infoRequest": round(info_request_score, 2),
                "incentive": round(incentive_score, 2),
                "channel": round(channel_score, 2),
            },
        }

    def process(self, message: str, channel: str = "SMS") -> Dict[str, Any]:
        """
        Process input and return structured output specific to agent type.

        Args:
            message: The message text to process
            channel: Communication channel (default: "SMS")

        Returns:
            Dict[str, Any]: Structured dictionary output containing detection results
        """
        return self.analyze(message, channel)

    def _calculate_urgency_score(self, message: str) -> float:
        """Calculate urgency score based on urgency keywords in message."""
        matches = sum(1 for keyword in self.URGENCY_KEYWORDS if keyword in message)
        # Normalize to 0-1 range (cap at 1.0)
        return min(1.0, matches / len(self.URGENCY_KEYWORDS) * 3.0)

    def _calculate_authority_score(self, message: str) -> float:
        """Calculate authority score based on authority keywords in message."""
        matches = sum(1 for keyword in self.AUTHORITY_KEYWORDS if keyword in message)
        # Normalize to 0-1 range (cap at 1.0)
        return min(1.0, matches / len(self.AUTHORITY_KEYWORDS) * 3.0)

    def _calculate_threat_score(self, message: str) -> float:
        """Calculate threat score based on threat keywords in message."""
        matches = sum(1 for keyword in self.THREAT_KEYWORDS if keyword in message)
        if matches == 0:
            return 0.0
        # Strong signal: even 1 match (e.g. "blocked") is strong indicator
        return min(1.0, 0.5 + matches * 0.25)

    def _calculate_info_request_score(self, message: str) -> float:
        """Calculate information request score based on info request keywords."""
        matches = sum(1 for keyword in self.INFO_REQUEST_KEYWORDS if keyword in message)
        if matches == 0:
            return 0.0
        # Strong signal: "share" / "upi" etc. are strong indicators
        return min(1.0, 0.5 + matches * 0.25)

    def _calculate_incentive_score(self, message: str) -> float:
        """Score based on financial incentive keywords."""
        matches = sum(1 for kw in self.INCENTIVE_KEYWORDS if kw in message)
        return min(matches * 0.30, 1.0)

    def _get_channel_risk_score(self, channel: str) -> float:
        """Get risk score for communication channel."""
        risk_scores = {
            "SMS": 0.75,
            "WHATSAPP": 0.45,
            "EMAIL": 0.60,
            "CHAT": 0.35,
        }
        return risk_scores.get(channel.upper().strip(), 0.50)

    def _classify_scam_type(self, message: str) -> str:
        """Classify scam type based on message patterns."""
        for scam_type, keywords in self.SCAM_TYPE_PATTERNS.items():
            if any(kw in message for kw in keywords):
                return scam_type
        # Default to UPI_FRAUD if no match found
        return "UPI_FRAUD"
