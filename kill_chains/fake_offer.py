import re
from typing import Tuple
from kill_chains.base_kill_chain import BaseKillChain

class FakeOfferKillChain(BaseKillChain):
    """
    3-stage kill-chain for fake offer scams.
    Models lottery, prize, and cashback fraud.
    """
    
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
        
        keywords = self.STAGE_DEFINITIONS[next_stage]["keywords"]
        matches = sum(1 for kw in keywords if kw in msg)
        
        if matches >= 1:
            confidence = min(0.74 + (matches * 0.10), 0.93)
            return (next_stage, confidence)
        
        return (current_stage, 0.0)
