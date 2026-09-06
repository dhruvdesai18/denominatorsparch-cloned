"""
Shared openFDA device/event client used by both the standalone CLI script
(scripts/fetch_maude_events.py) and MaudeIngestionAgent (agent1). Keeping
this logic in one place means both stay in sync automatically.

See scripts/fetch_maude_events.py's module docstring for the full rationale
behind date-range bisection and the anonymous-vs-keyed page limit split.
"""

import sys
import time
from datetime import date, datetime, timedelta

import requests

BASE_URL = "https://api.fda.gov/device/event.json"
PAGE_LIMIT_WITH_KEY = 1000  # openFDA max records per request
PAGE_LIMIT_NO_KEY = 999  # anonymous requests get HTTP 403 API_KEY_MISSING at exactly limit=1000
SKIP_CAP = 25000  # stay safely under openFDA's ~26,000 skip+limit ceiling
REQUEST_DELAY_SECONDS = 0.3
DAILY_LIMIT_NO_KEY = 1000
DAILY_LIMIT_WITH_KEY = 120000
CSV_FIELDNAMES = [
    "mdr_report_key",
    "event_type",
    "date_received",
    "date_of_event",
    "event_description",
    "device_name",
    "brand_name",
    "manufacturer_name",
    "device_report_product_code",
    "product_problems",
    "patient_outcome",
]


class RequestBudget:
    """Tracks how many openFDA requests we've made this run and warns before
    we run the account out of its daily allowance."""

    def __init__(self, has_api_key: bool):
        self.count = 0
        self.has_api_key = has_api_key
        self.daily_limit = DAILY_LIMIT_WITH_KEY if has_api_key else DAILY_LIMIT_NO_KEY
        self._warned = False

    def record(self):
        self.count += 1
        if not self._warned and self.count >= int(self.daily_limit * 0.9):
            self._warned = True
            print(
                f"WARNING: {self.count} openFDA requests made this run, "
                f"approaching the {self.daily_limit}/day limit for "
                f"{'an API key' if self.has_api_key else 'anonymous access'}. "
                f"{'Set OPENFDA_API_KEY to raise this limit.' if not self.has_api_key else ''}",
                file=sys.stderr,
            )


def build_search(product_code: str, start_date: str, end_date: str) -> str:
    """Build the openFDA `search` query for one date-bounded slice."""
    return (
        f"device.device_report_product_code:{product_code} "
        f"AND date_received:[{start_date} TO {end_date}]"
    )


def api_get(params: dict, api_key: str | None, budget: RequestBudget) -> dict:
    """GET one page from openFDA with basic retry/backoff on rate limiting.

    openFDA returns HTTP 404 (not an error payload) when a query matches zero
    records -- that's treated as an empty result set, not a failure.
    """
    if api_key:
        params = {**params, "api_key": api_key}

    max_retries = 5
    backoff = 1.0
    for attempt in range(max_retries):
        response = requests.get(BASE_URL, params=params, timeout=30)
        budget.record()

        if response.status_code == 404:
            return {"meta": {"results": {"total": 0}}, "results": []}

        if response.status_code == 429 or response.status_code >= 500:
            if attempt == max_retries - 1:
                response.raise_for_status()
            time.sleep(backoff)
            backoff *= 2
            continue

        response.raise_for_status()
        time.sleep(REQUEST_DELAY_SECONDS)
        return response.json()

    raise RuntimeError("openFDA request failed after retries")


def get_total_count(
    product_code: str, start_date: str, end_date: str, api_key: str | None, budget: RequestBudget
) -> int:
    """Probe how many records exist in this date range without fetching them."""
    params = {
        "search": build_search(product_code, start_date, end_date),
        "limit": 1,
    }
    payload = api_get(params, api_key, budget)
    return payload.get("meta", {}).get("results", {}).get("total", 0)


def fetch_slice(
    product_code: str, start_date: str, end_date: str, api_key: str | None, budget: RequestBudget, total: int
) -> list[dict]:
    """Paginate a date slice already known to be at or under SKIP_CAP records."""
    page_limit = PAGE_LIMIT_WITH_KEY if api_key else PAGE_LIMIT_NO_KEY
    records = []
    skip = 0
    fetch_count = min(total, SKIP_CAP)
    while skip < fetch_count:
        params = {
            "search": build_search(product_code, start_date, end_date),
            "limit": page_limit,
            "skip": skip,
        }
        payload = api_get(params, api_key, budget)
        page = payload.get("results", [])
        if not page:
            break
        records.extend(page)
        skip += page_limit
    return records


