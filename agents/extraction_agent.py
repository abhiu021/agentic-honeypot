"""
ExtractionAgent - Intelligence extraction from scammer messages.

Hybrid 95% regex / 5% LLM: fast regex for clear patterns (phones, UPI, URLs),
LLM escalation for ambiguous cases (order #, standalone 10-digit, multi-provider UPI).
Also provides extract_intelligence() matching SessionMemory.extractedIntelligence.
"""

import re
import time
import json
import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from urllib.parse import urlparse

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


def _norm_llm_phones(phones: List[Any]) -> List[str]:
    """Normalize LLM phone list to 91-prefix strings."""
    out: List[str] = []
    for p in phones or []:
        if not isinstance(p, str):
            continue
        digits = re.sub(r"\D", "", p)
        if len(digits) == 10 and digits[0] in "6789":
            out.append("91" + digits)
        elif len(digits) == 12 and digits.startswith("91"):
            out.append(digits)
        elif len(digits) == 10:
            out.append("91" + digits)
        else:
            out.append(digits)
    return out


def _norm_llm_upis(upis: List[Any]) -> List[Tuple[str, str]]:
    """Normalize LLM UPI list (strings like 'id@paytm') to (id, provider) tuples."""
    out: List[Tuple[str, str]] = []
    for u in upis or []:
        if isinstance(u, (list, tuple)) and len(u) >= 2:
            out.append((str(u[0]).strip(), str(u[1]).lower()))
        elif isinstance(u, str) and "@" in u:
            parts = u.strip().rsplit("@", 1)
            if len(parts) == 2:
                out.append((parts[0].strip(), parts[1].lower()))
    return out


