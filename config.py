from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv
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
        self.gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
        self.gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
        # Prefer llama-3.1-8b-instant (current); llama3-8b-8192 can return 400 on some accounts
        self.groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    
    def get_api_key(self) -> str:
        """Get API key for configured provider."""
        if self.provider == "gemini":
            if not self.gemini_api_key:
                raise ValueError("GEMINI_API_KEY not set in environment")
            return self.gemini_api_key
        elif self.provider == "groq":
            if not self.groq_api_key:
                raise ValueError("GROQ_API_KEY not set in environment")
            return self.groq_api_key
        elif self.provider == "mock":
            return "mock-key-not-needed"
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def get_model(self) -> str:
        """Get model name for configured provider."""
        if self.provider == "gemini":
            return self.gemini_model
        elif self.provider == "groq":
            return self.groq_model
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
    model_config = ConfigDict(extra="ignore", env_file=".env", case_sensitive=True)

    # API Configuration
    API_KEY: str = "sk_test_honeypot_2026"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # LLM Provider Configuration
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "gemini"  # "gemini" or "mock"
    LLM_MODEL: str = "gemini-1.5-flash"
    GROQ_API_KEY: str = Field(default="", description="Groq API key")
    GROQ_MODEL: str = Field(default="llama-3.1-8b-instant", description="Groq model")
    LLM_TIMEOUT: int = Field(default=5, description="LLM request timeout (seconds)")
    LLM_MAX_RETRIES: int = Field(default=3, description="LLM max retries")
    LLM_TEMPERATURE: float = Field(default=0.1, description="LLM temperature")
    LLM_MAX_TOKENS: int = Field(default=200, description="LLM max tokens")

    # Session Configuration
    SESSION_TIMEOUT_MINUTES: int = 30
    MAX_CONVERSATION_TURNS: int = 20

    # GUVI Integration
    GUVI_CALLBACK_URL: str = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    GUVI_CALLBACK_ENABLED: bool = True

    # Detection Thresholds
    SCAM_DETECTION_THRESHOLD: float = 0.45
    HIGH_CONFIDENCE_THRESHOLD: float = Field(default=0.60, description="High confidence threshold")

settings = Settings()

# Global configuration instances
llm_config = LLMConfig()
api_config = APIConfig()
