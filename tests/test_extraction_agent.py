"""
Tests for ExtractionAgent - intelligence extraction from scammer messages.
Includes hybrid extract() (95% regex, 5% LLM) and extract_intelligence() (full schema).
"""

import sys
import os
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.extraction_agent import ExtractionAgent


# --- Hybrid extract() tests (95% regex, 5% LLM) ---


def test_extract_clear_phone_regex() -> None:
    """1.9ms clear phone wins REGEX_ONLY."""
    agent = ExtractionAgent()
    result = agent.extract("Call +91 9876543210 NOW")
    assert result["phones"] == ["919876543210"]
    assert result["method"] == "REGEX_ONLY"
    assert result["latency_ms"] < 10
    assert result.get("confidence") == "HIGH"


def test_extract_clear_upi_regex() -> None:
    """Clear UPI -> REGEX_ONLY, upis as (id, provider) tuples."""
    agent = ExtractionAgent()
    result = agent.extract("Share test@paytm UPI")
    assert result["upis"] == [("test", "paytm")]
    assert result["method"] == "REGEX_ONLY"


def test_extract_clear_url_regex() -> None:
    """Clear URL -> REGEX_ONLY."""
    agent = ExtractionAgent()
    result = agent.extract("Click https://fakebank.com")
    assert any("fakebank.com" in u for u in result["urls"])
    assert result["method"] == "REGEX_ONLY"


def test_extract_bare_domain_regex() -> None:
    """Bare domains (no scheme) -> REGEX_ONLY, normalized to https://."""
    agent = ExtractionAgent()
    result = agent.extract("Visit www.fake-bank.in or signup.scam-trade.com to verify")
    urls = result["urls"]
    assert any("fake-bank.in" in u for u in urls)
    assert any("scam-trade.com" in u for u in urls)
    assert all(u.startswith("https://") for u in urls)
    assert result["method"] == "REGEX_ONLY"


def test_extract_order_id_ambiguity_llm() -> None:
    """Order #9876543210 -> LLM escalation when llm_client set."""
    mock_llm = Mock()
    mock_llm.generate.return_value = """{
        "phones": ["+919876543210"],
        "upis": [],
        "urls": [],
        "confidence": "HIGH"
    }"""
    agent = ExtractionAgent(llm_client=mock_llm)
    result = agent.extract("Order #9876543210 failed")
    assert result["method"] == "HYBRID"
    mock_llm.generate.assert_called_once()


def test_extract_standalone_phone_llm() -> None:
    """Standalone 9876543210 without other context -> LLM when llm_client set."""
    mock_llm = Mock()
    mock_llm.generate.return_value = """{"phones": [], "upis": [], "urls": [], "confidence": "LOW"}"""
    agent = ExtractionAgent(llm_client=mock_llm)
    result = agent.extract("Contact 9876543210 support")
    assert result["method"] == "HYBRID"
    mock_llm.generate.assert_called_once()


def test_extract_empty_message() -> None:
    agent = ExtractionAgent()
    result = agent.extract("")
    assert result["method"] == "EMPTY"
    assert result["phones"] == []
    assert result["upis"] == []
    assert result["urls"] == []


def test_extract_no_llm_client_fallback() -> None:
    """No LLM client -> ambiguous text returns REGEX_EMPTY."""
    agent = ExtractionAgent()
    result = agent.extract("Order #9876543210 failed")
    assert result["method"] == "REGEX_EMPTY"
    assert not result["phones"]


def test_extract_process_base_agent() -> None:
    """process() delegates to extract() for BaseAgent compatibility."""
    agent = ExtractionAgent()
    result = agent.process("Call +91 9876543210")
    assert "phones" in result
    assert result["phones"] == ["919876543210"]
    assert result["method"] == "REGEX_ONLY"


# --- extract_intelligence() tests (full schema) ---


