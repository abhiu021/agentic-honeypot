from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

class SessionMemory(BaseModel):
    sessionId: str
    scamType: Optional[str] = None
    killChainState: Optional[Any] = None
    conversationHistory: List[Dict] = Field(default_factory=list)
    extractedIntelligence: Dict = Field(default_factory=lambda: {
        "identityMarkers": {
            "phoneNumbers": [],
            "emailAddresses": [],
            "bankAccounts": [],
            "upiIds": []
        },
        "infrastructure": {
            "phishingDomains": [],
            "phishingUrls": []
        },
        "psychologicalTactics": {
            "urgencyExploitation": [],
            "authorityMimicry": [],
            "threatPatterns": [],
            "scarcityTactics": []
        },
        "suspiciousKeywords": []
    })
    totalMessagesExchanged: int = 0
    sessionStartTime: datetime = Field(default_factory=datetime.now)
    lastActivityTime: datetime = Field(default_factory=datetime.now)
    scammerProfile: Dict = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True
