from fastapi import Header, HTTPException, Request
from fastapi.responses import JSONResponse
from config import settings
import time
import logging

logger = logging.getLogger(__name__)

async def verify_api_key(x_api_key: str = Header(..., description="API authentication key")):
    """
    Validate API key from request header.
    Required for all protected endpoints.
    """
    valid_key = settings.API_KEY
    
    if x_api_key != valid_key:
        logger.warning(f"Invalid API key attempt: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key. Provide valid x-api-key header."
        )
    
    return x_api_key

async def log_requests(request: Request, call_next):
    """
    Middleware to log all incoming requests for debugging.
    """
    start_time = time.time()
    
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"Request completed in {process_time:.2f}s with status {response.status_code}")
    
    return response
