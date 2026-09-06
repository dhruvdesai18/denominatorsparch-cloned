import os
from datetime import date
from typing import Any

from .base_agent import AgentResult, DenominatorAgent
from .maude_client import RequestBudget, collect_records, flatten_record, parse_date_arg


class MaudeIngestionAgent(DenominatorAgent):
    """Agent #1: Fetches FDA MAUDE complaints and normalizes them via LLM.

    Owner: Shahul + Dhruv (Days 3-4)
    Uses 1 Claude API call, cached after first run.

    Status: the openFDA fetch half is implemented and cached. The LLM
    narrative-normalization half is NOT yet implemented -- it needs a design
    decision (what should normalization actually produce from
    event_description?) plus an ANTHROPIC_API_KEY, neither of which exist
    in this repo yet. Records returned by run() carry the raw openFDA
    narrative text, unnormalized.
    """

    name = "maude_ingestion"
    description = "MAUDE complaint fetch + LLM normalization"

    def run(self, inputs: dict[str, Any]) -> AgentResult:
        product_code = inputs.get("product_code", "FRN")
        start = parse_date_arg(inputs.get("start_date", "19910101"))
        end = parse_date_arg(inputs.get("end_date", date.today().strftime("%Y%m%d")))

        cache_key = f"maude_ingestion:{product_code}:{start.isoformat()}:{end.isoformat()}"
        cached = self.cache_manager.get(cache_key) if self.cache_manager else None
        if cached is not None:
            return AgentResult(
                agent_name=self.name,
                success=True,
                output=cached,
                llm_calls_used=0,
                notes="Loaded from cache -- no openFDA requests made this run.",
            )

        api_key = os.environ.get("OPENFDA_API_KEY")
        budget = RequestBudget(has_api_key=bool(api_key))

        raw_records, capped_slices = collect_records(product_code, start, end, api_key, budget)
        records = [flatten_record(r, product_code) for r in raw_records]

        output = {
            "records": records,
            "count": len(records),
            "product_code": product_code,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "capped_slices": capped_slices,
            "narratives_normalized": False,
        }

        if self.cache_manager:
            self.cache_manager.set(cache_key, output)

        notes = (
            f"Fetched {len(records)} MAUDE records for product code {product_code} "
            f"({start} to {end}) via {budget.count} openFDA requests. "
            "LLM narrative normalization not yet implemented -- event_description "
            "fields contain raw openFDA text only."
        )
        if capped_slices:
            notes += f" WARNING: {len(capped_slices)} date-slice(s) hit the pagination cap: {capped_slices}."

        return AgentResult(
            agent_name=self.name,
            success=True,
            output=output,
            llm_calls_used=0,
            notes=notes,
        )
