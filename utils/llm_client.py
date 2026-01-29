from abc import ABC, abstractmethod
from typing import Dict, Optional, List
import time
import json
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import httpx


class BaseLLMClient(ABC):
    """
    Abstract base class for all LLM client implementations.
    Provides unified interface for Gemini, Groq, and mock clients.
    """
    
    def __init__(self, api_key: str, timeout: int = 3):
        """
        Initialize base LLM client.
        
        Args:
            api_key: API key for the LLM provider
            timeout: Request timeout in seconds (default: 3)
        """
        self.api_key = api_key
        self.timeout = timeout
        self.total_tokens = 0
        self.total_cost = 0.0
    
    @abstractmethod
    def generate(
        self, 
        prompt: str, 
        temperature: float = 0.7,
        max_tokens: int = 150,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate completion from a single prompt.
        
        Args:
            prompt: User prompt text
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt for behavior control
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 150
    ) -> str:
        """
        Generate completion from chat message history.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate API cost based on token usage.
        
        Args:
            prompt_tokens: Number of tokens in prompt
            completion_tokens: Number of tokens in completion
            
        Returns:
            Cost in USD
        """
        pass
    
    def get_usage_stats(self) -> Dict:
        """
        Return token usage and cost statistics.
        
        Returns:
            Dict with 'total_tokens' and 'total_cost_usd' keys
        """
        return {
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 4)
        }


