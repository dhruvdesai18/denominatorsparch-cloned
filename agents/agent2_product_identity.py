from typing import Any

from .base_agent import AgentResult, DenominatorAgent


class ProductIdentityAgent(DenominatorAgent):
    """Agent #2: Cross-references complaints to official GUDIDs.

    Owner: Pranay + Roma (Day 5)
    Uses 1 OpenAI (gpt-4o-mini) API call, cached after first run.
    See agents/llm_client.py for the shared client (switched from the
    original Claude plan to OpenAI on 2026-09-07).
    """

    name = "product_identity"
    description = "AccessGUDID cross-reference + canonical device mapping"

    def run(self, inputs: dict[str, Any]) -> AgentResult:
        raise NotImplementedError("Implemented on Day 5")
