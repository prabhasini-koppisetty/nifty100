"""
Unit tests for Cash Flow KPIs & Capital Allocation Classifier in src/analytics/cashflow_kpis.py.
"""

import pytest
from src.analytics.cashflow_kpis import (
    calculate_free_cash_flow,
    calculate_cfo_quality_score,
    calculate_capex_intensity,
    calculate_fcf_conversion,
    classify_capital_allocation,
)


def test_free_cash_flow_normal_and_negative():
    # Operating = 500, Investing = -200 -> FCF = 300
    assert calculate_free_cash_flow(500.0, -200.0) == 300.0

    # Negative FCF allowed
    assert calculate_free_cash_flow(100.0, -300.0) == -200.0


def test_cfo_quality_score_classifications():
    # High Quality (> 1.0)
    cfo = [120.0, 150.0, 110.0]
    pat = [100.0, 100.0, 100.0]
    score, label = calculate_cfo_quality_score(cfo, pat)
    assert pytest.approx(score, rel=1e-3) == 1.2666
    assert label == "High Quality"

    # Moderate (0.5 to 1.0)
    cfo_mod = [80.0, 70.0, 90.0]
    score_mod, label_mod = calculate_cfo_quality_score(cfo_mod, pat)
    assert label_mod == "Moderate"

    # Accrual Risk (< 0.5)
    cfo_risk = [30.0, 40.0, 20.0]
    score_risk, label_risk = calculate_cfo_quality_score(cfo_risk, pat)
    assert label_risk == "Accrual Risk"

    # Zero PAT -> None
    assert calculate_cfo_quality_score([100.0], [0.0]) == (None, None)


def test_capex_intensity_classifications():
    # Asset Light (< 3%)
    intensity, label = calculate_capex_intensity(-20.0, 1000.0) # 2%
    assert round(intensity, 2) == 2.0
    assert label == "Asset Light"

    # Moderate (3% to 8%)
    intensity_mod, label_mod = calculate_capex_intensity(-50.0, 1000.0) # 5%
    assert label_mod == "Moderate"

    # Capital Intensive (> 8%)
    intensity_high, label_high = calculate_capex_intensity(-120.0, 1000.0) # 12%
    assert label_high == "Capital Intensive"

    # Zero sales -> None
    assert calculate_capex_intensity(-50.0, 0.0) == (None, None)


def test_fcf_conversion():
    # FCF = 300, Operating Profit = 500 -> 60%
    assert calculate_fcf_conversion(300.0, 500.0) == 60.0

    # Operating Profit = 0 -> None
    assert calculate_fcf_conversion(300.0, 0.0) is None


def test_capital_allocation_classifier_patterns():
    # (+,-,-) with high CFO/PAT -> Shareholder Returns
    cfo_s, cfi_s, cff_s, label1 = classify_capital_allocation(500, -200, -100, cfo_pat_ratio=1.2)
    assert (cfo_s, cfi_s, cff_s) == ("+", "-", "-")
    assert label1 == "Shareholder Returns"

    # (+,-,-) with normal CFO/PAT -> Reinvestor
    _, _, _, label2 = classify_capital_allocation(500, -200, -100, cfo_pat_ratio=0.8)
    assert label2 == "Reinvestor"

    # (+,+,-) -> Liquidating Assets
    _, _, _, label3 = classify_capital_allocation(500, 100, -200)
    assert label3 == "Liquidating Assets"

    # (-,+,+) -> Distress Signal
    _, _, _, label4 = classify_capital_allocation(-100, 50, 80)
    assert label4 == "Distress Signal"

    # (-,-,+) -> Growth Funded by Debt
    _, _, _, label5 = classify_capital_allocation(-100, -200, 400)
    assert label5 == "Growth Funded by Debt"

    # (+,+,+) -> Cash Accumulator
    _, _, _, label6 = classify_capital_allocation(100, 200, 300)
    assert label6 == "Cash Accumulator"

    # (-,-,-) -> Pre-Revenue
    _, _, _, label7 = classify_capital_allocation(-50, -50, -50)
    assert label7 == "Pre-Revenue"

    # (+,-,+) -> Mixed
    _, _, _, label8 = classify_capital_allocation(100, -50, 50)
    assert label8 == "Mixed"
