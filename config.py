from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    API_KEY: str = "sk_test_honeypot_2026"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # LLM Provider Configuration
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "openai"  # "openai" or "anthropic"
    LLM_MODEL: str = "gpt-4"
    
    # Session Configuration
    SESSION_TIMEOUT_MINUTES: int = 30
    MAX_CONVERSATION_TURNS: int = 20
    
    # GUVI Integration
    GUVI_CALLBACK_URL: str = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    GUVI_CALLBACK_ENABLED: bool = True
    
    # Detection Thresholds
    SCAM_DETECTION_THRESHOLD: float = 0.45
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
