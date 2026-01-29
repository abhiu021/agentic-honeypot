import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
from utils.llm_client import LLMClient, MockLLMClient, BaseLLMClient, GeminiLLMClient, GroqLLMClient


# ==================== FIXTURES ====================

@pytest.fixture
def mock_llm_default():
    """Mock LLM with default response."""
    return MockLLMClient(default_response="Test response")


@pytest.fixture
def mock_llm_predefined():
    """Mock LLM with predefined responses for scam detection."""
    responses = {
        "scam": json.dumps({
            "scamDetected": True,
            "scamScore": 0.85,
            "scamType": "UPI_FRAUD",
            "confidence": "HIGH"
        }),
        "urgent": "This message contains urgency tactics",
        "hello": "Hi there!"
    }
    return MockLLMClient(predefined_responses=responses)


# ==================== MOCK CLIENT TESTS ====================

def test_mock_llm_generate_default(mock_llm_default):
    """Test mock LLM returns default response."""
    result = mock_llm_default.generate("test prompt")
    assert result == "Test response"
    assert mock_llm_default.call_count == 1
    assert mock_llm_default.last_prompt == "test prompt"


def test_mock_llm_generate_predefined(mock_llm_predefined):
    """Test mock LLM returns predefined response when keyword matches."""
    result = mock_llm_predefined.generate("Is this a scam message?")
    assert "scamDetected" in result
    assert "UPI_FRAUD" in result
    assert mock_llm_predefined.call_count == 1


def test_mock_llm_generate_case_insensitive(mock_llm_predefined):
    """Test keyword matching is case-insensitive."""
    result = mock_llm_predefined.generate("URGENT MESSAGE")
    assert result == "This message contains urgency tactics"


def test_mock_llm_chat_completion(mock_llm_predefined):
    """Test mock LLM handles chat completion format."""
    messages = [
        {"role": "system", "content": "You are a scam detector"},
        {"role": "user", "content": "hello world"}
    ]
    result = mock_llm_predefined.chat_completion(messages)
    assert result == "Hi there!"
    assert mock_llm_predefined.call_count == 1


def test_mock_llm_chat_completion_combines_messages(mock_llm_predefined):
    """Test chat completion combines multiple user messages."""
    messages = [
        {"role": "user", "content": "Is this"},
        {"role": "assistant", "content": "Let me check"},
        {"role": "user", "content": "a scam?"}
    ]
    result = mock_llm_predefined.chat_completion(messages)
    # Should match "scam" keyword from combined user messages
    assert "scamDetected" in result


def test_mock_llm_call_history_tracking(mock_llm_default):
    """Test mock LLM tracks call history."""
    mock_llm_default.generate("prompt 1", temperature=0.5, max_tokens=100)
    mock_llm_default.generate("prompt 2", temperature=0.8, max_tokens=200)
    
    assert len(mock_llm_default.call_history) == 2
    assert mock_llm_default.call_history[0]["prompt"] == "prompt 1"
    assert mock_llm_default.call_history[0]["temperature"] == 0.5
    assert mock_llm_default.call_history[1]["max_tokens"] == 200


def test_mock_llm_reset(mock_llm_default):
    """Test reset clears call tracking."""
    mock_llm_default.generate("test")
    assert mock_llm_default.call_count == 1
    
    mock_llm_default.reset()
    assert mock_llm_default.call_count == 0
    assert mock_llm_default.last_prompt is None
    assert len(mock_llm_default.call_history) == 0


def test_mock_llm_calculate_cost():
    """Test mock LLM returns zero cost."""
    mock = MockLLMClient()
    cost = mock.calculate_cost(1000, 500)
    assert cost == 0.0


def test_mock_llm_usage_stats(mock_llm_default):
    """Test usage stats tracking."""
    stats = mock_llm_default.get_usage_stats()
    assert "total_tokens" in stats
    assert "total_cost_usd" in stats
    assert stats["total_tokens"] == 0
    assert stats["total_cost_usd"] == 0.0


# ==================== FACTORY TESTS ====================

def test_factory_create_gemini():
    """Test factory creates Gemini client."""
    client = LLMClient.create("gemini", api_key="test-key-456")
    assert isinstance(client, GeminiLLMClient)
    assert client.model == "gemini-2.0-flash"  # Default model


def test_factory_create_gemini_custom_model():
    """Test factory creates Gemini client with custom model."""
    client = LLMClient.create("gemini", api_key="test-key", model="gemini-2.5-pro")
    assert isinstance(client, GeminiLLMClient)
    assert client.model == "gemini-2.5-pro"


def test_factory_create_groq():
    """Test factory creates Groq client."""
    client = LLMClient.create("groq", api_key="gsk-test-key")
    assert isinstance(client, GroqLLMClient)
    assert client.model == "llama3-8b-8192"  # Default free model


