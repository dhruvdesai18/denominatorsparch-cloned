"""
Deterministic scope validation: checks each complaint record against the
locked scope (see docs/scope_lock.md) -- product family, review period,
and geography. Pure Python: no LLM calls, no network calls, every check
here is a plain field comparison.

period_start/period_end are NOT read from scope_lock.md automatically.
Per team decision (2026-09-08), the review period is a runtime input to
Agent 4 instead, since different runs validate different periods (e.g.
the verified 2024 MAUDE pull vs. scope_lock.md's original 2026 H1
example). See that doc's Scope descriptor note for the full rationale.

A record with a missing/blank date_received or reporter_country_code is
never silently assumed in-scope -- it's flagged as its own violation
reason (missing_date_received / missing_geography) rather than guessed.
"""

from datetime import date


def parse_record_date(value: str) -> date | None:
    """Parse a record's YYYYMMDD date field. Returns None (not a raised
    error) for blank or malformed values -- callers treat that as its own
    scope violation rather than a crash, since real MAUDE data does
    contain malformed/missing dates."""
    if not value or len(value) != 8:
        return None
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except ValueError:
        return None


def validate_record(
    record: dict, product_code: str, period_start: date, period_end: date, geography: str
) -> tuple[bool, list[str]]:
    """Check one record against the locked scope. Returns (in_scope,
    violations); violations is empty iff in_scope is True."""
    violations = []

    if record.get("device_report_product_code", "") != product_code:
        violations.append("wrong_product_family")

    received = parse_record_date(record.get("date_received", ""))
    if received is None:
        violations.append("missing_date_received")
    elif not (period_start <= received <= period_end):
        violations.append("out_of_period")

    country = record.get("reporter_country_code", "")
    if not country:
        violations.append("missing_geography")
    elif country != geography:
        violations.append("out_of_geography")

    return (len(violations) == 0, violations)


def validate_records(
    records: list[dict], product_code: str, period_start: date, period_end: date, geography: str
) -> list[dict]:
    """Validate every record, returning each with in_scope and
    scope_violations attached (original fields preserved)."""
    validated = []
    for record in records:
        in_scope, violations = validate_record(record, product_code, period_start, period_end, geography)
        validated.append({**record, "in_scope": in_scope, "scope_violations": violations})
    return validated
