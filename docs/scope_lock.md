# Scope Lock — Denominator Prototype

**Status: LOCKED.** This decision is irreversible for the hackathon prototype.
Every cache key, CSV, and threshold rationale downstream inherits this choice.

> **Correction (2026-09-05):** the product code was corrected from SKI/SKJ/SKL
> to **FRN**. See "Reason for this choice" below. All data pulled and
> verified under this scope (`infusion_pump_maude_events.csv`, 57,731
> records, 2024) uses FRN.

## Product family
- **Product:** Infusion pumps
- **FDA product code:** FRN
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
Infusion pumps (SKI/SKJ/SKL) were the original working scope from Day 1.
On 2026-09-05, this was corrected to **FRN**, the openFDA
`device_report_product_code` actually used for infusion pump MDR event
reports, and the one confirmed against real, verified MAUDE data (see
`scripts/fetch_maude_events.py`). All downstream artifacts — MAUDE
queries, data contracts, fixtures, and prompt design — are built against
this product family and date window.

## Decided by
Dhruv Atul Desai, on behalf of the team — recorded here per the Week 1 plan's
requirement that scope be written down before Day 3 begins. Product code
corrected to FRN on 2026-09-05, also by Dhruv Atul Desai.
