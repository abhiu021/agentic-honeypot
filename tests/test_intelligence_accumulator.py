"""
Tests for IntelligenceAccumulator - merge and cumulative intelligence.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.intelligence_accumulator import IntelligenceAccumulator


def _empty_intelligence() -> dict:
    """Return empty intelligence structure matching SessionMemory."""
    return {
        "identityMarkers": {
            "phoneNumbers": [],
            "emailAddresses": [],
            "upiIds": [],
            "bankAccounts": [],
        },
        "infrastructure": {
            "phishingDomains": [],
            "phishingUrls": [],
            "suspiciousGateways": [],
        },
        "psychologicalTactics": {
            "urgencyExploitation": [],
            "authorityMimicry": [],
            "threatPatterns": [],
            "scarcityTactics": [],
        },
        "suspiciousKeywords": [],
    }


def test_merge_phone_numbers() -> None:
    """Test merging phone numbers without duplicates."""
    existing = _empty_intelligence()
    existing["identityMarkers"]["phoneNumbers"] = ["+919876543210"]

    new = _empty_intelligence()
    new["identityMarkers"]["phoneNumbers"] = ["+919876543210", "+918765432109"]

    merged = IntelligenceAccumulator.merge_intelligence(existing, new)

    print(f"Merged phones: {merged['identityMarkers']['phoneNumbers']}")
    assert len(merged["identityMarkers"]["phoneNumbers"]) == 2
    assert "+919876543210" in merged["identityMarkers"]["phoneNumbers"]
    assert "+918765432109" in merged["identityMarkers"]["phoneNumbers"]


def test_cumulative_extraction() -> None:
    """Test cumulative intelligence across 3 messages."""
    intelligence = _empty_intelligence()

    # Message 1
    new1 = _empty_intelligence()
    new1["identityMarkers"]["phoneNumbers"] = ["+919876543210"]
    new1["identityMarkers"]["upiIds"] = ["scam@paytm"]
    new1["psychologicalTactics"]["urgencyExploitation"] = ["immediate"]
    intelligence = IntelligenceAccumulator.merge_intelligence(
        intelligence, new1
    )

    # Message 2
    new2 = _empty_intelligence()
    new2["identityMarkers"]["emailAddresses"] = ["fake@scam.com"]
    new2["infrastructure"]["phishingDomains"] = ["fake-bank.com"]
    new2["infrastructure"]["phishingUrls"] = ["http://fake-bank.com"]
    new2["psychologicalTactics"]["authorityMimicry"] = ["rbi"]
    intelligence = IntelligenceAccumulator.merge_intelligence(
        intelligence, new2
    )

    # Message 3 (duplicate phone)
    new3 = _empty_intelligence()
    new3["identityMarkers"]["phoneNumbers"] = ["+919876543210"]
    new3["psychologicalTactics"]["threatPatterns"] = ["blocked"]
    intelligence = IntelligenceAccumulator.merge_intelligence(
        intelligence, new3
    )

    print("\n=== Cumulative Intelligence ===")
    print(f"Phones: {intelligence['identityMarkers']['phoneNumbers']}")
    print(f"Emails: {intelligence['identityMarkers']['emailAddresses']}")
    print(f"UPI IDs: {intelligence['identityMarkers']['upiIds']}")
    print(f"Domains: {intelligence['infrastructure']['phishingDomains']}")
    print(f"Urgency: {intelligence['psychologicalTactics']['urgencyExploitation']}")
    print(f"Authority: {intelligence['psychologicalTactics']['authorityMimicry']}")
    print(f"Threats: {intelligence['psychologicalTactics']['threatPatterns']}")

    assert len(intelligence["identityMarkers"]["phoneNumbers"]) == 1
    assert len(intelligence["identityMarkers"]["emailAddresses"]) == 1
    assert len(intelligence["identityMarkers"]["upiIds"]) == 1
    assert len(intelligence["infrastructure"]["phishingDomains"]) == 1
    assert len(intelligence["psychologicalTactics"]["urgencyExploitation"]) == 1
    assert len(intelligence["psychologicalTactics"]["authorityMimicry"]) == 1
    assert len(intelligence["psychologicalTactics"]["threatPatterns"]) == 1


def test_get_intelligence_summary() -> None:
    """Test summary statistics."""
    intelligence = _empty_intelligence()
    intelligence["identityMarkers"]["phoneNumbers"] = ["+919876543210", "+918765432109"]
    intelligence["identityMarkers"]["upiIds"] = ["scam@paytm"]
    intelligence["infrastructure"]["phishingUrls"] = ["http://fake.com"]
    intelligence["psychologicalTactics"]["urgencyExploitation"] = ["urgent"]
    intelligence["psychologicalTactics"]["authorityMimicry"] = ["rbi"]

    summary = IntelligenceAccumulator.get_intelligence_summary(intelligence)

    assert summary["totalArtifacts"] == 4
    assert summary["phoneNumbersCount"] == 2
    assert summary["upiIdsCount"] == 1
    assert summary["urlsCount"] == 1
    assert "urgency" in summary["tacticsUsed"]
    assert "authority" in summary["tacticsUsed"]


if __name__ == "__main__":
    test_merge_phone_numbers()
    print("\n[OK] Merge test passed")
    test_cumulative_extraction()
    print("\n[OK] Cumulative test passed")
    test_get_intelligence_summary()
    print("\n[OK] All accumulator tests passed!")
