from fastapi import APIRouter, Depends, HTTPException, Request
from api.schemas import HoneypotRequest, HoneypotResponse, ErrorResponse, EngagementMetrics, AgentResponse, ExtractedIntelligence
from api.middleware import verify_api_key
from agents import initialize_agent_pipeline
from orchestration import process_message
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy LLM client for orchestration (optional)
_llm_client = None

def _get_llm_client():
    global _llm_client
    if _llm_client is not None:
        return _llm_client
    try:
        from config import LLMConfig
        from utils.llm_client import LLMClient
        cfg = LLMConfig()
        _llm_client = LLMClient.create(
            cfg.provider,
            api_key=cfg.get_api_key(),
            model=cfg.get_model(),
            timeout=cfg.timeout,
        )
        return _llm_client
    except Exception as e:
        logger.warning("LLM client not available: %s. Engagement will use fallbacks.", e)
        return None

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
        validate_request(request)
        logger.info("Processing message for session: %s", request.sessionId)
        llm_client = _get_llm_client()
        agents = initialize_agent_pipeline(llm_client=llm_client)
        response = process_message(request, agents)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Orchestration failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error: %s" % str(e))
