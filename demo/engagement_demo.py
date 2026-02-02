"""
Demo: EngagementAgent – persona-based honeypot replies.

Usage:
  Without LLM (fallback responses only; no API key):
    python demo/engagement_demo.py

  With LLM (set GEMINI_API_KEY or GROQ_API_KEY in .env):
    python demo/engagement_demo.py --llm

  Single message + persona:
    python demo/engagement_demo.py --msg "Send OTP to verify" --persona NAIVE
"""

import sys
import os
import argparse
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

SAMPLES = [
    "Your UPI will be blocked. Share test@paytm for verification.",
    "RBI official: Verify at https://rbi-fake.com immediately.",
    "Send OTP you received to restore your account.",
]


def run_demo(use_llm: bool = False, single_message: Optional[str] = None, persona: str = "AVERAGE"):
    from agents.engagement_agent import EngagementAgent
    from utils.llm_client import LLMClient
    from config import LLMConfig

    print("\n=== Engagement Demo (LLM: {}) ===\n".format("ON" if use_llm else "OFF"))

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
            print("LLM client created.\n")
        except Exception as e:
            print("Could not create LLM client: {}. Using fallbacks only.\n".format(e))

    agent = EngagementAgent(llm_client=llm_client)
    strategy = {"persona": persona, "engagementObjective": "Engage naturally", "responseApproach": "Show mild skepticism"}

    messages = [single_message] if single_message else SAMPLES
    history = []

    for i, scammer_msg in enumerate(messages, 1):
        print('Scammer: "{}"'.format(scammer_msg[:70] + ("..." if len(scammer_msg) > 70 else "")))
        result = agent.generate_response(scammer_msg, strategy, history)
        print("Persona: {}  Method: {}".format(result["persona"], result["method"]))
        print('Reply:   "{}"'.format(result["response"]))
        print("  latency_ms: {}  sentences: {}  valid: {}".format(
            result["latency_ms"], result["sentences"], result["validation"]["valid"]))
        print()
        history.append({"sender": "scammer", "text": scammer_msg})
        history.append({"sender": "user", "text": result["response"]})

    print("Done.\n")


def main():
    parser = argparse.ArgumentParser(description="Engagement demo (persona replies)")
    parser.add_argument("--llm", action="store_true", help="Use LLM (needs API key in .env)")
    parser.add_argument("--msg", type=str, default=None, help="Single scammer message to reply to")
    parser.add_argument("--persona", type=str, default="AVERAGE", choices=["NAIVE", "AVERAGE", "TECH_SAVVY"], help="Persona to use")
    args = parser.parse_args()
    run_demo(use_llm=args.llm, single_message=args.msg, persona=args.persona)


if __name__ == "__main__":
    main()
