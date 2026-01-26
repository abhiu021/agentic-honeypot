from fastapi import APIRouter, Depends, HTTPException, Request
from api.schemas import HoneypotRequest, HoneypotResponse, ErrorResponse, EngagementMetrics, AgentResponse, ExtractedIntelligence
from api.middleware import verify_api_key
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def validate_request(request: HoneypotRequest):
    """
    Validate incoming request structure and content.
    Raises HTTPException if validation fails.
    """
    # Session ID validation
    if not request.sessionId or len(request.sessionId) < 5:
        raise HTTPException(
            status_code=400,
            detail="sessionId must be at least 5 characters"
        )
    
    # Message text validation
    if not request.message.text or len(request.message.text.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="message.text cannot be empty"
        )
    
    # Sender validation
    if request.message.sender != "scammer":
        raise HTTPException(
            status_code=400,
            detail="message.sender must be 'scammer' for incoming messages"
        )
    
    # Conversation history validation
    for msg in request.conversationHistory:
        if not msg.text or msg.sender not in ["scammer", "user"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid conversationHistory format"
            )
    
    return True

@router.post("/api/honeypot", response_model=HoneypotResponse, responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}})
async def honeypot_endpoint(
    request: HoneypotRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Main honeypot endpoint for scam engagement.
    
    This endpoint orchestrates all 5 agents to:
    1. Detect scam type and calculate threat score
    2. Plan engagement strategy based on kill-chain stage
    3. Generate human-like response using selected persona
    4. Extract intelligence (phones, UPIs, URLs, tactics)
    5. Validate response for ethical compliance
    
    **GUVI Spec Compliant**: Accepts and returns exact schemas required by buildathon evaluation.
    """
    try:
        # Validate request structure
        validate_request(request)
        
        logger.info(f"Processing message for session: {request.sessionId}")
        
        # TODO: Day 2-5 - Implement full agent orchestration here
        # For now, return mock response to test API structure
        
        return HoneypotResponse(
            status="success",
            scamDetected=True,
            scamConfidenceScore=0.85,
            engagementMetrics=EngagementMetrics(
                engagementDurationSeconds=120,
                totalMessagesExchanged=3,
                userEngagementPhase="CREDIBILITY_ESTABLISHMENT",
                intelligenceValueRemaining=0.75,
                recommendedNextAction="CONTINUE_ENGAGEMENT"
            ),
            extractedIntelligence=ExtractedIntelligence(),
            agentResponse=AgentResponse(
                message="I'm concerned about this. Can you provide more details?",
                responseGeneratedBy="ENGAGEMENT_AGENT",
                personaUsed="AVERAGE_USER",
                intentionBehindResponse="Build trust while seeking verification"
            ),
            agentNotes="Scam detected with high confidence. Continuing engagement to extract intelligence."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