def test_phone_number_extraction() -> None:
    """Test phone number extraction (various formats)."""
    agent = ExtractionAgent()

    test_cases = [
        ("Call +91 9876543210", ["+919876543210"]),
        ("WhatsApp 9876543210", ["+919876543210"]),
        ("Contact: +91-98765-43210", ["+919876543210"]),
        ("Toll-free: 1800-123456", ["1800123456"]),
        ("Call 98765 43210 or 87654 32109", 2),  # expect at least 2 phones
    ]

    for message, expected in test_cases:
        result = agent.extract_intelligence(message)
        phones = result["identityMarkers"]["phoneNumbers"]
        print(f"Message: {message}")
        print(f"Extracted: {phones}")
        if isinstance(expected, list):
            assert len(phones) >= len(expected), (
                f"Expected at least {len(expected)}, got {len(phones)}"
            )
        else:
            assert len(phones) >= expected, (
                f"Expected at least {expected}, got {len(phones)}"
            )


def test_upi_id_extraction() -> None:
    """Test UPI ID extraction."""
    agent = ExtractionAgent()

    test_cases = [
        "Send payment to scammer@paytm",
        "My UPI: fraud@phonepe",
        "Transfer to 9876543210@paytm",
        "Use payment@ybl or backup@okaxis",
    ]

    for message in test_cases:
        result = agent.extract_intelligence(message)
        upi_ids = result["identityMarkers"]["upiIds"]
        print(f"Message: {message}")
        print(f"UPI IDs: {upi_ids}")
        assert len(upi_ids) > 0, "Should extract at least one UPI ID"


def test_url_extraction() -> None:
    """Test URL and domain extraction."""
    agent = ExtractionAgent()

    test_cases = [
        ("Click http://fake-bank.com/login", ["fake-bank.com"]),
        ("Verify: https://bit.ly/abc123", ["bit.ly"]),
        ("Visit https://www.scam-site.xyz/verify", ["www.scam-site.xyz"]),
    ]

    for message, expected_domains in test_cases:
        result = agent.extract_intelligence(message)
        domains = result["infrastructure"]["phishingDomains"]
        urls = result["infrastructure"]["phishingUrls"]
        print(f"Message: {message}")
        print(f"Domains: {domains}, URLs: {urls}")
        assert len(domains) > 0 or len(urls) > 0, "Should extract domain or URL"


def test_psychological_tactics() -> None:
    """Test psychological tactic detection."""
    agent = ExtractionAgent()

    # Urgency
    message1 = "Immediate action required! Account expires in 2 hours!"
    result1 = agent.extract_intelligence(message1)
    assert len(result1["psychologicalTactics"]["urgencyExploitation"]) >= 2

    # Authority
    message2 = "This is RBI official notification from NPCI security team"
    result2 = agent.extract_intelligence(message2)
    assert len(result2["psychologicalTactics"]["authorityMimicry"]) >= 2

    # Threats
    message3 = "Your account will be blocked and legal action will be taken"
    result3 = agent.extract_intelligence(message3)
    assert len(result3["psychologicalTactics"]["threatPatterns"]) >= 2


def test_comprehensive_message() -> None:
    """Test extraction from complex message with multiple elements."""
    agent = ExtractionAgent()

    message = """
    URGENT! Your UPI account @paytm is blocked by RBI.
    Call customer care immediately: +91-9876543210
    Verify here: http://fake-npci.com/verify
    Email: support@scam.com
    Account will be terminated in 2 hours!
    """

    result = agent.extract_intelligence(message)

    print("\n=== Comprehensive Test Results ===")
    print(f"Phone Numbers: {result['identityMarkers']['phoneNumbers']}")
    print(f"UPI IDs: {result['identityMarkers']['upiIds']}")
    print(f"Emails: {result['identityMarkers']['emailAddresses']}")
    print(f"Domains: {result['infrastructure']['phishingDomains']}")
    print(f"URLs: {result['infrastructure']['phishingUrls']}")
    print(f"Urgency: {result['psychologicalTactics']['urgencyExploitation']}")
    print(f"Authority: {result['psychologicalTactics']['authorityMimicry']}")
    print(f"Threats: {result['psychologicalTactics']['threatPatterns']}")

    assert len(result["identityMarkers"]["phoneNumbers"]) >= 1
    assert len(result["identityMarkers"]["upiIds"]) >= 1
    assert len(result["identityMarkers"]["emailAddresses"]) >= 1
    assert len(result["infrastructure"]["phishingDomains"]) >= 1
    assert len(result["psychologicalTactics"]["urgencyExploitation"]) >= 2
    assert len(result["psychologicalTactics"]["authorityMimicry"]) >= 1
    assert len(result["psychologicalTactics"]["threatPatterns"]) >= 1


