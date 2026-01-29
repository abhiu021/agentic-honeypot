"""
Intelligence Accumulator - Merge intelligence from multiple messages.

Handles deduplication and cumulative updates for session intelligence.
Matches SessionMemory.extractedIntelligence structure.
"""

from typing import Dict, List


class IntelligenceAccumulator:
    """
    Merges intelligence from multiple messages.
    Handles deduplication and cumulative updates.
    """

    @staticmethod
    def merge_intelligence(existing: Dict, new: Dict) -> Dict:
        """
        Merge new intelligence into existing intelligence.

        Args:
            existing: Current session intelligence (from SessionMemory)
            new: Newly extracted intelligence (from ExtractionAgent)

        Returns:
            Merged intelligence dictionary
        """
        merged = {
            "identityMarkers": {
                "phoneNumbers": IntelligenceAccumulator._merge_lists(
                    existing["identityMarkers"]["phoneNumbers"],
                    new["identityMarkers"]["phoneNumbers"],
                ),
                "emailAddresses": IntelligenceAccumulator._merge_lists(
                    existing["identityMarkers"]["emailAddresses"],
                    new["identityMarkers"]["emailAddresses"],
                ),
                "upiIds": IntelligenceAccumulator._merge_lists(
                    existing["identityMarkers"]["upiIds"],
                    new["identityMarkers"]["upiIds"],
                ),
                "bankAccounts": IntelligenceAccumulator._merge_lists(
                    existing["identityMarkers"]["bankAccounts"],
                    new["identityMarkers"]["bankAccounts"],
                ),
            },
            "infrastructure": {
                "phishingDomains": IntelligenceAccumulator._merge_lists(
                    existing["infrastructure"]["phishingDomains"],
                    new["infrastructure"]["phishingDomains"],
                ),
                "phishingUrls": IntelligenceAccumulator._merge_lists(
                    existing["infrastructure"]["phishingUrls"],
                    new["infrastructure"]["phishingUrls"],
                ),
                "suspiciousGateways": IntelligenceAccumulator._merge_lists(
                    existing["infrastructure"].get("suspiciousGateways", []),
                    new["infrastructure"].get("suspiciousGateways", []),
                ),
            },
            "psychologicalTactics": {
                "urgencyExploitation": IntelligenceAccumulator._merge_lists(
                    existing["psychologicalTactics"]["urgencyExploitation"],
                    new["psychologicalTactics"]["urgencyExploitation"],
                ),
                "authorityMimicry": IntelligenceAccumulator._merge_lists(
                    existing["psychologicalTactics"]["authorityMimicry"],
                    new["psychologicalTactics"]["authorityMimicry"],
                ),
                "threatPatterns": IntelligenceAccumulator._merge_lists(
                    existing["psychologicalTactics"]["threatPatterns"],
                    new["psychologicalTactics"]["threatPatterns"],
                ),
                "scarcityTactics": IntelligenceAccumulator._merge_lists(
                    existing["psychologicalTactics"]["scarcityTactics"],
                    new["psychologicalTactics"]["scarcityTactics"],
                ),
            },
            "suspiciousKeywords": IntelligenceAccumulator._merge_lists(
                existing["suspiciousKeywords"],
                new["suspiciousKeywords"],
            ),
        }

        return merged

    @staticmethod
    def _merge_lists(existing: List, new: List) -> List:
        """Merge two lists, removing duplicates while preserving order."""
        merged_dict: Dict[str, None] = {item: None for item in existing}
        merged_dict.update({item: None for item in new})
        return list(merged_dict.keys())

    @staticmethod
    def get_intelligence_summary(intelligence: Dict) -> Dict:
        """
        Get summary statistics of extracted intelligence.

        Returns:
            {
                "totalArtifacts": 15,
                "phoneNumbersCount": 2,
                "upiIdsCount": 1,
                "urlsCount": 3,
                "tacticsUsed": ["urgency", "authority"]
            }
        """
        total = 0
        total += len(intelligence["identityMarkers"]["phoneNumbers"])
        total += len(intelligence["identityMarkers"]["emailAddresses"])
        total += len(intelligence["identityMarkers"]["upiIds"])
        total += len(intelligence["identityMarkers"]["bankAccounts"])
        total += len(intelligence["infrastructure"]["phishingUrls"])

        tactics_used: List[str] = []
        if intelligence["psychologicalTactics"]["urgencyExploitation"]:
            tactics_used.append("urgency")
        if intelligence["psychologicalTactics"]["authorityMimicry"]:
            tactics_used.append("authority")
        if intelligence["psychologicalTactics"]["threatPatterns"]:
            tactics_used.append("threats")
        if intelligence["psychologicalTactics"]["scarcityTactics"]:
            tactics_used.append("scarcity")

        return {
            "totalArtifacts": total,
            "phoneNumbersCount": len(
                intelligence["identityMarkers"]["phoneNumbers"]
            ),
            "emailAddressesCount": len(
                intelligence["identityMarkers"]["emailAddresses"]
            ),
            "upiIdsCount": len(intelligence["identityMarkers"]["upiIds"]),
            "bankAccountsCount": len(
                intelligence["identityMarkers"]["bankAccounts"]
            ),
            "urlsCount": len(intelligence["infrastructure"]["phishingUrls"]),
            "domainsCount": len(
                intelligence["infrastructure"]["phishingDomains"]
            ),
            "tacticsUsed": tactics_used,
        }
