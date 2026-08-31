"""Token budget tracker for the Denominator hackathon.

Tracks the 3 planned LLM calls (Agents #1, #2, #5) against the 147,000
token allocation (21,000 tokens x 7 people via Manus) and reports spend
against the ~$16.44 estimate.
"""

from dataclasses import dataclass

TOTAL_BUDGET_TOKENS = 147_000


@dataclass
class PlannedCall:
    agent: str
    owner: str
    tokens: int
    cost_usd: float
    week: int


# Costs taken directly from the 14-day plan's budget breakdown table.
PLANNED_CALLS: list[PlannedCall] = [
    PlannedCall("Agent #1: MAUDE Ingestion", "Shahul + Dhruv", 2_300, 5.40, week=1),
    PlannedCall("Agent #2: Product Identity", "Pranay + Roma", 1_800, 4.14, week=1),
    PlannedCall("Agent #5: Document Impact", "Swetha + Pranay", 3_000, 6.90, week=2),
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
            f"| {call.tokens:>6} tok | ${cost:>5.2f}"
        )

    reserve_pct = round((1 - total_tokens_used / TOTAL_BUDGET_TOKENS) * 100, 1)

    lines.append("-" * 40)
    lines.append(f"Total budget:      {TOTAL_BUDGET_TOKENS:,} tokens")
    lines.append(f"Total planned use: {total_tokens_used:,} tokens")
    lines.append(f"Total spend:       ${round(total_cost, 2)}")
    lines.append(f"Reserve:           {reserve_pct}%")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
