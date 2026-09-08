import os
from typing import Any

from .base_agent import AgentResult, DenominatorAgent
from .openfda_client import RequestBudget
from .regulatory_context_client import fetch_classification, fetch_recent_recalls, search_literature


class RegulatoryContextAgent(DenominatorAgent):
    """Agent #3: Queries FDA openFDA + PubMed for regulatory context.

    Planned: Days 6-7
    Free public APIs only, no LLM calls.

    Given a product_code (default 'FRN'), fetches:
    - Device classification (device class, regulation number, medical
      specialty) from openFDA device/classification.json.
    - Recall history from openFDA device/recall.json: total count (the
      real signal -- has this product family been recalled often?) plus
      the most recent N recalls in detail.
    - Related medical literature from PubMed, one search per distinct
      problem_category passed in (typically Agent 1's categorization
      output) so results are relevant to the specific failure mode being
      reviewed, not just "infusion pump" in general.
    """

    name = "regulatory_context"
    description = "openFDA + PubMed regulatory context lookup"

    def run(self, inputs: dict[str, Any]) -> AgentResult:
        product_code = inputs.get("product_code", "FRN")
        problem_categories = inputs.get("problem_categories", [])
        recall_limit = inputs.get("recall_limit", 10)
        literature_retmax = inputs.get("literature_retmax", 5)

        cache_key = f"regulatory_context:{product_code}:{sorted(problem_categories)}:{recall_limit}"
        cached = self.cache_manager.get(cache_key) if self.cache_manager else None
        if cached is not None:
            return AgentResult(
                agent_name=self.name,
                success=True,
                output=cached,
                llm_calls_used=0,
                notes="Loaded from cache -- no openFDA/PubMed requests made this run.",
            )

        api_key = os.environ.get("OPENFDA_API_KEY")
        budget = RequestBudget(has_api_key=bool(api_key))

        classification = fetch_classification(product_code, api_key, budget)
        recall_total, recent_recalls = fetch_recent_recalls(product_code, api_key, budget, limit=recall_limit)

        base_term = classification["device_name"] if classification else product_code
        literature: dict[str, dict] = {}
        if problem_categories:
            for category in problem_categories:
                query = f"{base_term} {category}"
                literature[category] = search_literature(query, budget, retmax=literature_retmax)
        else:
            literature["_general"] = search_literature(base_term, budget, retmax=literature_retmax)

        output = {
            "product_code": product_code,
            "classification": classification,
            "recall_total": recall_total,
            "recent_recalls": recent_recalls,
            "literature": literature,
        }

        if self.cache_manager:
            self.cache_manager.set(cache_key, output)

        notes = (
            f"Fetched regulatory context for {product_code}: "
            f"{'classified as device class ' + classification['device_class'] if classification else 'no classification record found'}, "
            f"{recall_total} total recalls on file ({len(recent_recalls)} most recent fetched in detail), "
            f"literature searched for {len(literature)} term(s). {budget.count} requests made "
            "(openFDA + PubMed combined)."
        )

        return AgentResult(
            agent_name=self.name,
            success=True,
            output=output,
            llm_calls_used=0,
            notes=notes,
        )
