from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AgentResult:
    agent_name: str
    success: bool
    output: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    llm_calls_used: int = 0
    notes: str = ""


class DenominatorAgent(ABC):
    """Base class for all Denominator pipeline agents."""

    name: str = "unnamed_agent"
    description: str = ""

    def __init__(self, cache_manager=None):
        self.cache_manager = cache_manager

    @abstractmethod
    def run(self, inputs: dict[str, Any]) -> AgentResult:
        """Execute the agent's work and return a structured result."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
