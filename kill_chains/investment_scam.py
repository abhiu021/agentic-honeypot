import re
from typing import Tuple
from kill_chains.base_kill_chain import BaseKillChain

class InvestmentScamKillChain(BaseKillChain):
    """
    6-stage kill-chain for investment scams.
    Models fake trading platforms and Ponzi schemes.
    """
    
    STAGE_DEFINITIONS = {
        1: {
            "name": "Opportunity Lure",
            "objective": "Promise high returns",
            "keywords": ["earn", "guaranteed profit", "passive income",
                        "₹1 lakh per month", "working from home"]
        },
        2: {
            "name": "Trust Building",
            "objective": "Show fake success stories",
            "keywords": ["testimonials", "certified", "trusted platform",
                        "success story", "5000+ members"]
        },
        3: {
            "name": "Small Initial Investment",
            "objective": "Get victim to invest small amount",
            "keywords": ["start with", "minimum investment", "₹5000",
                        "registration fee", "risk-free"]
        },
        4: {
            "name": "Fake Returns Display",
            "objective": "Show fabricated profits",
            "keywords": ["profit", "grew by", "account balance",
                        "payout ready", "congratulations"]
        },
        5: {
            "name": "Large Investment Request",
            "objective": "Request major investment",
            "keywords": ["upgrade", "vip", "premium", "₹1 lakh",
                        "₹50000", "limited time"]
        },
        6: {
            "name": "Withdrawal Block",
            "objective": "Prevent money withdrawal",
            "keywords": ["withdrawal fee", "processing fee", "tax",
                        "unlock account", "gst"]
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
        
        keywords = self.STAGE_DEFINITIONS[next_stage]["keywords"]
        matches = sum(1 for kw in keywords if kw in msg)
        
        if matches >= 1:
            confidence = min(0.68 + (matches * 0.09), 0.91)
            return (next_stage, confidence)
        
        return (current_stage, 0.0)
