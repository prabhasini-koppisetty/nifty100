"""
Unit tests for CAGR Engine in src/analytics/cagr.py.
Covers 10+ deterministic scenarios across all 6 edge cases.
"""

import pytest
from src.analytics.cagr import (
    calculate_cagr,
    calculate_series_cagr,
    FLAG_NORMAL,
    FLAG_DECLINE_TO_LOSS,
    FLAG_TURNAROUND,
    FLAG_BOTH_NEGATIVE,
    FLAG_ZERO_BASE,
    FLAG_INSUFFICIENT,
)


def test_cagr_positive_to_positive_normal():
    val, flag = calculate_cagr(100.0, 133.1, 3)
    assert flag == FLAG_NORMAL
    assert val is not None
    assert round(val, 2) == 10.0


def test_cagr_positive_to_negative_decline_to_loss():
    val, flag = calculate_cagr(100.0, -50.0, 5)
    assert val is None
    assert flag == FLAG_DECLINE_TO_LOSS


def test_cagr_negative_to_positive_turnaround():
    val, flag = calculate_cagr(-50.0, 100.0, 5)
    assert val is None
    assert flag == FLAG_TURNAROUND


def test_cagr_negative_to_negative_both_negative():
    val, flag = calculate_cagr(-50.0, -100.0, 5)
    assert val is None
    assert flag == FLAG_BOTH_NEGATIVE


def test_cagr_zero_base():
    val, flag = calculate_cagr(0.0, 100.0, 5)
    assert val is None
    assert flag == FLAG_ZERO_BASE


def test_cagr_insufficient_data():
    val, flag = calculate_cagr(None, 100.0, 5)
    assert val is None
    assert flag == FLAG_INSUFFICIENT

    val2, flag2 = calculate_cagr(100.0, 200.0, 0)
    assert val2 is None
    assert flag2 == FLAG_INSUFFICIENT


def test_series_cagr_5yr_normal():
    series = {
        "2019-03": 100.0,
        "2020-03": 110.0,
        "2021-03": 120.0,
        "2022-03": 130.0,
        "2023-03": 140.0,
        "2024-03": 161.051,
    }
    val, flag = calculate_series_cagr(series, "2024-03", 5)
    assert flag == FLAG_NORMAL
    assert val is not None
    assert round(val, 2) == 10.0


def test_series_cagr_insufficient_years():
    series = {
        "2022-03": 100.0,
        "2023-03": 110.0,
        "2024-03": 120.0,
    }
    # Requesting 5-year CAGR when only 3 years exist
    val, flag = calculate_series_cagr(series, "2024-03", 5)
    assert val is None
    assert flag == FLAG_INSUFFICIENT


def test_series_cagr_missing_target_year():
    series = {
        "2022-03": 100.0,
        "2023-03": 110.0,
    }
    val, flag = calculate_series_cagr(series, "2025-03", 3)
    assert val is None
    assert flag == FLAG_INSUFFICIENT


def test_cagr_flat_growth_zero_percent():
    val, flag = calculate_cagr(100.0, 100.0, 5)
    assert flag == FLAG_NORMAL
    assert val == 0.0
