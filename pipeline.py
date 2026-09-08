"""
Pipeline orchestrator: chains all 6 stages (Agents 1-5 + Rate Engine) into
one run, passing each stage's output into the next.

Stops cleanly -- returns a PipelineResult with halted_at/halt_reason set,
never crashes or silently passes bad data downstream -- the moment any
stage can't produce usable output: an agent reports failure, a fetch
returns zero records, or the rate engine has no usable exposure data.

This is intentionally NOT the human decision gate. It stops right after
Agent 5 produces DRAFT Safety Action Pack(s). Per docs/architecture_spec.md,
nothing past that point may happen without a human explicitly reviewing
and deciding DISMISS / INVESTIGATE FURTHER / CONFIRM -- no code here (or
anywhere else in this pipeline) makes that call.
"""

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agents.agent1_maude_ingestion import MaudeIngestionAgent
from agents.agent2_product_identity import ProductIdentityAgent
from agents.agent3_regulatory_context import RegulatoryContextAgent
from agents.agent4_scope_validation import ScopeValidationAgent
from agents.agent5_document_impact import DocumentImpactAgent
from config.cache_manager import CacheManager
from rate_engine import compute_rates_for_exposure, load_csv_rows

DATA_DIR = Path(__file__).parent / "data"


@dataclass
class PipelineResult:
    product_code: str
    start_date: str
    end_date: str
    stage_results: dict[str, Any] = field(default_factory=dict)
    halted_at: str | None = None
    halt_reason: str | None = None

    @property
    def completed(self) -> bool:
        return self.halted_at is None


def _halt(result: PipelineResult, stage: str, reason: str) -> PipelineResult:
    result.halted_at = stage
    result.halt_reason = reason
    return result


def load_data_contracts(product_code: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Load exposure/baseline/document_map rows for this product_code only
    (these CSVs may hold multiple device_codes). A missing or empty file
    is not an error here -- it's surfaced as a halt reason by the stage
    that actually needs the data, so the message is specific rather than
    a generic file-not-found."""

    def _safe_load(name: str) -> list[dict]:
        path = DATA_DIR / name
        if not path.exists():
            return []
        return load_csv_rows(str(path))

    exposure = [r for r in _safe_load("exposure.csv") if r.get("device_code") == product_code]
    baseline = [r for r in _safe_load("baseline.csv") if r.get("device_code") == product_code]
    document_map = [r for r in _safe_load("document_map.csv") if r.get("device_code") == product_code]
    return exposure, baseline, document_map


def run_pipeline(
    product_code: str = "FRN",
    start_date: str = "20240101",
    end_date: str = "20240107",
    geography: str = "US",
    cache_dir: str = "cache",
) -> PipelineResult:
    result = PipelineResult(product_code=product_code, start_date=start_date, end_date=end_date)
    cache = CacheManager(cache_dir=cache_dir)

    r1 = MaudeIngestionAgent(cache_manager=cache).run(
        {"product_code": product_code, "start_date": start_date, "end_date": end_date}
    )
    result.stage_results["agent1"] = r1
    if not r1.success:
        return _halt(result, "agent1", r1.notes)
    if not r1.output.get("records"):
        return _halt(result, "agent1", "No MAUDE records fetched for this product_code/date range.")

    r2 = ProductIdentityAgent(cache_manager=cache).run(
        {"records": r1.output["records"], "product_code": product_code}
    )
    result.stage_results["agent2"] = r2
    if not r2.success:
        return _halt(result, "agent2", r2.notes)

    categories = sorted(
        {r.get("problem_category", "") for r in r2.output["records"] if r.get("problem_category")}
    )
    r3 = RegulatoryContextAgent(cache_manager=cache).run(
        {"product_code": product_code, "problem_categories": categories}
    )
    result.stage_results["agent3"] = r3
    if not r3.success:
        return _halt(result, "agent3", r3.notes)

    r4 = ScopeValidationAgent(cache_manager=cache).run(
        {
            "records": r2.output["records"],
            "start_date": start_date,
            "end_date": end_date,
            "product_code": product_code,
            "geography": geography,
        }
    )
    result.stage_results["agent4"] = r4
    if not r4.success:
        return _halt(result, "agent4", r4.notes)

    in_scope_records = [r for r in r4.output["records"] if r["in_scope"]]

    exposure_rows, baseline_rows, document_map_rows = load_data_contracts(product_code)
    if not exposure_rows:
        return _halt(
            result,
            "rate_engine",
            f"data/exposure.csv has no rows for device_code={product_code} -- cannot compute a rate "
            "without exposure data. Populate it with real or synthetic units_distributed figures.",
        )

    rate_results = compute_rates_for_exposure(in_scope_records, exposure_rows, baseline_rows)
    result.stage_results["rate_engine"] = rate_results

    computable = [r for r in rate_results if r.can_compute]
    if not computable:
        return _halt(
            result,
            "rate_engine",
            "No exposure row produced a computable rate (missing/zero denominators or unparseable periods).",
        )

    agent5 = DocumentImpactAgent(cache_manager=cache)
    packs = [
        agent5.run(
            {
                "rate_result": rate_result,
                "device_code": rate_result.device_code,
                "regulatory_context": r3.output,
                "records": in_scope_records,
                "document_map_rows": document_map_rows,
            }
        )
        for rate_result in computable
    ]
    result.stage_results["agent5"] = packs

    failed = [p.notes for p in packs if not p.success]
    if failed:
        return _halt(result, "agent5", "; ".join(failed))

    return result


def main():
    parser = argparse.ArgumentParser(description="Run the full Denominator pipeline end-to-end.")
    parser.add_argument("--product-code", default="FRN")
    parser.add_argument("--start-date", default="20240101")
    parser.add_argument("--end-date", default="20240107")
    parser.add_argument("--geography", default="US")
    parser.add_argument("--cache-dir", default="cache")
    args = parser.parse_args()

    result = run_pipeline(args.product_code, args.start_date, args.end_date, args.geography, args.cache_dir)

    print(f"Pipeline run: product_code={args.product_code}, period={args.start_date} to {args.end_date}")
    print("=" * 60)
    for stage, stage_result in result.stage_results.items():
        items = stage_result if isinstance(stage_result, list) else [stage_result]
        for item in items:
            print(f"[{stage}] {getattr(item, 'notes', item)}")

    print("=" * 60)
    if result.completed:
        print("Pipeline completed. Draft Safety Action Pack(s) ready for human review.")
        print("NOTE: no DISMISS/INVESTIGATE FURTHER/CONFIRM decision has been made -- that requires a human.")
    else:
        print(f"Pipeline halted at stage '{result.halted_at}': {result.halt_reason}")


if __name__ == "__main__":
    main()