class GeminiLLMClient(BaseLLMClient):
    """
    Google Gemini client wrapper with retry logic and cost tracking.
    Supports Gemini 2.x Flash/Pro models (e.g. gemini-2.0-flash, gemini-2.5-flash).
    """
    
    # Pricing per 1M tokens (approximate; gemini-2.0-flash as default)
    PRICING = {
        "gemini-2.0-flash": {"input": 0.15, "output": 0.60},
        "gemini-2.0-flash-001": {"input": 0.15, "output": 0.60},
        "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
        "gemini-2.5-flash-lite": {"input": 0.075, "output": 0.30},
        "gemini-2.5-pro": {"input": 3.5, "output": 10.5},
        "gemini-1.5-flash": {"input": 0.35, "output": 1.05},
        "gemini-1.5-pro": {"input": 3.5, "output": 10.5},
        "gemini-pro": {"input": 0.5, "output": 1.5},
    }
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        timeout: int = 3,
        max_retries: int = 3
    ):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google AI API key
            model: Model name (default: gemini-2.0-flash; use a v1beta-supported model)
            timeout: Request timeout in seconds (default: 3)
            max_retries: Maximum retry attempts for failed requests (default: 3)
        """
        super().__init__(api_key, timeout)
        self.model = model
        self.max_retries = max_retries
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(self.model)
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate completion from a single prompt.
        Gemini uses system instruction in model configuration.
        """
        # Combine system prompt with user prompt if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}"
        
        return self._generate_with_retry(
            prompt=full_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 150
    ) -> str:
        """
        Generate completion from chat messages.
        Converts chat format to Gemini conversation format.
        """
        # Convert messages to prompt format
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                prompt_parts.insert(0, f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        full_prompt = "\n\n".join(prompt_parts)
        
        return self._generate_with_retry(
            prompt=full_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def _generate_with_retry(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """
        Internal method for generation with retry logic.
        Implements exponential backoff for rate limits.
        """
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.generate_content(
                    prompt,
                    generation_config=generation_config,
                    request_options={'timeout': self.timeout}
                )
                
                # Track token usage if available
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    usage = response.usage_metadata
                    prompt_tokens = getattr(usage, 'prompt_token_count', 0)
                    completion_tokens = getattr(usage, 'candidates_token_count', 0)
                    
                    self.total_tokens += (prompt_tokens + completion_tokens)
                    self.total_cost += self.calculate_cost(prompt_tokens, completion_tokens)
                
                # Extract text from response
                if response.candidates and len(response.candidates) > 0:
                    return response.candidates[0].content.parts[0].text
                else:
                    return response.text
                
            except google_exceptions.ResourceExhausted as e:
                # Rate limit error
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Gemini rate limit exceeded after {self.max_retries} attempts: {e}")
            
            except google_exceptions.DeadlineExceeded as e:
                # Timeout error
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                else:
                    raise Exception(f"Gemini timeout after {self.max_retries} attempts: {e}")
            
            except Exception as e:
                raise Exception(f"Gemini API error: {e}")
        
        raise Exception("Gemini generation failed after all retry attempts")
    
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate API cost in USD based on token usage.
        Uses model-specific pricing from PRICING constant.
        """
        pricing = self.PRICING.get(self.model, self.PRICING["gemini-2.0-flash"])
        
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost


class GroqLLMClient(BaseLLMClient):
    """
    Groq API client wrapper (OpenAI-compatible).
    Uses https://api.groq.com/openai/v1/chat/completions. Default model: llama3-8b-8192.
    """
    BASE_URL = "https://api.groq.com/openai/v1"
    PRICING = {
        "llama3-8b-8192": {"input": 0.05, "output": 0.10},
        "llama3-70b-8192": {"input": 0.59, "output": 0.79},
        "mixtral-8x7b-32768": {"input": 0.24, "output": 0.24},
    }

    def __init__(
        self,
        api_key: str,
        model: str = "llama3-8b-8192",
        timeout: int = 3,
        max_retries: int = 3
    ):
        super().__init__(api_key, timeout)
        self.model = model
        self.max_retries = max_retries

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
        system_prompt: Optional[str] = None
    ) -> str:
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat_completion(messages, temperature=temperature, max_tokens=max_tokens)

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 150
    ) -> str:
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=float(self.timeout)) as client:
                    resp = client.post(
                        f"{self.BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        },
                    )
                resp.raise_for_status()
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                msg = choice.get("message", {})
                content = msg.get("content") or ""
                usage = data.get("usage", {})
                pt = usage.get("prompt_tokens", 0)
                ct = usage.get("completion_tokens", 0)
                self.total_tokens += pt + ct
                self.total_cost += self.calculate_cost(pt, ct)
                return content.strip()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise Exception(f"Groq API error: {e}")
            except Exception as e:
                raise Exception(f"Groq API error: {e}")
        raise Exception("Groq generation failed after retries")

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = self.PRICING.get(self.model, self.PRICING["llama3-8b-8192"])
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost


class MockLLMClient(BaseLLMClient):
    """
    Mock LLM client for testing without making real API calls.
    Returns predefined responses based on keyword matching or default response.
    Tracks all calls for testing verification.
    """
    
    def __init__(
        self,
        predefined_responses: Optional[Dict[str, str]] = None,
        default_response: str = "Mock LLM response"
    ):
        """
        Initialize mock LLM client.
        
        Args:
            predefined_responses: Dict mapping keywords to responses
            default_response: Fallback response if no keyword matches
        """
        super().__init__(api_key="mock-key", timeout=1)
        self.predefined_responses = predefined_responses or {}
        self.default_response = default_response
        self.call_count = 0
        self.last_prompt = None
        self.call_history = []
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Return predefined or default response based on prompt keywords.
        Tracks call for testing verification.
        """
        self.call_count += 1
        self.last_prompt = prompt
        self.call_history.append({
            "type": "generate",
            "prompt": prompt,
            "system_prompt": system_prompt,
            "temperature": temperature,
            "max_tokens": max_tokens
        })
        
        # Check for keyword matches in predefined responses
        prompt_lower = prompt.lower()
        for keyword, response in self.predefined_responses.items():
            if keyword.lower() in prompt_lower:
                return response
        
        # Return default response if no match
        return self.default_response
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 150
    ) -> str:
        """
        Return predefined or default response based on message keywords.
        Combines all user messages for keyword matching.
        """
        self.call_count += 1
        
        # Combine all user messages for keyword matching
        combined_prompt = " ".join(
            msg.get("content", "") for msg in messages if msg.get("role") == "user"
        )
        self.last_prompt = combined_prompt
        self.call_history.append({
            "type": "chat_completion",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        })
        
        # Check for keyword matches
        combined_lower = combined_prompt.lower()
        for keyword, response in self.predefined_responses.items():
            if keyword.lower() in combined_lower:
                return response
        
        # Return default response if no match
        return self.default_response
    
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Mock cost calculation (always returns $0 for testing).
        """
        return 0.0
    
    def reset(self):
        """Reset call tracking for new test."""
        self.call_count = 0
        self.last_prompt = None
        self.call_history = []


class LLMClient:
    """
    Factory class for creating LLM client instances.
    Supports Gemini, Groq, and Mock providers.
    """
    
    @staticmethod
    def create(
        provider: str,
        api_key: str,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseLLMClient:
        """
        Create appropriate LLM client based on provider.
        
        Args:
            provider: Provider name ("gemini", "groq", or "mock")
            api_key: API key for the provider (not used for mock)
            model: Specific model to use (optional, uses provider default)
            **kwargs: Additional provider-specific arguments (timeout, max_retries, etc.)
        
        Returns:
            BaseLLMClient instance
            
        Raises:
            ValueError: If provider is not supported
            
        Example:
            # Gemini client
            llm = LLMClient.create("gemini", api_key="AI...", model="gemini-2.0-flash")
            # Groq client (free model: llama3-8b-8192)
            llm = LLMClient.create("groq", api_key="gsk_...", model="llama3-8b-8192")
            # Mock client for testing
            llm = LLMClient.create("mock", api_key="not-needed",
                                   predefined_responses={"scam": "This is a scam"})
        """
        provider = provider.lower().strip()
        
        if provider == "gemini":
            return GeminiLLMClient(
                api_key=api_key,
                model=model or "gemini-2.0-flash",
                **kwargs
            )
        elif provider == "groq":
            return GroqLLMClient(
                api_key=api_key,
                model=model or "llama3-8b-8192",
                **kwargs
            )
        elif provider == "mock":
            return MockLLMClient(**kwargs)
        else:
            raise ValueError(
                f"Unknown provider: '{provider}'. "
                f"Supported providers: 'gemini', 'groq', 'mock'"
            )
