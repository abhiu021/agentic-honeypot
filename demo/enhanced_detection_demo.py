"""
Demo script for EnhancedDetectionAgent with real Gemini API.
Tests hybrid detection (rule-based + LLM) on various message types.
"""

import sys
import os
import json
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.enhanced_detection_agent import EnhancedDetectionAgent
from utils.llm_client import LLMClient
from config import llm_config


def print_result(message: str, channel: str, result: Dict[str, Any]):
    """Pretty print detection result."""
    print("\n" + "="*80)
    print(f"MESSAGE: {message}")
    print(f"CHANNEL: {channel}")
    print("-"*80)
    print(f"SCAM DETECTED: {result['scamDetected']}")
    print(f"SCAM SCORE: {result['scamScore']}")
    print(f"SCAM TYPE: {result.get('scamType', 'None')}")
    print(f"CONFIDENCE: {result.get('confidence', 'N/A')}")
    print(f"DETECTION METHOD: {result.get('detectionMethod', 'N/A')}")
    
    if 'ruleBasedScore' in result:
        print(f"RULE-BASED SCORE: {result['ruleBasedScore']} (original)")
        print(f"SCORE CHANGE: +{result['scamScore'] - result['ruleBasedScore']:.2f} (LLM adjustment)")
    
    print(f"REASONING: {result.get('reasoning', 'N/A')}")
    print("="*80)


def main():
    """Run demo with 6 test messages."""
    
    print("\n🚀 ENHANCED DETECTION AGENT DEMO")
    print("="*80)
    print(f"LLM Provider: {llm_config.provider}")
    print(f"Model: {llm_config.get_model()}")
    print(f"High Confidence Threshold: 0.60")
    print(f"Scam Detection Threshold: 0.35")
    print("="*80)
    
    # Initialize LLM client
    try:
        llm_client = LLMClient.create(
            provider=llm_config.provider,
            api_key=llm_config.get_api_key(),
            model=llm_config.get_model(),
            timeout=llm_config.timeout,
            max_retries=llm_config.max_retries
        )
        print("✅ LLM client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize LLM client: {e}")
        return
    
    # Initialize Enhanced Detection Agent
    agent = EnhancedDetectionAgent(llm_client=llm_client)
    
    # Test messages (covering different scenarios)
    test_cases = [
        # Case 1: High confidence - should skip LLM
        {
            "message": "URGENT ACTION REQUIRED: Your bank account will be BLOCKED. Submit your OTP and password IMMEDIATELY or face legal consequences from RBI authorities.",
            "channel": "SMS",
            "expected": "HIGH confidence, skip LLM (obvious scam)"
        },
        
        # Case 2: Low confidence - should call LLM (subtle scam)
        {
            "message": "Hi, there's an important update regarding your payment. Please verify your details.",
            "channel": "SMS",
            "expected": "MEDIUM confidence, LLM enhanced (borderline)"
        },
        
        # Case 3: Low confidence - should call LLM (legitimate)
        {
            "message": "Your Amazon order #12345 has been delivered. Thank you for shopping with us!",
            "channel": "Email",
            "expected": "LOW confidence, legitimate message"
        },
        
        # Case 4: Low confidence - novel scam pattern
        {
            "message": "Congratulations! You've been selected for an exclusive investment opportunity with guaranteed 50% returns. Limited seats available.",
            "channel": "WhatsApp",
            "expected": "LLM catches investment scam"
        },
        
        # Case 5: Borderline case
        {
            "message": "Important security update for your account. Please verify your identity at the earliest.",
            "channel": "SMS",
            "expected": "LLM decides if legitimate or scam"
        },
        
        # Case 6: High confidence legitimate
        {
            "message": "Hi, how are you doing today? Want to meet for coffee?",
            "channel": "WhatsApp",
            "expected": "LOW confidence, clearly not scam"
        }
    ]
    
    # Run tests
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n📋 TEST CASE {i}/6")
        print(f"Expected: {test_case['expected']}")
        
        try:
            result = agent.analyze(
                message=test_case['message'],
                channel=test_case['channel']
            )
            results.append(result)
            print_result(test_case['message'], test_case['channel'], result)
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n\n📊 SUMMARY")
    print("="*80)
    total = len(results)
    scams_detected = sum(1 for r in results if r['scamDetected'])
    high_conf = sum(1 for r in results if r.get('confidence') == 'HIGH')
    llm_used = sum(1 for r in results if r.get('detectionMethod') == 'LLM_ENHANCED')
    
    print(f"Total Messages: {total}")
    print(f"Scams Detected: {scams_detected}")
    print(f"High Confidence (no LLM): {high_conf}")
    print(f"LLM Enhanced: {llm_used}")
    print(f"LLM Usage Rate: {llm_used/total*100:.1f}%" if total > 0 else "LLM Usage Rate: N/A")
    print("="*80)
    
    print("\n✅ Demo completed successfully!")


if __name__ == "__main__":
    main()