def test_factory_create_groq_custom_model():
    """Test factory creates Groq client with custom model."""
    client = LLMClient.create("groq", api_key="gsk-test-key", model="llama3-70b-8192")
    assert isinstance(client, GroqLLMClient)
    assert client.model == "llama3-70b-8192"


def test_factory_create_mock():
    """Test factory creates Mock client."""
    client = LLMClient.create("mock", api_key="not-needed")
    assert isinstance(client, MockLLMClient)


def test_factory_create_mock_with_responses():
    """Test factory creates Mock client with predefined responses."""
    client = LLMClient.create(
        "mock",
        api_key="not-needed",
        predefined_responses={"test": "response"}
    )
    assert isinstance(client, MockLLMClient)
    assert client.predefined_responses == {"test": "response"}


def test_factory_case_insensitive_provider():
    """Test factory handles case-insensitive provider names."""
    client1 = LLMClient.create("GEMINI", api_key="test")
    client2 = LLMClient.create("GROQ", api_key="test")
    client3 = LLMClient.create("Mock", api_key="test")
    
    assert isinstance(client1, GeminiLLMClient)
    assert isinstance(client2, GroqLLMClient)
    assert isinstance(client3, MockLLMClient)


def test_factory_unknown_provider_raises_error():
    """Test factory raises ValueError for unknown provider."""
    with pytest.raises(ValueError) as exc_info:
        LLMClient.create("unknown-provider", api_key="test")
    
    assert "Unknown provider" in str(exc_info.value)
    assert "unknown-provider" in str(exc_info.value)
    assert "gemini" in str(exc_info.value).lower() or "groq" in str(exc_info.value).lower()


def test_factory_passes_kwargs():
    """Test factory passes additional kwargs to client."""
    client = LLMClient.create(
        "gemini",
        api_key="test",
        timeout=10,
        max_retries=5
    )
    assert client.timeout == 10
    assert client.max_retries == 5


# ==================== BASE CLIENT INTERFACE TESTS ====================

def test_base_client_interface():
    """Test all clients implement BaseLLMClient interface."""
    mock = MockLLMClient()
    
    assert isinstance(mock, BaseLLMClient)
    assert hasattr(mock, 'generate')
    assert hasattr(mock, 'chat_completion')
    assert hasattr(mock, 'calculate_cost')
    assert hasattr(mock, 'get_usage_stats')


def test_all_clients_have_required_methods():
    """Test all client types have required methods."""
    clients = [
        LLMClient.create("gemini", "test-key"),
        LLMClient.create("groq", "test-key"),
        LLMClient.create("mock", "test-key")
    ]
    
    for client in clients:
        assert callable(getattr(client, 'generate'))
        assert callable(getattr(client, 'chat_completion'))
        assert callable(getattr(client, 'calculate_cost'))
        assert callable(getattr(client, 'get_usage_stats'))


# ==================== COST CALCULATION TESTS ====================

def test_gemini_cost_calculation():
    """Test Gemini cost calculation."""
    client = LLMClient.create("gemini", "test-key", model="gemini-2.0-flash")
    # gemini-2.0-flash: $0.15/1M input, $0.60/1M output
    cost = client.calculate_cost(1000, 500)
    expected = (1000/1_000_000)*0.15 + (500/1_000_000)*0.60
    assert abs(cost - expected) < 0.0001


def test_groq_cost_calculation():
    """Test Groq cost calculation."""
    client = LLMClient.create("groq", "test-key", model="llama3-8b-8192")
    # llama3-8b-8192: $0.05/1M input, $0.10/1M output (placeholder)
    cost = client.calculate_cost(1000, 500)
    expected = (1000/1_000_000)*0.05 + (500/1_000_000)*0.10
    assert abs(cost - expected) < 0.0001


# ==================== INTEGRATION TESTS ====================

def test_generate_with_system_prompt(mock_llm_predefined):
    """Test generate method with system prompt."""
    result = mock_llm_predefined.generate(
        prompt="say hello",
        system_prompt="You are helpful",
        temperature=0.5,
        max_tokens=100
    )
    assert result == "Hi there!"
    assert mock_llm_predefined.call_history[0]["system_prompt"] == "You are helpful"


def test_chat_completion_with_multiple_turns(mock_llm_default):
    """Test chat completion with conversation history."""
    messages = [
        {"role": "system", "content": "Be helpful"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"},
        {"role": "user", "content": "How are you?"}
    ]
    
    result = mock_llm_default.chat_completion(messages, temperature=0.8)
    assert result == "Test response"
    assert mock_llm_default.call_count == 1
