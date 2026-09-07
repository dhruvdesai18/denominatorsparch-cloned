"""
Fetches the canonical GUDID (Global Unique Device Identification Database)
device registry for a product code, via openFDA's device/udi.json mirror.

Why not AccessGUDID's own API: it only supports exact-identifier lookup
(di/udi/record_key params) -- no search by brand name or company name. Since
MAUDE complaints never carry a device identifier (see agent1's data), an
exact-lookup-only API is useless here. openFDA's device/udi.json mirrors the
same GUDID data but supports field search, so that's what this module uses.

No date-range bisection needed here (unlike maude_client.py) -- the FRN
product family has under 1,000 registered devices, well under openFDA's
~25,000 skip/limit pagination cap, verified live.
"""

from .openfda_client import RequestBudget, api_get as _openfda_api_get, page_limit

BASE_URL = "https://api.fda.gov/device/udi.json"
SKIP_CAP = 25000  # same openFDA-wide ceiling as maude_client; not expected to be hit here


def build_search(product_code: str) -> str:
    return f"product_codes.code:{product_code}"


def api_get(params: dict, api_key: str | None, budget: RequestBudget) -> dict:
    return _openfda_api_get(BASE_URL, params, api_key, budget)


def get_total_count(product_code: str, api_key: str | None, budget: RequestBudget) -> int:
    payload = api_get({"search": build_search(product_code), "limit": 1}, api_key, budget)
    return payload.get("meta", {}).get("results", {}).get("total", 0)


def fetch_canonical_devices(product_code: str, api_key: str | None, budget: RequestBudget) -> list[dict]:
    """Fetch every GUDID device record registered under this product code.
    Raises if the population exceeds SKIP_CAP -- that would mean this
    product family has grown far beyond what's been verified to work with
    plain skip/limit pagination, and needs the same bisection treatment as
    maude_client.py before it's safe to trust."""
    total = get_total_count(product_code, api_key, budget)
    if total == 0:
        return []
    if total > SKIP_CAP:
        raise RuntimeError(
            f"{total} GUDID records for product code {product_code} exceeds the "
            f"{SKIP_CAP} pagination cap -- this module needs date/skip bisection "
            "added (see maude_client.collect_records) before it can fetch the "
            "full population safely."
        )

    limit = page_limit(api_key)
    records = []
    skip = 0
    while skip < total:
        payload = api_get(
            {"search": build_search(product_code), "limit": limit, "skip": skip}, api_key, budget
        )
        page = payload.get("results", [])
        if not page:
            break
        records.extend(page)
        skip += limit
    return records


def flatten_canonical_device(raw: dict) -> dict:
    """Extract just the fields useful for identity matching from a raw
    GUDID/device-udi record. Any field genuinely absent is left blank."""
    identifiers = raw.get("identifiers") or []
    primary = next((i for i in identifiers if i.get("type") == "Primary"), None)

    return {
        "gudid_record_key": raw.get("public_device_record_key", ""),
        "primary_di": (primary or {}).get("id", ""),
        "brand_name": raw.get("brand_name", ""),
        "company_name": raw.get("company_name", ""),
        "version_or_model_number": raw.get("version_or_model_number", ""),
        "device_description": raw.get("device_description", ""),
    }
