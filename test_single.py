#!/usr/bin/env python3
"""Real-time scam detection - type a message and get detection result."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from agents.enhanced_detection_agent import EnhancedDetectionAgent
from utils.llm_client import LLMClient
from config import llm_config


def main():
    # Build LLM client from config (agent expects llm_client, not llm_config)
    try:
        llm_client = LLMClient.create(
            provider=llm_config.provider,
            api_key=llm_config.get_api_key(),
            model=llm_config.get_model(),
            timeout=llm_config.timeout,
            max_retries=llm_config.max_retries,
        )
    except Exception as e:
        print(f"❌ Failed to initialize LLM client: {e}")
        return

    agent = EnhancedDetectionAgent(llm_client=llm_client)

    print("🔍 Honeypot Detection Agent - Live Test")
    print("=" * 60)

    while True:
        message = input("\n📱 Message (or 'quit'): ").strip()
        if message.lower() in ["quit", "exit", "q"]:
            break

        channel = input("📲 Channel (SMS/WhatsApp/Email): ").strip() or "SMS"

        result = agent.analyze(message, channel)
        print("\n" + "═" * 80)
        print("RESULT:", result)
        print("═" * 80)


if __name__ == "__main__":
    main()
