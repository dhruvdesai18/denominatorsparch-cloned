# Scope Lock — Denominator Prototype

**Status: LOCKED.** This decision is irreversible for the hackathon prototype.
Every cache key, CSV, and threshold rationale downstream inherits this choice.

## Product family
- **Product:** Infusion pumps
- **FDA product codes:** SKI, SKJ, SKL
- **Product family ID:** `INFUSION_PUMP_001`

## Scope descriptor
| Field | Value |
|---|---|
| product_family | INFUSION_PUMP_001 |
| period_start | 2026-01-01 |
| period_end | 2026-06-30 |
| geography | US |
| exposure_definition | units distributed |

## Threshold rationale
The demonstration review threshold is **0.75%**. This is a **demonstration
assumption for prototype purposes only** — it is not a clinical, statistical,
or regulatory figure. This sentence is reproduced verbatim in the Safety
Action Pack output so it is never mistaken for a validated threshold.

## Reason for this choice
Infusion pumps (SKI/SKJ/SKL) were the original working scope from Day 1 and
are retained as the locked prototype scope. All downstream artifacts —
MAUDE queries, data contracts, fixtures, and prompt design — are built
against this product family and date window.

## Decided by
Dhruv Atul Desai, on behalf of the team — recorded here per the Week 1 plan's
requirement that scope be written down before Day 3 begins.
