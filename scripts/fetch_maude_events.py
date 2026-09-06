#!/usr/bin/env python3
"""
Fetch FDA MAUDE adverse event data for infusion pumps (product code FRN) from
the openFDA device/event API and save it as a flat CSV for downstream
signal-detection analysis.

The actual openFDA client logic lives in agents/maude_client.py, shared with
MaudeIngestionAgent (agents/agent1_maude_ingestion.py) so the CLI and the
pipeline agent never drift out of sync. This file is just the CLI wrapper:
argument parsing, CSV writing, and the summary printout.

Usage:
    python scripts/fetch_maude_events.py
    python scripts/fetch_maude_events.py --start-date 20200101 --end-date 20231231
    OPENFDA_API_KEY=xxxxx python scripts/fetch_maude_events.py

Why the date-range splitting:
    openFDA's skip/limit pagination is only reliable up to ~25,000 results
    per query (skip + limit must stay under its ~26,000 hard cap). FRN alone
    may exceed that over its full history, so this script recursively bisects
    the requested date range: it probes each range's total hit count, and
    only paginates a range directly once its count is small enough. Ranges
    that still exceed the cap even at single-day granularity are fetched as
    far as the cap allows and reported at the end so nothing is silently lost.

Rate limits (see https://open.fda.gov/apis/authentication/):
    Without an API key: 240 requests/minute, 1,000 requests/day, and (as of
    this writing) openFDA rejects limit=1000 with HTTP 403 API_KEY_MISSING --
    anonymous requests must use limit=999. This script does that
    automatically when OPENFDA_API_KEY is unset.
    With an API key: 240 requests/minute, 120,000/day, and the full
    limit=1000 page size.
    This script sleeps ~0.3s between requests (~200/min) and prints a
    warning if the running request count approaches the daily cap.
"""

import argparse
import csv
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.maude_client import (  # noqa: E402
    CSV_FIELDNAMES,
    RequestBudget,
    collect_records,
    flatten_record,
    parse_date_arg,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--product-code", default="FRN", help="openFDA device_report_product_code to query (default: FRN)")
    parser.add_argument(
        "--start-date",
        default="19910101",
        help="Start of date_received range, YYYYMMDD (default: 19910101, approx. earliest MAUDE coverage)",
    )
    parser.add_argument(
        "--end-date",
        default=date.today().strftime("%Y%m%d"),
        help="End of date_received range, YYYYMMDD (default: today)",
    )
    parser.add_argument("--output", default="infusion_pump_maude_events.csv", help="Output CSV path")
    args = parser.parse_args()

    start = parse_date_arg(args.start_date)
    end = parse_date_arg(args.end_date)
    if start > end:
        parser.error("--start-date must be on or before --end-date")

    api_key = os.environ.get("OPENFDA_API_KEY")
    budget = RequestBudget(has_api_key=bool(api_key))

    print(f"Querying openFDA device/event for product code {args.product_code!r}")
    print(f"Date range: {args.start_date} to {args.end_date}")
    print(
        f"Rate limit in effect: {budget.daily_limit} requests/day "
        f"({'API key set' if api_key else 'no API key -- set OPENFDA_API_KEY to raise this'})"
    )

    raw_records, capped_slices = collect_records(args.product_code, start, end, api_key, budget)

    rows = [flatten_record(r, args.product_code) for r in raw_records]

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(rows)

    dates_received = [r["date_received"] for r in rows if r["date_received"]]
    print("\n--- Summary ---")
    print(f"Total records pulled: {len(rows)}")
    if dates_received:
        print(f"date_received range covered: {min(dates_received)} to {max(dates_received)}")
    else:
        print("date_received range covered: n/a (no records)")
    print(f"Total openFDA requests made: {budget.count}")
    print(f"Date-slices that hit the pagination cap: {len(capped_slices)}")
    if capped_slices:
        print("  (records in these single-day ranges may be incomplete -- narrow further manually if needed)")
        for s, e in capped_slices:
            print(f"    {s} to {e}")
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    main()
