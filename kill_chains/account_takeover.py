import re
from typing import Tuple
from kill_chains.base_kill_chain import (
    BaseKillChain,
    match_keywords_count,
)

class AccountTakeoverKillChain(BaseKillChain):
    """
    6-stage kill-chain for account takeover scams.
    Models complete account compromise workflow.
    Phase 1 FIX 1: Stage 6 uses patterns for flexible phrase matching.
    """
    
    STAGE_DEFINITIONS = {
        1: {
            "name": "Account Threat Alert",
            "objective": "Create fear of account compromise",
            "keywords": ["account blocked", "suspicious login", "kyc", 
                        "unauthorized access", "non-compliance"]
        },
        2: {
            "name": "Channel Migration",
            "objective": "Move to WhatsApp or phone call",
            "keywords": ["whatsapp", "call", "helpline", "contact us on",
                        "secure channel"],
            "patterns": [r'\+91\d{10}', r'1800\d{6,7}']
        },
        3: {
            "name": "Personal Info Harvesting",
            "objective": "Collect account details and personal data",
            "keywords": ["account number", "mobile number", "date of birth",
                        "pan", "confirm your", "share your"]
        },
        4: {
            "name": "Credential Extraction",
            "objective": "Obtain internet banking credentials",
            "keywords": ["user id", "password", "customer id", 
                        "internet banking", "login details"]
        },
        5: {
            "name": "OTP Deception",
            "objective": "Harvest OTP for account takeover",
            "keywords": ["otp", "6-digit code", "security code",
                        "verification code", "share it"]
        },
        6: {
            "name": "Account Compromise Complete",
            "objective": "Successfully taken over account",
            "patterns": [
                r'\baccount\s+secure\b',
                r'\baccount\s+is\s+(?:now\s+)?secure\b',
                r'\baccount\s+has\s+been\s+secured\b',
                r'\brestored\b',
                r'\bnew\s+password\b',
                r'\bpassword\s+reset\b',
                r'\baccount\s+access\s+restored\b',
                r'\bcheck\s+your\s+email\b',
            ]
        }
    }
    
    def get_stage_count(self) -> int:
        return 6
    
    def get_stage_name(self, stage: int) -> str:
        return self.STAGE_DEFINITIONS[stage]["name"]
    
    def get_stage_objective(self, stage: int) -> str:
        return self.STAGE_DEFINITIONS[stage]["objective"]
    
    def detect_transition(self, current_stage: int, message: str) -> Tuple[int, float]:
        msg = message.lower()
        next_stage = current_stage + 1
        
        if next_stage > 6:
            return (current_stage, 0.0)
        
        stage_def = self.STAGE_DEFINITIONS[next_stage]
        matches = 0
        if "patterns" in stage_def:
            matches += sum(1 for p in stage_def["patterns"] if re.search(p, msg, re.IGNORECASE))
        if "keywords" in stage_def:
            matches += match_keywords_count(stage_def["keywords"], msg)
        
        if matches >= 1:
            confidence = min(0.70 + (matches * 0.08), 0.93)
            return (next_stage, confidence)
        
        return (current_stage, 0.0)
