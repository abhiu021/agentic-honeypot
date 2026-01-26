from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class Message(BaseModel):
    """Single message in conversation"""
    sender: Literal["scammer", "user"]
    text: str
    timestamp: datetime = Field(default_factory=datetime.now)

class Metadata(BaseModel):
    """Request metadata - GUVI spec"""
    channel: Optional[str] = "SMS"  # SMS, WhatsApp, Email, Chat
    language: Optional[str] = "English"
    locale: Optional[str] = "IN"

class HoneypotRequest(BaseModel):
    """Incoming request schema - GUVI specification"""
    sessionId: str = Field(..., min_length=5, description="Unique session identifier")
    message: Message
    conversationHistory: List[Message] = Field(default_factory=list)
    metadata: Optional[Metadata] = Field(default_factory=Metadata)

class EngagementMetrics(BaseModel):
    """Engagement tracking metrics"""
    engagementDurationSeconds: int
    totalMessagesExchanged: int
    userEngagementPhase: str
    intelligenceValueRemaining: float = Field(..., ge=0.0, le=1.0)
    recommendedNextAction: Literal["CONTINUE_ENGAGEMENT", "TERMINATE", "HUMAN_REVIEW"]

class KillChainAnalysis(BaseModel):
    """Kill-chain state analysis"""
    detectedScamType: str
    estimatedKillChainStep: int
    stageName: str
    stageObjective: str
    nextPredictedStep: int
    killChainCompletion: float = Field(..., ge=0.0, le=100.0)

class IdentityMarkers(BaseModel):
    """Extracted identity intelligence"""
    phoneNumbers: List[str] = Field(default_factory=list)
    emailAddresses: List[str] = Field(default_factory=list)
    bankAccounts: List[str] = Field(default_factory=list)
    upiIds: List[str] = Field(default_factory=list)
    deviceFingerprints: List[str] = Field(default_factory=list)

class Infrastructure(BaseModel):
    """Extracted infrastructure intelligence"""
    phishingDomains: List[str] = Field(default_factory=list)
    phishingUrls: List[str] = Field(default_factory=list)
    suspiciousGateways: List[str] = Field(default_factory=list)

class PsychologicalTactics(BaseModel):
    """Extracted psychological manipulation tactics"""
    urgencyExploitation: List[str] = Field(default_factory=list)
    authorityMimicry: List[str] = Field(default_factory=list)
    threatPatterns: List[str] = Field(default_factory=list)
    scarcityTactics: List[str] = Field(default_factory=list)

class ExtractedIntelligence(BaseModel):
    """Complete intelligence extraction"""
    identityMarkers: IdentityMarkers = Field(default_factory=IdentityMarkers)
    infrastructure: Infrastructure = Field(default_factory=Infrastructure)
    psychologicalTactics: PsychologicalTactics = Field(default_factory=PsychologicalTactics)
    suspiciousKeywords: List[str] = Field(default_factory=list)

class AgentResponse(BaseModel):
    """Agent-generated response"""
    message: str
    responseGeneratedBy: str = "ENGAGEMENT_AGENT"
    personaUsed: str
    intentionBehindResponse: str

class HoneypotResponse(BaseModel):
    """API response schema - GUVI specification + internal intelligence"""
    status: Literal["success", "error"]
    scamDetected: bool
    scamConfidenceScore: float = Field(..., ge=0.0, le=1.0)
    engagementMetrics: EngagementMetrics
    killChainAnalysis: Optional[KillChainAnalysis] = None
    extractedIntelligence: ExtractedIntelligence
    agentResponse: AgentResponse
    agentNotes: str

class ErrorResponse(BaseModel):
    """Error response schema"""
    status: Literal["error"]
    message: str
    details: Optional[dict] = None
