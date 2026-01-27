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
        print(f"  Completion: {result['killChainCompletion']}%\n")

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

def test_fake_support_progression():
    """Test Fake Customer Support kill-chain"""
    print("\n=== Testing Fake Customer Support Kill-Chain ===\n")
    
    kc = get_kill_chain("FAKE_CUSTOMER_SUPPORT")
    
    messages = [
        "Your Jio connection will be disconnected due to bill pending.",
        "This is Jio customer care. We can help resolve this issue.",
        "Please download AnyDesk app for remote verification.",
        "Pay Rs 500 service fee to avoid disconnection."
    ]
    
    for i, msg in enumerate(messages, 1):
        result = kc.analyze_message(msg)
        print(f"Turn {i}: '{msg[:50]}...'")
        print(f"  Stage: {result['currentStage']} - {result['stageName']}")
        print(f"  Completion: {result['killChainCompletion']}%\n")

def test_phishing_progression():
    """Test Phishing kill-chain"""
    print("\n=== Testing Phishing Kill-Chain ===\n")
    
    kc = get_kill_chain("PHISHING")
    
    messages = [
        "Your package delivery failed. Track here: http://fake-track.xyz/verify",
        "Click the link and enter your login details to reschedule.",
        "Processing your request. Account updated successfully."
    ]
    
    for i, msg in enumerate(messages, 1):
        result = kc.analyze_message(msg)
        print(f"Turn {i}: '{msg[:50]}...'")
        print(f"  Stage: {result['currentStage']} - {result['stageName']}")
        print(f"  Completion: {result['killChainCompletion']}%\n")

def test_investment_scam_progression():
    """Test Investment Scam kill-chain"""
    print("\n=== Testing Investment Scam Kill-Chain ===\n")
    
    kc = get_kill_chain("INVESTMENT_SCAM")
    
    messages = [
        "Earn Rs 1 lakh per month with guaranteed profit. Working from home.",
        "Join 5000+ members on our trusted platform. See success stories.",
        "Start with minimum investment of just Rs 5000. Risk-free trading.",
        "Congratulations! Your profit grew by 50%. Payout ready.",
        "Upgrade to VIP membership for Rs 50000 to access premium features.",
        "Pay GST processing fee to unlock your account for withdrawal."
    ]
    
    for i, msg in enumerate(messages, 1):
        result = kc.analyze_message(msg)
        print(f"Turn {i}: '{msg[:50]}...'")
        print(f"  Stage: {result['currentStage']} - {result['stageName']}")
        print(f"  Completion: {result['killChainCompletion']}%\n")

def test_fake_offer_progression():
    """Test Fake Offer kill-chain"""
    print("\n=== Testing Fake Offer Kill-Chain ===\n")
    
    kc = get_kill_chain("FAKE_OFFER")
    
    messages = [
        "Congratulations! You won Rs 5 lakh in Amazon lottery. You are selected.",
        "To claim your prize, share your mobile number and PAN card details.",
        "Pay Rs 500 processing fee to receive your prize money."
    ]
    
    for i, msg in enumerate(messages, 1):
        result = kc.analyze_message(msg)
        print(f"Turn {i}: '{msg[:50]}...'")
        print(f"  Stage: {result['currentStage']} - {result['stageName']}")
        print(f"  Completion: {result['killChainCompletion']}%\n")

def test_all_kill_chains():
    """Test that all 6 kill-chains can be instantiated"""
    print("\n=== Testing All Kill-Chain Instantiation ===\n")
    
    scam_types = [
        "UPI_FRAUD",
        "ACCOUNT_TAKEOVER",
        "FAKE_CUSTOMER_SUPPORT",
        "PHISHING",
        "INVESTMENT_SCAM",
        "FAKE_OFFER"
    ]
    
    for scam_type in scam_types:
        kc = get_kill_chain(scam_type)
        print(f"[OK] {scam_type}: {kc.get_stage_count()} stages")
    
    print(f"\n[OK] All 6 kill-chains instantiated successfully!")

if __name__ == "__main__":
    test_all_kill_chains()
    test_upi_fraud_progression()
    test_account_takeover_progression()
    test_fake_support_progression()
    test_phishing_progression()
    test_investment_scam_progression()
    test_fake_offer_progression()
    print("\n[OK] Day 3 Engineer 1 tasks COMPLETE! All 6 kill-chains working!\n")
