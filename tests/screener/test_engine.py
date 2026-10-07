"""
Unit and Integration Tests for Screener Engine filters.
Covers 15 filterable metrics, Financials D/E carve-out, Debt-Free ICR handling, and custom screener.
"""

import pytest
import pandas as pd
import numpy as np
from src.screener.engine import apply_filters, run_custom_screener, load_screener_config


@pytest.fixture
def sample_financial_df():
    return pd.DataFrame([
        {
            "company_id": "COMP1",
            "company_name": "Non Financial Good",
            "broad_sector": "Industrials",
            "return_on_equity_pct": 20.0,
            "debt_to_equity": 0.5,
            "free_cash_flow_cr": 100.0,
            "revenue_cagr_5yr": 12.0,
            "pat_cagr_5yr": 15.0,
            "operating_profit_margin_pct": 18.0,
            "pe_ratio": 15.0,
            "pb_ratio": 2.5,
            "dividend_yield_pct": 1.5,
            "interest_coverage": 5.0,
            "icr_label": "High Coverage",
            "market_cap_crore": 10000.0,
            "net_profit": 500.0,
            "eps_cagr_5yr": 10.0,
            "asset_turnover": 1.2,
            "sales": 6000.0,
            "composite_quality_score": 85.0
        },
        {
            "company_id": "FIN1",
            "company_name": "Financials Bank",
            "broad_sector": "Financials",
            "return_on_equity_pct": 16.0,
            "debt_to_equity": 8.5,  # High D/E for bank
            "free_cash_flow_cr": 200.0,
            "revenue_cagr_5yr": 11.0,
            "pat_cagr_5yr": 14.0,
            "operating_profit_margin_pct": 25.0,
            "pe_ratio": 12.0,
            "pb_ratio": 1.5,
            "dividend_yield_pct": 2.0,
            "interest_coverage": np.nan,
            "icr_label": None,
            "market_cap_crore": 50000.0,
            "net_profit": 3000.0,
            "eps_cagr_5yr": 12.0,
            "asset_turnover": 0.1,
            "sales": 15000.0,
            "composite_quality_score": 75.0
        },
        {
            "company_id": "DEBTFREE1",
            "company_name": "Zero Debt Co",
            "broad_sector": "Information Technology",
            "return_on_equity_pct": 25.0,
            "debt_to_equity": 0.0,
            "free_cash_flow_cr": 50.0,
            "revenue_cagr_5yr": 8.0,
            "pat_cagr_5yr": 9.0,
            "operating_profit_margin_pct": 22.0,
            "pe_ratio": 22.0,
            "pb_ratio": 4.0,
            "dividend_yield_pct": 0.5,
            "interest_coverage": np.nan,
            "icr_label": "Debt Free",
            "market_cap_crore": 8000.0,
            "net_profit": 400.0,
            "eps_cagr_5yr": 8.0,
            "asset_turnover": 1.5,
            "sales": 3000.0,
            "composite_quality_score": 80.0
        }
    ])


def test_1_roe_min_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"roe_min": 18.0})
    assert len(res) == 2
    assert set(res["company_id"]) == {"COMP1", "DEBTFREE1"}


def test_2_de_max_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"de_max": 1.0})
    # COMP1 (0.5), DEBTFREE1 (0.0), FIN1 (Financials carve-out!)
    assert len(res) == 3


def test_3_fcf_min_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"fcf_min": 75.0})
    assert len(res) == 2
    assert set(res["company_id"]) == {"COMP1", "FIN1"}


def test_4_revenue_cagr_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"revenue_cagr_5yr_min": 10.0})
    assert len(res) == 2
    assert set(res["company_id"]) == {"COMP1", "FIN1"}


def test_5_pat_cagr_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"pat_cagr_5yr_min": 10.0})
    assert len(res) == 2
    assert set(res["company_id"]) == {"COMP1", "FIN1"}


def test_6_opm_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"opm_min": 20.0})
    assert len(res) == 2
    assert set(res["company_id"]) == {"FIN1", "DEBTFREE1"}


def test_7_pe_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"pe_max": 20.0})
    assert len(res) == 2
    assert set(res["company_id"]) == {"COMP1", "FIN1"}


def test_8_pb_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"pb_max": 2.0})
    assert len(res) == 1
    assert res.iloc[0]["company_id"] == "FIN1"


def test_9_dividend_yield_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"dividend_yield_min": 1.0})
    assert len(res) == 2
    assert set(res["company_id"]) == {"COMP1", "FIN1"}


def test_10_icr_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"icr_min": 4.0})
    # COMP1 (ICR=5.0) and DEBTFREE1 (icr_label='Debt Free' infinity rule)
    assert len(res) == 2
    assert set(res["company_id"]) == {"COMP1", "DEBTFREE1"}


def test_11_market_cap_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"market_cap_min": 9000.0})
    assert len(res) == 2
    assert set(res["company_id"]) == {"COMP1", "FIN1"}


def test_12_net_profit_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"net_profit_min": 450.0})
    assert len(res) == 2
    assert set(res["company_id"]) == {"COMP1", "FIN1"}


def test_13_eps_cagr_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"eps_cagr_min": 11.0})
    assert len(res) == 1
    assert res.iloc[0]["company_id"] == "FIN1"


def test_14_asset_turnover_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"asset_turnover_min": 1.0})
    assert len(res) == 2
    assert set(res["company_id"]) == {"COMP1", "DEBTFREE1"}


def test_15_sales_filter(sample_financial_df):
    res = apply_filters(sample_financial_df, {"sales_min": 5000.0})
    assert len(res) == 2
    assert set(res["company_id"]) == {"COMP1", "FIN1"}


def test_16_financials_de_carveout(sample_financial_df):
    # D/E max = 0.8: Non-Financials COMP1 (0.5) passes, DEBTFREE1 (0.0) passes.
    # Financials FIN1 (D/E 8.5) MUST automatically pass because broad_sector is Financials.
    res = apply_filters(sample_financial_df, {"de_max": 0.8})
    assert len(res) == 3
    assert "FIN1" in res["company_id"].values


def test_17_debt_free_icr_handling(sample_financial_df):
    # ICR min threshold = 100. DEBTFREE1 has icr_label='Debt Free', so it MUST pass any threshold.
    res = apply_filters(sample_financial_df, {"icr_min": 100.0})
    assert len(res) == 1
    assert res.iloc[0]["company_id"] == "DEBTFREE1"


def test_24_custom_screener(sample_financial_df):
    filters = {"roe_min": 15.0, "pe_max": 20.0, "de_max": 1.0}
    res = run_custom_screener(sample_financial_df, filters)
    assert len(res) == 2
    assert set(res["company_id"]) == {"COMP1", "FIN1"}
