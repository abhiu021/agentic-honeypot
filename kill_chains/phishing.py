import re
from typing import Tuple
from kill_chains.base_kill_chain import BaseKillChain, match_keywords_count

class PhishingKillChain(BaseKillChain):
    """
    3-stage kill-chain for phishing link scams.
    Models credential harvesting via fake websites.
    """
    
    STAGE_DEFINITIONS = {
        1: {
            "name": "Urgency with Link",
            "objective": "Create urgency and include phishing link",
            "keywords": ["click here", "verify now", "update", "confirm"],
            "patterns": [r'http[s]?://[^\s]+', r'bit\.ly', r'tinyurl']
        },
        2: {
            "name": "Credential Harvesting Page",
            "objective": "Direct to fake login page",
            "keywords": ["enter your", "login", "password", "username",
                        "submit", "sign in"]
        },
        3: {
            "name": "Data Exfiltration Complete",
            "objective": "Credentials submitted to attacker server",
            "keywords": ["processing", "verified", "successful", 
                        "account updated"]
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
        
        stage_def = self.STAGE_DEFINITIONS[next_stage]
        matches = 0
        if "patterns" in stage_def:
            matches += sum(1 for p in stage_def["patterns"] if re.search(p, msg, re.IGNORECASE))
        if "keywords" in stage_def:
            matches += match_keywords_count(stage_def["keywords"], msg)
        
        if matches >= 1:
            confidence = min(0.75 + (matches * 0.10), 0.92)
            return (next_stage, confidence)
        
        return (current_stage, 0.0)
