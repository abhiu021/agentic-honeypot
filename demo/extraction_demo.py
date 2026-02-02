"""
Demo: Hybrid ExtractionAgent (regex + optional LLM for ambiguous cases).

Usage:
  Regex only (no API key needed):
    python demo/extraction_demo.py

  With LLM escalation (set GEMINI_API_KEY or GROQ_API_KEY in .env):
    python demo/extraction_demo.py --llm

  Single message:
    python demo/extraction_demo.py --msg "Your order #9876543210 is ready. Pay at test@paytm"
"""

import sys
import os
import argparse
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Samples: clear regex hits vs ambiguous (order #, standalone 10-digit, multi-UPI)
SAMPLES_CLEAR = [
    "Contact us on +91 9876543210 or pay to scammer@paytm",
    "Track your package: https://fake-track.xyz/verify",
    "Visit www.fake-bank.in to update KYC",
]
SAMPLES_AMBIGUOUS = [
    "Your order #9876543210 has been shipped. Reply with UPI for refund.",
    "Call 9876543210 for support. Or use test@paytm / support@phonepe",
]


def run_demo(use_llm: bool = False, single_message: Optional[str] = None):
    from agents.extraction_agent import ExtractionAgent
    from utils.llm_client import LLMClient
    from config import LLMConfig

    print("\n=== Extraction Demo (LLM escalation: {} ) ===\n".format("ON" if use_llm else "OFF"))

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
            print("LLM client created – ambiguous messages may use LLM.\n")
        except Exception as e:
            print("Could not create LLM client: {}. Running regex-only.\n".format(e))

    agent = ExtractionAgent(llm_client=llm_client)

    if single_message:
        messages = [single_message]
        print("Single message:\n")
    else:
        messages = SAMPLES_CLEAR + SAMPLES_AMBIGUOUS
        print("Clear regex samples, then ambiguous samples:\n")

    for i, msg in enumerate(messages, 1):
        result = agent.extract(msg)
        print('Message {}: "{}"'.format(i, msg[:70] + ("..." if len(msg) > 70 else "")))
        print("  method: {}".format(result.get("method", "?")))
        print("  phones: {}".format(result.get("phones", [])))
        print("  upis:   {}".format(result.get("upis", [])))
        print("  urls:   {}".format(result.get("urls", [])))
        print("  latency_ms: {}  confidence: {}".format(result.get("latency_ms"), result.get("confidence")))
        print()

    print("Done.\n")


def main():
    parser = argparse.ArgumentParser(description="Extraction demo (regex + optional LLM)")
    parser.add_argument("--llm", action="store_true", help="Enable LLM for ambiguous cases (needs API key in .env)")
    parser.add_argument("--msg", type=str, default=None, help="Run on a single message string")
    args = parser.parse_args()
    run_demo(use_llm=args.llm, single_message=args.msg)


if __name__ == "__main__":
    main()
