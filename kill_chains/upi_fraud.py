import re
from typing import Tuple
from kill_chains.base_kill_chain import BaseKillChain, match_keywords_count

class UPIFraudKillChain(BaseKillChain):
    """
    6-stage kill-chain for UPI fraud scams.
    Phase 1 FIX 4: Anti-keywords to block false positives (legit cashback, OTP sent to user).
    """
    
    ANTI_KEYWORDS = {
        3: ["cashback", "credited", "successful", "completed", "received", "official app"],
        5: ["received otp", "your otp is", "otp for"],
    }
    
    STAGE_DEFINITIONS = {
        1: {
            "name": "Urgency Trigger",
            "objective": "Create panic to bypass rational thinking",
            "keywords": ["blocked", "suspended", "urgent", "immediate", 
                        "expire", "deactivated", "2 hours", "30 minutes"]
        },
        2: {
            "name": "Authority Establishment",
            "objective": "Impersonate legitimate institution",
            "keywords": ["npci", "rbi", "customer care", "security team",
                        "compliance", "official", "dear customer"]
        },
        3: {
            "name": "UPI ID Harvesting",
            "objective": "Obtain victim's UPI handle",
            "keywords": ["upi id", "upi handle", "share upi", "confirm upi"],
            "patterns": [r'upi\s+id', r'@(paytm|phonepe|ybl|okaxis)',
                        r'share.{0,20}upi', r'confirm.{0,20}upi']
        },
        4: {
            "name": "Payment Request Deception",
            "objective": "Trick victim into approving money transfer",
            "keywords": ["accept payment", "approve request", "₹1 verification",
                        "payment request", "no money will be deducted"]
        },
        5: {
            "name": "OTP Extraction",
            "objective": "Harvest OTP or mPIN",
            "keywords": ["otp", "pin", "mpin", "6-digit code", 
                        "verification code", "enter the code"]
        },
        6: {
            "name": "Fund Extraction",
            "objective": "Execute unauthorized transaction",
            "keywords": ["transaction", "processing", "completed", 
                        "credited", "confirmed"]
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
        
        # Phase 1 FIX 4: Block false positives with anti-keywords
        if next_stage in self.ANTI_KEYWORDS:
            if any(anti in msg for anti in self.ANTI_KEYWORDS[next_stage]):
                return (current_stage, 0.0)
        
        stage_def = self.STAGE_DEFINITIONS[next_stage]
        matches = 0
        if "patterns" in stage_def:
            matches += sum(1 for p in stage_def["patterns"] if re.search(p, msg, re.IGNORECASE))
        if "keywords" in stage_def:
            matches += match_keywords_count(stage_def["keywords"], msg)
        
        if matches >= 1:
            confidence = min(0.70 + (matches * 0.10), 0.95)
            return (next_stage, confidence)
        
        return (current_stage, 0.0)
