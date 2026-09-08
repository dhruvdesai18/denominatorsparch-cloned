from typing import Any

from .base_agent import AgentResult, DenominatorAgent
from .maude_client import parse_date_arg
from .scope_validator import validate_records


class ScopeValidationAgent(DenominatorAgent):
    """Agent #4: Deterministically validates complaint scope.

    Planned: Days 6-7
    Pure Python, no LLM calls -- see agents/scope_validator.py for the
    actual comparisons.

    inputs['start_date'] and inputs['end_date'] (YYYYMMDD) are required --
    the review period is a runtime parameter, not read automatically from
    docs/scope_lock.md, per the 2026-09-08 team decision recorded in that
    doc's Scope descriptor note. product_code defaults to 'FRN' and
    geography defaults to 'US', matching scope_lock.md's locked values,
    but both can be overridden per run.
    """

    name = "scope_validation"
    description = "Deterministic scope_validator.py logic"

    def run(self, inputs: dict[str, Any]) -> AgentResult:
        records = inputs.get("records", [])
        if not records:
            return AgentResult(
                agent_name=self.name,
                success=False,
                output={},
                llm_calls_used=0,
                notes="No input records provided -- expected inputs['records'] from Agent 1/2's output.",
            )

        if "start_date" not in inputs or "end_date" not in inputs:
            return AgentResult(
                agent_name=self.name,
                success=False,
                output={},
                llm_calls_used=0,
                notes=(
                    "inputs['start_date'] and inputs['end_date'] (YYYYMMDD) are required. "
                    "The review period is a runtime parameter, not auto-read from "
                    "docs/scope_lock.md -- see that doc's Scope descriptor note."
                ),
            )

        product_code = inputs.get("product_code", "FRN")
        geography = inputs.get("geography", "US")
        period_start = parse_date_arg(inputs["start_date"])
        period_end = parse_date_arg(inputs["end_date"])
        if period_start > period_end:
            return AgentResult(
                agent_name=self.name,
                success=False,
                output={},
                llm_calls_used=0,
                notes=f"start_date ({period_start}) is after end_date ({period_end}).",
            )

        validated = validate_records(records, product_code, period_start, period_end, geography)

        in_scope_count = sum(1 for r in validated if r["in_scope"])
        violation_counts: dict[str, int] = {}
        for r in validated:
            for reason in r["scope_violations"]:
                violation_counts[reason] = violation_counts.get(reason, 0) + 1

        output = {
            "records": validated,
            "count": len(validated),
            "in_scope_count": in_scope_count,
            "out_of_scope_count": len(validated) - in_scope_count,
            "violation_counts": violation_counts,
            "product_code": product_code,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "geography": geography,
        }

        notes = (
            f"Validated {len(validated)} records against product_code={product_code}, "
            f"period={period_start} to {period_end}, geography={geography}: "
            f"{in_scope_count} in scope, {len(validated) - in_scope_count} out of scope "
            f"{violation_counts}."
        )

        return AgentResult(
            agent_name=self.name,
            success=True,
            output=output,
            llm_calls_used=0,
            notes=notes,
        )
