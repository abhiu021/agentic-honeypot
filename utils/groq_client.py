from openai import OpenAI
from typing import Optional, Dict, Any
from utils.llm_client import BaseLLMClient

class GroqLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant", **kwargs):
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key
        )
        self.model = model
    
    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        # Ensure prompt is always a string
        if isinstance(prompt, (dict, list)):
            prompt = str(prompt)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
                **kwargs
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"Groq API error: {str(e)}")

    def chat_completion(self, messages: list, **kwargs) -> Optional[str]:
        """Chat completion endpoint"""
        print(f"DEBUG: Groq chat_completion called with {len(messages)} messages")
        print(f"DEBUG: First message: {messages[0] if messages else 'None'}")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=500,
                **kwargs
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"DEBUG: Full Groq error: {str(e)}")
            raise

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost for Groq (free tier: $0)"""
        return 0.0  # Groq free tier
