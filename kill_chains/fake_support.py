import re
from typing import Tuple
from kill_chains.base_kill_chain import BaseKillChain

class FakeCustomerSupportKillChain(BaseKillChain):
    """
    4-stage kill-chain for fake customer support scams.
    Models tech support and service impersonation scams.
    """
    
    STAGE_DEFINITIONS = {
        1: {
            "name": "Service Issue Alert",
            "objective": "Fabricate service problem",
            "keywords": ["disconnection", "overdue", "suspended", "expired",
                        "bill pending", "service will be terminated"]
        },
        2: {
            "name": "Support Impersonation",
            "objective": "Pose as customer care representative",
            "keywords": ["customer care", "customer support", "helpline",
                        "airtel", "jio", "amazon", "technical support"]
        },
        3: {
            "name": "Remote Access Request",
            "objective": "Get victim to install remote access tool",
            "keywords": ["anydesk", "teamviewer", "quicksupport", 
                        "download app", "remote access", "share screen"]
        },
        4: {
            "name": "Payment or Refund Scam",
            "objective": "Extract payment or bank details",
            "keywords": ["refund", "pending amount", "service fee",
                        "bank details", "card details", "pay via"]
        }
    }
    
    def get_stage_count(self) -> int:
        return 4
    
    def get_stage_name(self, stage: int) -> str:
        return self.STAGE_DEFINITIONS[stage]["name"]
    
    def get_stage_objective(self, stage: int) -> str:
        return self.STAGE_DEFINITIONS[stage]["objective"]
    
    def detect_transition(self, current_stage: int, message: str) -> Tuple[int, float]:
        msg = message.lower()
        next_stage = current_stage + 1
        
        if next_stage > 4:
            return (current_stage, 0.0)
        
        keywords = self.STAGE_DEFINITIONS[next_stage]["keywords"]
        matches = sum(1 for kw in keywords if kw in msg)
        
        if matches >= 1:
            confidence = min(0.72 + (matches * 0.10), 0.94)
            return (next_stage, confidence)
        
        return (current_stage, 0.0)
