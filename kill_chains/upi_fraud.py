import re
from typing import Tuple
from kill_chains.base_kill_chain import BaseKillChain

class UPIFraudKillChain(BaseKillChain):
    """
    6-stage kill-chain for UPI fraud scams.
    Models complete UPI fraud workflow from urgency creation to fund extraction.
    """
    
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
        """
        Detect stage transitions based on keywords and patterns.
        """
        msg = message.lower()
        next_stage = current_stage + 1
        
        if next_stage > 6:
            return (current_stage, 0.0)
        
        stage_def = self.STAGE_DEFINITIONS[next_stage]
        
        # Check keywords
        keyword_matches = 0
        if "keywords" in stage_def:
            for kw in stage_def["keywords"]:
                if kw in msg:
                    keyword_matches += 1
        
        # Check regex patterns
        pattern_matches = 0
        if "patterns" in stage_def:
            for pattern in stage_def["patterns"]:
                if re.search(pattern, msg):
                    pattern_matches += 1
        
        total_matches = keyword_matches + pattern_matches
        
        # Transition if at least 1 match
        if total_matches >= 1:
            confidence = min(0.70 + (total_matches * 0.10), 0.95)
            return (next_stage, confidence)
        
        return (current_stage, 0.0)