def test_20_sample_messages() -> None:
    """Test extraction on 20 diverse scam messages."""
    agent = ExtractionAgent()

    messages = [
        "Your UPI @paytm blocked. Call 9876543210 now!",
        "NPCI alert: Verify your phonepe@ybl ID immediately",
        "Click here to update account: http://fake-sbi.com/login",
        "Your package: https://bit.ly/track123",
        "Suspicious login! Reset password: www.fake-bank.in",
        "KYC pending. WhatsApp +91-9988776655",
        "Download AnyDesk app. Refund Rs. 5000 pending",
        "Customer care: 1800-555-1234. Service fee: Rs.500",
        "Earn Rs 1 lakh! Join: invest@paytm. Guaranteed profit!",
        "Trading account: signup.scam-trade.com",
        "Congratulations! Won Rs 50000. Pay Rs 500 processing fee",
        "Claim prize: lucky@phonepe or call 9123456789",
        "URGENT: Account A/C 123456789012 blocked by RBI",
        "Transfer to SBIN0001234, IFSC code required",
        "Email proof to verify@scam.org within 24 hours",
        "Limited time! Rs. 10,000 cashback. Act now!",
        "Official helpline 1800-SCAM-123. Don't delay!",
        "Your OTP: Share 123456 to customer.support@fake.in",
        "Payment gateway: razorpay-fake.com. Safe & secure!",
        "Download from play.google-fake.com/anydesk-pro",
    ]

    print("\n=== Testing 20 Sample Messages ===\n")
    total_extracted = 0

    for i, msg in enumerate(messages, 1):
        result = agent.extract_intelligence(msg)

        artifacts = (
            len(result["identityMarkers"]["phoneNumbers"])
            + len(result["identityMarkers"]["emailAddresses"])
            + len(result["identityMarkers"]["upiIds"])
            + len(result["identityMarkers"]["bankAccounts"])
            + len(result["infrastructure"]["phishingUrls"])
            + len(result["infrastructure"]["phishingDomains"])
        )

        total_extracted += artifacts

        print(f"Message {i}: {msg[:50]}...")
        print(f"  Artifacts: {artifacts}")
        if artifacts > 0:
            print("  [OK] Extraction successful")
        else:
            print("  [--] No artifacts (may be expected for some messages)")

    print(f"\nTotal artifacts extracted: {total_extracted}")
    print(f"Average per message: {total_extracted / len(messages):.2f}")

    assert total_extracted >= 15, (
        f"Should extract at least 15 artifacts from 20 messages, got {total_extracted}"
    )


if __name__ == "__main__":
    print("Testing ExtractionAgent...\n")
    test_phone_number_extraction()
    print("\n" + "=" * 50 + "\n")
    test_upi_id_extraction()
    print("\n" + "=" * 50 + "\n")
    test_url_extraction()
    print("\n" + "=" * 50 + "\n")
    test_psychological_tactics()
    print("\n" + "=" * 50 + "\n")
    test_comprehensive_message()
    print("\n" + "=" * 50 + "\n")
    test_20_sample_messages()
    print("\n[OK] All ExtractionAgent tests passed!")
