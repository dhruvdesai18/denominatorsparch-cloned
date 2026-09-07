from typing import Any

from .base_agent import AgentResult, DenominatorAgent


class DocumentImpactAgent(DenominatorAgent):
    """Agent #5: Maps evidence to QMS documents and suggests actions.

    Owner: Swetha + Pranay (Day 9)
    Uses 1 OpenAI (gpt-4o-mini) API call, cached after first run.
    See agents/llm_client.py for the shared client (switched from the
    original Claude plan to OpenAI on 2026-09-07).
    """

    name = "document_impact"
    description = "QMS document impact mapping + Safety Action Pack suggestion"

    def run(self, inputs: dict[str, Any]) -> AgentResult:
        raise NotImplementedError("Implemented on Day 9")
