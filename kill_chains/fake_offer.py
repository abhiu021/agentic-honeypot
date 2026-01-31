import re
from typing import Tuple
from kill_chains.base_kill_chain import BaseKillChain, match_keywords_count

class FakeOfferKillChain(BaseKillChain):
    """
    3-stage kill-chain for fake offer scams.
    Phase 1 FIX 4: Anti-keywords for Stage 1 to block legit marketing.
    """
    
    ANTI_KEYWORDS = {
        1: [
            "credited", "earned", "received", "paid",
            "on orders", "on purchase", "minimum order",
            "reward points", "loyalty", "cashback earned",
        ]
    }
    
    STAGE_DEFINITIONS = {
        1: {
            "name": "Too-Good-To-Be-True Offer",
            "objective": "Lure with unrealistic deal",
            "keywords": ["free", "congratulations", "won", "prize",
                        "selected", "lottery", "cashback"]
        },
        2: {
            "name": "Personal Detail Collection",
            "objective": "Harvest personal information",
            "keywords": ["claim", "share your details", "mobile number",
                        "address", "pan card", "aadhar"]
        },
        3: {
            "name": "Payment for Processing",
            "objective": "Extract payment for fake processing fee",
            "keywords": ["processing fee", "shipping charges", "tax",
                        "registration", "pay", "₹500"]
        }
    }
    
    def get_stage_count(self) -> int:
        return 3
    
    def get_stage_name(self, stage: int) -> str:
        return self.STAGE_DEFINITIONS[stage]["name"]
    
    def get_stage_objective(self, stage: int) -> str:
        return self.STAGE_DEFINITIONS[stage]["objective"]
    
    def detect_transition(self, current_stage: int, message: str) -> Tuple[int, float]:
        msg = message.lower()
        next_stage = current_stage + 1
        
        if next_stage > 3:
            return (current_stage, 0.0)
        
        if next_stage in self.ANTI_KEYWORDS:
            if any(anti in msg for anti in self.ANTI_KEYWORDS[next_stage]):
                return (current_stage, 0.0)
        
        stage_def = self.STAGE_DEFINITIONS[next_stage]
        matches = match_keywords_count(stage_def["keywords"], msg)
        
        if matches >= 1:
            confidence = min(0.74 + (matches * 0.10), 0.93)
            return (next_stage, confidence)
        
        return (current_stage, 0.0)
