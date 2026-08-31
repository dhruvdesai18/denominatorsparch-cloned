from typing import Any

from .base_agent import AgentResult, DenominatorAgent


class RegulatoryContextAgent(DenominatorAgent):
    """Agent #3: Queries FDA openFDA + PubMed for regulatory context.

    Owner: Pranay + Dhruv (Days 6-7)
    Free public APIs only, no LLM calls.
    """

    name = "regulatory_context"
    description = "openFDA + PubMed regulatory context lookup"

    def run(self, inputs: dict[str, Any]) -> AgentResult:
        raise NotImplementedError("Implemented on Days 6-7")
