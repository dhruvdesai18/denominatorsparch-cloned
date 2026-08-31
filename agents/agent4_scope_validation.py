from typing import Any

from .base_agent import AgentResult, DenominatorAgent


class ScopeValidationAgent(DenominatorAgent):
    """Agent #4: Deterministically validates complaint scope.

    Owner: Pranay + Dhruv (Days 6-7)
    Pure Python, no LLM calls.
    """

    name = "scope_validation"
    description = "Deterministic scope_validator.py logic"

    def run(self, inputs: dict[str, Any]) -> AgentResult:
        raise NotImplementedError("Implemented on Days 6-7")
