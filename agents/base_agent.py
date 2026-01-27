from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    """Abstract base class for all honeypot agents. All agents must implement the process() method that returns a structured dictionary output."""

    @abstractmethod
    def process(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Process input and return structured output specific to agent type.

        Returns:
            Dict[str, Any]: Structured dictionary output containing agent-specific results
        """
        pass