def collect_records(
    product_code: str, start: date, end: date, api_key: str | None, budget: RequestBudget
) -> tuple[list[dict], list[tuple[str, str]]]:
    """Recursively bisect [start, end] until every slice fits under SKIP_CAP,
    then fetch each slice. Returns (records, capped_slices) where
    capped_slices lists (start, end) date ranges that still exceeded the cap
    even after being narrowed to a single day -- meaning some records in that
    slice were not retrievable via skip/limit pagination.
    """
    all_records: list[dict] = []
    capped_slices: list[tuple[str, str]] = []
    stack = [(start, end)]

    while stack:
        range_start, range_end = stack.pop()
        start_str = range_start.strftime("%Y%m%d")
        end_str = range_end.strftime("%Y%m%d")

        total = get_total_count(product_code, start_str, end_str, api_key, budget)
        if total == 0:
            continue

        if total <= SKIP_CAP:
            print(f"  fetching {start_str}-{end_str}: {total} records")
            all_records.extend(fetch_slice(product_code, start_str, end_str, api_key, budget, total))
            continue

        if range_start == range_end:
            # Can't split any further (single day) and still over the cap:
            # fetch what we can and record the shortfall.
            print(
                f"  WARNING: {start_str} alone has {total} records, over the "
                f"{SKIP_CAP} pagination cap. Fetching first {SKIP_CAP} only."
            )
            all_records.extend(fetch_slice(product_code, start_str, end_str, api_key, budget, total))
            capped_slices.append((start_str, end_str))
            continue

        midpoint = range_start + (range_end - range_start) // 2
        stack.append((midpoint + timedelta(days=1), range_end))
        stack.append((range_start, midpoint))

    return all_records, capped_slices


def first_matching_device(devices: list[dict], product_code: str) -> dict:
    """Reports can list multiple devices; prefer the one matching our
    queried product code, falling back to the first device present."""
    for device in devices or []:
        if device.get("device_report_product_code") == product_code:
            return device
    return (devices or [{}])[0] if devices else {}


def extract_event_description(mdr_text: list[dict]) -> str:
    """Join all 'Description of Event or Problem' narrative segments.
    Falls back to nothing (not fabricated) if the field/type is absent."""
    descriptions = [
        entry.get("text", "")
        for entry in (mdr_text or [])
        if entry.get("text_type_code") == "Description of Event or Problem"
    ]
    return " | ".join(d for d in descriptions if d)


def extract_patient_outcome(patients: list[dict]) -> str:
    """Flatten sequence_number_outcome codes across all patients on the
    report, de-duplicated, preserving first-seen order."""
    seen = []
    for patient in patients or []:
        for outcome in patient.get("sequence_number_outcome") or []:
            if outcome not in seen:
                seen.append(outcome)
    return ";".join(seen)


def dedupe_preserve_order(values: list[str]) -> list[str]:
    """openFDA's product_problems array often repeats the same code once per
    affected device on the report; de-duplicate so downstream problem-code
    tallies aren't skewed by that repetition."""
    seen = []
    for v in values:
        if v not in seen:
            seen.append(v)
    return seen


def flatten_record(raw: dict, product_code: str) -> dict:
    """Convert one raw openFDA device/event record into our flat row shape.
    Any field genuinely absent from the source record is left blank --
    nothing here is guessed or backfilled."""
    device = first_matching_device(raw.get("device", []), product_code)
    product_problems = dedupe_preserve_order(raw.get("product_problems") or [])

    return {
        "mdr_report_key": raw.get("mdr_report_key", ""),
        "event_type": raw.get("event_type", ""),
        "date_received": raw.get("date_received", ""),
        "date_of_event": raw.get("date_of_event", ""),
        "event_description": extract_event_description(raw.get("mdr_text", [])),
        "device_name": device.get("generic_name", ""),
        "brand_name": device.get("brand_name", ""),
        "manufacturer_name": device.get("manufacturer_d_name", "") or raw.get("manufacturer_name", ""),
        "device_report_product_code": device.get("device_report_product_code", ""),
        "product_problems": ";".join(product_problems),
        "patient_outcome": extract_patient_outcome(raw.get("patient", [])),
    }


def parse_date_arg(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()
