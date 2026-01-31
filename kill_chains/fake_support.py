import re
from typing import Tuple
from kill_chains.base_kill_chain import BaseKillChain, match_keywords_count

class FakeCustomerSupportKillChain(BaseKillChain):
    """
    4-stage kill-chain for fake customer support scams.
    Phase 1 FIX 2: Removed brand names (jio, airtel, amazon) from Stage 2; stage-order validation.
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
            "keywords": [
                "customer care", "customer support", "helpline",
                "technical support", "support team", "care executive",
                "service center", "support representative"
            ]
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
        
        stage_def = self.STAGE_DEFINITIONS[next_stage]
        keywords = stage_def["keywords"]
        matches = match_keywords_count(keywords, msg)
        
        # Phase 1 FIX 2: When we have conversation context, require Stage 1 keywords in context before allowing 1->2
        if current_stage == 1 and next_stage == 2 and self.conversation_context and matches >= 1:
            stage1_keywords = self.STAGE_DEFINITIONS[1]["keywords"]
            context_text = " ".join(m.get("text", "") for m in self.conversation_context)
            stage1_present = match_keywords_count(stage1_keywords, context_text) >= 1
            if not stage1_present:
                return (1, 0.0)
        
        if matches >= 1:
            confidence = min(0.72 + (matches * 0.10), 0.94)
            return (next_stage, confidence)
        
        return (current_stage, 0.0)
