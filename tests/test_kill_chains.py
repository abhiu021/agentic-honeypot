import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kill_chains import get_kill_chain

def test_upi_fraud_progression():
    """Test UPI fraud kill-chain stage progression"""
    print("\n=== Testing UPI Fraud Kill-Chain ===\n")
    
    kc = get_kill_chain("UPI_FRAUD")
    
    messages = [
        "Your UPI account will be blocked today due to KYC pending.",
        "This is NPCI security team. Please respond immediately.",
        "Please share your UPI ID for verification.",
        "We will send you a Rs 1 verification payment request.",
        "Please enter the OTP you received to confirm.",
        "Transaction processing. Amount will be credited soon."
    ]
    
    for i, msg in enumerate(messages, 1):
        result = kc.analyze_message(msg)
        print(f"Turn {i}: '{msg[:50]}...'")
        print(f"  Stage: {result['currentStage']} - {result['stageName']}")
        print(f"  Completion: {result['killChainCompletion']}%")
        print(f"  Confidence: {result['transitionConfidence']}\n")

def test_account_takeover_progression():
    """Test Account Takeover kill-chain stage progression"""
    print("\n=== Testing Account Takeover Kill-Chain ===\n")
    
    kc = get_kill_chain("ACCOUNT_TAKEOVER")
    
    messages = [
        "Your account has been blocked due to suspicious login.",
        "Contact us immediately on WhatsApp: +919876543210",
        "Please confirm your account number for verification.",
        "We need your internet banking user ID to check transactions.",
        "Share the OTP you just received to restore access.",
        "Your account is now secure. Password reset link sent."
    ]
    
    for i, msg in enumerate(messages, 1):
        result = kc.analyze_message(msg)
        print(f"Turn {i}: '{msg[:50]}...'")
        print(f"  Stage: {result['currentStage']} - {result['stageName']}")
        print(f"  Completion: {result['killChainCompletion']}%\n")

if __name__ == "__main__":
    test_upi_fraud_progression()
    test_account_takeover_progression()
    print("\n[OK] All kill-chain tests completed!")
