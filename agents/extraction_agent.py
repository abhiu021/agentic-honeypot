"""
ExtractionAgent - Intelligence extraction from scammer messages.

Extracts structured intelligence using regex patterns and keyword matching.
Matches SessionMemory.extractedIntelligence structure.
"""

import re
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse


class ExtractionAgent:
    """
    Extracts structured intelligence from scammer messages.
    Uses regex patterns and keyword matching.
    """

    def __init__(self) -> None:
        """Initialize extraction patterns."""

        # Regex patterns for identity markers
        self.patterns: Dict[str, List[str]] = {
            "phone": [
                r"\+91[-\s]?\d{10}",  # +91 9876543210 or +91-9876543210
                r"\+91\d{10}",  # +919876543210
                r"(?<!\d)\d{10}(?!\d)",  # 9876543210 (standalone)
                r"1800[-\s]?\d{6,7}",  # Toll-free: 1800-123456
                r"\d{5}[-\s]\d{5}",  # 98765-43210
            ],
            "email": [
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            ],
            "upi": [
                r"[\w.-]+@(?:paytm|phonepe|ybl|okaxis|oksbi|axl|ibl|icici|kotak|airtel)",
                r"\w*\s*@\s*(?:paytm|phonepe|ybl|okaxis|oksbi|axl|ibl|icici|kotak|airtel)",  # "account @paytm"
                r"[a-zA-Z0-9._-]+@upi",
                r"\d{10}@paytm",  # Phone number as UPI
            ],
            "url": [
                r"https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                r"bit\.ly/[\w]+",
                r"tinyurl\.com/[\w]+",
                r"goo\.gl/[\w]+",
                r"[\w-]+\.(?:com|in|org|net|xyz)/[\w/.-]*",
            ],
            "bank_account": [
                r"(?<!\d)\d{9,18}(?!\d)",  # 9-18 digit account numbers
                r"A/C\s*[:=-]?\s*\d{9,18}",  # A/C: 123456789
                r"Account\s*[:=-]?\s*\d{9,18}",  # Account: 123456789
            ],
            "amount": [
                r"₹\s*[\d,]+(?:\.\d{2})?",  # ₹1,000 or ₹1000.00
                r"Rs\.?\s*[\d,]+(?:\.\d{2})?",  # Rs. 1000
                r"INR\s*[\d,]+(?:\.\d{2})?",  # INR 1000
            ],
            "ifsc": [
                r"[A-Z]{4}0[A-Z0-9]{6}",  # IFSC code: SBIN0001234
            ],
        }

        # Psychological tactic keywords
        self.tactic_keywords: Dict[str, List[str]] = {
            "urgencyExploitation": [
                "immediate",
                "immediately",
                "urgent",
                "urgently",
                "now",
                "right now",
                "asap",
                "today",
                "within 24 hours",
                "2 hours",
                "30 minutes",
                "expire",
                "expires",
                "expiring",
                "limited time",
                "act fast",
                "act now",
                "hurry",
                "quick",
                "quickly",
                "soon",
            ],
            "authorityMimicry": [
                "rbi",
                "reserve bank",
                "npci",
                "government",
                "ministry",
                "official",
                "authorized",
                "verified",
                "certified",
                "customer care",
                "customer support",
                "helpline",
                "technical support",
                "support team",
                "security team",
                "compliance team",
                "fraud department",
                "legal department",
            ],
            "threatPatterns": [
                "blocked",
                "block",
                "suspend",
                "suspended",
                "terminate",
                "terminated",
                "deactivated",
                "disabled",
                "closed",
                "legal action",
                "police",
                "arrest",
                "fir",
                "complaint",
                "penalty",
                "fine",
                "charges",
                "consequences",
                "action",
                "report",
                "reported",
            ],
            "scarcityTactics": [
                "limited",
                "limited time",
                "limited slots",
                "only",
                "exclusive",
                "last chance",
                "final",
                "running out",
                "few left",
                "stock limited",
                "offer ends",
                "expires",
            ],
        }

        # Suspicious keywords by category
        self.suspicious_keywords: Dict[str, List[str]] = {
            "verification_requests": [
                "verify",
                "verification",
                "confirm",
                "validate",
                "authenticate",
                "otp",
                "one time password",
                "pin",
                "mpin",
                "cvv",
                "password",
            ],
            "payment_requests": [
                "payment",
                "pay",
                "transfer",
                "send money",
                "deposit",
                "refund",
                "cashback",
                "processing fee",
                "registration fee",
                "service charge",
                "tax",
                "gst",
            ],
            "account_references": [
                "account",
                "bank account",
                "upi",
                "upi id",
                "upi handle",
                "paytm",
                "phonepe",
                "gpay",
                "google pay",
                "bhim",
                "internet banking",
                "net banking",
                "debit card",
                "credit card",
            ],
            "remote_access": [
                "anydesk",
                "teamviewer",
                "quicksupport",
                "remote",
                "remote access",
                "screen share",
                "download app",
                "install app",
            ],
        }

    def extract_intelligence(
        self, message: str, scam_type: Optional[str] = None
    ) -> Dict:
        """
        Extract all intelligence from a single message.

        Args:
            message: Scammer's message
            scam_type: Optional scam type for context

        Returns:
            Dictionary matching SessionMemory.extractedIntelligence structure
        """
        message_lower = message.lower()

        # Extract identity markers
        phone_numbers = self._extract_phone_numbers(message)
        email_addresses = self._extract_emails(message)
        upi_ids = self._extract_upi_ids(message)
        bank_accounts = self._extract_bank_accounts(message)

        # Extract infrastructure
        urls = self._extract_urls(message)
        domains = self._extract_domains(urls)

        # Extract psychological tactics
        urgency = self._find_keywords(
            message_lower, self.tactic_keywords["urgencyExploitation"]
        )
        authority = self._find_keywords(
            message_lower, self.tactic_keywords["authorityMimicry"]
        )
        threats = self._find_keywords(
            message_lower, self.tactic_keywords["threatPatterns"]
        )
        scarcity = self._find_keywords(
            message_lower, self.tactic_keywords["scarcityTactics"]
        )

        # Extract suspicious keywords
        suspicious: List[str] = []
        for keywords in self.suspicious_keywords.values():
            found = self._find_keywords(message_lower, keywords)
            suspicious.extend(found)

        return {
            "identityMarkers": {
                "phoneNumbers": phone_numbers,
                "emailAddresses": email_addresses,
                "upiIds": upi_ids,
                "bankAccounts": bank_accounts,
            },
            "infrastructure": {
                "phishingDomains": domains,
                "phishingUrls": urls,
                "suspiciousGateways": [],
            },
            "psychologicalTactics": {
                "urgencyExploitation": urgency,
                "authorityMimicry": authority,
                "threatPatterns": threats,
                "scarcityTactics": scarcity,
            },
            "suspiciousKeywords": list(dict.fromkeys(suspicious)),
        }

    def _extract_phone_numbers(self, message: str) -> List[str]:
        """Extract Indian phone numbers."""
        phones: Set[str] = set()
        for pattern in self.patterns["phone"]:
            for match in re.finditer(pattern, message):
                m = match.group(0)
                cleaned = re.sub(r"[-\s]", "", m)
                digits = re.sub(r"\D", "", cleaned)
                # Toll-free: keep as 1800XXXXXX, do not add +91
                if "1800" in pattern or cleaned.startswith("1800"):
                    phones.add(cleaned)
                    continue
                if len(digits) == 10 and digits.isdigit():
                    phones.add(f"+91{digits}")
                elif cleaned.startswith("+91"):
                    phones.add(re.sub(r"[-\s]", "", cleaned))
                elif len(digits) == 10:
                    phones.add(f"+91{digits}")
        return list(phones)

    def _extract_emails(self, message: str) -> List[str]:
        """Extract email addresses."""
        emails: Set[str] = set()
        for pattern in self.patterns["email"]:
            for match in re.finditer(pattern, message):
                emails.add(match.group(0).lower())
        return list(emails)

    def _extract_upi_ids(self, message: str) -> List[str]:
        """Extract UPI IDs."""
        upi_ids: Set[str] = set()
        msg_lower = message.lower()
        for pattern in self.patterns["upi"]:
            for match in re.finditer(pattern, msg_lower, re.IGNORECASE):
                raw = match.group(0).lower().replace(" ", "")
                upi_ids.add(raw)
        return list(upi_ids)

    def _extract_bank_accounts(self, message: str) -> List[str]:
        """Extract bank account numbers (9-18 digits, exclude plain 10-digit phones)."""
        accounts: Set[str] = set()
        for pattern in self.patterns["bank_account"]:
            for match in re.finditer(pattern, message):
                m = match.group(0)
                digits = re.sub(r"\D", "", m)
                if 9 <= len(digits) <= 18:
                    # Avoid adding 10-digit numbers that are likely phones
                    if len(digits) == 10 and digits.isdigit():
                        if digits[0] in "6789":  # Indian mobile prefix
                            continue
                    accounts.add(digits)
        return list(accounts)

    def _extract_urls(self, message: str) -> List[str]:
        """Extract URLs."""
        urls_set: Set[str] = set()
        for pattern in self.patterns["url"]:
            for match in re.finditer(pattern, message):
                urls_set.add(match.group(0))
        return list(urls_set)

    def _extract_domains(self, urls: List[str]) -> List[str]:
        """Extract domains from URLs."""
        domains: Set[str] = set()
        for url in urls:
            try:
                if not url.startswith(("http://", "https://")):
                    url = "http://" + url
                parsed = urlparse(url)
                if parsed.netloc:
                    domains.add(parsed.netloc.lower())
            except Exception:
                continue
        return list(domains)

    def _find_keywords(
        self, message_lower: str, keywords: List[str]
    ) -> List[str]:
        """Find matching keywords in message."""
        found: List[str] = []
        for keyword in keywords:
            if keyword.lower() in message_lower:
                found.append(keyword)
        return found
