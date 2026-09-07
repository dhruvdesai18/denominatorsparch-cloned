import os
from datetime import date
from typing import Any

from .base_agent import AgentResult, DenominatorAgent
from .maude_client import RequestBudget, collect_records, flatten_record, parse_date_arg
from .problem_categorizer import categorize_problems


class MaudeIngestionAgent(DenominatorAgent):
    """Agent #1: Fetches FDA MAUDE complaints and normalizes them via LLM.

    Owner: Shahul + Dhruv (Days 3-4)
    Uses OpenAI (gpt-4o-mini) to classify each record's narrative into a
    fixed problem category (see problem_categorizer.py); batched and cached
    so re-running on the same records costs nothing. Requires
    OPENAI_API_KEY to be set for the classification step -- the openFDA
    fetch itself needs no key (OPENFDA_API_KEY is optional, raises the
    rate limit if set).
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

        categories, llm_calls, prompt_tokens, completion_tokens = categorize_problems(
            records, cache_manager=self.cache_manager
        )
        for record in records:
            record["problem_category"] = categories.get(record["mdr_report_key"], "")

        output = {
            "records": records,
            "count": len(records),
            "product_code": product_code,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "capped_slices": capped_slices,
            "narratives_normalized": True,
        }

        if self.cache_manager:
            self.cache_manager.set(cache_key, output)

        notes = (
            f"Fetched {len(records)} MAUDE records for product code {product_code} "
            f"({start} to {end}) via {budget.count} openFDA requests. "
            f"Classified problem categories via {llm_calls} OpenAI call(s) "
            f"({prompt_tokens} prompt / {completion_tokens} completion tokens; "
            "0 for chunks served from cache)."
        )
        if capped_slices:
            notes += f" WARNING: {len(capped_slices)} date-slice(s) hit the pagination cap: {capped_slices}."

        return AgentResult(
            agent_name=self.name,
            success=True,
            output=output,
            llm_calls_used=llm_calls,
            notes=notes,
        )