class ExtractionAgent(BaseAgent):
    """
    Hybrid Regex+LLM extraction: 95% regex (fast), 5% LLM (ambiguous cases).
    extract(message) -> {method, phones, upis, urls, latency_ms, confidence}
    extract_intelligence(message) -> full SessionMemory.extractedIntelligence structure.
    """

    # --- Fast path: compiled regex (Indian phone / UPI / URL), ~1.9ms ---
    PHONE_RX = re.compile(r"\+?91[-.\s]?\d{10}|\b[6-9]\d{9}\b")
    UPI_RX = re.compile(
        r"\b([a-zA-Z0-9.-]+)@(paytm|phonepe|ybl|axis|bl|oksbi|icici|kotak|airtel)\b",
        re.I,
    )
    URL_RX = re.compile(r"https?://[^\s<>\"{}|\\^`\[\]]+")
    # Bare domains (no scheme): www.fake-bank.in, signup.scam-trade.com, example.com/path
    BARE_DOMAIN_RX = re.compile(
        r"\b(?:www\.)?(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?:\/[^\s<>\"{}|\\^`\[\]]*)?",
        re.I,
    )

    # LLM escalation triggers (5% of cases)
    AMBIGUOUS_PATTERNS = [
        r"order\s*#?",
        r"ref\s*#?",
        r"id\s*:?",
        r"ticket\s*#?",
        r"transaction\s*#?",
        r"invoice\s*#?",
    ]

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__()
        self.llm_client = llm_client
        self.config = config or {"llm_budget": 1000, "llm_enabled": True}
        self.llm_calls_today = 0
        self.session_llm_budget = self.config.get("session_llm_budget", 3)

        # Regex patterns for identity markers (used by extract_intelligence)
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
                # Bare domains (no scheme): www.fake-bank.in, signup.scam-trade.com
                r"(?:www\.)?(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?:/[^\s<>\"{}|\\^`\[\]]*)?",
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

    # --- Hybrid extract() API: 95% regex, 5% LLM escalation ---

    def extract(self, message: str) -> Dict[str, Any]:
        """
        Main extraction: 95% regex → 5% LLM escalation.
        Returns: {method, phones, upis, urls, latency_ms, confidence}
        """
        if not message or len(message.strip()) == 0:
            return {
                "method": "EMPTY",
                "phones": [],
                "upis": [],
                "urls": [],
                "latency_ms": 0.1,
            }

        start_time = time.time()
        regex_results = self._fast_regex_extract(message)
        needs_llm = self._needs_llm(message.lower(), regex_results)

        # Ambiguous case (order #, standalone 10-digit, etc.): escalate to LLM or treat as empty
        if needs_llm:
            if self.llm_client:
                llm_result = self._llm_extract_ambiguous(message)
                # Merge: keep regex results, add/fill from LLM (don't let empty LLM overwrite regex)
                phones = list(dict.fromkeys(regex_results["phones"] + _norm_llm_phones(llm_result.get("phones", []))))
                upis_regex = regex_results["upis"]
                upis_llm = _norm_llm_upis(llm_result.get("upis", []))
                upis = list(dict.fromkeys(upis_regex + [u for u in upis_llm if u not in upis_regex]))
                urls = list(dict.fromkeys(regex_results["urls"] + (llm_result.get("urls") or [])))
                result = {
                    "method": "HYBRID",
                    "latency_ms": round((time.time() - start_time) * 1000, 2),
                    "phones": phones,
                    "upis": upis,
                    "urls": urls,
                    "confidence": llm_result.get("confidence", "LOW"),
                }
                logger.info("LLM escalation: %s", llm_result)
                return result
            # No LLM client: do not trust regex for ambiguous context (could be order ID, not phone)
            result = {
                "method": "REGEX_EMPTY",
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "phones": [],
                "upis": [],
                "urls": [],
                "confidence": "LOW",
            }
            return result

        # Clear case: regex found something
        if regex_results["phones"] or regex_results["upis"] or regex_results["urls"]:
            result = {
                "method": "REGEX_ONLY",
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                **regex_results,
                "confidence": "HIGH",
            }
            logger.info("REGEX hit: %s", regex_results)
            return result

        result = {
            "method": "REGEX_EMPTY",
            "latency_ms": round((time.time() - start_time) * 1000, 2),
            "phones": [],
            "upis": [],
            "urls": [],
            "confidence": "LOW",
        }
        return result

    def _fast_regex_extract(self, message: str) -> Dict[str, Any]:
        """Fast path: extract phones, UPIs, URLs (~1.9ms)."""
        raw_phones = self.PHONE_RX.findall(message)
        phones: List[str] = []
        for m in raw_phones:
            digits = re.sub(r"\D", "", m)
            if len(digits) == 10 and digits[0] in "6789":
                phones.append("91" + digits)
            elif len(digits) == 12 and digits.startswith("91"):
                phones.append(digits)
            elif len(digits) == 10:
                phones.append("91" + digits)
            else:
                phones.append(digits)
        phones = list(dict.fromkeys(phones))

        upis_raw = self.UPI_RX.findall(message)
        upis: List[Tuple[str, str]] = [(id_part, provider.lower()) for id_part, provider in upis_raw]
        urls = list(dict.fromkeys(self.URL_RX.findall(message)))
        # Add bare domains (normalize to https:// for consistency)
        for bare in self.BARE_DOMAIN_RX.findall(message):
            normalized = bare if bare.startswith("http") else "https://" + bare
            if normalized not in urls:
                urls.append(normalized)
        urls = list(dict.fromkeys(urls))

        return {"phones": phones, "upis": upis, "urls": urls}

    def _needs_llm(self, msg_lower: str, regex_results: Dict[str, Any]) -> bool:
        """Smart escalation: 95% False, 5% True. Detects ambiguous context (with or without LLM)."""
        if self.llm_client and self.llm_calls_today >= self.config.get("llm_budget", 1000):
            return False
        if any(re.search(p, msg_lower) for p in self.AMBIGUOUS_PATTERNS):
            return True
        if re.search(
            r"(paytm|phonepe|ybl).*?(paytm|phonepe|ybl)",
            msg_lower,
            re.I,
        ):
            return True
        # Standalone 10-digit only when NOT clearly a +91 phone (avoid "Call +91 9876543210")
        has_plus91 = bool(re.search(r"\+?\s*91\s*\d", msg_lower))
        standalone = re.findall(r"\b[6-9]\d{9}\b", msg_lower)
        if (
            standalone
            and not has_plus91
            and not (regex_results.get("urls") or regex_results.get("upis"))
        ):
            return True
        return False

    def _llm_extract_ambiguous(self, message: str) -> Dict[str, Any]:
        """LLM for ambiguous cases."""
        self.llm_calls_today += 1
        if not self.llm_client:
            return {"phones": [], "upis": [], "urls": [], "confidence": "LOW"}

        prompt = f"""Extract phone numbers, UPI IDs, and URLs from this Indian scam message.
Return ONLY valid JSON. Be conservative - only extract CLEAR matches.

Message: "{message}"

{{
  "phones": ["+919876543210", "9876543210"],
  "upis": ["test@paytm", "user@phonepe"],
  "urls": ["https://fakebank.com/verify"],
  "confidence": "LOW|MEDIUM|HIGH"
}}
"""
        try:
            response = self.llm_client.generate(
                prompt, temperature=0.1, max_tokens=200
            )
            parsed = self._parse_llm_json(response)
            return {
                **parsed,
                "llm_raw": (response[:100] + "...") if response else "",
            }
        except Exception as e:
            logger.error("LLM extraction failed: %s", e)
            return {"phones": [], "upis": [], "urls": [], "confidence": "LOW"}

    def _parse_llm_json(self, response: str) -> Dict[str, Any]:
        """Safe JSON parsing with validation."""
        try:
            cleaned = re.sub(r"```(?:json)?", "", response or "", flags=re.I).strip()
            result = json.loads(cleaned)
            if not all(
                key in result for key in ["phones", "upis", "urls", "confidence"]
            ):
                raise ValueError("Missing required fields")
            return {
                "phones": result.get("phones", []),
                "upis": result.get("upis", []),
                "urls": result.get("urls", []),
                "confidence": result.get("confidence", "LOW"),
            }
        except Exception:
            return {"phones": [], "upis": [], "urls": [], "confidence": "LOW"}

    def process(self, message: str, **kwargs: Any) -> Dict[str, Any]:
        """BaseAgent: process() delegates to extract()."""
        return self.extract(message)

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
