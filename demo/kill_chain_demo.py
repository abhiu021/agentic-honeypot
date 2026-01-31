"""
Demo: Test kill chain implementation (rule-based + optional LLM fallback).

Usage:
  Rule-based only (no API key needed):
    python demo/kill_chain_demo.py

  With LLM fallback (set GEMINI_API_KEY or GROQ_API_KEY in .env):
    python demo/kill_chain_demo.py --llm

  Specific scam type:
    python demo/kill_chain_demo.py --type UPI_FRAUD
    python demo/kill_chain_demo.py --type PHISHING --llm
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from kill_chains import get_kill_chain

# Sample messages per scam type (one short sequence each)
SAMPLES = {
    "UPI_FRAUD": [
        "Your UPI account will be blocked today due to KYC pending.",
        "This is NPCI security team. Please respond immediately.",
        "Please share your UPI ID for verification.",
        "We will send you a Rs 1 verification payment request.",
    ],
    "ACCOUNT_TAKEOVER": [
        "Your account has been blocked due to suspicious login.",
        "Contact us immediately on WhatsApp: +919876543210",
        "Share the OTP you just received to restore access.",
    ],
    "FAKE_CUSTOMER_SUPPORT": [
        "Your Jio connection will be disconnected due to bill pending.",
        "This is Jio customer care. We can help resolve this issue.",
        "Please download AnyDesk app for remote verification.",
    ],
    "PHISHING": [
        "Your package delivery failed. Track here: http://fake-track.xyz/verify",
        "Click the link and enter your login details to reschedule.",
    ],
    "INVESTMENT_SCAM": [
        "Earn Rs 1 lakh per month with guaranteed profit.",
        "Start with minimum investment of just Rs 5000. Risk-free trading.",
    ],
    "FAKE_OFFER": [
        "Congratulations! You won Rs 5 lakh in Amazon lottery.",
        "To claim your prize, share your mobile number and PAN card details.",
    ],
}


def run_demo(scam_type: str = "UPI_FRAUD", use_llm: bool = False):
    from utils.llm_client import LLMClient
    from config import LLMConfig

    print(f"\n=== Kill Chain Demo: {scam_type} (LLM fallback: {'ON' if use_llm else 'OFF'}) ===\n")

    llm_client = None
    if use_llm:
        try:
            cfg = LLMConfig()
            llm_client = LLMClient.create(
                cfg.provider,
                api_key=cfg.get_api_key(),
                model=cfg.get_model(),
                timeout=cfg.timeout,
            )
            print("LLM client created – low-confidence turns may use LLM for stage detection.\n")
        except Exception as e:
            print(f"Could not create LLM client: {e}. Running rule-based only.\n")

    kc = get_kill_chain(scam_type, llm_client=llm_client)
    messages = SAMPLES.get(scam_type, SAMPLES["UPI_FRAUD"])

    for i, msg in enumerate(messages, 1):
        result = kc.analyze_message(msg)
        print(f"Turn {i}: \"{msg[:60]}{'...' if len(msg) > 60 else ''}\"")
        print(f"  Stage: {result['currentStage']} – {result['stageName']}")
        print(f"  Transition confidence: {result.get('transitionConfidence', 0):.2f}")
        print(f"  Completion: {result['killChainCompletion']}%")
        print(f"  LLM used:   {result.get('llmUsed', False)}")
        print()

    print("Done.\n")


def main():
    parser = argparse.ArgumentParser(description="Kill chain demo (rule-based + optional LLM)")
    parser.add_argument("--type", default="UPI_FRAUD", choices=list(SAMPLES.keys()), help="Scam type")
    parser.add_argument("--llm", action="store_true", help="Enable LLM fallback (needs API key in .env)")
    args = parser.parse_args()
    run_demo(scam_type=args.type, use_llm=args.llm)


if __name__ == "__main__":
    main()
