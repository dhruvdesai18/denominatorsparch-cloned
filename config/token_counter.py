"""Token budget tracker for the Denominator hackathon.

Tracks the 3 planned LLM calls (Agents #1, #2, #5) against the 147,000
token allocation (21,000 tokens x 7 people via Manus).

Provider note (2026-09-07): the original 14-day plan priced these 3 calls
against Claude. The team switched to OpenAI (gpt-4o-mini) instead -- see
agents/llm_client.py -- so cost_usd below is recomputed at gpt-4o-mini's
list pricing ($0.15 / 1M input tokens, $0.60 / 1M output tokens), assuming
a 70/30 input/output split per call since the original plan didn't track
that split separately. Token counts per call are unchanged since those
size the prompt/response, not the provider. Verify current OpenAI pricing
before treating these dollar figures as exact -- list prices change.
"""

from dataclasses import dataclass

TOTAL_BUDGET_TOKENS = 147_000
INPUT_COST_PER_TOKEN = 0.15 / 1_000_000
OUTPUT_COST_PER_TOKEN = 0.60 / 1_000_000
ASSUMED_INPUT_SHARE = 0.7


def _estimate_cost_usd(tokens: int) -> float:
    input_tokens = tokens * ASSUMED_INPUT_SHARE
    output_tokens = tokens * (1 - ASSUMED_INPUT_SHARE)
    return input_tokens * INPUT_COST_PER_TOKEN + output_tokens * OUTPUT_COST_PER_TOKEN


@dataclass
class PlannedCall:
    agent: str
    owner: str
    tokens: int
    cost_usd: float
    week: int


PLANNED_CALLS: list[PlannedCall] = [
    PlannedCall("Agent #1: MAUDE Ingestion", "Shahul + Dhruv", 2_300, _estimate_cost_usd(2_300), week=1),
    PlannedCall("Agent #2: Product Identity", "Pranay + Roma", 1_800, _estimate_cost_usd(1_800), week=1),
    PlannedCall("Agent #5: Document Impact", "Swetha + Pranay", 3_000, _estimate_cost_usd(3_000), week=2),
]


def report() -> str:
    lines = ["Denominator Token Budget Report", "=" * 40]
    total_tokens_used = 0
    total_cost = 0.0

    for call in PLANNED_CALLS:
        cost = call.cost_usd
        total_tokens_used += call.tokens
        total_cost += cost
        lines.append(
            f"Week {call.week} | {call.agent:<30} | {call.owner:<16} "
            f"| {call.tokens:>6} tok | ${cost:>7.4f}"
        )

    reserve_pct = round((1 - total_tokens_used / TOTAL_BUDGET_TOKENS) * 100, 1)

    lines.append("-" * 40)
    lines.append(f"Total budget:      {TOTAL_BUDGET_TOKENS:,} tokens")
    lines.append(f"Total planned use: {total_tokens_used:,} tokens")
    lines.append(f"Total spend:       ${round(total_cost, 4)} (OpenAI gpt-4o-mini estimate)")
    lines.append(f"Reserve:           {reserve_pct}%")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
