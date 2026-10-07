"""
Unit tests for Profitability, Leverage, and Efficiency Ratios in src/analytics/ratios.py.
"""

import pytest
import logging
from src.analytics.ratios import (
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    calculate_return_on_equity,
    calculate_return_on_capital_employed,
    calculate_return_on_assets,
    calculate_debt_to_equity,
    calculate_high_leverage_flag,
    calculate_interest_coverage,
    calculate_icr_label,
    calculate_icr_warning_flag,
    calculate_net_debt,
    calculate_asset_turnover,
)


def test_net_profit_margin_normal():
    assert calculate_net_profit_margin(150.0, 1000.0) == 15.0


def test_net_profit_margin_zero_sales():
    assert calculate_net_profit_margin(150.0, 0.0) is None


def test_opm_cross_check_logging(caplog):
    caplog.set_level(logging.WARNING)
    # Computed = 15%, Source = 10% (Diff > 1%)
    val = calculate_operating_profit_margin(
        150.0, 1000.0, source_opm=10.0, company_id="TESTCO", year="2024-03"
    )
    assert val == 15.0
    assert "OPM mismatch for TESTCO" in caplog.text


def test_return_on_equity_normal_and_negative_equity():
    # Normal case: NP=200, Eq=100, Res=400 -> ROE = 200 / 500 * 100 = 40.0%
    assert calculate_return_on_equity(200.0, 100.0, 400.0) == 40.0

    # Negative/zero equity: Eq=-200, Res=100 -> total = -100 <= 0 -> None
    assert calculate_return_on_equity(200.0, -200.0, 100.0) is None


def test_roce_normal_and_financials_sector():
    # EBIT=300, Eq=100, Res=400, Borrowings=500 -> CE = 1000 -> ROCE = 30%
    assert calculate_return_on_capital_employed(300.0, 100.0, 400.0, 500.0) == 30.0

    # Financials sector carve-out check
    roce_fin = calculate_return_on_capital_employed(
        300.0, 100.0, 400.0, 5000.0, is_financial=True
    )
    assert roce_fin == (300.0 / 5500.0) * 100.0


def test_return_on_assets_zero_denominator():
    assert calculate_return_on_assets(100.0, 1000.0) == 10.0
    assert calculate_return_on_assets(100.0, 0.0) is None


def test_debt_to_equity_debt_free_returns_zero():
    # Borrowings = 0 -> returns 0.0 (NOT None)
    assert calculate_debt_to_equity(0.0, 100.0, 400.0) == 0.0


def test_icr_zero_interest_and_debt_free_label():
    # Zero interest -> ICR is None
    icr = calculate_interest_coverage(100.0, 20.0, 0.0)
    assert icr is None

    # Debt Free label when ICR is None and interest is 0
    label = calculate_icr_label(icr, interest=0.0, borrowings=0.0)
    assert label == "Debt Free"


def test_high_leverage_flag_and_financials_carveout():
    # High leverage non-financial: D/E = 6.0 > 5 -> True
    assert calculate_high_leverage_flag(6.0, is_financial=False) is True

    # Financials broad_sector carve-out: D/E = 6.0 -> False
    assert calculate_high_leverage_flag(6.0, is_financial=True) is False


def test_icr_warning_flag():
    assert calculate_icr_warning_flag(1.2) is True
    assert calculate_icr_warning_flag(2.5) is False
    assert calculate_icr_warning_flag(None) is False


def test_net_debt_and_asset_turnover():
    # Net Debt = Borrowings (500) - Investments (200) = 300
    assert calculate_net_debt(500.0, 200.0) == 300.0

    # Asset turnover
    assert calculate_asset_turnover(2000.0, 1000.0) == 2.0
    assert calculate_asset_turnover(2000.0, 0.0) is None
