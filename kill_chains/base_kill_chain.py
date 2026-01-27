from abc import ABC, abstractmethod
from typing import Dict, Tuple, List
import re

class BaseKillChain(ABC):
    """
    Abstract base class for all scam type kill-chains.
    Each scam type implements its own stage definitions and transition logic.
    """
    
    def __init__(self):
        self.current_stage = 1
        self.stage_history: List[int] = [1]
        self.transition_confidences: List[float] = []
        
    @abstractmethod
    def get_stage_count(self) -> int:
        """Return total number of stages for this scam type."""
        pass
    
    @abstractmethod
    def get_stage_name(self, stage: int) -> str:
        """Return human-readable stage name."""
        pass
    
    @abstractmethod
    def get_stage_objective(self, stage: int) -> str:
        """Return what scammer is trying to accomplish in this stage."""
        pass
    
    @abstractmethod
    def detect_transition(self, current_stage: int, message: str) -> Tuple[int, float]:
        """
        Detect if message triggers transition to next stage.
        Returns: (new_stage, confidence_score)
        """
        pass
    
    def analyze_message(self, message: str) -> Dict:
        """
        Main entry point: analyze message and update state.
        """
        new_stage, confidence = self.detect_transition(
            self.current_stage, 
            message
        )
        
        if new_stage != self.current_stage:
            self.current_stage = new_stage
            self.stage_history.append(new_stage)
            self.transition_confidences.append(confidence)
        
        return {
            "currentStage": self.current_stage,
            "stageName": self.get_stage_name(self.current_stage),
            "stageObjective": self.get_stage_objective(self.current_stage),
            "nextPredictedStage": min(self.current_stage + 1, self.get_stage_count()),
            "killChainCompletion": round((self.current_stage / self.get_stage_count()) * 100, 2),
            "transitionConfidence": confidence if new_stage != self.current_stage else 0.0,
            "stageHistory": self.stage_history
        }
