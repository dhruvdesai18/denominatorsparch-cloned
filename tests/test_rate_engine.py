import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rate_engine import compute_rate, compute_rates_for_exposure, count_complaints_in_period


def test_compute_rate_basic():
    result = compute_rate("FRN", "2024-01-01", "2024-01-31", complaint_count=5, units_distributed=1000)
    assert result.can_compute is True
    assert result.rate_pct == 0.5
    assert result.exceeds_threshold is False  # 0.5% < 0.75% demonstration threshold


def test_compute_rate_exceeds_threshold():
    result = compute_rate("FRN", "2024-01-01", "2024-01-31", complaint_count=10, units_distributed=1000)
    assert result.rate_pct == 1.0
    assert result.exceeds_threshold is True  # 1.0% > 0.75%


def test_compute_rate_refuses_missing_denominator():
    result = compute_rate("FRN", "2024-01-01", "2024-01-31", complaint_count=5, units_distributed=None)
    assert result.can_compute is False
    assert result.rate_pct is None
    assert "No exposure data" in result.reason


def test_compute_rate_refuses_zero_denominator():
    result = compute_rate("FRN", "2024-01-01", "2024-01-31", complaint_count=5, units_distributed=0)
    assert result.can_compute is False
    assert result.rate_pct is None
    assert "zero denominator" in result.reason


def test_compute_rate_zero_complaints_is_valid():
    result = compute_rate("FRN", "2024-01-01", "2024-01-31", complaint_count=0, units_distributed=1000)
    assert result.can_compute is True
    assert result.rate_pct == 0.0
    assert result.exceeds_threshold is False


def test_count_complaints_in_period_filters_by_device_code_and_date():
    from datetime import date

    complaints = [
        {"device_report_product_code": "FRN", "date_received": "20240115"},
        {"device_report_product_code": "FRN", "date_received": "20240201"},  # outside period
        {"device_report_product_code": "SKI", "date_received": "20240115"},  # wrong device
        {"device_report_product_code": "FRN", "date_received": ""},  # unparseable, excluded
    ]
    count = count_complaints_in_period(complaints, "FRN", date(2024, 1, 1), date(2024, 1, 31))
    assert count == 1


def test_compute_rates_for_exposure_end_to_end():
    complaints = [
        {"device_report_product_code": "FRN", "date_received": "20240110"},
        {"device_report_product_code": "FRN", "date_received": "20240120"},
        {"device_report_product_code": "FRN", "date_received": "20240301"},  # outside period
    ]
    exposure_rows = [
        {"device_code": "FRN", "period_start": "2024-01-01", "period_end": "2024-01-31", "units_distributed": "200"},
    ]
    baseline_rows = [
        {"device_code": "FRN", "baseline_rate_pct": "0.5"},
    ]

    results = compute_rates_for_exposure(complaints, exposure_rows, baseline_rows)
    assert len(results) == 1
    result = results[0]
    assert result.complaint_count == 2
    assert result.rate_pct == 1.0  # 2 / 200 * 100
    assert result.exceeds_threshold is True
    assert result.baseline_rate_pct == 0.5


def test_compute_rates_for_exposure_missing_units_never_crashes():
    exposure_rows = [
        {"device_code": "FRN", "period_start": "2024-01-01", "period_end": "2024-01-31", "units_distributed": ""},
    ]
    results = compute_rates_for_exposure([], exposure_rows)
    assert results[0].can_compute is False


def test_compute_rates_for_exposure_malformed_period_never_crashes():
    exposure_rows = [
        {"device_code": "FRN", "period_start": "not-a-date", "period_end": "2024-01-31", "units_distributed": "100"},
    ]
    results = compute_rates_for_exposure([], exposure_rows)
    assert results[0].can_compute is False
