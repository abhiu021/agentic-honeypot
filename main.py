from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from api.middleware import log_requests
from config import settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Agentic Honeypot API",
    description="Multi-agent scam detection and intelligence extraction system for GUVI AI Impact Buildathon",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.middleware("http")(log_requests)

# Include API routes
app.include_router(router)

# Global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": f"Internal server error: {str(exc)}"
        }
    )

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify API is running.
    Returns system status and configuration info.
    """
    return {
        "status": "healthy",
        "service": "Agentic Honeypot API",
        "version": "1.0.0",
        "llm_provider": settings.LLM_PROVIDER,
        "scam_types_supported": [
            "UPI_FRAUD",
            "ACCOUNT_TAKEOVER",
            "FAKE_CUSTOMER_SUPPORT",
            "PHISHING",
            "INVESTMENT_SCAM",
            "FAKE_OFFER"
        ],
        "agents": 5,
        "kill_chains": 6
    }

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Agentic Honeypot API - GUVI AI Impact Buildathon 2026",
        "docs": "/docs",
        "health": "/health",
        "main_endpoint": "/api/honeypot"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )
