from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from .detection_agent import DetectionAgent
from .enhanced_detection_agent import EnhancedDetectionAgent
from .extraction_agent import ExtractionAgent
from .strategic_agent import StrategicAgent
from .engagement_agent import EngagementAgent
from .ethics_agent import EthicsAgent

__all__ = [
    "BaseAgent",
    "DetectionAgent",
    "EnhancedDetectionAgent",
    "ExtractionAgent",
    "StrategicAgent",
    "EngagementAgent",
    "EthicsAgent",
    "initialize_agent_pipeline",
]


def initialize_agent_pipeline(llm_client: Optional[Any] = None) -> Dict[str, Any]:
    """
    Production agent factory - all 5 agents + kill chain getter.
    Call from api/routes with optional LLM client (from config).
    """
    get_kill_chain = None
    try:
        from kill_chains import get_kill_chain as _gkc
        get_kill_chain = _gkc
    except Exception:
        pass
    return {
        "detection": DetectionAgent(),
        "strategy": StrategicAgent(llm_client=llm_client),
        "engagement": EngagementAgent(llm_client=llm_client),
        "extraction": ExtractionAgent(llm_client=None),
        "ethics": EthicsAgent(),
        "get_kill_chain": get_kill_chain,
        "llm_client": llm_client,
    }
