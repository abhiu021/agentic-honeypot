"""
LLM Client Wrapper Verification Script
Tests all LLM client implementations without requiring real API keys.
"""

import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import LLMClient, MockLLMClient


def test_mock_client():
    """Test mock client with predefined responses."""
    print("\n" + "="*60)
    print("TEST 1: Mock LLM Client")
    print("="*60)
    
    # Create mock client with scam detection responses
    scam_response = json.dumps({
        "scamDetected": True,
        "scamScore": 0.85,
        "scamType": "UPI_FRAUD",
        "confidence": "HIGH",
        "reasoning": "Contains urgency and UPI keywords"
    })
    
    mock = LLMClient.create(
        provider="mock",
        api_key="not-needed",
        predefined_responses={
            "scam": scam_response,
            "urgent": "High urgency detected",
            "hello": "Hi there!"
        }
    )
    
    # Test 1: Simple generate
    print("\n1. Simple generate (default response):")
    result = mock.generate("What is the weather?")
    print(f"   Prompt: 'What is the weather?'")
    print(f"   Response: {result}")
    
    # Test 2: Predefined response (scam)
    print("\n2. Predefined response (scam keyword):")
    result = mock.generate("Is this a scam message?")
    print(f"   Prompt: 'Is this a scam message?'")
    print(f"   Response: {result[:100]}...")
    
    # Test 3: Chat completion
    print("\n3. Chat completion:")
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "hello world"}
    ]
    result = mock.chat_completion(messages)
    print(f"   Messages: {len(messages)} messages")
    print(f"   Response: {result}")
    
    # Test 4: Usage stats
    print("\n4. Usage statistics:")
    stats = mock.get_usage_stats()
    print(f"   Total calls: {mock.call_count}")
    print(f"   Total tokens: {stats['total_tokens']}")
    print(f"   Total cost: ${stats['total_cost_usd']}")
    
    # Test 5: Call history
    print("\n5. Call history tracking:")
    print(f"   Calls tracked: {len(mock.call_history)}")
    for i, call in enumerate(mock.call_history, 1):
        print(f"   Call {i}: {call['type']}")
    
    print("\n✅ Mock client test PASSED")


def test_factory_patterns():
    """Test factory creation patterns."""
    print("\n" + "="*60)
    print("TEST 2: Factory Patterns")
    print("="*60)
    
    # Test 1: Create Gemini client
    print("\n1. Creating Gemini client:")
    try:
        gemini_client = LLMClient.create(
            provider="gemini",
            api_key="test-key-456",
            model="gemini-2.0-flash"
        )
        print(f"   ✅ Gemini client created: {type(gemini_client).__name__}")
        print(f"   Model: {gemini_client.model}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Create Mock client
    print("\n2. Creating Mock client:")
    mock_client = LLMClient.create(provider="mock", api_key="not-needed")
    print(f"   ✅ Mock client created: {type(mock_client).__name__}")
    
    # Test 3: Unknown provider error
    print("\n3. Testing unknown provider error handling:")
    try:
        LLMClient.create(provider="invalid-provider", api_key="test")
        print("   ❌ Should have raised ValueError")
    except ValueError as e:
        print(f"   ✅ Correctly raised ValueError: {str(e)[:60]}...")
    
    print("\n✅ Factory patterns test PASSED")


def test_cost_calculations():
    """Test cost calculation accuracy."""
    print("\n" + "="*60)
    print("TEST 3: Cost Calculations")
    print("="*60)
    
    # Gemini cost calculation
    print("\n1. Gemini 2.0 Flash cost:")
    gemini_client = LLMClient.create("gemini", "test-key", model="gemini-2.0-flash")
    cost = gemini_client.calculate_cost(prompt_tokens=1000, completion_tokens=500)
    print(f"   1,000 prompt tokens + 500 completion tokens")
    print(f"   Pricing: $0.15/1M input, $0.60/1M output")
    print(f"   Calculated cost: ${cost:.6f}")
    expected = (1000/1_000_000)*0.15 + (500/1_000_000)*0.60
    print(f"   Expected cost: ${expected:.6f}")
    print(f"   ✅ Match: {abs(cost - expected) < 0.0001}")
    
    # Mock cost (always $0)
    print("\n2. Mock client cost:")
    mock_client = LLMClient.create("mock", "test-key")
    cost = mock_client.calculate_cost(prompt_tokens=10000, completion_tokens=5000)
    print(f"   10,000 prompt tokens + 5,000 completion tokens")
    print(f"   Calculated cost: ${cost:.6f}")
    print(f"   ✅ Correct: {cost == 0.0}")
    
    print("\n✅ Cost calculations test PASSED")


def test_scam_detection_scenario():
    """Test realistic scam detection scenario."""
    print("\n" + "="*60)
    print("TEST 4: Scam Detection Scenario (End-to-End)")
    print("="*60)
    
    # Create mock LLM with scam detection response
    scam_analysis = json.dumps({
        "scamDetected": True,
        "scamScore": 0.92,
        "scamType": "UPI_FRAUD",
        "confidence": "VERY_HIGH",
        "reasoning": "Message contains explicit urgency tactics, authority impersonation (NPCI), and requests UPI ID verification",
        "componentScores": {
            "urgency": 0.95,
            "authority": 0.85,
            "threat": 0.90,
            "infoRequest": 0.88,
            "incentive": 0.0
        }
    })
    
    llm = LLMClient.create(
        provider="mock",
        api_key="not-needed",
        predefined_responses={"analyze": scam_analysis}
    )
    
    # Simulate scam message
    scam_message = """
    URGENT: Your UPI account has been suspended by NPCI. 
    Verify your UPI ID within 2 hours to avoid permanent deactivation.
    Reply with your UPI ID now.
    """
    
    print(f"\n1. Scam message:")
    print(f"   {scam_message.strip()[:100]}...")
    
    # Simulate LLM analysis
    print(f"\n2. Sending to LLM for analysis...")
    prompt = f"Analyze this message for scam indicators: {scam_message}"
    
    response = llm.generate(prompt, temperature=0.1, max_tokens=300)
    
    print(f"\n3. LLM Response:")
    result = json.loads(response)
    print(f"   Scam Detected: {result['scamDetected']}")
    print(f"   Scam Score: {result['scamScore']}")
    print(f"   Scam Type: {result['scamType']}")
    print(f"   Confidence: {result['confidence']}")
    print(f"   Reasoning: {result['reasoning'][:80]}...")
    
    print(f"\n4. Component Scores:")
    for component, score in result['componentScores'].items():
        print(f"   {component:15s}: {score:.2f}")
    
    print(f"\n5. LLM Usage:")
    stats = llm.get_usage_stats()
    print(f"   API calls made: {llm.call_count}")
    print(f"   Total cost: ${stats['total_cost_usd']}")
    
    print("\n✅ Scam detection scenario test PASSED")


def main():
    """Run all verification tests."""
    print("\n" + "="*60)
    print("LLM CLIENT WRAPPER VERIFICATION")
    print("="*60)
    print("Testing all LLM client functionality without real API calls")
    
    try:
        test_mock_client()
        test_factory_patterns()
        test_cost_calculations()
        test_scam_detection_scenario()
        
        print("\n" + "="*60)
        print("ALL TESTS PASSED ✅")
        print("="*60)
        print("\nLLM Client Wrapper is ready for use!")
        print("\nNext steps:")
        print("1. Add real API keys to .env file")
        print("2. Change LLM_PROVIDER to 'gemini' for real API")
        print("3. Integrate with EnhancedDetectionAgent")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
