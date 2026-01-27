from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class LLMConfig:
    """LLM client configuration from environment variables."""
    
    def __init__(self):
        self.provider: str = os.getenv("LLM_PROVIDER", "gemini").lower()
        self.timeout: int = int(os.getenv("LLM_TIMEOUT", "3"))
        self.max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
        self.temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "150"))
        
        # Provider-specific settings
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
        
        self.gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
        self.gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    def get_api_key(self) -> str:
        """Get API key for configured provider."""
        if self.provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set in environment")
            return self.openai_api_key
        elif self.provider == "gemini":
            if not self.gemini_api_key:
                raise ValueError("GEMINI_API_KEY not set in environment")
            return self.gemini_api_key
        elif self.provider == "mock":
            return "mock-key-not-needed"
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def get_model(self) -> str:
        """Get model name for configured provider."""
        if self.provider == "openai":
            return self.openai_model
        elif self.provider == "gemini":
            return self.gemini_model
        else:
            return "mock-model"


class APIConfig:
    """API configuration from environment variables."""
    
    def __init__(self):
        self.api_key: str = os.getenv("API_KEY", "sk-test-honeypot-2026")
        self.guvi_callback_url: str = os.getenv(
            "GUVI_CALLBACK_URL",
            "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
        )


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

# Global configuration instances
llm_config = LLMConfig()
api_config = APIConfig()
