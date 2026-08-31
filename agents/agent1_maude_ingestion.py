from typing import Any

from .base_agent import AgentResult, DenominatorAgent


class MaudeIngestionAgent(DenominatorAgent):
    """Agent #1: Fetches FDA MAUDE complaints and normalizes them via LLM.

    Owner: Shahul + Dhruv (Days 3-4)
    Uses 1 Claude API call, cached after first run.
    """

    name = "maude_ingestion"
    description = "MAUDE complaint fetch + LLM normalization"

    def run(self, inputs: dict[str, Any]) -> AgentResult:
        raise NotImplementedError("Implemented in Days 3-4")
