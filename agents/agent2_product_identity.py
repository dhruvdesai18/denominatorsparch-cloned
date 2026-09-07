import os
from typing import Any

from .base_agent import AgentResult, DenominatorAgent
from .gudid_client import fetch_canonical_devices, flatten_canonical_device
from .openfda_client import RequestBudget
from .product_identity_matcher import match_products


class ProductIdentityAgent(DenominatorAgent):
    """Agent #2: Cross-references complaints to official GUDIDs.

    Owner: Pranay + Roma (Day 5)

    Takes records from Agent 1 (each with a raw brand_name/manufacturer_name
    from MAUDE) and matches each to a canonical device record in the FDA's
    GUDID registry (fetched via openFDA's device/udi.json mirror -- see
    gudid_client.py for why AccessGUDID's own API doesn't work here: it only
    supports exact-identifier lookup, and MAUDE complaints never carry a
    device identifier).

    Matching is 3-tier (agents/product_identity_matcher.py): exact
    normalized-text match (free), then fuzzy candidate narrowing + one
    OpenAI (gpt-4o-mini) call per batch of ambiguous pairs, cached per
    batch. A pair that doesn't clearly match anything is left as
    match_method="no_match" rather than forced onto the nearest candidate.
    """

    name = "product_identity"
    description = "GUDID (via openFDA device/udi) cross-reference + canonical device mapping"

    def run(self, inputs: dict[str, Any]) -> AgentResult:
        records = inputs.get("records", [])
        product_code = inputs.get("product_code", "FRN")

        if not records:
            return AgentResult(
                agent_name=self.name,
                success=False,
                output={},
                llm_calls_used=0,
                notes="No input records provided -- expected inputs['records'] from Agent 1's output.",
            )

        canonical_cache_key = f"gudid_canonical:{product_code}"
        canonical = self.cache_manager.get(canonical_cache_key) if self.cache_manager else None
        if canonical is None:
            api_key = os.environ.get("OPENFDA_API_KEY")
            budget = RequestBudget(has_api_key=bool(api_key))
            raw_canonical = fetch_canonical_devices(product_code, api_key, budget)
            canonical = [flatten_canonical_device(r) for r in raw_canonical]
            if self.cache_manager:
                self.cache_manager.set(canonical_cache_key, canonical)

        # Sorted, not just deduplicated: set iteration order is randomized
        # per-process in Python, which would otherwise scramble which pairs
        # land in which LLM batch across runs and silently break the
        # per-batch cache in match_products.
        pairs = sorted({(r.get("brand_name", ""), r.get("manufacturer_name", "")) for r in records})

        match_map, llm_calls, prompt_tokens, completion_tokens = match_products(
            pairs, canonical, cache_manager=self.cache_manager
        )

        enriched = []
        for record in records:
            match = match_map.get(
                (record.get("brand_name", ""), record.get("manufacturer_name", "")),
                {
                    "gudid_record_key": "",
                    "gudid_brand_name": "",
                    "gudid_company_name": "",
                    "match_method": "no_match",
                },
            )
            enriched.append({**record, **match})

        method_counts = {"exact": 0, "llm": 0, "no_match": 0}
        for match in match_map.values():
            method_counts[match["match_method"]] += 1

        output = {
            "records": enriched,
            "count": len(enriched),
            "distinct_pairs": len(pairs),
            "match_method_counts": method_counts,
            "canonical_device_count": len(canonical),
        }

        notes = (
            f"Matched {len(pairs)} distinct brand/manufacturer pairs against "
            f"{len(canonical)} canonical GUDID records for product code {product_code}: "
            f"{method_counts['exact']} exact, {method_counts['llm']} via LLM, "
            f"{method_counts['no_match']} no_match. "
            f"{llm_calls} OpenAI call(s) made ({prompt_tokens} prompt / "
            f"{completion_tokens} completion tokens; 0 for batches served from cache)."
        )

        return AgentResult(
            agent_name=self.name,
            success=True,
            output=output,
            llm_calls_used=llm_calls,
            notes=notes,
        )
